//! CLI for Finviz scraper
//!
//! Usage:
//!   finviz-scraper stock AAPL MSFT GOOGL
//!   finviz-scraper screen --sector technology --market-cap large

use clap::{Parser, Subcommand};
use stock_advisor::scraper::finviz::{FinvizScraper, ScreenerFilters};
use tracing::{info, Level};
use tracing_subscriber::FmtSubscriber;

#[derive(Parser)]
#[command(name = "finviz-scraper")]
#[command(about = "High-performance Finviz scraper for Stock Advisor")]
struct Cli {
    #[command(subcommand)]
    command: Commands,

    /// Verbosity level
    #[arg(short, long, default_value = "info")]
    log_level: String,

    /// Output format (json, csv, table)
    #[arg(short, long, default_value = "json")]
    format: String,
}

#[derive(Subcommand)]
enum Commands {
    /// Fetch data for specific stocks
    Stock {
        /// Ticker symbols to fetch
        tickers: Vec<String>,
    },

    /// Screen stocks based on criteria
    Screen {
        /// Sector filter
        #[arg(long)]
        sector: Option<String>,

        /// Market cap filter (micro, small, mid, large, mega)
        #[arg(long)]
        market_cap: Option<String>,

        /// Exchange filter (nyse, nasdaq, amex)
        #[arg(long)]
        exchange: Option<String>,
    },
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();

    // Setup logging
    let log_level = match cli.log_level.to_lowercase().as_str() {
        "trace" => Level::TRACE,
        "debug" => Level::DEBUG,
        "info" => Level::INFO,
        "warn" => Level::WARN,
        "error" => Level::ERROR,
        _ => Level::INFO,
    };

    let subscriber = FmtSubscriber::builder()
        .with_max_level(log_level)
        .with_target(false)
        .finish();
    tracing::subscriber::set_global_default(subscriber)?;

    let scraper = FinvizScraper::new()?;

    match cli.command {
        Commands::Stock { tickers } => {
            info!("Fetching data for {} stocks", tickers.len());

            let ticker_refs: Vec<&str> = tickers.iter().map(|s| s.as_str()).collect();
            let results = scraper.get_stocks(&ticker_refs).await;

            let mut stocks = Vec::new();
            for result in results {
                match result {
                    Ok(stock) => stocks.push(stock),
                    Err(e) => eprintln!("Error: {}", e),
                }
            }

            match cli.format.as_str() {
                "json" => {
                    println!("{}", serde_json::to_string_pretty(&stocks)?);
                }
                "csv" => {
                    println!("ticker,company,price,pe,peg,market_cap,dividend_yield,roe,debt_to_equity");
                    for stock in stocks {
                        println!(
                            "{},{},{},{},{},{},{},{},{}",
                            stock.ticker,
                            stock.company.replace(",", ";"),
                            stock.price.map(|v| v.to_string()).unwrap_or_default(),
                            stock.pe.map(|v| v.to_string()).unwrap_or_default(),
                            stock.peg.map(|v| v.to_string()).unwrap_or_default(),
                            stock.market_cap.map(|v| v.to_string()).unwrap_or_default(),
                            stock.dividend_yield.map(|v| v.to_string()).unwrap_or_default(),
                            stock.roe.map(|v| v.to_string()).unwrap_or_default(),
                            stock.debt_to_equity.map(|v| v.to_string()).unwrap_or_default(),
                        );
                    }
                }
                "table" => {
                    println!("{:<8} {:<30} {:>10} {:>8} {:>8}", "Ticker", "Company", "Price", "P/E", "PEG");
                    println!("{}", "-".repeat(70));
                    for stock in stocks {
                        println!(
                            "{:<8} {:<30} {:>10} {:>8} {:>8}",
                            stock.ticker,
                            &stock.company[..stock.company.len().min(30)],
                            stock.price.map(|v| format!("{:.2}", v)).unwrap_or("-".to_string()),
                            stock.pe.map(|v| format!("{:.1}", v)).unwrap_or("-".to_string()),
                            stock.peg.map(|v| format!("{:.2}", v)).unwrap_or("-".to_string()),
                        );
                    }
                }
                _ => {
                    println!("{}", serde_json::to_string_pretty(&stocks)?);
                }
            }
        }

        Commands::Screen {
            sector,
            market_cap,
            exchange,
        } => {
            let mut filters = ScreenerFilters::new();

            if let Some(sec) = sector {
                filters = filters.sector(&sec);
            }
            if let Some(cap) = market_cap {
                filters = filters.market_cap(&cap);
            }
            if let Some(ex) = exchange {
                filters = filters.exchange(&ex);
            }

            info!("Screening stocks with filters...");
            let tickers = scraper.screen(&filters).await?;

            match cli.format.as_str() {
                "json" => {
                    println!("{}", serde_json::to_string_pretty(&tickers)?);
                }
                _ => {
                    println!("Found {} stocks:", tickers.len());
                    for ticker in &tickers {
                        println!("  {}", ticker);
                    }
                }
            }
        }
    }

    Ok(())
}
