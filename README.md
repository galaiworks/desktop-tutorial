# TimeKeeper Pro for Mac

プロフェッショナル向けタイムキーパー macOSアプリケーション

## 概要

セミナー登壇者・司会者がスライド操作を妨げることなく、画面上に半透明のカウントダウンタイマーを表示し、時間帯に応じた色分けで直感的に残り時間を把握できるツールです。

## 特徴

- **フローティングタイマー**: 常に最前面に表示、クリックスルー対応
- **フェーズカラー**: 残り時間に応じて自動で色が変化（最大8段階）
- **マルチモニター対応**: 複数ディスプレイでの表示をサポート
- **リモートコントロール**: 同一LAN上のスマートフォン・タブレットのブラウザからタイマーを遠隔操作（PIN認証・QRコード対応）
- **ユニバーサルデザイン**: VoiceOver、ダイナミックタイプ、フルキーボードアクセス対応
- **多言語対応**: 日本語、英語、中国語、ドイツ語、フランス語、スペイン語、韓国語

## ドキュメント

| ファイル | 説明 |
|:---|:---|
| [docs/TimeKeeperPro_Mac_App_Design.md](docs/TimeKeeperPro_Mac_App_Design.md) | 設計仕様書（機能、UI、アーキテクチャ） |
| [CLAUDE_DEVELOPMENT_GUIDE.md](CLAUDE_DEVELOPMENT_GUIDE.md) | Claude Code用開発ガイド |

## 開発環境

- **言語**: Swift 5.10+
- **フレームワーク**: SwiftUI, AppKit
- **最小サポートOS**: macOS 14 Sonoma
- **IDE**: Xcode 15+

## Claude Codeでの開発開始方法

```bash
# 1. リポジトリをクローン
git clone https://github.com/galaiworks/desktop-tutorial.git
cd desktop-tutorial

# 2. Claude Codeを起動
claude

# 3. 設計書を読み込ませる
> /read docs/TimeKeeperPro_Mac_App_Design.md

# 4. 開発ガイドに従って開発を開始
> /read CLAUDE_DEVELOPMENT_GUIDE.md
```

## ライセンス

MIT License
