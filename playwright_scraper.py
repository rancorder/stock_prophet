# playwright_scraper.py
from playwright.sync_api import sync_playwright
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PlaywrightStockScraper:
    def __init__(self):
        self.db_path = '/home/stock_prophet/data/stock_data.db'
        
    def scrape_yahoo_finance(self, ticker, days=90):
        """Yahoo Financeから株価データをスクレイピング"""
        logger.info(f"🎭 Playwright起動: {ticker}")
        
        with sync_playwright() as p:
            # Headless Chromium起動
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            
            page = context.new_page()
            
            try:
                # Yahoo Finance履歴ページ
                url = f'https://finance.yahoo.com/quote/{ticker}/history'
                logger.info(f"📊 アクセス: {url}")
                
                page.goto(url, wait_until='networkidle', timeout=30000)
                
                # ページが完全に読み込まれるまで待機
                page.wait_for_selector('table', timeout=10000)
                
                # テーブルデータ取得
                rows = page.query_selector_all('table tbody tr')
                
                data = []
                for row in rows:
                    try:
                        cells = row.query_selector_all('td')
                        if len(cells) >= 7:
                            date_str = cells[0].inner_text()
                            open_price = cells[1].inner_text().replace(',', '')
                            high_price = cells[2].inner_text().replace(',', '')
                            low_price = cells[3].inner_text().replace(',', '')
                            close_price = cells[4].inner_text().replace(',', '')
                            adj_close = cells[5].inner_text().replace(',', '')
                            volume = cells[6].inner_text().replace(',', '')
                            
                            # データクリーニング
                            if open_price != '-' and close_price != '-':
                                data.append({
                                    'Date': date_str,
                                    'Open': float(open_price),
                                    'High': float(high_price),
                                    'Low': float(low_price),
                                    'Close': float(close_price),
                                    'Adj Close': float(adj_close),
                                    'Volume': int(volume) if volume != '-' else 0
                                })
                    except Exception as e:
                        logger.warning(f"行の解析エラー: {e}")
                        continue
                
                logger.info(f"✅ {ticker}: {len(data)}件取得")
                
                # DataFrameに変換
                df = pd.DataFrame(data)
                df['Date'] = pd.to_datetime(df['Date'])
                df = df.sort_values('Date')
                df.set_index('Date', inplace=True)
                
                return df
                
            except Exception as e:
                logger.error(f"❌ スクレイピングエラー: {e}")
                return None
                
            finally:
                browser.close()
    
    def scrape_additional_info(self, ticker):
        """追加情報をスクレイピング（ニュース、指標など）"""
        logger.info(f"📰 追加情報取得: {ticker}")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                url = f'https://finance.yahoo.com/quote/{ticker}'
                page.goto(url, wait_until='networkidle')
                
                # 企業情報
                info = {}
                
                # 時価総額
                try:
                    market_cap = page.query_selector('[data-test="MARKET_CAP-value"]')
                    if market_cap:
                        info['market_cap'] = market_cap.inner_text()
                except:
                    pass
                
                # PER
                try:
                    pe_ratio = page.query_selector('[data-test="PE_RATIO-value"]')
                    if pe_ratio:
                        info['pe_ratio'] = pe_ratio.inner_text()
                except:
                    pass
                
                # 最新ニュース取得
                try:
                    news_items = page.query_selector_all('h3 a')
                    news = [item.inner_text() for item in news_items[:5]]
                    info['latest_news'] = news
                except:
                    pass
                
                logger.info(f"✅ 追加情報取得完了")
                return info
                
            except Exception as e:
                logger.error(f"❌ 追加情報取得エラー: {e}")
                return {}
                
            finally:
                browser.close()
    
    def save_to_db(self, ticker, df):
        """SQLiteに保存"""
        if df is not None and len(df) > 0:
            conn = sqlite3.connect(self.db_path)
            table_name = ticker.replace('.', '_').replace('-', '_')
            df.to_sql(table_name, conn, if_exists='replace')
            conn.close()
            logger.info(f"💾 DB保存完了: {table_name}")
    
    def run(self, tickers):
        """複数銘柄を順次スクレイピング"""
        for ticker in tickers:
            try:
                # 株価データ
                df = self.scrape_yahoo_finance(ticker)
                if df is not None:
                    self.save_to_db(ticker, df)
                
                # 追加情報
                info = self.scrape_additional_info(ticker)
                
                # レート制限対策
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"❌ {ticker}処理エラー: {e}")
                continue

# 実行
if __name__ == "__main__":
    scraper = PlaywrightStockScraper()
    
    tickers = [
        '7203.T',   # トヨタ
        '6758.T',   # ソニー
        '9984.T',   # ソフトバンク
        'AAPL',     # Apple
        'TSLA',     # Tesla
        'NVDA',     # NVIDIA
        'GOOGL',    # Google
        'MSFT',     # Microsoft
    ]
    
    scraper.run(tickers)
