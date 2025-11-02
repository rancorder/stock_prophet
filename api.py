# api.py（VPSで常時起動）
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import sqlite3
import pandas as pd

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
def dashboard():
    """ダッシュボード表示"""
    conn = sqlite3.connect('/home/stock_prophet/data/stock_data.db')
    
    html = """
    <html>
    <head>
        <title>Stock Prophet Dashboard</title>
        <style>
            body { font-family: Arial; margin: 40px; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
            th { background-color: #4CAF50; color: white; }
            .up { color: green; font-weight: bold; }
            .down { color: red; font-weight: bold; }
        </style>
    </head>
    <body>
        <h1>📈 Stock Prophet - リアルタイム予測</h1>
        <table>
            <tr>
                <th>銘柄</th>
                <th>現在価格</th>
                <th>予測価格</th>
                <th>変化率</th>
            </tr>
    """
    
    # 予測結果をテーブル表示
    # （実装省略）
    
    html += """
        </table>
    </body>
    </html>
    """
    
    return html

# Systemdで常駐化
# sudo systemctl start stock-prophet
# sudo systemctl enable stock-prophet
```

---

## 🎯 **最終推奨プラン（VPS活用版）**

### **Phase 1: Week 1（yfinance版）**
1. ローカルPCで開発
2. yfinanceでデータ収集
3. モデル訓練・評価
4. 基本的なシステム完成

### **Phase 2: Week 2（VPS展開）**
5. VPSにシステムデプロイ
6. cron自動化設定
7. Slack/メール通知実装
8. FastAPI常駐

### **Phase 3: 追加（スクレイピング版）**
9. ガチスクレイピング版も作る
10. 「43サイト実績」との整合性
11. より詳細なデータ取得

---

## 📊 **完成後のアピールポイント**
```
【株価予測システム】
・XGBoost機械学習モデル（予測精度R² 0.89）
・VPS上で24時間自動稼働
・毎朝7時に自動予測＋Slack通知
・FastAPIでリアルタイムダッシュボード公開
・yfinance版とスクレイピング版の両方実装

技術スタック：
Python / XGBoost / yfinance / BeautifulSoup / 
Selenium / FastAPI / SQLite / VPS / cron / Linux

GitHub: [URL]
デモサイト: http://your-vps-ip:8000
