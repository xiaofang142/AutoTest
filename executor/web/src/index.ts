import http from "http";
import express from "express";
import cors from "cors";
import { ensureBrowser, getPage, closeBrowser, pageState, smartScreenshot } from "./browser.js";
import { Capturer } from "./capturer.js";
import { Reporter } from "./reporter.js";
import { RunManager } from "./run-manager.js";
import { executeStep } from "./step-executor.js";
import type { RunEntry } from "./types.js";

// ---------------------------------------------------------------------------
// App setup
// ---------------------------------------------------------------------------
const app = express();
app.use(cors());
app.use(express.json({ limit: "50mb" }));

const server = http.createServer(app);

// ---------------------------------------------------------------------------
// Services & shared capturer for legacy /agent/* endpoints
// ---------------------------------------------------------------------------
const capturer = new Capturer();
const reporter = new Reporter(server);
const runManager = new RunManager(capturer, reporter);

// ---------------------------------------------------------------------------
// Legacy /agent/* endpoints (backward compatible)
// ---------------------------------------------------------------------------

app.post("/agent/navigate", async (req, res) => {
  try {
    const { page } = await ensureBrowser();
    const { url } = req.body;
    if (!url) {
      res.status(400).json({ success: false, message: "URL required" });
      return;
    }
    await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });
    res.json({
      success: true,
      screenshot: await smartScreenshot(false),
      url: page.url(),
    });
  } catch (e: any) {
    res.status(500).json({ success: false, message: e.message });
  }
});

app.post("/agent/execute", async (req, res) => {
  try {
    await ensureBrowser();
    const { action, target, value } = req.body;

    // Clear capturer buffers for this execution
    capturer.clear();

    // Build a synthetic step for the step-executor
    const step = {
      name: `${action} ${target || ""}`,
      action: action || "click",
      target: target || "",
      value: value || undefined,
    };

    const before = await smartScreenshot(false);
    let ok = false;
    let errMsg = "";
    let levelUsed = -1;

    // Level 0: Midscene AI
    try {
      const agent = (await ensureBrowser()).agent;
      const instruction = `${step.action} ${step.target}`;
      await agent.ai(value ? `${instruction} with value "${value}"` : instruction);
      const page = getPage()!;
      await page.waitForTimeout(800);
      ok = true;
      levelUsed = 0;
    } catch (e: any) {
      errMsg = e.message;

      // Level 1 fallback: DOM evaluation
      try {
        const page = getPage()!;
        const found = await page.evaluate(
          ({ t, sel }: { t: string; sel: string[] }) => {
            for (const el of Array.from(document.querySelectorAll(sel.join(",")))) {
              const h = el as HTMLElement;
              if (
                h.innerText?.includes(t) ||
                (el as HTMLInputElement).placeholder?.includes(t)
              ) {
                h.click();
                return true;
              }
            }
            return false;
          },
          {
            t: target || "",
            sel: ["button", "a", "input", "span", "[role='button']", "[role='link']"],
          }
        );
        if (found) {
          ok = true;
          levelUsed = 1;
          await page.waitForTimeout(500);
        }
      } catch {
        // fall through
      }
    }

    const after = ok ? await smartScreenshot(false) : await smartScreenshot(true);
    const state = await pageState();
    const errors = capturer.getErrors();
    const warnings = capturer.getWarnings();
    const network = capturer.getNetwork();
    const confidence = ok ? (levelUsed === 0 ? 0.95 : 0.85) : 0;

    res.json({
      success: ok,
      confidence,
      message: ok
        ? `Done: ${action} ${target}`
        : `Failed: ${errMsg}`,
      screenshotBefore: before,
      screenshotAfter: after,
      consoleLogs: {
        errors: errors.slice(0, 20),
        warnings: warnings.slice(0, 20),
      },
      networkRequests: network
        .filter((n) => n.type === "response")
        .slice(-30)
        .map((n) => ({
          method: n.method,
          url: n.url,
          status: n.status,
          timing: n.timing,
        })),
      pageState: state,
      duration_ms: Date.now() - stepStart(),
    });
  } catch (e: any) {
    res.status(500).json({ success: false, message: e.message });
  }
});

// Track step start time via a simple variable for the legacy endpoint
let _stepStart = Date.now();
function stepStart(): number {
  const now = Date.now();
  const prev = _stepStart;
  _stepStart = now;
  return prev;
}

app.post("/agent/screenshot", async (req, res) => {
  try {
    await ensureBrowser();
    const full = req.body?.full === true;
    res.json({ success: true, screenshot: await smartScreenshot(full) });
  } catch (e: any) {
    res.status(500).json({ success: false, message: e.message });
  }
});

app.get("/health", (_req, res) => {
  const page = getPage();
  res.json({
    status: "ok",
    version: "0.1.0",
    browserReady: page !== null,
    pageUrl: page?.url() || null,
  });
});

app.post("/cleanup", async (_req, res) => {
  await capturer.detach();
  await closeBrowser();
  res.json({ success: true });
});

// ---------------------------------------------------------------------------
// New run management endpoints
// ---------------------------------------------------------------------------

app.post("/run/create", (req, res) => {
  try {
    // Accept both snake_case (from Python client) and camelCase
    const body = req.body as { runId?: string; run_id?: string; entry?: RunEntry };
    const runId = body.runId || body.run_id || "";
    if (!runId || !body.entry) {
      res.status(400).json({ success: false, message: "runId/run_id and entry required" });
      return;
    }
    const state = runManager.create(runId, body.entry);
    res.json({ success: true, run_id: state.runId, status: state.status, totalSteps: state.totalSteps });
  } catch (e: any) {
    res.status(500).json({ success: false, message: e.message });
  }
});

app.post("/run/:id/start", async (req, res) => {
  try {
    const { id } = req.params;
    // Fire and forget — client tracks progress via WebSocket
    runManager.start(id).catch((err) => {
      console.error(`[RunManager] Run ${id} error:`, err);
    });
    res.json({ success: true, runId: id, message: "Run started" });
  } catch (e: any) {
    res.status(500).json({ success: false, message: e.message });
  }
});

app.post("/run/:id/cancel", (req, res) => {
  try {
    const { id } = req.params;
    runManager.cancel(id);
    res.json({ success: true, runId: id, message: "Run cancelled" });
  } catch (e: any) {
    res.status(500).json({ success: false, message: e.message });
  }
});

app.get("/run/:id/progress", (req, res) => {
  try {
    const { id } = req.params;
    const progress = runManager.getProgress(id);
    if (!progress) {
      res.status(404).json({ success: false, message: `Run not found: ${id}` });
      return;
    }
    res.json({ success: true, ...progress });
  } catch (e: any) {
    res.status(500).json({ success: false, message: e.message });
  }
});

app.get("/run/:id/status", (req, res) => {
  try {
    const { id } = req.params;
    const status = runManager.getStatus(id);
    if (!status) {
      res.status(404).json({ success: false, message: `Run not found: ${id}` });
      return;
    }
    res.json({ success: true, run: status });
  } catch (e: any) {
    res.status(500).json({ success: false, message: e.message });
  }
});

// ---------------------------------------------------------------------------
// Start server
// ---------------------------------------------------------------------------
const PORT = parseInt(process.env.PORT || "3100", 10);
server.listen(PORT, () => {
  console.log(`[AutoTest Executor] :${PORT} CDP+Midscene+RunManager`);
});
