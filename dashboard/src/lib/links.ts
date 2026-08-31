/**
 * Build a URL for a static file served alongside the app.
 *
 * The site is deployed to a project subpath (`/AeroGuard/`), which Vite exposes
 * as BASE_URL. Vite does NOT rewrite plain `href` strings in JSX, so a literal
 * `/docs/x.md` resolves against the domain root and 404s on GitHub Pages.
 * Always route static links through here.
 *
 * @param path Path relative to the site root, with no leading slash.
 */
export function assetUrl(path: string): string {
  return `${import.meta.env.BASE_URL}${path.replace(/^\/+/, "")}`;
}

/** The polished research paper, bundled into the deploy from `paper/`. */
export const PAPER_HTML = assetUrl("paper/AeroGuard_Research_Paper.html");
export const PAPER_PDF = assetUrl("paper/AeroGuard_Research_Paper.pdf");

/** The internal, frozen end-to-end report the paper is synthesized from. */
export const FULL_REPORT = assetUrl("docs/AEROGUARD_FINAL_RESEARCH_REPORT.md");
export const PROVENANCE = assetUrl("docs/PROVENANCE.md");
