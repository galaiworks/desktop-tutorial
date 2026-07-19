# NUMEN — 数秘術 × ビッグファイブ AI診断・マッチングツール

生年月日から算出する**数秘術（ライフパスナンバー）**と、心理学で最も信頼される性格理論**ビッグファイブ（TIPI-J）**を掛け合わせ、**AIがパーソナライズした診断文**を生成します。診断を入口に恋愛／ビジネスの相性マッチングへ展開し、公式LINE登録へ誘導する MVP 実装です。

> 要件定義書（コードネーム NUMEN v0.1）の **P0（コアロジック）〜P2（AI生成・相性簡易版）** を実装したものです。

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
| §8 無料/有料の出し分け（フル鑑定はぼかしてLINEへ） | 結果画面 |
| §10 禁止ワードガード + 娯楽目的の但し書き自動付与 | `src/lib/guard.ts` |
| レーダーチャート（依存ゼロのSVG） | `src/components/RadarChart.tsx` |

将来フェーズ（相性フルUI、マッチングDB、Supabase永続化、LIFF、BtoB）は未実装です。

## 設計上の重要判断（要件定義書のデフォルト採用）

- **マスターナンバー**: 11/22/33 を含む **12種**（`config/numerology.json` で切替可、44はデフォルト無効）
- **還元方式**: 一括合計（`sum-all`）をデフォルト。各柱還元（`reduce-each-pillar`）も設定で選択可
- **責務分離**: 番号・スコア・相性判定は**すべてコードで確定**。AIは読み物化のみ（ハルシネーション防止）
- **フォールバック**: `ANTHROPIC_API_KEY` 未設定でも決定論テンプレで動作（キーがあれば Claude API を使用）

## セットアップ

```bash
npm install
cp .env.example .env.local   # 任意: ANTHROPIC_API_KEY / NEXT_PUBLIC_LINE_ADD_URL を設定
npm run dev                  # http://localhost:3000
```

```bash
npm test        # エンジンのユニットテスト（30件）
npm run build   # 本番ビルド + 型チェック
```

## 要チェック事項（未確定・監修待ち。要件定義書 §13/§14）

- **TIPI-J 項目本文**: `config/tipi_j.json` の `text` は **placeholder**。商用利用の権利確認の上、公式版（小塩ら, 2012）の正規項目文へ差し替えること（`placeholder: true` フラグで検出可能）。採点構造（因子対応・逆転）は正しく実装済み。
- **ナンバー解説文**: `data/numbers/*.json` は独自執筆のドラフト。**森田さん監修で最終化**。既存ブランド流派の文言は転用していません。
- **相性マトリクス / Big5相性重み**: `config/numerology_affinity.json`・`config/big5_compat.json` は初期ヒューリスティクス。森田さんの流派解釈でチューニングしてください。
- **法務**: 生年月日＝個人情報（利用目的の明示・同意・プライバシーポリシー整備が必要）。占い表記の但し書き・景表法ガードは実装済み。

## 技術スタック

Next.js 14（App Router）/ TypeScript / React（モバイルファースト）。数秘・Big5計算は外部依存なしの純ロジック（サーバ／クライアント両対応）。詳細は [`docs/NUMEN_IMPLEMENTATION.md`](docs/NUMEN_IMPLEMENTATION.md)。

---

> 補足: 本リポジトリには別プロジェクト「TimeKeeper Pro」の設計ドキュメント（`docs/TimeKeeperPro_Mac_App_Design.md`, `CLAUDE_DEVELOPMENT_GUIDE.md`）が同梱されています。NUMEN の実装とは独立しています。
