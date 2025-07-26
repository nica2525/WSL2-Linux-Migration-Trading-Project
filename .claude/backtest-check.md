# /backtest-check カスタムコマンド

MT4バックテスト結果の総合確認を行います。EA開発・分析時に使用。

## MT4結果ディレクトリ確認
バックテスト結果ファイルの一覧とサイズを確認：

```bash
ls -lah MT4_Results/
```

## FXTファイル容量確認
全ティックデータファイルの容量を確認：

```bash
du -h MT4_Results/*.fxt 2>/dev/null || echo "No .fxt files found"
```

## レポートファイル確認
HTMLレポートの存在と更新日時を確認：

```bash
ls -la MT4_Results/*.htm 2>/dev/null || echo "No .htm reports found"
```

## バックテスト操作履歴
最近のテスト実行履歴を確認：

```bash
if [ -f "MT4_Results/バックテスト操作履歴.txt" ]; then
    echo "=== 最新のバックテスト操作履歴 ==="
    tail -10 "MT4_Results/バックテスト操作履歴.txt"
else
    echo "バックテスト操作履歴ファイルが見つかりません"
fi
```

## ディスク使用量警告
結果フォルダの総容量を確認：

```bash
echo "=== MT4結果フォルダ総容量 ==="
du -sh MT4_Results/
```

このコマンドによりバックテスト結果の状況が一度に把握できます。
