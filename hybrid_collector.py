# hybrid_collector.py
import yfinance as yf
from playwright_scraper import PlaywrightStockScraper
import logging

logger = logging.getLogger(__name__)

class HybridCollector:
    def __init__(self):
        self.playwright_scraper = PlaywrightStockScraper()
    
    def collect_with_fallback(self, ticker):
        """yfinanceで取得、失敗時はplaywright"""
        logger.info(f"🔄 {ticker}データ収集開始")
        
        # まずyfinanceで試す（速い）
        try:
            logger.info("📊 yfinanceで取得中...")
            df = yf.download(ticker, period='3mo', progress=False)
            
            if len(df) > 0:
                logger.info(f"✅ yfinance成功: {len(df)}件")
                return df, 'yfinance'
        except Exception as e:
            logger.warning(f"⚠️ yfinance失敗: {e}")
        
        # yfinance失敗時はplaywright
        logger.info("🎭 playwrightで取得中...")
        df = self.playwright_scraper.scrape_yahoo_finance(ticker)
        
        if df is not None and len(df) > 0:
            logger.info(f"✅ playwright成功: {len(df)}件")
            return df, 'playwright'
        
        logger.error(f"❌ {ticker}取得失敗（両方とも）")
        return None, None
    
    def collect_all(self, tickers):
        """全銘柄収集"""
        results = {}
        
        for ticker in tickers:
            df, method = self.collect_with_fallback(ticker)
            if df is not None:
                results[ticker] = {
                    'data': df,
                    'method': method,
                    'records': len(df)
                }
        
        return results

# 実行
if __name__ == "__main__":
    collector = HybridCollector()
    
    tickers = ['7203.T', 'AAPL', 'TSLA']
    results = collector.collect_all(tickers)
    
    for ticker, result in results.items():
        print(f"{ticker}: {result['records']}件 ({result['method']})")
