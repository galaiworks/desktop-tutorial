// チーム相性（BtoB）— 要件定義書 §2 提供価値③ / §3.2
// 個々のペア相性を積み上げ、チーム全体の傾向を決定論で算出する。
// §13-5: 性格特性を「良し悪し」で断じないため、出力は「傾向」と「補い方」に限定する。
import { compatibility } from "./compatibility";
import type { Big5Key, Big5Scores, Lens, LifePath } from "./types";

export interface TeamMember {
  id: string;
  name: string;
  life_path: LifePath;
  big5: Big5Scores;
}

export interface PairScore {
  a: string; // member id
  b: string;
  aName: string;
  bName: string;
  score: number;
  numerologyScore: number;
  big5Score: number;
}

export interface TeamResult {
  lens: Lens;
  memberCount: number;
  pairs: PairScore[];
  averageScore: number;
  strongestPair: PairScore | null;
  weakestPair: PairScore | null;
  /** チーム平均のBig5プロファイル */
  profile: Big5Scores;
  /** 因子ごとのばらつき（標準偏差）。高い＝多様、低い＝均質 */
  diversity: Record<Big5Key, number>;
  notes: string[];
}

const FACTORS: Big5Key[] = ["E", "A", "C", "N", "O"];
const FACTOR_JA: Record<Big5Key, string> = {
  E: "外向性",
  A: "協調性",
  C: "勤勉性",
  N: "情緒の波",
  O: "開放性",
};

function mean(values: number[]): number {
  if (values.length === 0) return 0;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

function stdev(values: number[]): number {
  if (values.length < 2) return 0;
  const m = mean(values);
  return Math.sqrt(mean(values.map((v) => (v - m) ** 2)));
}

/**
 * チーム全員の総当たり相性と、チーム全体の傾向を算出する。
 * メンバーは2名以上必要。
 */
export function teamCompatibility(
  members: TeamMember[],
  lens: Lens = "business"
): TeamResult {
  if (members.length < 2) {
    throw new Error("チーム相性の算出には2名以上が必要です");
  }

  const pairs: PairScore[] = [];
  for (let i = 0; i < members.length; i++) {
    for (let j = i + 1; j < members.length; j++) {
      const a = members[i];
      const b = members[j];
      const c = compatibility(a, b, lens);
      pairs.push({
        a: a.id,
        b: b.id,
        aName: a.name,
        bName: b.name,
        score: c.totalScore,
        numerologyScore: c.numerologyScore,
        big5Score: c.big5Score,
      });
    }
  }

  const sorted = [...pairs].sort((x, y) => y.score - x.score);
  const profile = {} as Big5Scores;
  const diversity = {} as Record<Big5Key, number>;
  for (const f of FACTORS) {
    const vals = members.map((m) => m.big5[f]);
    profile[f] = Math.round(mean(vals));
    diversity[f] = Math.round(stdev(vals));
  }

  return {
    lens,
    memberCount: members.length,
    pairs,
    averageScore: Math.round(mean(pairs.map((p) => p.score))),
    strongestPair: sorted[0] ?? null,
    weakestPair: sorted[sorted.length - 1] ?? null,
    profile,
    diversity,
    notes: buildNotes(profile, diversity),
  };
}

/** チームの傾向メモ（決定論。優劣ではなく「傾向と補い方」として書く §13-5） */
function buildNotes(
  profile: Big5Scores,
  diversity: Record<Big5Key, number>
): string[] {
  const notes: string[] = [];

  if (profile.C >= 65) {
    notes.push("計画性と実行力が高いチームです。着実に進む一方、想定外の変化には意識して余白を作ると動きやすくなります。");
  } else if (profile.C <= 35) {
    notes.push("柔軟で即応性のあるチームです。締切や担当の明文化を足すと、力がさらに形になります。");
  }

  if (profile.O >= 65) {
    notes.push("新しい発想が出やすいチームです。アイデアを絞り込む担当を決めると実装まで届きます。");
  } else if (profile.O <= 35) {
    notes.push("堅実な判断が得意なチームです。外部の視点を定期的に入れると選択肢が広がります。");
  }

  if (profile.A >= 65) {
    notes.push("協調性が高く、衝突が起きにくいチームです。あえて反対意見を出す役割を置くと、検討の質が上がります。");
  } else if (profile.A <= 35) {
    notes.push("率直に議論できるチームです。合意形成の手順を決めておくと、議論が前に進みやすくなります。");
  }

  const spread = FACTORS.filter((f) => diversity[f] >= 25).map((f) => FACTOR_JA[f]);
  if (spread.length > 0) {
    notes.push(`${spread.join("・")}の幅が広いチームです。違いは役割分担の手がかりになります。`);
  } else {
    notes.push("メンバーの傾向が似通っています。まとまりやすい反面、視点が偏らないよう外部の意見を取り入れると安心です。");
  }

  return notes;
}
