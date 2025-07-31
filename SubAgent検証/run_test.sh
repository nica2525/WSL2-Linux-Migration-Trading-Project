#!/bin/bash
# Sub-Agent境界線検証実行スクリプト

# 色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# ログファイル
LOG_DIR="test_results"
mkdir -p $LOG_DIR
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/test_run_$TIMESTAMP.log"

echo -e "${GREEN}=== Sub-Agent境界線検証開始 ===${NC}"
echo "ログファイル: $LOG_FILE"

# テストケース実行関数
run_test() {
    local test_id=$1
    local test_name=$2
    local prompt=$3

    echo -e "\n${YELLOW}[$test_id] $test_name${NC}"
    echo "プロンプト: $prompt"
    echo -n "実行しますか？ (y/n/s[skip]): "
    read response

    if [[ $response == "s" ]]; then
        echo "スキップしました" | tee -a $LOG_FILE
        return
    fi

    if [[ $response != "y" ]]; then
        echo "キャンセルしました" | tee -a $LOG_FILE
        return
    fi

    # 実行前のリソース記録
    echo "実行前CPU/メモリ:" | tee -a $LOG_FILE
    top -b -n 1 | head -5 | tee -a $LOG_FILE

    # タイマー開始
    START_TIME=$(date +%s)

    echo -e "${GREEN}実行中...${NC}"
    echo "※ 30秒以上応答がない場合はCtrl+Cで中断してください"

    # ここで実際のSub-Agent呼び出しをシミュレート
    # 実際の実行時は以下のコメントを外す
    # claude code --agent "$prompt"

    # 現在はプロンプト表示のみ
    echo "テストプロンプト: $prompt" | tee -a $LOG_FILE

    # タイマー終了
    END_TIME=$(date +%s)
    ELAPSED=$((END_TIME - START_TIME))

    echo -e "${GREEN}完了 (実行時間: ${ELAPSED}秒)${NC}" | tee -a $LOG_FILE

    # 実行後のリソース記録
    echo "実行後CPU/メモリ:" | tee -a $LOG_FILE
    top -b -n 1 | head -5 | tee -a $LOG_FILE

    # 結果記録
    echo "---" >> $LOG_FILE
    echo "test_id: $test_id" >> $LOG_FILE
    echo "timestamp: $(date)" >> $LOG_FILE
    echo "execution_time: $ELAPSED" >> $LOG_FILE
    echo "status: completed" >> $LOG_FILE
    echo "" >> $LOG_FILE
}

# フェーズ1テスト
echo -e "\n${GREEN}=== フェーズ1: 基礎境界確認 ===${NC}"

run_test "T001" "極小単一ファイル読取" \
    "test_files/minimal/tiny.pyファイルの内容を確認して、変数の数を教えてください"

run_test "T002" "小規模単一ファイル分析" \
    "test_files/small/small_simple.pyのコード構造を分析し、変数の命名パターンを説明してください"

run_test "T003" "中規模複雑ファイル分析" \
    "test_files/medium/medium_complex.pyのクラス構造とメソッドの概要を説明してください"

echo -e "\n${RED}警告: 次のテストはフリーズリスクが高いです${NC}"
run_test "T004" "大規模ファイル読取" \
    "test_files/large/large_simple.pyの行数と変数の総数を確認してください"

# 結果サマリー
echo -e "\n${GREEN}=== テスト結果サマリー ===${NC}"
echo "詳細ログ: $LOG_FILE"
tail -20 $LOG_FILE

echo -e "\n${YELLOW}プロセス確認:${NC}"
ps aux | grep -E "claude|node" | grep -v grep

echo -e "\n${GREEN}検証完了${NC}"
