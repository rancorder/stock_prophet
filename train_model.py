#!/usr/bin/env python3
"""
株価予測モデル訓練スクリプト
"""
import sys
sys.path.append('.')

import pandas as pd
import numpy as np
import sqlite3
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
import joblib
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StockPredictor:
    def __init__(self):
        self.db_path = './data/stock_data.db'
        self.model_path = './models/stock_model.pkl'
    
    def create_features(self, df):
        """テクニカル指標作成"""
        # 移動平均
        df['SMA_5'] = df['Close'].rolling(5).mean()
        df['SMA_20'] = df['Close'].rolling(20).mean()
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # 価格変動率
        df['Return_1d'] = df['Close'].pct_change(1)
        df['Return_5d'] = df['Close'].pct_change(5)
        
        # ボラティリティ
        df['Volatility'] = df['Return_1d'].rolling(20).std()
        
        # 出来高
        df['Volume_SMA'] = df['Volume'].rolling(20).mean()
        
        # ターゲット: 翌日の終値
        df['Target'] = df['Close'].shift(-1)
        
        return df.dropna()
    
    def load_all_data(self):
        """全銘柄データ読み込み"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        all_data = []
        
        for table in tables:
            table_name = table[0]
            try:
                df = pd.read_sql(
                    f"SELECT * FROM '{table_name}'",
                    conn,
                    parse_dates=['Date']
                )
                df = df.set_index('Date')
                df = self.create_features(df)
                
                if len(df) > 0:
                    all_data.append(df)
                    logger.info(f"✅ {table_name}: {len(df)}件")
            except Exception as e:
                logger.error(f"❌ {table_name}: {e}")
        
        conn.close()
        
        if len(all_data) == 0:
            logger.error("❌ データが見つかりません")
            return None
        
        # 全データ結合
        combined = pd.concat(all_data)
        logger.info(f"\n�� 合計データ数: {len(combined)}件")
        
        return combined
    
    def train(self):
        """モデル訓練"""
        logger.info("=" * 60)
        logger.info("🤖 モデル訓練開始")
        logger.info("=" * 60)
        
        # データ読み込み
        logger.info("\n📥 データ読み込み中...")
        df = self.load_all_data()
        
        if df is None or len(df) == 0:
            logger.error("❌ データがありません")
            return None
        
        # 特徴量とターゲット
        feature_cols = [
            'Open', 'High', 'Low', 'Close', 'Volume',
            'SMA_5', 'SMA_20', 'RSI',
            'Return_1d', 'Return_5d', 'Volatility', 'Volume_SMA'
        ]
        
        X = df[feature_cols].values
        y = df['Target'].values
        
        logger.info(f"📊 特徴量数: {X.shape[1]}")
        logger.info(f"📊 サンプル数: {len(X)}")
        
        # 訓練・テストデータ分割
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        logger.info(f"\n🔀 データ分割")
        logger.info(f"  訓練: {len(X_train)}件")
        logger.info(f"  テスト: {len(X_test)}件")
        
        # XGBoostモデル訓練
        logger.info(f"\n🤖 XGBoostモデル訓練中...")
        model = XGBRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            random_state=42,
            verbosity=0
        )
        
        model.fit(X_train, y_train)
        
        # 評価
        train_score = model.score(X_train, y_train)
        test_score = model.score(X_test, y_test)
        
        logger.info(f"\n📈 モデル評価")
        logger.info(f"  訓練スコア (R²): {train_score:.4f}")
        logger.info(f"  テストスコア (R²): {test_score:.4f}")
        
        # 予測精度確認
        y_pred = model.predict(X_test)
        mae = np.mean(np.abs(y_test - y_pred))
        logger.info(f"  平均誤差 (MAE): ${mae:.2f}")
        
        # モデル保存
        joblib.dump(model, self.model_path)
        logger.info(f"\n💾 モデル保存完了: {self.model_path}")
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ 訓練完了！")
        logger.info("=" * 60)
        
        return model

if __name__ == "__main__":
    predictor = StockPredictor()
    model = predictor.train()
    
    if model is None:
        logger.error("❌ モデル訓練失敗")
        sys.exit(1)
