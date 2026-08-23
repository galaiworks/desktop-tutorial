"use client";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { lifePathFromISO } from "@/lib/numerology";
import { scoreBig5, ITEMS } from "@/lib/big5Scale";
import { getPublicNumber } from "@/lib/contentPublic";
import { decodeCode, encodeCode, buildLineUrl } from "@/lib/share";
import { loadSelf } from "@/lib/storage";
import { track } from "@/lib/analytics";
import type { CompatibilityResult, Lens, Person } from "@/lib/types";
import Big5Quiz from "@/components/Big5Quiz";

type Step = "setup" | "target-quiz" | "result";
type TargetMode = "code" | "quiz";

const LINE_URL = process.env.NEXT_PUBLIC_LINE_ADD_URL || "";

export default function Compatibility() {
  const [step, setStep] = useState<Step>("setup");
  const [self, setSelf] = useState<Person | null>(null);
  const [target, setTarget] = useState<Person | null>(null);
  const [lens, setLens] = useState<Lens>("romance");

  const [targetMode, setTargetMode] = useState<TargetMode>("code");
  const [codeInput, setCodeInput] = useState("");
  const [targetBirth, setTargetBirth] = useState("");
  const [answers, setAnswers] = useState<number[]>(Array(ITEMS.length).fill(0));

  const [result, setResult] = useState<CompatibilityResult | null>(null);
  const [reading, setReading] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 自分の結果はローカル保存から復元。URLパラメータでの受け渡しにも対応（§5.7）
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const stored = loadSelf();
    const selfFromUrl = decodeCode(params.get("self") ?? "");
    const fromUrl = selfFromUrl ?? null;
    if (fromUrl) {
      setSelf(fromUrl);
    } else if (stored) {
      setSelf({ life_path: stored.life_path, big5: stored.big5 });
      setLens(stored.lens);
    }
    // 「この人と相性を見る」リンク経由なら、相手のコードが入っている
    const withCode = decodeCode(params.get("with") ?? "");
    if (withCode) {
      setTarget(withCode);
      setCodeInput(encodeCode(withCode));
    }
    track("compatibility_start", { has_self: Boolean(fromUrl ?? stored) });
  }, []);

  function applyCode() {
    setError(null);
    const decoded = decodeCode(codeInput);
    if (!decoded) {
      setError("診断コードの形式が正しくありません。例：N1-11-72-40-85-30-66");
      return;
    }
    setTarget(decoded);
  }

  function setAnswer(i: number, v: number) {
    setAnswers((prev) => {
      const next = [...prev];
      next[i] = v;
      return next;
    });
  }

  function finishTargetQuiz() {
    setError(null);
    try {
      const lp = lifePathFromISO(targetBirth);
      const b5 = scoreBig5(answers);
      setTarget({ life_path: lp, big5: b5.scores });
      setStep("setup");
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function submit() {
    if (!self || !target) return;
    setError(null);
    setLoading(true);
    setStep("result");
    try {
      const res = await fetch("/api/generate", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          self,
          target,
          lens,
          mode: "compatibility",
          depth: "teaser", // 無料は「答えの一歩手前」まで（§8）
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? "診断に失敗しました");
      setResult(data.compatibility ?? null);
      setReading(data.text ?? "");
      track("compatibility_result_view", {
        lens,
        score: data.compatibility?.totalScore,
      });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  const lineHref = useMemo(() => {
    if (!self) return LINE_URL || "#";
    return buildLineUrl(LINE_URL, encodeCode(self), lens) || "#";
  }, [self, lens]);

  // ── 相手の10問を代理回答 ──
  if (step === "target-quiz") {
    const allAnswered = answers.filter((a) => a > 0).length === ITEMS.length;
    return (
      <div className="card science">
        <p className="eyebrow science">お相手について</p>
        <h1 className="serif">お相手の10問</h1>
        <p className="muted">
          お相手ご本人に回答してもらうのが理想です。端末を渡すか、
          お相手の診断コードを使う方法もあります。
        </p>

        <label htmlFor="tb" style={{ marginTop: 18 }}>
          お相手の生年月日
        </label>
        <input
          id="tb"
          type="date"
          value={targetBirth}
          min="1900-01-01"
          max="2025-12-31"
          onChange={(e) => setTargetBirth(e.target.value)}
        />

        <div style={{ marginTop: 22 }}>
          <Big5Quiz
            answers={answers}
            onAnswer={setAnswer}
            idPrefix="tq"
            stemNote="お相手は自分自身のことを…"
          />
        </div>

        {error && (
          <p className="err" role="alert">
            {error}
          </p>
        )}
        <div className="btn-row">
          <button
            className="btn btn-primary"
            disabled={!allAnswered || !targetBirth}
            onClick={finishTargetQuiz}
          >
            この内容で決定
          </button>
          <button
            className="btn btn-outline"
            type="button"
            onClick={() => setStep("setup")}
          >
            戻る
          </button>
        </div>
      </div>
    );
  }

  // ── 結果 ──
  if (step === "result") {
    const sc = self ? getPublicNumber(self.life_path) : null;
    const tc = target ? getPublicNumber(target.life_path) : null;
    return (
      <>
        <div className="card story">
          <p className="eyebrow story">
            {lens === "romance" ? "恋愛レンズ" : "ビジネスレンズ"} ・ 相性
          </p>
          <div aria-live="polite" aria-busy={loading}>
            {loading || !result ? (
              <p className="reading reading-loading">相性を算出しています…</p>
            ) : (
              <>
                <div className="score-hero">
                  <span className="score-hero-num">{result.totalScore}</span>
                  <span className="score-hero-unit">点</span>
                </div>
                {sc && tc && (
                  <p className="center muted">
                    ライフパス{sc.number}（{sc.keywords[0]}） × ライフパス
                    {tc.number}（{tc.keywords[0]}）
                  </p>
                )}
                <table className="score-table" style={{ marginTop: 18 }}>
                  <caption>相性の内訳（0〜100）</caption>
                  <tbody>
                    <tr>
                      <th scope="row">
                        数秘の相性
                        <span className="meter story" aria-hidden="true">
                          <i style={{ width: `${result.numerologyScore}%` }} />
                        </span>
                      </th>
                      <td className="val">{result.numerologyScore}</td>
                    </tr>
                    <tr>
                      <th scope="row">
                        性格（Big5）の相性
                        <span className="meter" aria-hidden="true">
                          <i style={{ width: `${result.big5Score}%` }} />
                        </span>
                      </th>
                      <td className="val">{result.big5Score}</td>
                    </tr>
                  </tbody>
                </table>
              </>
            )}
          </div>
        </div>

        {!loading && reading && (
          <div className="card">
            <p className="eyebrow story" style={{ color: "var(--brass)" }}>
              AIの読み解き（さわり）
            </p>
            <p className="reading">{reading}</p>
          </div>
        )}

        <div className="card">
          <p className="eyebrow story">フル相性鑑定</p>
          <h2 className="serif">続きは公式LINEで</h2>
          <p className="muted">
            2人が噛み合う場面・すれ違いやすい場面、そして
            {lens === "romance" ? "距離を縮める" : "協働をうまく進める"}
            具体的な進め方は、公式LINEでお届けします。
          </p>
          <div className="btn-row">
            <a
              className="btn btn-line"
              href={lineHref}
              onClick={() => track("line_cta_click", { from: "compatibility", lens })}
            >
              LINEでフル相性鑑定を受け取る
            </a>
            <button
              className="btn btn-outline"
              type="button"
              onClick={() => {
                setStep("setup");
                setResult(null);
                setReading("");
              }}
            >
              条件を変えて診断する
            </button>
          </div>
        </div>

        {error && (
          <p className="err" role="alert">
            {error}
          </p>
        )}

        <p className="notice">
          相性スコアはエンジンが算出した参考指標です。本診断は娯楽・自己理解を目的としたもので、
          人間関係の判断を保証・代替するものではありません。
        </p>
      </>
    );
  }

  // ── セットアップ ──
  return (
    <>
      <div className="card story">
        <p className="eyebrow story">2人の相性</p>
        <h1 className="serif">相性を見る</h1>
        <p className="muted">
          数秘の相性と、ビッグファイブの相性。2つを合わせて算出します。
        </p>
      </div>

      <div className="card">
        <h2>1. あなた</h2>
        {self ? (
          <p>
            <span className="chip">ライフパス{self.life_path}</span>
            <span className="muted" style={{ marginLeft: 8 }}>
              診断済みの結果を使います
            </span>
          </p>
        ) : (
          <>
            <p className="muted">
              先に無料の自己診断（約2分）を済ませると、ここに自動で反映されます。
            </p>
            <div className="btn-row">
              <Link href="/diagnose" className="btn btn-primary">
                自己診断をする
              </Link>
            </div>
          </>
        )}
      </div>

      <div className="card">
        <h2>2. お相手</h2>
        {target ? (
          <p>
            <span className="chip">ライフパス{target.life_path}</span>
            <button
              className="linkish"
              type="button"
              onClick={() => {
                setTarget(null);
                setCodeInput("");
              }}
            >
              入力し直す
            </button>
          </p>
        ) : (
          <>
            <div className="lens-toggle" role="group" aria-label="お相手の入力方法">
              <button
                type="button"
                aria-pressed={targetMode === "code"}
                onClick={() => setTargetMode("code")}
              >
                診断コードを貼る
              </button>
              <button
                type="button"
                aria-pressed={targetMode === "quiz"}
                onClick={() => setTargetMode("quiz")}
              >
                その場で答える
              </button>
            </div>

            {targetMode === "code" ? (
              <div style={{ marginTop: 16 }}>
                <label htmlFor="code">お相手の診断コード</label>
                <p className="field-hint" id="code-hint">
                  お相手の結果画面に表示されるコードです（例：N1-11-72-40-85-30-66）
                </p>
                <input
                  id="code"
                  type="text"
                  inputMode="text"
                  autoComplete="off"
                  placeholder="N1-11-72-40-85-30-66"
                  aria-describedby="code-hint"
                  value={codeInput}
                  onChange={(e) => setCodeInput(e.target.value)}
                />
                <div className="btn-row">
                  <button className="btn btn-outline" type="button" onClick={applyCode}>
                    コードを読み込む
                  </button>
                </div>
              </div>
            ) : (
              <div style={{ marginTop: 16 }}>
                <p className="muted">
                  お相手の生年月日と10問に、この端末で回答します。
                </p>
                <div className="btn-row">
                  <button
                    className="btn btn-outline"
                    type="button"
                    onClick={() => setStep("target-quiz")}
                  >
                    お相手の入力へ進む
                  </button>
                </div>
              </div>
            )}
          </>
        )}
        {error && (
          <p className="err" role="alert">
            {error}
          </p>
        )}
      </div>

      <div className="card">
        <h2>3. どちらのレンズで見る？</h2>
        <div className="lens-toggle" role="group" aria-label="診断のレンズ">
          <button
            type="button"
            aria-pressed={lens === "romance"}
            onClick={() => {
              setLens("romance");
              track("lens_switch", { lens: "romance", page: "compatibility" });
            }}
          >
            恋愛レンズ
          </button>
          <button
            type="button"
            aria-pressed={lens === "business"}
            onClick={() => {
              setLens("business");
              track("lens_switch", { lens: "business", page: "compatibility" });
            }}
          >
            ビジネスレンズ
          </button>
        </div>
        <div className="btn-row">
          <button
            className="btn btn-primary"
            disabled={!self || !target || loading}
            onClick={submit}
          >
            相性を診断する
          </button>
        </div>
        {(!self || !target) && (
          <p className="muted" style={{ marginTop: 10 }}>
            {!self ? "あなたの診断結果" : "お相手の情報"}が未入力です。
          </p>
        )}
      </div>
    </>
  );
}
