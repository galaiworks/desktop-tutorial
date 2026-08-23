import { describe, it, expect } from "vitest";
import {
  personalYear,
  personalMonth,
  personalYearFromISO,
  getPersonalYearContent,
} from "@/lib/personalYear";

describe("personalYear", () => {
  it("sums birth month + birth day + target year and reduces to 1-9", () => {
    // 12月3日 + 2026 → (1+2) + (0+3) + (2+0+2+6) = 3+3+10 = 16 → 7
    expect(personalYear(12, 3, 2026)).toBe(7);
  });

  it("never returns a master number (year runs on a 9-year cycle)", () => {
    for (let m = 1; m <= 12; m++) {
      for (let d = 1; d <= 28; d++) {
        const v = personalYear(m, d, 2026);
        expect(v).toBeGreaterThanOrEqual(1);
        expect(v).toBeLessThanOrEqual(9);
      }
    }
  });

  it("advances by one each year and wraps 9 → 1", () => {
    const a = personalYear(12, 3, 2026);
    const b = personalYear(12, 3, 2027);
    expect(b).toBe(a === 9 ? 1 : a + 1);
  });

  it("reads the birth date from an ISO string", () => {
    expect(personalYearFromISO("1985-12-03", 2026)).toBe(7);
  });

  it("rejects a malformed date", () => {
    expect(() => personalYearFromISO("1985/12/03", 2026)).toThrow();
  });
});

describe("personalMonth", () => {
  it("adds the month to the personal year and reduces", () => {
    expect(personalMonth(7, 5)).toBe(3); // 12 → 3
    expect(personalMonth(1, 1)).toBe(2);
  });
});

describe("getPersonalYearContent", () => {
  it("has content for all nine years", () => {
    for (let n = 1; n <= 9; n++) {
      const c = getPersonalYearContent(n);
      expect(c.year).toBe(n);
      expect(c.theme).toBeTruthy();
      expect(c.dos.length).toBeGreaterThan(0);
      expect(c.donts.length).toBeGreaterThan(0);
    }
  });
  it("throws for an out-of-range year", () => {
    expect(() => getPersonalYearContent(11)).toThrow();
  });
});
