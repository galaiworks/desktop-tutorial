import { NextRequest, NextResponse } from "next/server";
import { teamCompatibility, type TeamMember } from "@/lib/team";
import { generateTeamReading } from "@/lib/generate";
import type { Big5Key, Big5Scores, LifePath } from "@/lib/types";

export const runtime = "nodejs";

const LIFEPATHS = new Set([1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 22, 33]);
const KEYS: Big5Key[] = ["E", "A", "C", "N", "O"];
const MAX_MEMBERS = 20;

function parseMember(m: unknown, index: number): TeamMember | null {
  if (!m || typeof m !== "object") return null;
  const o = m as Record<string, unknown>;
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
  const name = typeof o.name === "string" && o.name.trim() ? o.name.trim().slice(0, 40) : `メンバー${index + 1}`;
  const id = typeof o.id === "string" && o.id ? o.id : `m${index}`;
  return { id, name, life_path: lp as LifePath, big5 };
}

export async function POST(req: NextRequest) {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "JSONが不正です" }, { status: 400 });
  }
  const o = body as Record<string, unknown>;
  const raw = Array.isArray(o.members) ? o.members : [];
  if (raw.length < 2) {
    return NextResponse.json(
      { error: "チーム相性の算出には2名以上が必要です" },
      { status: 400 }
    );
  }
  if (raw.length > MAX_MEMBERS) {
    return NextResponse.json(
      { error: `メンバーは最大${MAX_MEMBERS}名までです` },
      { status: 400 }
    );
  }

  const members: TeamMember[] = [];
  for (const [i, m] of raw.entries()) {
    const parsed = parseMember(m, i);
    if (!parsed) {
      return NextResponse.json(
        { error: `${i + 1}人目のデータが不正です` },
        { status: 400 }
      );
    }
    members.push(parsed);
  }

  const lens = o.lens === "romance" ? "romance" : "business";
  const team = teamCompatibility(members, lens);
  const reading = await generateTeamReading(team);

  return NextResponse.json({ team, ...reading });
}
