import type { Page } from "playwright";
import type { ExecutableStep, StepResult } from "./types.js";
import { getPage, pageState, smartScreenshot } from "./browser.js";

/**
 * Execute a single test step with Playwright native locators (no AI vision).
 *
 * Level 0 – Playwright locator API (getByRole, getByText, locator, getByPlaceholder)
 * Level 1 – DOM querySelectorAll text matching via page.evaluate
 * Level 2 – XPath evaluation via document.evaluate
 *
 * Pure DOM-based execution — no screenshots sent to LLM.
 * Saves OCR + DOM text for server-side analysis.
 */
export async function executeStep(
  step: ExecutableStep,
  stepIndex: number,
  timeoutMs: number = 30000
): Promise<StepResult> {
  const page = getPage();
  const stepStart = Date.now();

  const stepName = step.name || `${step.action} ${step.target || ""}`;
  const before = await smartScreenshot(false);

  let success = false;
  let message = "";
  let levelUsed = -1;

  // -- Level 0: Playwright locator API --
  if (!success && page) {
    try {
      await executePlaywrightLocator(page, step, timeoutMs);
      success = true;
      message = `[Level 0] Playwright locator: ${step.action} ${step.target || ""}`;
      levelUsed = 0;
    } catch (e: any) {
      message = `Level 0 failed: ${e.message}`;
    }
  }

  // -- Level 1: DOM querySelectorAll --
  if (!success && page) {
    try {
      await executeDomLevel(page, step, timeoutMs);
      success = true;
      message = `[Level 1] DOM query: ${step.action} ${step.target || ""}`;
      levelUsed = 1;
    } catch (e: any) {
      message = `Level 1 failed: ${e.message}`;
    }
  }

  // -- Level 2: XPath --
  if (!success && page) {
    try {
      await executeXPathLevel(page, step, timeoutMs);
      success = true;
      message = `[Level 2] XPath: ${step.action} ${step.target || ""}`;
      levelUsed = 2;
    } catch (e: any) {
      message = `Level 2 failed: ${e.message}`;
    }
  }

  const after = await smartScreenshot(success);
  const state = await pageState();
  const confidence = success ? [0.95, 0.85, 0.7][levelUsed] || 0 : 0;

  return {
    stepIndex,
    stepName,
    success,
    confidence,
    message,
    screenshotBefore: before,
    screenshotAfter: after,
    consoleLogs: [],
    networkRequests: [],
    pageState: state,
    durationMs: Date.now() - stepStart,
    levelUsed,
  };
}

// ---- Helpers ----

function buildInstruction(step: ExecutableStep): string {
  let inst = `${step.action} ${step.target || ""}`;
  if (step.value) inst += ` with value "${step.value}"`;
  return inst;
}

async function executePlaywrightLocator(
  page: Page,
  step: ExecutableStep,
  timeoutMs: number
): Promise<void> {
  const { action, target, value } = step;
  const t = target || "";

  if (action === "click" || action === "tap") {
    // Try role-based first, then text, then CSS
    try {
      await page.getByRole("button", { name: t }).click({ timeout: Math.min(timeoutMs, 5000) });
      return;
    } catch { /* fall through */ }
    try {
      await page.getByRole("link", { name: t }).click({ timeout: Math.min(timeoutMs, 5000) });
      return;
    } catch { /* fall through */ }
    try {
      await page.getByText(t, { exact: false }).first().click({ timeout: Math.min(timeoutMs, 5000) });
      return;
    } catch { /* fall through */ }
    try {
      await page.locator(t).click({ timeout: Math.min(timeoutMs, 5000) });
      return;
    } catch { /* fall through */ }
    throw new Error(`Playwright locator could not find click target: ${t}`);
  }

  if (action === "type" || action === "fill") {
    try {
      await page.getByPlaceholder(t).fill(value || "", { timeout: Math.min(timeoutMs, 5000) });
      return;
    } catch { /* fall through */ }
    try {
      await page.getByLabel(t).fill(value || "", { timeout: Math.min(timeoutMs, 5000) });
      return;
    } catch { /* fall through */ }
    try {
      await page.locator(t).fill(value || "", { timeout: Math.min(timeoutMs, 5000) });
      return;
    } catch { /* fall through */ }
    throw new Error(`Playwright locator could not find input: ${t}`);
  }

  if (action === "select") {
    try {
      await page.locator(t).selectOption(value || "", { timeout: Math.min(timeoutMs, 5000) });
      return;
    } catch { /* fall through */ }
    throw new Error(`Playwright locator could not find select: ${t}`);
  }

  if (action === "hover") {
    try {
      await page.locator(t).hover({ timeout: Math.min(timeoutMs, 5000) });
      return;
    } catch { /* fall through */ }
    throw new Error(`Playwright locator could not find hover target: ${t}`);
  }

  if (action === "navigate") {
    await page.goto(t, { waitUntil: "networkidle", timeout: timeoutMs });
    return;
  }

  // Generic: try as CSS selector
  try {
    await page.locator(t).click({ timeout: Math.min(timeoutMs, 5000) });
  } catch {
    throw new Error(`Playwright locator: unsupported action "${action}" or element not found`);
  }
}

async function executeDomLevel(
  page: Page,
  step: ExecutableStep,
  timeoutMs: number
): Promise<void> {
  const { action, target, value } = step;
  const t = target || "";

  const selectors = [
    "button", "a", "input", "span",
    "[role='button']", "[role='link']", "[role='option']",
    "select", "textarea", "label",
  ];

  if (action === "click" || action === "tap") {
    const found = await page.evaluate(
      ({ sel, text }: { sel: string[]; text: string }) => {
        for (const el of Array.from(document.querySelectorAll(sel.join(",")))) {
          const h = el as HTMLElement;
          if (
            h.innerText?.includes(text) ||
            (el as HTMLInputElement).placeholder?.includes(text) ||
            (el as HTMLInputElement).title?.includes(text) ||
            h.getAttribute("aria-label")?.includes(text)
          ) {
            h.click();
            return true;
          }
        }
        return false;
      },
      { sel: selectors, text: t }
    );
    if (!found) throw new Error(`DOM level: element with text "${t}" not found`);
  } else if (action === "type" || action === "fill") {
    const found = await page.evaluate(
      ({ text, val, sel }: { text: string; val: string; sel: string[] }) => {
        for (const el of Array.from(document.querySelectorAll(sel.join(",")))) {
          const input = el as HTMLInputElement;
          if (
            input.placeholder?.includes(text) ||
            input.title?.includes(text) ||
            input.getAttribute("aria-label")?.includes(text) ||
            input.name?.includes(text)
          ) {
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
              window.HTMLInputElement.prototype,
              "value"
            )?.set;
            nativeInputValueSetter?.call(input, val);
            input.dispatchEvent(new Event("input", { bubbles: true }));
            input.dispatchEvent(new Event("change", { bubbles: true }));
            return true;
          }
        }
        return false;
      },
      { text: t, val: value || "", sel: selectors }
    );
    if (!found) throw new Error(`DOM level: input with text "${t}" not found`);
  } else {
    throw new Error(`DOM level: unsupported action "${action}"`);
  }

  await page.waitForTimeout(300);
}

async function executeXPathLevel(
  page: Page,
  step: ExecutableStep,
  timeoutMs: number
): Promise<void> {
  const { action, target, value } = step;
  const t = target || "";
  let xpath = t;

  // If the target doesn't look like an XPath expression, try to build one
  if (!t.startsWith("/") && !t.startsWith("(") && !t.startsWith(".")) {
    const escaped = t.replace(/'/g, "\\'");
    xpath = `//*[contains(text(), '${escaped}')]`;
  }

  if (action === "click" || action === "tap") {
    const found = await page.evaluate((xp: string) => {
      const result = document.evaluate(
        xp,
        document,
        null,
        XPathResult.FIRST_ORDERED_NODE_TYPE,
        null
      );
      const node = result.singleNodeValue;
      if (node) {
        (node as HTMLElement).click();
        return true;
      }
      return false;
    }, xpath);
    if (!found) throw new Error(`XPath level: element not found: ${xpath}`);
  } else if (action === "type" || action === "fill") {
    const found = await page.evaluate(
      ({ xp, val }: { xp: string; val: string }) => {
        const result = document.evaluate(
          xp,
          document,
          null,
          XPathResult.FIRST_ORDERED_NODE_TYPE,
          null
        );
        const node = result.singleNodeValue as HTMLInputElement;
        if (node) {
          const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype,
            "value"
          )?.set;
          nativeInputValueSetter?.call(node, val);
          node.dispatchEvent(new Event("input", { bubbles: true }));
          node.dispatchEvent(new Event("change", { bubbles: true }));
          return true;
        }
        return false;
      },
      { xp: xpath, val: value || "" }
    );
    if (!found) throw new Error(`XPath level: input not found: ${xpath}`);
  } else {
    throw new Error(`XPath level: unsupported action "${action}"`);
  }

  await page.waitForTimeout(300);
}
