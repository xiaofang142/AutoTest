import http from "http";
import express from "express";
import cors from "cors";
import { ensureBrowser, getPage, closeBrowser, pageState, smartScreenshot } from "./browser.js";
import { Capturer } from "./capturer.js";
import { Reporter } from "./reporter.js";
import { discover } from "./discovery/page-discoverer.js";
import { RunManager } from "./run-manager.js";
import { executeStep } from "./step-executor.js";
import type { RunEntry, ExecutableStep } from "./types.js";

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
    const { page, cdpSession } = await ensureBrowser();
    const { url } = req.body;
    if (!url) {
      res.status(400).json({ success: false, message: "URL required" });
      return;
    }
    // Ensure clean CDP state — disable any stale Fetch interception
    try { await cdpSession.send("Fetch.disable"); } catch {}
    await page.goto(url, { waitUntil: "load", timeout: 45000 });
    res.json({
      success: true,
      screenshot: await smartScreenshot(false),
      url: page.url(),
      pageState: await pageState(),
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

    // Build a synthetic step for the pure-Playwright step-executor
    const step: ExecutableStep = {
      name: `${action} ${target || ""}`,
      action: action || "click",
      target: target || "",
      value: value || undefined,
    };

    // Execute via pure Playwright with 3-level fallback (no Midscene AI vision)
    const result = await executeStep(step, 0, 30000);

    // Attach captured network/log data
    result.consoleLogs = capturer.getLogs();
    result.networkRequests = capturer.getNetwork();

    res.json({
      success: result.success,
      confidence: result.confidence,
      levelUsed: result.levelUsed,
      message: result.message,
      screenshotBefore: result.screenshotBefore,
      screenshotAfter: result.screenshotAfter,
      consoleLogs: {
        errors: (result.consoleLogs as any[])?.filter((l: any) => l.level === "error" || l.level === "exception").slice(0, 20) || [],
        warnings: (result.consoleLogs as any[])?.filter((l: any) => l.level === "warning").slice(0, 20) || [],
      },
      networkRequests: (result.networkRequests as any[])
        ?.filter((n: any) => n.type === "response")
        .slice(-30)
        .map((n: any) => ({
          method: n.method,
          url: n.url,
          status: n.status,
          timing: n.timing,
        })) || [],
      pageState: result.pageState,
      duration_ms: result.durationMs,
    });
  } catch (e: any) {
    res.status(500).json({ success: false, message: e.message });
  }
});

app.post("/agent/screenshot", async (req, res) => {
  try {
    await ensureBrowser();
    const full = req.body?.full === true;
    res.json({ success: true, screenshot: await smartScreenshot(full) });
  } catch (e: any) {
    res.status(500).json({ success: false, message: e.message });
  }
});

app.post("/agent/discover", async (req, res) => {
  try {
    const { page } = await ensureBrowser();
    const result = await discover(page);
    res.json({ success: true, ...result });
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
  console.log(`[AutoTest Executor] :${PORT} CDP+PurePlaywright+RunManager`);
});
