"use client";
import { useMemo, useState } from "react";
import { lifePathFromISO } from "@/lib/numerology";
import { scoreTipi, ITEMS, TIPI } from "@/lib/tipi";
import { getNumberContent } from "@/lib/content";
import { fusionHeadline } from "@/lib/fusion";
import type { Big5Result, Lens, LifePath } from "@/lib/types";
import RadarChart from "@/components/RadarChart";

type Step = "birth" | "quiz" | "result";

const LINE_URL = process.env.NEXT_PUBLIC_LINE_ADD_URL || "";

export default function Diagnose() {
  const [step, setStep] = useState<Step>("birth");
  const [birth, setBirth] = useState("");
  const [lens, setLens] = useState<Lens>("romance");
  const [answers, setAnswers] = useState<number[]>(Array(ITEMS.length).fill(0));
  const [error, setError] = useState<string | null>(null);

  const [lifePath, setLifePath] = useState<LifePath | null>(null);
  const [big5, setBig5] = useState<Big5Result | null>(null);
  const [reading, setReading] = useState<string>("");
  const [loading, setLoading] = useState(false);

  const answered = answers.filter((a) => a > 0).length;
  const allAnswered = answered === ITEMS.length;

  function startQuiz() {
    setError(null);
    try {
      lifePathFromISO(birth); // 妥当性検証（実際の算出は結果画面で）
      setStep("quiz");
    } catch (e) {
      setError((e as Error).message);
    }
  }

  function setAnswer(i: number, v: number) {
    setAnswers((prev) => {
      const next = [...prev];
      next[i] = v;
      return next;
    });
  }

  async function submit() {
    setError(null);
    setLoading(true);
    try {
      const lp = lifePathFromISO(birth);
      const b5 = scoreTipi(answers);
      setLifePath(lp);
      setBig5(b5);
      setStep("result");

      const res = await fetch("/api/generate", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          self: { life_path: lp, big5: b5.scores },
          lens,
          mode: "self",
        }),
      });
      const data = await res.json();
      setReading(data.text ?? "");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  // LINE誘導URL（診断結果を引き継ぐパラメータ付き。§5.7）
  const lineHref = useMemo(() => {
    if (!lifePath || !big5) return LINE_URL || "#";
    const payload = {
      lp: lifePath,
      b5: big5.scores,
      lens,
      v: 1,
    };
    const token =
      typeof window !== "undefined"
        ? window.btoa(unescape(encodeURIComponent(JSON.stringify(payload))))
        : "";
    if (!LINE_URL) return "#";
    const sep = LINE_URL.includes("?") ? "&" : "?";
    return `${LINE_URL}${sep}numen=${encodeURIComponent(token)}`;
  }, [lifePath, big5, lens]);

  // ── 生年月日入力 ──
  if (step === "birth") {
    return (
      <div className="card">
        <h1>生年月日を教えてください</h1>
        <p className="muted">ライフパスナンバーの算出に使います。本名は不要です。</p>
        <label htmlFor="bd">生年月日</label>
        <input
          id="bd"
          type="date"
          value={birth}
          min="1900-01-01"
          max="2025-12-31"
          onChange={(e) => setBirth(e.target.value)}
        />

        <label style={{ marginTop: 18 }}>どちらのレンズで診断しますか？</label>
        <div className="lens-toggle">
          <button
            className={lens === "romance" ? "on" : ""}
            onClick={() => setLens("romance")}
            type="button"
          >
            💗 恋愛
          </button>
          <button
            className={lens === "business" ? "on" : ""}
            onClick={() => setLens("business")}
            type="button"
          >
            💼 ビジネス
          </button>
        </div>

        {error && <p className="err">{error}</p>}
        <button
          className="btn btn-primary"
          style={{ marginTop: 18 }}
          disabled={!birth}
          onClick={startQuiz}
        >
          次へ（10問の質問）
        </button>
      </div>
    );
  }

  // ── TIPI-J 10問 ──
  if (step === "quiz") {
    return (
      <div className="card">
        <div className="progress">
          <i style={{ width: `${(answered / ITEMS.length) * 100}%` }} />
        </div>
        <h2>あなた自身について（{answered}/{ITEMS.length}）</h2>
        <p className="muted">{TIPI.scale.stem}</p>

        {ITEMS.map((item, i) => (
          <div key={item.id} style={{ margin: "18px 0" }}>
            <div style={{ fontWeight: 700, fontSize: 15 }}>
              {i + 1}. {item.text}
            </div>
            <div className="likert" role="radiogroup" aria-label={item.text}>
              {[1, 2, 3, 4, 5, 6, 7].map((v) => (
                <button
                  key={v}
                  type="button"
                  className={answers[i] === v ? "on" : ""}
                  aria-checked={answers[i] === v}
                  role="radio"
                  onClick={() => setAnswer(i, v)}
                >
                  {v}
                </button>
              ))}
            </div>
            <div className="likert-ends">
              <span>全く違う</span>
              <span>強くそう思う</span>
            </div>
          </div>
        ))}

        {error && <p className="err">{error}</p>}
        <button
          className="btn btn-primary"
          disabled={!allAnswered || loading}
          onClick={submit}
        >
          {loading ? "診断中…" : "結果を見る"}
        </button>
        <button
          className="btn btn-ghost"
          style={{ marginTop: 8 }}
          type="button"
          onClick={() => setStep("birth")}
        >
          戻る
        </button>
      </div>
    );
  }

  // ── 結果 ──
  const content = lifePath ? getNumberContent(lifePath) : null;
  const headline = lifePath && big5 ? fusionHeadline(lifePath, big5.scores) : "";

  return (
    <>
      <div className="card center">
        <p className="muted">あなたのタイプ</p>
        <h1 style={{ color: "var(--brand)" }}>{headline}</h1>
        {content && (
          <p>
            {content.keywords.map((k) => (
              <span className="chip" key={k}>
                {k}
              </span>
            ))}
          </p>
        )}
      </div>

      {big5 && (
        <div className="card">
          <h2>あなたのビッグファイブ</h2>
          <p className="muted">心理学の五因子モデル（TIPI-J）による測定結果です。</p>
          <RadarChart scores={big5.scores} />
        </div>
      )}

      <div className="card">
        <h2>AIによる読み解き</h2>
        {loading ? (
          <p className="muted">あなただけの診断文を生成しています…</p>
        ) : (
          <p className="reading">{reading}</p>
        )}
      </div>

      {content && (
        <div className="card">
          <h2>もっと深く知る（フル鑑定）</h2>
          <div className="lock-wrap">
            <div className="locked">
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
                <b>{lens === "romance" ? "恋愛" : "適職"}：</b>
                {lens === "romance" ? content.love : content.work}
              </p>
              <p>
                <b>注意点：</b>
                {content.caution}
              </p>
            </div>
            <div className="lock-badge">🔒 続きは公式LINEで</div>
          </div>
          <p className="muted" style={{ marginTop: 12 }}>
            あなたのフル鑑定書と、
            {lens === "romance" ? "恋愛" : "ビジネス"}
            の相性診断・攻略は公式LINEでお届けします。
          </p>
          <a className="btn btn-line" href={lineHref}>
            LINEでフル鑑定を受け取る
          </a>
          {!LINE_URL && (
            <p className="muted" style={{ marginTop: 8 }}>
              （設定メモ：環境変数 <code>NEXT_PUBLIC_LINE_ADD_URL</code>{" "}
              に友だち追加URLを設定すると有効化されます）
            </p>
          )}
        </div>
      )}

      <button
        className="btn btn-ghost"
        onClick={() => {
          setStep("birth");
          setAnswers(Array(ITEMS.length).fill(0));
          setReading("");
        }}
      >
        もう一度診断する
      </button>

      <p className="notice">
        ※本診断は娯楽・自己理解を目的としたものであり、結果を保証するものではありません。
        {content?.disclaimer}
        <br />
        Big5尺度：小塩ら（2012）TIPI-J, パーソナリティ研究, 21, 40–52。
      </p>
    </>
  );
}
