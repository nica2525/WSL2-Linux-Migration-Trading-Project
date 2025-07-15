# 緊急修正版：`cost_resistant_wfa_execution.py` バグ修正ガイド

参照：`CHATGPT_TASK_REQUEST.md`（緊急要請）  
対象ファイル：`cost_resistant_wfa_execution.py`

---

## 1. 修正要件サマリー

| No. | 要件                                        | 修正内容                                     |
|-----|---------------------------------------------|----------------------------------------------|
| 1   | **Look-ahead Bias** 排除                   | future_data 参照の完全削除                  |
| 2   | **ポジション管理** ロジック実装             | ポジション状態 (in_position) の管理導入     |
| 3   | **バーごと進行型バックテスト** への刷新      | 時系列インデックスを用いたループ検証方式に書き換え |

---

## 2. Look-ahead Bias 完全排除

- price = future_data['close'][i+1] を使用している箇所を削除  
- 当バーの終値 historical_data['close'][i] のみを参照

```
- price = future_data['close'][i+1]
+ price = historical_data['close'][i]  # 現在バーの終値
```

## 3. ポジション管理ロジック実装

- ループ開始前に in_position = False を初期化  
- buy シグナル時に if not in_position でエントリー  
- 決済時に in_position = False

```
in_position = False
for i in range(len(data)):
price = data['close'][i]
signal = signals[i]
if signal == 'buy' and not in_position:
    entry_price = price
    in_position = True
elif signal == 'sell' and in_position:
    pnl += price - entry_price
    in_position = False
```

## 4. バーごと進行型バックテストへの書き換え

- 時系列ループで1バーずつ処理し、future_data参照を排除

```
def execute_oos_test(data, signals):
pnl = 0.0
in_position = False
entry_price = 0.0
for i in range(len(data)):
    price = data['close'].iloc[i]
    sig = signals[i]
    if sig == 'buy' and not in_position:
        entry_price = price
        in_position = True
    elif sig == 'sell' and in_position:
        pnl += price - entry_price
        in_position = False
return pnl
```

## 5. 期待される効果と検証

- Look-ahead Bias排除  
- 異常建玉防止  
- 正確な評価  

---
