"use client";
import { useRef } from "react";

/**
 * アクセシブルな7件法リッカート。
 * WAI-ARIA の radiogroup パターン: 矢印キー移動 / Home / End、roving tabindex。
 */
export default function Likert({
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

  function focusValue(v: number) {
    requestAnimationFrame(() => {
      groupRef.current?.querySelector<HTMLElement>(`[data-v="${v}"]`)?.focus();
    });
  }

  function move(delta: number) {
    const current = value || 4;
    const next = Math.min(7, Math.max(1, current + delta));
    onChange(next);
    focusValue(next);
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
      focusValue(1);
    } else if (e.key === "End") {
      e.preventDefault();
      onChange(7);
      focusValue(7);
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
