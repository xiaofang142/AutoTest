// ============================================================
// AutoTest Executor — Shared Type Definitions
// ============================================================

/**
 * A single browser console log entry captured during step execution.
 */
export interface LogEntry {
  level: string;
  message: string;
  location: string;
  timestamp: number;
}

/**
 * A single network request/response entry captured via CDP Fetch API.
 */
export interface NetworkEntry {
  type: "request" | "response";
  method: string;
  url: string;
  status?: number;
  mime?: string;
  headers?: Record<string, string>;
  /** Truncated response body (max 100 KB) */
  body?: string;
  timing?: Record<string, number> | null;
  timestamp: number;
}

/**
 * Snapshot of the page state at a point in time.
 */
export interface PageStateSnapshot {
  url: string;
  visibleTexts: string[];
  alerts: string[];
  perf: any[];
}

/**
 * A single executable test step.
 */
export interface ExecutableStep {
  name: string;
  action: string;
  target?: string;
  value?: string;
  timeoutMs?: number;
}

/**
 * A test case consisting of one or more steps.
 */
export interface ExecutableCase {
  name: string;
  /** Optional per-case navigation URL (overrides entry url) */
  url?: string;
  steps: ExecutableStep[];
}

/**
 * Entry point definition for a multi-step run.
 */
export interface RunEntry {
  /** Initial navigation URL */
  url: string;
  /** Ordered test cases */
  cases: ExecutableCase[];
}

/**
 * Result produced by executing a single step.
 */
export interface StepResult {
  stepIndex: number;
  stepName: string;
  success: boolean;
  confidence: number;
  message: string;
  screenshotBefore: string;
  screenshotAfter: string;
  consoleLogs: LogEntry[];
  networkRequests: NetworkEntry[];
  pageState: PageStateSnapshot;
  durationMs: number;
  /** Which fallback level succeeded (0-3, -1 if none) */
  levelUsed: number;
}

/**
 * Current state of a multi-step run.
 */
export interface RunState {
  runId: string;
  entry: RunEntry;
  status: RunStatus;
  currentCaseIndex: number;
  currentStepIndex: number;
  results: StepResult[];
  errors: string[];
  startedAt?: number;
  completedAt?: number;
  /** Per-step timeout in milliseconds (default 30000) */
  stepTimeoutMs: number;
  /** Global run timeout in milliseconds (default 300000) */
  runTimeoutMs: number;
  /** Whether to continue execution after a step failure */
  continueOnFailure: boolean;
  totalSteps: number;
}

export type RunStatus =
  | "pending"
  | "running"
  | "completed"
  | "cancelled"
  | "error";

export type RunEventType =
  | "run_started"
  | "case_started"
  | "step_completed"
  | "case_completed"
  | "run_completed"
  | "run_cancelled"
  | "run_error"
  | "progress";

/**
 * Event payload pushed to WebSocket subscribers.
 */
export interface RunEvent {
  type: RunEventType;
  runId: string;
  timestamp: number;
  data?: Record<string, unknown>;
}
