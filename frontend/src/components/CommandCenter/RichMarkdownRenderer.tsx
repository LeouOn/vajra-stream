/**
 * RichMarkdownRenderer — minimal markdown-to-JSX renderer for chat messages.
 *
 * Extracted verbatim from `components/UI/CommandCenter.jsx` (lines 191-365) as
 * part of the CommandCenter decomposition (Task 3.3). Pure presentational
 * component: props-only, zero coupling to CommandCenter state. Supports
 * headings (h2-h4), blockquotes, ordered/unordered lists, fenced code blocks,
 * and inline bold / italics / inline-code styling. The two nested helpers
 * (`flushList`, `renderInlineStyles`) travel with the component unchanged.
 *
 * @component
 * @param {Object} props
 * @param {string} props.content - raw markdown text to render.
 */
import React from 'react';
import { stripThinking } from '../../utils/thinkStrip';

export const RichMarkdownRenderer = ({ content }) => {
  if (!content) return null;

  const { clean, reasoning } = stripThinking(content);
  if (!clean && !reasoning) return null;

  const lines = clean.split('\n');
  const elements = [];
  let currentList = null; // { type: 'ul' | 'ol', items: [] }
  let inCodeBlock = false;
  let codeBlockLines = [];
  let codeBlockLang = '';

  const flushList = (key) => {
    if (currentList) {
      const Tag = currentList.type;
      const listKey = `list-${key}`;
      elements.push(
        <Tag key={listKey} className={currentList.type === 'ul' ? 'list-disc pl-5 space-y-1.5 my-2.5' : 'list-decimal pl-5 space-y-1.5 my-2.5'}>
          {currentList.items.map((item, idx) => (
            <li key={idx} className="text-gray-200 text-sm leading-relaxed">
              {renderInlineStyles(item)}
            </li>
          ))}
        </Tag>
      );
      currentList = null;
    }
  };

  const renderInlineStyles = (lineText) => {
    let parts = [lineText];

    // Bold: **text**
    parts = parts.flatMap(part => {
      if (typeof part !== 'string') return part;
      const subparts = part.split('**');
      return subparts.map((chunk, idx) => {
        if (idx % 2 === 1) {
          return <strong key={idx} className="text-purple-300 font-bold">{chunk}</strong>;
        }
        return chunk;
      });
    });

    // Inline code: `code`
    parts = parts.flatMap(part => {
      if (typeof part !== 'string') return part;
      const subparts = part.split('`');
      return subparts.map((chunk, idx) => {
        if (idx % 2 === 1) {
          return <code key={idx} className="bg-black/60 border border-white/10 px-1.5 py-0.5 rounded text-cyan-300 font-mono text-xs break-all [word-break:break-all] max-w-[200px] inline-block overflow-hidden text-ellipsis align-bottom">{chunk}</code>;
        }
        return chunk;
      });
    });

    // Italics: *text*
    parts = parts.flatMap(part => {
      if (typeof part !== 'string') return part;
      const subparts = part.split('*');
      if (subparts.length > 1 && subparts.length % 2 === 1) {
        return subparts.map((chunk, idx) => {
          if (idx % 2 === 1) {
            return <em key={idx} className="text-gray-300 italic">{chunk}</em>;
          }
          return chunk;
        });
      }
      return part;
    });

    return parts;
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Handle code block
    if (line.trim().startsWith('```')) {
      if (inCodeBlock) {
        const blockKey = `code-${elements.length}-${i}`;
        elements.push(
          <pre key={blockKey} className="bg-black/80 border border-white/10 p-3 rounded-lg font-mono text-xs text-cyan-400 overflow-x-auto my-3 leading-normal">
            <code>{codeBlockLines.join('\n')}</code>
          </pre>
        );
        inCodeBlock = false;
        codeBlockLines = [];
      } else {
        flushList(i);
        inCodeBlock = true;
        codeBlockLang = line.replace('```', '').trim();
      }
      continue;
    }

    if (inCodeBlock) {
      codeBlockLines.push(line);
      continue;
    }

    // Handle headers
    if (line.startsWith('### ')) {
      flushList(i);
      const text = line.substring(4);
      elements.push(<h4 key={`h4-${i}`} className="text-sm font-bold text-white tracking-wide mt-3 mb-2">{renderInlineStyles(text)}</h4>);
      continue;
    }
    if (line.startsWith('## ')) {
      flushList(i);
      const text = line.substring(3);
      elements.push(<h3 key={`h3-${i}`} className="text-base font-bold text-white tracking-wider mt-4 mb-2">{renderInlineStyles(text)}</h3>);
      continue;
    }
    if (line.startsWith('# ')) {
      flushList(i);
      const text = line.substring(2);
      elements.push(<h2 key={`h2-${i}`} className="text-lg font-bold text-white tracking-widest mt-4 mb-2">{renderInlineStyles(text)}</h2>);
      continue;
    }

    // Handle blockquotes
    if (line.trim().startsWith('> ')) {
      flushList(i);
      const text = line.trim().substring(2);
      elements.push(
        <blockquote key={`bq-${i}`} className="border-l-4 border-purple-500/60 bg-purple-950/20 px-3 py-2 my-2 rounded-r-lg text-xs italic text-purple-200">
          {renderInlineStyles(text)}
        </blockquote>
      );
      continue;
    }

    // Handle unordered lists
    if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
      const text = line.trim().substring(2);
      if (!currentList || currentList.type !== 'ul') {
        flushList(i);
        currentList = { type: 'ul', items: [text] };
      } else {
        currentList.items.push(text);
      }
      continue;
    }

    // Handle ordered lists
    const olMatch = line.trim().match(/^(\d+)\.\s(.*)/);
    if (olMatch) {
      const text = olMatch[2];
      if (!currentList || currentList.type !== 'ol') {
        flushList(i);
        currentList = { type: 'ol', items: [text] };
      } else {
        currentList.items.push(text);
      }
      continue;
    }

    // Empty lines
    if (!line.trim()) {
      flushList(i);
      continue;
    }

    // Regular paragraph
    flushList(i);
    elements.push(
      <p key={`p-${i}`} className="mb-2 last:mb-0 text-gray-100 text-sm leading-relaxed">
        {renderInlineStyles(line)}
      </p>
    );
  }

  flushList(lines.length);

  return (
    <>
      {elements}
      {reasoning && (
        <details className="text-xs opacity-60 mt-2">
          <summary>💭 Reasoning</summary>
          <div className="mt-1 whitespace-pre-wrap">{reasoning}</div>
        </details>
      )}
    </>
  );
};
