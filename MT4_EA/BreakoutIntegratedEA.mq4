//+------------------------------------------------------------------+
//|                                         BreakoutIntegratedEA.mq4 |
//|                  統合ブレイクアウトEA - Python連携完全版           |
//|             ブレイクアウトロジック + 通信機能 + リスク管理        |
//+------------------------------------------------------------------+

#property strict
#property copyright "Claude Code"
#property link      "https://claude.ai"
#property version   "2.00"

//--- 通信パラメータ
input string Section1 = "=== 通信設定 ===";              // 通信設定
input string PythonServerHost = "localhost";             // Python TCP サーバーホスト
input int    PythonServerPort = 8888;                    // Python TCP サーバーポート
input string MessageFileDirectory = "C:\\temp\\mt4_bridge_messages"; // メッセージファイルディレクトリ
input bool   UseTCPCommunication = true;                 // TCP通信使用
input bool   UseFileCommunication = true;                // ファイル通信使用
input int    HeartbeatInterval = 5;                      // ハートビート間隔（秒）

//--- ブレイクアウトパラメータ
input string Section2 = "=== ブレイクアウト設定 ===";    // ブレイクアウト設定
input int    H4_RangePeriod = 24;                        // H4レンジ期間（バー数）
input int    H1_RangePeriod = 24;                        // H1レンジ期間（バー数）
input double MinBreakDistance = 5.0;                      // 最小ブレイク幅（pips）
input int    ATR_Period = 14;                            // ATR期間

//--- リスク管理パラメータ
input string Section3 = "=== リスク管理設定 ===";        // リスク管理設定
input double RiskPercent = 1.5;                          // リスク割合（%）
input double ATR_MultiplierTP = 2.0;                     // 利確ATR倍率
input double ATR_MultiplierSL = 1.5;                     // 損切ATR倍率
input double MaxDailyLoss = 2.0;                         // 最大日次損失（%）
input double MaxMonthlyDrawdown = 12.0;                  // 最大月次ドローダウン（%）
input int    MaxConsecutiveLosses = 4;                   // 最大連続損失数

//--- セッションフィルター
input string Section4 = "=== セッション設定 ===";        // セッション設定
input bool   UseLondonSession = true;                    // ロンドンセッション使用
input bool   UseNewYorkSession = true;                   // ニューヨークセッション使用
input bool   UseTokyoSession = false;                    // 東京セッション使用
input int    LondonStart = 7;                            // ロンドン開始（GMT）
input int    LondonEnd = 16;                             // ロンドン終了（GMT）
input int    NewYorkStart = 12;                          // ニューヨーク開始（GMT）
input int    NewYorkEnd = 21;                            // ニューヨーク終了（GMT）
input int    TokyoStart = 23;                            // 東京開始（GMT）
input int    TokyoEnd = 8;                               // 東京終了（GMT）

//--- 実行パラメータ
input string Section5 = "=== 実行設定 ===";              // 実行設定
input bool   AutoExecuteTrades = true;                    // 自動取引実行
input int    MaxSlippage = 3;                            // 最大スリッページ（ポイント）
input int    MagicNumber = 20250720;                     // マジックナンバー
input bool   EnableDebugPrint = true;                     // デバッグ出力有効

// Windows API定義（TCP通信用）
#import "ws2_32.dll"
   int socket(int af, int type, int protocol);
   int connect(int socket, int& sockaddr[], int namelen);
   int send(int socket, string buffer, int length, int flags);
   int recv(int socket, string& buffer, int length, int flags);
   int closesocket(int socket);
   int WSAGetLastError();
   int WSAStartup(int wVersionRequested, int& wsaData[]);
   int WSACleanup();
#import

// ソケット定数
#define AF_INET         2
#define SOCK_STREAM     1
#define IPPROTO_TCP     6
#define SOCKET_ERROR    -1
#define INVALID_SOCKET  -1

//--- グローバル変数（通信）
int SocketHandle = INVALID_SOCKET;
bool IsConnected = false;
datetime LastHeartbeat = 0;
datetime LastConnectionAttempt = 0;
int MessageCounter = 0;

//--- グローバル変数（ブレイクアウト）
double H4_RangeHigh = 0.0;
double H4_RangeLow = 0.0;
double H1_RangeHigh = 0.0;
double H1_RangeLow = 0.0;
datetime LastH4CalculationTime = 0;
datetime LastH1CalculationTime = 0;

//--- グローバル変数（リスク管理）
double DailyLoss = 0.0;
double MonthlyDrawdown = 0.0;
int ConsecutiveLosses = 0;
datetime LastTradeDate = 0;
datetime LastMonthStart = 0;
double MonthStartBalance = 0.0;
double InitialBalance = 0.0;

//--- 統計情報
int TotalSignalsGenerated = 0;
int TotalTradesExecuted = 0;
int WinningTrades = 0;
int LosingTrades = 0;

//+------------------------------------------------------------------+
//| TCP接続関数                                                      |
//+------------------------------------------------------------------+
bool ConnectToTCPServer()
{
    if(SocketHandle != INVALID_SOCKET)
    {
        closesocket(SocketHandle);
        SocketHandle = INVALID_SOCKET;
    }
    
    // Winsock初期化
    int wsaData[100];
    if(WSAStartup(0x0202, wsaData) != 0)
    {
        Print("❌ WSAStartup失敗");
        return false;
    }
    
    // ソケット作成
    SocketHandle = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if(SocketHandle == INVALID_SOCKET)
    {
        Print("❌ ソケット作成失敗: ", WSAGetLastError());
        return false;
    }
    
    // サーバーアドレス設定
    int sockaddr[4];
    sockaddr[0] = AF_INET;
    sockaddr[1] = PythonServerPort;
    sockaddr[2] = 0x0100007F; // 127.0.0.1
    sockaddr[3] = 0;
    
    // 接続
    if(connect(SocketHandle, sockaddr, 16) == SOCKET_ERROR)
    {
        Print("❌ TCP接続失敗: ", WSAGetLastError());
        closesocket(SocketHandle);
        SocketHandle = INVALID_SOCKET;
        return false;
    }
    
    IsConnected = true;
    LastConnectionAttempt = TimeGMT();
    return true;
}

//+------------------------------------------------------------------+
//| メッセージ送信関数                                               |
//+------------------------------------------------------------------+
bool SendMessage(string message)
{
    bool success = false;
    
    // TCP送信試行
    if(UseTCPCommunication && IsConnected && SocketHandle != INVALID_SOCKET)
    {
        if(send(SocketHandle, message, StringLen(message), 0) != SOCKET_ERROR)
        {
            success = true;
            if(EnableDebugPrint) Print("✅ TCP送信成功: ", message);
        }
        else
        {
            IsConnected = false;
            if(EnableDebugPrint) Print("❌ TCP送信失敗");
        }
    }
    
    // ファイル送信（TCP失敗時またはファイル通信有効時）
    if(UseFileCommunication && (!success || !UseTCPCommunication))
    {
        string filename = MessageFileDirectory + "\\signals\\signal_" + 
                         IntegerToString(MessageCounter++) + ".json";
        int handle = FileOpen(filename, FILE_WRITE|FILE_TXT);
        if(handle != INVALID_HANDLE)
        {
            FileWriteString(handle, message);
            FileClose(handle);
            success = true;
            if(EnableDebugPrint) Print("✅ ファイル送信成功: ", filename);
        }
    }
    
    return success;
}

//+------------------------------------------------------------------+
//| ATR計算関数                                                      |
//+------------------------------------------------------------------+
double CalculateATR(int timeframe, int period)
{
    double atr = iATR(Symbol(), timeframe, period, 0);
    return NormalizeDouble(atr, Digits);
}

//+------------------------------------------------------------------+
//| レンジ計算関数                                                   |
//+------------------------------------------------------------------+
void CalculateRange(int timeframe, int period, double &rangeHigh, double &rangeLow)
{
    rangeHigh = 0.0;
    rangeLow = 999999.0;
    
    for(int i = 1; i <= period; i++)
    {
        double high = iHigh(Symbol(), timeframe, i);
        double low = iLow(Symbol(), timeframe, i);
        
        if(high > rangeHigh) rangeHigh = high;
        if(low < rangeLow) rangeLow = low;
    }
    
    rangeHigh = NormalizeDouble(rangeHigh, Digits);
    rangeLow = NormalizeDouble(rangeLow, Digits);
}

//+------------------------------------------------------------------+
//| ブレイクアウト検出関数                                           |
//+------------------------------------------------------------------+
bool CheckBreakout(double currentPrice, double rangeHigh, double rangeLow, 
                   double minBreakDistance, int &direction)
{
    double pipSize = MarketInfo(Symbol(), MODE_POINT);
    if(Digits == 3 || Digits == 5) pipSize *= 10;
    
    double breakDistance = minBreakDistance * pipSize;
    
    if(currentPrice > rangeHigh + breakDistance)
    {
        direction = 1;
        return true;
    }
    
    if(currentPrice < rangeLow - breakDistance)
    {
        direction = -1;
        return true;
    }
    
    direction = 0;
    return false;
}

//+------------------------------------------------------------------+
//| 取引セッション確認関数                                           |
//+------------------------------------------------------------------+
bool IsInTradingSession()
{
    datetime currentGMT = TimeGMT();
    int currentHour = TimeHour(currentGMT);
    
    if(UseLondonSession && currentHour >= LondonStart && currentHour < LondonEnd)
        return true;
    
    if(UseNewYorkSession && currentHour >= NewYorkStart && currentHour < NewYorkEnd)
        return true;
    
    if(UseTokyoSession)
    {
        if(TokyoStart > TokyoEnd)
        {
            if(currentHour >= TokyoStart || currentHour < TokyoEnd)
                return true;
        }
        else
        {
            if(currentHour >= TokyoStart && currentHour < TokyoEnd)
                return true;
        }
    }
    
    return false;
}

//+------------------------------------------------------------------+
//| ポジションサイズ計算関数                                         |
//+------------------------------------------------------------------+
double CalculatePositionSize(double stopLossDistance)
{
    double accountBalance = AccountBalance();
    double riskAmount = accountBalance * (RiskPercent / 100.0);
    
    double tickValue = MarketInfo(Symbol(), MODE_TICKVALUE);
    double pipValue = tickValue;
    if(Digits == 3 || Digits == 5) pipValue = tickValue * 10;
    
    double lotSize = riskAmount / (stopLossDistance / MarketInfo(Symbol(), MODE_POINT) * pipValue);
    
    double minLot = MarketInfo(Symbol(), MODE_MINLOT);
    double maxLot = MarketInfo(Symbol(), MODE_MAXLOT);
    double lotStep = MarketInfo(Symbol(), MODE_LOTSTEP);
    
    lotSize = MathFloor(lotSize / lotStep) * lotStep;
    lotSize = MathMax(lotSize, minLot);
    lotSize = MathMin(lotSize, maxLot);
    
    return NormalizeDouble(lotSize, 2);
}

//+------------------------------------------------------------------+
//| リスク管理チェック関数                                           |
//+------------------------------------------------------------------+
bool CheckRiskLimits()
{
    if(DailyLoss >= MaxDailyLoss)
    {
        if(EnableDebugPrint) Print("❌ 日次損失限界到達: ", DailyLoss, "%");
        return false;
    }
    
    if(MonthlyDrawdown >= MaxMonthlyDrawdown)
    {
        if(EnableDebugPrint) Print("❌ 月次ドローダウン限界到達: ", MonthlyDrawdown, "%");
        return false;
    }
    
    if(ConsecutiveLosses >= MaxConsecutiveLosses)
    {
        if(EnableDebugPrint) Print("❌ 連続損失限界到達: ", ConsecutiveLosses, "回");
        return false;
    }
    
    return true;
}

//+------------------------------------------------------------------+
//| リスク統計更新関数                                               |
//+------------------------------------------------------------------+
void UpdateRiskStatistics()
{
    datetime currentDate = TimeLocal();
    
    if(TimeDay(currentDate) != TimeDay(LastTradeDate))
    {
        DailyLoss = 0.0;
        LastTradeDate = currentDate;
    }
    
    if(TimeMonth(currentDate) != TimeMonth(LastMonthStart))
    {
        MonthlyDrawdown = 0.0;
        MonthStartBalance = AccountBalance();
        LastMonthStart = currentDate;
    }
    
    if(MonthStartBalance > 0)
    {
        double currentDrawdown = (MonthStartBalance - AccountBalance()) / MonthStartBalance * 100.0;
        if(currentDrawdown > MonthlyDrawdown)
            MonthlyDrawdown = currentDrawdown;
    }
}

//+------------------------------------------------------------------+
//| 取引実行関数                                                     |
//+------------------------------------------------------------------+
bool ExecuteTrade(int direction, double lotSize, double slDistance, double tpDistance)
{
    if(!AutoExecuteTrades) return false;
    
    double price, sl, tp;
    int orderType;
    
    if(direction > 0) // BUY
    {
        orderType = OP_BUY;
        price = Ask;
        sl = price - slDistance;
        tp = price + tpDistance;
    }
    else // SELL
    {
        orderType = OP_SELL;
        price = Bid;
        sl = price + slDistance;
        tp = price - tpDistance;
    }
    
    int ticket = OrderSend(Symbol(), orderType, lotSize, price, MaxSlippage, 
                          sl, tp, "Breakout EA", MagicNumber, 0, 
                          direction > 0 ? clrBlue : clrRed);
    
    if(ticket > 0)
    {
        TotalTradesExecuted++;
        Print("✅ 取引実行成功: Ticket=", ticket);
        return true;
    }
    else
    {
        Print("❌ 取引実行失敗: Error=", GetLastError());
        return false;
    }
}

//+------------------------------------------------------------------+
//| シグナル生成とJSON作成関数                                       |
//+------------------------------------------------------------------+
void GenerateAndSendSignal(int direction, double lotSize, double slDistance, double tpDistance)
{
    TotalSignalsGenerated++;
    
    // JSON形式のシグナル作成
    string signal = "{";
    signal += "\"type\": \"BREAKOUT_SIGNAL\",";
    signal += "\"symbol\": \"" + Symbol() + "\",";
    signal += "\"direction\": \"" + (direction > 0 ? "BUY" : "SELL") + "\",";
    signal += "\"lot_size\": " + DoubleToString(lotSize, 2) + ",";
    signal += "\"sl_distance\": " + DoubleToString(slDistance, Digits) + ",";
    signal += "\"tp_distance\": " + DoubleToString(tpDistance, Digits) + ",";
    signal += "\"current_price\": " + DoubleToString(Bid, Digits) + ",";
    signal += "\"h4_range_high\": " + DoubleToString(H4_RangeHigh, Digits) + ",";
    signal += "\"h4_range_low\": " + DoubleToString(H4_RangeLow, Digits) + ",";
    signal += "\"h1_range_high\": " + DoubleToString(H1_RangeHigh, Digits) + ",";
    signal += "\"h1_range_low\": " + DoubleToString(H1_RangeLow, Digits) + ",";
    signal += "\"atr\": " + DoubleToString(CalculateATR(PERIOD_H1, ATR_Period), Digits) + ",";
    signal += "\"account_balance\": " + DoubleToString(AccountBalance(), 2) + ",";
    signal += "\"risk_percent\": " + DoubleToString(RiskPercent, 2) + ",";
    signal += "\"timestamp\": \"" + TimeToString(TimeGMT(), TIME_DATE|TIME_SECONDS) + "\"";
    signal += "}";
    
    // シグナル送信
    if(SendMessage(signal))
    {
        Print("📤 ブレイクアウトシグナル送信成功");
        
        // 自動実行が有効な場合は取引実行
        if(AutoExecuteTrades)
        {
            ExecuteTrade(direction, lotSize, slDistance, tpDistance);
        }
    }
}

//+------------------------------------------------------------------+
//| 統計情報表示関数                                                 |
//+------------------------------------------------------------------+
void PrintStatistics()
{
    Print("=== 統計情報 ===");
    Print("初期残高: ", InitialBalance);
    Print("現在残高: ", AccountBalance());
    Print("総利益: ", AccountBalance() - InitialBalance);
    Print("シグナル生成数: ", TotalSignalsGenerated);
    Print("取引実行数: ", TotalTradesExecuted);
    Print("勝ちトレード: ", WinningTrades);
    Print("負けトレード: ", LosingTrades);
    Print("日次損失: ", DailyLoss, "%");
    Print("月次ドローダウン: ", MonthlyDrawdown, "%");
    Print("連続損失: ", ConsecutiveLosses);
    Print("================");
}

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("=== BreakoutIntegratedEA 初期化開始 ===");
    
    // 初期設定
    InitialBalance = AccountBalance();
    MonthStartBalance = AccountBalance();
    LastMonthStart = TimeLocal();
    LastTradeDate = TimeLocal();
    
    // TCP接続試行
    if(UseTCPCommunication)
    {
        if(ConnectToTCPServer())
        {
            Print("✅ TCP接続成功");
        }
        else
        {
            Print("⚠️ TCP接続失敗 - ファイル通信モード");
        }
    }
    
    // ファイルディレクトリ作成
    if(UseFileCommunication)
    {
        // ディレクトリ作成処理（Windows APIを使用）
        Print("📁 ファイル通信ディレクトリ設定: ", MessageFileDirectory);
    }
    
    // レンジ計算
    CalculateRange(PERIOD_H4, H4_RangePeriod, H4_RangeHigh, H4_RangeLow);
    CalculateRange(PERIOD_H1, H1_RangePeriod, H1_RangeHigh, H1_RangeLow);
    
    Print("初期H4レンジ: High=", H4_RangeHigh, " Low=", H4_RangeLow);
    Print("初期H1レンジ: High=", H1_RangeHigh, " Low=", H1_RangeLow);
    
    PrintStatistics();
    
    Print("=== BreakoutIntegratedEA 初期化完了 ===");
    return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    Print("=== BreakoutIntegratedEA 終了処理 ===");
    
    // TCP接続クローズ
    if(SocketHandle != INVALID_SOCKET)
    {
        closesocket(SocketHandle);
        SocketHandle = INVALID_SOCKET;
    }
    
    // Winsockクリーンアップ
    WSACleanup();
    
    // 最終統計表示
    PrintStatistics();
    
    Print("=== BreakoutIntegratedEA 終了完了 ===");
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    // リスク統計更新
    UpdateRiskStatistics();
    
    // ハートビート送信
    if(IsConnected && TimeGMT() - LastHeartbeat > HeartbeatInterval)
    {
        string heartbeat = "{\"type\": \"HEARTBEAT\", \"timestamp\": \"" + 
                          TimeToString(TimeGMT(), TIME_DATE|TIME_SECONDS) + "\"}";
        SendMessage(heartbeat);
        LastHeartbeat = TimeGMT();
    }
    
    // H4レンジ更新
    datetime currentH4Time = iTime(Symbol(), PERIOD_H4, 0);
    if(currentH4Time != LastH4CalculationTime)
    {
        CalculateRange(PERIOD_H4, H4_RangePeriod, H4_RangeHigh, H4_RangeLow);
        LastH4CalculationTime = currentH4Time;
        if(EnableDebugPrint) Print("H4レンジ更新: High=", H4_RangeHigh, " Low=", H4_RangeLow);
    }
    
    // H1レンジ更新
    datetime currentH1Time = iTime(Symbol(), PERIOD_H1, 0);
    if(currentH1Time != LastH1CalculationTime)
    {
        CalculateRange(PERIOD_H1, H1_RangePeriod, H1_RangeHigh, H1_RangeLow);
        LastH1CalculationTime = currentH1Time;
        if(EnableDebugPrint) Print("H1レンジ更新: High=", H1_RangeHigh, " Low=", H1_RangeLow);
    }
    
    // ブレイクアウトチェック
    if(!IsInTradingSession() || !CheckRiskLimits() || OrdersTotal() > 0)
        return;
    
    double currentPrice = Bid;
    int h4Direction = 0, h1Direction = 0;
    
    bool h4Breakout = CheckBreakout(currentPrice, H4_RangeHigh, H4_RangeLow, 
                                    MinBreakDistance, h4Direction);
    bool h1Breakout = CheckBreakout(currentPrice, H1_RangeHigh, H1_RangeLow, 
                                    MinBreakDistance, h1Direction);
    
    // 両タイムフレームでブレイクアウト確認
    if(h4Breakout && h1Breakout && h4Direction == h1Direction)
    {
        double atr = CalculateATR(PERIOD_H1, ATR_Period);
        double stopLossDistance = atr * ATR_MultiplierSL;
        double takeProfitDistance = atr * ATR_MultiplierTP;
        double lotSize = CalculatePositionSize(stopLossDistance);
        
        if(EnableDebugPrint)
        {
            Print("🎯 ブレイクアウトシグナル検出");
            Print("  方向: ", (h4Direction > 0 ? "BUY" : "SELL"));
            Print("  ロットサイズ: ", lotSize);
        }
        
        GenerateAndSendSignal(h4Direction, lotSize, stopLossDistance, takeProfitDistance);
    }
}

//+------------------------------------------------------------------+
//| Trade function - 取引結果処理                                    |
//+------------------------------------------------------------------+
void OnTrade()
{
    // 最新の取引結果を確認
    if(OrdersHistoryTotal() > 0)
    {
        if(OrderSelect(OrdersHistoryTotal() - 1, SELECT_BY_POS, MODE_HISTORY))
        {
            if(OrderMagicNumber() == MagicNumber && OrderCloseTime() > 0)
            {
                double profit = OrderProfit() + OrderSwap() + OrderCommission();
                
                if(profit > 0)
                {
                    WinningTrades++;
                    ConsecutiveLosses = 0;
                }
                else
                {
                    LosingTrades++;
                    ConsecutiveLosses++;
                    
                    // 日次損失更新
                    double lossPercent = MathAbs(profit) / InitialBalance * 100.0;
                    DailyLoss += lossPercent;
                }
                
                // 結果をPythonに送信
                string result = "{";
                result += "\"type\": \"TRADE_RESULT\",";
                result += "\"ticket\": " + IntegerToString(OrderTicket()) + ",";
                result += "\"symbol\": \"" + OrderSymbol() + "\",";
                result += "\"direction\": \"" + (OrderType() == OP_BUY ? "BUY" : "SELL") + "\",";
                result += "\"profit\": " + DoubleToString(profit, 2) + ",";
                result += "\"close_time\": \"" + TimeToString(OrderCloseTime(), TIME_DATE|TIME_SECONDS) + "\"";
                result += "}";
                
                SendMessage(result);
            }
        }
    }
}

//+------------------------------------------------------------------+