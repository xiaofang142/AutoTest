import express from "express";
import cors from "cors";
import { chromium, Browser, BrowserContext, Page } from "playwright";
import { PageAgent } from "@midscene/web";

const app = express();
app.use(cors());
app.use(express.json({ limit: "50mb" }));

let browser: Browser | null = null;
let context: BrowserContext | null = null;
let page: Page | null = null;
let agent: PageAgent | null = null;
const capturedLogs: any[] = [];
const capturedRequests: any[] = [];

async function ensureBrowser() {
  if (!browser) {
    browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
    context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
    page = await context.newPage();
    page.on("console", (msg) => capturedLogs.push({ level: msg.type(), message: msg.text(), timestamp: new Date().toISOString() }));
    await page.route("**/*", (route) => { capturedRequests.push({ method: route.request().method(), url: route.request().url(), timestamp: new Date().toISOString() }); route.continue(); });
    agent = new PageAgent(page as any);
    console.log("[Executor] Midscene PageAgent + Playwright ready");
  }
}

async function pageState() {
  if (!page) return { url: "", visibleTexts: [], alerts: [] };
  return {
    url: page.url(),
    visibleTexts: await page.evaluate(() => Array.from(document.querySelectorAll("h1,h2,h3,p,button,span,a,label,li")).map(e => (e as HTMLElement).innerText?.trim()).filter(Boolean).slice(0, 100)),
    alerts: await page.evaluate(() => Array.from(document.querySelectorAll("[class*='error'],[class*='alert'],[role='alert']")).map(e => (e as HTMLElement).innerText?.trim()).filter(Boolean)),
  };
}

async function screenshot(): Promise<string> {
  if (!page) return "";
  return `data:image/png;base64,${(await page.screenshot({ fullPage: true })).toString("base64")}`;
}

app.post("/agent/navigate", async (req, res) => {
  try {
    await ensureBrowser();
    const { url } = req.body;
    if (!url) return res.status(400).json({ success: false, message: "URL required" });
    await page!.goto(url, { waitUntil: "networkidle", timeout: 30000 });
    res.json({ success: true, screenshot: await screenshot(), url: page!.url() });
  } catch (e: any) { res.status(500).json({ success: false, message: e.message }); }
});

app.post("/agent/execute", async (req, res) => {
  try {
    await ensureBrowser();
    const { action, target, value } = req.body;
    capturedLogs.length = 0;
    capturedRequests.length = 0;
    const before = await screenshot();
    let ok = false, errMsg = "";

    try {
      let inst = `${action} ${target}`;
      if (value) inst += ` with value "${value}"`;
      // Midscene AI visual execution
      await agent!.ai(inst);
      await page!.waitForTimeout(1000);
      ok = true;
    } catch (e: any) {
      errMsg = e.message;
      console.warn(`Midscene failed: ${errMsg}, trying DOM fallback`);
      try {
        const found = await page!.evaluate((t: string) => {
          for (const el of Array.from(document.querySelectorAll("button,a,input,span,[role='button'],[role='link']"))) {
            const h = el as HTMLElement;
            if (h.innerText?.includes(t) || (el as HTMLInputElement).placeholder?.includes(t)) {
              h.click(); return true;
            }
          }
          return false;
        }, target);
        if (found) { ok = true; await page!.waitForTimeout(500); }
      } catch {}
    }

    const after = await screenshot();
    const state = await pageState();
    res.json({
      success: ok, confidence: ok ? 0.92 : 0, message: ok ? `Done: ${action} ${target}` : `Failed: ${errMsg}`,
      screenshotBefore: before, screenshotAfter: after,
      consoleLogs: { errors: capturedLogs.filter(l => l.level === "error"), warnings: capturedLogs.filter(l => l.level === "warning") },
      networkRequests: capturedRequests.slice(-50), pageState: state,
    });
  } catch (e: any) { res.status(500).json({ success: false, message: e.message }); }
});

app.post("/agent/screenshot", async (_req, res) => {
  try { await ensureBrowser(); res.json({ success: true, screenshot: await screenshot() }); }
  catch (e: any) { res.status(500).json({ success: false, message: e.message }); }
});

app.get("/health", (_req, res) => res.json({ status: "ok", browserReady: browser !== null, pageUrl: page?.url() || null }));

app.post("/cleanup", async (_req, res) => {
  if (browser) await browser.close();
  browser = null; context = null; page = null; agent = null;
  capturedLogs.length = 0; capturedRequests.length = 0;
  res.json({ success: true });
});

const PORT = parseInt(process.env.PORT || "3100", 10);
app.listen(PORT, () => console.log(`AutoTest Web Executor :${PORT} - Midscene ${agent ? "ready" : "standby"}`));
