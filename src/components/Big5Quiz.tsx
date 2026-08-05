"use client";
import { ITEMS, SCALE } from "@/lib/big5Scale";
import Likert from "./Likert";

/**
 * ビッグファイブ10問の設問ブロック（自己診断／相性診断の相手入力で共用）。
 * 項目は config/big5_scale.json の active 尺度から供給される。
 * 設問は fieldset/legend で構造化し、回答は radiogroup として提供する。
 */
export default function Big5Quiz({
  answers,
  onAnswer,
  idPrefix = "q",
  stemNote,
}: {
  answers: number[];
  onAnswer: (index: number, value: number) => void;
  idPrefix?: string;
  stemNote?: string;
}) {
  const answered = answers.filter((a) => a > 0).length;

  return (
    <>
      <div className="progress" aria-hidden="true">
        <i style={{ width: `${(answered / ITEMS.length) * 100}%` }} />
      </div>
      <p className="progress-label" role="status" aria-live="polite">
        {answered} / {ITEMS.length} 問 回答済み
      </p>
      <p className="muted">
        {stemNote ?? SCALE.scale.stem}（1=全く違う 〜 7=強くそう思う）
      </p>

      {ITEMS.map((item, i) => {
        const legendId = `${idPrefix}-${item.id}`;
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
              onChange={(v) => onAnswer(i, v)}
            />
          </fieldset>
        );
      })}
    </>
  );
}
