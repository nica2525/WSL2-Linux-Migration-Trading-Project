//+------------------------------------------------------------------+
//|                                          JamesORB_Standalone.mq4 |
//|                                 Copyright 2012,Clifford H. James |
//|                                  Modified for standalone operation|
//+------------------------------------------------------------------+

#property copyright "Copyright 2012,Clifford H. James"
#property link      ""

// CONSTANTS
extern double OBR_PIP_OFFSET = 0.0002;
extern int EET_START = 10;
extern double OBR_RATIO = 1.9;
extern double ATR_PERIOD = 72;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int init()
{
   return(0);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                |
//+------------------------------------------------------------------+
int deinit()
{
   return(0);
}

//+------------------------------------------------------------------+
//| Convert relative distance to points                             |
//+------------------------------------------------------------------+
double RelDistToPoints(double price)
{
   return(MathAbs(price - Bid) / Point);
}

//+------------------------------------------------------------------+
//| Close all outstanding orders                                    |
//+------------------------------------------------------------------+
void CloseAllOutstandingOrders()
{
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      if(OrderSelect(i, SELECT_BY_POS))
      {
         if(OrderType() == OP_BUY)
         {
            OrderClose(OrderTicket(), OrderLots(), Bid, 2);
         }
         else if(OrderType() == OP_SELL)
         {
            OrderClose(OrderTicket(), OrderLots(), Ask, 2);
         }
         else
         {
            OrderDelete(OrderTicket());
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Place pending stop order                                        |
//+------------------------------------------------------------------+
void PlacePendingStopOrder(int tradeType, string Symb, double ReqPrice, double Lots, double Dist_SL, double Dist_TP)
{
   // Sanity checks
   if(Dist_SL < 0 || Dist_TP < 0 || ReqPrice < 0) 
   {
      Alert("Invalid Parameters! Cannot have negative values for price, sl or tp!");
      return;
   }
   if(!(tradeType == OP_BUYSTOP || tradeType == OP_SELLSTOP))
   {
      Alert("Called PlacePendingStopOrder with a non Pending Stop order!");
      return;
   }
   
   double tradeFactor = 1.0;
   if(tradeType == OP_SELLSTOP) tradeFactor = -1.0;
   
   int Min_Dist = MarketInfo(Symb, MODE_STOPLEVEL);
   double Min_Lot = MarketInfo(Symb, MODE_MINLOT);
   
   // Check lots
   if (Lots < Min_Lot)
   {
      Alert("Cannot Place order, minLot for ", Symb, " is ", Min_Lot, " lots");
      return;
   }
   
   // Adjust SL distance
   if (Dist_SL < Min_Dist) Dist_SL = Min_Dist;
   double SL = ReqPrice - tradeFactor * Dist_SL * Point;
   
   // Adjust TP distance  
   if (Dist_TP < Min_Dist) Dist_TP = Min_Dist;
   double TP = ReqPrice + tradeFactor * Dist_TP * Point;
   
   // Place order
   int ticket = OrderSend(Symb, tradeType, Lots, ReqPrice, 2, SL, TP, "JamesORB", 0, 0);
   
   if(ticket < 0)
   {
      Alert("OrderSend failed with error: ", GetLastError());
   }
   else
   {
      Alert("Order placed successfully. Ticket: ", ticket);
   }
}

//+------------------------------------------------------------------+
//| Calculate current ORB                                           |
//+------------------------------------------------------------------+
double CalcCurrORB() 
{
   double currATR = iATR(NULL, 0, ATR_PERIOD, 1);
   return (currATR + OBR_PIP_OFFSET);
}

//+------------------------------------------------------------------+
//| Generate daily pending orders                                   |
//+------------------------------------------------------------------+
void generateDailyPendingOrders(double orbval) 
{
   double tenEETHi = High[1]; 
   double tenEETLo = Low[1];
   
   double buyEntry = tenEETHi + orbval;
   double SL = buyEntry - (1.65 * orbval);
   double TP = buyEntry + orbval;
   double SL_Dist = RelDistToPoints(SL);
   double TP_Dist = RelDistToPoints(TP);   
   double lotSize = 0.01;  // Fixed small lot size
   
   Alert("Current Price: ", Bid, "/", Ask);
      
   // Buy side  
   PlacePendingStopOrder(OP_BUYSTOP, Symbol(), buyEntry, lotSize, SL_Dist, TP_Dist);
   
   double sellEntry = tenEETLo - orbval;
   SL = sellEntry + (1.65 * orbval);
   TP = sellEntry - orbval;
   SL_Dist = RelDistToPoints(SL);
   TP_Dist = RelDistToPoints(TP);
   
   // Sell side
   PlacePendingStopOrder(OP_SELLSTOP, Symbol(), sellEntry, lotSize, SL_Dist, TP_Dist);
}

//+------------------------------------------------------------------+
//| Check if at close of day                                        |
//+------------------------------------------------------------------+
bool AtCloseOfDay() 
{
   int currHour = TimeHour(TimeCurrent());
   int currMin = TimeMinute(TimeCurrent());
   return(currHour == 17 && currMin == 30);
}

//+------------------------------------------------------------------+
//| Expert start function                                           |
//+------------------------------------------------------------------+
int start()
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
      return(0);
   }
   processedClose = false; 
   
   // Check for first bar of the hour
   if (Time0 == Time[0]) return(0);
   Time0 = Time[0];
   int currHour = TimeHour(Time[0]); 
  
   double currOrb = 0;
   if(currHour == 11) 
   {
      currOrb = CalcCurrORB();
      generateDailyPendingOrders(currOrb);
   }
   
   return(0);
}
//+------------------------------------------------------------------+