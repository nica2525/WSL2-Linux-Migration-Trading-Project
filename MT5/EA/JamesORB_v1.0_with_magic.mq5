//+------------------------------------------------------------------+
//|                                          JamesORB_Standalone.mq5 |
//|                                 Copyright 2012,Clifford H. James |
//|                            Modified for MT5 standalone operation |
//|                                    Added Magic Number for tracking |
//+------------------------------------------------------------------+

#property copyright "Copyright 2012,Clifford H. James"
#property link      ""
#property version   "2.01"

#include <Trade\Trade.mqh>

// CONSTANTS
input double OBR_PIP_OFFSET = 0.0002;
input int EET_START = 10;
input double OBR_RATIO = 1.9;
input double ATR_PERIOD = 72;
input int MAGIC_NUMBER = 20250727;  // JamesORB専用マジックナンバー

// Global variables
CTrade trade;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   // マジックナンバーを設定
   trade.SetExpertMagicNumber(MAGIC_NUMBER);
   
   Print("JamesORB EA initialized with Magic Number: ", MAGIC_NUMBER);
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   Print("JamesORB EA deinitialized. Reason: ", reason);
}

//+------------------------------------------------------------------+
//| Convert relative distance to points                             |
//+------------------------------------------------------------------+
double RelDistToPoints(double diff)
{
   return(diff / _Point);
}

//+------------------------------------------------------------------+
//| Close all outstanding orders for this EA only                   |
//+------------------------------------------------------------------+
void CloseAllOutstandingOrders()
{
   // Close all positions belonging to this EA
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0)
      {
         if(PositionSelectByTicket(ticket))
         {
            // マジックナンバーをチェック
            if(PositionGetInteger(POSITION_MAGIC) == MAGIC_NUMBER)
            {
               trade.PositionClose(ticket);
               Print("Closed position with ticket: ", ticket);
            }
         }
      }
   }

   // Delete all pending orders belonging to this EA
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket > 0)
      {
         if(OrderSelect(ticket))
         {
            // マジックナンバーをチェック
            if(OrderGetInteger(ORDER_MAGIC) == MAGIC_NUMBER)
            {
               trade.OrderDelete(ticket);
               Print("Deleted order with ticket: ", ticket);
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
      Alert("Invalid Parameters! Cannot have negative values for price, sl or tp!");
      return;
   }
   if(!(tradeType == ORDER_TYPE_BUY_STOP || tradeType == ORDER_TYPE_SELL_STOP))
   {
      Alert("Called PlacePendingStopOrder with a non Pending Stop order!");
      return;
   }

   double Min_Lot = SymbolInfoDouble(Symb, SYMBOL_VOLUME_MIN);

   // Check lots
   if (Lots < Min_Lot)
   {
      Alert("Cannot Place order, minLot for ", Symb, " is ", Min_Lot, " lots");
      return;
   }

   // Place order with magic number
   bool result = trade.OrderOpen(Symb, tradeType, Lots, 0, ReqPrice, SL, TP, ORDER_TIME_DAY, 0, "JamesORB");

   if(!result)
   {
      Alert("OrderOpen failed with error: ", trade.ResultRetcode());
   }
   else
   {
      Alert("Order placed successfully. Ticket: ", trade.ResultOrder());
      Print("Order placed with Magic Number: ", MAGIC_NUMBER);
   }
}

//+------------------------------------------------------------------+
//| Place market order                                              |
//+------------------------------------------------------------------+
void PlaceMarketOrder(ENUM_ORDER_TYPE tradeType, string Symb, double Lots, double SL, double TP)
{
   // Sanity checks
   if(SL < 0 || TP < 0)
   {
      Alert("Invalid Parameters! Cannot have negative values for sl or tp!");
      return;
   }
   if(!(tradeType == ORDER_TYPE_BUY || tradeType == ORDER_TYPE_SELL))
   {
      Alert("Called PlaceMarketOrder with a non Market order type!");
      return;
   }

   double Min_Lot = SymbolInfoDouble(Symb, SYMBOL_VOLUME_MIN);

   // Check lots
   if (Lots < Min_Lot)
   {
      Alert("Cannot Place order, minLot for ", Symb, " is ", Min_Lot, " lots");
      return;
   }

   // Place market order
   bool result;
   if(tradeType == ORDER_TYPE_BUY)
   {
      result = trade.Buy(Lots, Symb, 0, SL, TP, "JamesORB Market Buy");
   }
   else
   {
      result = trade.Sell(Lots, Symb, 0, SL, TP, "JamesORB Market Sell");
   }

   if(!result)
   {
      Alert("Market order failed with error: ", trade.ResultRetcode());
   }
   else
   {
      Alert("Market order placed successfully. Ticket: ", trade.ResultDeal());
      Print("Market order placed with Magic Number: ", MAGIC_NUMBER);
   }
}

//+------------------------------------------------------------------+
//| Get current server time in minutes since midnight               |
//+------------------------------------------------------------------+
int GetCurrentTimeMinutes()
{
   datetime currentTime = TimeCurrent();
   MqlDateTime timeStruct;
   TimeToStruct(currentTime, timeStruct);
   return timeStruct.hour * 60 + timeStruct.min;
}

//+------------------------------------------------------------------+
//| Check if trading is allowed at current time                     |
//+------------------------------------------------------------------+
bool IsTradingAllowed()
{
   int currentMinutes = GetCurrentTimeMinutes();
   int startMinutes = EET_START * 60; // EET_START時間を分に変換
   
   // 市場時間チェック（例：10:00-22:00）
   return (currentMinutes >= startMinutes && currentMinutes <= 22 * 60);
}

//+------------------------------------------------------------------+
//| Get current positions count for this EA                         |
//+------------------------------------------------------------------+
int GetCurrentPositionsCount()
{
   int count = 0;
   for(int i = 0; i < PositionsTotal(); i++)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0 && PositionSelectByTicket(ticket))
      {
         if(PositionGetInteger(POSITION_MAGIC) == MAGIC_NUMBER)
         {
            count++;
         }
      }
   }
   return count;
}

//+------------------------------------------------------------------+
//| Expert tick function                                            |
//+------------------------------------------------------------------+
void OnTick()
{
   // 基本的な取引ロジックをここに実装
   // 現在はテスト用のシンプルな実装
   
   static datetime lastTradeTime = 0;
   datetime currentTime = TimeCurrent();
   
   // 1時間に1回のみチェック
   if(currentTime - lastTradeTime < 3600)
      return;
   
   // 取引許可時間チェック
   if(!IsTradingAllowed())
      return;
   
   // 既存ポジションがある場合は新規取引しない
   if(GetCurrentPositionsCount() > 0)
      return;
   
   // シンプルなORB（Opening Range Breakout）ロジック
   // 注意：これは基本的な例です。実際の戦略に合わせて修正してください
   double currentPrice = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   
   // ATRに基づくストップロス・テイクプロフィット
   double atr = iATR(_Symbol, PERIOD_H1, (int)ATR_PERIOD, 1);
   double stopLoss = atr * OBR_RATIO;
   double takeProfit = stopLoss * 2.0; // 2:1のリスクリワード
   
   // 例：簡単なブレイクアウト戦略
   static double dayHigh = 0, dayLow = 0;
   
   // 日次の高値・安値を更新
   if(TimeHour(currentTime) == EET_START && TimeMinute(currentTime) == 0)
   {
      dayHigh = iHigh(_Symbol, PERIOD_D1, 1);
      dayLow = iLow(_Symbol, PERIOD_D1, 1);
      Print("Daily range updated: High=", dayHigh, ", Low=", dayLow);
   }
   
   // ブレイクアウト判定
   if(dayHigh > 0 && dayLow > 0)
   {
      if(ask > dayHigh + OBR_PIP_OFFSET)
      {
         // 上方ブレイクアウト
         double sl = currentPrice - stopLoss;
         double tp = currentPrice + takeProfit;
         PlaceMarketOrder(ORDER_TYPE_BUY, _Symbol, 0.01, sl, tp);
         lastTradeTime = currentTime;
         Print("Buy signal: Price=", ask, ", SL=", sl, ", TP=", tp);
      }
      else if(currentPrice < dayLow - OBR_PIP_OFFSET)
      {
         // 下方ブレイクアウト
         double sl = currentPrice + stopLoss;
         double tp = currentPrice - takeProfit;
         PlaceMarketOrder(ORDER_TYPE_SELL, _Symbol, 0.01, sl, tp);
         lastTradeTime = currentTime;
         Print("Sell signal: Price=", currentPrice, ", SL=", sl, ", TP=", tp);
      }
   }
}