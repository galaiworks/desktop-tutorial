#!/usr/bin/env node
// data/numbers/*.json から「クライアントに送ってよい部分」だけを抽出する。
// 有料コンテンツ（本質・使命・強み・恋愛/仕事・注意点）をJSバンドルに混入させないための仕組み。
// 生成物: data/numbers.public.json（コミット対象。npm run build の前に自動実行される）
import fs from "node:fs";

const NUMBERS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 22, 33];

// クライアントに出してよいフィールドのみを列挙する（ここに追加するときは有料範囲との整合を確認すること）
const PUBLIC_FIELDS = ["number", "isMaster", "keywords"];

const out = {};
for (const n of NUMBERS) {
  const src = JSON.parse(fs.readFileSync(`data/numbers/${n}.json`, "utf8"));
  const picked = {};
  for (const f of PUBLIC_FIELDS) picked[f] = src[f];
  out[n] = picked;
}

const payload = {
  $comment:
    "自動生成ファイル。編集しないこと。data/numbers/*.json を変更したら npm run gen:public を実行する。",
  $generatedFrom: "data/numbers/*.json",
  $publicFields: PUBLIC_FIELDS,
  numbers: out,
};

const path = "data/numbers.public.json";
const next = JSON.stringify(payload, null, 2) + "\n";
const prev = fs.existsSync(path) ? fs.readFileSync(path, "utf8") : "";
if (prev !== next) {
  fs.writeFileSync(path, next);
  console.log(`[numen] ${path} を更新しました`);
} else {
  console.log(`[numen] ${path} は最新です`);
}
