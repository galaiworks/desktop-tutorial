"use client";
import { useState } from "react";
import { lifePathFromISO } from "@/lib/numerology";
import { decodeCode } from "@/lib/share";
import type { Big5Scores, LifePath, Lens } from "@/lib/types";
import type { TeamResult } from "@/lib/team";

interface Draft {
  name: string;
  code: string;
}

const FACTOR_LABELS: { key: keyof Big5Scores; label: string }[] = [
  { key: "E", label: "外向性" },
  { key: "A", label: "協調性" },
  { key: "C", label: "勤勉性" },
  { key: "N", label: "情緒の波" },
  { key: "O", label: "開放性" },
];

export default function TeamPage() {
  const [drafts, setDrafts] = useState<Draft[]>([
    { name: "", code: "" },
    { name: "", code: "" },
  ]);
  const [lens, setLens] = useState<Lens>("business");
  const [result, setResult] = useState<TeamResult | null>(null);
  const [reading, setReading] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function update(i: number, patch: Partial<Draft>) {
    setDrafts((prev) => prev.map((d, idx) => (idx === i ? { ...d, ...patch } : d)));
  }

  function addMember() {
    if (drafts.length >= 20) return;
    setDrafts((prev) => [...prev, { name: "", code: "" }]);
  }

  function removeMember(i: number) {
    setDrafts((prev) => prev.filter((_, idx) => idx !== i));
  }

  async function submit() {
    setError(null);
    const members: {
      id: string;
      name: string;
      life_path: LifePath;
      big5: Big5Scores;
    }[] = [];

    for (const [i, d] of drafts.entries()) {
      const decoded = decodeCode(d.code);
      if (!decoded) {
        setError(`${i + 1}人目の診断コードが正しくありません（例：N1-11-72-40-85-30-66）`);
        return;
      }
      members.push({
        id: `m${i}`,
        name: d.name.trim() || `メンバー${i + 1}`,
        life_path: decoded.life_path,
        big5: decoded.big5,
      });
    }

    setLoading(true);
    try {
      const res = await fetch("/api/team", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ members, lens }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? "算出に失敗しました");
      setResult(data.team);
      setReading(data.text ?? "");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <div className="card science">
        <p className="eyebrow science">法人向け</p>
        <h1 className="serif">チーム相性</h1>
        <p className="muted">
          メンバーの診断コードを入力すると、総当たりの相性とチーム全体の傾向を算出します。
          各メンバーには先に無料診断を受けてもらい、結果画面のコードを共有してもらってください。
        </p>

        {drafts.map((d, i) => (
          <fieldset key={i} style={{ marginTop: 18 }}>
            <legend>{i + 1}人目</legend>
            <label htmlFor={`n${i}`} className="sr-only">
              {i + 1}人目の表示名
            </label>
            <input
              id={`n${i}`}
              type="text"
              placeholder="表示名（例：田中）"
              value={d.name}
              onChange={(e) => update(i, { name: e.target.value })}
              style={{ fontFamily: "var(--sans)", marginBottom: 8 }}
            />
            <label htmlFor={`c${i}`} className="sr-only">
              {i + 1}人目の診断コード
            </label>
            <input
              id={`c${i}`}
              type="text"
              placeholder="N1-11-72-40-85-30-66"
              value={d.code}
              onChange={(e) => update(i, { code: e.target.value })}
            />
            {drafts.length > 2 && (
              <button
                className="linkish"
                type="button"
                onClick={() => removeMember(i)}
                style={{ marginTop: 6 }}
              >
                この行を削除
              </button>
            )}
          </fieldset>
        ))}

        <div className="btn-row">
          <button className="btn btn-outline" type="button" onClick={addMember}>
            メンバーを追加（{drafts.length}/20）
          </button>
        </div>

        <p className="label" style={{ marginTop: 20 }} id="team-lens">
          見る観点
        </p>
        <div className="lens-toggle" role="group" aria-labelledby="team-lens">
          <button
            type="button"
            aria-pressed={lens === "business"}
            onClick={() => setLens("business")}
          >
            ビジネス
          </button>
          <button
            type="button"
            aria-pressed={lens === "romance"}
            onClick={() => setLens("romance")}
          >
            プライベート
          </button>
        </div>

        {error && (
          <p className="err" role="alert">
            {error}
          </p>
        )}
        <div className="btn-row">
          <button className="btn btn-primary" disabled={loading} onClick={submit}>
            {loading ? "算出中…" : "チーム相性を算出する"}
          </button>
        </div>
      </div>

      {result && (
        <>
          <div className="card story">
            <p className="eyebrow story">チーム全体</p>
            <div className="score-hero">
              <span className="score-hero-num">{result.averageScore}</span>
              <span className="score-hero-unit">点</span>
            </div>
            <p className="center muted">{result.memberCount}名の平均相性</p>
          </div>

          <div className="card science">
            <p className="eyebrow science">ペア別</p>
            <table className="score-table">
              <caption>総当たりの相性（0〜100）</caption>
              <thead>
                <tr>
                  <th scope="col">組み合わせ</th>
                  <th scope="col" style={{ textAlign: "right" }}>
                    スコア
                  </th>
                </tr>
              </thead>
              <tbody>
                {[...result.pairs]
                  .sort((a, b) => b.score - a.score)
                  .map((p) => (
                    <tr key={`${p.a}-${p.b}`}>
                      <th scope="row" style={{ fontWeight: 600 }}>
                        {p.aName} × {p.bName}
                        <span className="meter" aria-hidden="true">
                          <i style={{ width: `${p.score}%` }} />
                        </span>
                      </th>
                      <td className="val">{p.score}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>

          <div className="card science">
            <p className="eyebrow science">チームの傾向</p>
            <table className="score-table">
              <caption>平均プロファイルと、メンバー間のばらつき</caption>
              <thead>
                <tr>
                  <th scope="col">因子</th>
                  <th scope="col" style={{ textAlign: "right" }}>
                    平均
                  </th>
                  <th scope="col" style={{ textAlign: "right" }}>
                    ばらつき
                  </th>
                </tr>
              </thead>
              <tbody>
                {FACTOR_LABELS.map((f) => (
                  <tr key={f.key}>
                    <th scope="row" style={{ fontWeight: 600 }}>
                      {f.label}
                    </th>
                    <td className="val">{result.profile[f.key]}</td>
                    <td className="val">{result.diversity[f.key]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="card">
            <p className="eyebrow story" style={{ color: "var(--brass)" }}>
              相互理解レポート
            </p>
            <p className="reading">{reading}</p>
          </div>
        </>
      )}

      <p className="notice">
        本機能は<b>相互理解を目的とした参考情報</b>です。性格特性に優劣はありません。
        採用選考・人事評価の唯一の判断根拠として用いないでください（
        <a href="/terms">ご利用にあたって</a>）。
      </p>
    </>
  );
}
