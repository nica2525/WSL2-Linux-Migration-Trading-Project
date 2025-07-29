#!/bin/bash
# Dashboard Health Check Script
# 作成日: 2025-07-29
# 用途: Phase 1 ダッシュボードの死活監視

DASHBOARD_URL="http://localhost:5000"
PID_FILE="dashboard.pid"
DATA_FILE="/tmp/mt5_data/positions.json"

echo "=== Dashboard Health Check ==="
echo "Time: $(date)"
echo ""

# 1. プロセス確認
echo "🔍 Process Status:"
if [ -f $PID_FILE ] && ps -p $(cat $PID_FILE) > /dev/null 2>&1; then
    PID=$(cat $PID_FILE)
    MEMORY=$(ps -p $PID -o rss= | tr -d ' ')
    CPU=$(ps -p $PID -o pcpu= | tr -d ' ')
    UPTIME=$(ps -p $PID -o etime= | tr -d ' ')
    
    echo "  ✅ Running (PID: $PID)"
    echo "  📊 Memory: ${MEMORY}KB, CPU: ${CPU}%, Uptime: $UPTIME"
else
    echo "  ❌ Not running"
    HEALTH_STATUS=1
fi

echo ""

# 2. HTTP確認
echo "🌐 HTTP Accessibility:"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $DASHBOARD_URL 2>/dev/null)
RESPONSE_TIME=$(curl -s -o /dev/null -w "%{time_total}" $DASHBOARD_URL 2>/dev/null)

if [ "$HTTP_CODE" = "200" ]; then
    echo "  ✅ Accessible (HTTP $HTTP_CODE, ${RESPONSE_TIME}s)"
else
    echo "  ❌ Not accessible (HTTP ${HTTP_CODE:-000})"
    HEALTH_STATUS=1
fi

echo ""

# 3. WebSocket確認
echo "🔌 WebSocket Status:"
WS_TEST=$(curl -s -I -H "Connection: Upgrade" -H "Upgrade: websocket" $DASHBOARD_URL/socket.io/ 2>/dev/null | head -1)
if echo "$WS_TEST" | grep -q "101\|200"; then
    echo "  ✅ WebSocket endpoint responding"
else
    echo "  ⚠️  WebSocket endpoint may have issues"
fi

echo ""

# 4. データファイル確認
echo "📁 Data File Status:"
if [ -f "$DATA_FILE" ]; then
    AGE=$(expr $(date +%s) - $(stat -c %Y "$DATA_FILE" 2>/dev/null || echo 0))
    SIZE=$(stat -c %s "$DATA_FILE" 2>/dev/null || echo 0)
    
    if [ $AGE -lt 300 ]; then  # 5分以内の更新
        echo "  ✅ Fresh (${AGE}s ago, ${SIZE} bytes)"
    else
        echo "  ⚠️  Stale (${AGE}s ago, ${SIZE} bytes)"
    fi
    
    # JSON妥当性確認
    if python3 -c "import json; json.load(open('$DATA_FILE'))" 2>/dev/null; then
        echo "  ✅ Valid JSON format"
    else
        echo "  ❌ Invalid JSON format"
        HEALTH_STATUS=1
    fi
else
    echo "  ❌ Missing data file"
    HEALTH_STATUS=1
fi

echo ""

# 5. システムリソース確認
echo "💻 System Resources:"
DISK_USAGE=$(df -h /tmp 2>/dev/null | tail -1 | awk '{print $5}' | sed 's/%//')
MEMORY_USAGE=$(free | grep '^Mem:' | awk '{printf("%.1f", $3/$2 * 100.0)}')
LOAD_AVG=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')

echo "  📊 Disk Usage: ${DISK_USAGE}%"
echo "  📊 Memory Usage: ${MEMORY_USAGE}%"
echo "  📊 Load Average: ${LOAD_AVG}"

if [ "$DISK_USAGE" -gt 90 ]; then
    echo "  ⚠️  High disk usage"
fi

if [ "$(echo "$MEMORY_USAGE > 80" | bc -l 2>/dev/null || echo 0)" = "1" ]; then
    echo "  ⚠️  High memory usage"
fi

echo ""

# 6. ログ確認
echo "📋 Log Status:"
if [ -f "dashboard.log" ]; then
    LOG_SIZE=$(stat -c %s dashboard.log)
    ERROR_COUNT=$(grep -c -i error dashboard.log 2>/dev/null || echo 0)
    WARNING_COUNT=$(grep -c -i warning dashboard.log 2>/dev/null || echo 0)
    
    echo "  📊 Log Size: ${LOG_SIZE} bytes"
    echo "  📊 Errors: $ERROR_COUNT, Warnings: $WARNING_COUNT"
    
    if [ $ERROR_COUNT -gt 0 ]; then
        echo "  ⚠️  Recent errors found in log"
        echo "  📝 Latest error:"
        grep -i error dashboard.log | tail -1 | sed 's/^/    /'
    fi
else
    echo "  📊 No log file (stdout/stderr mode)"
fi

echo ""

# 7. 48時間テスト状況確認（該当する場合）
echo "🧪 Long-term Test Status:"
if [ -f "continuous_test.log" ]; then
    if ps aux | grep -q "test_continuous_operation" | grep -v grep; then
        echo "  🏃 48-hour test running"
        LAST_LOG=$(tail -1 continuous_test.log 2>/dev/null)
        echo "  📝 Last log: $LAST_LOG"
    else
        echo "  💤 No long-term test running"
    fi
else
    echo "  💤 No test log available"
fi

echo ""

# 最終判定
if [ "${HEALTH_STATUS:-0}" = "0" ]; then
    echo "🎉 Overall Health Check: ✅ PASSED"
    exit 0
else
    echo "❌ Overall Health Check: ❌ FAILED"
    echo ""
    echo "🔧 Suggested Actions:"
    echo "  1. Check process status: ps aux | grep 'python3 app.py'"
    echo "  2. Check logs: tail -f dashboard.log"
    echo "  3. Restart if needed: pkill -f 'python3 app.py' && python3 app.py &"
    exit 1
fi