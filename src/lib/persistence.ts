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

// ── フェーズ2: マッチング / LIFF 連携（§3.2 / §5.7） ──

interface MatchProfileRow {
  id: string;
  handle: string;
  life_path: LifePath;
  big5: Big5Scores;
}

async function select<T>(path: string): Promise<T[]> {
  if (!isPersistenceEnabled()) return [];
  try {
    const res = await fetch(`${URL}/rest/v1/${path}`, {
      headers: {
        apikey: KEY as string,
        authorization: `Bearer ${KEY}`,
      },
      cache: "no-store",
    });
    if (!res.ok) return [];
    return (await res.json()) as T[];
  } catch {
    console.warn(`[numen] failed to query ${path}`);
    return [];
  }
}

/** マッチングにオプトインした候補者を取得する（レンズ別） */
export async function listCandidates(
  lens: Lens,
  limit = 200
): Promise<MatchProfileRow[]> {
  return select<MatchProfileRow>(
    `match_profiles?opted_in=eq.true&lens=eq.${lens}` +
      `&select=id,handle,life_path,big5&limit=${limit}`
  );
}

/** マッチングへの参加登録（明示的オプトインが前提） */
export async function upsertMatchProfile(params: {
  handle: string;
  life_path: LifePath;
  big5: Big5Scores;
  lens: Lens;
  opted_in: boolean;
}): Promise<void> {
  await insert("match_profiles", { ...params, updated_at: new Date().toISOString() });
}

/** LIFFで取得したLINEユーザーと診断結果を紐付ける（§5.7） */
export async function linkLineUser(params: {
  token: string;
  line_user_id: string;
  life_path: LifePath;
  big5: Big5Scores;
  lens: Lens;
}): Promise<void> {
  await insert("line_links", { ...params, consumed_at: new Date().toISOString() });
}
