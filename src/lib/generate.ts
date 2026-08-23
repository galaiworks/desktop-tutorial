// AI生成レイヤー（要件定義書 §5.5 / §10）
// 責務分離: 番号・スコア・相性判定は「確定事実」としてコードで渡し、AIは読み物化のみ。
// APIキーが無い環境でも動くよう、決定論フォールバック（テンプレ合成）を必ず持つ。
import type { Big5Scores, DiagnosisInput, Lens, LifePath } from "./types";
import { buildFusionFacts } from "./fusion";
import { getNumberContent } from "./content";
import { compatibility } from "./compatibility";
import { DISCLAIMER, checkGuard, ensureDisclaimer } from "./guard";
import type { TeamResult } from "./team";

const LENS_LABEL: Record<Lens, string> = {
  romance: "恋愛",
  business: "ビジネス",
};

// ── システムプロンプト（監修者のトーン。実運用はSKILL/プロンプトで固定 §10） ──
export const SYSTEM_PROMPT = `あなたは数秘術とビッグファイブ性格診断を融合して読み物を書く占い監修者です。
守るべきルール:
- 丁寧語ベース。断定しすぎず、相手に寄り添うやわらかいトーン。
- 与えられた「確定事実」（ライフパス番号・Big5スコア・相性判定）は事実として尊重し、数値や判定を創作・改変しない。
- 「必ず」「100%」「絶対」「確実に」など保証・断定・不安を煽る表現は使わない（景表法・占い表記の遵守）。
- 数秘は物語の入口（娯楽）、Big5は科学的裏付け、という二層を混同させない。
- 出力は日本語。見出しと短い段落で、スマホで読みやすく。`;

/** Big5スコアを人間可読な一文へ（プロンプトに埋め込む確定事実） */
function big5Line(b: Big5Scores): string {
  return `外向性${b.E} / 協調性${b.A} / 勤勉性${b.C} / 神経症傾向${b.N} / 開放性${b.O}（各0-100）`;
}

/** AIに渡すユーザープロンプトを構築 */
export function buildPrompt(input: DiagnosisInput): string {
  const selfFacts = buildFusionFacts(input.self.life_path, input.self.big5, input.lens);
  const lens = LENS_LABEL[input.lens];

  if (input.mode === "self" || !input.target) {
    const c = selfFacts.content;
    return `# 依頼: 自己診断の読み物を生成（${lens}レンズ）
## 確定事実（創作しないこと）
- ラベル: ${selfFacts.headline}
- ライフパス${c.number}のキーワード: ${c.keywords.join("・")}
- 本質: ${c.essence}
- 強み: ${c.strengths.join(" / ")}
- 使命: ${c.mission}
- Big5スコア: ${big5Line(input.self.big5)}
## 出力要件
上記を統合し、「あなた」に語りかける300〜500字の診断文を1本。数秘ラベルの物語性で惹きつけ、Big5スコアで具体的に描き分ける（例: 開放性が高いなら新しい挑戦を、勤勉性が高いなら着実さを織り込む）。最後に${lens}面での一言を添える。`;
  }

  // 相性モード
  const compat = compatibility(input.self, input.target, input.lens);
  const sc = getNumberContent(input.self.life_path);
  const tc = getNumberContent(input.target.life_path);
  return `# 依頼: 2者相性の読み物を生成（${lens}レンズ）
## 確定事実（数値は創作・改変しないこと）
- 自分: ライフパス${sc.number}（${sc.keywords.join("・")}） / Big5 ${big5Line(input.self.big5)}
- 相手: ライフパス${tc.number}（${tc.keywords.join("・")}） / Big5 ${big5Line(input.target.big5)}
- 数秘相性: ${compat.numerologyScore}点 / Big5相性: ${compat.big5Score}点 / 総合相性: ${compat.totalScore}点（100点満点）
## 出力要件
${
  input.depth === "teaser"
    ? `無料版の「さわり」です。総合相性${compat.totalScore}点が何を意味するかを2〜3文（120字以内）で述べ、2人の関係の"核心"には触れずに期待だけを残してください。具体的な攻略法・改善策は書かないでください（続きは公式LINEで渡すため）。`
    : `総合相性${compat.totalScore}点を軸に、${lens}面での2人の噛み合い方・すれ違いやすい点・関係を深めるヒントを300〜500字で。相性が高い点と補い合う点を具体的に。`
}`;
}

/** 決定論フォールバック: APIキーが無い/失敗時に確定事実からテンプレ合成する */
export function fallbackText(input: DiagnosisInput): string {
  const lens = LENS_LABEL[input.lens];
  if (input.mode === "self" || !input.target) {
    const f = buildFusionFacts(input.self.life_path, input.self.big5, input.lens);
    const c = f.content;
    const hi = f.descriptors
      .filter((d) => d.level === "high")
      .map((d) => d.label);
    const lensText = input.lens === "romance" ? c.love : c.work;
    const strengthLine = hi.length
      ? `特に${hi.join("・")}の高さが、あなたらしさを際立たせています。`
      : "バランスの取れた性質が、状況に応じた強みになります。";
    const body = `あなたは「${f.headline}」。${c.essence}\n\n${strengthLine}${c.strengths[0]}を軸に動くと、力が自然に発揮されます。使命は「${c.mission}」。\n\n【${lens}の傾向】${lensText}`;
    return ensureDisclaimer(body);
  }

  const compat = compatibility(input.self, input.target, input.lens);
  const sc = getNumberContent(input.self.life_path);
  const tc = getNumberContent(input.target.life_path);
  const verdict =
    compat.totalScore >= 75
      ? "とても好相性"
      : compat.totalScore >= 55
        ? "噛み合いやすい相性"
        : compat.totalScore >= 40
          ? "工夫しがいのある相性"
          : "違いを楽しめると伸びる相性";
  // 無料枠（§8）: スコアと"入口"までを見せ、攻略の中身は渡さない
  if (input.depth === "teaser") {
    const teaser = `【${lens}相性: ${compat.totalScore}点 / ${verdict}】\n\nライフパス${sc.number}（${sc.keywords.join("・")}）のあなたと、ライフパス${tc.number}（${tc.keywords.join("・")}）のお相手。数秘の相性は${compat.numerologyScore}点、性格傾向（Big5）の相性は${compat.big5Score}点でした。\n\nこの2つの数字の"差"にこそ、お二人の関係のくせが表れています。`;
    return ensureDisclaimer(teaser);
  }

  const body = `【${lens}相性: ${compat.totalScore}点 / ${verdict}】\n\nライフパス${sc.number}（${sc.keywords.join("・")}）のあなたと、ライフパス${tc.number}（${tc.keywords.join("・")}）のお相手。数秘の相性は${compat.numerologyScore}点、性格傾向（Big5）の相性は${compat.big5Score}点です。\n\n似ているところは安心感に、違うところはお互いを補い合う余白になります。${lens}面では、相手のペースを尊重しながら、あなたの強み「${sc.strengths[0]}」を差し出すと関係が深まります。`;
  return ensureDisclaimer(body);
}

export interface GenerateResult {
  text: string;
  source: "claude" | "fallback";
  guard: { ok: boolean; violations: string[] };
}

/**
 * 診断文を生成する。ANTHROPIC_API_KEY があれば Claude API を使い、
 * 無ければ/失敗すれば決定論フォールバックを返す。生成後は必ず禁止ワードガード + 但し書きを通す。
 */
export async function generateDiagnosis(
  input: DiagnosisInput
): Promise<GenerateResult> {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  const model = process.env.ANTHROPIC_MODEL || "claude-sonnet-5";

  if (apiKey) {
    try {
      const res = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          "x-api-key": apiKey,
          "anthropic-version": "2023-06-01",
        },
        body: JSON.stringify({
          model,
          max_tokens: 1024,
          system: SYSTEM_PROMPT,
          messages: [{ role: "user", content: buildPrompt(input) }],
        }),
      });
      if (res.ok) {
        const data = (await res.json()) as {
          content?: { type: string; text?: string }[];
        };
        const raw =
          data.content?.map((b) => b.text ?? "").join("").trim() ?? "";
        if (raw) {
          const text = ensureDisclaimer(raw);
          return { text, source: "claude", guard: checkGuard(text) };
        }
      }
    } catch {
      // ネットワーク/APIエラー時はフォールバックへ
    }
  }

  const text = fallbackText(input);
  return { text, source: "fallback", guard: checkGuard(text) };
}

// ── チーム診断（BtoB）の生成 — 要件定義書 §2 提供価値③ / §3.2 ──

/** チーム所見のプロンプト。数値はすべて確定値として渡し、AIは解釈のみ担う。 */
export function buildTeamPrompt(team: TeamResult): string {
  const pairLines = team.pairs
    .map((p) => `- ${p.aName} × ${p.bName}: ${p.score}点`)
    .join("\n");
  return `# 依頼: チームの相互理解レポートを生成
## 確定事実（数値は創作・改変しないこと）
- 人数: ${team.memberCount}名 / 平均相性: ${team.averageScore}点
- チーム平均のBig5: ${big5Line(team.profile)}
- ペア別スコア:
${pairLines}
- 傾向メモ: ${team.notes.join(" / ")}
## 出力要件
チームの強みと、噛み合いにくい場面での工夫を400字程度で。
**重要**: 個人の性格を優劣で評価しないこと。採用・評価の判断材料として断定しないこと。
「このチームはこう動くと力が出る」という相互理解の視点で書いてください。`;
}

/** チーム所見の決定論フォールバック */
export function fallbackTeamText(team: TeamResult): string {
  const strong = team.strongestPair;
  const body = [
    `【チーム相性レポート（${team.memberCount}名 / 平均${team.averageScore}点）】`,
    "",
    team.notes.join("\n"),
    "",
    strong
      ? `もっとも噛み合いやすいのは ${strong.aName} と ${strong.bName}（${strong.score}点）の組み合わせです。難易度の高い案件では、この2人を軸に据えると進みやすくなります。`
      : "",
    "",
    "スコアは相互理解のための参考指標です。低いペアは「相性が悪い」のではなく、前提の共有に少し時間をかけるとよい組み合わせだと捉えてください。",
  ]
    .filter(Boolean)
    .join("\n");
  return ensureDisclaimer(body);
}

/** チーム所見を生成する（Claude → 失敗時フォールバック） */
export async function generateTeamReading(
  team: TeamResult
): Promise<GenerateResult> {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  const model = process.env.ANTHROPIC_MODEL || "claude-sonnet-5";

  if (apiKey) {
    try {
      const res = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          "x-api-key": apiKey,
          "anthropic-version": "2023-06-01",
        },
        body: JSON.stringify({
          model,
          max_tokens: 1024,
          system: SYSTEM_PROMPT,
          messages: [{ role: "user", content: buildTeamPrompt(team) }],
        }),
      });
      if (res.ok) {
        const data = (await res.json()) as {
          content?: { type: string; text?: string }[];
        };
        const raw = data.content?.map((b) => b.text ?? "").join("").trim() ?? "";
        if (raw) {
          const text = ensureDisclaimer(raw);
          return { text, source: "claude", guard: checkGuard(text) };
        }
      }
    } catch {
      // フォールバックへ
    }
  }
  const text = fallbackTeamText(team);
  return { text, source: "fallback", guard: checkGuard(text) };
}
