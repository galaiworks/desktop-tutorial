"use client";
import { useId } from "react";
import type { Big5Scores } from "@/lib/types";

const AXES: { key: keyof Big5Scores; label: string }[] = [
  { key: "E", label: "外向性" },
  { key: "A", label: "協調性" },
  { key: "C", label: "勤勉性" },
  { key: "N", label: "情緒安定" },
  { key: "O", label: "開放性" },
];

// N（神経症傾向）は高いほど不安定なので、表示では「情緒安定＝100-N」に反転して見せる
export function displayValue(key: keyof Big5Scores, scores: Big5Scores): number {
  return key === "N" ? 100 - scores.N : scores[key];
}

export default function RadarChart({
  scores,
  size = 280,
}: {
  scores: Big5Scores;
  size?: number;
}) {
  const titleId = useId();
  const descId = useId();
  const cx = size / 2;
  const cy = size / 2;
  const r = size / 2 - 46;
  const n = AXES.length;

  const point = (i: number, radius: number) => {
    const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
    return [cx + radius * Math.cos(angle), cy + radius * Math.sin(angle)];
  };

  const rings = [0.25, 0.5, 0.75, 1];
  const dataPoints = AXES.map((a, i) => point(i, r * (displayValue(a.key, scores) / 100)));
  const dataPath =
    dataPoints
      .map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`)
      .join(" ") + " Z";

  const desc = AXES.map((a) => `${a.label}${displayValue(a.key, scores)}`).join("、");

  return (
    <svg
      viewBox={`0 0 ${size} ${size}`}
      width="100%"
      style={{ maxWidth: size, display: "block", margin: "4px auto 0", color: "var(--science)" }}
      role="img"
      aria-labelledby={`${titleId} ${descId}`}
    >
      <title id={titleId}>ビッグファイブのレーダーチャート</title>
      <desc id={descId}>各因子を0〜100で表示：{desc}（詳細は下の表を参照）</desc>
      {rings.map((ring, ri) => {
        const pts = AXES.map((_, i) => point(i, r * ring));
        const d = pts.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x},${y}`).join(" ") + " Z";
        return <path key={ri} d={d} fill="none" stroke="var(--hairline-strong)" strokeWidth={1} />;
      })}
      {AXES.map((_, i) => {
        const [x, y] = point(i, r);
        return <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke="var(--hairline)" strokeWidth={1} />;
      })}
      <path
        d={dataPath}
        fill="color-mix(in srgb, var(--science) 22%, transparent)"
        stroke="var(--science)"
        strokeWidth={2}
      />
      {dataPoints.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r={3.5} fill="var(--science)" />
      ))}
      {AXES.map((a, i) => {
        const [x, y] = point(i, r + 28);
        return (
          <text
            key={a.key}
            x={x}
            y={y}
            fontSize={12.5}
            fontWeight={700}
            fill="var(--ink-soft)"
            textAnchor="middle"
            dominantBaseline="middle"
          >
            {a.label}
          </text>
        );
      })}
    </svg>
  );
}
