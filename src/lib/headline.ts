// クライアント安全な融合ロジック（要件定義書 §5.4）。
// 公開データ（キーワード）のみを参照するため、有料コンテンツをバンドルに持ち込まない。
// フル解説を含む確定事実の組み立ては fusion.ts（サーバー専用）を使うこと。
import type { Big5Key, Big5Scores, LifePath } from "./types";
import { getPublicNumber } from "./contentPublic";

const FACTOR_JA: Record<Big5Key, string> = {
  E: "外向性",
  A: "協調性",
  C: "勤勉性",
  N: "情緒の波",
  O: "開放性",
};

export type Level = "high" | "mid" | "low";

export function levelOf(score: number): Level {
  if (score >= 67) return "high";
  if (score <= 33) return "low";
  return "mid";
}

/** Big5プロファイルを「高い/低い」の言語ラベルに変換（AIプロンプトの事実として渡す） */
export function big5Descriptors(scores: Big5Scores): {
  factor: Big5Key;
  label: string;
  score: number;
  level: Level;
}[] {
  return (Object.keys(FACTOR_JA) as Big5Key[]).map((f) => ({
    factor: f,
    label: FACTOR_JA[f],
    score: scores[f],
    level: levelOf(scores[f]),
  }));
}

/**
 * 数秘ラベル × Big5補正の「一言所見」を決定論で生成する（無料結果の一言／AIのたたき台）。
 * 例: ライフパス3（創造）でも外向性が低ければ「静かな創造者」。
 */
export function fusionHeadline(lifePath: LifePath, scores: Big5Scores): string {
  const core = getPublicNumber(lifePath).keywords[0] ?? `ライフパス${lifePath}`;
  const e = levelOf(scores.E);
  const prefix = e === "low" ? "静かな" : e === "high" ? "はじける" : "";
  return `${prefix}${core}の人（ライフパス${lifePath}）`;
}
