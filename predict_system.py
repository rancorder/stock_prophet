"""
株価予測実行スクリプト
訓練済みモデルを使用して株価予測を実行
"""
import sys
sys.path.append('.')

import pandas as pd
import numpy as np
import sqlite3
import joblib
import logging
from datetime import datetime
from config.stock_config import get_all_tickers, get_stock_name
from typing import Optional, List, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StockPredictionSystem:
    """株価予測システム"""
    
    def __init__(self):
        """初期化"""
        self.db_path = './data/stock_data.db'
        self.model_path = './models/stock_model.pkl'
        self.model = None
    
    def load_model(self) -> bool:
        """
        訓練済みモデルを読み込み
        
        Returns:
            成功時True、失敗時False
        """
        try:
            self.model = joblib.load(self.model_path)
            logger.info("✅ モデル読み込み完了")
            return True
        except Exception as e:
            logger.error(f"❌ モデル読み込み失敗: {e}")
            logger.error("💡 先にモデルを訓練してください: python3 train_model.py")
            return False
    
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        テクニカル指標を作成
        
        Args:
            df: 株価データのDataFrame
        
        Returns:
            特徴量追加後のDataFrame
        """
        df['SMA_5'] = df['Close'].rolling(5).mean()
        df['SMA_20'] = df['Close'].rolling(20).mean()
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        df['Return_1d'] = df['Close'].pct_change(1)
        df['Return_5d'] = df['Close'].pct_change(5)
        df['Volatility'] = df['Return_1d'].rolling(20).std()
        df['Volume_SMA'] = df['Volume'].rolling(20).mean()
        
        return df.dropna()
    
    def predict_single(self, ticker: str) -> Optional[Dict[str, float]]:
        """
        単一銘柄の予測を実行
        
        Args:
            ticker: ティッカーシンボル
        
        Returns:
            予測結果の辞書、失敗時はNone
            keys: 'ticker', 'name', 'current_price', 'predicted_price', 
                  'change', 'change_percent', 'date'
        """
        try:
            conn = sqlite3.connect(self.db_path)
            table_name = ticker.replace('.', '_').replace('-', '_')
            
            df = pd.read_sql(
                f"SELECT * FROM '{table_name}'",
                conn,
                parse_dates=['Date']
            )
            conn.close()
            
            if len(df) < 50:
                logger.warning(f"⚠️  {ticker}: データ不足")
                return None
            
            df = df.set_index('Date')
            df = self.create_features(df)
            
            if len(df) == 0:
                logger.warning(f"⚠️  {ticker}: 特徴量作成後データなし")
                return None
            
            feature_cols = [
                'Open', 'High', 'Low', 'Close', 'Volume',
                'SMA_5', 'SMA_20', 'RSI',
                'Return_1d', 'Return_5d', 'Volatility', 'Volume_SMA'
            ]
            
            X_latest = df[feature_cols].iloc[-1:].values
            current_price = df['Close'].iloc[-1]
            
            predicted_price = self.model.predict(X_latest)[0]
            change = predicted_price - current_price
            change_percent = (change / current_price) * 100
            
            return {
                'ticker': ticker,
                'name': get_stock_name(ticker),
                'current_price': float(current_price),
                'predicted_price': float(predicted_price),
                'change': float(change),
                'change_percent': float(change_percent),
                'date': df.index[-1].strftime('%Y-%m-%d')
            }
            
        except Exception as e:
            logger.error(f"❌ {ticker}予測エラー: {e}")
            return None
    
    def predict_all(self) -> List[Dict[str, float]]:
        """
        全銘柄の予測を実行
        
        Returns:
            予測結果のリスト
        """
        logger.info("=" * 60)
        logger.info("📈 Stock Prophet 予測システム")
        logger.info(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
        
        if not self.load_model():
            return []
        
        tickers = get_all_tickers()
        predictions = []
        
        logger.info(f"\n🎯 対象: {len(tickers)}銘柄\n")
        
        for ticker in tickers:
            pred = self.predict_single(ticker)
            if pred:
                predictions.append(pred)
                
                symbol = "🟢" if pred['change_percent'] > 0 else "🔴"
                logger.info(
                    f"{symbol} {pred['name']:30s} "
                    f"${pred['current_price']:9,.2f} → "
                    f"${pred['predicted_price']:9,.2f} "
                    f"({pred['change_percent']:+6.2f}%)"
                )
        
        logger.info("\n" + "=" * 60)
        logger.info("📊 予測サマリー")
        logger.info("=" * 60)
        
        if len(predictions) > 0:
            sorted_preds = sorted(predictions, key=lambda x: x['change_percent'], reverse=True)
            
            logger.info("\n🟢 上昇予想 TOP3:")
            for pred in sorted_preds[:3]:
                logger.info(
                    f"  {pred['name']:30s} {pred['change_percent']:+6.2f}%"
                )
            
            logger.info("\n🔴 下落予想 TOP3:")
            for pred in sorted_preds[-3:]:
                logger.info(
                    f"  {pred['name']:30s} {pred['change_percent']:+6.2f}%"
                )
            
            avg_change = np.mean([p['change_percent'] for p in predictions])
            logger.info(f"\n📊 平均予測変動率: {avg_change:+.2f}%")
        
        logger.info("\n" + "=" * 60)
        logger.info(f"✅ 予測完了: {len(predictions)}/{len(tickers)}銘柄")
        logger.info("=" * 60)
        
        return predictions

if __name__ == "__main__":
    system = StockPredictionSystem()
    predictions = system.predict_all()
    
    if len(predictions) == 0:
        logger.error("❌ 予測結果なし")
        sys.exit(1)
