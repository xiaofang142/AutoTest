import type { RunState, RunEntry, RunEvent, ExecutableCase, RunStatus } from "./types.js";
import { ensureBrowser } from "./browser.js";
import type { Capturer } from "./capturer.js";
import type { Reporter } from "./reporter.js";
import { executeStep } from "./step-executor.js";

const DEFAULT_STEP_TIMEOUT_MS = 30_000;
const DEFAULT_RUN_TIMEOUT_MS = 300_000;

/**
 * Orchestrates multi-step test runs.
 *
 * Manages the full lifecycle: create → start → (per-case/step execution) →
 * completed/cancelled/error. Pushes progress events via Reporter and uses
 * Capturer for per-step network/log capture.
 */
export class RunManager {
  private runs: Map<string, RunState> = new Map();
  private capturer: Capturer;
  private reporter: Reporter;
  private timers: Map<string, NodeJS.Timeout> = new Map();

  constructor(capturer: Capturer, reporter: Reporter) {
    this.capturer = capturer;
    this.reporter = reporter;
  }

  /**
   * Create a new run with the given entry configuration.
   */
  create(runId: string, entry: RunEntry): RunState {
    const totalSteps = entry.cases.reduce(
      (sum, c) => sum + c.steps.length,
      0
    );
    const state: RunState = {
      runId,
      entry,
      status: "pending",
      currentCaseIndex: -1,
      currentStepIndex: -1,
      results: [],
      errors: [],
      stepTimeoutMs: DEFAULT_STEP_TIMEOUT_MS,
      runTimeoutMs: DEFAULT_RUN_TIMEOUT_MS,
      continueOnFailure: false,
      totalSteps,
    };
    this.runs.set(runId, state);
    return state;
  }

  /**
   * Start execution of a previously created run.
   *
   * Flow: ensureBrowser → navigate to entry.url → for each case/step:
   *   capturer.clear() → executeStep() → attach captured data → push event
   */
  async start(runId: string): Promise<void> {
    const state = this.runs.get(runId);
    if (!state) throw new Error(`Run not found: ${runId}`);
    if (state.status !== "pending") throw new Error(`Run ${runId} is already ${state.status}`);

    state.status = "running";
    state.startedAt = Date.now();

    const timer = setTimeout(() => {
      this.cancel(runId);
    }, state.runTimeoutMs);
    this.timers.set(runId, timer);

    this.emit(runId, {
      type: "run_started",
      runId,
      timestamp: Date.now(),
      data: { totalSteps: state.totalSteps, entryUrl: state.entry.url },
    });

    try {
      const { page, cdpSession } = await ensureBrowser();
      await this.capturer.attach(cdpSession, page);

      await page.goto(state.entry.url, {
        waitUntil: "networkidle",
        timeout: 30_000,
      });

      this.emit(runId, {
        type: "progress",
        runId,
        timestamp: Date.now(),
        data: { message: `Navigated to ${state.entry.url}` },
      });

      for (let ci = 0; ci < state.entry.cases.length; ci++) {
        if ((state.status as RunStatus) === "cancelled") break;

        const testCase: ExecutableCase = state.entry.cases[ci];
        state.currentCaseIndex = ci;

        this.emit(runId, {
          type: "case_started",
          runId,
          timestamp: Date.now(),
          data: { caseName: testCase.name, caseIndex: ci },
        });

        // Per-case navigation
        if (testCase.url) {
          await page.goto(testCase.url, {
            waitUntil: "networkidle",
            timeout: 30_000,
          });
        }

        for (let si = 0; si < testCase.steps.length; si++) {
          if ((state.status as RunStatus) === "cancelled") break;

          state.currentStepIndex = si;
          const step = testCase.steps[si];

          // Reset capture buffers for this step
          this.capturer.clear();

          // Execute step
          const stepTimeout = step.timeoutMs || state.stepTimeoutMs;
          const result = await executeStep(step, si, stepTimeout);

          // Attach captured data to result
          result.consoleLogs = this.capturer.getLogs();
          result.networkRequests = this.capturer.getNetwork();

          state.results.push(result);

          this.emit(runId, {
            type: "step_completed",
            runId,
            timestamp: Date.now(),
            data: {
              stepIndex: si,
              stepName: step.name || `${step.action} ${step.target || ""}`,
              success: result.success,
              confidence: result.confidence,
              caseName: testCase.name,
              caseIndex: ci,
              durationMs: result.durationMs,
            },
          });

          // Stop on failure unless continueOnFailure is set
          if (!result.success && !state.continueOnFailure) {
            state.errors.push(
              `Step ${si} ("${step.name || step.action}") in case "${testCase.name}": ${result.message}`
            );
            break;
          }
        }

        this.emit(runId, {
          type: "case_completed",
          runId,
          timestamp: Date.now(),
          data: {
            caseName: testCase.name,
            caseIndex: ci,
            stepCount: testCase.steps.length,
          },
        });
      }

      if ((state.status as RunStatus) !== "cancelled") {
        state.status = "completed";
        state.completedAt = Date.now();
        this.emit(runId, {
          type: "run_completed",
          runId,
          timestamp: Date.now(),
          data: { totalSteps: state.totalSteps, resultCount: state.results.length },
        });
      }
    } catch (e: any) {
      state.status = "error";
      state.errors.push(e.message);
      state.completedAt = Date.now();
      this.emit(runId, {
        type: "run_error",
        runId,
        timestamp: Date.now(),
        data: { error: e.message },
      });
    } finally {
      const t = this.timers.get(runId);
      if (t) {
        clearTimeout(t);
        this.timers.delete(runId);
      }
    }
  }

  /**
   * Cancel a running run.
   */
  cancel(runId: string): void {
    const state = this.runs.get(runId);
    if (!state || state.status === "completed" || state.status === "cancelled" || state.status === "error") {
      return;
    }
    state.status = "cancelled";
    state.completedAt = Date.now();
    this.emit(runId, {
      type: "run_cancelled",
      runId,
      timestamp: Date.now(),
    });
  }

  /**
   * Get the current progress of a run.
   */
  getProgress(runId: string): {
    runId: string;
    status: string;
    currentCaseIndex: number;
    currentStepIndex: number;
    completedSteps: number;
    totalSteps: number;
    progress: number;
    errors: string[];
  } | null {
    const state = this.runs.get(runId);
    if (!state) return null;
    const completedSteps = state.results.length;
    return {
      runId,
      status: state.status,
      currentCaseIndex: state.currentCaseIndex,
      currentStepIndex: state.currentStepIndex,
      completedSteps,
      totalSteps: state.totalSteps,
      progress: state.totalSteps > 0 ? Math.round((completedSteps / state.totalSteps) * 100) : 0,
      errors: state.errors,
    };
  }

  /**
   * Get the full state of a run (including all results).
   */
  getStatus(runId: string): RunState | null {
    return this.runs.get(runId) || null;
  }

  private emit(runId: string, event: RunEvent): void {
    this.reporter.push(runId, event);
  }
}
