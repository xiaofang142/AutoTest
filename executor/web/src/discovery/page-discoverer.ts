import type { Page } from "playwright";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface DiscoveredElement {
  type: string;
  text: string;
  selectorHint: string;
  isVisible: boolean;
  region: string;
}

export interface PageDiscoveryResult {
  title: string;
  url: string;
  elements: DiscoveredElement[];
  regions: Record<string, number>;
  screenshot: string;
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/**
 * Build a compact CSS-selector-like hint from an element's tag, id and classes.
 */
function buildSelectorHint(tag: string, id: string, classes: string[]): string {
  let hint = tag.toLowerCase();
  if (id) hint += `#${id}`;
  const cls = classes.filter(Boolean).slice(0, 2);
  if (cls.length) hint += `.${cls.join(".")}`;
  return hint;
}

/**
 * Determine the semantic region an element belongs to by walking up ancestors
 * and checking tag names / ARIA role attributes.
 */
function detectRegion(el: Element): string {
  // Prefer explicit role
  const role = el.getAttribute("role");
  if (role && ["banner", "navigation", "main", "complementary", "contentinfo", "dialog"].includes(role)) {
    return role;
  }

  // Walk up to closest landmark ancestor
  const landmark = el.closest("header,nav,main,aside,footer,dialog,[role='banner'],[role='navigation'],[role='main'],[role='complementary'],[role='contentinfo'],[role='dialog']");
  if (landmark) {
    const tag = landmark.tagName.toLowerCase();
    if (tag === "header") return "banner";
    if (tag === "nav") return "navigation";
    if (tag === "main") return "main";
    if (tag === "aside") return "complementary";
    if (tag === "footer") return "contentinfo";
    if (tag === "dialog") return "dialog";
    const r = landmark.getAttribute("role");
    if (r) return r;
  }
  return "unknown";
}

/**
 * Check whether an element is visually visible on the page.
 */
function isVisible(el: Element): boolean {
  const h = el as HTMLElement;
  if (!h.offsetParent && !["HTML", "BODY"].includes(el.tagName)) return false;
  const style = getComputedStyle(h);
  if (style.display === "none") return false;
  if (style.visibility === "hidden") return false;
  const rect = h.getBoundingClientRect();
  if (rect.width === 0 && rect.height === 0) return false;
  return true;
}

// ---------------------------------------------------------------------------
// DOM extraction (runs inside the page)
// ---------------------------------------------------------------------------

function extractInteractiveElements(): DiscoveredElement[] {
  const raw: DiscoveredElement[] = [];

  // Buttons & button-likes
  const buttons = document.querySelectorAll(
    "button,input[type='button'],input[type='submit'],a[href]"
  );
  for (const el of buttons) {
    if (raw.length >= 50) break;
    const text =
      (el as HTMLElement).innerText?.trim() ||
      (el as HTMLInputElement).value?.trim() ||
      "";
    raw.push({
      type: el.tagName.toLowerCase(),
      text,
      selectorHint: buildSelectorHint(
        el.tagName,
        el.id,
        Array.from(el.classList)
      ),
      isVisible: isVisible(el),
      region: detectRegion(el),
    });
  }
  if (raw.length >= 50) return raw.slice(0, 50);

  // Inputs, selects, textareas (excluding hidden)
  const controls = document.querySelectorAll(
    "input:not([type='hidden']):not([type='button']):not([type='submit']),select,textarea"
  );
  for (const el of controls) {
    if (raw.length >= 50) break;
    const input = el as HTMLInputElement;
    const text = input.placeholder?.trim() || "";
    raw.push({
      type: el.tagName.toLowerCase(),
      text,
      selectorHint: buildSelectorHint(
        el.tagName,
        el.id,
        Array.from(el.classList)
      ),
      isVisible: isVisible(el),
      region: detectRegion(el),
    });
  }

  return raw.slice(0, 50);
}

function extractTextElements(): DiscoveredElement[] {
  const raw: DiscoveredElement[] = [];

  const headings = document.querySelectorAll("h1,h2,h3");
  for (const el of headings) {
    if (raw.length >= 80) break;
    const text = (el as HTMLElement).innerText?.trim();
    if (!text) continue;
    raw.push({
      type: el.tagName.toLowerCase(),
      text,
      selectorHint: buildSelectorHint(
        el.tagName,
        el.id,
        Array.from(el.classList)
      ),
      isVisible: isVisible(el),
      region: detectRegion(el),
    });
  }

  if (raw.length < 80) {
    const navItems = document.querySelectorAll("nav a,nav button,[role='navigation'] a,[role='navigation'] button,li a,li button");
    for (const el of navItems) {
      if (raw.length >= 80) break;
      const text = (el as HTMLElement).innerText?.trim();
      if (!text) continue;
      // Deduplicate by checking if identical text+region already exists
      if (raw.some((e) => e.text === text && e.region === detectRegion(el))) continue;
      raw.push({
        type: el.tagName.toLowerCase(),
        text,
        selectorHint: buildSelectorHint(
          el.tagName,
          el.id,
          Array.from(el.classList)
        ),
        isVisible: isVisible(el),
        region: detectRegion(el),
      });
    }
  }

  return raw.slice(0, 80);
}

function countRegions(elements: DiscoveredElement[]): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const el of elements) {
    counts[el.region] = (counts[el.region] || 0) + 1;
  }
  return counts;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Discover the structure and interactive elements of the current page.
 */
export async function discover(page: Page): Promise<PageDiscoveryResult> {
  const [title, elements, screenshot] = await Promise.all([
    page.title(),
    page.evaluate(() => {
      const interactive = extractInteractiveElements();
      const text = extractTextElements();
      const merged = [...interactive, ...text];
      return {
        elements: merged,
        regions: countRegions(merged),
      };
    }),
    page.screenshot({ fullPage: true, type: "png" }).catch(() => null),
  ]);

  return {
    title,
    url: page.url(),
    elements: elements.elements,
    regions: elements.regions,
    screenshot: screenshot
      ? `data:image/png;base64,${screenshot.toString("base64")}`
      : "",
  };
}
