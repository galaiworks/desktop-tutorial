# LOOP.md — 動画編集パイプライン loop contract

対象: Caesura-Coconala Edition(タスク内ループ = 1案件のS1→S6実行。セッション横断ループは対象外、案件受注は人間トリガーのため)

## 1. Goal
job.yamlで指定された1案件について、S6のQAチェック(尺・-14 LUFS±1・黒フレームゼロ・字幕はみ出しゼロ・Checker校正パス)がすべてグリーンになり、output/に納品パッケージが揃うまで。

## 2. Trigger
手動(`python pipeline/run.py jobs/<job_id>`)。cron/自動起動は行わない。案件受注・素材受領・DM相談の転記が人間の責任範囲のため。

## 3. Stop(L1三重ガード)
- 反復上限: 各ステージのリトライは3回まで。3回失敗で停止しエスカレーション
- 差分停止: カットリスト再生成で前回と95%以上同一の結果が2回続いたら収束とみなし先に進む(無限微修正の防止)
- 予算上限: 1案件あたりAPIコスト2,000円。超過で即停止

## 4. Verify(L2 Maker-Checker)
- Maker: editor / telop_writer / music_selector(Sonnet系)
- Checker: checker.md(Opus系、Makerと別エージェント)。証跡は `logs/checker_report.json`(誤字リスト・尺検証・ラウドネス実測値・NG事項照合結果)
- 機械検証: ffprobe/ラウドネス測定はスクリプトで実行し、LLMの自己申告を採用しない

## 5. Permission(L3)
- 自動許可: jobs/<job_id>/ 配下の読み書き、ffmpeg/whisper/auto-editorの実行、assets/の読み取り
- 禁止: jobs/外への書き込み、素材の外部送信、外部サイトからのBGM/SE取得、ギガファイル便等へのアップロード、job.yamlの書き換え

## 6. Memory(L4)
状態ファイル: `jobs/<job_id>/state.json`
記録4項目: ①現在ステージと完了ステージ ②中間成果物パス(cutlist.json / telop.json / mix.json) ③消費コスト累計 ④直近エラーとリトライ回数。
セッションはまっさらで再起動し、state.jsonから続行する。

## 7. Escalate(L6)
以下は停止して人間(ガライさん)へ通知(ローカル通知 or Slack webhook):
- 目標尺にカットで収まらない(素材の情報密度が高すぎる)
- モザイク候補の検出(S5承認ゲートとは別に、検出時点で即リスト提示)
- 音声品質が閾値以下(SNR低・録音破綻)で自動補正の範囲を超える
- job.yamlのNG事項と矛盾する判断が必要になった場合
- 予算・リトライ上限到達

## 自律度
初期値 **L1.5 相当**(S1〜S4は自動実行するが、S5プレビュー承認・モザイク承認・サムネ選択の3ゲートは人間必須)。
昇格対象外: モザイク承認は事故リスクの性質上、恒久的に人間ゲートとする。
