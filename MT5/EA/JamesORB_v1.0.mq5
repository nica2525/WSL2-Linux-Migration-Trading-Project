//+------------------------------------------------------------------+
//|                                          JamesORB_Standalone.mq5 |
//|                                 Copyright 2012,Clifford H. James |
//|                            Modified for MT5 standalone operation |
//|                                    v2.01 - Added Magic Number   |
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
   // Close all positions
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0)
      {
         trade.PositionClose(ticket);
      }
   }

   // Delete all pending orders
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket > 0)
      {
         trade.OrderDelete(ticket);
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

   // Place order
   bool result = trade.OrderOpen(Symb, tradeType, Lots, 0, ReqPrice, SL, TP, ORDER_TIME_DAY, 0, "JamesORB");

   if(!result)
   {
      Alert("OrderOpen failed with error: ", trade.ResultRetcode());
   }
   else
   {
      Alert("Order placed successfully. Ticket: ", trade.ResultOrder());
   }
}

//+------------------------------------------------------------------+
//| Calculate current ORB                                           |
//+------------------------------------------------------------------+
double CalcCurrORB()
{
   double atr_buffer[];
   int atr_handle = iATR(_Symbol, PERIOD_CURRENT, (int)ATR_PERIOD);

   if(atr_handle == INVALID_HANDLE)
   {
      Alert("Failed to create ATR indicator handle");
      return 0;
   }

   ArraySetAsSeries(atr_buffer, true);

   if(CopyBuffer(atr_handle, 0, 1, 1, atr_buffer) <= 0)
   {
      Alert("Failed to copy ATR buffer data");
      return 0;
   }

   return (atr_buffer[0] + OBR_PIP_OFFSET);
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
   double SL_buy = buyEntry - (1.65 * orbval);
   double TP_buy = buyEntry + orbval;
   double lotSize = 0.01;  // Fixed small lot size

   double current_bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double current_ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);

   Alert("Current Price: ", current_bid, "/", current_ask);

   // Buy side
   PlacePendingStopOrder(ORDER_TYPE_BUY_STOP, _Symbol, buyEntry, lotSize, SL_buy, TP_buy);

   double sellEntry = tenEETLo - orbval;
   double SL_sell = sellEntry + (1.65 * orbval);
   double TP_sell = sellEntry - orbval;

   // Sell side
   PlacePendingStopOrder(ORDER_TYPE_SELL_STOP, _Symbol, sellEntry, lotSize, SL_sell, TP_sell);
}

//+------------------------------------------------------------------+
//| Check if at close of day                                        |
//+------------------------------------------------------------------+
bool AtCloseOfDay()
{
   MqlDateTime current_time;
   TimeToStruct(TimeCurrent(), current_time);
   return(current_time.hour == 17 && current_time.min == 30);
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
