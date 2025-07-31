//+------------------------------------------------------------------+
//|                                          JamesORB_Standalone.mq5 |
//|                                 Copyright 2012,Clifford H. James |
//|                            Modified for MT5 standalone operation |
//|                                    v2.01 - Added Magic Number   |
//+------------------------------------------------------------------+

#property copyright "Copyright 2012,Clifford H. James"
#property link      ""
#property version   "2.05"

#include <Trade\Trade.mqh>

// CONSTANTS
input double OBR_PIP_OFFSET = 0.0002;
input int EET_START = 10;
input double OBR_RATIO = 1.9;
input double ATR_PERIOD = 72;
input int MAGIC_NUMBER = 20250727;  // JamesORB専用マジックナンバー

// リアル運用向けロット管理パラメータ
input double LOT_SIZE = 0.01;        // 固定ロットサイズ
input double MAX_RISK_PERCENT = 1.0; // 最大リスク割合（％）
input bool USE_DYNAMIC_LOT = false;  // 動的ロット計算使用
input double MAX_EQUITY_USAGE = 15.0; // 最大証拠金使用率（％）

// Global variables
CTrade trade;
int g_atr_handle = INVALID_HANDLE;  // ATRハンドル（メモリリーク対策）

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   // マジックナンバーを設定
   trade.SetExpertMagicNumber(MAGIC_NUMBER);

   // ATRハンドル作成（メモリリーク対策）
   g_atr_handle = iATR(_Symbol, PERIOD_CURRENT, (int)ATR_PERIOD);
   if(g_atr_handle == INVALID_HANDLE)
   {
      Alert("Failed to create ATR indicator handle");
      return(INIT_FAILED);
   }

   Print("JamesORB EA initialized with Magic Number: ", MAGIC_NUMBER);
   Print("ATR Handle created successfully: ", g_atr_handle);
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   // ATRハンドル解放（メモリリーク対策）
   if(g_atr_handle != INVALID_HANDLE)
   {
      IndicatorRelease(g_atr_handle);
      g_atr_handle = INVALID_HANDLE;
      Print("ATR Handle released successfully");
   }
}

//+------------------------------------------------------------------+
//| Convert relative distance to points                             |
//+------------------------------------------------------------------+
double RelDistToPoints(double diff)
{
   return(diff / _Point);
}

//+------------------------------------------------------------------+
//| Close all outstanding orders                                    |
//+------------------------------------------------------------------+
void CloseAllOutstandingOrders()
{
   // Close positions with matching magic number only (Critical fix)
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0)
      {
         if(PositionSelectByTicket(ticket))
         {
            if(PositionGetInteger(POSITION_MAGIC) == MAGIC_NUMBER)
            {
               if(!trade.PositionClose(ticket))
               {
                  Print("ERROR: Failed to close position ", ticket,
                        ", Error: ", trade.ResultRetcode(), " - ", trade.ResultComment());
               }
               else
               {
                  Print("INFO: Successfully closed position ", ticket);
               }
            }
         }
      }
   }

   // Delete pending orders with matching magic number only (Critical fix)
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket > 0)
      {
         if(OrderSelect(ticket))
         {
            if(OrderGetInteger(ORDER_MAGIC) == MAGIC_NUMBER)
            {
               if(!trade.OrderDelete(ticket))
               {
                  Print("ERROR: Failed to delete order ", ticket,
                        ", Error: ", trade.ResultRetcode(), " - ", trade.ResultComment());
               }
               else
               {
                  Print("INFO: Successfully deleted order ", ticket);
               }
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Place pending stop order                                        |
//+------------------------------------------------------------------+
void PlacePendingStopOrder(ENUM_ORDER_TYPE tradeType, string Symb, double ReqPrice, double Lots, double SL, double TP)
{
   // Sanity checks
   if(SL < 0 || TP < 0 || ReqPrice < 0)
   {
      Print("ERROR: Invalid Parameters! Cannot have negative values - Price:", ReqPrice, " SL:", SL, " TP:", TP);
      Alert("Invalid Parameters! Cannot have negative values for price, sl or tp!");
      return;
   }
   if(!(tradeType == ORDER_TYPE_BUY_STOP || tradeType == ORDER_TYPE_SELL_STOP))
   {
      Print("ERROR: Invalid order type: ", EnumToString(tradeType));
      Alert("Called PlacePendingStopOrder with a non Pending Stop order!");
      return;
   }

   // Market status checks (Enhanced error handling)
   if(!SymbolInfoInteger(Symb, SYMBOL_TRADE_MODE))
   {
      Print("ERROR: Trading is disabled for ", Symb);
      Alert("Trading is disabled for ", Symb);
      return;
   }

   // Spread check (Enhanced error handling)
   double spread = SymbolInfoInteger(Symb, SYMBOL_SPREAD) * _Point;
   double current_orb = CalcCurrORB();
   if(spread > current_orb * 0.3)
   {
      Print("WARNING: High spread detected - Spread:", spread, " vs ORB:", current_orb);
      Alert("Warning: High spread detected: ", spread, " vs ORB: ", current_orb);
   }

   double Min_Lot = SymbolInfoDouble(Symb, SYMBOL_VOLUME_MIN);
   double Max_Lot = SymbolInfoDouble(Symb, SYMBOL_VOLUME_MAX);
   double Lot_Step = SymbolInfoDouble(Symb, SYMBOL_VOLUME_STEP);

   // Enhanced lot checks
   if (Lots < Min_Lot)
   {
      Print("ERROR: Lot size too small - Requested:", Lots, " Min:", Min_Lot);
      Alert("Cannot Place order, minLot for ", Symb, " is ", Min_Lot, " lots");
      return;
   }
   if (Lots > Max_Lot)
   {
      Print("ERROR: Lot size too large - Requested:", Lots, " Max:", Max_Lot);
      Alert("Cannot Place order, maxLot for ", Symb, " is ", Max_Lot, " lots");
      return;
   }

   // Normalize lot size
   Lots = NormalizeDouble(Lots / Lot_Step, 0) * Lot_Step;

   // Enhanced order placement with detailed error logging
   bool result = trade.OrderOpen(Symb, tradeType, Lots, 0, ReqPrice, SL, TP, ORDER_TIME_DAY, 0, "JamesORB");

   if(!result)
   {
      uint error_code = trade.ResultRetcode();
      string error_desc = trade.ResultComment();
      Print("ERROR: OrderOpen failed - Symbol:", Symb, " Type:", EnumToString(tradeType),
            " Lots:", Lots, " Price:", ReqPrice, " SL:", SL, " TP:", TP,
            " ErrorCode:", error_code, " Description:", error_desc);
      Alert("OrderOpen failed with error: ", error_code, " - ", error_desc);
   }
   else
   {
      ulong ticket = trade.ResultOrder();
      Print("SUCCESS: Order placed - Ticket:", ticket, " Symbol:", Symb,
            " Type:", EnumToString(tradeType), " Lots:", Lots, " Price:", ReqPrice);
      Alert("Order placed successfully. Ticket: ", ticket);
   }
}

//+------------------------------------------------------------------+
//| Calculate current ORB                                           |
//+------------------------------------------------------------------+
double CalcCurrORB()
{
   // グローバルATRハンドル使用（メモリリーク対策・パフォーマンス改善）
   if(g_atr_handle == INVALID_HANDLE)
   {
      Alert("ATR handle is invalid");
      return 0;
   }

   double atr_buffer[];
   ArraySetAsSeries(atr_buffer, true);

   if(CopyBuffer(g_atr_handle, 0, 1, 1, atr_buffer) <= 0)
   {
      Alert("Failed to copy ATR buffer data");
      return 0;
   }

   return (atr_buffer[0] + OBR_PIP_OFFSET);
}

//+------------------------------------------------------------------+
//| Calculate dynamic lot size based on risk management             |
//+------------------------------------------------------------------+
double CalculateDynamicLot(double orbval)
{
   if(!USE_DYNAMIC_LOT)
   {
      return LOT_SIZE;
   }

   // 口座情報取得
   double account_equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(account_equity <= 0)
   {
      Print("ERROR: Invalid account equity: ", account_equity, " - Using fixed lot");
      return LOT_SIZE;
   }

   // ORB値検証（通貨ペア適応型・MQL5リファレンス準拠）
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double pip_size = (digits == 5 || digits == 3) ? 10 * _Point : _Point;
   double max_reasonable_orb = 2000 * pip_size; // 2000pips相当（USDJPY対応）
   if(orbval <= 0 || orbval > max_reasonable_orb)
   {
      Print("WARNING: Unusual ORB value: ", orbval, " (Max: ", max_reasonable_orb,
            ", Digits: ", digits, ", PipSize: ", pip_size, ") - Using fixed lot");
      return LOT_SIZE;
   }

   // リスク金額計算
   double risk_amount = account_equity * (MAX_RISK_PERCENT / 100.0);
   double stop_loss_distance = 1.2 * orbval;  // 実際の価格差

   // 正確なpips計算（通貨ペア対応）- 既に定義済みの変数を使用
   double pip_value = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE) *
                      (pip_size / SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE));

   if(pip_value <= 0)
   {
      Print("ERROR: Invalid pip value: ", pip_value, " - Using fixed lot");
      return LOT_SIZE;
   }

   // リスクベースロット計算
   double stop_loss_pips = stop_loss_distance / pip_size;
   double risk_based_lot = risk_amount / (stop_loss_pips * pip_value);

   // 証拠金ベース制限（正確な計算方法に修正）
   double test_lot = 1.0;  // 1ロットでテスト
   double margin_required;
   if(!OrderCalcMargin(ORDER_TYPE_BUY, _Symbol, test_lot,
                      SymbolInfoDouble(_Symbol, SYMBOL_ASK), margin_required))
   {
      Print("ERROR: Failed to calculate margin - Using fixed lot");
      return LOT_SIZE;
   }

   // 最大許容証拠金額
   double max_margin_usage = account_equity * (MAX_EQUITY_USAGE / 100.0);
   double max_equity_lot = (margin_required > 0) ? (max_margin_usage / margin_required) * test_lot : LOT_SIZE;

   // より保守的な値を採用
   double calculated_lot = MathMin(risk_based_lot, max_equity_lot);

   // ブローカー制限適用
   double min_lot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double max_lot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lot_step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

   calculated_lot = MathMax(calculated_lot, min_lot);
   calculated_lot = MathMin(calculated_lot, max_lot);
   calculated_lot = NormalizeDouble(calculated_lot / lot_step, 0) * lot_step;

   // デバッグ情報出力（MQL5リファレンス準拠検証含む）
   Print("Dynamic Lot Calculation - ORB: ", orbval, " (", orbval/pip_size, " pips)",
         ", Equity: ", account_equity, ", Risk Amount: ", risk_amount,
         ", Risk-based Lot: ", risk_based_lot, ", Margin Limit Lot: ", max_equity_lot,
         ", Final Lot: ", calculated_lot);

   return calculated_lot;
}

//+------------------------------------------------------------------+
//| Generate daily pending orders                                   |
//+------------------------------------------------------------------+
void generateDailyPendingOrders(double orbval)
{
   MqlRates rates[];
   ArraySetAsSeries(rates, true);

   if(CopyRates(_Symbol, PERIOD_CURRENT, 1, 1, rates) <= 0)
   {
      Alert("Failed to copy rates data");
      return;
   }

   double tenEETHi = rates[0].high;
   double tenEETLo = rates[0].low;

   double buyEntry = tenEETHi + orbval;
   double SL_buy = buyEntry - (1.2 * orbval);
   double TP_buy = buyEntry + (1.5 * orbval);
   double lotSize = CalculateDynamicLot(orbval);  // 動的ロット計算

   double current_bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double current_ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);

   Alert("Current Price: ", current_bid, "/", current_ask);

   // Buy side
   PlacePendingStopOrder(ORDER_TYPE_BUY_STOP, _Symbol, buyEntry, lotSize, SL_buy, TP_buy);

   double sellEntry = tenEETLo - orbval;
   double SL_sell = sellEntry + (1.2 * orbval);
   double TP_sell = sellEntry - (1.5 * orbval);

   // Sell side
   PlacePendingStopOrder(ORDER_TYPE_SELL_STOP, _Symbol, sellEntry, lotSize, SL_sell, TP_sell);
}

//+------------------------------------------------------------------+
//| Check if at close of day                                        |
//+------------------------------------------------------------------+
bool AtCloseOfDay()
{
   // サーバー時間使用（MQL5ベストプラクティス）
   MqlDateTime server_time;
   TimeToStruct(TimeTradeServer(), server_time);
   return(server_time.hour == 17 && server_time.min == 30);
}

//+------------------------------------------------------------------+
//| Expert tick function                                            |
//+------------------------------------------------------------------+
void OnTick()
{
   static datetime Time0;
   static bool processedClose;

   if(AtCloseOfDay())
   {
      if(!processedClose)
      {
         CloseAllOutstandingOrders();
         processedClose = true;
      }
      return;
   }
   processedClose = false;

   // Check for first bar of the hour
   datetime current_time = iTime(_Symbol, PERIOD_CURRENT, 0);
   if (Time0 == current_time) return;
   Time0 = current_time;

   MqlDateTime time_struct;
   TimeToStruct(current_time, time_struct);
   int currHour = time_struct.hour;

   double currOrb = 0;
   if(currHour == 11)
   {
      currOrb = CalcCurrORB();
      generateDailyPendingOrders(currOrb);
   }
}
//+------------------------------------------------------------------+
