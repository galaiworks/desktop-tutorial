"use client";
import { useMemo, useRef, useState } from "react";
import { lifePathFromISO } from "@/lib/numerology";
import { scoreTipi, ITEMS, TIPI } from "@/lib/tipi";
import { getNumberContent } from "@/lib/content";
import { fusionHeadline } from "@/lib/fusion";
import type { Big5Result, Big5Scores, Lens, LifePath } from "@/lib/types";
import RadarChart, { displayValue } from "@/components/RadarChart";

type Step = "birth" | "quiz" | "result";

const LINE_URL = process.env.NEXT_PUBLIC_LINE_ADD_URL || "";

const AXIS_LABELS: { key: keyof Big5Scores; label: string }[] = [
  { key: "E", label: "外向性" },
  { key: "A", label: "協調性" },
  { key: "C", label: "勤勉性" },
  { key: "N", label: "情緒安定性" },
  { key: "O", label: "開放性" },
];

/** アクセシブルな7件法リッカート（radiogroup / 矢印キー対応・roving tabindex） */
function Likert({
  name,
  value,
  onChange,
  labelledBy,
}: {
  name: string;
  value: number;
  onChange: (v: number) => void;
  labelledBy: string;
}) {
  const groupRef = useRef<HTMLDivElement>(null);

  function move(delta: number) {
    const current = value || 4;
    const next = Math.min(7, Math.max(1, current + delta));
    onChange(next);
    requestAnimationFrame(() => {
      const el = groupRef.current?.querySelector<HTMLElement>(
        `[data-v="${next}"]`
      );
      el?.focus();
    });
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowRight" || e.key === "ArrowDown") {
      e.preventDefault();
      move(1);
    } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
      e.preventDefault();
      move(-1);
    } else if (e.key === "Home") {
      e.preventDefault();
      onChange(1);
    } else if (e.key === "End") {
      e.preventDefault();
      onChange(7);
    }
  }

  return (
    <>
      <div
        className="likert"
        role="radiogroup"
        aria-labelledby={labelledBy}
        ref={groupRef}
        onKeyDown={onKeyDown}
      >
        {[1, 2, 3, 4, 5, 6, 7].map((v) => {
          const checked = value === v;
          // roving tabindex: 選択済み（無ければ中央4）だけをタブ順に入れる
          const tabbable = value ? checked : v === 4;
          return (
            <span
              key={v}
              className="opt"
              role="radio"
              data-v={v}
              aria-checked={checked}
              aria-label={`${name}: 7段階中 ${v}`}
              tabIndex={tabbable ? 0 : -1}
              onClick={() => onChange(v)}
              onKeyDown={(e) => {
                if (e.key === " " || e.key === "Enter") {
                  e.preventDefault();
                  onChange(v);
                }
              }}
            >
              {v}
            </span>
          );
        })}
      </div>
      <div className="likert-ends" aria-hidden="true">
        <span>全く違う</span>
        <span>強くそう思う</span>
      </div>
    </>
  );
}

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
      lifePathFromISO(birth);
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

  const lineHref = useMemo(() => {
    if (!lifePath || !big5) return LINE_URL || "#";
    const payload = { lp: lifePath, b5: big5.scores, lens, v: 1 };
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
      <div className="card story">
        <p className="eyebrow story">STEP 1 / 2 ・ 数秘</p>
        <h1 className="serif">生年月日を教えてください</h1>
        <label htmlFor="bd">生年月日</label>
        <p className="field-hint" id="bd-hint">
          ライフパスナンバーの算出に使います。本名は不要です。
        </p>
        <input
          id="bd"
          type="date"
          value={birth}
          min="1900-01-01"
          max="2025-12-31"
          aria-describedby="bd-hint"
          onChange={(e) => setBirth(e.target.value)}
        />

        <div style={{ marginTop: 22 }}>
          <p className="label" id="lens-label">
            どちらのレンズで読みますか？
          </p>
          <div
            className="lens-toggle"
            role="group"
            aria-labelledby="lens-label"
          >
            <button
              type="button"
              aria-pressed={lens === "romance"}
              onClick={() => setLens("romance")}
            >
              恋愛レンズ
            </button>
            <button
              type="button"
              aria-pressed={lens === "business"}
              onClick={() => setLens("business")}
            >
              ビジネスレンズ
            </button>
          </div>
        </div>

        {error && (
          <p className="err" role="alert" style={{ marginTop: 14 }}>
            {error}
          </p>
        )}
        <div className="btn-row">
          <button
            className="btn btn-primary"
            disabled={!birth}
            onClick={startQuiz}
          >
            次へ（10問の質問）
          </button>
        </div>
      </div>
    );
  }

  // ── TIPI-J 10問 ──
  if (step === "quiz") {
    return (
      <div className="card science">
        <p className="eyebrow science">STEP 2 / 2 ・ ビッグファイブ</p>
        <div className="progress" aria-hidden="true">
          <i style={{ width: `${(answered / ITEMS.length) * 100}%` }} />
        </div>
        <p className="progress-label" role="status" aria-live="polite">
          {answered} / {ITEMS.length} 問 回答済み
        </p>
        <p className="muted">{TIPI.scale.stem}（1=全く違う 〜 7=強くそう思う）</p>

        {ITEMS.map((item, i) => {
          const legendId = `q-${item.id}`;
          return (
            <fieldset key={item.id}>
              <legend id={legendId}>
                <span className="q-num" aria-hidden="true">
                  {i + 1}.
                </span>
                {item.text}
              </legend>
              <Likert
                name={`設問${i + 1}`}
                labelledBy={legendId}
                value={answers[i]}
                onChange={(v) => setAnswer(i, v)}
              />
            </fieldset>
          );
        })}

        {error && (
          <p className="err" role="alert">
            {error}
          </p>
        )}
        <div className="btn-row">
          <button
            className="btn btn-primary"
            disabled={!allAnswered || loading}
            onClick={submit}
          >
            {loading ? "診断中…" : "結果を見る"}
          </button>
          <button
            className="btn btn-outline"
            type="button"
            onClick={() => setStep("birth")}
          >
            戻る
          </button>
        </div>
      </div>
    );
  }

  // ── 結果 ──
  const content = lifePath ? getNumberContent(lifePath) : null;
  const headline = lifePath && big5 ? fusionHeadline(lifePath, big5.scores) : "";

  return (
    <>
      <div className="card story">
        <p className="eyebrow story">物語の入口 ・ あなたの数</p>
        {lifePath && (
          <div style={{ textAlign: "center" }}>
            <div className="numeral" aria-hidden="true">
              {lifePath}
            </div>
            <p className="type-name">{headline}</p>
          </div>
        )}
        {content && (
          <ul className="chips" style={{ justifyContent: "center", marginTop: 6 }}>
            {content.keywords.map((k) => (
              <li className="chip" key={k}>
                {k}
              </li>
            ))}
          </ul>
        )}
      </div>

      {big5 && (
        <div className="card science">
          <p className="eyebrow science">科学の裏づけ ・ ビッグファイブ</p>
          <h2>あなたの5因子</h2>
          <RadarChart scores={big5.scores} />
          <table className="score-table">
            <caption>各因子のスコア（0〜100）</caption>
            <thead>
              <tr>
                <th scope="col">因子</th>
                <th scope="col" style={{ textAlign: "right" }}>
                  スコア
                </th>
              </tr>
            </thead>
            <tbody>
              {AXIS_LABELS.map((a) => {
                const v = displayValue(a.key, big5.scores);
                return (
                  <tr key={a.key}>
                    <th scope="row" style={{ fontWeight: 600 }}>
                      {a.label}
                      <span className="meter" aria-hidden="true">
                        <i style={{ width: `${v}%` }} />
                      </span>
                    </th>
                    <td className="val">{v}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className="muted" style={{ marginTop: 10 }}>
            ※「情緒安定性」は神経症傾向スコアを反転して表示しています。
          </p>
        </div>
      )}

      <div className="card">
        <p className="eyebrow story" style={{ color: "var(--brass)" }}>
          AIの読み解き
        </p>
        <h2 className="serif">あなたのための一篇</h2>
        <div aria-live="polite" aria-busy={loading}>
          {loading ? (
            <p className="reading reading-loading">
              あなただけの診断文を生成しています…
            </p>
          ) : (
            <p className="reading">{reading}</p>
          )}
        </div>
      </div>

      {content && (
        <div className="card">
          <p className="eyebrow story">フル鑑定</p>
          <h2 className="serif">もっと深く知る</h2>
          <div className="lock-wrap">
            <div className="locked" aria-hidden="true">
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
            <p className="lock-badge">
              <span aria-hidden="true">🔒</span>
              続きは公式LINEで
            </p>
          </div>
          <p className="muted" style={{ marginTop: 14 }}>
            あなたのフル鑑定書と、
            {lens === "romance" ? "恋愛" : "ビジネス"}
            の相性診断・攻略は公式LINEでお届けします。
          </p>
          <div className="btn-row">
            <a className="btn btn-line" href={lineHref}>
              LINEでフル鑑定を受け取る
            </a>
          </div>
          {!LINE_URL && (
            <p className="muted" style={{ marginTop: 10 }}>
              （設定メモ：環境変数 <code>NEXT_PUBLIC_LINE_ADD_URL</code>{" "}
              に友だち追加URLを設定すると有効化されます）
            </p>
          )}
        </div>
      )}

      <div className="btn-row">
        <button
          className="btn btn-outline"
          onClick={() => {
            setStep("birth");
            setAnswers(Array(ITEMS.length).fill(0));
            setReading("");
          }}
        >
          もう一度診断する
        </button>
      </div>

      <p className="notice">
        本診断は娯楽・自己理解を目的としたもので、結果を保証するものではありません。
        {content?.disclaimer}
        <br />
        Big5尺度：小塩ら（2012）TIPI-J, パーソナリティ研究, 21, 40–52。
      </p>
    </>
  );
}
