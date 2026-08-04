// マッチング（ユーザー同士の相互推薦）— 要件定義書 §3.2 / §5.6
// ランキングは純粋関数。データ取得は persistence 側に分離する。
import { compatibility } from "./compatibility";
import type { Big5Scores, Lens, LifePath } from "./types";

export interface Candidate {
  id: string;
  handle: string;
  life_path: LifePath;
  big5: Big5Scores;
}

export interface Recommendation extends Candidate {
  score: number;
  numerologyScore: number;
  big5Score: number;
}

/**
 * 候補者を相性スコア順に並べ、上位を返す。
 * 自分自身は除外する。同点はハンドル名で安定ソートする。
 */
export function rankCandidates(
  self: { id?: string; life_path: LifePath; big5: Big5Scores },
  candidates: Candidate[],
  lens: Lens,
  limit = 10
): Recommendation[] {
  return candidates
    .filter((c) => c.id !== self.id)
    .map((c) => {
      const r = compatibility(self, c, lens);
      return {
        ...c,
        score: r.totalScore,
        numerologyScore: r.numerologyScore,
        big5Score: r.big5Score,
      };
    })
    .sort((a, b) => b.score - a.score || a.handle.localeCompare(b.handle))
    .slice(0, Math.max(0, limit));
}
