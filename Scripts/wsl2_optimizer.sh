#!/bin/bash
# WSL2最適化スクリプト
# Gemini査読結果に基づくWSL2パフォーマンス・安定性向上

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="$PROJECT_DIR/.wsl2_optimizer.log"

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_message "=== WSL2 Optimizer Started ==="

# 1. 現在のWSL2設定確認
log_message "📋 Checking current WSL2 configuration..."

WSL_CONFIG="/mnt/c/Users/$USER/.wslconfig"
WSL_CONFIG_ALT="$HOME/.wslconfig"

# Windows側のユーザー名を推定
WINDOWS_USER=$(cmd.exe /c "echo %USERNAME%" 2>/dev/null | tr -d '\r\n' || echo "Unknown")
WSL_CONFIG_WIN="/mnt/c/Users/$WINDOWS_USER/.wslconfig"

log_message "Windows User: $WINDOWS_USER"
log_message "Checking WSL config locations:"
log_message "  - $WSL_CONFIG_WIN"
log_message "  - $WSL_CONFIG"
log_message "  - $WSL_CONFIG_ALT"

# WSL設定ファイルの場所を特定
WSLCONFIG_PATH=""
if [[ -f "$WSL_CONFIG_WIN" ]]; then
    WSLCONFIG_PATH="$WSL_CONFIG_WIN"
elif [[ -f "$WSL_CONFIG" ]]; then
    WSLCONFIG_PATH="$WSL_CONFIG"
elif [[ -f "$WSL_CONFIG_ALT" ]]; then
    WSLCONFIG_PATH="$WSL_CONFIG_ALT"
fi

if [[ -n "$WSLCONFIG_PATH" ]]; then
    log_message "✅ Found WSL config: $WSLCONFIG_PATH"
    log_message "Current content:"
    cat "$WSLCONFIG_PATH" | while read -r line; do
        log_message "  $line"
    done
else
    log_message "⚠️ No WSL config found, will create optimal configuration"
fi

# 2. 最適なWSL2設定を生成
log_message "🔧 Generating optimal WSL2 configuration..."

# システム情報取得
TOTAL_MEMORY_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
TOTAL_MEMORY_GB=$((TOTAL_MEMORY_KB / 1024 / 1024))
CPU_CORES=$(nproc)

# WSL2用メモリ（全体の75%、最小4GB、最大12GB）
WSL_MEMORY_GB=$((TOTAL_MEMORY_GB * 3 / 4))
if [[ $WSL_MEMORY_GB -lt 4 ]]; then
    WSL_MEMORY_GB=4
elif [[ $WSL_MEMORY_GB -gt 12 ]]; then
    WSL_MEMORY_GB=12
fi

# WSL2用CPU（全体の75%、最小2、最大16）
WSL_PROCESSORS=$((CPU_CORES * 3 / 4))
if [[ $WSL_PROCESSORS -lt 2 ]]; then
    WSL_PROCESSORS=2
elif [[ $WSL_PROCESSORS -gt 16 ]]; then
    WSL_PROCESSORS=16
fi

log_message "System specs:"
log_message "  Total Memory: ${TOTAL_MEMORY_GB}GB"
log_message "  CPU Cores: $CPU_CORES"
log_message "Optimal WSL2 allocation:"
log_message "  Memory: ${WSL_MEMORY_GB}GB"
log_message "  Processors: $WSL_PROCESSORS"

# 3. 最適化された.wslconfig生成
OPTIMAL_WSLCONFIG=$(cat << EOF
# WSL2最適化設定 - Claude Sub-Agent安定性向上用
# Generated: $(date)

[wsl2]
# メモリ割り当て（システムの75%、Claude Sub-Agent安定動作用）
memory=${WSL_MEMORY_GB}GB

# CPU割り当て（システムの75%）
processors=$WSL_PROCESSORS

# スワップファイル（メモリの50%）
swap=$((WSL_MEMORY_GB / 2))GB

# ネットワーク設定（mirrored mode - MCP接続安定化）
networkingMode=mirrored

# DNS設定（接続安定化）
dnsTunneling=true

# ファイルシステム最適化
[experimental]
autoMemoryReclaim=gradual
sparseVhd=true

# ファイアウォール設定
firewall=true

# ホストからの接続許可
localhostForwarding=true

# 詳細ログ
debugConsole=false
EOF
)

# 4. 設定ファイル配置場所の決定
if [[ -d "/mnt/c/Users/$WINDOWS_USER" ]]; then
    TARGET_WSLCONFIG="/mnt/c/Users/$WINDOWS_USER/.wslconfig"
    log_message "✅ Will create/update: $TARGET_WSLCONFIG"
else
    TARGET_WSLCONFIG="$HOME/.wslconfig"
    log_message "⚠️ Windows user directory not accessible, using: $TARGET_WSLCONFIG"
fi

# 5. バックアップ作成
if [[ -f "$TARGET_WSLCONFIG" ]]; then
    BACKUP_FILE="${TARGET_WSLCONFIG}.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$TARGET_WSLCONFIG" "$BACKUP_FILE"
    log_message "✅ Backup created: $BACKUP_FILE"
fi

# 6. 新しい設定を書き込み
echo "$OPTIMAL_WSLCONFIG" > "$TARGET_WSLCONFIG"
log_message "✅ WSL2 configuration written to: $TARGET_WSLCONFIG"

# 7. /etc/wsl.conf の最適化
log_message "🔧 Optimizing /etc/wsl.conf..."

WSL_CONF_CONTENT=$(cat << 'EOF'
# WSL2最適化設定 - Sub-Agent安定動作用

[boot]
systemd=true

[network]
# DNS設定最適化（Claude Code接続安定化）
generateHosts = true
generateResolvConf = true

[interop]
# Windows実行ファイルへのアクセス最適化
enabled = true
appendWindowsPath = true

[user]
# デフォルトユーザー設定
default = trader

[filesystem]
# ファイルシステム最適化
umask = 022
EOF
)

echo "$WSL_CONF_CONTENT" | sudo tee /etc/wsl.conf > /dev/null
log_message "✅ /etc/wsl.conf optimized"

# 8. システム設定確認
log_message "📊 Current system status:"

# メモリ使用量
MEMORY_USAGE=$(free -h | awk 'NR==2{printf "Memory: %s/%s (%.1f%%)", $3,$2,$3*100/$2}')
log_message "  $MEMORY_USAGE"

# CPU負荷
LOAD_AVG=$(uptime | awk -F'load average:' '{print $2}' | xargs)
log_message "  Load Average: $LOAD_AVG"

# ディスク使用量
DISK_USAGE=$(df -h / | awk 'NR==2{printf "Disk: %s/%s (%s used)", $3,$2,$5}')
log_message "  $DISK_USAGE"

log_message "=== WSL2 optimization completed ==="

echo ""
echo "✅ WSL2 optimization completed successfully"
echo ""
echo "📁 Configuration files:"
echo "   .wslconfig: $TARGET_WSLCONFIG"
echo "   /etc/wsl.conf: Updated"
echo ""
echo "🔄 To apply changes:"
echo "   1. Exit all WSL sessions"
echo "   2. Run in Windows PowerShell (as Administrator):"
echo "      wsl --shutdown"
echo "   3. Wait 8 seconds, then restart WSL"
echo ""
echo "📝 Detailed log: $LOG_FILE"

# 9. WSL再起動が必要な旨を記録
log_message "⚠️ WSL restart required to apply configuration changes"
log_message "Run 'wsl --shutdown' in Windows PowerShell (as Administrator)"
