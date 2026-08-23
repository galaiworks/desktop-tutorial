import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";
import { getPublicNumber, LOCKED_SECTIONS } from "@/lib/contentPublic";
import { getNumberContent } from "@/lib/content";

const NUMBERS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 22, 33] as const;
const PAID_FIELDS = ["essence", "mission", "strengths", "love", "work", "caution"] as const;

describe("公開データと有料データの分離（§8）", () => {
  it("公開データにはキーワードだけがあり、有料項目は含まれない", () => {
    for (const n of NUMBERS) {
      const pub = getPublicNumber(n) as unknown as Record<string, unknown>;
      expect(pub.keywords.length).toBeGreaterThan(0);
      for (const f of PAID_FIELDS) {
        expect(pub[f]).toBeUndefined();
      }
    }
  });

  it("公開データは元データと同期している（npm run gen:public 忘れの検出）", () => {
    for (const n of NUMBERS) {
      const pub = getPublicNumber(n);
      const full = getNumberContent(n);
      expect(pub.keywords).toEqual(full.keywords);
      expect(pub.number).toBe(full.number);
      expect(pub.isMaster).toBe(full.isMaster);
    }
  });

  it("ロック表示は見出しのみで、本文を持たない", () => {
    for (const label of LOCKED_SECTIONS) {
      expect(label.length).toBeLessThan(12); // 見出し語であって本文ではない
    }
  });
});

describe("クライアントコードが有料データを取り込んでいないこと", () => {
  const clientFiles = [
    "src/app/diagnose/page.tsx",
    "src/app/compatibility/page.tsx",
    "src/app/name/page.tsx",
    "src/app/liff/page.tsx",
    "src/components/RadarChart.tsx",
    "src/lib/headline.ts",
    "src/lib/contentPublic.ts",
  ];

  it("'use client' のファイルは content.ts / fusion.ts を import しない", () => {
    for (const f of clientFiles) {
      const src = fs.readFileSync(path.join(process.cwd(), f), "utf8");
      expect(src).not.toMatch(/from ["']@\/lib\/content["']/);
      expect(src).not.toMatch(/from ["']@\/lib\/fusion["']/);
    }
  });

  it("公開データJSONに有料項目が書き出されていない", () => {
    const raw = fs.readFileSync(
      path.join(process.cwd(), "data/numbers.public.json"),
      "utf8"
    );
    for (const f of PAID_FIELDS) {
      expect(raw).not.toContain(`"${f}"`);
    }
  });
});
