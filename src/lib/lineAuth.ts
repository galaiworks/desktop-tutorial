// LINEログイン（LIFF）のIDトークン検証 — 要件定義書 §5.7 / §9
// サーバー専用。クライアントから渡された line_user_id を信用せず、
// LINEの検証エンドポイントで本人であることを確かめてから有料コンテンツを渡す。
const VERIFY_ENDPOINT = "https://api.line.me/oauth2/v2.1/verify";

const CHANNEL_ID = process.env.LINE_LOGIN_CHANNEL_ID;

export function isLineAuthConfigured(): boolean {
  return Boolean(CHANNEL_ID);
}

export interface VerifiedLineUser {
  userId: string;
  displayName?: string;
}

/**
 * LIFFの getIDToken() が返すIDトークンを検証し、LINEユーザーIDを取り出す。
 * 検証に失敗した場合は null（呼び出し側は有料コンテンツを返さないこと）。
 */
export async function verifyLineIdToken(
  idToken: string
): Promise<VerifiedLineUser | null> {
  if (!CHANNEL_ID || !idToken) return null;
  try {
    const res = await fetch(VERIFY_ENDPOINT, {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        id_token: idToken,
        client_id: CHANNEL_ID,
      }),
      cache: "no-store",
    });
    if (!res.ok) return null;
    const data = (await res.json()) as {
      sub?: string;
      aud?: string;
      name?: string;
      exp?: number;
    };
    // aud（対象チャネル）が自分のチャネルであることを確認する
    if (!data.sub || data.aud !== CHANNEL_ID) return null;
    if (typeof data.exp === "number" && data.exp * 1000 < Date.now()) return null;
    return { userId: data.sub, displayName: data.name };
  } catch {
    return null;
  }
}
