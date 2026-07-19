import { describe, it, expect } from "vitest";
import { fallbackText, buildPrompt } from "@/lib/generate";
import { checkGuard, ensureDisclaimer } from "@/lib/guard";
import type { DiagnosisInput } from "@/lib/types";

const self: DiagnosisInput = {
  self: { life_path: 3, big5: { E: 20, A: 60, C: 55, N: 40, O: 80 } },
  lens: "romance",
  mode: "self",
};

const compat: DiagnosisInput = {
  self: { life_path: 11, big5: { E: 72, A: 40, C: 85, N: 30, O: 66 } },
  target: { life_path: 6, big5: { E: 55, A: 80, C: 60, N: 45, O: 50 } },
  lens: "business",
  mode: "compatibility",
};

describe("fallbackText", () => {
  it("self reading includes disclaimer and passes guard", () => {
    const t = fallbackText(self);
    expect(t).toContain("娯楽");
    expect(checkGuard(t).ok).toBe(true);
    // 外向性が低いので「静かな」ラベルが出る
    expect(t).toContain("静かな");
  });
  it("compatibility reading contains a computed score", () => {
    const t = fallbackText(compat);
    expect(t).toMatch(/相性: \d+点/);
    expect(checkGuard(t).ok).toBe(true);
  });
});

describe("buildPrompt", () => {
  it("self prompt embeds factual scores, not fabricated", () => {
    const p = buildPrompt(self);
    expect(p).toContain("ライフパス3");
    expect(p).toContain("創作しない");
  });
  it("compatibility prompt embeds computed total score", () => {
    const p = buildPrompt(compat);
    expect(p).toMatch(/総合相性: \d+点/);
  });
});

describe("guard", () => {
  it("flags banned phrases", () => {
    expect(checkGuard("これは必ず当たる占いです").ok).toBe(false);
    expect(checkGuard("100%成功します").ok).toBe(false);
  });
  it("passes safe text", () => {
    expect(checkGuard("あなたの傾向を穏やかに読み解きます").ok).toBe(true);
  });
  it("ensureDisclaimer is idempotent", () => {
    const once = ensureDisclaimer("本文");
    const twice = ensureDisclaimer(once);
    expect(once).toBe(twice);
  });
});
