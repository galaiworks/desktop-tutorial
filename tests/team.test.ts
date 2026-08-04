import { describe, it, expect } from "vitest";
import { teamCompatibility, type TeamMember } from "@/lib/team";
import { rankCandidates, type Candidate } from "@/lib/matching";
import type { Big5Scores } from "@/lib/types";

const mid: Big5Scores = { E: 50, A: 50, C: 50, N: 50, O: 50 };

const members: TeamMember[] = [
  { id: "a", name: "Aさん", life_path: 1, big5: { ...mid, C: 90, O: 80 } },
  { id: "b", name: "Bさん", life_path: 6, big5: { ...mid, A: 85, C: 70 } },
  { id: "c", name: "Cさん", life_path: 22, big5: { ...mid, E: 20, C: 88 } },
];

describe("teamCompatibility", () => {
  it("produces every unique pair (n choose 2)", () => {
    const r = teamCompatibility(members, "business");
    expect(r.pairs).toHaveLength(3); // 3C2
    expect(r.memberCount).toBe(3);
    const keys = r.pairs.map((p) => `${p.a}-${p.b}`);
    expect(new Set(keys).size).toBe(3);
  });

  it("scores stay within 0-100 and the average matches", () => {
    const r = teamCompatibility(members, "business");
    for (const p of r.pairs) {
      expect(p.score).toBeGreaterThanOrEqual(0);
      expect(p.score).toBeLessThanOrEqual(100);
    }
    const avg = Math.round(
      r.pairs.reduce((s, p) => s + p.score, 0) / r.pairs.length
    );
    expect(r.averageScore).toBe(avg);
  });

  it("identifies the strongest and weakest pair", () => {
    const r = teamCompatibility(members, "business");
    const scores = r.pairs.map((p) => p.score);
    expect(r.strongestPair?.score).toBe(Math.max(...scores));
    expect(r.weakestPair?.score).toBe(Math.min(...scores));
  });

  it("averages the team profile and measures spread", () => {
    const r = teamCompatibility(members, "business");
    expect(r.profile.C).toBe(Math.round((90 + 70 + 88) / 3));
    expect(r.diversity.C).toBeGreaterThan(0);
    // 全員同値の因子はばらつき 0
    expect(r.diversity.N).toBe(0);
  });

  it("always returns at least one interpretive note", () => {
    const r = teamCompatibility(members, "business");
    expect(r.notes.length).toBeGreaterThan(0);
  });

  it("requires two or more members", () => {
    expect(() => teamCompatibility([members[0]], "business")).toThrow();
  });

  it("changes with the lens", () => {
    const biz = teamCompatibility(members, "business").averageScore;
    const rom = teamCompatibility(members, "romance").averageScore;
    expect(biz).not.toBe(rom);
  });
});

describe("rankCandidates（マッチング）", () => {
  const candidates: Candidate[] = [
    { id: "x", handle: "みかん", life_path: 6, big5: mid },
    { id: "y", handle: "すだち", life_path: 3, big5: { ...mid, E: 95 } },
    { id: "z", handle: "ゆず", life_path: 9, big5: { ...mid, A: 90 } },
  ];
  const self = { id: "me", life_path: 11 as const, big5: mid };

  it("returns candidates sorted by score descending", () => {
    const r = rankCandidates(self, candidates, "romance");
    expect(r).toHaveLength(3);
    for (let i = 1; i < r.length; i++) {
      expect(r[i - 1].score).toBeGreaterThanOrEqual(r[i].score);
    }
  });

  it("respects the limit", () => {
    expect(rankCandidates(self, candidates, "romance", 2)).toHaveLength(2);
    expect(rankCandidates(self, candidates, "romance", 0)).toHaveLength(0);
  });

  it("excludes yourself from your own recommendations", () => {
    const withSelf = [...candidates, { id: "me", handle: "自分", life_path: 11 as const, big5: mid }];
    const r = rankCandidates(self, withSelf, "romance");
    expect(r.find((c) => c.id === "me")).toBeUndefined();
  });

  it("handles an empty candidate pool", () => {
    expect(rankCandidates(self, [], "business")).toEqual([]);
  });
});
