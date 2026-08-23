import { NextRequest, NextResponse } from "next/server";
import { generateDiagnosis } from "@/lib/generate";
import { compatibility } from "@/lib/compatibility";
import { recordDiagnosis, recordMatch } from "@/lib/persistence";
import type { Big5Key, Big5Scores, DiagnosisInput, LifePath } from "@/lib/types";

export const runtime = "nodejs";

const LIFEPATHS = new Set([1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 22, 33]);
const KEYS: Big5Key[] = ["E", "A", "C", "N", "O"];

function parsePerson(p: unknown): { life_path: LifePath; big5: Big5Scores } | null {
  if (!p || typeof p !== "object") return null;
  const o = p as Record<string, unknown>;
  const lp = Number(o.life_path);
  if (!LIFEPATHS.has(lp)) return null;
  const b = o.big5 as Record<string, unknown> | undefined;
  if (!b) return null;
  const big5 = {} as Big5Scores;
  for (const k of KEYS) {
    const v = Number(b[k]);
    if (!Number.isFinite(v) || v < 0 || v > 100) return null;
    big5[k] = Math.round(v);
  }
  return { life_path: lp as LifePath, big5 };
}

export async function POST(req: NextRequest) {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "JSONが不正です" }, { status: 400 });
  }
  const o = body as Record<string, unknown>;
  const self = parsePerson(o.self);
  if (!self) {
    return NextResponse.json({ error: "self データが不正です" }, { status: 400 });
  }
  const lens = o.lens === "business" ? "business" : "romance";
  const mode = o.mode === "compatibility" ? "compatibility" : "self";
  const depth = o.depth === "teaser" ? "teaser" : "full";
  const target = mode === "compatibility" ? parsePerson(o.target) : undefined;
  if (mode === "compatibility" && !target) {
    return NextResponse.json({ error: "target データが不正です" }, { status: 400 });
  }

  const input: DiagnosisInput = {
    self,
    target: target ?? undefined,
    lens,
    mode,
    depth,
  };

  // 相性スコアはエンジンが確定させる（AIには解説のみ任せる §5.5）
  const compat =
    mode === "compatibility" && target
      ? compatibility(self, target, lens)
      : undefined;

  const result = await generateDiagnosis(input);

  // 保存は待たない（失敗しても診断結果は返す §7）
  const persist =
    mode === "compatibility" && target && compat
      ? recordMatch({
          self_life_path: self.life_path,
          target_life_path: target.life_path,
          lens,
          score: compat.totalScore,
        })
      : recordDiagnosis({ life_path: self.life_path, big5: self.big5, lens });
  persist.catch(() => {});

  return NextResponse.json({ ...result, compatibility: compat });
}
