# MQL5技術仕様書 - 実装絶対遵守事項

## 🚨 ファイル操作制限（最重要）

### ❌ 禁止事項
- `/tmp/`、`/home/`等のLinuxパスへの直接書き込み
- `FileOpen()`でのサンドボックス外パス指定
- Wine仮想パスへの直接アクセス

### ✅ 許可事項
- `MQL5/Files/`ディレクトリ内のみ
- `FILE_COMMON`フラグ使用時：`Terminal/Common/Files/`
- 相対パス指定（例：`"data/positions.json"`）

**正しい実装例:**
```mql5
// ✅ 正しい
string file_path = "dashboard_data.json";
int handle = FileOpen(file_path, FILE_WRITE|FILE_TXT);

// ❌ 絶対に禁止
int handle = FileOpen("/tmp/mt5_data/positions.json", FILE_WRITE|FILE_TXT);
```

## 🕒 タイマー機能

### ❌ 禁止事項
- `GetTickCount()`による手動タイマー実装
- `Sleep()`による処理ブロック
- `OnTick()`内での重い定期処理

### ✅ 正しい実装
```mql5
// ✅ EventSetTimer使用
int OnInit() {
    EventSetTimer(5); // 5秒間隔
    return INIT_SUCCEEDED;
}

void OnTimer() {
    // 定期実行処理
    ExportDashboardData();
}

void OnDeinit(const int reason) {
    EventKillTimer();
}
```

## 🔐 セキュリティ制限

### MQL5サンドボックス
- ファイルシステムアクセスは厳格に制限
- ネットワーク通信は専用関数のみ
- 外部プロセス実行不可

### 通信方法
- **推奨**: TCP/IPソケット通信（`SocketCreate`, `SocketConnect`）
- **代替**: 許可ディレクトリでのファイル共有

## 📊 データ型・精度

### 価格データ
- `double`型使用必須
- 小数点以下5桁まで対応
- `DoubleToString(price, 5)`で出力

### 時刻データ
- `datetime`型使用
- `TimeCurrent()`で現在時刻取得
- ISO8601形式変換：`TimeToString(time, TIME_DATE|TIME_SECONDS)`

## 🎯 EA開発ベストプラクティス

### OnTick()内制限
- 重い処理は避ける
- ファイルI/Oは最小限
- 計算集約的処理は別関数化

### エラーハンドリング
```mql5
// ✅ 必須エラーチェック
if(handle == INVALID_HANDLE) {
    Print("ファイルオープンエラー: ", GetLastError());
    return;
}
```

## 🚨 実装前チェックリスト

- [ ] ファイルパスがサンドボックス内か？
- [ ] タイマーはEventSetTimer使用か？
- [ ] エラーハンドリングは適切か？
- [ ] OnTick()内の処理は軽量か？
- [ ] データ型は適切か？

**この仕様書への準拠は絶対条件です。違反する実装は一切受け入れられません。**