//+------------------------------------------------------------------+
//| MT4_CSV_Communicator.mq4                                        |
//| CSV通信によるPython統合テスト用EA                                    |
//| MT4-Python統合の第一段階として安全で確実なCSV通信を実装                 |
//+------------------------------------------------------------------+
#property copyright "Trading Development Project 2025"
#property version   "1.00"
#property strict

// 入力パラメータ
input string DataDirectory = "MT4_Data";           // データディレクトリ
input int    UpdateIntervalMs = 100;               // 更新間隔（ミリ秒）
input bool   EnablePythonSignals = true;           // Pythonシグナル受信有効
input double DefaultLotSize = 0.1;                 // デフォルトロットサイズ
input int    MaxSpreadPips = 3;                    // 最大スプレッド（pips）
input int    MagicNumber = 20250720;               // ユニークなマジックナンバー
input int    MaxRetries = 3;                       // 注文失敗時の最大リトライ回数

// グローバル変数
string g_PriceDataFile;
string g_SignalFile; 
string g_StatusFile;
datetime g_LastSignalCheck = 0;
datetime g_LastPriceUpdate = 0;
int g_FileHandle = -1;
bool g_PythonConnected = false;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("🚀 MT4-CSV通信システム初期化開始");
    
    // ファイルパス設定
    g_PriceDataFile = DataDirectory + "\\price_data.csv";
    g_SignalFile = DataDirectory + "\\trading_signals.csv";
    g_StatusFile = DataDirectory + "\\connection_status.csv";
    
    // データディレクトリ作成
    if(!CreateDataDirectory())
    {
        Print("❌ データディレクトリ作成失敗: ", DataDirectory);
        return INIT_FAILED;
    }
    
    // 初期ファイル作成
    if(!InitializeCsvFiles())
    {
        Print("❌ CSVファイル初期化失敗");
        return INIT_FAILED;
    }
    
    // ステータス更新
    WriteConnectionStatus("MT4_STARTED");
    
    Print("✅ MT4-CSV通信システム初期化完了");
    Print("   価格データファイル: ", g_PriceDataFile);
    Print("   シグナルファイル: ", g_SignalFile);
    Print("   ステータスファイル: ", g_StatusFile);
    
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    WriteConnectionStatus("MT4_STOPPED");
    
    if(g_FileHandle != -1)
    {
        FileClose(g_FileHandle);
        g_FileHandle = -1;
    }
    
    Print("🛑 MT4-CSV通信システム停止");
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    // 価格データ更新（指定間隔ごと）
    if(TimeCurrent() - g_LastPriceUpdate >= UpdateIntervalMs / 1000)
    {
        UpdatePriceData();
        g_LastPriceUpdate = TimeCurrent();
    }
    
    // Pythonシグナル確認（1秒ごと）
    if(EnablePythonSignals && TimeCurrent() - g_LastSignalCheck >= 1)
    {
        CheckPythonSignals();
        g_LastSignalCheck = TimeCurrent();
    }
}

//+------------------------------------------------------------------+
//| データディレクトリ作成                                              |
//+------------------------------------------------------------------+
bool CreateDataDirectory()
{
    string folderPath = TerminalInfoString(TERMINAL_DATA_PATH) + "\\MQL4\\Files\\" + DataDirectory;
    
    // WindowsAPIを使用してディレクトリ作成を試行
    // MQL4では直接ディレクトリ作成ができないため、ファイル作成で代用
    int handle = FileOpen(DataDirectory + "\\test.txt", FILE_WRITE | FILE_TXT);
    if(handle != -1)
    {
        FileClose(handle);
        FileDelete(DataDirectory + "\\test.txt");
        return true;
    }
    
    return false;
}

//+------------------------------------------------------------------+
//| CSVファイル初期化                                                 |
//+------------------------------------------------------------------+
bool InitializeCsvFiles()
{
    // 価格データファイル初期化
    int handle = FileOpen(g_PriceDataFile, FILE_WRITE | FILE_CSV);
    if(handle == -1)
    {
        Print("❌ 価格データファイル作成失敗: ", GetLastError());
        return false;
    }
    
    // ヘッダー書き込み
    FileWrite(handle, "timestamp", "symbol", "bid", "ask", "volume");
    FileClose(handle);
    
    Print("✅ CSVファイル初期化完了");
    return true;
}

//+------------------------------------------------------------------+
//| 価格データ更新                                                    |
//+------------------------------------------------------------------+
void UpdatePriceData()
{
    int handle = FileOpen(g_PriceDataFile, FILE_WRITE | FILE_CSV);
    if(handle == -1)
    {
        Print("❌ 価格データファイル更新失敗: ", GetLastError());
        return;
    }
    
    // ヘッダー書き込み
    FileWrite(handle, "timestamp", "symbol", "bid", "ask", "volume");
    
    // 現在の価格データ書き込み
    double timestamp = (double)TimeCurrent();
    string symbol = Symbol();
    double bid = Bid;
    double ask = Ask;
    long volume = Volume[0];
    
    FileWrite(handle, DoubleToString(timestamp, 0), symbol, 
              DoubleToString(bid, Digits), DoubleToString(ask, Digits), 
              IntegerToString(volume));
    
    FileClose(handle);
}

//+------------------------------------------------------------------+
//| Pythonシグナル確認                                                |
//+------------------------------------------------------------------+
void CheckPythonSignals()
{
    int handle = FileOpen(g_SignalFile, FILE_READ | FILE_CSV);
    if(handle == -1)
    {
        // ファイルが存在しない場合は問題なし
        return;
    }
    
    string headers = FileReadString(handle);  // ヘッダー行スキップ
    
    string latestSignal = "";
    // ファイルの最後の行を読む
    while(!FileIsEnding(handle))
    {
        latestSignal = FileReadString(handle);
    }
    
    FileClose(handle);
    
    if(latestSignal != "")
    {
        ProcessPythonSignal(latestSignal);
    }
}

//+------------------------------------------------------------------+
//| Pythonシグナル処理                                                |
//+------------------------------------------------------------------+
void ProcessPythonSignal(string signalData)
{
    // CSV行をパース: timestamp,symbol,action,price,confidence,volume,stop_loss,take_profit
    string parts[];
    int count = StringSplit(signalData, ',', parts);
    
    if(count < 8)
    {
        Print("❌ 不正なシグナルデータ: ", signalData);
        return;
    }
    
    // シグナルデータ抽出
    string timestamp = parts[0];
    string signalSymbol = parts[1];
    string action = parts[2];
    double price = StringToDouble(parts[3]);
    double confidence = StringToDouble(parts[4]);
    double volume = StringToDouble(parts[5]);
    double stopLoss = StringToDouble(parts[6]);
    double takeProfit = StringToDouble(parts[7]);
    
    // 現在のシンボルと一致する場合のみ処理
    if(signalSymbol != Symbol())
    {
        return;
    }
    
    // 信頼度チェック
    if(confidence < 0.3)
    {
        Print("⚠️ 信頼度が低いため注文をスキップ: ", confidence);
        return;
    }
    
    // スプレッドチェック
    double currentSpread = (Ask - Bid) / Point;
    if(currentSpread > MaxSpreadPips)
    {
        Print("⚠️ スプレッドが大きすぎるため注文をスキップ: ", currentSpread, " pips");
        return;
    }
    
    // 注文実行
    ExecuteOrder(action, volume, stopLoss, takeProfit, confidence);
}

//+------------------------------------------------------------------+
//| 注文実行                                                          |
//+------------------------------------------------------------------+
void ExecuteOrder(string action, double lotSize, double stopLoss, double takeProfit, double confidence)
{
    int orderType;
    double openPrice;
    color orderColor;
    
    // 注文タイプ設定
    if(action == "BUY")
    {
        orderType = OP_BUY;
        openPrice = Ask;
        orderColor = clrBlue;
    }
    else if(action == "SELL")
    {
        orderType = OP_SELL;
        openPrice = Bid;
        orderColor = clrRed;
    }
    else
    {
        Print("❌ 不明な注文タイプ: ", action);
        return;
    }
    
    // ロットサイズ検証
    double minLot = MarketInfo(Symbol(), MODE_MINLOT);
    double maxLot = MarketInfo(Symbol(), MODE_MAXLOT);
    lotSize = MathMax(minLot, MathMin(maxLot, lotSize));
    
    // 注文コメント作成
    string comment = StringFormat("Python_%s_%.2f", action, confidence);
    
    // 注文送信（リトライ機能付き）
    int ticket = -1;
    int attempts = 0;
    
    while(attempts < MaxRetries && ticket <= 0)
    {
        attempts++;
        
        ticket = OrderSend(Symbol(), orderType, lotSize, openPrice, 3, 
                          stopLoss, takeProfit, comment, MagicNumber, 0, orderColor);
        
        if(ticket > 0)
        {
            Print("✅ 注文成功 - Ticket: ", ticket, " Action: ", action, 
                  " Lots: ", lotSize, " Price: ", openPrice, " Confidence: ", confidence,
                  " Attempts: ", attempts);
            
            WriteConnectionStatus("ORDER_EXECUTED");
            break;
        }
        else
        {
            int error = GetLastError();
            string errorMsg = "";
            
            // エラー種別による詳細分析
            switch(error)
            {
                case ERR_SERVER_BUSY:
                    errorMsg = "Server Busy - Retrying";
                    Sleep(1000); // 1秒待機
                    break;
                case ERR_TRADE_TIMEOUT:
                    errorMsg = "Trade Timeout - Retrying";
                    Sleep(500);
                    break;
                case ERR_INVALID_PRICE:
                    errorMsg = "Invalid Price - Cannot retry";
                    attempts = MaxRetries; // リトライ停止
                    break;
                case ERR_INSUFFICIENT_MONEY:
                    errorMsg = "Insufficient Money - Cannot retry";
                    attempts = MaxRetries;
                    break;
                default:
                    errorMsg = "Unknown Error: " + IntegerToString(error);
                    Sleep(300);
                    break;
            }
            
            Print("❌ 注文失敗 (", attempts, "/", MaxRetries, ") - ", errorMsg,
                  " Action: ", action, " Lots: ", lotSize, " Price: ", openPrice,
                  " Spread: ", DoubleToString((Ask - Bid) / Point, 1), " pips");
            
            if(attempts >= MaxRetries)
            {
                WriteConnectionStatus("ORDER_FAILED_FINAL");
            }
        }
    }
}

//+------------------------------------------------------------------+
//| 接続ステータス書き込み                                              |
//+------------------------------------------------------------------+
void WriteConnectionStatus(string status)
{
    int handle = FileOpen(g_StatusFile, FILE_WRITE | FILE_CSV);
    if(handle == -1)
    {
        Print("❌ ステータスファイル書き込み失敗: ", GetLastError());
        return;
    }
    
    // ヘッダーとデータ書き込み
    FileWrite(handle, "timestamp", "status", "heartbeat");
    FileWrite(handle, DoubleToString(TimeCurrent(), 0), status, DoubleToString(TimeCurrent(), 0));
    
    FileClose(handle);
}

//+------------------------------------------------------------------+
//| チャートイベント処理                                               |
//+------------------------------------------------------------------+
void OnChartEvent(const int id, const long& lparam, const double& dparam, const string& sparam)
{
    // Python接続状態表示更新
    if(id == CHARTEVENT_CHART_CHANGE)
    {
        UpdateConnectionDisplay();
    }
}

//+------------------------------------------------------------------+
//| 接続状態表示更新                                                   |
//+------------------------------------------------------------------+
void UpdateConnectionDisplay()
{
    // チャートにPython接続状態を表示
    string labelName = "PythonConnectionStatus";
    string statusText = g_PythonConnected ? "🟢 Python Connected" : "🔴 Python Disconnected";
    color textColor = g_PythonConnected ? clrGreen : clrRed;
    
    if(ObjectFind(labelName) == -1)
    {
        ObjectCreate(labelName, OBJ_LABEL, 0, 0, 0);
        ObjectSet(labelName, OBJPROP_XDISTANCE, 20);
        ObjectSet(labelName, OBJPROP_YDISTANCE, 20);
        ObjectSet(labelName, OBJPROP_CORNER, CORNER_LEFT_UPPER);
    }
    
    ObjectSetText(labelName, statusText, 12, "Arial Bold", textColor);
}