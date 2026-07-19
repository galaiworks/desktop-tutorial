"use client";
import type { Big5Scores } from "@/lib/types";

const AXES: { key: keyof Big5Scores; label: string }[] = [
  { key: "E", label: "外向性" },
  { key: "A", label: "協調性" },
  { key: "C", label: "勤勉性" },
  { key: "N", label: "情緒安定" },
  { key: "O", label: "開放性" },
];

// N（神経症傾向）は高いほど不安定なので、レーダー表示では「情緒安定＝100-N」に反転して見せる
function displayValue(key: keyof Big5Scores, scores: Big5Scores): number {
  return key === "N" ? 100 - scores.N : scores[key];
}

export default function RadarChart({
  scores,
  size = 280,
}: {
  scores: Big5Scores;
  size?: number;
}) {
  const cx = size / 2;
  const cy = size / 2;
  const r = size / 2 - 44;
  const n = AXES.length;

  const point = (i: number, radius: number) => {
    const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
    return [cx + radius * Math.cos(angle), cy + radius * Math.sin(angle)];
  };

  const rings = [0.25, 0.5, 0.75, 1];
  const dataPoints = AXES.map((a, i) => {
    const v = displayValue(a.key, scores) / 100;
    return point(i, r * v);
  });
  const dataPath =
    dataPoints.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ") + " Z";

  return (
    <svg
      viewBox={`0 0 ${size} ${size}`}
      width="100%"
      style={{ maxWidth: size, display: "block", margin: "0 auto" }}
      role="img"
      aria-label="ビッグファイブのレーダーチャート"
    >
      {rings.map((ring, ri) => {
        const pts = AXES.map((_, i) => point(i, r * ring));
        const d = pts.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x},${y}`).join(" ") + " Z";
        return <path key={ri} d={d} fill="none" stroke="#e6e1f7" strokeWidth={1} />;
      })}
      {AXES.map((_, i) => {
        const [x, y] = point(i, r);
        return <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke="#e6e1f7" strokeWidth={1} />;
      })}
      <path d={dataPath} fill="rgba(109,94,252,0.28)" stroke="#6d5efc" strokeWidth={2} />
      {dataPoints.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r={3.5} fill="#6d5efc" />
      ))}
      {AXES.map((a, i) => {
        const [x, y] = point(i, r + 26);
        return (
          <text
            key={a.key}
            x={x}
            y={y}
            fontSize={12}
            fontWeight={700}
            fill="#4a4763"
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
