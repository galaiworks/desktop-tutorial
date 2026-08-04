import { NextRequest, NextResponse } from "next/server";
import { decodeCode } from "@/lib/share";
import { isPersistenceEnabled, linkLineUser } from "@/lib/persistence";

export const runtime = "nodejs";

/**
 * POST /api/link — LIFFで取得したLINEユーザーと診断結果を紐付ける（§5.7）
 * LIFFのアクセストークン検証はLINE側の設定に依存するため、
 * 本番導入時は verifyIdToken を通したうえで line_user_id を渡すこと。
 */
export async function POST(req: NextRequest) {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "JSONが不正です" }, { status: 400 });
  }
  const o = body as Record<string, unknown>;

  const code = typeof o.code === "string" ? o.code : "";
  const payload = decodeCode(code);
  if (!payload) {
    return NextResponse.json({ error: "診断コードが不正です" }, { status: 400 });
  }

  const lineUserId = typeof o.line_user_id === "string" ? o.line_user_id : "";
  if (!lineUserId) {
    return NextResponse.json(
      { error: "LINEユーザー情報が取得できませんでした" },
      { status: 400 }
    );
  }

  const lens = o.lens === "business" ? "business" : "romance";

  if (!isPersistenceEnabled()) {
    // DB未設定でもLIFF側の表示は続行できるよう、保存だけを飛ばす
    return NextResponse.json({ ok: true, persisted: false });
  }

  await linkLineUser({
    token: code,
    line_user_id: lineUserId,
    life_path: payload.life_path,
    big5: payload.big5,
    lens,
  });
  return NextResponse.json({ ok: true, persisted: true });
}
