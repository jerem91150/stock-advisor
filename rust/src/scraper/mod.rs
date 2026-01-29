//! Scraping modules for various financial data sources.

pub mod finviz;

use thiserror::Error;

/// Errors that can occur during scraping.
#[derive(Error, Debug)]
pub enum ScraperError {
    #[error("HTTP request failed: {0}")]
    HttpError(#[from] reqwest::Error),

    #[error("Failed to parse HTML: {0}")]
    ParseError(String),

    #[error("Rate limit exceeded")]
    RateLimitExceeded,

    #[error("Stock not found: {0}")]
    StockNotFound(String),

    #[error("Invalid response: {0}")]
    InvalidResponse(String),
}

pub type Result<T> = std::result::Result<T, ScraperError>;
