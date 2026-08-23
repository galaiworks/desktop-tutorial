# NUMEN 実装ノート

要件定義書「数秘術 × ビッグファイブ AI診断・マッチングツール（NUMEN v0.1）」に対する実装の対応表と技術メモ。

## 1. アーキテクチャ

```
config/                     流派・尺度・重みの設定（監修者の確認を経て上書きする層）
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
  share.ts                  診断コードの生成・解釈
  storage.ts                自己診断結果の端末保存
  analytics.ts              KPI計測
  persistence.ts            Supabase保存（未設定なら無効）
  types.ts                  共通型
src/app/                    Next.js App Router（モバイルファーストUI）
  page.tsx                  LP
  diagnose/page.tsx         生年月日 → TIPI-J → 結果 → 診断コード → LINE誘導
  compatibility/page.tsx    2者相性（コード貼付 / 代理回答・レンズ切替）
  privacy, terms            法務ページ
  api/generate/route.ts     AI生成API（入力バリデーション + 保存）
src/components/             RadarChart / TipiQuiz / Likert（共通UI）
tests/                      vitest（43件）
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
- システムプロンプトで監修者のトーンを固定（丁寧語・断定回避・二層分離）。
- 生成後は必ず `checkGuard` + `ensureDisclaimer` を通す。

### §5.6 相性エンジン
- 総合 = 数秘相性 × w1 + Big5相性 × w2（`config/scoring.json`、正規化）。
- 数秘相性はレンズ別 12×12 マトリクス（対称化のため両方向平均）。
- Big5相性は因子ごとに similarity（差が小さいほど加点）/ complementarity（差が大きいほど加点）を重み付き適用。神経症傾向は補完性、協調性・勤勉性は類似性を既定。

### §5.7 LINE誘導
- 結果画面の CTA から友だち追加URL（`NEXT_PUBLIC_LINE_ADD_URL`）へ。
- 診断結果（ライフパス + Big5 + レンズ）を診断コード `?numen=N1-...&lens=...` で引き継ぎ。
- URL未設定時は導線を無効化しつつ設定メモを表示。

### §8 無料/有料の出し分け
- 無料: 数秘ラベル + Big5レーダー + AI一言（読み物）。
- 有料（LINE後）: フル解説（本質/使命/強み/恋愛or適職/注意点）を**ぼかし表示（blur）**して「続きはLINEで」。

### §10 ガード
- 景表法・不安喚起・断定に触れる表現を正規表現で検出（`BANNED_PATTERNS`）。
- 出力末尾へ娯楽目的の但し書きを冪等に付与。

## 3. テスト（`npm test`）
- share: 診断コードの往復・全角入力の吸収・URL生成
- numerology: 桁合計・還元・マスター停止・要件の実例・還元方式・入力検証。
- tipi: 逆転処理・中立=50・正規化・逆転採点・異常入力。
- compatibility: 数秘相性の範囲/対称性・類似/補完・総合・レンズ差。
- generate: フォールバック文（スコア埋め込み・ガード通過）・プロンプト構築・ガード・但し書き冪等性。

## 4. 未実装（将来フェーズ）
- ユーザー同士のマッチング（DBから相性上位を相互推薦。テーブルは用意済み）
- LIFF（LINE内ミニアプリ化）、BtoBチーム相性ダッシュボード
- パーソナルイヤー（年運）、名前ベースの数字（ディスティニー等）

## 5. 運用前に埋める（§14 の未確定論点）
1. TIPI-J 項目本文の権利確認と正規文差替（`config/tipi_j.json`）
2. ナンバー解説の監修（`data/numbers/*.json`）
3. 相性マトリクス・重みのチューニング（`config/*`）
4. 主戦場レンズ（恋愛/ビジネス）の初期前面出し
5. 無料開示範囲の最終ライン（相性スコアを数値まで見せるか）
6. プロダクト名確定、LINE初回商品の設計

## 6. 追加実装（MVP完成分）

### §3.1 2者相性診断UI — `src/app/compatibility/page.tsx`
- 自分のデータは自己診断時に端末へ保存（`src/lib/storage.ts`）し自動復元。生年月日は保存せず算出結果のみ。
- 相手の指定は2通り: **診断コードを貼る**／**その場で代理回答**（生年月日＋TIPI-J 10問）。
- `?with=<code>` 付きリンクで開くと相手が自動セットされる＝シェアからの相性診断が1タップで始まる。
- 結果は総合スコアを主役に、数秘相性／Big5相性の内訳を色分けメーター＋数値で提示。

### 診断コード — `src/lib/share.ts`
`N1-{lifePath}-{E}-{A}-{C}-{N}-{O}`（例 `N1-11-72-40-85-30-66`）。
Base64ではなく可読な書式にしたため、口頭・スクショ・LINEでの受け渡しに耐える。
全角英数/全角ハイフンを正規化して取り込む（コピペ耐性）。LINE誘導URLにも同じコードを使用。

### §8 無料/有料の出し分け（`depth`）
`depth: "teaser" | "full"` をAI生成レイヤーに追加。相性診断の無料枠は
「スコアは見せる／攻略は渡さない」。フォールバック文・プロンプト双方に反映し、テストで担保。

### §12 KPI計測 — `src/lib/analytics.ts`
GTM(dataLayer)/GA4(gtag)/Plausible のいずれかがあれば送信、無ければ無害に破棄。
計測イベント: `diagnosis_start` / `birth_submitted` / `tipi_complete` / `result_view` /
`share_click` / `code_copy` / `line_cta_click` / `compatibility_start` /
`compatibility_result_view` / `lens_switch`。個人情報はイベントに載せない。

### §7 永続化 — `supabase/migrations/0001_init.sql` + `src/lib/persistence.ts`
`users` / `diagnoses` / `matches` / `line_links`。**RLSを有効化しポリシーを作らない**ことで
匿名クライアントからの読み書きを遮断し、サーバの service role 経由のみ許可する。
環境変数未設定なら保存は完全に無効化され、診断は通常どおり動作する。

### §13 法務ページ
`/privacy`（取得情報・利用目的・保存範囲・外部送信・LINE連携）と
`/terms`（娯楽目的の明示・免責・性格特性を優劣で断じない旨・TIPI-J出典）。フッターから常時到達可能。

## 7. フェーズ2の実装（§3.2）

### 名前ベースの数字 — `src/lib/name.ts` + `/name`
ピタゴラス式（A=1…I=9, J=1…R=9, S=1…Z=8）で3種を算出する。
- **ディスティニー**（全文字）／**ソウル**（母音）／**パーソナリティ**（子音）
- Yを母音として扱うか、姓名を各々還元するかは `config/name_numerology.json` で切替。
- マスターナンバーは保持する（例: `Ann` → 11）。
- 入力名は**サーバーに送信せず端末内で計算**する（§13-4 本名不要の設計方針）。

### パーソナルイヤー — `src/lib/personalYear.ts` + `/year`
「誕生月 + 誕生日 + 対象年」を1桁まで還元。年運は9年周期のため**マスターは残さない**。
パーソナルマンス（年運＋月）も算出。解説は `data/personal_year.json`（独自執筆・監修待ち）。

### チーム相性（BtoB） — `src/lib/team.ts` + `/team` + `api/team`
メンバーの診断コードを入力し、総当たり（nC2）の相性・平均・最良/最難ペア・
チーム平均プロファイル・因子ごとのばらつき（標準偏差）を算出する。最大20名。
§13-5に従い、出力は優劣評価ではなく「傾向と補い方」に限定し、
UIにも採用・評価の唯一根拠にしない旨を明記している。

### マッチング — `src/lib/matching.ts` + `/match` + `api/match`
- `action: "recommend"` … オプトイン済み候補を相性順に返す
- `action: "join"` … 参加登録（`opted_in: true` と表示名が**必須**。同意なしでは登録できない）
- **他人のBig5スコアはAPIレスポンスに含めない**。返すのは表示名・ライフパス・相性スコアのみ。
- DB未設定時は 503 と案内文を返し、UIは「準備中」を表示する。

### LIFF — `/liff` + `api/link`
LINEアプリ内で開かれたときにSDKをCDNから読み込み、`liff.init` → プロフィール取得まで
成功した場合**のみ**フル鑑定を開放する（`state === "ready"` でゲート）。
未設定・未検証の状態では本命コンテンツを描画しないため、§8の無料/有料の線引きが保たれる。
本番導入時は `verifyIdToken` を通したうえで `line_user_id` を渡すこと。

## 8. テスト構成（78件）
- numerology / tipi / compatibility / generate / share（MVP）
- name: 文字値・母音判定・3アスペクト・マスター保持・流派設定・異常入力
- personalYear: 算出・1〜9の範囲・年送り・月運・全年分のコンテンツ存在
- team: 総当たり件数・平均・最良/最難・プロファイル/ばらつき・人数下限・レンズ差
- matching: 降順ソート・件数制限・自分の除外・空プール

## 9. 尺度アダプタと公開前チェック

### ビッグファイブ尺度の差し替え（§5.3 / §13-2 / §14）
`config/big5_scale.json` の `active` で尺度を切り替える。

| 尺度 | 権利処理 | 学術的検証 | 状態 |
|---|---|---|---|
| `numen-10`（既定） | 不要（独自作成） | 未実施 | そのまま公開可 |
| `tipi-j` | 要確認 | 済 | 項目文が仮のため active 不可 |

要件定義書 §13-2 の「不安があれば独自Big5尺度の別途作成を検討」に対応し、
権利ブロッカーなしで公開できる独自10項目を作成した。因子ごとに正1・逆1の構成は共通。

安全装置：
- `npm run validate` … 仮テキストのまま active ならエラー
- `tests/big5Scale.test.ts` … active 尺度に placeholder が混じっていたら失敗
- 未検証の尺度に `citation` を書くと両方が失敗（誇大表示の防止）

利用規約・プライバシーポリシー・結果画面の脚注は `SCALE` から自動生成されるため、
尺度を切り替えると表記も追従する（独自尺度のときは「検証していない」旨を明示）。

### 運営者情報（§13-4）
`config/site.json` に集約。未設定のあいだは法務ページに赤字で
「【公開前に要記載】」と表示され、黙って空欄にはならない。

### 内部メモとユーザー向け文言の分離
ナンバー解説・年運解説の監修用メモは `_editorialNote`（アンダースコア始まり＝内部用）に格納し、
UIには一切描画しない。

### 公開前チェック（`npm run validate`）
尺度の構造・仮テキスト・解説データの必須項目・相性マトリクス144通り×2レンズの
完全性と範囲・Big5重み・年運1〜9・運営者情報を検証する。`--strict` で警告もエラー扱い。

## 10. 有料コンテンツのサーバー側ゲート（§8）

### 直した問題
当初、フル鑑定の本文（本質・使命・強み・恋愛/仕事・注意点）は
`data/numbers/*.json` をクライアントコンポーネントから import していたため
**JSバンドルに丸ごと含まれていた**。画面はCSSの `filter: blur()` で伏せているだけなので、
`/_next/static/chunks/*.js` を直接開けば全文が読めた＝無料/有料の線引きが成立していなかった。

### 対策
1. **公開データの分離** — `scripts/gen-public-content.mjs` が
   `data/numbers/*.json` から公開可の項目（number / isMaster / keywords）だけを
   `data/numbers.public.json` に書き出す。`prebuild` で自動実行。
2. **クライアントは公開データのみ参照** — `src/lib/contentPublic.ts` を新設。
   `fusion.ts`（有料データを読む）から、クライアント安全な `headline.ts` を分離した。
   `content.ts` / `fusion.ts` は**サーバー専用**。
3. **本文はサーバーから配信** — `/api/reading/full` がLIFFのIDトークンを
   LINEの検証エンドポイントで確認し、通った場合にのみ本文を返す
   （`src/lib/lineAuth.ts`。`aud` とチャネルID、有効期限も検証）。
   クライアントが送ってくる `line_user_id` は信用しない。
4. **無料側の表示** — ぼかした本物のテキストではなく、
   ロックされた「見出しだけ」のリストを出す（本文はそもそも手元に無い）。

### 回帰を防ぐ仕組み
- `tests/contentGate.test.ts` … 公開データに有料項目が無いこと、
  公開データが元データと同期していること、`use client` のファイルが
  `@/lib/content` / `@/lib/fusion` を import しないことを検査。
- `npm run validate` … 公開ファイルの有料項目混入とキーワードの不一致を検出。
- CI（`.github/workflows/ci.yml`）… `npm run gen:public` を実行して差分が出たら失敗。

いずれも、わざと `essence` を公開側に混ぜた状態で失敗することを確認済み。
