# NUMEN — 数秘術 × ビッグファイブ AI診断・マッチングツール

生年月日から算出する**数秘術（ライフパスナンバー）**と、心理学で最も信頼される性格理論**ビッグファイブ（TIPI-J）**を掛け合わせ、**AIがパーソナライズした診断文**を生成します。診断を入口に恋愛／ビジネスの相性マッチングへ展開し、公式LINE登録へ誘導する MVP 実装です。

> 要件定義書（コードネーム NUMEN v0.1）の **MVP（フェーズ1）およびフェーズ2の機能一式**を実装したものです。

## 実装済みスコープ

| 要件 | 実装 |
|---|---|
| §5.2 数秘エンジン（マスターナンバー・還元方式を設定化） | `src/lib/numerology.ts` + `config/numerology.json` |
| §5.3 TIPI-J 10問・5因子採点（逆転処理・0-100正規化） | `src/lib/tipi.ts` + `config/tipi_j.json` |
| §5.4 融合ロジック（数秘ラベル × Big5補正） | `src/lib/fusion.ts` |
| §5.5 AI生成レイヤー（確定値はコード／読み物はAI） | `src/lib/generate.ts` + `src/app/api/generate` |
| §5.6 相性エンジン（数秘マトリクス × Big5相性・レンズ別） | `src/lib/compatibility.ts` + `config/*` |
| §5.7 LINE誘導（結果を引き継ぐパラメータ付きURL） | `src/app/diagnose/page.tsx` |
| §5.2 ナンバー解説データ（12種・独自執筆） | `data/numbers/{n}.json` |
| §3.1 2者相性診断UI（恋愛／ビジネスレンズ） | `src/app/compatibility/page.tsx` |
| §8 無料/有料の出し分け（相性はスコア＋さわりまで） | 結果画面 + `depth: teaser` |
| §10 禁止ワードガード + 娯楽目的の但し書き自動付与 | `src/lib/guard.ts` |
| §12 KPI計測（ファネル全ステップ） | `src/lib/analytics.ts` |
| §13 プライバシーポリシー / 利用にあたって | `src/app/privacy`, `src/app/terms` |
| §7 データ設計（RLS込みスキーマ・保存） | `supabase/migrations/0001_init.sql` + `src/lib/persistence.ts` |
| レーダーチャート（依存ゼロのSVG） | `src/components/RadarChart.tsx` |
| §3.2 名前の数字（ディスティニー／ソウル／パーソナリティ） | `src/lib/name.ts` + `src/app/name` |
| §3.2 パーソナルイヤー（年運） | `src/lib/personalYear.ts` + `src/app/year` |
| §3.2 BtoBチーム相性ダッシュボード | `src/lib/team.ts` + `src/app/team` |
| §3.2 ユーザー同士のマッチング（DB） | `src/lib/matching.ts` + `src/app/match` + `api/match` |
| §5.7 LIFF（LINE内でフル鑑定を開放） | `src/app/liff` + `api/link` |

決済（Stripe等）は要件定義書 §3.3 により非スコープです。

## 設計上の重要判断（要件定義書のデフォルト採用）

- **マスターナンバー**: 11/22/33 を含む **12種**（`config/numerology.json` で切替可、44はデフォルト無効）
- **還元方式**: 一括合計（`sum-all`）をデフォルト。各柱還元（`reduce-each-pillar`）も設定で選択可
- **責務分離**: 番号・スコア・相性判定は**すべてコードで確定**。AIは読み物化のみ（ハルシネーション防止）
- **フォールバック**: `ANTHROPIC_API_KEY` 未設定でも決定論テンプレで動作（キーがあれば Claude API を使用）
- **無料で見せる範囲**（§14の未確定論点）: 相性は**スコアの数値は見せ、攻略は渡さない**を既定に。拡散性を優先しつつ§8の鉄則を守る
- **診断コードによる引き継ぎ**: `N1-11-72-40-85-30-66` 形式。相性診断の相手指定とLINE誘導で共用（人が読める・コピペできる書式）

## セットアップ

```bash
npm install
cp .env.example .env.local   # 任意: ANTHROPIC_API_KEY / NEXT_PUBLIC_LINE_ADD_URL を設定
npm run dev                  # http://localhost:3000
```

```bash
npm test        # ユニットテスト（78件）
npm run build   # 本番ビルド + 型チェック
```

## 要チェック事項（未確定・監修待ち。要件定義書 §13/§14）

- **TIPI-J 項目本文**: `config/tipi_j.json` の `text` は **placeholder**。商用利用の権利確認の上、公式版（小塩ら, 2012）の正規項目文へ差し替えること（`placeholder: true` フラグで検出可能）。採点構造（因子対応・逆転）は正しく実装済み。
- **ナンバー解説文**: `data/numbers/*.json` は独自執筆のドラフト。**森田さん監修で最終化**。既存ブランド流派の文言は転用していません。
- **相性マトリクス / Big5相性重み**: `config/numerology_affinity.json`・`config/big5_compat.json` は初期ヒューリスティクス。森田さんの流派解釈でチューニングしてください。
- **法務**: プライバシーポリシー・利用にあたっての雛形は実装済みだが、**運営者名と問い合わせ先は公開前に記載が必要**（`src/app/privacy/page.tsx`）。
- **環境変数**: `NEXT_PUBLIC_LINE_ADD_URL` 未設定だとLINE導線は無効表示。`SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` 未設定なら保存とマッチングは無効（診断は動作）。`NEXT_PUBLIC_LIFF_ID` 未設定なら `/liff` はフル鑑定を出しません。
- **マイグレーション**: `supabase/migrations/` の SQL を適用してからマッチング機能を有効化してください。

## 技術スタック

Next.js 14（App Router）/ TypeScript / React（モバイルファースト）。数秘・Big5計算は外部依存なしの純ロジック（サーバ／クライアント両対応）。詳細は [`docs/NUMEN_IMPLEMENTATION.md`](docs/NUMEN_IMPLEMENTATION.md)。

---

> 補足: 本リポジトリには別プロジェクト「TimeKeeper Pro」の設計ドキュメント（`docs/TimeKeeperPro_Mac_App_Design.md`, `CLAUDE_DEVELOPMENT_GUIDE.md`）が同梱されています。NUMEN の実装とは独立しています。
