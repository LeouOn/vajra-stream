/**
 * Strip `<think>...</think>` blocks from LLM output.
 *
 * Some LLMs emit a `<think>` reasoning block before the final answer.
 * For user-facing display we hide that reasoning by default but keep it
 * available so it can be revealed via a collapsible `<details>` element.
 *
 * Handles three cases:
 *   1. A closed `<think>...</think>` block anywhere in the content.
 *   2. An unclosed `<think>...` block (streaming partial) — everything
 *      after the opening tag is treated as reasoning, nothing shown.
 *   3. No `<think>` tag at all — the content is returned unchanged.
 *
 * @param {string} content - Raw LLM output, possibly containing `<think>` blocks.
 * @returns {{ clean: string, reasoning: string | null }}
 *   `clean` is the content with all reasoning stripped (safe to render).
 *   `reasoning` is the extracted reasoning text, or `null` if none was found.
 */
export function stripThinking(content) {
  if (typeof content !== 'string') {
    return { clean: '', reasoning: null };
  }

  const match = content.match(/<think>([\s\S]*?)<\/think>/);
  if (match) {
    const reasoning = match[1].trim();
    const clean = content.replace(/<think>[\s\S]*?<\/think>/g, '').trim();
    return { clean, reasoning };
  }

  // Streaming partial: unclosed <think> tag
  const openMatch = content.match(/<think>([\s\S]*)/);
  if (openMatch) {
    return { clean: '', reasoning: openMatch[1].trim() };
  }

  return { clean: content, reasoning: null };
}