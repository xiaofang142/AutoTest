import express from "express";
import cors from "cors";
import { chromium, Browser, BrowserContext, Page, CDPSession } from "playwright";
import { PageAgent } from "@midscene/web";

const app = express();
app.use(cors());
app.use(express.json({ limit: "50mb" }));

let browser: Browser | null = null;
let context: BrowserContext | null = null;
let page: Page | null = null;
let cdp: CDPSession | null = null;
let agent: PageAgent | null = null;
const capturedLogs: any[] = [];
const capturedNetwork: any[] = [];

async function ensureBrowser() {
  if (!browser) {
    browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
    context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
    page = await context.newPage();

    // CDP for structured network capture (instead of route interception)
    cdp = await context.newCDPSession(page);
    await cdp.send("Network.enable");
    cdp.on("Network.responseReceived", (params: any) => {
      capturedNetwork.push({
        type: "response",
        method: params.response?.requestMethod || "GET",
        url: params.response?.url || "",
        status: params.response?.status || 0,
        mime: params.response?.mimeType || "",
        timing: params.response?.timing || null,
        timestamp: Date.now(),
      });
    });
    cdp.on("Network.requestWillBeSent", (params: any) => {
      capturedNetwork.push({
        type: "request",
        method: params.request?.method || "GET",
        url: params.request?.url || "",
        headers: params.request?.headers || {},
        timestamp: Date.now(),
      });
    });

    // Console with level filtering and cap
    page.on("console", (msg) => {
      if (capturedLogs.length < 200) {
        capturedLogs.push({
          level: msg.type(), message: msg.text(),
          location: msg.location()?.url || "",
          timestamp: Date.now(),
        });
      }
    });

    agent = new PageAgent(page as any);
    console.log("[Executor] CDP + Midscene ready");
  }
}

async function pageState() {
  if (!page) return { url: "", visibleTexts: [], alerts: [], perf: {} };
  const perf = await page.evaluate(() => {
    try {
      const entries = performance.getEntriesByType("resource");
      return entries.slice(-30).map((e: any) => ({
        name: e.name?.split("?"[0]).slice(0, 100),
        duration: Math.round(e.duration),
        type: e.initiatorType,
      }));
    } catch { return []; }
  });
  return {
    url: page.url(),
    visibleTexts: await page.evaluate(() =>
      Array.from(document.querySelectorAll("h1,h2,h3,p,button,span,a,label,li"))
        .map(e => (e as HTMLElement).innerText?.trim()).filter(Boolean).slice(0, 80)),
    alerts: await page.evaluate(() =>
      Array.from(document.querySelectorAll("[class*='error'],[class*='alert'],[role='alert']"))
        .map(e => (e as HTMLElement).innerText?.trim()).filter(Boolean)),
    perf,
  };
}

async function smartScreenshot(full: boolean = false): Promise<string> {
  if (!page) return "";
  const buf = await page.screenshot({ fullPage: full, type: "png" });
  return `data:image/png;base64,${buf.toString("base64")}`;
}

app.post("/agent/navigate", async (req, res) => {
  try {
    await ensureBrowser();
    const { url } = req.body;
    if (!url) return res.status(400).json({ success: false, message: "URL required" });
    await page!.goto(url, { waitUntil: "networkidle", timeout: 30000 });
    res.json({ success: true, screenshot: await smartScreenshot(false), url: page!.url() });
  } catch (e: any) { res.status(500).json({ success: false, message: e.message }); }
});

app.post("/agent/execute", async (req, res) => {
  try {
    await ensureBrowser();
    const { action, target, value } = req.body;
    const stepStart = Date.now();
    capturedLogs.length = 0;
    capturedNetwork.length = 0;

    // Smart screenshot: viewport-only before (faster)
    const before = await smartScreenshot(false);
    let ok = false, errMsg = "";

    try {
      let inst = `${action} ${target}`;
      if (value) inst += ` with value "${value}"`;
      await agent!.ai(inst);
      await page!.waitForTimeout(800);
      ok = true;
    } catch (e: any) {
      errMsg = e.message;
      try {
        const found = await page!.evaluate((t: string) => {
          for (const el of Array.from(document.querySelectorAll("button,a,input,span,[role='button'],[role='link']"))) {
            const h = el as HTMLElement;
            if (h.innerText?.includes(t) || (el as HTMLInputElement).placeholder?.includes(t)) { h.click(); return true; }
          }
          return false;
        }, target);
        if (found) { ok = true; await page!.waitForTimeout(500); }
      } catch {}
    }

    // Smart screenshot: only full-page if action changed the page
    const after = ok ? await smartScreenshot(false) : await smartScreenshot(true);
    const state = await pageState();
    const errors = capturedLogs.filter(l => l.level === "error" || l.level === "exception");
    const warnings = capturedLogs.filter(l => l.level === "warning");

    res.json({
      success: ok, confidence: ok ? 0.92 : 0,
      message: ok ? `Done: ${action} ${target}` : `Failed: ${errMsg}`,
      screenshotBefore: before, screenshotAfter: after,
      consoleLogs: { errors: errors.slice(0, 20), warnings: warnings.slice(0, 20) },
      networkRequests: capturedNetwork
        .filter((n: any) => n.type === "response")
        .slice(-30)
        .map((n: any) => ({ method: n.method, url: n.url, status: n.status, timing: n.timing })),
      pageState: state,
      duration_ms: Date.now() - stepStart,
    });
  } catch (e: any) { res.status(500).json({ success: false, message: e.message }); }
});

app.post("/agent/screenshot", async (req, res) => {
  try {
    await ensureBrowser();
    const full = req.body?.full === true;
    res.json({ success: true, screenshot: await smartScreenshot(full) });
  } catch (e: any) { res.status(500).json({ success: false, message: e.message }); }
});

app.get("/health", (_req, res) => res.json({
  status: "ok", version: "0.1.0",
  browserReady: browser !== null, pageUrl: page?.url() || null,
}));

app.post("/cleanup", async (_req, res) => {
  if (browser) await browser.close();
  browser = null; context = null; page = null; cdp = null; agent = null;
  capturedLogs.length = 0; capturedNetwork.length = 0;
  res.json({ success: true });
});

const PORT = parseInt(process.env.PORT || "3100", 10);
app.listen(PORT, () => console.log(`[AutoTest Executor] :${PORT} CDP+Midscene`));
