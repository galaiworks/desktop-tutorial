// 相性エンジン（要件定義書 §5.6）— 数値は完全にコードで確定させ、AIには解説のみ任せる。
import affinity from "@config/numerology_affinity.json";
import big5compat from "@config/big5_compat.json";
import scoring from "@config/scoring.json";
import type {
  Big5Key,
  Big5Scores,
  CompatibilityResult,
  Lens,
  LifePath,
} from "./types";

type Matrix = Record<string, Record<string, number>>;
interface AffinityConfig {
  numbers: number[];
  romance: Matrix;
  business: Matrix;
}
interface FactorRule {
  mode: "similarity" | "complementarity";
  weight: number;
}
interface Big5CompatConfig {
  factors: Big5Key[];
  romance: Record<Big5Key, FactorRule>;
  business: Record<Big5Key, FactorRule>;
}
interface ScoringConfig {
  numerologyWeight: number;
  big5Weight: number;
}

const affinityCfg = affinity as unknown as AffinityConfig;
const compatCfg = big5compat as unknown as Big5CompatConfig;
const scoringCfg = scoring as unknown as ScoringConfig;

/** 数秘相性（0–100）。マトリクスは対称でない場合もありうるので両方向の平均を取る。 */
export function numerologyAffinity(a: LifePath, b: LifePath, lens: Lens): number {
  const m = affinityCfg[lens];
  const ab = m?.[String(a)]?.[String(b)];
  const ba = m?.[String(b)]?.[String(a)];
  if (ab == null && ba == null) return 50;
  if (ab == null) return ba!;
  if (ba == null) return ab;
  return Math.round((ab + ba) / 2);
}

/**
 * Big5相性（0–100）。因子ごとに similarity / complementarity と重みを適用（要件定義書 §5.6 B）。
 * similarity: |diff| が小さいほど高得点。complementarity: |diff| が大きいほど高得点。
 */
export function big5Compatibility(
  self: Big5Scores,
  target: Big5Scores,
  lens: Lens
): { score: number; breakdown: CompatibilityResult["breakdown"] } {
  const rules = compatCfg[lens];
  const breakdown: CompatibilityResult["breakdown"] = [];
  let weighted = 0;
  let weightSum = 0;

  for (const f of compatCfg.factors) {
    const rule = rules[f];
    const diff = Math.abs(self[f] - target[f]); // 0–100
    const factorScore =
      rule.mode === "similarity" ? 100 - diff : diff; // 0–100
    weighted += factorScore * rule.weight;
    weightSum += rule.weight;
    breakdown.push({
      factor: f,
      mode: rule.mode,
      weight: rule.weight,
      score: Math.round(factorScore),
    });
  }

  const score = weightSum === 0 ? 50 : Math.round(weighted / weightSum);
  return { score, breakdown };
}

/** 総合相性スコア = 数秘相性 × w1 + Big5相性 × w2（重みは正規化）。 */
export function compatibility(
  self: { life_path: LifePath; big5: Big5Scores },
  target: { life_path: LifePath; big5: Big5Scores },
  lens: Lens
): CompatibilityResult {
  const numerologyScore = numerologyAffinity(self.life_path, target.life_path, lens);
  const { score: big5Score, breakdown } = big5Compatibility(self.big5, target.big5, lens);

  const w1 = scoringCfg.numerologyWeight;
  const w2 = scoringCfg.big5Weight;
  const wSum = w1 + w2 || 1;
  const totalScore = Math.round((numerologyScore * w1 + big5Score * w2) / wSum);

  return { lens, numerologyScore, big5Score, totalScore, breakdown };
}
