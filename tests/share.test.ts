import { describe, it, expect } from "vitest";
import {
  encodeCode,
  decodeCode,
  normalizeCode,
  buildLineUrl,
  buildCompatibilityUrl,
} from "@/lib/share";
import type { Big5Scores } from "@/lib/types";

const big5: Big5Scores = { E: 72, A: 40, C: 85, N: 30, O: 66 };

describe("encodeCode / decodeCode", () => {
  it("round-trips a payload", () => {
    const code = encodeCode({ life_path: 11, big5 });
    expect(code).toBe("N1-11-72-40-85-30-66");
    expect(decodeCode(code)).toEqual({ life_path: 11, big5 });
  });

  it("round-trips every valid life path", () => {
    for (const lp of [1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 22, 33] as const) {
      const decoded = decodeCode(encodeCode({ life_path: lp, big5 }));
      expect(decoded?.life_path).toBe(lp);
    }
  });

  it("clamps out-of-range scores when encoding", () => {
    const code = encodeCode({
      life_path: 1,
      big5: { E: 140, A: -20, C: 50, N: 50, O: 50 },
    });
    expect(code).toBe("N1-1-100-0-50-50-50");
  });
});

describe("decodeCode 入力の頑健さ", () => {
  it("accepts full-width characters and stray spaces (コピペ耐性)", () => {
    expect(decodeCode(" ｎ１－１１－７２－４０－８５－３０－６６ ")).toEqual({
      life_path: 11,
      big5,
    });
  });

  it("rejects malformed input instead of throwing", () => {
    expect(decodeCode("")).toBeNull();
    expect(decodeCode("hello")).toBeNull();
    expect(decodeCode("N1-11-72-40-85-30")).toBeNull(); // 桁不足
    expect(decodeCode("N2-11-72-40-85-30-66")).toBeNull(); // 未知バージョン
    expect(decodeCode("N1-10-72-40-85-30-66")).toBeNull(); // 10は不正なライフパス
    expect(decodeCode("N1-11-172-40-85-30-66")).toBeNull(); // スコア範囲外
    expect(decodeCode("N1-11-x-40-85-30-66")).toBeNull(); // 数値でない
  });
});

describe("normalizeCode", () => {
  it("uppercases and strips whitespace", () => {
    expect(normalizeCode(" n1-1-2-3-4-5-6 ")).toBe("N1-1-2-3-4-5-6");
  });
});

describe("URL builders", () => {
  it("appends the code to a LINE url without an existing query", () => {
    expect(buildLineUrl("https://lin.ee/abc", "N1-11-72-40-85-30-66", "romance")).toBe(
      "https://lin.ee/abc?numen=N1-11-72-40-85-30-66&lens=romance"
    );
  });
  it("appends with & when the url already has a query", () => {
    expect(buildLineUrl("https://lin.ee/abc?x=1", "N1-1-0-0-0-0-0")).toBe(
      "https://lin.ee/abc?x=1&numen=N1-1-0-0-0-0-0"
    );
  });
  it("returns empty string when no LINE url is configured", () => {
    expect(buildLineUrl("", "N1-1-0-0-0-0-0")).toBe("");
  });
  it("builds a compatibility share url", () => {
    expect(buildCompatibilityUrl("https://numen.app", "N1-11-72-40-85-30-66")).toBe(
      "https://numen.app/compatibility?with=N1-11-72-40-85-30-66"
    );
  });
});
