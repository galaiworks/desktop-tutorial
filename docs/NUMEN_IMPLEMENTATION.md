# NUMEN 実装ノート

要件定義書「数秘術 × ビッグファイブ AI診断・マッチングツール（NUMEN v0.1）」に対する実装の対応表と技術メモ。

## 1. アーキテクチャ

```
config/                     流派・尺度・重みの設定（森田さん監修で上書きする層）
  numerology.json           マスターナンバー / 還元方式
  tipi_j.json               TIPI-J 尺度定義（項目本文は placeholder）
  numerology_affinity.json  数秘 12×12 相性マトリクス（レンズ別）
  big5_compat.json          Big5相性の類似/補完ルール・重み（レンズ別）
  scoring.json              総合スコアの数秘/Big5 重み
data/numbers/{n}.json       ナンバー解説（独自執筆・監修待ち）
src/lib/                    純ロジック（外部依存なし・完全決定論）
  numerology.ts             ライフパス算出
  tipi.ts                   TIPI-J 採点
  compatibility.ts          相性エンジン
  fusion.ts                 数秘×Big5 融合（確定事実の組み立て）
  generate.ts               AI生成レイヤー（Claude + フォールバック）
  guard.ts                  禁止ワードガード + 但し書き
  content.ts                ナンバー解説ローダ
  types.ts                  共通型
src/app/                    Next.js App Router（モバイルファーストUI）
  page.tsx                  LP
  diagnose/page.tsx         生年月日 → TIPI-J → 結果 → LINE誘導
  api/generate/route.ts     AI生成API（入力バリデーションつき）
src/components/RadarChart.tsx  依存ゼロのSVGレーダー
tests/                      vitest（30件）
```

## 2. 要件 → 実装 対応（詳細）

### §5.2 数秘エンジン
- `digit_sum` / `reduce_number` / `life_path` を要件定義書のアルゴリズムどおり実装。
- 還元途中でマスターナンバー（11/22/33）が出たら停止。
- 検算: `1985-12-03 → 11`、`1990-07-20 → 1`（要件定義書の例。テストで固定）。
- 流派差は `config/numerology.json` で切替（33の有無、44の有無、還元方式）。

### §5.3 TIPI-J
- 5因子 × 正逆2項目 = 10項目、7件法。逆転項目は `8 - value`。
- 各因子＝対応2項目の平均（1–7）→ 0–100 に正規化してレーダー化。
- **項目本文は改変せず公式版を使う**という遵守事項に従い、本実装では本文を転載せず placeholder を置き、`placeholder: true` フラグと `$license` 注記で差替を明示。採点構造（因子対応・逆転キー）は方法論的事実として実装。
- 出典を UI 脚注と config に明記（小塩ら, 2012, パーソナリティ研究, 21, 40–52）。

### §5.4 融合ロジック
- 数秘＝ラベル（`fusionHeadline`：例「ライフパス3でも外向性が低ければ"静かな創造者"」）。
- Big5＝補正（`big5Descriptors`：高/中/低のレベル言語化）。
- `buildFusionFacts` が「AIに渡す確定事実の束」を作り、AIはこれを創作しない。

### §5.5 AI生成レイヤー
- 入力は要件定義書の構造化JSON（self/target/lens/mode）。
- `ANTHROPIC_API_KEY` があれば Claude Messages API（既定モデル `claude-sonnet-5`、`ANTHROPIC_MODEL` で変更可）。
- 失敗時・キー未設定時は決定論フォールバック（`fallbackText`）。
- システムプロンプトで森田さん監修トーンを固定（丁寧語・断定回避・二層分離）。
- 生成後は必ず `checkGuard` + `ensureDisclaimer` を通す。

### §5.6 相性エンジン
- 総合 = 数秘相性 × w1 + Big5相性 × w2（`config/scoring.json`、正規化）。
- 数秘相性はレンズ別 12×12 マトリクス（対称化のため両方向平均）。
- Big5相性は因子ごとに similarity（差が小さいほど加点）/ complementarity（差が大きいほど加点）を重み付き適用。神経症傾向は補完性、協調性・勤勉性は類似性を既定。

### §5.7 LINE誘導
- 結果画面の CTA から友だち追加URL（`NEXT_PUBLIC_LINE_ADD_URL`）へ。
- 診断結果（ライフパス + Big5 + レンズ）を Base64 トークン `?numen=` で引き継ぎ。
- URL未設定時は導線を無効化しつつ設定メモを表示。

### §8 無料/有料の出し分け
- 無料: 数秘ラベル + Big5レーダー + AI一言（読み物）。
- 有料（LINE後）: フル解説（本質/使命/強み/恋愛or適職/注意点）を**ぼかし表示（blur）**して「続きはLINEで」。

### §10 ガード
- 景表法・不安喚起・断定に触れる表現を正規表現で検出（`BANNED_PATTERNS`）。
- 出力末尾へ娯楽目的の但し書きを冪等に付与。

## 3. テスト（`npm test`）
- numerology: 桁合計・還元・マスター停止・要件の実例・還元方式・入力検証。
- tipi: 逆転処理・中立=50・正規化・逆転採点・異常入力。
- compatibility: 数秘相性の範囲/対称性・類似/補完・総合・レンズ差。
- generate: フォールバック文（スコア埋め込み・ガード通過）・プロンプト構築・ガード・但し書き冪等性。

## 4. 未実装（将来フェーズ）
- 相性フルUI（現状はAPIとエンジンのみ。self診断UIを実装）
- ユーザーDB・マッチング（Supabase）、LIFF、BtoBダッシュボード
- パーソナルイヤー（年運）、名前ベースの数字
- 計測基盤（§12 KPI 計装）

## 5. 運用前に埋める（§14 の未確定論点）
1. TIPI-J 項目本文の権利確認と正規文差替（`config/tipi_j.json`）
2. ナンバー解説の監修（`data/numbers/*.json`）
3. 相性マトリクス・重みのチューニング（`config/*`）
4. 主戦場レンズ（恋愛/ビジネス）の初期前面出し
5. 無料開示範囲の最終ライン（相性スコアを数値まで見せるか）
6. プロダクト名確定、LINE初回商品の設計
