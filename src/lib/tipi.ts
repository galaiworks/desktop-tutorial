// TIPI-J 採点エンジン（要件定義書 §5.3 / 付録A）
import tipi from "@config/tipi_j.json";
import type { Big5Key, Big5Raw, Big5Result, Big5Scores } from "./types";

interface TipiItem {
  id: number;
  factor: Big5Key;
  reverse: boolean;
  placeholder: boolean;
  text: string;
}
interface TipiConfig {
  scale: { min: number; max: number; stem: string; anchors: Record<string, string> };
  reverseFormula: string;
  factors: Record<Big5Key, string>;
  items: TipiItem[];
  citation: string;
}

const cfg = tipi as unknown as TipiConfig;
export const TIPI = cfg;
export const ITEMS = cfg.items;
export const FACTORS: Big5Key[] = ["E", "A", "C", "N", "O"];

const SCALE_MIN = cfg.scale.min; // 1
const SCALE_MAX = cfg.scale.max; // 7

/** 逆転処理: (min+max) - value （TIPI-Jは 8 - value） */
export function applyReverse(value: number): number {
  return SCALE_MIN + SCALE_MAX - value;
}

/**
 * TIPI-J回答（項目id順・10件・各1〜7）を採点する。
 * 各因子 = 対応2項目の平均（逆転項目は逆転処理後）。1〜7の素点と0〜100正規化を返す。
 */
export function scoreTipi(answers: number[]): Big5Result {
  if (answers.length !== cfg.items.length) {
    throw new Error(`回答数が不正です。${cfg.items.length}件必要ですが ${answers.length}件でした。`);
  }
  for (const [i, v] of answers.entries()) {
    if (!Number.isInteger(v) || v < SCALE_MIN || v > SCALE_MAX) {
      throw new Error(`項目${i + 1}の回答が範囲外です（${SCALE_MIN}〜${SCALE_MAX}）: ${v}`);
    }
  }

  const byFactor: Record<Big5Key, number[]> = { E: [], A: [], C: [], N: [], O: [] };
  cfg.items.forEach((item, idx) => {
    const raw = answers[idx];
    byFactor[item.factor].push(item.reverse ? applyReverse(raw) : raw);
  });

  const rawScores = {} as Big5Raw;
  const scores = {} as Big5Scores;
  for (const f of FACTORS) {
    const vals = byFactor[f];
    const mean = vals.reduce((a, b) => a + b, 0) / vals.length; // 1〜7
    rawScores[f] = Math.round(mean * 100) / 100;
    // 1〜7 → 0〜100 に正規化
    scores[f] = Math.round(((mean - SCALE_MIN) / (SCALE_MAX - SCALE_MIN)) * 100);
  }

  return { raw: rawScores, scores };
}
