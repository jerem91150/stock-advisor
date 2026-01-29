//! Finviz scraper for stock screening and financial data.
//!
//! Finviz provides comprehensive stock screening capabilities and financial ratios.
//! This module implements concurrent scraping with rate limiting.

use super::{Result, ScraperError};
use governor::{Quota, RateLimiter};
use reqwest::Client;
use scraper::{Html, Selector};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::num::NonZeroU32;
use std::sync::Arc;
use std::time::Duration;
use tracing::{debug, info, warn};

/// Stock data from Finviz
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FinvizStock {
    pub ticker: String,
    pub company: String,
    pub sector: Option<String>,
    pub industry: Option<String>,
    pub country: Option<String>,

    // Price data
    pub price: Option<f64>,
    pub change_percent: Option<f64>,
    pub volume: Option<u64>,
    pub avg_volume: Option<u64>,

    // Valuation
    pub market_cap: Option<f64>,
    pub pe: Option<f64>,
    pub forward_pe: Option<f64>,
    pub peg: Option<f64>,
    pub ps: Option<f64>,
    pub pb: Option<f64>,

    // Financials
    pub eps: Option<f64>,
    pub eps_growth_this_year: Option<f64>,
    pub eps_growth_next_year: Option<f64>,
    pub sales_growth: Option<f64>,

    // Margins
    pub profit_margin: Option<f64>,
    pub operating_margin: Option<f64>,
    pub gross_margin: Option<f64>,

    // Returns
    pub roe: Option<f64>,
    pub roa: Option<f64>,
    pub roi: Option<f64>,

    // Debt
    pub debt_to_equity: Option<f64>,
    pub current_ratio: Option<f64>,
    pub quick_ratio: Option<f64>,

    // Dividend
    pub dividend_yield: Option<f64>,

    // Technical
    pub rsi: Option<f64>,
    pub beta: Option<f64>,
    pub sma20: Option<f64>,
    pub sma50: Option<f64>,
    pub sma200: Option<f64>,

    // 52-week
    pub high_52w: Option<f64>,
    pub low_52w: Option<f64>,

    // Analyst
    pub target_price: Option<f64>,
    pub analyst_recom: Option<f64>,
}

impl Default for FinvizStock {
    fn default() -> Self {
        Self {
            ticker: String::new(),
            company: String::new(),
            sector: None,
            industry: None,
            country: None,
            price: None,
            change_percent: None,
            volume: None,
            avg_volume: None,
            market_cap: None,
            pe: None,
            forward_pe: None,
            peg: None,
            ps: None,
            pb: None,
            eps: None,
            eps_growth_this_year: None,
            eps_growth_next_year: None,
            sales_growth: None,
            profit_margin: None,
            operating_margin: None,
            gross_margin: None,
            roe: None,
            roa: None,
            roi: None,
            debt_to_equity: None,
            current_ratio: None,
            quick_ratio: None,
            dividend_yield: None,
            rsi: None,
            beta: None,
            sma20: None,
            sma50: None,
            sma200: None,
            high_52w: None,
            low_52w: None,
            target_price: None,
            analyst_recom: None,
        }
    }
}

/// Finviz scraper with rate limiting
pub struct FinvizScraper {
    client: Client,
    rate_limiter: Arc<RateLimiter<governor::state::NotKeyed, governor::state::InMemoryState, governor::clock::DefaultClock>>,
    base_url: String,
}

impl FinvizScraper {
    /// Create a new Finviz scraper with default rate limiting (1 request per second)
    pub fn new() -> Result<Self> {
        Self::with_rate_limit(1)
    }

    /// Create a scraper with custom rate limit (requests per second)
    pub fn with_rate_limit(requests_per_second: u32) -> Result<Self> {
        let client = Client::builder()
            .user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            .timeout(Duration::from_secs(30))
            .cookie_store(true)
            .gzip(true)
            .build()
            .map_err(ScraperError::HttpError)?;

        let quota = Quota::per_second(NonZeroU32::new(requests_per_second).unwrap());
        let rate_limiter = Arc::new(RateLimiter::direct(quota));

        Ok(Self {
            client,
            rate_limiter,
            base_url: "https://finviz.com".to_string(),
        })
    }

    /// Scrape stock data for a single ticker
    pub async fn get_stock(&self, ticker: &str) -> Result<FinvizStock> {
        // Wait for rate limiter
        self.rate_limiter.until_ready().await;

        let url = format!("{}/quote.ashx?t={}", self.base_url, ticker.to_uppercase());
        debug!("Fetching: {}", url);

        let response = self.client.get(&url).send().await?;

        if !response.status().is_success() {
            return Err(ScraperError::StockNotFound(ticker.to_string()));
        }

        let html = response.text().await?;
        self.parse_stock_page(&html, ticker)
    }

    /// Scrape multiple stocks concurrently
    pub async fn get_stocks(&self, tickers: &[&str]) -> Vec<Result<FinvizStock>> {
        let mut results = Vec::with_capacity(tickers.len());

        // Process in batches to respect rate limiting
        for ticker in tickers {
            let result = self.get_stock(ticker).await;
            results.push(result);
        }

        results
    }

    /// Parse a Finviz stock page
    fn parse_stock_page(&self, html: &str, ticker: &str) -> Result<FinvizStock> {
        let document = Html::parse_document(html);
        let mut stock = FinvizStock::default();
        stock.ticker = ticker.to_uppercase();

        // Parse company name
        let title_selector = Selector::parse("table.fullview-title td.fullview-title").unwrap();
        if let Some(title_elem) = document.select(&title_selector).next() {
            stock.company = title_elem.text().collect::<String>().trim().to_string();
        }

        // Parse the snapshot table
        let table_selector = Selector::parse("table.snapshot-table2 tr").unwrap();
        let td_selector = Selector::parse("td").unwrap();

        let mut current_key = String::new();

        for row in document.select(&table_selector) {
            let cells: Vec<_> = row.select(&td_selector).collect();

            // Process pairs of cells (label, value)
            for chunk in cells.chunks(2) {
                if chunk.len() == 2 {
                    let key = chunk[0].text().collect::<String>().trim().to_string();
                    let value = chunk[1].text().collect::<String>().trim().to_string();

                    self.set_stock_field(&mut stock, &key, &value);
                }
            }
        }

        // Parse sector, industry, country from links
        let link_selector = Selector::parse("a.tab-link").unwrap();
        let mut link_values: Vec<String> = Vec::new();

        for link in document.select(&link_selector) {
            if let Some(href) = link.value().attr("href") {
                if href.contains("sec_") {
                    stock.sector = Some(link.text().collect::<String>().trim().to_string());
                } else if href.contains("ind_") {
                    stock.industry = Some(link.text().collect::<String>().trim().to_string());
                } else if href.contains("geo_") {
                    stock.country = Some(link.text().collect::<String>().trim().to_string());
                }
            }
        }

        Ok(stock)
    }

    /// Set a stock field based on the Finviz label
    fn set_stock_field(&self, stock: &mut FinvizStock, key: &str, value: &str) {
        // Skip empty or "-" values
        if value.is_empty() || value == "-" {
            return;
        }

        match key {
            "Price" => stock.price = self.parse_number(value),
            "Change" => stock.change_percent = self.parse_percent(value),
            "Volume" => stock.volume = self.parse_volume(value),
            "Avg Volume" => stock.avg_volume = self.parse_volume(value),
            "Market Cap" => stock.market_cap = self.parse_market_cap(value),
            "P/E" => stock.pe = self.parse_number(value),
            "Forward P/E" => stock.forward_pe = self.parse_number(value),
            "PEG" => stock.peg = self.parse_number(value),
            "P/S" => stock.ps = self.parse_number(value),
            "P/B" => stock.pb = self.parse_number(value),
            "EPS (ttm)" => stock.eps = self.parse_number(value),
            "EPS this Y" => stock.eps_growth_this_year = self.parse_percent(value),
            "EPS next Y" => stock.eps_growth_next_year = self.parse_percent(value),
            "Sales Q/Q" => stock.sales_growth = self.parse_percent(value),
            "Profit Margin" => stock.profit_margin = self.parse_percent(value),
            "Oper. Margin" => stock.operating_margin = self.parse_percent(value),
            "Gross Margin" => stock.gross_margin = self.parse_percent(value),
            "ROE" => stock.roe = self.parse_percent(value),
            "ROA" => stock.roa = self.parse_percent(value),
            "ROI" => stock.roi = self.parse_percent(value),
            "Debt/Eq" => stock.debt_to_equity = self.parse_number(value),
            "Current Ratio" => stock.current_ratio = self.parse_number(value),
            "Quick Ratio" => stock.quick_ratio = self.parse_number(value),
            "Dividend %" => stock.dividend_yield = self.parse_percent(value),
            "RSI (14)" => stock.rsi = self.parse_number(value),
            "Beta" => stock.beta = self.parse_number(value),
            "SMA20" => stock.sma20 = self.parse_percent(value),
            "SMA50" => stock.sma50 = self.parse_percent(value),
            "SMA200" => stock.sma200 = self.parse_percent(value),
            "52W High" => stock.high_52w = self.parse_percent(value),
            "52W Low" => stock.low_52w = self.parse_percent(value),
            "Target Price" => stock.target_price = self.parse_number(value),
            "Recom" => stock.analyst_recom = self.parse_number(value),
            _ => {}
        }
    }

    /// Parse a number from string
    fn parse_number(&self, s: &str) -> Option<f64> {
        let cleaned = s.replace(",", "").replace("$", "");
        cleaned.parse().ok()
    }

    /// Parse a percentage value
    fn parse_percent(&self, s: &str) -> Option<f64> {
        let cleaned = s.replace("%", "").replace(",", "");
        cleaned.parse().ok()
    }

    /// Parse volume (handles K, M suffixes)
    fn parse_volume(&self, s: &str) -> Option<u64> {
        let cleaned = s.replace(",", "");
        if cleaned.ends_with('K') {
            let num: f64 = cleaned.trim_end_matches('K').parse().ok()?;
            Some((num * 1_000.0) as u64)
        } else if cleaned.ends_with('M') {
            let num: f64 = cleaned.trim_end_matches('M').parse().ok()?;
            Some((num * 1_000_000.0) as u64)
        } else {
            cleaned.parse().ok()
        }
    }

    /// Parse market cap (handles B, M suffixes)
    fn parse_market_cap(&self, s: &str) -> Option<f64> {
        let cleaned = s.replace(",", "");
        if cleaned.ends_with('B') {
            let num: f64 = cleaned.trim_end_matches('B').parse().ok()?;
            Some(num * 1_000.0) // Return in millions
        } else if cleaned.ends_with('M') {
            let num: f64 = cleaned.trim_end_matches('M').parse().ok()?;
            Some(num)
        } else {
            cleaned.parse().ok()
        }
    }

    /// Screen stocks based on Finviz screener criteria
    pub async fn screen(&self, filters: &ScreenerFilters) -> Result<Vec<String>> {
        self.rate_limiter.until_ready().await;

        let url = format!(
            "{}/screener.ashx?v=111&{}",
            self.base_url,
            filters.to_query_string()
        );

        debug!("Screening: {}", url);

        let response = self.client.get(&url).send().await?;
        let html = response.text().await?;

        self.parse_screener_results(&html)
    }

    /// Parse screener results to get list of tickers
    fn parse_screener_results(&self, html: &str) -> Result<Vec<String>> {
        let document = Html::parse_document(html);
        let ticker_selector = Selector::parse("a.screener-link-primary").unwrap();

        let tickers: Vec<String> = document
            .select(&ticker_selector)
            .filter_map(|elem| {
                let text = elem.text().collect::<String>().trim().to_string();
                if !text.is_empty() {
                    Some(text)
                } else {
                    None
                }
            })
            .collect();

        Ok(tickers)
    }
}

impl Default for FinvizScraper {
    fn default() -> Self {
        Self::new().expect("Failed to create default FinvizScraper")
    }
}

/// Screener filters for Finviz
#[derive(Debug, Default, Clone)]
pub struct ScreenerFilters {
    pub exchange: Option<String>,
    pub market_cap: Option<String>,
    pub pe: Option<String>,
    pub peg: Option<String>,
    pub dividend_yield: Option<String>,
    pub sector: Option<String>,
    pub industry: Option<String>,
    pub country: Option<String>,
}

impl ScreenerFilters {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn exchange(mut self, exchange: &str) -> Self {
        self.exchange = Some(exchange.to_string());
        self
    }

    pub fn market_cap(mut self, cap: &str) -> Self {
        self.market_cap = Some(cap.to_string());
        self
    }

    pub fn sector(mut self, sector: &str) -> Self {
        self.sector = Some(sector.to_string());
        self
    }

    pub fn to_query_string(&self) -> String {
        let mut params = Vec::new();

        if let Some(ref ex) = self.exchange {
            params.push(format!("f=exch_{}", ex));
        }
        if let Some(ref cap) = self.market_cap {
            params.push(format!("f=cap_{}", cap));
        }
        if let Some(ref sec) = self.sector {
            params.push(format!("f=sec_{}", sec));
        }

        params.join("&")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_number() {
        let scraper = FinvizScraper::new().unwrap();
        assert_eq!(scraper.parse_number("123.45"), Some(123.45));
        assert_eq!(scraper.parse_number("1,234.56"), Some(1234.56));
        assert_eq!(scraper.parse_number("-"), None);
    }

    #[test]
    fn test_parse_percent() {
        let scraper = FinvizScraper::new().unwrap();
        assert_eq!(scraper.parse_percent("12.34%"), Some(12.34));
        assert_eq!(scraper.parse_percent("-5.67%"), Some(-5.67));
    }

    #[test]
    fn test_parse_market_cap() {
        let scraper = FinvizScraper::new().unwrap();
        assert_eq!(scraper.parse_market_cap("2.5B"), Some(2500.0));
        assert_eq!(scraper.parse_market_cap("500M"), Some(500.0));
    }
}
