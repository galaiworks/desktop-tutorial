// クライアントに送ってよいナンバー情報だけを扱うモジュール（要件定義書 §8）。
// 有料コンテンツ（本質・使命・強み・恋愛/仕事・注意点）は含まれないため、
// このモジュールはクライアントコンポーネントから import してよい。
// フル解説が必要な場合は content.ts（サーバー専用）か /api/reading/full を使うこと。
import data from "@data/numbers.public.json";
import type { LifePath } from "./types";

export interface PublicNumber {
  number: LifePath;
  isMaster: boolean;
  keywords: string[];
}

const numbers = (data as { numbers: Record<string, PublicNumber> }).numbers;

export function getPublicNumber(n: LifePath): PublicNumber {
  const c = numbers[String(n)];
  if (!c) throw new Error(`ナンバー ${n} の公開データが見つかりません`);
  return c;
}

/** フル鑑定に含まれる項目の「見出しだけ」。中身はサーバー側にしか無い。 */
export const LOCKED_SECTIONS = [
  "本質",
  "使命",
  "強み",
  "恋愛・適職",
  "気をつけたいこと",
] as const;
