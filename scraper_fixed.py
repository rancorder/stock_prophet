"""
株価スクレイパー（playwright使用）
Yahoo Financeから株価データを取得
"""
from playwright.sync_api import sync_playwright
import pandas as pd
import time
import logging
import sqlite3
from typing import Optional, Dict

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class StockScraperFixed:
    """株価データスクレイパー"""
    
    def __init__(self):
        """初期化"""
        self.db_path = './data/stock_data.db'
    
    def scrape_single_stock(
        self,
        ticker: str,
        days: int = 90
    ) -> Optional[pd.DataFrame]:
        """
        単一銘柄の株価データをスクレイピング
        
        Args:
            ticker: ティッカーシンボル（例: 'AAPL', '7203.T'）
            days: 取得日数（デフォルト: 90日）
        
        Returns:
            株価データのDataFrame、失敗時はNone
            columns: ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        
        Examples:
            >>> scraper = StockScraperFixed()
            >>> df = scraper.scrape_single_stock('AAPL')
            >>> print(df.head())
        """
        logger.info(f"📊 処理開始: {ticker}")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                ]
            )
            
            page = browser.new_page()
            
            try:
                url = f'https://finance.yahoo.com/quote/{ticker}/history'
                page.goto(url, wait_until='domcontentloaded', timeout=60000)
                page.wait_for_selector('table tbody tr', timeout=20000)
                
                rows = page.query_selector_all('table tbody tr')
                
                data = []
                for row in rows[:days]:
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
                    except:
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
                logger.error(f"❌ {ticker}エラー: {e}")
                return None
            finally:
                browser.close()
    
    def scrape_multiple(
        self,
        tickers: list[str]
    ) -> Dict[str, pd.DataFrame]:
        """
        複数銘柄を順次スクレイピング
        
        Args:
            tickers: ティッカーシンボルのリスト
        
        Returns:
            {ticker: DataFrame} の辞書
        """
        results = {}
        
        for i, ticker in enumerate(tickers, 1):
            logger.info(f"\n進捗: {i}/{len(tickers)}")
            
            df = self.scrape_single_stock(ticker)
            
            if df is not None:
                results[ticker] = df
                self.save_to_db(ticker, df)
            
            if i < len(tickers):
                time.sleep(3)
        
        return results
    
    def save_to_db(
        self,
        ticker: str,
        df: pd.DataFrame
    ) -> None:
        """
        SQLiteにデータ保存
        
        Args:
            ticker: ティッカーシンボル
            df: 株価データのDataFrame
        """
        try:
            conn = sqlite3.connect(self.db_path)
            table_name = ticker.replace('.', '_').replace('-', '_')
            df.to_sql(table_name, conn, if_exists='replace')
            conn.close()
            logger.info(f"💾 DB保存完了: {table_name}")
        except Exception as e:
            logger.error(f"❌ DB保存エラー: {e}")

if __name__ == "__main__":
    import sys
    sys.path.append('.')
    from config.stock_config import get_all_tickers
    
    scraper = StockScraperFixed()
    tickers = get_all_tickers()
    
    logger.info(f"🚀 スクレイピング開始: {len(tickers)}銘柄")
    results = scraper.scrape_multiple(tickers)
    logger.info(f"✅ 完了: {len(results)}/{len(tickers)}銘柄")
