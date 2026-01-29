//! Parser modules for various data formats.

use serde::{Deserialize, Serialize};
use thiserror::Error;

#[derive(Error, Debug)]
pub enum ParserError {
    #[error("Failed to parse JSON: {0}")]
    JsonError(#[from] serde_json::Error),

    #[error("Failed to parse HTML: {0}")]
    HtmlError(String),

    #[error("Missing required field: {0}")]
    MissingField(String),

    #[error("Invalid format: {0}")]
    InvalidFormat(String),
}

pub type Result<T> = std::result::Result<T, ParserError>;

/// Common stock data structure used across parsers
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ParsedStock {
    pub ticker: String,
    pub name: String,
    pub price: f64,
    pub change: f64,
    pub change_percent: f64,
    pub volume: u64,
    pub market_cap: Option<f64>,
    pub pe_ratio: Option<f64>,
    pub dividend_yield: Option<f64>,
}

/// Parse a financial number string (handles K, M, B, T suffixes)
pub fn parse_financial_number(s: &str) -> Option<f64> {
    let s = s.trim().replace(",", "").replace("$", "");

    if s.is_empty() || s == "-" || s == "N/A" {
        return None;
    }

    let (num_str, multiplier) = if s.ends_with('T') {
        (s.trim_end_matches('T'), 1_000_000_000_000.0)
    } else if s.ends_with('B') {
        (s.trim_end_matches('B'), 1_000_000_000.0)
    } else if s.ends_with('M') {
        (s.trim_end_matches('M'), 1_000_000.0)
    } else if s.ends_with('K') {
        (s.trim_end_matches('K'), 1_000.0)
    } else {
        (s.as_str(), 1.0)
    };

    num_str.parse::<f64>().ok().map(|n| n * multiplier)
}

/// Parse a percentage string
pub fn parse_percent(s: &str) -> Option<f64> {
    let s = s.trim().replace("%", "").replace(",", "");

    if s.is_empty() || s == "-" || s == "N/A" {
        return None;
    }

    s.parse().ok()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_financial_number() {
        assert_eq!(parse_financial_number("1.5B"), Some(1_500_000_000.0));
        assert_eq!(parse_financial_number("500M"), Some(500_000_000.0));
        assert_eq!(parse_financial_number("100K"), Some(100_000.0));
        assert_eq!(parse_financial_number("1,234.56"), Some(1234.56));
        assert_eq!(parse_financial_number("-"), None);
        assert_eq!(parse_financial_number("N/A"), None);
    }

    #[test]
    fn test_parse_percent() {
        assert_eq!(parse_percent("12.34%"), Some(12.34));
        assert_eq!(parse_percent("-5.67%"), Some(-5.67));
        assert_eq!(parse_percent("N/A"), None);
    }
}
