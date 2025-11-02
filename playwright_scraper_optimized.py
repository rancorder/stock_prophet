# playwright_scraper_optimized.py
from playwright.sync_api import sync_playwright
import pandas as pd
import sqlite3
from datetime import datetime
import logging
import gc  # ガベージコレクション

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OptimizedStockScraper:
    def __init__(self):
        self.db_path = '/home/stock_prophet/data/stock_data.db'
        
    def scrape_with_single_browser(self, tickers):
        """1つのブラウザで全銘柄を処理（メモリ節約）"""
        logger.info("🎭 Playwright起動（最適化モード）")
        
        with sync_playwright() as p:
            # ブラウザは1回だけ起動
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-software-rasterizer',
                    '--disable-extensions',
                    # メモリ節約設定
                    '--single-process',
                    '--disable-background-networking',
                    '--disable-default-apps',
                    '--disable-sync',
                ]
            )
            
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            
            results = {}
            
            for ticker in tickers:
                try:
                    logger.info(f"📊 処理中: {ticker}")
                    
                    # 新しいページを開く
                    page = context.new_page()
                    
                    # Yahoo Finance履歴ページ
                    url = f'https://finance.yahoo.com/quote/{ticker}/history'
                    page.goto(url, wait_until='domcontentloaded', timeout=20000)
                    
                    # テーブル取得を待つ
                    try:
                        page.wait_for_selector('table tbody tr', timeout=10000)
                    except:
                        logger.warning(f"⚠️ {ticker}: テーブル読み込みタイムアウト")
                        page.close()
                        continue
                    
                    # データ抽出
                    rows = page.query_selector_all('table tbody tr')
                    
                    data = []
                    for row in rows[:90]:  # 最新90日分のみ（メモリ節約）
                        try:
                            cells = row.query_selector_all('td')
                            if len(cells) >= 7:
                                date_str = cells[0].inner_text()
                                
                                # "Dividend"行はスキップ
                                if 'Dividend' in date_str or 'Split' in date_str:
                                    continue
                                
                                open_price = cells[1].inner_text().replace(',', '')
                                high_price = cells[2].inner_text().replace(',', '')
                                low_price = cells[3].inner_text().replace(',', '')
                                close_price = cells[4].inner_text().replace(',', '')
                                adj_close = cells[5].inner_text().replace(',', '')
                                volume = cells[6].inner_text().replace(',', '')
                                
                                if open_price != '-' and close_price != '-':
                                    data.append({
                                        'Date': date_str,
                                        'Open': float(open_price),
                                        'High': float(high_price),
                                        'Low': float(low_price),
                                        'Close': float(close_price),
                                        'Adj Close': float(adj_close) if adj_close != '-' else float(close_price),
                                        'Volume': int(volume) if volume != '-' else 0
                                    })
                        except Exception as e:
                            continue
                    
                    if len(data) > 0:
                        df = pd.DataFrame(data)
                        df['Date'] = pd.to_datetime(df['Date'])
                        df = df.sort_values('Date')
                        df.set_index('Date', inplace=True)
                        
                        results[ticker] = df
                        logger.info(f"✅ {ticker}: {len(df)}件取得")
                    else:
                        logger.warning(f"⚠️ {ticker}: データなし")
                    
                    # ページを閉じてメモリ解放
                    page.close()
                    
                    # 短い待機（レート制限対策）
                    import time
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"❌ {ticker}エラー: {e}")
                    continue
            
            browser.close()
            
            # 明示的にメモリ解放
            gc.collect()
            
            return results
    
    def save_all_to_db(self, results):
        """一括でDB保存"""
        conn = sqlite3.connect(self.db_path)
        
        for ticker, df in results.items():
            try:
                table_name = ticker.replace('.', '_').replace('-', '_')
                df.to_sql(table_name, conn, if_exists='replace')
                logger.info(f"💾 {ticker}保存完了")
            except Exception as e:
                logger.error(f"❌ {ticker}保存エラー: {e}")
        
        conn.close()
    
    def run(self, tickers):
        """実行"""
        results = self.scrape_with_single_browser(tickers)
        self.save_all_to_db(results)
        return results

# 実行
if __name__ == "__main__":
    scraper = OptimizedStockScraper()
    
    # 日本株 + 米国株
    tickers = [
        # 日本株
        '7203.T',   # トヨタ
        '6758.T',   # ソニー
        '9984.T',   # ソフトバンク
        '6501.T',   # 日立
        '8306.T',   # 三菱UFJ
        # 米国株
        'AAPL',     # Apple
        'TSLA',     # Tesla
        'NVDA',     # NVIDIA
        'GOOGL',    # Google
        'MSFT',     # Microsoft
    ]
    
    logger.info("🚀 最適化版スクレイパー起動")
    results = scraper.run(tickers)
    logger.info(f"✅ 完了: {len(results)}銘柄")
