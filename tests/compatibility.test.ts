import { describe, it, expect } from "vitest";
import {
  compatibility,
  numerologyAffinity,
  big5Compatibility,
} from "@/lib/compatibility";
import type { Big5Scores } from "@/lib/types";

const mid: Big5Scores = { E: 50, A: 50, C: 50, N: 50, O: 50 };

describe("numerologyAffinity", () => {
  it("returns 0-100", () => {
    const v = numerologyAffinity(1, 5, "romance");
    expect(v).toBeGreaterThanOrEqual(0);
    expect(v).toBeLessThanOrEqual(100);
  });
  it("same number is high", () => {
    expect(numerologyAffinity(1, 1, "romance")).toBeGreaterThanOrEqual(80);
  });
  it("is symmetric via averaging", () => {
    expect(numerologyAffinity(3, 8, "business")).toBe(
      numerologyAffinity(8, 3, "business")
    );
  });
});

describe("big5Compatibility", () => {
  it("similarity: identical profiles score high on similarity factors", () => {
    const { breakdown } = big5Compatibility(mid, mid, "romance");
    for (const b of breakdown) {
      if (b.mode === "similarity") expect(b.score).toBe(100);
      if (b.mode === "complementarity") expect(b.score).toBe(0);
    }
  });
  it("complementarity: opposite N scores high when complementary", () => {
    const a: Big5Scores = { ...mid, N: 10 };
    const b: Big5Scores = { ...mid, N: 90 };
    const { breakdown } = big5Compatibility(a, b, "romance");
    const nFactor = breakdown.find((x) => x.factor === "N")!;
    expect(nFactor.mode).toBe("complementarity");
    expect(nFactor.score).toBe(80);
  });
});

describe("compatibility (総合)", () => {
  it("combines numerology + big5 into 0-100", () => {
    const r = compatibility(
      { life_path: 11, big5: { E: 72, A: 40, C: 85, N: 30, O: 66 } },
      { life_path: 6, big5: { E: 55, A: 80, C: 60, N: 45, O: 50 } },
      "romance"
    );
    expect(r.totalScore).toBeGreaterThanOrEqual(0);
    expect(r.totalScore).toBeLessThanOrEqual(100);
    expect(r.breakdown.length).toBe(5);
    expect(r.lens).toBe("romance");
  });
  it("lens changes the result", () => {
    const self = { life_path: 3 as const, big5: mid };
    const target = { life_path: 8 as const, big5: { ...mid, E: 90 } };
    const rom = compatibility(self, target, "romance");
    const biz = compatibility(self, target, "business");
    expect(rom.totalScore).not.toBe(biz.totalScore);
  });
});
