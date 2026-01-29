//! Stock Advisor Rust Library
//!
//! High-performance scraping and parsing components for Stock Advisor.

pub mod scraper;
pub mod parser;

pub use scraper::finviz::FinvizScraper;
