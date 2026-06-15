/**
 * transitExport.js — backward-compatibility shim.
 *
 * The glyph-free LLM-optimized formatters now live in `astrologyExport.js`.
 * This file re-exports them under the original names so any existing imports
 * continue to work. New code should import directly from `astrologyExport.js`.
 *
 * NOTE: output is now glyph-free by design. See astrologyExport.js for the
 * formatting rules.
 */
export {
  formatTransitReportMarkdown as formatTransitExportMarkdown,
  formatTransitReportJSON as formatTransitExportJSON,
} from './astrologyExport.js';
