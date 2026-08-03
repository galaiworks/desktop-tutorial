// 診断結果の保存（要件定義書 §7 データ設計）
// 依存を増やさないため Supabase REST を fetch で叩く。サーバ側専用（service role key を使う）。
// 環境変数が未設定なら完全に無効化され、診断そのものは動き続ける。
import type { Big5Scores, Lens, LifePath } from "./types";

const URL = process.env.SUPABASE_URL;
const KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

export function isPersistenceEnabled(): boolean {
  return Boolean(URL && KEY);
}

async function insert(table: string, row: Record<string, unknown>): Promise<void> {
  if (!isPersistenceEnabled()) return;
  try {
    await fetch(`${URL}/rest/v1/${table}`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        apikey: KEY as string,
        authorization: `Bearer ${KEY}`,
        prefer: "return=minimal",
      },
      body: JSON.stringify(row),
    });
  } catch {
    // 計測・保存の失敗が診断体験を壊さないようにする（ログのみ）
    console.warn(`[numen] failed to persist into ${table}`);
  }
}

/** 自己診断の記録。生年月日は保存しない（算出済みのライフパスのみ §13-4） */
export async function recordDiagnosis(params: {
  life_path: LifePath;
  big5: Big5Scores;
  lens: Lens;
}): Promise<void> {
  await insert("diagnoses", {
    life_path: params.life_path,
    big5: params.big5,
    lens: params.lens,
  });
}

/** 相性診断の記録 */
export async function recordMatch(params: {
  self_life_path: LifePath;
  target_life_path: LifePath;
  lens: Lens;
  score: number;
}): Promise<void> {
  await insert("matches", {
    self_life_path: params.self_life_path,
    target_life_path: params.target_life_path,
    lens: params.lens,
    score: params.score,
  });
}
