// ビッグファイブ尺度アダプタ（要件定義書 §5.3 / §13-2 / §14）
// 尺度は差し替え可能にしてある。config/big5_scale.json の active を変えるだけで、
// 独自尺度（numen-10）と TIPI-J を切り替えられる。
import selector from "@config/big5_scale.json";
import numen10 from "@config/scales/numen-10.json";
import tipiJ from "@config/scales/tipi-j.json";
import type { Big5Key, Big5Raw, Big5Result, Big5Scores } from "./types";

export interface ScaleItem {
  id: number;
  factor: Big5Key;
  reverse: boolean;
  text: string;
  /** 正規の項目文への差し替えが必要な仮テキストかどうか */
  placeholder?: boolean;
}

export interface Big5Scale {
  id: string;
  label: string;
  /** 出典。独自尺度は null */
  citation: string | null;
  licenseNote: string;
  /** 学術的な信頼性・妥当性の検証を経ているか */
  validated: boolean;
  validationNote: string;
  scale: {
    min: number;
    max: number;
    stem: string;
    anchors: Record<string, string>;
  };
  reverseFormula: string;
  factors: Record<Big5Key, string>;
  items: ScaleItem[];
}

const REGISTRY: Record<string, Big5Scale> = {
  "numen-10": numen10 as unknown as Big5Scale,
  "tipi-j": tipiJ as unknown as Big5Scale,
};

const activeId = (selector as { active: string }).active;

export const SCALE: Big5Scale = REGISTRY[activeId] ?? REGISTRY["numen-10"];
export const ITEMS = SCALE.items;
export const FACTORS: Big5Key[] = ["E", "A", "C", "N", "O"];

export function getScale(id: string): Big5Scale | undefined {
  return REGISTRY[id];
}

export function listScales(): Big5Scale[] {
  return Object.values(REGISTRY);
}

/** 逆転処理: (min + max) - value（7件法なら 8 - value） */
export function applyReverse(value: number, scale: Big5Scale = SCALE): number {
  return scale.scale.min + scale.scale.max - value;
}

/**
 * 回答（項目順・各 min〜max）を採点する。
 * 各因子＝対応2項目の平均（逆転項目は逆転処理後）。素点と0〜100正規化を返す。
 */
export function scoreBig5(answers: number[], scale: Big5Scale = SCALE): Big5Result {
  const { min, max } = scale.scale;
  if (answers.length !== scale.items.length) {
    throw new Error(
      `回答数が不正です。${scale.items.length}件必要ですが ${answers.length}件でした。`
    );
  }
  for (const [i, v] of answers.entries()) {
    if (!Number.isInteger(v) || v < min || v > max) {
      throw new Error(`項目${i + 1}の回答が範囲外です（${min}〜${max}）: ${v}`);
    }
  }

  const byFactor: Record<Big5Key, number[]> = { E: [], A: [], C: [], N: [], O: [] };
  scale.items.forEach((item, idx) => {
    const raw = answers[idx];
    byFactor[item.factor].push(item.reverse ? applyReverse(raw, scale) : raw);
  });

  const rawScores = {} as Big5Raw;
  const scores = {} as Big5Scores;
  for (const f of FACTORS) {
    const vals = byFactor[f];
    const m = vals.reduce((a, b) => a + b, 0) / vals.length;
    rawScores[f] = Math.round(m * 100) / 100;
    scores[f] = Math.round(((m - min) / (max - min)) * 100);
  }
  return { raw: rawScores, scores };
}

/** UIの脚注に出す出典表記。独自尺度のときは検証未実施である旨を返す。 */
export function scaleFootnote(scale: Big5Scale = SCALE): string {
  if (scale.citation) return `性格傾向の尺度：${scale.citation}`;
  return `性格傾向の尺度：${scale.label}（本サービス独自作成。学術的な検証は行っていません）`;
}
