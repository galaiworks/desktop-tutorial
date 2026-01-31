# TimeKeeper Pro for Mac: Claude Code 開発ガイド

**バージョン**: 1.0  
**作成日**: 2026年1月31日

## 1. 概要

このドキュメントは、AIコーディングエージェント「Claude Code」を用いて、macOSアプリ「TimeKeeper Pro」を開発するための手順書です。各ステップは、Claude Codeに直接入力できるプロンプト形式で記述されています。

開発を始める前に、必ず `docs/TimeKeeperPro_Mac_App_Design.md` をClaude Codeに読み込ませてください。

```bash
# Claude Codeを起動し、設計書を読み込ませる
claude
> /read docs/TimeKeeperPro_Mac_App_Design.md
```

## 2. 開発フェーズ

### Phase 1: プロジェクトのセットアップと基本構造

**目的**: Xcodeプロジェクトを作成し、MVVMアーキテクチャに基づいた基本的なファイルとフォルダ構造を構築します。

**プロンプト例**:

1.  `> TimeKeeperProという名前で、SwiftUIを使った新しいmacOSアプリのXcodeプロジェクトを作成して。ターゲットはmacOS 14.0以降にして。`
2.  `> 設計書の「7.3 ファイル構成」に基づいて、以下のディレクトリを作成して：Views, ViewModels, Models, Services, Resources`
3.  `> 以下の空のSwiftファイルを作成して：
    - Views/TimerView.swift
    - ViewModels/TimerViewModel.swift
    - Models/TimerPhase.swift
    - Services/TimerEngine.swift`
4.  `> TimeKeeperProApp.swiftを編集して、TimerViewをメインのビューとして表示するようにして。`

### Phase 2: コアタイマー機能の実装

**目的**: カウントダウンタイマーの基本的なロジックと、それを表示するUIを実装します。

**プロンプト例**:

1.  `> TimerEngine.swiftに、Combineフレームワークを使って1秒ごとにカウントダウンするタイマーロジックを実装して。`
2.  `> TimerViewModel.swiftで、TimerEngineのインスタンスを保持し、残り時間を@Publishedプロパティとして公開して。`
3.  `> TimerView.swiftに、残り時間をMM:SS形式で表示するTextビューと、「スタート/一時停止」「リセット」ボタンを配置して。`
4.  `> ボタンのアクションをTimerViewModelにバインドして、タイマーを操作できるようにして。`

### Phase 3: フローティングウィンドウと表示設定

**目的**: AppKitを連携させ、常に最前面に表示される半透明のフローティングウィンドウを実装します。

**プロンプト例**:

1.  `> AppKitをインポートして、NSWindowをカスタマイズするコードを追加して。ウィンドウをフローティングさせ、背景を透明にする設定を実装して。`
2.  `> ウィンドウのクリックスルー（ignoresMouseEvents）を切り替える機能を実装して。`
3.  `> ウィンドウの透明度を調整するスライダーをSettingsViewに追加して。`

### Phase 4: ユニバーサルデザインと多言語対応

**目的**: アクセシビリティと国際化の機能を実装します。

**プロンプト例**:

1.  `> String Catalogs (.xcstrings) をプロジェクトに追加して、日本語と英語のローカライゼーションを設定して。`
2.  `> TimerViewのすべてのUIテキストを、String Catalogsから読み込むように変更して。`
3.  `> すべてのボタンとコントロールに、VoiceOverが読み上げるためのアクセシビリティラベルを追加して。`
4.  `> Textビューがシステムのダイナミックタイプ設定に追従するようにして。`

### Phase 5: テンプレート機能とデータ永続化

**目的**: ユーザーが設定をテンプレートとして保存・復元できるようにします。

**プロンプト例**:

1.  `> Template.swiftモデルを作成して。Codableに準拠させて。`
2.  `> TemplateManager.swiftを作成し、テンプレートをJSONファイルとしてローカルに保存・読み込みする機能を実装して。`
3.  `> CloudKitを有効にして、TemplateManagerにiCloud経由でテンプレートを同期する機能を実装して。`

## 3. デバッグとテスト

- **エラー修正**: エラーメッセージをそのままClaude Codeに貼り付け、「このエラーを解決して」と指示します。
- **ユニットテスト**: `> TimerEngineのロジックを検証するためのXCTestケースを作成して。`

このガイドに沿って開発を進めることで、設計書に基づいた高品質なアプリケーションを効率的に構築できます。
