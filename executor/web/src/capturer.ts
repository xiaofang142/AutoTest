import type { CDPSession, Page } from "playwright";
import type { LogEntry, NetworkEntry } from "./types.js";

const MAX_BODY_SIZE = 100 * 1024; // 100 KB
const MAX_NETWORK_ENTRIES = 50;
const MAX_LOG_ENTRIES = 200;

/**
 * Captures browser console logs and network traffic via CDP.
 *
 * Uses the CDP Fetch API (not Network events) to capture full request/response
 * bodies with 100 KB truncation. A single Fetch.enable call registers handlers
 * for both Request and Response stages, dispatched by params.requestStage.
 */
export class Capturer {
  private network: NetworkEntry[] = [];
  private logs: LogEntry[] = [];
  private cdp: CDPSession | null = null;
  private page: Page | null = null;
  private attached = false;
  private boundHandler: ((params: any) => void) | null = null;

  /**
   * Attach to an active CDP session and page.
   * Idempotent — safe to call multiple times.
   */
  async attach(cdpSession: CDPSession, pageInstance: Page): Promise<void> {
    if (this.attached) return;
    this.cdp = cdpSession;
    this.page = pageInstance;

    // Single Fetch.enable call with both request stages
    await cdpSession.send("Fetch.enable", {
      patterns: [
        { urlPattern: "*", requestStage: "Request" },
        { urlPattern: "*", requestStage: "Response" },
      ],
    });

    this.boundHandler = this.onRequestPaused.bind(this);
    cdpSession.on("Fetch.requestPaused", this.boundHandler);

    pageInstance.on("console", this.onConsoleMessage);
    this.attached = true;
  }

  /**
   * Detach from CDP session and page, cleaning up all listeners.
   */
  async detach(): Promise<void> {
    if (!this.attached) return;
    try {
      await this.cdp?.send("Fetch.disable");
    } catch {
      // session may already be closed
    }
    if (this.boundHandler && this.cdp) {
      this.cdp.removeListener("Fetch.requestPaused", this.boundHandler);
    }
    if (this.page) {
      this.page.removeListener("console", this.onConsoleMessage);
    }
    this.attached = false;
    this.cdp = null;
    this.page = null;
    this.boundHandler = null;
    this.clear();
  }

  /**
   * Clear all captured data between steps.
   */
  clear(): void {
    this.network = [];
    this.logs = [];
  }

  getNetwork(): NetworkEntry[] {
    return this.network;
  }

  getLogs(): LogEntry[] {
    return this.logs;
  }

  getErrors(): LogEntry[] {
    return this.logs.filter((l) => l.level === "error" || l.level === "exception");
  }

  getWarnings(): LogEntry[] {
    return this.logs.filter((l) => l.level === "warning");
  }

  // ---- Private handlers ----

  private readonly onConsoleMessage = (msg: any): void => {
    if (this.logs.length >= MAX_LOG_ENTRIES) return;
    this.logs.push({
      level: msg.type(),
      message: msg.text(),
      location: msg.location()?.url || "",
      timestamp: Date.now(),
    });
  };

  private async onRequestPaused(params: any): Promise<void> {
    const { requestId, request, requestStage, responseStatusCode, responseHeaders } = params;

    if (requestStage === "Request") {
      if (this.network.length < MAX_NETWORK_ENTRIES) {
        this.network.push({
          type: "request",
          method: request?.method || "GET",
          url: request?.url || "",
          headers: request?.headers || {},
          timestamp: Date.now(),
        });
      }
      await this.cdp!.send("Fetch.continueRequest", { requestId });
    } else if (requestStage === "Response") {
      let body = "";
      try {
        const resp = await this.cdp!.send("Fetch.getResponseBody", { requestId });
        body = resp.base64Encoded
          ? Buffer.from(resp.body, "base64").toString("utf-8").slice(0, MAX_BODY_SIZE)
          : resp.body.slice(0, MAX_BODY_SIZE);
      } catch {
        // body not available (redirect, opaque, etc.)
      }

      if (this.network.length < MAX_NETWORK_ENTRIES) {
        this.network.push({
          type: "response",
          method: request?.method || "GET",
          url: request?.url || "",
          status: responseStatusCode || 0,
          headers: responseHeaders
            ? (responseHeaders as Array<{ name: string; value: string }>).reduce(
                (acc: Record<string, string>, h) => {
                  acc[h.name] = h.value;
                  return acc;
                },
                {}
              )
            : undefined,
          body: body || undefined,
          timestamp: Date.now(),
        });
      }

      await this.cdp!.send("Fetch.continueResponse", { requestId });
    }
  }
}
