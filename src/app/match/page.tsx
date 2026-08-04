"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { loadSelf } from "@/lib/storage";
import { track } from "@/lib/analytics";
import type { Lens, Person } from "@/lib/types";

interface Recommendation {
  id: string;
  handle: string;
  life_path: number;
  score: number;
}

export default function MatchPage() {
  const [self, setSelf] = useState<Person | null>(null);
  const [lens, setLens] = useState<Lens>("romance");
  const [handle, setHandle] = useState("");
  const [agreed, setAgreed] = useState(false);
  const [joined, setJoined] = useState(false);
  const [recs, setRecs] = useState<Recommendation[] | null>(null);
  const [unavailable, setUnavailable] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const stored = loadSelf();
    if (stored) {
      setSelf({ life_path: stored.life_path, big5: stored.big5 });
      setLens(stored.lens);
    }
  }, []);

  async function call(action: "join" | "recommend") {
    if (!self) return;
    setError(null);
    setLoading(true);
    try {
      const res = await fetch("/api/match", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          ...self,
          lens,
          action,
          handle,
          opted_in: agreed,
        }),
      });
      const data = await res.json();
      if (res.status === 503) {
        setUnavailable(data.error);
        return;
      }
      if (!res.ok) throw new Error(data.error ?? "処理に失敗しました");
      if (action === "join") {
        setJoined(true);
      } else {
        setRecs(data.recommendations ?? []);
        track("compatibility_result_view", { kind: "match", lens });
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  if (!self) {
    return (
      <div className="card story">
        <p className="eyebrow story">マッチング</p>
        <h1 className="serif">相性のいい人を探す</h1>
        <p className="muted">
          先に無料の自己診断（約2分）を済ませてください。診断結果をもとに、
          相性の高い方をおすすめします。
        </p>
        <div className="btn-row">
          <Link href="/diagnose" className="btn btn-primary">
            自己診断をする
          </Link>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="card story">
        <p className="eyebrow story">マッチング</p>
        <h1 className="serif">相性のいい人を探す</h1>
        <p className="muted">
          あなた（ライフパス{self.life_path}）の診断結果をもとに、
          参加に同意した方の中から相性の高い順に表示します。
        </p>

        <p className="label" style={{ marginTop: 18 }} id="match-lens">
          探す観点
        </p>
        <div className="lens-toggle" role="group" aria-labelledby="match-lens">
          <button
            type="button"
            aria-pressed={lens === "romance"}
            onClick={() => setLens("romance")}
          >
            恋愛
          </button>
          <button
            type="button"
            aria-pressed={lens === "business"}
            onClick={() => setLens("business")}
          >
            ビジネス
          </button>
        </div>

        <div className="btn-row">
          <button className="btn btn-primary" disabled={loading} onClick={() => call("recommend")}>
            {loading ? "検索中…" : "相性の高い人を見る"}
          </button>
        </div>
      </div>

      {unavailable && (
        <div className="card">
          <p className="eyebrow story">準備中</p>
          <p className="muted">{unavailable}</p>
        </div>
      )}

      {recs && !unavailable && (
        <div className="card science">
          <p className="eyebrow science">おすすめ</p>
          {recs.length === 0 ? (
            <p className="muted">
              まだ参加者がいません。下のフォームから参加すると、
              あなたも他の方のおすすめに表示されるようになります。
            </p>
          ) : (
            <table className="score-table">
              <caption>相性の高い順（0〜100）</caption>
              <thead>
                <tr>
                  <th scope="col">お相手</th>
                  <th scope="col" style={{ textAlign: "right" }}>
                    相性
                  </th>
                </tr>
              </thead>
              <tbody>
                {recs.map((r) => (
                  <tr key={r.id}>
                    <th scope="row" style={{ fontWeight: 600 }}>
                      {r.handle}
                      <span className="muted" style={{ marginLeft: 8, fontWeight: 400 }}>
                        ライフパス{r.life_path}
                      </span>
                      <span className="meter" aria-hidden="true">
                        <i style={{ width: `${r.score}%` }} />
                      </span>
                    </th>
                    <td className="val">{r.score}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {!joined && !unavailable && (
        <div className="card">
          <p className="eyebrow story">参加する</p>
          <h2 className="serif">おすすめに載る</h2>
          <p className="muted">
            参加すると、あなたの<b>表示名とライフパスナンバー</b>が他の参加者の
            おすすめ一覧に表示されます。性格スコアは相性の計算にのみ使われ、
            他の方には表示されません。本名は入力しないでください。
          </p>

          <label htmlFor="handle" style={{ marginTop: 14 }}>
            表示名（ニックネーム）
          </label>
          <input
            id="handle"
            type="text"
            value={handle}
            maxLength={24}
            placeholder="ニックネーム"
            autoComplete="off"
            onChange={(e) => setHandle(e.target.value)}
            style={{ fontFamily: "var(--sans)" }}
          />

          <label
            style={{ display: "flex", gap: 10, alignItems: "flex-start", marginTop: 16 }}
          >
            <input
              type="checkbox"
              checked={agreed}
              onChange={(e) => setAgreed(e.target.checked)}
              style={{ width: 22, height: 22, marginTop: 3, flexShrink: 0 }}
            />
            <span style={{ fontWeight: 400, fontSize: "0.92rem" }}>
              上記の内容が他の参加者に表示されることに同意します（
              <a href="/privacy">プライバシーポリシー</a>）
            </span>
          </label>

          {error && (
            <p className="err" role="alert">
              {error}
            </p>
          )}
          <div className="btn-row">
            <button
              className="btn btn-outline"
              disabled={!agreed || !handle.trim() || loading}
              onClick={() => call("join")}
            >
              マッチングに参加する
            </button>
          </div>
        </div>
      )}

      {joined && (
        <div className="card">
          <p className="eyebrow story">参加しました</p>
          <p className="muted">
            おすすめ一覧に表示されるようになりました。掲載の停止をご希望の場合は、
            公式LINEからお知らせください。
          </p>
        </div>
      )}

      <p className="notice">
        表示される相性スコアは参考指標です。実際のやりとりは、
        お互いの同意のうえで慎重に進めてください。
      </p>
    </>
  );
}
