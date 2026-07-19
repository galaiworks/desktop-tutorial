import { describe, it, expect } from "vitest";
import { scoreTipi, applyReverse, ITEMS } from "@/lib/tipi";

describe("applyReverse", () => {
  it("uses 8 - value for 1-7 scale", () => {
    expect(applyReverse(1)).toBe(7);
    expect(applyReverse(7)).toBe(1);
    expect(applyReverse(4)).toBe(4);
  });
});

describe("scoreTipi", () => {
  it("has 10 items", () => {
    expect(ITEMS.length).toBe(10);
  });

  it("all 4 (neutral) -> 50/100 on every factor", () => {
    const r = scoreTipi(Array(10).fill(4));
    for (const k of ["E", "A", "C", "N", "O"] as const) {
      expect(r.raw[k]).toBe(4);
      expect(r.scores[k]).toBe(50);
    }
  });

  it("normalizes 1..7 to 0..100", () => {
    const r = scoreTipi(Array(10).fill(7));
    // 逆転項目があるため、素の7ばかりだと各因子は正逆で相殺され中央付近になる
    for (const k of ["E", "A", "C", "N", "O"] as const) {
      expect(r.scores[k]).toBeGreaterThanOrEqual(0);
      expect(r.scores[k]).toBeLessThanOrEqual(100);
    }
  });

  it("reverse scoring works: high extraversion pattern", () => {
    // E: item1(正)=7, item6(逆)=1 -> 逆転後7、平均7 -> 100
    const a = [7, 4, 4, 4, 4, 1, 4, 4, 4, 4];
    const r = scoreTipi(a);
    expect(r.scores.E).toBe(100);
  });

  it("rejects wrong length", () => {
    expect(() => scoreTipi([1, 2, 3])).toThrow();
  });
  it("rejects out-of-range", () => {
    expect(() => scoreTipi([8, ...Array(9).fill(4)])).toThrow();
  });
});
