# GitHub調査結果: MQL4 BreakoutEA修正のためのベストプラクティス分析

## 調査目的
Geminiが指摘したBreakoutEA_Complete.mq4の致命的バグを修正するため、GitHubの実績あるMQL4コードを調査し、安全な実装パターンを特定する。

## 調査対象の問題点
1. **無限再帰バグ**: LoadWFAParameters()関数の再帰呼び出し
2. **リスク計算の不正確性**: 口座残高基準の誤り
3. **OnTrade統計処理**: 決済注文の処理漏れ

## 調査結果

### 1. ファイル処理ベストプラクティス
**参照元**: KeisukeIwabuchi/MQL4-File
**GitHub URL**: https://github.com/KeisukeIwabuchi/MQL4-File

#### 安全なファイル読み込みパターン:
```cpp
static string File::Read(const string path) {
   int handle = File::openHandle(path, READ);
   if(handle == INVALID_HANDLE) return("");  // 再帰なし、デフォルト値返却
   
   // ファイル処理
   string result = performFileOperations(handle);
   
   File::closeHandle(handle);  // 必ずクリーンアップ
   return result;
}
```

#### 重要なポイント:
- **INVALID_HANDLE時は即座にデフォルト値を返す**
- **絶対に再帰呼び出ししない**
- **try-finallyパターンでリソース確実解放**
- **while(!FileIsEnding(handle))で無限ループ防止**

### 2. リスク管理・ポジションサイジング
**参照元**: LeonardoCiaccio/Position-Size-Calculator
**GitHub URL**: https://github.com/LeonardoCiaccio/Position-Size-Calculator

#### 正確なリスク計算パターン:
```cpp
// 口座残高基準の選択肢
enum ACCOUNT_MONEY_TYPE {
    FREE_MARGIN,
    BALANCE,
    EQUITY
};

double CalculatePositionSize(double riskPercent, double stopLossPips) {
    double accountMoney = 0;
    switch(accountMoneyType) {
        case FREE_MARGIN: accountMoney = AccountFreeMargin(); break;
        case BALANCE: accountMoney = AccountBalance(); break;
        case EQUITY: accountMoney = AccountEquity(); break;
    }
    
    if(accountMoney <= 0) return 0;  // 安全チェック
    
    // リスク計算
    double riskAmount = accountMoney * (riskPercent / 100.0);
    // ... 以下計算処理
}
```

#### 重要なポイント:
- **期間開始時の残高を基準に計算**
- **複数の口座残高タイプ対応**
- **NormalizeDouble()で精度確保**
- **パラメータ検証（unitCost > 0等）**

### 3. OnTrade処理・統計計算
**参照元**: KeisukeIwabuchi/MQL4-TradeManager
**GitHub URL**: https://github.com/KeisukeIwabuchi/MQL4-TradeManager

#### 全注文処理パターン:
```cpp
// MQL4にはOnTradeがないため、カスタム実装
static int previousHistoryTotal = 0;

void OnTick() {
    int currentHistoryTotal = OrdersHistoryTotal();
    
    if(currentHistoryTotal != previousHistoryTotal) {
        // 新しい決済注文を処理
        ProcessNewHistoryOrders(previousHistoryTotal, currentHistoryTotal);
        previousHistoryTotal = currentHistoryTotal;
    }
}

void ProcessNewHistoryOrders(int fromIndex, int toIndex) {
    for(int i = fromIndex; i < toIndex; i++) {
        if(OrderSelect(i, SELECT_BY_POS, MODE_HISTORY)) {
            // 各決済注文の統計処理
            UpdateTradeStatistics();
        }
    }
}
```

#### 重要なポイント:
- **OrdersHistoryTotal()の変化を監視**
- **逆順ループで最新から処理**
- **全ての決済注文を漏れなく処理**
- **静的変数で前回状態を記憶**

## 我々のBreakoutEAへの適用方針

### 1. LoadWFAParameters()修正
```cpp
bool LoadWFAParameters() {
    if(!UseWFAParameters) {
        return LoadDefaultParameters();  // デフォルト設定
    }
    
    int handle = FileOpen(WFAParameterFile, FILE_READ|FILE_TXT|FILE_COMMON);
    if(handle == INVALID_HANDLE) {
        Print("⚠️ WFAファイル読み込み失敗、デフォルト使用");
        return LoadDefaultParameters();  // 再帰なし
    }
    
    // パラメータ読み込み処理
    FileClose(handle);
    return true;
}
```

### 2. リスク計算修正
```cpp
void UpdateRiskStatistics() {
    datetime current_time = TimeLocal();
    
    // 期間変更時に開始残高を更新
    if(TimeDay(current_time) != TimeDay(g_last_trade_date)) {
        g_day_start_balance = AccountBalance();  // 日開始残高
        g_daily_loss = 0.0;
    }
    
    // 日次損失を開始残高基準で計算
    if(g_day_start_balance > 0) {
        g_daily_loss = (g_day_start_balance - AccountBalance()) / g_day_start_balance * 100.0;
    }
}
```

### 3. OnTrade処理修正
```cpp
static int g_previous_history_total = 0;

void OnTick() {
    int current_history_total = OrdersHistoryTotal();
    
    if(current_history_total > g_previous_history_total) {
        ProcessNewClosedOrders(g_previous_history_total, current_history_total);
        g_previous_history_total = current_history_total;
    }
    
    // 既存のブレイクアウトロジック
}
```

## 期待される改善効果
1. **安全性向上**: 無限再帰バグの完全排除
2. **精度向上**: 正確なリスク計算による資金管理
3. **信頼性向上**: 全決済注文の確実な統計処理
4. **パフォーマンス**: 効率的なファイル・メモリ管理

## 次のステップ
1. 上記パターンに基づくコード修正実装
2. ローカルでのコンパイル・構文チェック
3. 修正版のGemini再査読
4. ストラテジーテスターでの動作確認