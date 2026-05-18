import type { Page } from "playwright";

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
  elements: any[];
  regions: Record<string, number>;
  screenshot: string;
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
    page.evaluate(function() {
      var raw = [];
      var els = document.querySelectorAll("button,input[type='button'],input[type='submit'],a[href]");
      for(var i=0;i<els.length&&raw.length<50;i++){
        var t=(els[i].innerText||els[i].value||"").trim();
        if(t) raw.push({type:els[i].tagName.toLowerCase(),text:t});
      }
      var headings = document.querySelectorAll("h1,h2,h3");
      for(var i=0;i<headings.length&&raw.length<80;i++){
        var t=(headings[i].innerText||"").trim();
        if(t) raw.push({type:headings[i].tagName.toLowerCase(),text:t});
      }
      return {elements:raw,regions:{}};
    }),
    page.screenshot({ type: "png" }).catch(() => null),
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
