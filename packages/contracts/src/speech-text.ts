const SENTENCE_END = /[.!?…。！？]$/u;

/**
 * The words of a Markdown reply that a listener needs. Code blocks, tables, images and addresses are
 * not read; a link reads as its text, and a mention as its name. Each line ends as a sentence, so a
 * list item does not run into the next one. Desktop and mobile read replies aloud with it.
 */
export function speechTextFromMarkdown(markdown: string): string {
  const prose = markdown.replace(/```[\s\S]*?(```|$)/gu, "\n").replace(/~~~[\s\S]*?(~~~|$)/gu, "\n");
  const lines = withoutReasoning(prose)
    .replace(/<[^>\n]+>/gu, " ")
    .replace(/\btokens?\s*\/\s*(?:seconds?|secs?|s)\b/giu, "tokens per second")
    .replace(/!\[[^\]]*\]\([^)]*\)/gu, " ")
    .replace(/\[([^\]]+)\]\([^)]*\)/gu, "$1")
    .replace(/https?:\/\/\S+/gu, " ")
    .split("\n");
  const sentences: string[] = [];
  for (const raw of lines) {
    // A table row and its divider are not read.
    if (/^\s*\|/u.test(raw)) continue;
    const line = raw
      .replace(/^\s{0,3}(#{1,6}|>+|[-*+]|\d+[.)])\s+/u, "")
      .replace(/^\s*[-*_]{3,}\s*$/u, "")
      .replace(/`([^`]*)`/gu, "$1")
      .replace(/(^|[\s(])@(?=[\p{L}\p{N}])/gu, "$1")
      .replace(/(\*\*|__|~~)(.+?)\1/gu, "$2")
      .replace(/(^|[^\p{L}\p{N}])[*_](\S(?:.*?\S)?)[*_](?=$|[^\p{L}\p{N}])/gu, "$1$2")
      .replace(/\s+/gu, " ")
      .trim();
    if (!line) continue;
    sentences.push(SENTENCE_END.test(line) || /[:;,]$/u.test(line) ? line : `${line}.`);
  }
  return sentences.join(" ");
}

/** Keep nested and unfinished reasoning blocks out of spoken output. */
function withoutReasoning(text: string): string {
  const tags = /<\/?(?:think|thinking|analysis|reasoning)\b[^>]*>/giu;
  let depth = 0;
  let offset = 0;
  let spoken = "";
  for (const tag of text.matchAll(tags)) {
    if (depth === 0) spoken += text.slice(offset, tag.index);
    depth = tag[0].startsWith("</") ? Math.max(0, depth - 1) : depth + 1;
    offset = tag.index + tag[0].length;
    if (depth === 0) spoken += " ";
  }
  return depth === 0 ? spoken + text.slice(offset) : spoken;
}
