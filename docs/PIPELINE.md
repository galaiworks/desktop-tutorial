# 動画編集パイプライン Caesura-Coconala Edition

[LOOP.md](./LOOP.md) の loop contract に基づく、1案件(S1→S6)の動画編集パイプラインです。

## 全体像

```
jobs/<job_id>/job.yaml(人間が作成・読み取り専用)
      │
      ▼
S1 素材取り込み ── whisper 文字起こし・機械検品・モザイク候補スキャン
S2 カット編集   ── Maker: editor(Sonnet)→ 尺を機械検証 → ffmpeg レンダリング
S3 テロップ     ── Maker: telop_writer(Sonnet)→ はみ出しを機械検証 → SRT生成
S4 ミックス     ── Maker: music_selector(Sonnet)→ ffmpeg BGMミックス + -14 LUFS 正規化
S5 人間ゲート   ── プレビュー承認 / モザイク承認 / サムネ選択(3ゲートとも人間必須)
S6 QA・納品    ── 機械検証4項目 + Checker: checker(Opus)校正 → output/ に納品パッケージ
```

## セットアップ

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
export SLACK_WEBHOOK_URL=https://hooks.slack.com/...   # 任意(L6通知)

# 外部ツール(必須: ffmpeg/ffprobe/whisper、任意: auto-editor)
python pipeline/run.py --check-env
```

## 使い方

案件受注・素材受領・DM相談の転記は人間の責任範囲です(LOOP.md §2)。
`jobs/<job_id>/job.yaml` を作成し、素材を `assets/` に置いてから手動で起動します。

```bash
# 実行(中断していれば state.json から自動再開)
python pipeline/run.py jobs/sample_job

# 進捗確認
python pipeline/run.py jobs/sample_job --status

# S5 人間ゲート(パイプラインが exit code 2 で待機したら)
python pipeline/run.py jobs/sample_job --approve preview      # work/final_draft.mp4 確認後
python pipeline/run.py jobs/sample_job --approve mosaic       # logs/mosaic_candidates.json 確認後
python pipeline/run.py jobs/sample_job --select-thumbnail 2   # preview/ の候補3枚から選択

# 承認後に再実行して続行
python pipeline/run.py jobs/sample_job
```

終了コード: `0` 完了 / `1` 停止(エスカレーション・予算超過等)/ `2` S5 承認待ち

## LOOP.md との対応

| 契約 | 実装 |
|---|---|
| §1 Goal | `stages/s6_qa.py` — 尺・-14 LUFS±1・黒フレーム0・字幕はみ出し0・Checker校正パスで `output/` に納品パッケージ |
| §2 Trigger | 手動CLIのみ。cron等の自動起動なし |
| §3 L1 反復上限 | `guards.with_retry` — 各ステージ3回まで、超過でエスカレーション |
| §3 L1 差分停止 | `guards.check_convergence` — カットリスト95%以上同一×2回で収束 |
| §3 L1 予算上限 | `budget.Budget` — API実測トークン→円換算、¥2,000超過で即停止 |
| §4 L2 Maker-Checker | Maker(editor/telop_writer/music_selector)= `claude-sonnet-5`、Checker(checker)= `claude-opus-4-8`。証跡 `logs/checker_report.json` |
| §4 機械検証 | `media.py` — ffprobe/loudnorm/blackdetect/volumedetect をスクリプト実行。LLM自己申告は不採用 |
| §5 L3 | `permissions.Sandbox` — 書き込みは `jobs/<job_id>/` のみ、`job.yaml` 書換禁止、ツール許可リスト、BGMはローカルライブラリ限定 |
| §6 L4 | `state.py` — 記録4項目(ステージ/成果物パス/コスト累計/直近エラー)。まっさらなセッションから再開可能 |
| §7 L6 | `notify.py` + `EscalationError` — 尺超過・モザイク候補・音声品質・NG矛盾・予算/リトライ上限で停止して通知 |
| 自律度 L1.5 | S1〜S4自動、S5の3ゲートは人間必須。モザイク承認は恒久的に人間ゲート(コードに昇格経路なし) |

## ディレクトリ構成

```
pipeline/            # パイプライン本体
  run.py             # CLI・オーケストレーター
  config.py          # ガード定数・モデル・QA基準
  guards.py          # L1 三重ガード
  permissions.py     # L3 サンドボックス
  state.py           # L4 state.json
  budget.py          # 予算トラッカー
  llm.py             # Maker/Checker 呼び出し(structured outputs)
  media.py           # ffmpeg/ffprobe/whisper 機械検証・レンダリング
  telop.py           # 字幕はみ出し検査・SRT変換
  notify.py          # L6 通知(ローカル/Slack)
  stages/            # S1〜S6
agents/              # エージェント定義(システムプロンプト)
jobs/<job_id>/       # 案件(job.yaml は人間が作成)
  state.json         # L4 状態(自動生成)
  work/  logs/  preview/  output/
assets/              # 素材・BGMライブラリ(読み取り専用)
tests/               # 単体テスト + S1→S6 統合テスト
```

## テスト

```bash
python -m pytest tests/ -v
```

メディア処理とLLMをモック化した統合テスト(`tests/test_integration.py`)で、
モザイクエスカレーション→承認→S5ゲート→納品完了までの全フローを検証しています。
