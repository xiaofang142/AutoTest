import { chromium, Browser, BrowserContext, Page, CDPSession } from "playwright";
import type { PageStateSnapshot } from "./types.js";

let browser: Browser | null = null;
let context: BrowserContext | null = null;
let page: Page | null = null;
let cdpSession: CDPSession | null = null;

/**
 * Ensure a Chromium browser instance is running.
 * Lazily creates the browser, context, page, CDP session, and Midscene agent
 * on first call. Subsequent calls are idempotent.
 */
export async function ensureBrowser(
  viewport?: { width: number; height: number }
): Promise<{ browser: Browser; context: BrowserContext; page: Page; cdpSession: CDPSession }> {
  const needsRestart = !browser || !context || context.pages().length === 0;
  if (needsRestart) {
    if (browser) { try { await browser.close(); } catch {} }
    browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
    context = await browser.newContext({
      viewport: viewport || { width: 1920, height: 1080 },
    });
    page = await context.newPage();
    cdpSession = await context.newCDPSession(page);
    console.log("[Browser] Chromium + CDP ready");
  }
  return { browser: browser!, context: context!, page: page!, cdpSession: cdpSession! };
}

export function getPage(): Page | null {
  return page;
}

export function getCDP(): CDPSession | null {
  return cdpSession;
}

/**
 * Close the browser and reset all singleton references.
 */
export async function closeBrowser(): Promise<void> {
  if (browser) {
    try {
      await browser.close();
    } catch {
      // ignore close errors
    }
  }
  browser = null;
  context = null;
  page = null;
  cdpSession = null;
}

/**
 * Capture a snapshot of the current page state.
 */
export async function pageState(): Promise<PageStateSnapshot> {
  if (!page) {
    return { url: "", visibleTexts: [], alerts: [], perf: [] };
  }
  let perf: any[] = [];
  try {
    perf = await page.evaluate(() => {
      const entries = performance.getEntriesByType("resource");
      return entries.slice(-30).map((e: any) => ({
        name: e.name?.split("?")[0]?.slice(0, 100),
        duration: Math.round(e.duration),
        type: e.initiatorType,
      }));
    });
  } catch {
    // performance API may not be available
  }

  let visibleTexts: string[] = [];
  try {
    visibleTexts = await page.evaluate(() =>
      Array.from(
        document.querySelectorAll("h1,h2,h3,p,button,span,a,label,li")
      )
        .map((e) => (e as HTMLElement).innerText?.trim())
        .filter(Boolean)
        .slice(0, 80)
    );
  } catch {
    // cross-origin access may fail
  }

  let alerts: string[] = [];
  try {
    alerts = await page.evaluate(() =>
      Array.from(
        document.querySelectorAll(
          "[class*='error'],[class*='alert'],[role='alert']"
        )
      )
        .map((e) => (e as HTMLElement).innerText?.trim())
        .filter(Boolean)
    );
  } catch {
    // cross-origin access may fail
  }

  return {
    url: page.url(),
    visibleTexts,
    alerts,
    perf,
  };
}

/**
 * Take a screenshot and return it as a base64 data URI.
 */
export async function smartScreenshot(full: boolean = false): Promise<string> {
  if (!page) return "";
  try {
    const buf = await page.screenshot({ fullPage: full, type: "png" });
    return `data:image/png;base64,${buf.toString("base64")}`;
  } catch {
    return "";
  }
}
