# MT4 WFA パラメータ読み込み仕様書

## 1. 分析結果概要

### 1.1 発見したWFAファイル構造
プロジェクト内で以下のWFA最適化結果ファイルを確認：

**主要ファイル:**
- `cost_resistant_wfa_results_ALL_BIAS_FIXED.json` - メインのWFA結果
- `parallel_wfa_results_20250717_205703.json` - 並列最適化結果
- `enhanced_slippage_wfa_results_20250717_213013.json` - スリッページ考慮版
- `wfa_config.json` - WFA設定ファイル

### 1.2 パラメータ構造分析

#### 基本戦略パラメータ
```json
{
  "base_parameters": {
    "h4_period": 24,
    "h1_period": 24,
    "atr_period": 14,
    "profit_atr": 2.5,
    "stop_atr": 1.3,
    "min_break_pips": 5,
    "spread_pips": 1.5,
    "commission_pips": 0.3
  }
}
```

#### コスト耐性パラメータ
```json
{
  "cost_resistance_parameters": {
    "min_atr_multiple": 1.0,
    "min_trend_strength": 0.1,
    "min_profit_pips": 4.0,
    "min_cost_ratio": 2.0,
    "atr_period": 14,
    "trend_ma_long_period": 50,
    "trend_ma_short_period": 20,
    "breakout_confirmation": 2,
    "cost_pips": 2.0
  }
}
```

#### WFAフォールド最適化結果
```json
{
  "wfa_results_raw": [
    {
      "fold_id": 1,
      "trades": 576,
      "winning_trades": 369,
      "win_rate": 0.640625,
      "profit_factor": 2.2985887013624713,
      "sharpe_ratio": 0.15569410139250078
    }
  ]
}
```

## 2. MT4統合用パラメータファイル仕様

### 2.1 パラメータファイル形式 - JSON版

**ファイル名**: `mt4_wfa_parameters_YYYYMMDD.json`

```json
{
  "meta": {
    "creation_date": "2025-07-19T21:00:00",
    "strategy_name": "Cost_Resistant_Breakout",
    "version": "1.0",
    "symbol": "EURUSD",
    "timeframe": "M5",
    "wfa_source_file": "cost_resistant_wfa_results_ALL_BIAS_FIXED.json",
    "best_fold": 1,
    "selection_criteria": "highest_sharpe_ratio"
  },
  "trading_parameters": {
    "h4_period": 24,
    "h1_period": 24,
    "atr_period": 14,
    "profit_atr_multiplier": 2.5,
    "stop_atr_multiplier": 1.3,
    "min_break_pips": 5,
    "breakout_confirmation": 2
  },
  "risk_management": {
    "max_risk_per_trade": 1.5,
    "min_atr_multiple": 1.0,
    "min_profit_pips": 4.0,
    "min_cost_ratio": 2.0,
    "max_daily_trades": 6,
    "max_consecutive_losses": 4
  },
  "cost_parameters": {
    "spread_pips": 1.5,
    "commission_pips": 0.3,
    "slippage_pips": 0.5,
    "cost_pips_total": 2.3
  },
  "filter_parameters": {
    "min_trend_strength": 0.1,
    "trend_ma_long_period": 50,
    "trend_ma_short_period": 20,
    "use_session_filter": true
  },
  "performance_metrics": {
    "expected_win_rate": 0.640625,
    "expected_profit_factor": 2.30,
    "expected_sharpe_ratio": 0.156,
    "max_drawdown_limit": 12.0,
    "min_monthly_trades": 30
  }
}
```

### 2.2 パラメータファイル形式 - INI版（MT4互換）

**ファイル名**: `mt4_wfa_parameters_YYYYMMDD.ini`

```ini
[META]
creation_date=2025-07-19T21:00:00
strategy_name=Cost_Resistant_Breakout
version=1.0
symbol=EURUSD
timeframe=M5
wfa_source_file=cost_resistant_wfa_results_ALL_BIAS_FIXED.json
best_fold=1
selection_criteria=highest_sharpe_ratio

[TRADING_PARAMETERS]
h4_period=24
h1_period=24
atr_period=14
profit_atr_multiplier=2.5
stop_atr_multiplier=1.3
min_break_pips=5
breakout_confirmation=2

[RISK_MANAGEMENT]
max_risk_per_trade=1.5
min_atr_multiple=1.0
min_profit_pips=4.0
min_cost_ratio=2.0
max_daily_trades=6
max_consecutive_losses=4

[COST_PARAMETERS]
spread_pips=1.5
commission_pips=0.3
slippage_pips=0.5
cost_pips_total=2.3

[FILTER_PARAMETERS]
min_trend_strength=0.1
trend_ma_long_period=50
trend_ma_short_period=20
use_session_filter=1

[PERFORMANCE_METRICS]
expected_win_rate=0.640625
expected_profit_factor=2.30
expected_sharpe_ratio=0.156
max_drawdown_limit=12.0
min_monthly_trades=30
```

## 3. MT4パラメータ読み込み機能

### 3.1 MQL4ファイル読み込み関数

```mql4
// パラメータ構造体定義
struct WFAParameters {
    // Trading Parameters
    int h4_period;
    int h1_period;
    int atr_period;
    double profit_atr_multiplier;
    double stop_atr_multiplier;
    double min_break_pips;
    int breakout_confirmation;
    
    // Risk Management
    double max_risk_per_trade;
    double min_atr_multiple;
    double min_profit_pips;
    double min_cost_ratio;
    int max_daily_trades;
    int max_consecutive_losses;
    
    // Cost Parameters
    double spread_pips;
    double commission_pips;
    double slippage_pips;
    double cost_pips_total;
    
    // Filter Parameters
    double min_trend_strength;
    int trend_ma_long_period;
    int trend_ma_short_period;
    bool use_session_filter;
    
    // Performance Metrics
    double expected_win_rate;
    double expected_profit_factor;
    double expected_sharpe_ratio;
    double max_drawdown_limit;
    int min_monthly_trades;
};

// グローバル変数
WFAParameters g_wfa_params;
string g_parameter_file = "mt4_wfa_parameters_" + TimeToStr(TimeCurrent(), TIME_DATE) + ".ini";

// パラメータ読み込み関数
bool LoadWFAParameters() {
    string file_path = "WFA_Parameters\\" + g_parameter_file;
    
    if(!FileIsExist(file_path)) {
        Print("WFAパラメータファイルが見つかりません: ", file_path);
        return false;
    }
    
    int file_handle = FileOpen(file_path, FILE_READ | FILE_TXT);
    if(file_handle == INVALID_HANDLE) {
        Print("WFAパラメータファイルを開けません: ", file_path);
        return false;
    }
    
    string current_section = "";
    string line;
    
    while(!FileIsEnding(file_handle)) {
        line = FileReadString(file_handle);
        line = StringTrimLeft(StringTrimRight(line));
        
        // セクション判定
        if(StringFind(line, "[") == 0 && StringFind(line, "]") > 0) {
            current_section = StringSubstr(line, 1, StringFind(line, "]") - 1);
            continue;
        }
        
        // コメント行をスキップ
        if(StringFind(line, "#") == 0 || StringFind(line, ";") == 0) continue;
        if(StringLen(line) == 0) continue;
        
        // キー=値の解析
        int equal_pos = StringFind(line, "=");
        if(equal_pos > 0) {
            string key = StringTrimRight(StringSubstr(line, 0, equal_pos));
            string value = StringTrimLeft(StringSubstr(line, equal_pos + 1));
            
            ParseParameterValue(current_section, key, value);
        }
    }
    
    FileClose(file_handle);
    Print("WFAパラメータを正常に読み込みました: ", file_path);
    return true;
}

// パラメータ値解析関数
void ParseParameterValue(string section, string key, string value) {
    if(section == "TRADING_PARAMETERS") {
        if(key == "h4_period") g_wfa_params.h4_period = (int)StringToInteger(value);
        else if(key == "h1_period") g_wfa_params.h1_period = (int)StringToInteger(value);
        else if(key == "atr_period") g_wfa_params.atr_period = (int)StringToInteger(value);
        else if(key == "profit_atr_multiplier") g_wfa_params.profit_atr_multiplier = StringToDouble(value);
        else if(key == "stop_atr_multiplier") g_wfa_params.stop_atr_multiplier = StringToDouble(value);
        else if(key == "min_break_pips") g_wfa_params.min_break_pips = StringToDouble(value);
        else if(key == "breakout_confirmation") g_wfa_params.breakout_confirmation = (int)StringToInteger(value);
    }
    else if(section == "RISK_MANAGEMENT") {
        if(key == "max_risk_per_trade") g_wfa_params.max_risk_per_trade = StringToDouble(value);
        else if(key == "min_atr_multiple") g_wfa_params.min_atr_multiple = StringToDouble(value);
        else if(key == "min_profit_pips") g_wfa_params.min_profit_pips = StringToDouble(value);
        else if(key == "min_cost_ratio") g_wfa_params.min_cost_ratio = StringToDouble(value);
        else if(key == "max_daily_trades") g_wfa_params.max_daily_trades = (int)StringToInteger(value);
        else if(key == "max_consecutive_losses") g_wfa_params.max_consecutive_losses = (int)StringToInteger(value);
    }
    else if(section == "COST_PARAMETERS") {
        if(key == "spread_pips") g_wfa_params.spread_pips = StringToDouble(value);
        else if(key == "commission_pips") g_wfa_params.commission_pips = StringToDouble(value);
        else if(key == "slippage_pips") g_wfa_params.slippage_pips = StringToDouble(value);
        else if(key == "cost_pips_total") g_wfa_params.cost_pips_total = StringToDouble(value);
    }
    else if(section == "FILTER_PARAMETERS") {
        if(key == "min_trend_strength") g_wfa_params.min_trend_strength = StringToDouble(value);
        else if(key == "trend_ma_long_period") g_wfa_params.trend_ma_long_period = (int)StringToInteger(value);
        else if(key == "trend_ma_short_period") g_wfa_params.trend_ma_short_period = (int)StringToInteger(value);
        else if(key == "use_session_filter") g_wfa_params.use_session_filter = ((int)StringToInteger(value) == 1);
    }
    else if(section == "PERFORMANCE_METRICS") {
        if(key == "expected_win_rate") g_wfa_params.expected_win_rate = StringToDouble(value);
        else if(key == "expected_profit_factor") g_wfa_params.expected_profit_factor = StringToDouble(value);
        else if(key == "expected_sharpe_ratio") g_wfa_params.expected_sharpe_ratio = StringToDouble(value);
        else if(key == "max_drawdown_limit") g_wfa_params.max_drawdown_limit = StringToDouble(value);
        else if(key == "min_monthly_trades") g_wfa_params.min_monthly_trades = (int)StringToInteger(value);
    }
}
```

### 3.2 EA初期化での使用例

```mql4
int OnInit() {
    // WFAパラメータ読み込み
    if(!LoadWFAParameters()) {
        Print("WFAパラメータの読み込みに失敗しました。デフォルト値を使用します。");
        SetDefaultParameters();
        return INIT_SUCCEEDED;
    }
    
    // 読み込んだパラメータを確認
    Print("=== WFAパラメータ読み込み完了 ===");
    Print("H4期間: ", g_wfa_params.h4_period);
    Print("H1期間: ", g_wfa_params.h1_period);
    Print("ATR期間: ", g_wfa_params.atr_period);
    Print("利確ATR倍率: ", g_wfa_params.profit_atr_multiplier);
    Print("損切ATR倍率: ", g_wfa_params.stop_atr_multiplier);
    Print("期待勝率: ", g_wfa_params.expected_win_rate);
    Print("期待プロフィットファクター: ", g_wfa_params.expected_profit_factor);
    
    // パラメータ妥当性チェック
    if(!ValidateParameters()) {
        Print("WFAパラメータの妥当性チェックに失敗しました。");
        return INIT_PARAMETERS_INCORRECT;
    }
    
    return INIT_SUCCEEDED;
}

// デフォルトパラメータ設定
void SetDefaultParameters() {
    g_wfa_params.h4_period = 24;
    g_wfa_params.h1_period = 24;
    g_wfa_params.atr_period = 14;
    g_wfa_params.profit_atr_multiplier = 2.5;
    g_wfa_params.stop_atr_multiplier = 1.3;
    g_wfa_params.min_break_pips = 5;
    g_wfa_params.max_risk_per_trade = 1.5;
    g_wfa_params.min_profit_pips = 4.0;
    g_wfa_params.spread_pips = 1.5;
    g_wfa_params.commission_pips = 0.3;
    g_wfa_params.expected_win_rate = 0.60;
    g_wfa_params.expected_profit_factor = 2.0;
}

// パラメータ妥当性チェック
bool ValidateParameters() {
    if(g_wfa_params.h4_period < 1 || g_wfa_params.h4_period > 100) return false;
    if(g_wfa_params.h1_period < 1 || g_wfa_params.h1_period > 100) return false;
    if(g_wfa_params.atr_period < 1 || g_wfa_params.atr_period > 50) return false;
    if(g_wfa_params.profit_atr_multiplier <= 0 || g_wfa_params.profit_atr_multiplier > 10) return false;
    if(g_wfa_params.stop_atr_multiplier <= 0 || g_wfa_params.stop_atr_multiplier > 10) return false;
    if(g_wfa_params.max_risk_per_trade <= 0 || g_wfa_params.max_risk_per_trade > 10) return false;
    
    return true;
}
```

## 4. Python側のパラメータファイル生成機能

### 4.1 WFA結果からMT4パラメータファイル生成

```python
import json
import configparser
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

class MT4ParameterGenerator:
    """MT4用パラメータファイル生成クラス"""
    
    def __init__(self, wfa_results_file: str):
        self.wfa_results_file = wfa_results_file
        self.wfa_data = self.load_wfa_results()
        
    def load_wfa_results(self) -> Dict[str, Any]:
        """WFA結果ファイル読み込み"""
        with open(self.wfa_results_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def select_best_fold(self, criteria: str = "sharpe_ratio") -> Dict[str, Any]:
        """最適フォールド選択"""
        folds = self.wfa_data.get("wfa_results_raw", [])
        
        if criteria == "sharpe_ratio":
            best_fold = max(folds, key=lambda x: x.get("sharpe_ratio", -999))
        elif criteria == "profit_factor":
            best_fold = max(folds, key=lambda x: x.get("profit_factor", 0))
        elif criteria == "win_rate":
            best_fold = max(folds, key=lambda x: x.get("win_rate", 0))
        else:
            best_fold = folds[0] if folds else {}
            
        return best_fold
    
    def generate_json_parameters(self, output_file: str, criteria: str = "sharpe_ratio") -> bool:
        """JSON形式パラメータファイル生成"""
        try:
            best_fold = self.select_best_fold(criteria)
            base_params = self.wfa_data.get("base_parameters", {})
            cost_params = self.wfa_data.get("cost_resistance_parameters", {})
            
            mt4_params = {
                "meta": {
                    "creation_date": datetime.now().isoformat(),
                    "strategy_name": "Cost_Resistant_Breakout",
                    "version": "1.0",
                    "symbol": "EURUSD",
                    "timeframe": "M5",
                    "wfa_source_file": Path(self.wfa_results_file).name,
                    "best_fold": best_fold.get("fold_id", 1),
                    "selection_criteria": criteria
                },
                "trading_parameters": {
                    "h4_period": base_params.get("h4_period", 24),
                    "h1_period": base_params.get("h1_period", 24),
                    "atr_period": base_params.get("atr_period", 14),
                    "profit_atr_multiplier": base_params.get("profit_atr", 2.5),
                    "stop_atr_multiplier": base_params.get("stop_atr", 1.3),
                    "min_break_pips": base_params.get("min_break_pips", 5),
                    "breakout_confirmation": cost_params.get("breakout_confirmation", 2)
                },
                "risk_management": {
                    "max_risk_per_trade": 1.5,
                    "min_atr_multiple": cost_params.get("min_atr_multiple", 1.0),
                    "min_profit_pips": cost_params.get("min_profit_pips", 4.0),
                    "min_cost_ratio": cost_params.get("min_cost_ratio", 2.0),
                    "max_daily_trades": 6,
                    "max_consecutive_losses": 4
                },
                "cost_parameters": {
                    "spread_pips": base_params.get("spread_pips", 1.5),
                    "commission_pips": base_params.get("commission_pips", 0.3),
                    "slippage_pips": 0.5,
                    "cost_pips_total": cost_params.get("cost_pips", 2.0)
                },
                "filter_parameters": {
                    "min_trend_strength": cost_params.get("min_trend_strength", 0.1),
                    "trend_ma_long_period": cost_params.get("trend_ma_long_period", 50),
                    "trend_ma_short_period": cost_params.get("trend_ma_short_period", 20),
                    "use_session_filter": True
                },
                "performance_metrics": {
                    "expected_win_rate": best_fold.get("win_rate", 0.60),
                    "expected_profit_factor": best_fold.get("profit_factor", 2.0),
                    "expected_sharpe_ratio": best_fold.get("sharpe_ratio", 0.15),
                    "max_drawdown_limit": 12.0,
                    "min_monthly_trades": 30
                }
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(mt4_params, f, indent=2, ensure_ascii=False)
            
            print(f"MT4パラメータファイル（JSON）を生成しました: {output_file}")
            return True
            
        except Exception as e:
            print(f"JSONパラメータファイル生成エラー: {e}")
            return False
    
    def generate_ini_parameters(self, output_file: str, criteria: str = "sharpe_ratio") -> bool:
        """INI形式パラメータファイル生成"""
        try:
            best_fold = self.select_best_fold(criteria)
            base_params = self.wfa_data.get("base_parameters", {})
            cost_params = self.wfa_data.get("cost_resistance_parameters", {})
            
            config = configparser.ConfigParser()
            
            # META section
            config['META'] = {
                'creation_date': datetime.now().isoformat(),
                'strategy_name': 'Cost_Resistant_Breakout',
                'version': '1.0',
                'symbol': 'EURUSD',
                'timeframe': 'M5',
                'wfa_source_file': Path(self.wfa_results_file).name,
                'best_fold': str(best_fold.get("fold_id", 1)),
                'selection_criteria': criteria
            }
            
            # TRADING_PARAMETERS section
            config['TRADING_PARAMETERS'] = {
                'h4_period': str(base_params.get("h4_period", 24)),
                'h1_period': str(base_params.get("h1_period", 24)),
                'atr_period': str(base_params.get("atr_period", 14)),
                'profit_atr_multiplier': str(base_params.get("profit_atr", 2.5)),
                'stop_atr_multiplier': str(base_params.get("stop_atr", 1.3)),
                'min_break_pips': str(base_params.get("min_break_pips", 5)),
                'breakout_confirmation': str(cost_params.get("breakout_confirmation", 2))
            }
            
            # RISK_MANAGEMENT section
            config['RISK_MANAGEMENT'] = {
                'max_risk_per_trade': '1.5',
                'min_atr_multiple': str(cost_params.get("min_atr_multiple", 1.0)),
                'min_profit_pips': str(cost_params.get("min_profit_pips", 4.0)),
                'min_cost_ratio': str(cost_params.get("min_cost_ratio", 2.0)),
                'max_daily_trades': '6',
                'max_consecutive_losses': '4'
            }
            
            # COST_PARAMETERS section
            config['COST_PARAMETERS'] = {
                'spread_pips': str(base_params.get("spread_pips", 1.5)),
                'commission_pips': str(base_params.get("commission_pips", 0.3)),
                'slippage_pips': '0.5',
                'cost_pips_total': str(cost_params.get("cost_pips", 2.0))
            }
            
            # FILTER_PARAMETERS section
            config['FILTER_PARAMETERS'] = {
                'min_trend_strength': str(cost_params.get("min_trend_strength", 0.1)),
                'trend_ma_long_period': str(cost_params.get("trend_ma_long_period", 50)),
                'trend_ma_short_period': str(cost_params.get("trend_ma_short_period", 20)),
                'use_session_filter': '1'
            }
            
            # PERFORMANCE_METRICS section
            config['PERFORMANCE_METRICS'] = {
                'expected_win_rate': str(best_fold.get("win_rate", 0.60)),
                'expected_profit_factor': str(best_fold.get("profit_factor", 2.0)),
                'expected_sharpe_ratio': str(best_fold.get("sharpe_ratio", 0.15)),
                'max_drawdown_limit': '12.0',
                'min_monthly_trades': '30'
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                config.write(f)
            
            print(f"MT4パラメータファイル（INI）を生成しました: {output_file}")
            return True
            
        except Exception as e:
            print(f"INIパラメータファイル生成エラー: {e}")
            return False

# 使用例
if __name__ == "__main__":
    # WFA結果ファイルを指定
    wfa_file = "cost_resistant_wfa_results_ALL_BIAS_FIXED.json"
    
    # パラメータジェネレータ作成
    generator = MT4ParameterGenerator(wfa_file)
    
    # 現在日付でファイル名生成
    date_str = datetime.now().strftime("%Y%m%d")
    
    # JSON形式で生成
    json_file = f"mt4_wfa_parameters_{date_str}.json"
    generator.generate_json_parameters(json_file, "sharpe_ratio")
    
    # INI形式で生成
    ini_file = f"mt4_wfa_parameters_{date_str}.ini"
    generator.generate_ini_parameters(ini_file, "sharpe_ratio")
```

## 5. ファイル配置とパス設定

### 5.1 推奨ディレクトリ構造

```
MT4_Data_Folder/
├── MQL4/
│   ├── Experts/
│   │   └── BreakoutEA.mq4
│   └── Include/
│       └── WFAParameterLoader.mqh
├── Files/
│   └── WFA_Parameters/
│       ├── mt4_wfa_parameters_20250719.ini
│       ├── mt4_wfa_parameters_20250719.json
│       └── parameter_history/
│           ├── mt4_wfa_parameters_20250718.ini
│           └── mt4_wfa_parameters_20250717.ini
└── Logs/
    └── WFA_Parameter_Logs/
        └── parameter_load_log_20250719.txt
```

### 5.2 パラメータファイル自動更新機能

```python
import schedule
import time
from datetime import datetime

def daily_parameter_update():
    """日次パラメータ更新"""
    try:
        # 最新のWFA結果ファイルを検索
        wfa_files = list(Path(".").glob("*wfa_results*.json"))
        latest_wfa = max(wfa_files, key=lambda x: x.stat().st_mtime)
        
        # パラメータファイル生成
        generator = MT4ParameterGenerator(str(latest_wfa))
        date_str = datetime.now().strftime("%Y%m%d")
        
        # MT4ファイルディレクトリに出力
        mt4_files_dir = Path("C:/Users/[User]/AppData/Roaming/MetaQuotes/Terminal/[ID]/MQL4/Files/WFA_Parameters")
        mt4_files_dir.mkdir(exist_ok=True)
        
        ini_file = mt4_files_dir / f"mt4_wfa_parameters_{date_str}.ini"
        json_file = mt4_files_dir / f"mt4_wfa_parameters_{date_str}.json"
        
        generator.generate_ini_parameters(str(ini_file))
        generator.generate_json_parameters(str(json_file))
        
        print(f"パラメータファイルを更新しました: {date_str}")
        
    except Exception as e:
        print(f"パラメータ更新エラー: {e}")

# 毎日午前2時に実行
schedule.every().day.at("02:00").do(daily_parameter_update)

while True:
    schedule.run_pending()
    time.sleep(60)
```

## 6. 実装優先順位と次のステップ

### 6.1 Phase 1: 基本実装
1. **WFA結果解析完了** ✅
2. **パラメータファイル形式定義完了** ✅
3. **Python生成機能実装** ⭐ 次のステップ
4. **MT4読み込み機能実装** ⭐ 次のステップ

### 6.2 Phase 2: 統合テスト
1. パラメータファイル生成テスト
2. MT4読み込みテスト
3. バックテスト検証
4. 本番環境テスト

### 6.3 Phase 3: 自動化
1. 日次パラメータ更新
2. パフォーマンス監視
3. アラート機能
4. レポート生成

この仕様書に基づいて、MT4でWFA最適化パラメータを動的に読み込む機能を実装することができます。