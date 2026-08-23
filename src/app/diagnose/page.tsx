"use client";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { lifePathFromISO } from "@/lib/numerology";
import { scoreBig5, ITEMS, scaleFootnote } from "@/lib/big5Scale";
import { getPublicNumber, LOCKED_SECTIONS } from "@/lib/contentPublic";
import { fusionHeadline } from "@/lib/headline";
import { encodeCode, buildLineUrl, buildCompatibilityUrl } from "@/lib/share";
import { saveSelf } from "@/lib/storage";
import { track } from "@/lib/analytics";
import type { Big5Result, Big5Scores, Lens, LifePath } from "@/lib/types";
import RadarChart, { displayValue } from "@/components/RadarChart";
import Big5Quiz from "@/components/Big5Quiz";

type Step = "birth" | "quiz" | "result";

const LINE_URL = process.env.NEXT_PUBLIC_LINE_ADD_URL || "";

const AXIS_LABELS: { key: keyof Big5Scores; label: string }[] = [
  { key: "E", label: "外向性" },
  { key: "A", label: "協調性" },
  { key: "C", label: "勤勉性" },
  { key: "N", label: "情緒安定性" },
  { key: "O", label: "開放性" },
];

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
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    track("diagnosis_start");
  }, []);

  const answered = answers.filter((a) => a > 0).length;
  const allAnswered = answered === ITEMS.length;

  function startQuiz() {
    setError(null);
    try {
      lifePathFromISO(birth);
      track("birth_submitted", { lens });
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
      const b5 = scoreBig5(answers);
      setLifePath(lp);
      setBig5(b5);
      setStep("result");
      saveSelf({ life_path: lp, big5: b5.scores, lens });
      track("tipi_complete");
      track("result_view", { life_path: lp, lens });

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

  const code = useMemo(
    () => (lifePath && big5 ? encodeCode({ life_path: lifePath, big5: big5.scores }) : ""),
    [lifePath, big5]
  );

  const lineHref = useMemo(
    () => (code ? buildLineUrl(LINE_URL, code, lens) || "#" : LINE_URL || "#"),
    [code, lens]
  );

  async function copyCode() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      track("code_copy");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setError("コピーできませんでした。コードを長押しして選択してください。");
    }
  }

  async function share() {
    const content = lifePath ? getPublicNumber(lifePath) : null;
    const url =
      typeof window !== "undefined"
        ? buildCompatibilityUrl(window.location.origin, code)
        : "";
    const text = `私は「${fusionHeadline(lifePath!, big5!.scores)}」でした。あなたとの相性も見てみませんか？`;
    track("share_click");
    try {
      if (navigator.share) {
        await navigator.share({ title: "NUMEN 診断結果", text, url });
      } else {
        await navigator.clipboard.writeText(`${text}\n${url}`);
        setError(null);
        alert("共有リンクをコピーしました");
      }
    } catch {
      // ユーザーが共有をキャンセルした場合は何もしない
    }
  }

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
          <div className="lens-toggle" role="group" aria-labelledby="lens-label">
            <button
              type="button"
              aria-pressed={lens === "romance"}
              onClick={() => {
                setLens("romance");
                track("lens_switch", { lens: "romance", page: "diagnose" });
              }}
            >
              恋愛レンズ
            </button>
            <button
              type="button"
              aria-pressed={lens === "business"}
              onClick={() => {
                setLens("business");
                track("lens_switch", { lens: "business", page: "diagnose" });
              }}
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
          <button className="btn btn-primary" disabled={!birth} onClick={startQuiz}>
            次へ（10問の質問）
          </button>
        </div>
      </div>
    );
  }

  // ── ビッグファイブ10問 ──
  if (step === "quiz") {
    return (
      <div className="card science">
        <p className="eyebrow science">STEP 2 / 2 ・ ビッグファイブ</p>
        <Big5Quiz answers={answers} onAnswer={setAnswer} />

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
  const content = lifePath ? getPublicNumber(lifePath) : null;
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

      {/* 拡散導線（§12 シェア率） */}
      <div className="card">
        <p className="eyebrow story">相性を見る</p>
        <h2 className="serif">気になる人と、重ねてみる</h2>
        <p className="muted">
          あなたの診断コードです。相手に渡すか、リンクを共有すると相性を算出できます。
        </p>
        <div className="code-box">
          <code className="code-value">{code}</code>
          <button className="btn btn-outline code-copy" type="button" onClick={copyCode}>
            {copied ? "コピーしました" : "コードをコピー"}
          </button>
        </div>
        <div className="btn-row">
          <button className="btn btn-outline" type="button" onClick={share}>
            結果をシェアする
          </button>
          <Link href="/compatibility" className="btn btn-primary">
            相性診断へ進む
          </Link>
        </div>
      </div>

      {content && (
        <div className="card">
          <p className="eyebrow story">フル鑑定</p>
          <h2 className="serif">もっと深く知る</h2>
          <div className="lock-wrap">
            <ul className="locked-list">
              {LOCKED_SECTIONS.map((label) => (
                <li key={label}>
                  <span aria-hidden="true">🔒</span>
                  {label}
                </li>
              ))}
            </ul>
          </div>
          <p className="muted" style={{ marginTop: 14 }}>
            あなたのフル鑑定書と、
            {lens === "romance" ? "恋愛" : "ビジネス"}
            の相性診断・攻略は公式LINEでお届けします。
          </p>
          <div className="btn-row">
            <a
              className="btn btn-line"
              href={lineHref}
              onClick={() => track("line_cta_click", { from: "diagnose", lens })}
            >
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

      {error && (
        <p className="err" role="alert">
          {error}
        </p>
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
        <br />
        {scaleFootnote()}
      </p>
    </>
  );
}
