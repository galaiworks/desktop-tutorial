"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { decodeCode, encodeCode } from "@/lib/share";
import { loadSelf } from "@/lib/storage";
import { fusionHeadline } from "@/lib/headline";
import type { Lens, Person } from "@/lib/types";

const LIFF_ID = process.env.NEXT_PUBLIC_LIFF_ID || "";
const LIFF_SDK = "https://static.line-scdn.net/liff/edge/2/sdk.js";

interface LiffSdk {
  init: (c: { liffId: string }) => Promise<void>;
  isLoggedIn: () => boolean;
  login: () => void;
  getIDToken: () => string | null;
}
declare global {
  interface Window {
    liff?: LiffSdk;
  }
}

interface FullReading {
  keywords: string[];
  essence: string;
  mission: string;
  strengths: string[];
  lensText: string;
  caution: string;
}

type State = "loading" | "ready" | "unconfigured" | "denied" | "error";

/**
 * LIFF（LINE内ミニアプリ）エントリ — 要件定義書 §5.7 / §8。
 * フル鑑定の本文はこのページのバンドルに含めず、IDトークンをサーバーで検証したうえで
 * /api/reading/full から取得する（クライアント側の表示制御だけに頼らない）。
 */
export default function LiffPage() {
  const [state, setState] = useState<State>("loading");
  const [displayName, setDisplayName] = useState<string | null>(null);
  const [self, setSelf] = useState<Person | null>(null);
  const [lens, setLens] = useState<Lens>("romance");
  const [reading, setReading] = useState<FullReading | null>(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const stored = loadSelf();
    const fromUrl = decodeCode(params.get("numen") ?? "");
    const urlLens = params.get("lens");
    const resolvedLens: Lens =
      urlLens === "business" || urlLens === "romance"
        ? urlLens
        : (stored?.lens ?? "romance");
    setLens(resolvedLens);

    const resolved =
      fromUrl ?? (stored ? { life_path: stored.life_path, big5: stored.big5 } : null);
    setSelf(resolved);

    if (!LIFF_ID) {
      setState("unconfigured");
      return;
    }

    // SDKは実行時にCDNから読み込む（未設定環境でビルドを壊さないため）
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
        const idToken = liff.getIDToken();
        if (!idToken) throw new Error("LINEのIDトークンを取得できませんでした");
        if (!resolved) {
          setState("ready");
          return;
        }

        const res = await fetch("/api/reading/full", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            id_token: idToken,
            code: encodeCode(resolved),
            lens: resolvedLens,
          }),
        });
        const data = await res.json();
        if (!res.ok) {
          setMessage(data.error ?? "フル鑑定を取得できませんでした");
          setState(res.status === 401 ? "denied" : "error");
          return;
        }
        setDisplayName(data.displayName ?? null);
        setReading(data.reading);
        setState("ready");
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
              （設定メモ：<code>NEXT_PUBLIC_LIFF_ID</code> と{" "}
              <code>LINE_LOGIN_CHANNEL_ID</code> を設定すると有効化されます）
            </p>
            <div className="btn-row">
              <Link href="/diagnose" className="btn btn-outline">
                無料診断にもどる
              </Link>
            </div>
          </>
        )}

        {(state === "denied" || state === "error") && (
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

      {/* 本文はサーバー検証を通った場合のみ届く */}
      {reading && self && (
        <>
          <div className="card story">
            <p className="eyebrow story">あなたの数</p>
            <div style={{ textAlign: "center" }}>
              <div className="numeral" aria-hidden="true">
                {self.life_path}
              </div>
              <p className="type-name">
                {fusionHeadline(self.life_path, self.big5)}
              </p>
            </div>
          </div>

          <div className="card">
            <p className="eyebrow story">フル鑑定</p>
            <h2 className="serif">あなたという人の全体像</h2>
            <p>
              <b>本質：</b>
              {reading.essence}
            </p>
            <p>
              <b>使命：</b>
              {reading.mission}
            </p>
            <p>
              <b>強み：</b>
              {reading.strengths.join(" / ")}
            </p>
            <p>
              <b>{lens === "romance" ? "恋愛の傾向" : "仕事・適職の傾向"}：</b>
              {reading.lensText}
            </p>
            <p>
              <b>気をつけたいこと：</b>
              {reading.caution}
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
