// Strip leaked model reasoning (<think>...</think>) and stray reasoning tags before rendering.
export function cleanText(input) {
  if (input === null || input === undefined) return '';
  let s = String(input);
  // Text before the last closing tag is leaked chain-of-thought.
  const close = s.lastIndexOf('</think>');
  if (close !== -1) s = s.slice(close + '</think>'.length);
  // Unclosed opening tag: drop the remainder (it is reasoning).
  s = s.replace(/<think(?:ing)?>[\s\S]*$/i, '');
  s = s.replace(/<\/?(?:think|thinking|reasoning|scratchpad)>/gi, '');
  return s.trim();
}

export const hadReasoningLeak = (input) => /<\/?(?:think|thinking|reasoning|scratchpad)>/i.test(String(input ?? ''));