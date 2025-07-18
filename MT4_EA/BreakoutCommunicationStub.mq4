//+------------------------------------------------------------------+
//|                                        BreakoutCommunicationStub.mq4 |
//|                                 Python-MT4通信スタブ EA                |
//|                         TCP・ファイル通信対応ブレイクアウト戦略           |
//+------------------------------------------------------------------+

#property strict
#property copyright "Claude Code"
#property link      "https://claude.ai"
#property version   "1.00"

// 外部パラメータ
input string PythonServerHost = "localhost";        // Python TCP サーバーホスト
input int    PythonServerPort = 8888;              // Python TCP サーバーポート
input string MessageFileDirectory = "C:\\temp\\mt4_bridge_messages"; // メッセージファイルディレクトリ
input bool   UseTCPCommunication = true;           // TCP通信使用
input bool   UseFileCommunication = true;          // ファイル通信使用
input double DefaultLotSize = 0.1;                 // デフォルトロット数
input int    MaxSlippage = 3;                      // 最大スリッページ（ポイント）
input int    HeartbeatInterval = 5;                // ハートビート間隔（秒）
input int    ConnectionTimeout = 10;               // 接続タイムアウト（秒）
input bool   EnableLogging = true;                 // ログ出力有効

// グローバル変数
int SocketHandle = INVALID_HANDLE;                  // TCP ソケットハンドル
datetime LastHeartbeat = 0;                        // 最後のハートビート時刻
datetime LastConnectionAttempt = 0;                 // 最後の接続試行時刻
bool IsConnected = false;                           // 接続状態
string CurrentSymbol = "";                          // 現在のシンボル
double CurrentPrice = 0.0;                          // 現在価格
int MessageCounter = 0;                             // メッセージカウンター

// 統計情報
int MessagesReceived = 0;                           // 受信メッセージ数
int MessagesSent = 0;                              // 送信メッセージ数
int ConnectionAttempts = 0;                         // 接続試行回数
int SuccessfulConnections = 0;                      // 成功した接続数
int ExecutedTrades = 0;                            // 実行された取引数

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("=== BreakoutCommunicationStub EA 初期化開始 ===");
    
    // 初期化
    CurrentSymbol = Symbol();
    CurrentPrice = MarketInfo(CurrentSymbol, MODE_BID);
    
    // TCP接続試行
    if (UseTCPCommunication)
    {
        if (ConnectToTCPServer())
        {
            Print("✅ TCP接続成功");
            SendHeartbeat();
        }
        else
        {
            Print("⚠️ TCP接続失敗 - ファイル通信にフォールバック");
        }
    }
    
    // ファイル通信ディレクトリ作成
    if (UseFileCommunication)
    {
        if (CreateDirectoryStructure())
        {
            Print("✅ ファイル通信ディレクトリ作成成功");
        }
        else
        {
            Print("❌ ファイル通信ディレクトリ作成失敗");
        }
    }
    
    // 初期統計情報表示
    PrintStatistics();
    
    Print("=== BreakoutCommunicationStub EA 初期化完了 ===");
    return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    Print("=== BreakoutCommunicationStub EA 終了処理開始 ===");
    
    // 終了理由表示
    string reasonText = "";
    switch(reason)
    {
        case REASON_PROGRAM: reasonText = "プログラム終了"; break;
        case REASON_REMOVE: reasonText = "EA削除"; break;
        case REASON_RECOMPILE: reasonText = "再コンパイル"; break;
        case REASON_CHARTCHANGE: reasonText = "チャート変更"; break;
        case REASON_CHARTCLOSE: reasonText = "チャートクローズ"; break;
        case REASON_PARAMETERS: reasonText = "パラメータ変更"; break;
        case REASON_ACCOUNT: reasonText = "口座変更"; break;
        case REASON_TEMPLATE: reasonText = "テンプレート変更"; break;
        case REASON_INITFAILED: reasonText = "初期化失敗"; break;
        case REASON_CLOSE: reasonText = "ターミナルクローズ"; break;
        default: reasonText = "不明な理由"; break;
    }
    
    Print("終了理由: ", reasonText);
    
    // 最終統計情報表示
    PrintStatistics();
    
    // TCP接続クローズ
    if (SocketHandle != INVALID_HANDLE)
    {
        SocketClose(SocketHandle);
        SocketHandle = INVALID_HANDLE;
        Print("✅ TCP接続クローズ完了");
    }
    
    Print("=== BreakoutCommunicationStub EA 終了処理完了 ===");
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    // 価格更新
    CurrentPrice = MarketInfo(CurrentSymbol, MODE_BID);
    
    // 接続状態チェック
    CheckConnection();
    
    // TCP通信処理
    if (UseTCPCommunication && IsConnected)
    {
        ProcessTCPMessages();
    }
    
    // ファイル通信処理
    if (UseFileCommunication)
    {
        ProcessFileMessages();
    }
    
    // ハートビート送信
    if (TimeCurrent() - LastHeartbeat >= HeartbeatInterval)
    {
        SendHeartbeat();
    }
}

//+------------------------------------------------------------------+
//| TCP サーバー接続                                                  |
//+------------------------------------------------------------------+
bool ConnectToTCPServer()
{
    ConnectionAttempts++;
    
    Print("TCP接続試行: ", PythonServerHost, ":", PythonServerPort);
    
    // 既存接続のクローズ
    if (SocketHandle != INVALID_HANDLE)
    {
        SocketClose(SocketHandle);
        SocketHandle = INVALID_HANDLE;
    }
    
    // 新規接続
    SocketHandle = SocketCreate();
    if (SocketHandle == INVALID_HANDLE)
    {
        Print("❌ ソケット作成失敗");
        return false;
    }
    
    // 接続試行
    if (SocketConnect(SocketHandle, PythonServerHost, PythonServerPort, ConnectionTimeout * 1000))
    {
        IsConnected = true;
        SuccessfulConnections++;
        LastConnectionAttempt = TimeCurrent();
        
        Print("✅ TCP接続成功");
        return true;
    }
    else
    {
        Print("❌ TCP接続失敗: ", GetLastError());
        SocketClose(SocketHandle);
        SocketHandle = INVALID_HANDLE;
        IsConnected = false;
        return false;
    }
}

//+------------------------------------------------------------------+
//| 接続状態チェック                                                  |
//+------------------------------------------------------------------+
void CheckConnection()
{
    if (!UseTCPCommunication)
        return;
    
    // 接続状態確認
    if (SocketHandle != INVALID_HANDLE)
    {
        if (!SocketIsConnected(SocketHandle))
        {
            Print("⚠️ TCP接続切断検出");
            IsConnected = false;
            SocketClose(SocketHandle);
            SocketHandle = INVALID_HANDLE;
        }
    }
    
    // 自動再接続
    if (!IsConnected && TimeCurrent() - LastConnectionAttempt >= 5)
    {
        Print("🔄 TCP自動再接続試行");
        ConnectToTCPServer();
    }
}

//+------------------------------------------------------------------+
//| TCP メッセージ処理                                               |
//+------------------------------------------------------------------+
void ProcessTCPMessages()
{
    if (SocketHandle == INVALID_HANDLE)
        return;
    
    // メッセージ受信
    string message = "";
    uint messageLength = SocketReadString(SocketHandle);
    
    if (messageLength > 0)
    {
        message = SocketReadString(SocketHandle);
        
        if (StringLen(message) > 0)
        {
            MessagesReceived++;
            
            if (EnableLogging)
            {
                Print("📨 TCP メッセージ受信: ", message);
            }
            
            // メッセージ解析・処理
            ProcessMessage(message);
        }
    }
}

//+------------------------------------------------------------------+
//| ファイル通信ディレクトリ作成                                      |
//+------------------------------------------------------------------+
bool CreateDirectoryStructure()
{
    // メインディレクトリ
    if (!FolderCreate(MessageFileDirectory, 0))
    {
        Print("❌ メインディレクトリ作成失敗: ", MessageFileDirectory);
        return false;
    }
    
    // サブディレクトリ作成
    string directories[] = {"inbox", "outbox", "processed", "failed"};
    
    for (int i = 0; i < ArraySize(directories); i++)
    {
        string dirPath = MessageFileDirectory + "\\" + directories[i];
        if (!FolderCreate(dirPath, 0))
        {
            Print("❌ サブディレクトリ作成失敗: ", dirPath);
            return false;
        }
    }
    
    return true;
}

//+------------------------------------------------------------------+
//| ファイル メッセージ処理                                           |
//+------------------------------------------------------------------+
void ProcessFileMessages()
{
    string inboxPath = MessageFileDirectory + "\\inbox";
    string fileName = "";
    long searchHandle = FileFindFirst(inboxPath + "\\*.msg", fileName);
    
    if (searchHandle != INVALID_HANDLE)
    {
        do
        {
            string filePath = inboxPath + "\\" + fileName;
            
            if (EnableLogging)
            {
                Print("📁 ファイル メッセージ検出: ", fileName);
            }
            
            // ファイル読み込み・処理
            if (ProcessMessageFile(filePath))
            {
                // 処理済みディレクトリに移動
                string processedPath = MessageFileDirectory + "\\processed\\" + fileName;
                if (FileMove(filePath, processedPath, 0))
                {
                    if (EnableLogging)
                    {
                        Print("✅ ファイル処理完了: ", fileName);
                    }
                }
                else
                {
                    Print("❌ ファイル移動失敗: ", fileName);
                }
            }
            else
            {
                // 失敗ディレクトリに移動
                string failedPath = MessageFileDirectory + "\\failed\\" + fileName;
                FileMove(filePath, failedPath, 0);
                Print("❌ ファイル処理失敗: ", fileName);
            }
            
        } while (FileFindNext(searchHandle, fileName));
        
        FileFindClose(searchHandle);
    }
}

//+------------------------------------------------------------------+
//| メッセージファイル処理                                            |
//+------------------------------------------------------------------+
bool ProcessMessageFile(string filePath)
{
    int fileHandle = FileOpen(filePath, FILE_READ | FILE_TXT);
    if (fileHandle == INVALID_HANDLE)
    {
        Print("❌ ファイル読み込み失敗: ", filePath);
        return false;
    }
    
    // ファイル内容読み込み
    string fileContent = "";
    while (!FileIsEnding(fileHandle))
    {
        fileContent += FileReadString(fileHandle);
    }
    
    FileClose(fileHandle);
    
    if (StringLen(fileContent) > 0)
    {
        MessagesReceived++;
        
        if (EnableLogging)
        {
            Print("📄 ファイル メッセージ読み込み: ", fileContent);
        }
        
        // メッセージ処理
        return ProcessMessage(fileContent);
    }
    
    return false;
}

//+------------------------------------------------------------------+
//| メッセージ処理                                                    |
//+------------------------------------------------------------------+
bool ProcessMessage(string message)
{
    // 簡単なJSON解析（実際の実装ではより堅牢な解析が必要）
    
    // メッセージタイプ判定
    if (StringFind(message, "\"message_type\":\"signal\"") >= 0)
    {
        return ProcessSignalMessage(message);
    }
    else if (StringFind(message, "\"message_type\":\"heartbeat\"") >= 0)
    {
        return ProcessHeartbeatMessage(message);
    }
    else if (StringFind(message, "\"message_type\":\"parameter_update\"") >= 0)
    {
        return ProcessParameterUpdateMessage(message);
    }
    else if (StringFind(message, "\"message_type\":\"status_request\"") >= 0)
    {
        return ProcessStatusRequestMessage(message);
    }
    
    Print("⚠️ 不明なメッセージタイプ: ", message);
    return false;
}

//+------------------------------------------------------------------+
//| シグナル メッセージ処理                                           |
//+------------------------------------------------------------------+
bool ProcessSignalMessage(string message)
{
    Print("🎯 取引シグナル受信");
    
    // 簡単なシグナル解析（実際の実装ではより詳細な解析が必要）
    string action = "BUY";  // デフォルト
    double price = CurrentPrice;
    double volume = DefaultLotSize;
    
    // アクション判定
    if (StringFind(message, "\"action\":\"BUY\"") >= 0)
    {
        action = "BUY";
    }
    else if (StringFind(message, "\"action\":\"SELL\"") >= 0)
    {
        action = "SELL";
    }
    else if (StringFind(message, "\"action\":\"CLOSE\"") >= 0)
    {
        action = "CLOSE";
    }
    
    // 取引実行
    bool result = ExecuteTrade(action, volume, price);
    
    // 確認応答送信
    SendConfirmation(result, action, price, volume);
    
    return result;
}

//+------------------------------------------------------------------+
//| ハートビート メッセージ処理                                       |
//+------------------------------------------------------------------+
bool ProcessHeartbeatMessage(string message)
{
    if (EnableLogging)
    {
        Print("💓 ハートビート受信");
    }
    
    // ハートビート応答送信
    SendHeartbeat();
    
    return true;
}

//+------------------------------------------------------------------+
//| パラメータ更新 メッセージ処理                                     |
//+------------------------------------------------------------------+
bool ProcessParameterUpdateMessage(string message)
{
    Print("⚙️ パラメータ更新メッセージ受信");
    
    // パラメータ更新処理（実装依存）
    // 実際の実装では、メッセージからパラメータを解析して更新
    
    return true;
}

//+------------------------------------------------------------------+
//| ステータス要求 メッセージ処理                                     |
//+------------------------------------------------------------------+
bool ProcessStatusRequestMessage(string message)
{
    Print("📊 ステータス要求受信");
    
    // ステータス応答送信
    SendStatusResponse();
    
    return true;
}

//+------------------------------------------------------------------+
//| 取引実行                                                         |
//+------------------------------------------------------------------+
bool ExecuteTrade(string action, double volume, double price)
{
    Print("🚀 取引実行開始: ", action, " ", volume, " lots at ", price);
    
    int ticket = -1;
    bool result = false;
    
    if (action == "BUY")
    {
        ticket = OrderSend(CurrentSymbol, OP_BUY, volume, Ask, MaxSlippage, 0, 0, 
                          "Python Signal BUY", 0, 0, clrGreen);
        result = (ticket > 0);
    }
    else if (action == "SELL")
    {
        ticket = OrderSend(CurrentSymbol, OP_SELL, volume, Bid, MaxSlippage, 0, 0, 
                          "Python Signal SELL", 0, 0, clrRed);
        result = (ticket > 0);
    }
    else if (action == "CLOSE")
    {
        // 全ポジションクローズ
        result = CloseAllPositions();
    }
    
    if (result)
    {
        ExecutedTrades++;
        Print("✅ 取引実行成功: Ticket=", ticket);
    }
    else
    {
        Print("❌ 取引実行失敗: Error=", GetLastError());
    }
    
    return result;
}

//+------------------------------------------------------------------+
//| 全ポジションクローズ                                             |
//+------------------------------------------------------------------+
bool CloseAllPositions()
{
    bool result = true;
    
    for (int i = OrdersTotal() - 1; i >= 0; i--)
    {
        if (OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
        {
            if (OrderSymbol() == CurrentSymbol)
            {
                bool closeResult = false;
                
                if (OrderType() == OP_BUY)
                {
                    closeResult = OrderClose(OrderTicket(), OrderLots(), Bid, MaxSlippage, clrRed);
                }
                else if (OrderType() == OP_SELL)
                {
                    closeResult = OrderClose(OrderTicket(), OrderLots(), Ask, MaxSlippage, clrGreen);
                }
                
                if (!closeResult)
                {
                    Print("❌ ポジションクローズ失敗: Ticket=", OrderTicket(), " Error=", GetLastError());
                    result = false;
                }
            }
        }
    }
    
    return result;
}

//+------------------------------------------------------------------+
//| ハートビート送信                                                 |
//+------------------------------------------------------------------+
void SendHeartbeat()
{
    string heartbeatMessage = StringConcatenate(
        "{",
        "\"message_type\":\"heartbeat\",",
        "\"timestamp\":", TimeCurrent(), ",",
        "\"data\":{\"status\":\"alive\",\"symbol\":\"", CurrentSymbol, "\",\"price\":", CurrentPrice, "},",
        "\"message_id\":\"heartbeat_", MessageCounter++, "\"",
        "}"
    );
    
    SendMessage(heartbeatMessage);
    LastHeartbeat = TimeCurrent();
    
    if (EnableLogging)
    {
        Print("💓 ハートビート送信");
    }
}

//+------------------------------------------------------------------+
//| 確認応答送信                                                     |
//+------------------------------------------------------------------+
void SendConfirmation(bool success, string action, double price, double volume)
{
    string confirmationMessage = StringConcatenate(
        "{",
        "\"message_type\":\"confirmation\",",
        "\"timestamp\":", TimeCurrent(), ",",
        "\"data\":{\"success\":", (success ? "true" : "false"), ",\"action\":\"", action, "\",\"price\":", price, ",\"volume\":", volume, "},",
        "\"message_id\":\"confirmation_", MessageCounter++, "\"",
        "}"
    );
    
    SendMessage(confirmationMessage);
    
    Print("📤 確認応答送信: ", (success ? "成功" : "失敗"));
}

//+------------------------------------------------------------------+
//| ステータス応答送信                                               |
//+------------------------------------------------------------------+
void SendStatusResponse()
{
    string statusMessage = StringConcatenate(
        "{",
        "\"message_type\":\"status_response\",",
        "\"timestamp\":", TimeCurrent(), ",",
        "\"data\":{",
        "\"symbol\":\"", CurrentSymbol, "\",",
        "\"price\":", CurrentPrice, ",",
        "\"connected\":", (IsConnected ? "true" : "false"), ",",
        "\"messages_received\":", MessagesReceived, ",",
        "\"messages_sent\":", MessagesSent, ",",
        "\"executed_trades\":", ExecutedTrades,
        "},",
        "\"message_id\":\"status_", MessageCounter++, "\"",
        "}"
    );
    
    SendMessage(statusMessage);
    
    Print("📊 ステータス応答送信");
}

//+------------------------------------------------------------------+
//| メッセージ送信                                                    |
//+------------------------------------------------------------------+
void SendMessage(string message)
{
    bool tcpSent = false;
    bool fileSent = false;
    
    // TCP送信
    if (UseTCPCommunication && IsConnected && SocketHandle != INVALID_HANDLE)
    {
        string messageWithNewline = message + "\n";
        int bytesSent = SocketSend(SocketHandle, messageWithNewline);
        tcpSent = (bytesSent > 0);
        
        if (tcpSent)
        {
            MessagesSent++;
            if (EnableLogging)
            {
                Print("📡 TCP メッセージ送信成功");
            }
        }
        else
        {
            Print("❌ TCP メッセージ送信失敗");
        }
    }
    
    // ファイル送信（TCPが失敗した場合のみ）
    if (UseFileCommunication && !tcpSent)
    {
        string fileName = "mt4_message_" + IntegerToString(MessageCounter) + "_" + IntegerToString(TimeCurrent()) + ".msg";
        string filePath = ActualMessageDirectory + "\\outbox\\" + fileName;
        
        int fileHandle = FileOpen(filePath, FILE_WRITE | FILE_TXT);
        if (fileHandle != INVALID_HANDLE)
        {
            FileWriteString(fileHandle, message);
            FileClose(fileHandle);
            fileSent = true;
            
            if (EnableLogging)
            {
                Print("📁 ファイル メッセージ送信成功: ", fileName);
            }
        }
        else
        {
            Print("❌ ファイル メッセージ送信失敗: ", filePath);
        }
    }
    
    // 送信確認
    if (!tcpSent && !fileSent)
    {
        Print("❌ メッセージ送信完全失敗");
    }
}

//+------------------------------------------------------------------+
//| 統計情報表示                                                     |
//+------------------------------------------------------------------+
void PrintStatistics()
{
    Print("=== 統計情報 ===");
    Print("受信メッセージ数: ", MessagesReceived);
    Print("送信メッセージ数: ", MessagesSent);
    Print("接続試行回数: ", ConnectionAttempts);
    Print("成功接続数: ", SuccessfulConnections);
    Print("実行取引数: ", ExecutedTrades);
    Print("現在接続状態: ", (IsConnected ? "接続中" : "切断中"));
    Print("===============");
}

//+------------------------------------------------------------------+
//| データセクション抽出                                             |
//+------------------------------------------------------------------+
string ExtractDataSection(string message)
{
    // data_json フィールドから値を抽出
    if (JsonParser.HasKey("data_json"))
    {
        return JsonParser.GetStringValue("data_json");
    }
    
    // 従来のdata オブジェクトを文字列として抽出（簡易実装）
    int dataStart = StringFind(message, "\"data\":");
    if (dataStart < 0)
    {
        return "";
    }
    
    dataStart += 7; // "data":をスキップ
    int braceCount = 0;
    int dataEnd = dataStart;
    bool inBrace = false;
    
    for (int i = dataStart; i < StringLen(message); i++)
    {
        string char = StringGetChar(message, i);
        
        if (char == "{")
        {
            braceCount++;
            inBrace = true;
        }
        else if (char == "}")
        {
            braceCount--;
            if (braceCount == 0 && inBrace)
            {
                dataEnd = i + 1;
                break;
            }
        }
    }
    
    if (dataEnd > dataStart)
    {
        return StringSubstr(message, dataStart, dataEnd - dataStart);
    }
    
    return "";
}