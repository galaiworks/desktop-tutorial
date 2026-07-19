// 禁止ワードガード & 娯楽目的の但し書き（要件定義書 §10 / §13-3,7）
// 断定・不安を煽る・景表法に触れる表現を検出し、生成文の末尾に但し書きを自動付与する。

export const DISCLAIMER =
  "※本診断は娯楽・自己理解を目的としたものであり、結果を保証するものではありません。重要な意思決定は専門家にご相談ください。";

// 景表法・不安喚起・断定に触れやすい表現（部分一致）
export const BANNED_PATTERNS: RegExp[] = [
  /100\s*%/,
  /必ず(当たる|成功|うまく)/,
  /絶対に?(当たる|成功|別れ|結婚|不幸)/,
  /確実に/,
  /保証します/,
  /診断します(?!。)/, // 医療的断定の予防（緩め）
  /呪|祟|霊障/,
  /不幸になる/,
  /このままでは(危険|不幸|失敗)/,
];

export interface GuardResult {
  ok: boolean;
  violations: string[];
}

/** 生成文に禁止表現が含まれていないか検査 */
export function checkGuard(text: string): GuardResult {
  const violations: string[] = [];
  for (const re of BANNED_PATTERNS) {
    const m = re.exec(text);
    if (m) violations.push(m[0]);
  }
  return { ok: violations.length === 0, violations };
}

/** 但し書きが無ければ付与する */
export function ensureDisclaimer(text: string): string {
  if (text.includes("娯楽")) return text.trimEnd();
  return `${text.trimEnd()}\n\n${DISCLAIMER}`;
}
