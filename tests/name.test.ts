import { describe, it, expect } from "vitest";
import {
  letterValue,
  isVowel,
  normalizeName,
  nameNumber,
  nameNumbers,
  type NameNumerologyConfig,
} from "@/lib/name";

describe("letterValue（ピタゴラス式）", () => {
  it("maps A-I to 1-9", () => {
    expect(letterValue("A")).toBe(1);
    expect(letterValue("I")).toBe(9);
  });
  it("wraps J-R to 1-9 and S-Z to 1-8", () => {
    expect(letterValue("J")).toBe(1);
    expect(letterValue("R")).toBe(9);
    expect(letterValue("S")).toBe(1);
    expect(letterValue("Z")).toBe(8);
  });
  it("is case-insensitive and ignores non-letters", () => {
    expect(letterValue("a")).toBe(1);
    expect(letterValue("-")).toBe(0);
    expect(letterValue("あ")).toBe(0);
  });
});

describe("isVowel", () => {
  it("treats AEIOU as vowels and Y as a consonant by default", () => {
    for (const v of ["A", "E", "I", "O", "U"]) expect(isVowel(v)).toBe(true);
    expect(isVowel("Y")).toBe(false);
    expect(isVowel("Y", true)).toBe(true);
  });
});

describe("normalizeName", () => {
  it("splits words and strips non-letters", () => {
    expect(normalizeName("Taro Yamada")).toEqual(["Taro", "Yamada"]);
    expect(normalizeName("O'Brien-Smith")).toEqual(["OBrienSmith"]);
  });
  it("accepts full-width letters and ideographic spaces", () => {
    expect(normalizeName("Ｔａｒｏ　Ｙａｍａｄａ")).toEqual(["Taro", "Yamada"]);
  });
  it("returns an empty list when there are no letters", () => {
    expect(normalizeName("山田太郎")).toEqual([]);
  });
});

describe("nameNumber", () => {
  // TARO = 2+1+9+6 = 18, YAMADA = 7+1+4+1+4+1 = 18 → 36 → 9
  it("computes the destiny number from all letters", () => {
    expect(nameNumber("Taro Yamada", "destiny")).toBe(9);
  });
  // 母音 A,O + A,A,A = 1+6+1+1+1 = 10 → 1
  it("computes the soul number from vowels only", () => {
    expect(nameNumber("Taro Yamada", "soul")).toBe(1);
  });
  // 子音 T,R + Y,M,D = 2+9+7+4+4 = 26 → 8
  it("computes the personality number from consonants only", () => {
    expect(nameNumber("Taro Yamada", "personality")).toBe(8);
  });
  it("keeps destiny = soul + personality consistent before reduction", () => {
    const r = nameNumbers("Taro Yamada");
    expect(r.destiny).toBe(9);
    expect(r.soul).toBe(1);
    expect(r.personality).toBe(8);
  });
  it("returns null for input with no usable letters", () => {
    expect(nameNumber("山田太郎", "destiny")).toBeNull();
    expect(nameNumber("", "destiny")).toBeNull();
  });
  it("returns null for soul when the spelling has no vowels", () => {
    expect(nameNumber("Rhythm", "soul")).toBeNull();
  });
  it("preserves master numbers", () => {
    // K(2)+E(5)+N(5) = 12; ANN = 1+5+5 = 11 → master
    expect(nameNumber("Ann", "destiny")).toBe(11);
  });
});

describe("設定による流派差", () => {
  const conf = (patch: Partial<NameNumerologyConfig>): NameNumerologyConfig =>
    ({
      treatYAsVowel: false,
      reductionMethod: "sum-all",
      aspects: {} as NameNumerologyConfig["aspects"],
      ...patch,
    }) as NameNumerologyConfig;

  it("treatYAsVowel moves Y between soul and personality", () => {
    const asConsonant = nameNumber("Taro Yamada", "soul", conf({}));
    const asVowel = nameNumber("Taro Yamada", "soul", conf({ treatYAsVowel: true }));
    expect(asVowel).not.toBe(asConsonant); // Y(7) が母音側に移る
  });

  it("reduce-each-word is available as an alternative", () => {
    const n = nameNumber("Taro Yamada", "destiny", conf({ reductionMethod: "reduce-each-word" }));
    // 18→9, 18→9 → 18 → 9
    expect(n).toBe(9);
  });
});
