"use client";
import { useState } from "react";
import { nameNumbers, NAME_CONFIG, type NameAspect } from "@/lib/name";
import { getPublicNumber } from "@/lib/contentPublic";
import type { LifePath } from "@/lib/types";

const ASPECTS: NameAspect[] = ["destiny", "soul", "personality"];

export default function NamePage() {
  const [input, setInput] = useState("");
  const [result, setResult] = useState<ReturnType<typeof nameNumbers> | null>(null);
  const [error, setError] = useState<string | null>(null);

  function calc() {
    setError(null);
    const r = nameNumbers(input);
    if (!r.destiny) {
      setError("ローマ字（英字）でお名前を入力してください。例：Taro Yamada");
      return;
    }
    setResult(r);
  }

  return (
    <>
      <div className="card story">
        <p className="eyebrow story">名前の数字</p>
        <h1 className="serif">名前が示す、3つの数</h1>
        <p className="muted">
          生年月日が「人生の道すじ」を示すのに対し、名前は「才能・本音・印象」を示すと
          考えられています。お名前をローマ字で入力してください。
        </p>

        <label htmlFor="nm" style={{ marginTop: 16 }}>
          お名前（ローマ字）
        </label>
        <p className="field-hint" id="nm-hint">
          例：Taro Yamada／ニックネームでも算出できます。入力内容は保存されません。
        </p>
        <input
          id="nm"
          type="text"
          value={input}
          placeholder="Taro Yamada"
          autoComplete="off"
          aria-describedby="nm-hint"
          onChange={(e) => setInput(e.target.value)}
        />
        {error && (
          <p className="err" role="alert">
            {error}
          </p>
        )}
        <div className="btn-row">
          <button className="btn btn-primary" disabled={!input.trim()} onClick={calc}>
            名前の数字を見る
          </button>
        </div>
      </div>

      {result &&
        ASPECTS.map((aspect) => {
          const n = result[aspect];
          const meta = NAME_CONFIG.aspects[aspect];
          if (!n) {
            return (
              <div className="card" key={aspect}>
                <p className="eyebrow story">{meta.label}</p>
                <p className="muted">
                  この綴りでは{meta.source}が見つからないため算出できませんでした。
                </p>
              </div>
            );
          }
          const c = getPublicNumber(n as LifePath);
          return (
            <div className="card" key={aspect}>
              <p className="eyebrow story">
                {meta.label}（{meta.source}）
              </p>
              <div style={{ textAlign: "center" }}>
                <div className="numeral" aria-hidden="true">
                  {n}
                </div>
                <p className="type-name">{c.keywords.join("・")}</p>
              </div>
              <p className="muted">{meta.meaning}</p>
            </div>
          );
        })}

      <p className="notice">
        名前の数字はピタゴラス式の文字対応（A=1…I=9, J=1…R=9, S=1…Z=8）で算出しています。
        本診断は娯楽・自己理解を目的としたもので、結果を保証するものではありません。
        入力されたお名前はサーバーに送信・保存されません（すべて端末内で計算しています）。
      </p>
    </>
  );
}
