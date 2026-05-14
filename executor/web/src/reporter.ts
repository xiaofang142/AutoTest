import type { Server as HttpServer } from "http";
import { WebSocketServer, WebSocket } from "ws";
import type { RunEvent } from "./types.js";

const WS_PATH_PATTERN = /^\/ws\/run\/([^/]+)/;

/**
 * WebSocket-based progress reporter for multi-step test runs.
 *
 * Clients connect to /ws/run/{run_id} and receive RunEvent JSON messages
 * as the run progresses. Multiple clients can subscribe to the same run.
 */
export class Reporter {
  private wss: WebSocketServer;
  private clients: Map<string, Set<WebSocket>> = new Map();

  constructor(server: HttpServer) {
    this.wss = new WebSocketServer({ server });

    this.wss.on("connection", (ws: WebSocket, req) => {
      const url = req.url || "";
      const match = url.match(WS_PATH_PATTERN);

      if (!match) {
        ws.close(4000, "Invalid path — expected /ws/run/{run_id}");
        return;
      }

      const runId = match[1];

      // Register client for this run
      let clientSet = this.clients.get(runId);
      if (!clientSet) {
        clientSet = new Set();
        this.clients.set(runId, clientSet);
      }
      clientSet.add(ws);

      // Clean up on disconnect
      ws.on("close", () => {
        const set = this.clients.get(runId);
        if (!set) return;
        set.delete(ws);
        if (set.size === 0) {
          this.clients.delete(runId);
        }
      });

      ws.on("error", () => {
        // handled by close event
      });
    });
  }

  /**
   * Push a RunEvent to all WebSocket clients subscribed to the given run.
   */
  push(runId: string, event: RunEvent): void {
    const clientSet = this.clients.get(runId);
    if (!clientSet || clientSet.size === 0) return;

    const data = JSON.stringify(event);
    for (const ws of clientSet) {
      if (ws.readyState === WebSocket.OPEN) {
        try {
          ws.send(data);
        } catch {
          // client may have disconnected between iteration and send
          clientSet.delete(ws);
        }
      }
    }
  }

  /**
   * Close the WebSocket server and all connections.
   */
  close(): void {
    for (const [, clientSet] of this.clients) {
      for (const ws of clientSet) {
        try {
          ws.close(1001, "Server shutting down");
        } catch {
          // ignore
        }
      }
    }
    this.clients.clear();
    this.wss.close();
  }
}
