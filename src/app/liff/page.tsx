"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { decodeCode } from "@/lib/share";
import { loadSelf } from "@/lib/storage";
import { getNumberContent } from "@/lib/content";
import { fusionHeadline } from "@/lib/fusion";
import type { Lens, Person } from "@/lib/types";

const LIFF_ID = process.env.NEXT_PUBLIC_LIFF_ID || "";
const LIFF_SDK = "https://static.line-scdn.net/liff/edge/2/sdk.js";

interface LiffSdk {
  init: (c: { liffId: string }) => Promise<void>;
  isLoggedIn: () => boolean;
  login: () => void;
  getProfile: () => Promise<{ userId: string; displayName: string }>;
}
declare global {
  interface Window {
    liff?: LiffSdk;
  }
}

type State = "loading" | "ready" | "unconfigured" | "error";

/**
 * LIFF（LINE内ミニアプリ）エントリ — 要件定義書 §5.7「将来: LIFF」/ §8。
 * LINE内で開かれた友だちに、Webでは伏せているフル鑑定を表示する。
 */
export default function LiffPage() {
  const [state, setState] = useState<State>("loading");
  const [displayName, setDisplayName] = useState("");
  const [self, setSelf] = useState<Person | null>(null);
  const [lens, setLens] = useState<Lens>("romance");
  const [message, setMessage] = useState("");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const fromUrl = decodeCode(params.get("numen") ?? "");
    const stored = loadSelf();
    const urlLens = params.get("lens");
    if (urlLens === "business" || urlLens === "romance") setLens(urlLens);
    else if (stored) setLens(stored.lens);

    const resolved = fromUrl ?? (stored ? { life_path: stored.life_path, big5: stored.big5 } : null);
    setSelf(resolved);

    if (!LIFF_ID) {
      setState("unconfigured");
      return;
    }

    // SDKはCDNから実行時に読み込む（未設定環境でビルドを壊さないため）
    const script = document.createElement("script");
    script.src = LIFF_SDK;
    script.async = true;
    script.onload = async () => {
      try {
        const liff = window.liff;
        if (!liff) throw new Error("LIFF SDKを読み込めませんでした");
        await liff.init({ liffId: LIFF_ID });
        if (!liff.isLoggedIn()) {
          liff.login();
          return;
        }
        const profile = await liff.getProfile();
        setDisplayName(profile.displayName);
        setState("ready");

        if (resolved) {
          await fetch("/api/link", {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({
              code: params.get("numen") ?? "",
              line_user_id: profile.userId,
              lens: urlLens ?? "romance",
            }),
          }).catch(() => {});
        }
      } catch (e) {
        setMessage((e as Error).message);
        setState("error");
      }
    };
    script.onerror = () => {
      setMessage("LIFF SDKの読み込みに失敗しました");
      setState("error");
    };
    document.body.appendChild(script);
    return () => {
      script.remove();
    };
  }, []);

  const content = self ? getNumberContent(self.life_path) : null;

  return (
    <>
      <div className="card story">
        <p className="eyebrow story">LINE限定</p>
        <h1 className="serif">
          {displayName ? `${displayName}さんのフル鑑定` : "フル鑑定"}
        </h1>
        {state === "loading" && <p className="muted">読み込んでいます…</p>}
        {state === "unconfigured" && (
          <>
            <p className="muted">
              このページは公式LINEの友だち向けです。LINEアプリ内から開いてください。
            </p>
            <p className="muted">
              （設定メモ：環境変数 <code>NEXT_PUBLIC_LIFF_ID</code>{" "}
              を設定すると有効化されます）
            </p>
            <div className="btn-row">
              <Link href="/diagnose" className="btn btn-outline">
                無料診断にもどる
              </Link>
            </div>
          </>
        )}
        {state === "error" && (
          <p className="err" role="alert">
            {message}
          </p>
        )}
        {state === "ready" && !self && (
          <>
            <p className="muted">
              診断結果が見つかりませんでした。先に無料診断を受けてください。
            </p>
            <div className="btn-row">
              <Link href="/diagnose" className="btn btn-primary">
                無料診断をする
              </Link>
            </div>
          </>
        )}
      </div>

      {/* LINE内で本人確認できた場合のみ本命コンテンツを開放する（§8のゲートを迂回させない） */}
      {state === "ready" && self && content && (
        <>
          <div className="card story">
            <p className="eyebrow story">あなたの数</p>
            <div style={{ textAlign: "center" }}>
              <div className="numeral" aria-hidden="true">
                {self.life_path}
              </div>
              <p className="type-name">{fusionHeadline(self.life_path, self.big5)}</p>
            </div>
          </div>

          {/* Webでは blur で伏せている本命コンテンツを、LINE内では開放する（§8） */}
          <div className="card">
            <p className="eyebrow story">フル鑑定</p>
            <h2 className="serif">あなたという人の全体像</h2>
            <p>
              <b>本質：</b>
              {content.essence}
            </p>
            <p>
              <b>使命：</b>
              {content.mission}
            </p>
            <p>
              <b>強み：</b>
              {content.strengths.join(" / ")}
            </p>
            <p>
              <b>{lens === "romance" ? "恋愛の傾向" : "仕事・適職の傾向"}：</b>
              {lens === "romance" ? content.love : content.work}
            </p>
            <p>
              <b>気をつけたいこと：</b>
              {content.caution}
            </p>
          </div>
        </>
      )}

      <p className="notice">
        本診断は娯楽・自己理解を目的としたもので、結果を保証するものではありません。
      </p>
    </>
  );
}
