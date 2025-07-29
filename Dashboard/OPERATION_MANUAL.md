# 📖 Phase 1 ダッシュボード運用マニュアル

**作成日**: 2025-07-29  
**バージョン**: v1.0  
**対象**: Phase 1 リアルタイムポジション監視ダッシュボード

---

## 🚀 起動・停止手順

### 標準起動手順

#### 1. 事前確認
```bash
# 作業ディレクトリ移動
cd /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Dashboard

# 必要ファイル確認
ls -la app.py requirements.txt templates/dashboard.html

# MT5データディレクトリ確認
ls -la /tmp/mt5_data/
```

#### 2. 依存関係確認
```bash
# 必要パッケージ確認
pip3 list | grep -E "(flask|socketio|eventlet|watchdog)"

# 不足している場合はインストール
pip3 install -r requirements.txt
```

#### 3. ダッシュボード起動
```bash
# フォアグラウンド起動（開発・デバッグ用）
python3 app.py

# バックグラウンド起動（本番運用）
nohup python3 app.py > dashboard.log 2>&1 &
echo $! > dashboard.pid
```

#### 4. 起動確認
```bash
# プロセス確認
ps aux | grep "python3 app.py" | grep -v grep

# HTTP アクセス確認
curl -s http://localhost:5000 | head -10

# ブラウザアクセス
# http://localhost:5000
```

### 停止手順

#### 1. プロセス停止
```bash
# PIDファイルから停止（推奨）
if [ -f dashboard.pid ]; then
    kill $(cat dashboard.pid)
    rm dashboard.pid
fi

# プロセス名から停止
pkill -f "python3 app.py"

# 強制停止（緊急時のみ）
pkill -9 -f "python3 app.py"
```

#### 2. 停止確認
```bash
# プロセス確認
ps aux | grep "python3 app.py" | grep -v grep

# ポート使用確認
netstat -tlnp | grep :5000
```

---

## 🔧 システム構成

### ファイル構成
```
Dashboard/
├── app.py                          # メインアプリケーション
├── requirements.txt                # 依存関係
├── templates/dashboard.html        # フロントエンド
├── static/                         # 静的ファイル
│   ├── css/dashboard.css
│   └── js/dashboard.js
├── config/                         # 設定ファイル（Phase 2+）
├── legacy_scripts/                 # 過去スクリプト（参考用）
└── docs/                           # ドキュメント
```

### プロセス構成
```
Dashboard Process (app.py)
├── Flask HTTP Server (port 5000)
├── SocketIO WebSocket Server
├── Watchdog File Monitor (/tmp/mt5_data/)
└── Event Handler (position data processing)
```

### データフロー
```
MT5 EA → positions.json → File Monitor → Data Processing → WebSocket → Browser
```

---

## 📊 監視・ヘルスチェック

### システム監視項目

#### 1. プロセス監視
```bash
# ダッシュボードプロセス確認
ps aux | grep "python3 app.py" | grep -v grep

# プロセス詳細情報
if [ -f dashboard.pid ]; then
    PID=$(cat dashboard.pid)
    ps -p $PID -o pid,ppid,cmd,%mem,%cpu,etime
fi
```

#### 2. ネットワーク監視
```bash
# ポート使用状況
netstat -tlnp | grep :5000

# HTTP レスポンス確認
curl -I http://localhost:5000

# WebSocket接続テスト
curl -i -N -H "Connection: Upgrade" \
     -H "Upgrade: websocket" \
     -H "Sec-WebSocket-Version: 13" \
     -H "Sec-WebSocket-Key: x3JJHMbDL1EzLkh9GBhXDw==" \
     http://localhost:5000/socket.io/
```

#### 3. ファイル監視
```bash
# MT5データファイル確認
ls -la /tmp/mt5_data/positions.json
stat /tmp/mt5_data/positions.json

# ファイル更新監視（リアルタイム）
watch -n 1 'stat /tmp/mt5_data/positions.json'
```

#### 4. リソース監視
```bash
# メモリ使用量
if [ -f dashboard.pid ]; then
    PID=$(cat dashboard.pid)
    ps -p $PID -o pid,rss,vsz | tail -1
fi

# CPU使用率
top -p $(cat dashboard.pid) -n 1 | tail -1

# ディスク使用量
df -h /tmp/mt5_data/
```

### ヘルスチェックスクリプト

```bash
#!/bin/bash
# health_check.sh

DASHBOARD_URL="http://localhost:5000"
PID_FILE="dashboard.pid"

echo "=== Dashboard Health Check ==="
echo "Time: $(date)"

# プロセス確認
if [ -f $PID_FILE ] && ps -p $(cat $PID_FILE) > /dev/null; then
    echo "✅ Process: Running (PID: $(cat $PID_FILE))"
else
    echo "❌ Process: Not running"
    exit 1
fi

# HTTP確認
if curl -s $DASHBOARD_URL > /dev/null; then
    echo "✅ HTTP: Accessible"
else
    echo "❌ HTTP: Not accessible"
    exit 1
fi

# データファイル確認
if [ -f "/tmp/mt5_data/positions.json" ]; then
    AGE=$(expr $(date +%s) - $(stat -c %Y /tmp/mt5_data/positions.json))
    if [ $AGE -lt 300 ]; then  # 5分以内の更新
        echo "✅ Data: Fresh (${AGE}s ago)"
    else
        echo "⚠️  Data: Stale (${AGE}s ago)"
    fi
else
    echo "❌ Data: Missing"
fi

echo "✅ Health Check: PASSED"
```

---

## 🚨 トラブルシューティング

### よくある問題と対処法

#### 1. ダッシュボードが起動しない

**症状**: `python3 app.py` でエラー
```
ModuleNotFoundError: No module named 'flask'
```

**対処法**:
```bash
# 依存関係インストール
pip3 install -r requirements.txt

# 権限問題の場合
pip3 install --user flask python-socketio eventlet watchdog
```

---

**症状**: ポート使用エラー
```
Address already in use: ('0.0.0.0', 5000)
```

**対処法**:
```bash
# 既存プロセス確認・停止
lsof -ti:5000 | xargs kill -9

# 別ポート使用（緊急時）
export FLASK_RUN_PORT=5001
python3 app.py
```

#### 2. データが更新されない

**症状**: ブラウザで古いデータのまま

**対処法**:
```bash
# MT5データファイル確認
ls -la /tmp/mt5_data/positions.json
cat /tmp/mt5_data/positions.json

# ファイル監視テスト
echo '{"test": "data"}' > /tmp/mt5_data/positions.json

# ブラウザキャッシュクリア（Ctrl+F5）
```

#### 3. WebSocket接続エラー

**症状**: ブラウザコンソールに接続エラー

**対処法**:
```bash
# ファイアウォール確認
sudo ufw status

# プロキシ・ネットワーク設定確認
# ブラウザの開発者ツールでネットワークタブ確認
```

#### 4. メモリリーク

**症状**: 時間経過でメモリ使用量増加

**対処法**:
```bash
# メモリ使用量監視
watch -n 60 'ps -p $(cat dashboard.pid) -o pid,rss,vsz'

# 再起動（緊急時）
pkill -f "python3 app.py"
python3 app.py > dashboard.log 2>&1 &
```

### ログ分析

#### アプリケーションログ
```bash
# 標準ログ確認
tail -f dashboard.log

# エラーのみ抽出
grep -i error dashboard.log

# 警告・エラー抽出
grep -E "(WARNING|ERROR|CRITICAL)" dashboard.log
```

#### システムログ
```bash
# システムログ確認
journalctl -u python3 --since "1 hour ago"

# プロセス関連ログ
dmesg | grep python3
```

---

## 📈 パフォーマンス最適化

### 基本設定

#### 1. システムリソース制限
```bash
# プロセスリミット設定
ulimit -n 4096  # ファイルハンドル数
ulimit -u 1024  # プロセス数
```

#### 2. Python最適化
```bash
# バイトコードキャッシュ使用
export PYTHONDONTWRITEBYTECODE=0

# メモリ最適化
export PYTHONOPTIMIZE=1
```

### 監視による最適化

#### 1. メモリ使用量監視
```bash
# 定期監視スクリプト
watch -n 300 'ps -p $(cat dashboard.pid) -o pid,rss,vsz,pcpu'
```

#### 2. レスポンス時間監視
```bash
# HTTP レスポンス時間測定
while true; do
    curl -o /dev/null -s -w "%{time_total}\n" http://localhost:5000
    sleep 60
done
```

---

## 🔄 メンテナンス作業

### 日次メンテナンス

#### 1. ヘルスチェック
```bash
./health_check.sh
```

#### 2. ログローテーション
```bash
# ログサイズ確認
du -sh *.log

# 手動ローテーション（1MB超過時）
if [ $(stat -c%s dashboard.log) -gt 1048576 ]; then
    mv dashboard.log dashboard.log.$(date +%Y%m%d)
    touch dashboard.log
fi
```

### 週次メンテナンス

#### 1. パフォーマンス確認
```bash
# 48時間テスト実行（週末）
./test_continuous_operation.py --quick
```

#### 2. ディスク容量確認
```bash
df -h /tmp/mt5_data/
du -sh legacy_scripts/
```

### 月次メンテナンス

#### 1. 依存関係更新
```bash
pip3 list --outdated
# 重要パッケージのみ更新（テスト後）
```

#### 2. セキュリティ確認
```bash
# 不要ファイル削除
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +
```

---

## 📋 運用チェックリスト

### 起動時チェックリスト
- [ ] 依存関係確認
- [ ] MT5データディレクトリ存在確認  
- [ ] ポート使用状況確認
- [ ] プロセス起動確認
- [ ] HTTP アクセス確認
- [ ] WebSocket 接続確認
- [ ] データ更新確認

### 日次チェックリスト
- [ ] プロセス稼働確認
- [ ] メモリ使用量確認
- [ ] ログエラー確認
- [ ] データ更新確認
- [ ] レスポンス時間確認

### 週次チェックリスト
- [ ] パフォーマンステスト実行
- [ ] ログローテーション実行
- [ ] ディスク容量確認
- [ ] バックアップ確認

### 月次チェックリスト
- [ ] 依存関係更新検討
- [ ] セキュリティチェック
- [ ] ドキュメント更新
- [ ] パフォーマンス分析

---

## 📞 サポート情報

### 緊急連絡先
- **システム管理者**: kiro
- **開発担当**: Claude
- **監査**: Gemini

### 関連ドキュメント
- `SYSTEM_ARCHITECTURE_DESIGN.md` - システム設計書
- `IMPROVED_TASK_PLAN_2025-07-29.md` - 改善計画書
- `legacy_scripts/README.md` - 過去スクリプト参照

### 外部リンク
- [Flask公式ドキュメント](https://flask.palletsprojects.com/)
- [python-socketio](https://python-socketio.readthedocs.io/)
- [watchdog](https://pythonhosted.org/watchdog/)

---

**作成者**: Claude  
**最終更新**: 2025-07-29  
**次回見直し**: Phase 2 開始時