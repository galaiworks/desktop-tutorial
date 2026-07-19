// 融合ロジック（要件定義書 §5.4）: 数秘=ラベル、Big5=補正。
// ここでは「AIに渡す前の確定した読み筋（決定的部分）」を組み立てる。読み物化はAIレイヤーの責務。
import type { Big5Key, Big5Scores, Lens, LifePath, NumberContent } from "./types";
import { getNumberContent } from "./content";

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
  const c = getNumberContent(lifePath);
  const core = c.keywords[0] ?? c.essence.slice(0, 6);
  const e = levelOf(scores.E);
  const prefix =
    e === "low" ? "静かな" : e === "high" ? "はじける" : "";
  return `${prefix}${core}の人（ライフパス${lifePath}）`;
}

export interface FusionFacts {
  lifePath: LifePath;
  content: NumberContent;
  big5: Big5Scores;
  descriptors: ReturnType<typeof big5Descriptors>;
  headline: string;
  lens: Lens;
}

/** AI生成レイヤーに渡す確定事実の束を構築（ハルシネーション防止：AIはこれを創作しない）。 */
export function buildFusionFacts(
  lifePath: LifePath,
  big5: Big5Scores,
  lens: Lens
): FusionFacts {
  return {
    lifePath,
    content: getNumberContent(lifePath),
    big5,
    descriptors: big5Descriptors(big5),
    headline: fusionHeadline(lifePath, big5),
    lens,
  };
}
