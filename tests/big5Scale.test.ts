import { describe, it, expect } from "vitest";
import { scoreBig5, applyReverse, ITEMS, SCALE, listScales } from "@/lib/big5Scale";

describe("applyReverse", () => {
  it("uses 8 - value for 1-7 scale", () => {
    expect(applyReverse(1)).toBe(7);
    expect(applyReverse(7)).toBe(1);
    expect(applyReverse(4)).toBe(4);
  });
});

describe("scoreBig5", () => {
  it("has 10 items", () => {
    expect(ITEMS.length).toBe(10);
  });

  it("all 4 (neutral) -> 50/100 on every factor", () => {
    const r = scoreBig5(Array(10).fill(4));
    for (const k of ["E", "A", "C", "N", "O"] as const) {
      expect(r.raw[k]).toBe(4);
      expect(r.scores[k]).toBe(50);
    }
  });

  it("normalizes 1..7 to 0..100", () => {
    const r = scoreBig5(Array(10).fill(7));
    // 逆転項目があるため、素の7ばかりだと各因子は正逆で相殺され中央付近になる
    for (const k of ["E", "A", "C", "N", "O"] as const) {
      expect(r.scores[k]).toBeGreaterThanOrEqual(0);
      expect(r.scores[k]).toBeLessThanOrEqual(100);
    }
  });

  it("reverse scoring works: high extraversion pattern", () => {
    // E: item1(正)=7, item6(逆)=1 -> 逆転後7、平均7 -> 100
    const a = [7, 4, 4, 4, 4, 1, 4, 4, 4, 4];
    const r = scoreBig5(a);
    expect(r.scores.E).toBe(100);
  });

  it("rejects wrong length", () => {
    expect(() => scoreBig5([1, 2, 3])).toThrow();
  });
  it("rejects out-of-range", () => {
    expect(() => scoreBig5([8, ...Array(9).fill(4)])).toThrow();
  });
});

describe("尺度アダプタ（§5.3 / §13-2）", () => {
  it("every registered scale is structurally valid", () => {
    for (const s of listScales()) {
      expect(s.items).toHaveLength(10);
      for (const f of ["E", "A", "C", "N", "O"] as const) {
        const items = s.items.filter((i) => i.factor === f);
        expect(items).toHaveLength(2); // 各因子2項目
        expect(items.filter((i) => i.reverse)).toHaveLength(1); // 正1・逆1
      }
      expect(s.scale.min).toBeLessThan(s.scale.max);
    }
  });

  it("the active scale must not ship placeholder item text", () => {
    for (const item of SCALE.items) {
      expect(item.placeholder ?? false).toBe(false);
      expect(item.text).not.toContain("要・公式項目文差替");
    }
  });

  it("an unvalidated scale must not claim a citation", () => {
    for (const s of listScales()) {
      if (!s.validated) expect(s.citation).toBeNull();
    }
  });

  it("scoring works identically across scales", () => {
    for (const s of listScales()) {
      const r = scoreBig5(Array(10).fill(4), s);
      for (const f of ["E", "A", "C", "N", "O"] as const) {
        expect(r.scores[f]).toBe(50);
      }
    }
  });
});
