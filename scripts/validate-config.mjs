#!/usr/bin/env node
// 公開前チェック（要件定義書 §13 / §14）
// 監修・権利処理・運営者情報の入力漏れを機械的に検出する。
// 使い方: npm run validate  （--strict で警告もエラー扱い）

import fs from "node:fs";
import path from "node:path";

const strict = process.argv.includes("--strict");
const errors = [];
const warnings = [];

const read = (p) => JSON.parse(fs.readFileSync(p, "utf8"));
const err = (m) => errors.push(m);
const warn = (m) => warnings.push(m);

const NUMBERS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 22, 33];
const FACTORS = ["E", "A", "C", "N", "O"];

// ── 1. ビッグファイブ尺度 ──
const selector = read("config/big5_scale.json");
const scaleFiles = fs
  .readdirSync("config/scales")
  .filter((f) => f.endsWith(".json"));

let activeScale = null;
for (const f of scaleFiles) {
  const s = read(path.join("config/scales", f));
  if (s.id === selector.active) activeScale = s;

  if (s.items.length !== 10) err(`[尺度:${s.id}] 項目数が10ではありません（${s.items.length}）`);
  for (const factor of FACTORS) {
    const items = s.items.filter((i) => i.factor === factor);
    if (items.length !== 2) err(`[尺度:${s.id}] 因子${factor}の項目が2つではありません（${items.length}）`);
    if (items.filter((i) => i.reverse).length !== 1)
      err(`[尺度:${s.id}] 因子${factor}に逆転項目がちょうど1つありません`);
  }
  if (!s.validated && s.citation)
    err(`[尺度:${s.id}] 未検証の尺度に出典が設定されています（誤認を招くため不可）`);
}

if (!activeScale) {
  err(`[尺度] active に指定された "${selector.active}" が config/scales に見つかりません`);
} else {
  const placeholders = activeScale.items.filter(
    (i) => i.placeholder || String(i.text).includes("要・公式項目文差替")
  );
  if (placeholders.length > 0)
    err(
      `[尺度:${activeScale.id}] 仮の項目文が ${placeholders.length}件 残ったまま active になっています。` +
        `権利処理と正規項目文への差し替えを完了してください（§13-2）`
    );
  if (!activeScale.validated)
    warn(
      `[尺度:${activeScale.id}] 学術的な検証を経ていない尺度が有効です。` +
        `「検証済み」と訴求しないでください（§13-7）`
    );
}

// ── 2. 数秘の解説データ ──
const REQUIRED_FIELDS = [
  "keywords",
  "essence",
  "strengths",
  "mission",
  "love",
  "work",
  "caution",
];
let draftCount = 0;
for (const n of NUMBERS) {
  const p = `data/numbers/${n}.json`;
  if (!fs.existsSync(p)) {
    err(`[解説] ${p} がありません`);
    continue;
  }
  const c = read(p);
  for (const field of REQUIRED_FIELDS) {
    const v = c[field];
    const empty = Array.isArray(v) ? v.length === 0 : !v;
    if (empty) err(`[解説:${n}] ${field} が空です`);
  }
  if (String(c._editorialNote ?? "").includes("ドラフト")) draftCount++;
}
if (draftCount > 0)
  warn(`[解説] ${draftCount}/${NUMBERS.length} 件が監修前のドラフトのままです（§5.2）`);

// ── 3. 相性マトリクス ──
const affinity = read("config/numerology_affinity.json");
for (const lens of ["romance", "business"]) {
  const m = affinity[lens];
  if (!m) {
    err(`[相性] ${lens} のマトリクスがありません`);
    continue;
  }
  for (const a of NUMBERS) {
    for (const b of NUMBERS) {
      const v = m?.[a]?.[b];
      if (typeof v !== "number") {
        err(`[相性:${lens}] ${a}×${b} が未設定です`);
      } else if (v < 0 || v > 100) {
        err(`[相性:${lens}] ${a}×${b} が範囲外です（${v}）`);
      }
    }
  }
}

// ── 4. Big5相性の重み ──
const compat = read("config/big5_compat.json");
for (const lens of ["romance", "business"]) {
  for (const f of FACTORS) {
    const rule = compat[lens]?.[f];
    if (!rule) {
      err(`[Big5相性:${lens}] 因子${f}の設定がありません`);
      continue;
    }
    if (!["similarity", "complementarity"].includes(rule.mode))
      err(`[Big5相性:${lens}] 因子${f}の mode が不正です（${rule.mode}）`);
    if (typeof rule.weight !== "number" || rule.weight < 0)
      err(`[Big5相性:${lens}] 因子${f}の weight が不正です`);
  }
}

// ── 5. 年運の解説 ──
const py = read("data/personal_year.json");
for (let n = 1; n <= 9; n++) {
  const c = py.years?.[String(n)];
  if (!c) err(`[年運] ${n} の解説がありません`);
  else if (!c.theme || !c.summary) err(`[年運:${n}] theme / summary が空です`);
}

// ── 6. 運営者情報（§13-4） ──
const site = read("config/site.json");
if (!site.operatorName) err("[運営者] operatorName が未設定です（公開前に必須）");
if (!site.contactEmail) err("[運営者] contactEmail が未設定です（公開前に必須）");

// ── 出力 ──
const line = "─".repeat(58);
console.log(line);
console.log("NUMEN 公開前チェック");
console.log(line);
if (warnings.length) {
  console.log(`\n⚠ 警告 ${warnings.length}件`);
  warnings.forEach((w) => console.log(`  - ${w}`));
}
if (errors.length) {
  console.log(`\n✖ 未完了 ${errors.length}件`);
  errors.forEach((e) => console.log(`  - ${e}`));
} else {
  console.log("\n✓ 必須項目はすべて埋まっています");
}
console.log(`\n${line}`);

const failed = errors.length > 0 || (strict && warnings.length > 0);
process.exit(failed ? 1 : 0);
