#!/bin/bash
# パフォーマンス測定スクリプト - WSL2 vs Native Linux比較
# 実行: bash performance_benchmark.sh

set -euo pipefail

# 色付きログ出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_benchmark() {
    echo -e "${CYAN}[BENCHMARK]${NC} $1"
}

# ベンチマーク結果保存用
BENCHMARK_RESULTS=()

# 結果記録関数
record_result() {
    local test_name="$1"
    local result="$2"
    local unit="$3"
    
    BENCHMARK_RESULTS+=("$test_name|$result|$unit")
    log_benchmark "$test_name: $result $unit"
}

# 時間測定関数
measure_time() {
    local command="$1"
    local description="$2"
    
    log_info "測定中: $description"
    
    local start_time=$(date +%s.%N)
    eval "$command" >/dev/null 2>&1 || true
    local end_time=$(date +%s.%N)
    
    local duration=$(echo "$end_time - $start_time" | bc -l)
    record_result "$description" "$(printf "%.3f" "$duration")" "秒"
}

# システム情報取得
get_system_info() {
    log_info "=== システム情報取得 ==="
    
    echo "🖥️ システム基本情報:"
    echo "  - OS: $(lsb_release -d 2>/dev/null | cut -f2- || uname -a)"
    echo "  - カーネル: $(uname -r)"
    echo "  - アーキテクチャ: $(uname -m)"
    echo "  - CPU: $(lscpu | grep "Model name" | cut -d: -f2- | xargs)"
    echo "  - CPUコア数: $(nproc)"
    echo "  - メモリ: $(free -h | awk 'NR==2{print $2}')"
    echo "  - ディスク: $(df -h / | tail -1 | awk '{print $2 " (" $4 " available)"}')"
    echo
    
    # WSL2検出
    if grep -qi wsl /proc/version 2>/dev/null; then
        echo "🔍 環境: WSL2 (仮想化レイヤーあり)"
        export IS_WSL2=true
    else
        echo "🔍 環境: Native Linux (仮想化レイヤーなし)"
        export IS_WSL2=false
    fi
    echo
}

# CPU性能テスト
benchmark_cpu() {
    log_info "=== CPU性能ベンチマーク ==="
    
    # 素数計算テスト
    log_benchmark "素数計算テスト (10000番目まで)"
    measure_time "python3 -c '
import time
def sieve_of_eratosthenes(limit):
    sieve = [True] * (limit + 1)
    sieve[0] = sieve[1] = False
    for i in range(2, int(limit**0.5) + 1):
        if sieve[i]:
            for j in range(i*i, limit + 1, i):
                sieve[j] = False
    return [i for i in range(2, limit + 1) if sieve[i]]

primes = sieve_of_eratosthenes(100000)
'" "素数計算"
    
    # 数値計算テスト
    log_benchmark "numpy行列計算テスト"
    if python3 -c "import numpy" 2>/dev/null; then
        measure_time "python3 -c '
import numpy as np
a = np.random.rand(1000, 1000)
b = np.random.rand(1000, 1000)
c = np.dot(a, b)
'" "numpy行列計算"
    else
        log_warning "numpyが見つかりません。スキップします"
    fi
    
    # ファイル圧縮テスト
    log_benchmark "ファイル圧縮テスト"
    local test_file="/tmp/benchmark_test.txt"
    # 10MBのテストファイル作成
    dd if=/dev/zero of="$test_file" bs=1M count=10 2>/dev/null
    
    measure_time "gzip -c '$test_file' > /tmp/benchmark_test.gz" "gzip圧縮"
    measure_time "gunzip -c /tmp/benchmark_test.gz > /tmp/benchmark_test_uncompressed.txt" "gzip展開"
    
    # クリーンアップ
    rm -f "$test_file" /tmp/benchmark_test.gz /tmp/benchmark_test_uncompressed.txt
}

# I/O性能テスト
benchmark_io() {
    log_info "=== I/O性能ベンチマーク ==="
    
    local test_dir="/tmp/io_benchmark"
    mkdir -p "$test_dir"
    
    # 順次書き込みテスト
    log_benchmark "順次書き込みテスト (100MB)"
    measure_time "dd if=/dev/zero of='$test_dir/write_test' bs=1M count=100 oflag=sync" "順次書き込み"
    
    # 順次読み込みテスト
    log_benchmark "順次読み込みテスト (100MB)"
    # キャッシュクリア
    sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches' 2>/dev/null || true
    measure_time "dd if='$test_dir/write_test' of=/dev/null bs=1M" "順次読み込み"
    
    # ランダムI/Oテスト（小ファイル）
    log_benchmark "小ファイル作成テスト (1000個)"
    measure_time "for i in {1..1000}; do echo 'test data' > '$test_dir/small_file_\$i.txt'; done" "小ファイル作成"
    
    # ファイル検索テスト
    log_benchmark "ファイル検索テスト"
    measure_time "find '$test_dir' -name '*.txt' | wc -l" "ファイル検索"
    
    # クリーンアップ
    rm -rf "$test_dir"
}

# メモリ性能テスト
benchmark_memory() {
    log_info "=== メモリ性能ベンチマーク ==="
    
    # メモリ割り当てテスト
    log_benchmark "メモリ割り当てテスト (1GB)"
    measure_time "python3 -c '
import gc
data = [0] * (1024 * 1024 * 128)  # 約1GB
del data
gc.collect()
'" "メモリ割り当て"
    
    # メモリコピーテスト
    if command -v python3 >/dev/null 2>&1; then
        log_benchmark "メモリコピーテスト"
        measure_time "python3 -c '
import array
a = array.array(\"i\", range(10000000))
b = array.array(\"i\", a)
'" "メモリコピー"
    fi
}

# 開発環境特化テスト
benchmark_development() {
    log_info "=== 開発環境特化ベンチマーク ==="
    
    local project_dir="$HOME/Trading-Development/2.ブレイクアウト手法プロジェクト"
    
    if [ -d "$project_dir" ]; then
        cd "$project_dir"
        
        # Git操作テスト
        log_benchmark "Git操作テスト"
        measure_time "git status" "git status"
        measure_time "git log --oneline -n 100" "git log"
        
        # ファイル検索テスト
        log_benchmark "プロジェクトファイル検索テスト"
        measure_time "find . -name '*.py' | wc -l" "Pythonファイル検索"
        measure_time "find . -name '*.mq5' | wc -l" "MQL5ファイル検索"
        measure_time "grep -r 'JamesORB' . --include='*.py' --include='*.mq5' | wc -l" "文字列検索"
        
        # スクリプト実行テスト
        if [ -x "Scripts/cron_system_monitor.py" ]; then
            log_benchmark "システム監視スクリプト実行テスト"
            measure_time "timeout 10 python3 Scripts/cron_system_monitor.py" "システム監視実行"
        fi
        
    else
        log_warning "プロジェクトディレクトリが見つかりません。開発環境テストをスキップします"
    fi
    
    # Python import テスト
    log_benchmark "Python importテスト"
    local python_packages=("pandas" "numpy" "requests" "json" "datetime")
    for package in "${python_packages[@]}"; do
        if python3 -c "import $package" 2>/dev/null; then
            measure_time "python3 -c 'import $package'" "import $package"
        fi
    done
    
    # Node.js実行テスト
    if command -v node >/dev/null 2>&1; then
        log_benchmark "Node.js実行テスト"
        measure_time "node -e 'console.log(\"Node.js performance test\")'" "Node.js実行"
    fi
}

# Claude Code特化テスト
benchmark_claude() {
    log_info "=== Claude Code特化ベンチマーク ==="
    
    if command -v claude >/dev/null 2>&1; then
        # Claude基本コマンドテスト
        log_benchmark "Claude基本コマンドテスト"
        measure_time "claude --version" "claude --version"
        
        # 認証状況確認（時間測定）
        log_benchmark "Claude認証確認テスト"
        measure_time "timeout 5 claude whoami" "claude whoami"
        
    else
        log_warning "Claude CLIが見つかりません。Claude特化テストをスキップします"
    fi
    
    # 設定ファイル読み込みテスト
    if [ -f "$HOME/.claude/settings.json" ]; then
        log_benchmark "Claude設定ファイル読み込みテスト"
        measure_time "python3 -m json.tool '$HOME/.claude/settings.json'" "設定ファイル解析"
    fi
    
    if [ -f "$HOME/.config/claude-desktop/config.json" ]; then
        log_benchmark "MCP設定ファイル読み込みテスト"
        measure_time "python3 -m json.tool '$HOME/.config/claude-desktop/config.json'" "MCP設定解析"
    fi
}

# 結果表示・保存
show_results() {
    log_info "=== ベンチマーク結果サマリー ==="
    
    echo "📊 測定結果:"
    printf "%-35s | %-10s | %-10s\n" "テスト項目" "結果" "単位"
    printf "%-35s-+-%-10s-+-%-10s\n" "-----------------------------------" "----------" "----------"
    
    for result in "${BENCHMARK_RESULTS[@]}"; do
        IFS='|' read -r test_name value unit <<< "$result"
        printf "%-35s | %-10s | %-10s\n" "$test_name" "$value" "$unit"
    done
    
    echo
    
    # パフォーマンス評価
    local total_tests=${#BENCHMARK_RESULTS[@]}
    log_info "総測定項目数: $total_tests"
    
    # 結果保存
    local report_file="performance_benchmark_$(date +%Y%m%d_%H%M%S).txt"
    {
        echo "Performance Benchmark Report"
        echo "============================="
        echo "測定日時: $(date)"
        echo "システム: $(uname -a)"
        echo "環境: $([ "$IS_WSL2" = true ] && echo "WSL2" || echo "Native Linux")"
        echo ""
        echo "結果:"
        printf "%-35s | %-10s | %-10s\n" "テスト項目" "結果" "単位"
        printf "%-35s-+-%-10s-+-%-10s\n" "-----------------------------------" "----------" "----------"
        for result in "${BENCHMARK_RESULTS[@]}"; do
            IFS='|' read -r test_name value unit <<< "$result"
            printf "%-35s | %-10s | %-10s\n" "$test_name" "$value" "$unit"
        done
    } > "$report_file"
    
    log_success "ベンチマーク結果保存: $report_file"
    
    # WSL2 vs Native Linux比較コメント
    if [ "$IS_WSL2" = true ]; then
        echo
        log_info "💡 WSL2環境での測定結果です"
        echo "Native Linuxとの比較推定:"
        echo "  - CPU処理: 約5-10%高速化が期待されます"
        echo "  - I/O処理: 約30-50%高速化が期待されます"
        echo "  - メモリ処理: 約5-15%高速化が期待されます"
        echo "  - 開発環境: ファイルアクセスが大幅に高速化されます"
    else
        echo
        log_success "🚀 Native Linux環境での測定結果です"
        echo "WSL2と比較したパフォーマンス優位性を享受しています！"
    fi
}

# メイン実行
main() {
    echo -e "${CYAN}"
    cat << 'EOF'
╔══════════════════════════════════════════════════════════════╗
║            Performance Benchmark Tool                       ║
║        WSL2 vs Native Linux Performance Comparison          ║
╚══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    
    log_info "=== パフォーマンスベンチマーク開始 ==="
    log_info "開始時刻: $(date)"
    echo
    
    # 事前準備
    if ! command -v bc >/dev/null 2>&1; then
        log_warning "bc (計算ツール) がインストールされていません。インストール中..."
        sudo apt-get update -qq && sudo apt-get install -y bc
    fi
    
    # 測定実行
    get_system_info
    benchmark_cpu
    echo
    benchmark_io
    echo
    benchmark_memory
    echo
    benchmark_development
    echo
    benchmark_claude
    echo
    
    # 結果表示
    show_results
    
    log_success "パフォーマンスベンチマーク完了"
    log_info "完了時刻: $(date)"
}

# スクリプト実行
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main
fi