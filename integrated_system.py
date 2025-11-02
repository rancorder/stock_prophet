# integrated_system.py
from playwright_scraper_optimized import OptimizedStockScraper
from feature_engineering import FeatureEngineer
import joblib
import pandas as pd
import sqlite3
import logging
from datetime import datetime
import requests
import psutil

logging.basicConfig(
    filename='/home/stock_prophet/logs/system.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class IntegratedSystem:
    def __init__(self):
        self.scraper = OptimizedStockScraper()
        self.feature_engineer = FeatureEngineer()
        self.db_path = '/home/stock_prophet/data/stock_data.db'
        
        # リソースチェック
        self.check_system_resources()
    
    def check_system_resources(self):
        """起動前のリソース確認"""
        memory = psutil.virtual_memory()
        available_gb = memory.available / (1024**3)
        
        logging.info(f"💾 利用可能メモリ: {available_gb:.2f}GB")
        
        if available_gb < 0.5:  # 500MB未満
            logging.warning("⚠️  メモリ不足！処理を中止")
            raise Exception("メモリ不足")
        
        logging.info("✅ リソース確認OK")
    
    def run_prediction_system(self):
        """株価予測システム実行"""
        logging.info("=" * 60)
        logging.info("🚀 Stock Prophet 統合システム起動")
        logging.info(f"実行時刻: {datetime.now()}")
        logging.info("=" * 60)
        
        try:
            # ティッカーリスト
            tickers = [
                '7203.T', '6758.T', '9984.T', '6501.T', '8306.T',  # 日本株
                'AAPL', 'TSLA', 'NVDA', 'GOOGL', 'MSFT'  # 米国株
            ]
            
            # 1. データ収集（playwright）
            logging.info("\n📊 Phase 1: データ収集")
            results = self.scraper.run(tickers)
            
            if len(results) == 0:
                logging.error("❌ データ収集失敗")
                return
            
            # 2. 予測
            logging.info("\n🤖 Phase 2: 予測実行")
            predictions = []
            
            model = joblib.load('/home/stock_prophet/models/best_model.pkl')
            
            for ticker, df in results.items():
                try:
                    # 特徴量作成
                    df_features = self.feature_engineer.create_technical_indicators(df)
                    
                    if len(df_features) < 20:
                        logging.warning(f"⚠️  {ticker}: データ不足")
                        continue
                    
                    # 予測
                    feature_cols = self.feature_engineer.get_feature_columns()
                    X_latest = df_features[feature_cols].iloc[-1:].values
                    
                    predicted_price = model.predict(X_latest)[0]
                    current_price = df_features['Close'].iloc[-1]
                    change_percent = ((predicted_price - current_price) / current_price) * 100
                    
                    predictions.append({
                        'ticker': ticker,
                        'current_price': float(current_price),
                        'predicted_price': float(predicted_price),
                        'change_percent': float(change_percent)
                    })
                    
                    logging.info(f"✅ {ticker}: {change_percent:+.2f}%")
                    
                except Exception as e:
                    logging.error(f"❌ {ticker}予測エラー: {e}")
            
            # 3. 通知
            if len(predictions) > 0:
                logging.info("\n📢 Phase 3: 通知送信")
                self.send_slack_notification(predictions)
            
            # 4. リソース使用状況ログ
            memory = psutil.virtual_memory()
            logging.info(f"\n💾 処理後メモリ使用率: {memory.percent:.1f}%")
            
            logging.info("\n✅ 処理完了")
            logging.info("=" * 60)
            
        except Exception as e:
            logging.error(f"❌ システムエラー: {e}")
            raise
    
    def send_slack_notification(self, predictions):
        """Slack通知"""
        webhook_url = "YOUR_SLACK_WEBHOOK_URL"
        
        # 上昇率順にソート
        sorted_preds = sorted(predictions, key=lambda x: x['change_percent'], reverse=True)
        
        message = f"📈 *Stock Prophet 予測レポート*\n"
        message += f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        message += f"📊 対象銘柄: {len(predictions)}銘柄\n\n"
        
        message += "*🟢 上昇予想 TOP3*\n"
        for pred in sorted_preds[:3]:
            message += f"• *{pred['ticker']}*: {pred['change_percent']:+.2f}% "
            message += f"(¥{pred['current_price']:,.0f} → ¥{pred['predicted_price']:,.0f})\n"
        
        message += "\n*🔴 下落予想 TOP3*\n"
        for pred in sorted_preds[-3:]:
            message += f"• *{pred['ticker']}*: {pred['change_percent']:+.2f}% "
            message += f"(¥{pred['current_price']:,.0f} → ¥{pred['predicted_price']:,.0f})\n"
        
        try:
            response = requests.post(webhook_url, json={"text": message}, timeout=10)
            if response.status_code == 200:
                logging.info("✅ Slack通知送信完了")
            else:
                logging.warning(f"⚠️  Slack通知失敗: {response.status_code}")
        except Exception as e:
            logging.error(f"❌ Slack通知エラー: {e}")

if __name__ == "__main__":
    system = IntegratedSystem()
    system.run_prediction_system()
