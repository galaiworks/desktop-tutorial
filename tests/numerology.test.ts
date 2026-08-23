import { describe, it, expect } from "vitest";
import {
  digitSum,
  reduceNumber,
  lifePath,
  lifePathFromISO,
  masterSet,
} from "@/lib/numerology";

describe("digitSum", () => {
  it("sums digits", () => {
    expect(digitSum(1985)).toBe(23);
    expect(digitSum(29)).toBe(11);
    expect(digitSum(0)).toBe(0);
  });
});

describe("reduceNumber", () => {
  it("reduces to single digit", () => {
    expect(reduceNumber(28)).toBe(1); // 28 -> 10 -> 1
    expect(reduceNumber(9)).toBe(9);
  });
  it("stops at master numbers", () => {
    expect(reduceNumber(29)).toBe(11); // 29 -> 11 (master, stop)
    expect(reduceNumber(11)).toBe(11);
    expect(reduceNumber(22)).toBe(22);
    expect(reduceNumber(33)).toBe(33);
  });
});

describe("lifePath — 要件定義書の例", () => {
  it("1985-12-03 -> 11 (master, stop)", () => {
    // 1+9+8+5 + 1+2 + 0+3 = 29 -> 2+9 = 11
    expect(lifePath(1985, 12, 3)).toBe(11);
    expect(lifePathFromISO("1985-12-03")).toBe(11);
  });
  it("1990-07-20 -> 1", () => {
    // 1+9+9+0 + 0+7 + 2+0 = 28 -> 10 -> 1
    expect(lifePath(1990, 7, 20)).toBe(1);
    expect(lifePathFromISO("1990-07-20")).toBe(1);
  });
});

describe("masterSet default (33含む=12種)", () => {
  it("includes 11,22,33 but not 44 by default", () => {
    const s = masterSet();
    expect(s.has(11)).toBe(true);
    expect(s.has(22)).toBe(true);
    expect(s.has(33)).toBe(true);
    expect(s.has(44)).toBe(false);
  });
});

describe("reduce-each-pillar 方式", () => {
  it("differs from sum-all when appropriate", () => {
    const cfg = {
      masterNumbers: { include11: true, include22: true, include33: true, include44: false },
      reductionMethod: "reduce-each-pillar" as const,
    };
    // 年:1985->23->5, 月:12->3, 日:03->3 => 5+3+3=11 (master)
    expect(lifePath(1985, 12, 3, cfg)).toBe(11);
  });
});

describe("入力検証", () => {
  it("rejects bad format", () => {
    expect(() => lifePathFromISO("1985/12/03")).toThrow();
  });
  it("rejects impossible date", () => {
    expect(() => lifePathFromISO("2023-02-30")).toThrow();
  });
});
