//+------------------------------------------------------------------+
//|                                                    JSONUtils.mqh |
//|                              堅牢なJSON解析・生成ユーティリティ   |
//|                                  Python-MT4通信用ライブラリ      |
//+------------------------------------------------------------------+

#property strict

// JSON値の型定義
enum JSON_VALUE_TYPE
{
    JSON_STRING,
    JSON_NUMBER,
    JSON_BOOLEAN,
    JSON_NULL,
    JSON_OBJECT,
    JSON_ARRAY
};

// JSON値構造体
struct JSONValue
{
    JSON_VALUE_TYPE type;
    string stringValue;
    double numberValue;
    bool booleanValue;
};

// JSON解析クラス
class JSONParser
{
private:
    string m_json;
    int m_position;
    int m_length;
    
    void SkipWhitespace();
    string ParseString();
    double ParseNumber();
    bool ParseBoolean();
    JSONValue ParseValue();
    bool IsWhitespace(string char);
    bool IsDigit(string char);
    string UnescapeString(string str);

public:
    JSONParser();
    ~JSONParser();
    
    bool ParseJSON(string json);
    string GetStringValue(string key);
    double GetNumberValue(string key);
    bool GetBooleanValue(string key);
    bool HasKey(string key);
    string GetLastError();
    
private:
    string m_lastError;
    string m_parsedKeys[];
    JSONValue m_parsedValues[];
    int m_keyCount;
};

// JSON生成クラス
class JSONBuilder
{
private:
    string m_json;
    bool m_firstItem;
    int m_objectLevel;

public:
    JSONBuilder();
    ~JSONBuilder();
    
    void StartObject();
    void EndObject();
    void AddString(string key, string value);
    void AddNumber(string key, double value);
    void AddBoolean(string key, bool value);
    void AddNull(string key);
    string ToString();
    void Reset();
    
private:
    string EscapeString(string str);
    void AddCommaIfNeeded();
};

//+------------------------------------------------------------------+
//| JSONParser実装                                                   |
//+------------------------------------------------------------------+

JSONParser::JSONParser()
{
    m_position = 0;
    m_length = 0;
    m_lastError = "";
    m_keyCount = 0;
    ArrayResize(m_parsedKeys, 100);
    ArrayResize(m_parsedValues, 100);
}

JSONParser::~JSONParser()
{
}

bool JSONParser::ParseJSON(string json)
{
    m_json = json;
    m_length = StringLen(json);
    m_position = 0;
    m_keyCount = 0;
    m_lastError = "";
    
    SkipWhitespace();
    
    if (m_position >= m_length || StringGetCharacter(m_json, m_position) != '{')
    {
        m_lastError = "JSONオブジェクトは{で開始する必要があります";
        return false;
    }
    
    m_position++; // {をスキップ
    SkipWhitespace();
    
    // 空のオブジェクト
    if (m_position < m_length && StringGetCharacter(m_json, m_position) == '}')
    {
        return true;
    }
    
    while (m_position < m_length)
    {
        SkipWhitespace();
        
        // キー解析
        if (StringGetCharacter(m_json, m_position) != '"')
        {
            m_lastError = "JSONキーは文字列である必要があります";
            return false;
        }
        
        string key = ParseString();
        if (m_lastError != "")
            return false;
            
        SkipWhitespace();
        
        // コロン確認
        if (m_position >= m_length || StringGetCharacter(m_json, m_position) != ':')
        {
            m_lastError = "JSONキーの後にはコロンが必要です";
            return false;
        }
        
        m_position++; // :をスキップ
        SkipWhitespace();
        
        // 値解析
        JSONValue value = ParseValue();
        if (m_lastError != "")
            return false;
            
        // キー・値を保存
        if (m_keyCount < ArraySize(m_parsedKeys))
        {
            m_parsedKeys[m_keyCount] = key;
            m_parsedValues[m_keyCount] = value;
            m_keyCount++;
        }
        
        SkipWhitespace();
        
        // カンマまたは終了ブレース
        if (m_position >= m_length)
        {
            m_lastError = "JSON文字列が不完全です";
            return false;
        }
        
        int currentChar = StringGetCharacter(m_json, m_position);
        if (currentChar == '}')
        {
            return true; // 正常終了
        }
        else if (currentChar == ',')
        {
            m_position++; // カンマをスキップして次の要素へ
        }
        else
        {
            m_lastError = "JSONフォーマットエラー: カンマまたは}が期待されます";
            return false;
        }
    }
    
    m_lastError = "JSON文字列が}で終了していません";
    return false;
}

JSONValue JSONParser::ParseValue()
{
    JSONValue value;
    SkipWhitespace();
    
    if (m_position >= m_length)
    {
        m_lastError = "JSON値が見つかりません";
        return value;
    }
    
    int currentChar = StringGetCharacter(m_json, m_position);
    
    if (currentChar == '"')
    {
        // 文字列
        value.type = JSON_STRING;
        value.stringValue = ParseString();
    }
    else if (currentChar == 't' || currentChar == 'f')
    {
        // boolean
        value.type = JSON_BOOLEAN;
        value.booleanValue = ParseBoolean();
    }
    else if (currentChar == 'n')
    {
        // null
        value.type = JSON_NULL;
        if (m_position + 4 <= m_length && StringSubstr(m_json, m_position, 4) == "null")
        {
            m_position += 4;
        }
        else
        {
            m_lastError = "不正なnull値";
        }
    }
    else if (IsDigit(StringGetChar(m_json, m_position)) || currentChar == '-')
    {
        // 数値
        value.type = JSON_NUMBER;
        value.numberValue = ParseNumber();
    }
    else
    {
        m_lastError = "未対応のJSON値タイプ";
    }
    
    return value;
}

string JSONParser::ParseString()
{
    if (m_position >= m_length || StringGetCharacter(m_json, m_position) != '"')
    {
        m_lastError = "文字列は\"で開始する必要があります";
        return "";
    }
    
    m_position++; // 開始の"をスキップ
    string result = "";
    
    while (m_position < m_length)
    {
        int currentChar = StringGetCharacter(m_json, m_position);
        
        if (currentChar == '"')
        {
            m_position++; // 終了の"をスキップ
            return UnescapeString(result);
        }
        else if (currentChar == '\\')
        {
            // エスケープ文字処理
            m_position++;
            if (m_position < m_length)
            {
                int escapeChar = StringGetCharacter(m_json, m_position);
                if (escapeChar == '"' || escapeChar == '\\' || escapeChar == '/')
                {
                    result += StringGetChar(m_json, m_position);
                }
                else if (escapeChar == 'n')
                {
                    result += "\n";
                }
                else if (escapeChar == 't')
                {
                    result += "\t";
                }
                else if (escapeChar == 'r')
                {
                    result += "\r";
                }
                else
                {
                    result += StringGetChar(m_json, m_position);
                }
                m_position++;
            }
        }
        else
        {
            result += StringGetChar(m_json, m_position);
            m_position++;
        }
    }
    
    m_lastError = "文字列が\"で終了していません";
    return "";
}

double JSONParser::ParseNumber()
{
    string numberStr = "";
    
    while (m_position < m_length)
    {
        string currentChar = StringGetChar(m_json, m_position);
        
        if (IsDigit(currentChar) || currentChar == "." || currentChar == "-" || currentChar == "+" || 
            currentChar == "e" || currentChar == "E")
        {
            numberStr += currentChar;
            m_position++;
        }
        else
        {
            break;
        }
    }
    
    return StringToDouble(numberStr);
}

bool JSONParser::ParseBoolean()
{
    if (m_position + 4 <= m_length && StringSubstr(m_json, m_position, 4) == "true")
    {
        m_position += 4;
        return true;
    }
    else if (m_position + 5 <= m_length && StringSubstr(m_json, m_position, 5) == "false")
    {
        m_position += 5;
        return false;
    }
    else
    {
        m_lastError = "不正なboolean値";
        return false;
    }
}

void JSONParser::SkipWhitespace()
{
    while (m_position < m_length && IsWhitespace(StringGetChar(m_json, m_position)))
    {
        m_position++;
    }
}

bool JSONParser::IsWhitespace(string char)
{
    return (char == " " || char == "\t" || char == "\n" || char == "\r");
}

bool JSONParser::IsDigit(string char)
{
    int code = StringGetCharacter(char, 0);
    return (code >= 48 && code <= 57); // '0' から '9'
}

string JSONParser::UnescapeString(string str)
{
    // 簡単なアンエスケープ実装
    StringReplace(str, "\\\"", "\"");
    StringReplace(str, "\\\\", "\\");
    StringReplace(str, "\\n", "\n");
    StringReplace(str, "\\t", "\t");
    StringReplace(str, "\\r", "\r");
    return str;
}

string JSONParser::GetStringValue(string key)
{
    for (int i = 0; i < m_keyCount; i++)
    {
        if (m_parsedKeys[i] == key && m_parsedValues[i].type == JSON_STRING)
        {
            return m_parsedValues[i].stringValue;
        }
    }
    return "";
}

double JSONParser::GetNumberValue(string key)
{
    for (int i = 0; i < m_keyCount; i++)
    {
        if (m_parsedKeys[i] == key && m_parsedValues[i].type == JSON_NUMBER)
        {
            return m_parsedValues[i].numberValue;
        }
    }
    return 0.0;
}

bool JSONParser::GetBooleanValue(string key)
{
    for (int i = 0; i < m_keyCount; i++)
    {
        if (m_parsedKeys[i] == key && m_parsedValues[i].type == JSON_BOOLEAN)
        {
            return m_parsedValues[i].booleanValue;
        }
    }
    return false;
}

bool JSONParser::HasKey(string key)
{
    for (int i = 0; i < m_keyCount; i++)
    {
        if (m_parsedKeys[i] == key)
        {
            return true;
        }
    }
    return false;
}

string JSONParser::GetLastError()
{
    return m_lastError;
}

//+------------------------------------------------------------------+
//| JSONBuilder実装                                                  |
//+------------------------------------------------------------------+

JSONBuilder::JSONBuilder()
{
    Reset();
}

JSONBuilder::~JSONBuilder()
{
}

void JSONBuilder::StartObject()
{
    m_json += "{";
    m_firstItem = true;
    m_objectLevel++;
}

void JSONBuilder::EndObject()
{
    m_json += "}";
    m_objectLevel--;
    if (m_objectLevel > 0)
    {
        m_firstItem = false;
    }
}

void JSONBuilder::AddString(string key, string value)
{
    AddCommaIfNeeded();
    m_json += "\"" + key + "\":\"" + EscapeString(value) + "\"";
    m_firstItem = false;
}

void JSONBuilder::AddNumber(string key, double value)
{
    AddCommaIfNeeded();
    m_json += "\"" + key + "\":" + DoubleToString(value, 8);
    m_firstItem = false;
}

void JSONBuilder::AddBoolean(string key, bool value)
{
    AddCommaIfNeeded();
    m_json += "\"" + key + "\":" + (value ? "true" : "false");
    m_firstItem = false;
}

void JSONBuilder::AddNull(string key)
{
    AddCommaIfNeeded();
    m_json += "\"" + key + "\":null";
    m_firstItem = false;
}

void JSONBuilder::AddCommaIfNeeded()
{
    if (!m_firstItem)
    {
        m_json += ",";
    }
}

string JSONBuilder::EscapeString(string str)
{
    string result = str;
    StringReplace(result, "\\", "\\\\");
    StringReplace(result, "\"", "\\\"");
    StringReplace(result, "\n", "\\n");
    StringReplace(result, "\t", "\\t");
    StringReplace(result, "\r", "\\r");
    return result;
}

string JSONBuilder::ToString()
{
    return m_json;
}

void JSONBuilder::Reset()
{
    m_json = "";
    m_firstItem = true;
    m_objectLevel = 0;
}