// 診断コード（結果の共有・引き継ぎ）— 要件定義書 §5.7
// 相性診断とLINE誘導の両方で同じ書式を使う。
// 書式: N1-{lifePath}-{E}-{A}-{C}-{N}-{O}   例) N1-11-72-40-85-30-66
// URLにもそのまま載せられ、人が目視・コピペできる短さを優先（Base64より運用しやすい）。
import type { Big5Key, Big5Scores, LifePath } from "./types";

export const CODE_VERSION = "N1";

const VALID_LIFE_PATHS = new Set<number>([1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 22, 33]);
const KEYS: Big5Key[] = ["E", "A", "C", "N", "O"];

export interface SharePayload {
  life_path: LifePath;
  big5: Big5Scores;
}

/** 全角英数・全角ハイフン・空白などを吸収して正規化する（コピペ耐性） */
export function normalizeCode(input: string): string {
  return input
    .replace(/[Ａ-Ｚａ-ｚ０-９]/g, (c) =>
      String.fromCharCode(c.charCodeAt(0) - 0xfee0)
    )
    .replace(/[－−—–ー]/g, "-")
    .replace(/\s/g, "")
    .trim()
    .toUpperCase();
}

/** 診断結果を共有コードへ */
export function encodeCode(payload: SharePayload): string {
  const scores = KEYS.map((k) => clampScore(payload.big5[k]));
  return [CODE_VERSION, payload.life_path, ...scores].join("-");
}

/** 共有コードを診断結果へ。不正なら null（例外を投げない＝UIで扱いやすい） */
export function decodeCode(raw: string): SharePayload | null {
  if (!raw) return null;
  const parts = normalizeCode(raw).split("-");
  if (parts.length !== 7) return null;
  if (parts[0] !== CODE_VERSION) return null;

  const lp = Number(parts[1]);
  if (!Number.isInteger(lp) || !VALID_LIFE_PATHS.has(lp)) return null;

  const big5 = {} as Big5Scores;
  for (const [i, key] of KEYS.entries()) {
    const v = Number(parts[i + 2]);
    if (!Number.isInteger(v) || v < 0 || v > 100) return null;
    big5[key] = v;
  }
  return { life_path: lp as LifePath, big5 };
}

function clampScore(v: number): number {
  return Math.max(0, Math.min(100, Math.round(v)));
}

/** 「この人と相性を見る」共有URL（受け取った側では target として読み込まれる） */
export function buildCompatibilityUrl(origin: string, myCode: string): string {
  return `${origin}/compatibility?with=${encodeURIComponent(myCode)}`;
}

/** LINE友だち追加URLに診断結果を引き継ぐ（§5.7） */
export function buildLineUrl(baseUrl: string, code: string, lens?: string): string {
  if (!baseUrl) return "";
  const sep = baseUrl.includes("?") ? "&" : "?";
  const lensPart = lens ? `&lens=${encodeURIComponent(lens)}` : "";
  return `${baseUrl}${sep}numen=${encodeURIComponent(code)}${lensPart}`;
}
