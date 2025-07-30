# TrailToBreakeven機能 - MQL5技術仕様書

## 1. 取引API仕様の詳細

### 1.1 PositionModify() - 推奨メソッド
```mql5
// CTradeクラスの使用（推奨）
#include <Trade\Trade.mqh>
CTrade trade;

// ポジション修正の実装
bool ModifyPosition(string symbol, double new_sl, double new_tp)
{
    if(!trade.PositionModify(symbol, new_sl, new_tp))
    {
        Print("PositionModify失敗: ", trade.ResultRetcode(), " - ", trade.ResultRetcodeDescription());
        return false;
    }
    return true;
}
```

**重要な技術的違い:**
- **PositionModify()**: 既存ポジションの直接修正、戻り値でtrue/falseを返すが成功保証なし
- **OrderModify()**: 待機注文専用、ポジション修正には使用不可
- **必須確認**: `trade.ResultRetcode()`で実際のサーバー応答を確認

### 1.2 ポジション管理API仕様
```mql5
// ポジション選択と情報取得
bool SelectAndGetPositionInfo(string symbol, double &open_price, double &current_sl, double &profit)
{
    if(!PositionSelect(symbol))
    {
        Print("ポジション選択失敗: ", symbol);
        return false;
    }
    
    open_price = PositionGetDouble(POSITION_PRICE_OPEN);
    current_sl = PositionGetDouble(POSITION_SL);
    profit = PositionGetDouble(POSITION_PROFIT);
    
    return true;
}
```

**重要なプロパティ:**
- `POSITION_PRICE_OPEN`: エントリー価格
- `POSITION_PRICE_CURRENT`: 現在価格（BUY/SELLに応じてBid/Ask自動選択）
- `POSITION_SL`: 現在のストップロス
- `POSITION_PROFIT`: 現在の損益

## 2. 価格処理・正規化の最適化手法

### 2.1 価格正規化の正確な実装
```mql5
// 最適化された価格正規化関数
double NormalizePrice(string symbol, double price)
{
    double tick_size = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
    if(tick_size == 0) return price; // エラー回避
    
    return MathRound(price / tick_size) * tick_size;
}

// ストップレベル正規化（金属・CFD対応）
double NormalizeStopLevel(string symbol, double price)
{
    // Pointではなく、SYMBOL_TRADE_TICK_SIZEを使用（金属対応）
    double tick_size = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
    return NormalizePrice(symbol, price);
}
```

### 2.2 価格精度の動的取得
```mql5
// シンボル固有の精度取得
int GetSymbolDigits(string symbol)
{
    return (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
}

// 最小価格変動の取得
double GetSymbolPoint(string symbol)
{
    return SymbolInfoDouble(symbol, SYMBOL_POINT);
}
```

## 3. ブローカー環境対応

### 3.1 口座タイプ確認
```mql5
// 口座タイプとFIFOルール確認
bool CheckAccountRestrictions()
{
    bool is_fifo = (bool)AccountInfoInteger(ACCOUNT_FIFO_CLOSE);
    bool is_hedging = ((ENUM_ACCOUNT_MARGIN_MODE)AccountInfoInteger(ACCOUNT_MARGIN_MODE) == ACCOUNT_MARGIN_MODE_RETAIL_HEDGING);
    
    Print("FIFO口座: ", is_fifo);
    Print("ヘッジング口座: ", is_hedging);
    
    return true;
}
```

### 3.2 ストップレベル制限の確認
```mql5
// ストップレベル制限チェック
bool CheckStopLevel(string symbol, double entry_price, double stop_price, bool is_buy)
{
    long stops_level = SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL);
    double min_distance = stops_level * SymbolInfoDouble(symbol, SYMBOL_POINT);
    
    double current_price = is_buy ? 
        SymbolInfoDouble(symbol, SYMBOL_BID) : 
        SymbolInfoDouble(symbol, SYMBOL_ASK);
    
    double distance = is_buy ? 
        current_price - stop_price : 
        stop_price - current_price;
    
    if(distance < min_distance)
    {
        Print("ストップレベル違反: 最小距離=", min_distance, " 実際=", distance);
        return false;
    }
    
    return true;
}
```

### 3.3 フィル・ポリシーの最適化
```mql5
// 適切なフィル・ポリシー選択
ENUM_ORDER_TYPE_FILLING GetOptimalFillPolicy(string symbol)
{
    long filling_modes = SymbolInfoInteger(symbol, SYMBOL_FILLING_MODE);
    
    // FOK優先（完全約定）
    if((filling_modes & SYMBOL_FILLING_FOK) != 0)
        return ORDER_FILLING_FOK;
    
    // IOC次点（部分約定許可）
    if((filling_modes & SYMBOL_FILLING_IOC) != 0)
        return ORDER_FILLING_IOC;
    
    // デフォルト（Return）
    return ORDER_FILLING_RETURN;
}
```

## 4. エラーハンドリング・パフォーマンス最適化

### 4.1 包括的エラーハンドリング
```mql5
// 統合エラー処理システム
class TradeErrorHandler
{
private:
    int m_retry_count;
    int m_max_retries;
    
public:
    TradeErrorHandler() : m_retry_count(0), m_max_retries(3) {}
    
    bool HandleTradeError(uint error_code)
    {
        switch(error_code)
        {
            case TRADE_RETCODE_REQUOTE:
            case TRADE_RETCODE_PRICE_OFF:
                if(m_retry_count < m_max_retries)
                {
                    m_retry_count++;
                    Sleep(100); // 短時間待機
                    return true; // リトライ実行
                }
                break;
                
            case TRADE_RETCODE_INVALID_STOPS:
                Print("無効なストップレベル - 価格調整が必要");
                return false;
                
            case TRADE_RETCODE_HEDGE_PROHIBITED:
                Print("ヘッジング禁止口座");
                return false;
                
            default:
                Print("取引エラー: ", error_code);
                return false;
        }
        
        return false;
    }
    
    void Reset() { m_retry_count = 0; }
};
```

### 4.2 パフォーマンス最適化
```mql5
// 最適化されたTrailToBreakeven実装
class OptimizedTrailToBreakeven
{
private:
    string m_symbol;
    double m_threshold_points;
    TradeErrorHandler m_error_handler;
    
    // キャッシュされた値
    double m_cached_tick_size;
    double m_cached_point;
    int m_cached_digits;
    
public:
    OptimizedTrailToBreakeven(string symbol, double threshold_points) :
        m_symbol(symbol), m_threshold_points(threshold_points)
    {
        // 初期化時にシンボル情報をキャッシュ
        CacheSymbolInfo();
    }
    
private:
    void CacheSymbolInfo()
    {
        m_cached_tick_size = SymbolInfoDouble(m_symbol, SYMBOL_TRADE_TICK_SIZE);
        m_cached_point = SymbolInfoDouble(m_symbol, SYMBOL_POINT);
        m_cached_digits = (int)SymbolInfoInteger(m_symbol, SYMBOL_DIGITS);
    }
    
    double NormalizePriceFast(double price)
    {
        return MathRound(price / m_cached_tick_size) * m_cached_tick_size;
    }
    
public:
    bool Execute()
    {
        // 高速ポジション確認
        if(!PositionSelect(m_symbol))
            return false;
        
        double open_price = PositionGetDouble(POSITION_PRICE_OPEN);
        double current_sl = PositionGetDouble(POSITION_SL);
        double current_profit = PositionGetDouble(POSITION_PROFIT);
        
        // 利益閾値チェック（ポイント変換なし、直接比較）
        if(current_profit < m_threshold_points * m_cached_point)
            return false;
        
        // ブレイクイーブン計算
        double new_sl = NormalizePriceFast(open_price);
        
        // 既にブレイクイーブンの場合はスキップ
        if(MathAbs(current_sl - new_sl) < m_cached_tick_size)
            return true;
        
        // ストップレベル確認
        long pos_type = PositionGetInteger(POSITION_TYPE);
        if(!CheckStopLevel(m_symbol, open_price, new_sl, pos_type == POSITION_TYPE_BUY))
            return false;
        
        // ポジション修正実行
        CTrade trade;
        trade.SetTypeFilling(GetOptimalFillPolicy(m_symbol));
        
        m_error_handler.Reset();
        bool success = trade.PositionModify(m_symbol, new_sl, PositionGetDouble(POSITION_TP));
        
        if(!success)
        {
            if(m_error_handler.HandleTradeError(trade.ResultRetcode()))
            {
                // リトライ
                return trade.PositionModify(m_symbol, new_sl, PositionGetDouble(POSITION_TP));
            }
        }
        
        return success;
    }
};
```

## 5. 実装ベストプラクティス

### 5.1 メモリ効率化
- シンボル情報のキャッシュ化
- 不要なオブジェクト生成回避
- 静的変数の活用

### 5.2 実行効率化
- 数学計算の最小化
- 条件分岐の最適化
- API呼び出し回数の削減

### 5.3 堅牢性確保
- 多段階エラーハンドリング
- リトライ機構の実装
- ブローカー固有制限への対応

## 6. 使用例

```mql5
// EA内での使用例
int OnInit()
{
    // 初期化
    return INIT_SUCCEEDED;
}

void OnTick()
{
    OptimizedTrailToBreakeven trail("EURUSD", 100); // 10ポイント利益で発動
    trail.Execute();
}
```

## 7. 注意事項

1. **価格正規化**: 必ずTICK_SIZEベースで正規化
2. **ストップレベル**: ブローカーの最小距離制限を確認
3. **口座タイプ**: FIFO/ヘッジング制限を考慮
4. **エラーハンドリング**: リトライ機構を実装
5. **パフォーマンス**: 頻繁な処理のため最適化が重要

この技術仕様書に基づいて実装することで、高品質で互換性の高いTrailToBreakeven機能を構築できます。