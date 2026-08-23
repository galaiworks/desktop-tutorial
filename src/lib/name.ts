// 名前ベースの数字（ディスティニー／ソウル／パーソナリティ）— 要件定義書 §3.2
// ピタゴラス式の文字対応表は公知（§13-1）。解説文は独自執筆のものを用いる。
import config from "@config/name_numerology.json";
import { masterSet, reduceNumber } from "./numerology";
import type { LifePath } from "./types";

export interface NameNumerologyConfig {
  treatYAsVowel: boolean;
  reductionMethod: "sum-all" | "reduce-each-word";
  aspects: Record<
    NameAspect,
    { label: string; source: string; meaning: string }
  >;
}

export type NameAspect = "destiny" | "soul" | "personality";

const cfg = config as unknown as NameNumerologyConfig;
export const NAME_CONFIG = cfg;

/** ピタゴラス式: A=1..I=9, J=1..R=9, S=1..Z=8 */
export function letterValue(ch: string): number {
  const code = ch.toUpperCase().charCodeAt(0);
  if (code < 65 || code > 90) return 0; // A-Z 以外は無視
  return ((code - 65) % 9) + 1;
}

const BASE_VOWELS = new Set(["A", "E", "I", "O", "U"]);

export function isVowel(ch: string, treatYAsVowel = cfg.treatYAsVowel): boolean {
  const c = ch.toUpperCase();
  if (BASE_VOWELS.has(c)) return true;
  return treatYAsVowel && c === "Y";
}

/**
 * 入力名をローマ字のA-Zのみに正規化し、単語ごとに分割する。
 * 全角英字も受け付ける（日本語話者はローマ字で入力する想定）。
 */
export function normalizeName(input: string): string[] {
  return input
    .replace(/[Ａ-Ｚａ-ｚ]/g, (c) => String.fromCharCode(c.charCodeAt(0) - 0xfee0))
    .split(/[\s　]+/)
    .map((w) => w.replace(/[^A-Za-z]/g, ""))
    .filter((w) => w.length > 0);
}

function sumLetters(word: string, filter: (ch: string) => boolean): number {
  return word
    .split("")
    .filter(filter)
    .reduce((acc, ch) => acc + letterValue(ch), 0);
}

/** 指定アスペクトの数字を算出する。名前が空なら null。 */
export function nameNumber(
  input: string,
  aspect: NameAspect,
  conf: NameNumerologyConfig = cfg
): LifePath | null {
  const words = normalizeName(input);
  if (words.length === 0) return null;

  const filter = (ch: string): boolean => {
    if (aspect === "destiny") return true;
    const vowel = isVowel(ch, conf.treatYAsVowel);
    return aspect === "soul" ? vowel : !vowel;
  };

  const master = masterSet();
  let total: number;
  if (conf.reductionMethod === "reduce-each-word") {
    total = words.reduce(
      (acc, w) => acc + reduceNumber(sumLetters(w, filter), master),
      0
    );
  } else {
    total = words.reduce((acc, w) => acc + sumLetters(w, filter), 0);
  }
  if (total === 0) return null; // 例: 母音が1つも無い綴り
  return reduceNumber(total, master) as LifePath;
}

export interface NameNumbers {
  destiny: LifePath | null;
  soul: LifePath | null;
  personality: LifePath | null;
}

/** 3つのアスペクトをまとめて算出 */
export function nameNumbers(
  input: string,
  conf: NameNumerologyConfig = cfg
): NameNumbers {
  return {
    destiny: nameNumber(input, "destiny", conf),
    soul: nameNumber(input, "soul", conf),
    personality: nameNumber(input, "personality", conf),
  };
}
