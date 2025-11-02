# main_system.py
import yfinance as yf
from hybrid_collector import HybridCollector
from feature_engineering import FeatureEngineer
from model_training import StockPredictor
import sqlite3
import pandas as pd
import logging
import requests
from datetime import datetime

logging.basicConfig(
    filename='/var/log/stock_prophet.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class StockProphetSystem:
    def __init__(self):
        self.collector = HybridCollector()
        self.feature_engineer = FeatureEngineer()
        self.predictor = StockPredictor()
        self.db_path = '/home/stock_prophet/data/stock_data.db'
        
    def run_daily_prediction(self):
        """毎日の予測実行"""
        logging.info("=" * 50)
        logging.info("🚀 Stock Prophet 起動")
        logging.info(f"実行時刻: {datetime.now()}")
        logging.info("=" * 50)
        
        tickers = [
            '7203.T',   # トヨタ
            '6758.T',   # ソニー
            '9984.T',   # ソフトバンク
            '6501.T',   # 日立
            'AAPL',     # Apple
            'TSLA',     # Tesla
            'NVDA',     # NVIDIA
            'GOOGL',    # Google
        ]
        
        # 1. データ収集
        logging.info("\n📊 Phase 1: データ収集")
        results = self.collector.collect_all(tickers)
        
        # 2. 特徴量作成 & 予測
        logging.info("\n🤖 Phase 2: 予測実行")
        predictions = []
        
        for ticker, result in results.items():
            try:
                df = result['data']
                
                # 特徴量作成
                df = self.feature_engineer.create_technical_indicators(df)
                
                # 予測
                pred = self.predictor.predict_next_day(df, ticker)
                predictions.append(pred)
                
            except Exception as e:
                logging.error(f"❌ {ticker}予測エラー: {e}")
        
        # 3. 通知
        logging.info("\n📢 Phase 3: 通知送信")
        self.send_notifications(predictions)
        
        # 4. 予測履歴保存
        self.save_predictions(predictions)
        
        logging.info("\n✅ 処理完了")
        logging.info("=" * 50)
    
    def send_notifications(self, predictions):
        """Slack通知"""
        webhook_url = "YOUR_SLACK_WEBHOOK_URL"
        
        message = f"📈 *Stock Prophet 予測レポート*\n"
        message += f"日時: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        
        # 上昇予想トップ3
        sorted_preds = sorted(predictions, key=lambda x: x['change_percent'], reverse=True)
        
        message += "*🟢 上昇予想 TOP3*\n"
        for pred in sorted_preds[:3]:
            message += f"• {pred['ticker']}: +{pred['change_percent']:.2f}%\n"
        
        message += "\n*🔴 下落予想 TOP3*\n"
        for pred in sorted_preds[-3:]:
            message += f"• {pred['ticker']}: {pred['change_percent']:.2f}%\n"
        
        try:
            requests.post(webhook_url, json={"text": message})
            logging.info("✅ Slack通知送信完了")
        except Exception as e:
            logging.error(f"❌ Slack通知失敗: {e}")
    
    def save_predictions(self, predictions):
        """予測履歴をDBに保存"""
        conn = sqlite3.connect(self.db_path)
        df = pd.DataFrame(predictions)
        df['timestamp'] = datetime.now()
        df.to_sql('predictions_history', conn, if_exists='append', index=False)
        conn.close()
        logging.info("💾 予測履歴保存完了")

if __name__ == "__main__":
    system = StockProphetSystem()
    system.run_daily_prediction()
