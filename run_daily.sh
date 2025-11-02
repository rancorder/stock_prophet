#!/bin/bash
##############################################
# Stock Prophet 自動実行スクリプト
# 毎日自動でデータ収集 → 予測実行
##############################################

echo "=========================================="
echo "📈 Stock Prophet 自動実行"
echo "実行時刻: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

cd /root/stock_prophet

# ログファイル設定
LOG_FILE="./logs/daily_$(date '+%Y%m%d').log"

echo "" | tee -a $LOG_FILE
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a $LOG_FILE
echo "Phase 1: データ収集" | tee -a $LOG_FILE
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a $LOG_FILE
python3 scraper_fixed.py 2>&1 | tee -a $LOG_FILE

echo "" | tee -a $LOG_FILE
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a $LOG_FILE
echo "Phase 2: 予測実行" | tee -a $LOG_FILE
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a $LOG_FILE
python3 predict_system.py 2>&1 | tee -a $LOG_FILE

echo "" | tee -a $LOG_FILE
echo "=========================================="
echo "✅ 処理完了"
echo "ログ: $LOG_FILE"
echo "=========================================="
