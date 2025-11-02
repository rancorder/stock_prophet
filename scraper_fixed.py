from playwright.sync_api import sync_playwright
import pandas as pd
import time
import logging
import sqlite3
import sys
sys.path.append('.')

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class StockScraperFixed:
    def __init__(self):
        self.db_path = './data/stock_data.db'
    
    def scrape_single_stock(self, ticker):
        """1銘柄をスクレイピング（タイムアウト対策版）"""
        logger.info(f"📊 処理開始: {ticker}")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
            context = browser.new_context()
            page = context.new_page()
            
            try:
                url = f'https://finance.yahoo.com/quote/{ticker}/history'
                
                # 修正1: domcontentloadedに変更（高速化）
                # 修正2: タイムアウト60秒に延長
                page.goto(url, wait_until='domcontentloaded', timeout=60000)
                
                # 修正3: テーブル待機時間も延長
                page.wait_for_selector('table tbody tr', timeout=30000)
                
                rows = page.query_selector_all('table tbody tr')
                logger.info(f"  テーブル行数: {len(rows)}")
                
                data = []
                for row in rows[:90]:
                    try:
                        cells = row.query_selector_all('td')
                        if len(cells) >= 7:
                            date_str = cells[0].inner_text()
                            
                            if 'Dividend' in date_str or 'Split' in date_str:
                                continue
                            
                            open_p = cells[1].inner_text().replace(',', '')
                            high_p = cells[2].inner_text().replace(',', '')
                            low_p = cells[3].inner_text().replace(',', '')
                            close_p = cells[4].inner_text().replace(',', '')
                            volume = cells[6].inner_text().replace(',', '')
                            
                            if open_p != '-' and close_p != '-':
                                data.append({
                                    'Date': date_str,
                                    'Open': float(open_p),
                                    'High': float(high_p),
                                    'Low': float(low_p),
                                    'Close': float(close_p),
                                    'Volume': int(volume) if volume != '-' else 0
                                })
                    except Exception as e:
                        continue
                
                if len(data) > 0:
                    df = pd.DataFrame(data)
                    df['Date'] = pd.to_datetime(df['Date'])
                    df = df.sort_values('Date')
                    df.set_index('Date', inplace=True)
                    
                    logger.info(f"✅ {ticker}: {len(df)}件取得")
                    return df
                else:
                    logger.warning(f"⚠️  {ticker}: データなし")
                    return None
                    
            except Exception as e:
                logger.error(f"❌ {ticker}エラー: {str(e)[:100]}")
                return None
            finally:
                context.close()
                browser.close()
    
    def scrape_multiple(self, tickers):
        """複数銘柄を順次スクレイピング"""
        results = {}
        
        for i, ticker in enumerate(tickers, 1):
            logger.info(f"\n━━━━━━━━━━━━━━━━━━━━━━")
            logger.info(f"進捗: {i}/{len(tickers)} - {ticker}")
            logger.info(f"━━━━━━━━━━━━━━━━━━━━━━")
            
            df = self.scrape_single_stock(ticker)
            
            if df is not None:
                results[ticker] = df
                self.save_to_db(ticker, df)
            else:
                logger.warning(f"⚠️  {ticker}のデータ取得失敗（スキップ）")
            
            # レート制限対策（待機時間を長めに）
            if i < len(tickers):
                logger.info(f"⏳ 3秒待機...")
                time.sleep(3)
        
        return results
    
    def save_to_db(self, ticker, df):
        """SQLiteに保存"""
        try:
            conn = sqlite3.connect(self.db_path)
            table_name = ticker.replace('.', '_').replace('-', '_')
            df.to_sql(table_name, conn, if_exists='replace')
            conn.close()
            logger.info(f"💾 DB保存完了: {table_name}")
        except Exception as e:
            logger.error(f"❌ DB保存エラー: {e}")

if __name__ == "__main__":
    from config.stock_config import get_all_tickers
    
    scraper = StockScraperFixed()
    tickers = get_all_tickers()
    
    logger.info(f"🚀 改良版スクレイピング開始")
    logger.info(f"📊 対象: {len(tickers)}銘柄")
    logger.info(f"銘柄: {', '.join(tickers)}")
    logger.info(f"")
    
    results = scraper.scrape_multiple(tickers)
    
    logger.info(f"\n" + "=" * 60)
    logger.info(f"✅ スクレイピング完了")
    logger.info(f"成功: {len(results)}/{len(tickers)}銘柄")
    logger.info(f"=" * 60)
    
    if len(results) > 0:
        logger.info(f"\n📊 取得成功銘柄:")
        for ticker in results.keys():
            logger.info(f"  ✅ {ticker}")
