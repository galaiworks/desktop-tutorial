import { NextRequest, NextResponse } from "next/server";
import { decodeCode } from "@/lib/share";
import { getNumberContent } from "@/lib/content";
import { isLineAuthConfigured, verifyLineIdToken } from "@/lib/lineAuth";
import { linkLineUser } from "@/lib/persistence";

export const runtime = "nodejs";

/**
 * POST /api/reading/full — フル鑑定の本文を返す（要件定義書 §8）
 *
 * 有料（LINE登録後）コンテンツはクライアントのバンドルに含めず、
 * LIFFのIDトークンをサーバーで検証できた場合にのみここから配信する。
 * 検証できない限り本文は一切返さない。
 */
export async function POST(req: NextRequest) {
  if (!isLineAuthConfigured()) {
    return NextResponse.json(
      {
        error:
          "LINEログインが未設定のため、フル鑑定は配信できません（LINE_LOGIN_CHANNEL_ID を設定してください）",
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

  const idToken = typeof o.id_token === "string" ? o.id_token : "";
  const verified = await verifyLineIdToken(idToken);
  if (!verified) {
    return NextResponse.json(
      { error: "LINEアカウントの確認ができませんでした" },
      { status: 401 }
    );
  }

  const payload = decodeCode(typeof o.code === "string" ? o.code : "");
  if (!payload) {
    return NextResponse.json({ error: "診断コードが不正です" }, { status: 400 });
  }

  const lens = o.lens === "business" ? "business" : "romance";
  const c = getNumberContent(payload.life_path);

  // 本人確認できたので診断結果とLINEユーザーを紐付ける（保存先未設定なら無視される）
  linkLineUser({
    token: typeof o.code === "string" ? o.code : "",
    line_user_id: verified.userId,
    life_path: payload.life_path,
    big5: payload.big5,
    lens,
  }).catch(() => {});

  return NextResponse.json({
    displayName: verified.displayName ?? null,
    life_path: payload.life_path,
    reading: {
      keywords: c.keywords,
      essence: c.essence,
      mission: c.mission,
      strengths: c.strengths,
      lensText: lens === "romance" ? c.love : c.work,
      caution: c.caution,
    },
  });
}
