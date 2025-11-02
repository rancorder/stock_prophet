# auto_stock_system.py
import yfinance as yf
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import requests
from xgboost import XGBRegressor
import joblib
import logging

# ログ設定
logging.basicConfig(
    filename='/var/log/stock_prophet.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class AutoStockSystem:
    def __init__(self):
        self.db_path = '/home/stock_prophet/data/stock_data.db'
        self.model_path = '/home/stock_prophet/models/best_model.pkl'
        self.model = joblib.load(self.model_path)
        
    def collect_data(self, tickers):
        """株価データ収集"""
        logging.info("データ収集開始")
        
        for ticker in tickers:
            try:
                # 最新3ヶ月分
                df = yf.download(ticker, period='3mo')
                
                if len(df) > 0:
                    # DB保存
                    conn = sqlite3.connect(self.db_path)
                    df.to_sql(
                        ticker.replace('.', '_'), 
                        conn, 
                        if_exists='replace'
                    )
                    conn.close()
                    
                    logging.info(f"{ticker}: {len(df)}件取得完了")
                else:
                    logging.warning(f"{ticker}: データ取得失敗")
                    
            except Exception as e:
                logging.error(f"{ticker}: エラー - {e}")
    
    def create_features(self, df):
        """特徴量作成"""
        # 移動平均
        df['SMA_5'] = df['Close'].rolling(5).mean()
        df['SMA_20'] = df['Close'].rolling(20).mean()
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        
        # ボリンジャーバンド
        df['BB_middle'] = df['Close'].rolling(20).mean()
        std = df['Close'].rolling(20).std()
        df['BB_upper'] = df['BB_middle'] + (std * 2)
        df['BB_lower'] = df['BB_middle'] - (std * 2)
        
        return df.dropna()
    
    def predict(self, ticker):
        """予測実行"""
        try:
            # DB読み込み
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql(
                f"SELECT * FROM '{ticker.replace('.', '_')}'", 
                conn,
                index_col='Date',
                parse_dates=['Date']
            )
            conn.close()
            
            # 特徴量作成
            df = self.create_features(df)
            
            # 予測
            feature_cols = ['SMA_5', 'SMA_20', 'RSI', 'MACD', 
                          'BB_middle', 'BB_upper', 'BB_lower']
            X_latest = df[feature_cols].iloc[-1:].values
            predicted_price = self.model.predict(X_latest)[0]
            
            current_price = df['Close'].iloc[-1]
            change_percent = ((predicted_price - current_price) / current_price) * 100
            
            result = {
                'ticker': ticker,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'current_price': float(current_price),
                'predicted_price': float(predicted_price),
                'change_percent': float(change_percent)
            }
            
            logging.info(f"{ticker}予測完了: {change_percent:.2f}%")
            return result
            
        except Exception as e:
            logging.error(f"{ticker}予測エラー: {e}")
            return None
    
    def send_notification(self, predictions):
        """Slack通知"""
        # あなたの43サイト実績でChatWork使ってたので、それも対応
        
        # Slack Webhook URL
        webhook_url = "YOUR_SLACK_WEBHOOK_URL"
        
        message = "📈 *本日の株価予測*\n\n"
        
        for pred in predictions:
            if pred:
                emoji = "🔴" if pred['change_percent'] < 0 else "🟢"
                message += f"{emoji} *{pred['ticker']}*\n"
                message += f"現在: ¥{pred['current_price']:,.0f}\n"
                message += f"予測: ¥{pred['predicted_price']:,.0f}\n"
                message += f"変化: {pred['change_percent']:+.2f}%\n\n"
        
        requests.post(webhook_url, json={"text": message})
        logging.info("通知送信完了")
    
    def run(self):
        """メイン処理"""
        logging.info("=== 自動株価予測システム起動 ===")
        
        tickers = [
            '7203.T',  # トヨタ
            '6758.T',  # ソニー
            '9984.T',  # ソフトバンク
            'AAPL',    # Apple
            'TSLA',    # Tesla
        ]
        
        # データ収集
        self.collect_data(tickers)
        
        # 予測
        predictions = []
        for ticker in tickers:
            result = self.predict(ticker)
            if result:
                predictions.append(result)
        
        # 通知
        if predictions:
            self.send_notification(predictions)
        
        logging.info("=== 処理完了 ===")

if __name__ == "__main__":
    system = AutoStockSystem()
    system.run()
