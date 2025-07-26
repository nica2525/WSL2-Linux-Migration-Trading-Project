# /session-start カスタムコマンド

セッション開始時のCLAUDE.md必須プロトコルを一括実行します。

## Git履歴確認
最近のコミット履歴とプロジェクト状況を確認：

```bash
git log --oneline -10
```

## cron自動化システム確認
システムの自動化機能が正常動作しているか確認：

```bash
crontab -l
ps aux | grep cron | grep -v grep
```

## 自動化ログ確認
Git自動保存とシステム監視の動作状況を確認：

```bash
tail -10 .cron_git_auto_save.log
tail -10 .cron_monitor.log
```

## セッション記録確認
最新の作業記録とタスク状況を確認：

```bash
ls -la 文書/記録/セッション記録*.md | tail -5
cat "$(ls -t 文書/記録/セッション記録*.md | head -1)"
```

## 品質状況確認
現在のプロジェクト品質指標を確認：

```bash
cat 文書/管理/現在の品質状況.md
```

このコマンドによりセッション開始に必要な全情報が一度に確認できます。
