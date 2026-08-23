import { NextRequest, NextResponse } from "next/server";
import { rankCandidates } from "@/lib/matching";
import {
  isPersistenceEnabled,
  listCandidates,
  upsertMatchProfile,
} from "@/lib/persistence";
import type { Big5Key, Big5Scores, LifePath } from "@/lib/types";

export const runtime = "nodejs";

const LIFEPATHS = new Set([1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 22, 33]);
const KEYS: Big5Key[] = ["E", "A", "C", "N", "O"];

function parseSelf(o: Record<string, unknown>): {
  life_path: LifePath;
  big5: Big5Scores;
} | null {
  const lp = Number(o.life_path);
  if (!LIFEPATHS.has(lp)) return null;
  const b = o.big5 as Record<string, unknown> | undefined;
  if (!b) return null;
  const big5 = {} as Big5Scores;
  for (const k of KEYS) {
    const v = Number(b[k]);
    if (!Number.isFinite(v) || v < 0 || v > 100) return null;
    big5[k] = Math.round(v);
  }
  return { life_path: lp as LifePath, big5 };
}

/**
 * POST /api/match
 * - action: "recommend" … 相性上位の候補を返す
 * - action: "join"      … マッチングへの参加登録（明示的オプトインが必須）
 */
export async function POST(req: NextRequest) {
  if (!isPersistenceEnabled()) {
    return NextResponse.json(
      {
        error:
          "マッチング機能はデータベース未設定のため利用できません（SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY を設定してください）",
        configured: false,
      },
      { status: 503 }
    );
  }

  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "JSONが不正です" }, { status: 400 });
  }
  const o = body as Record<string, unknown>;
  const self = parseSelf(o);
  if (!self) {
    return NextResponse.json({ error: "診断データが不正です" }, { status: 400 });
  }
  const lens = o.lens === "business" ? "business" : "romance";

  if (o.action === "join") {
    // 同意なしに他人へ推薦されないよう、明示的なオプトインを必須にする（§13-6）
    if (o.opted_in !== true) {
      return NextResponse.json(
        { error: "マッチングへの参加には同意（opted_in）が必要です" },
        { status: 400 }
      );
    }
    const handle =
      typeof o.handle === "string" && o.handle.trim()
        ? o.handle.trim().slice(0, 24)
        : null;
    if (!handle) {
      return NextResponse.json(
        { error: "表示名（ニックネーム）を入力してください" },
        { status: 400 }
      );
    }
    await upsertMatchProfile({ ...self, handle, lens, opted_in: true });
    return NextResponse.json({ ok: true });
  }

  const limit = Math.min(20, Math.max(1, Number(o.limit) || 10));
  const candidates = await listCandidates(lens);
  const ranked = rankCandidates(self, candidates, lens, limit);

  // 他人の性格スコアそのものは返さない（表示に必要な情報だけに絞る §13-4）
  const recommendations = ranked.map(({ id, handle, life_path, score }) => ({
    id,
    handle,
    life_path,
    score,
  }));
  return NextResponse.json({ recommendations, candidateCount: candidates.length });
}
