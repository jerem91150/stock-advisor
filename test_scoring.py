"""Test du nouveau scoring avec TTE.PA"""
import yfinance as yf
import numpy as np


def calculate_full_score(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")

        if hist.empty or len(hist) < 50:
            return None

        info = stock.info

        result = {
            "ticker": ticker,
            "name": info.get("shortName", ticker),
            "price": info.get("currentPrice") or info.get("regularMarketPrice", 0),
            "currency": info.get("currency", "USD"),
            "sector": info.get("sector", "N/A"),
            "scores": {},
            "details": {},
        }

        # Seuils P/E par secteur
        sector_pe = {
            "Energy": {"very_low": 5, "low": 8, "fair": 12, "high": 18, "very_high": 25},
            "Technology": {"very_low": 12, "low": 18, "fair": 28, "high": 40, "very_high": 55},
            "Financial Services": {"very_low": 6, "low": 9, "fair": 14, "high": 20, "very_high": 28},
            "Healthcare": {"very_low": 12, "low": 18, "fair": 28, "high": 40, "very_high": 55},
            "Consumer Cyclical": {"very_low": 8, "low": 13, "fair": 20, "high": 28, "very_high": 38},
            "Consumer Defensive": {"very_low": 12, "low": 16, "fair": 22, "high": 28, "very_high": 36},
            "Industrials": {"very_low": 10, "low": 14, "fair": 20, "high": 28, "very_high": 38},
            "Utilities": {"very_low": 10, "low": 14, "fair": 18, "high": 24, "very_high": 32},
            "Real Estate": {"very_low": 12, "low": 18, "fair": 28, "high": 40, "very_high": 55},
            "Basic Materials": {"very_low": 6, "low": 9, "fair": 14, "high": 20, "very_high": 28},
            "Communication Services": {"very_low": 12, "low": 16, "fair": 24, "high": 32, "very_high": 45},
        }
        default_pe = {"very_low": 8, "low": 13, "fair": 20, "high": 30, "very_high": 42}
        sector = info.get("sector", "N/A")
        pe_thresh = sector_pe.get(sector, default_pe)

        # 1. SCORE TECHNIQUE (30%)
        current_price = float(hist["Close"].iloc[-1])
        ma50 = float(hist["Close"].tail(50).mean())
        ma200 = float(hist["Close"].mean()) if len(hist) >= 200 else ma50

        tech_score = 50
        tech_details = []

        if current_price > ma50 * 1.02:
            tech_score += 10
            tech_details.append("Prix > MA50 (+10)")
        elif current_price > ma50:
            tech_score += 5
            tech_details.append("Prix ~ MA50 (+5)")
        elif current_price < ma50 * 0.95:
            tech_score -= 15
            tech_details.append("Prix << MA50 (-15)")
        elif current_price < ma50 * 0.98:
            tech_score -= 10
            tech_details.append("Prix < MA50 (-10)")

        if ma50 > ma200 * 1.05:
            tech_score += 15
            tech_details.append("Golden Cross fort (+15)")
        elif ma50 > ma200:
            tech_score += 5
            tech_details.append("MA50 > MA200 (+5)")
        elif ma50 < ma200 * 0.95:
            tech_score -= 15
            tech_details.append("Death Cross (-15)")
        elif ma50 < ma200:
            tech_score -= 5
            tech_details.append("MA50 < MA200 (-5)")

        # RSI 14j
        if len(hist) >= 14:
            delta = hist["Close"].diff()
            gain = delta.where(delta > 0, 0).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss.replace(0, np.inf)
            rsi_val = float((100 - (100 / (1 + rs))).iloc[-1])
            if rsi_val > 80:
                tech_score -= 15
                tech_details.append(f"RSI={rsi_val:.0f} surachat fort (-15)")
            elif rsi_val > 70:
                tech_score -= 10
                tech_details.append(f"RSI={rsi_val:.0f} surachat (-10)")
            elif rsi_val > 65:
                tech_score -= 5
                tech_details.append(f"RSI={rsi_val:.0f} surachat leger (-5)")
            elif rsi_val < 25:
                tech_score += 15
                tech_details.append(f"RSI={rsi_val:.0f} survente forte (+15)")
            elif rsi_val < 30:
                tech_score += 10
                tech_details.append(f"RSI={rsi_val:.0f} survente (+10)")
            elif rsi_val < 40:
                tech_score += 5
                tech_details.append(f"RSI={rsi_val:.0f} zone basse (+5)")
        else:
            rsi_val = None

        # Distance au 52w high
        high_52w = float(hist["High"].max())
        if high_52w > 0:
            pct_from_high = current_price / high_52w
            if pct_from_high > 0.95:
                tech_score -= 10
                tech_details.append(f"Proche 52w high {pct_from_high*100:.0f}% (-10)")
            elif pct_from_high > 0.90:
                tech_score -= 5
                tech_details.append(f"Proche 52w high {pct_from_high*100:.0f}% (-5)")
            elif pct_from_high < 0.65:
                tech_score -= 5
                tech_details.append(f"Loin du 52w high {pct_from_high*100:.0f}% (-5)")

        # Distance MA200
        if len(hist) >= 200 and ma200 > 0:
            pct_above_ma200 = current_price / ma200
            if pct_above_ma200 > 1.30:
                tech_score -= 10
                tech_details.append(f"Trop etire +{(pct_above_ma200-1)*100:.0f}% vs MA200 (-10)")
            elif pct_above_ma200 > 1.20:
                tech_score -= 5
                tech_details.append(f"Etire +{(pct_above_ma200-1)*100:.0f}% vs MA200 (-5)")

        # Pente MA50
        if len(hist) >= 60:
            ma50_now = float(hist["Close"].tail(50).mean())
            ma50_prev = float(hist["Close"].iloc[-60:-10].tail(50).mean())
            if ma50_prev > 0:
                ma50_slope = (ma50_now / ma50_prev - 1) * 100
                if ma50_slope < -2:
                    tech_score -= 8
                    tech_details.append(f"MA50 en baisse {ma50_slope:.1f}% (-8)")
                elif ma50_slope < 0:
                    tech_score -= 3
                    tech_details.append(f"MA50 s'aplatit {ma50_slope:.1f}% (-3)")

        # Momentum 1M
        if len(hist) >= 21:
            price_1m = float(hist["Close"].iloc[-21])
            mom_1m = (current_price / price_1m - 1) * 100
            if mom_1m > 10:
                tech_score += 10
                tech_details.append(f"Momentum 1M: +{mom_1m:.1f}% (+10)")
            elif mom_1m > 5:
                tech_score += 5
                tech_details.append(f"Momentum 1M: +{mom_1m:.1f}% (+5)")
            elif mom_1m > 2:
                tech_score += 2
                tech_details.append(f"Momentum 1M: +{mom_1m:.1f}% (+2)")
            elif mom_1m < -10:
                tech_score -= 15
                tech_details.append(f"Momentum 1M: {mom_1m:.1f}% (-15)")
            elif mom_1m < -5:
                tech_score -= 10
                tech_details.append(f"Momentum 1M: {mom_1m:.1f}% (-10)")
            elif mom_1m < -2:
                tech_score -= 5
                tech_details.append(f"Momentum 1M: {mom_1m:.1f}% (-5)")

        tech_score = max(0, min(100, tech_score))
        result["scores"]["technical"] = tech_score
        result["details"]["technical"] = tech_details

        # 2. SCORE FONDAMENTAL (30%)
        fund_score = 50
        fund_details = []

        pe = info.get("trailingPE")
        if pe and pe > 0:
            if pe < pe_thresh["very_low"]:
                fund_score += 15
                fund_details.append(f"P/E={pe:.1f} tres bas vs secteur (+15)")
            elif pe < pe_thresh["low"]:
                fund_score += 10
                fund_details.append(f"P/E={pe:.1f} bas vs secteur (+10)")
            elif pe < pe_thresh["fair"]:
                fund_score += 5
                fund_details.append(f"P/E={pe:.1f} correct vs secteur (+5)")
            elif pe < pe_thresh["high"]:
                fund_details.append(f"P/E={pe:.1f} dans la norme secteur")
            elif pe < pe_thresh["very_high"]:
                fund_score -= 10
                fund_details.append(f"P/E={pe:.1f} eleve vs secteur (-10)")
            else:
                fund_score -= 15
                fund_details.append(f"P/E={pe:.1f} tres eleve vs secteur (-15)")
        elif pe and pe < 0:
            fund_score -= 10
            fund_details.append("P/E negatif (-10)")

        peg = info.get("pegRatio")
        if peg and peg > 0:
            if peg < 0.5:
                fund_score += 12
                fund_details.append(f"PEG={peg:.2f} tres attractif (+12)")
            elif peg < 1.0:
                fund_score += 8
                fund_details.append(f"PEG={peg:.2f} attractif (+8)")
            elif peg < 1.5:
                fund_score += 3
                fund_details.append(f"PEG={peg:.2f} correct (+3)")
            elif peg > 3.0:
                fund_score -= 10
                fund_details.append(f"PEG={peg:.2f} tres eleve (-10)")
            elif peg > 2.0:
                fund_score -= 5
                fund_details.append(f"PEG={peg:.2f} eleve (-5)")

        margin = info.get("profitMargins")
        if margin is not None:
            margin_pct = margin * 100
            if margin_pct > 25:
                fund_score += 10
                fund_details.append(f"Marge={margin_pct:.1f}% excellente (+10)")
            elif margin_pct > 15:
                fund_score += 5
                fund_details.append(f"Marge={margin_pct:.1f}% bonne (+5)")
            elif margin_pct > 5:
                fund_details.append(f"Marge={margin_pct:.1f}% correcte")
            elif margin_pct > 0:
                fund_score -= 5
                fund_details.append(f"Marge={margin_pct:.1f}% faible (-5)")
            else:
                fund_score -= 10
                fund_details.append(f"Marge={margin_pct:.1f}% negative (-10)")

        roe = info.get("returnOnEquity")
        if roe is not None:
            roe_pct = roe * 100
            if roe_pct > 25:
                fund_score += 12
                fund_details.append(f"ROE={roe_pct:.1f}% excellent (+12)")
            elif roe_pct > 15:
                fund_score += 8
                fund_details.append(f"ROE={roe_pct:.1f}% bon (+8)")
            elif roe_pct > 10:
                fund_score += 3
                fund_details.append(f"ROE={roe_pct:.1f}% correct (+3)")
            elif roe_pct > 0:
                fund_score -= 3
                fund_details.append(f"ROE={roe_pct:.1f}% faible (-3)")
            else:
                fund_score -= 12
                fund_details.append(f"ROE={roe_pct:.1f}% negatif (-12)")

        debt = info.get("debtToEquity")
        if debt is not None:
            if debt < 30:
                fund_score += 8
                fund_details.append(f"Debt/Eq={debt:.0f}% faible (+8)")
            elif debt < 80:
                fund_score += 3
                fund_details.append(f"Debt/Eq={debt:.0f}% modere (+3)")
            elif debt > 200:
                fund_score -= 12
                fund_details.append(f"Debt/Eq={debt:.0f}% tres eleve (-12)")
            elif debt > 150:
                fund_score -= 8
                fund_details.append(f"Debt/Eq={debt:.0f}% eleve (-8)")

        fund_score = max(0, min(100, fund_score))
        result["scores"]["fundamental"] = fund_score
        result["details"]["fundamental"] = fund_details

        # 3. SCORE SENTIMENT (20%)
        sent_score = 50
        sent_details = []

        if len(hist) >= 5:
            price_5d = float(hist["Close"].iloc[-5])
            mom_5d = (current_price / price_5d - 1) * 100
            if mom_5d > 5:
                sent_score += 15
                sent_details.append(f"Momentum 5j: +{mom_5d:.1f}% fort (+15)")
            elif mom_5d > 2:
                sent_score += 10
                sent_details.append(f"Momentum 5j: +{mom_5d:.1f}% (+10)")
            elif mom_5d > 0:
                sent_score += 3
                sent_details.append(f"Momentum 5j: +{mom_5d:.1f}% (+3)")
            elif mom_5d > -2:
                sent_score -= 3
                sent_details.append(f"Momentum 5j: {mom_5d:.1f}% (-3)")
            elif mom_5d > -5:
                sent_score -= 10
                sent_details.append(f"Momentum 5j: {mom_5d:.1f}% (-10)")
            else:
                sent_score -= 18
                sent_details.append(f"Momentum 5j: {mom_5d:.1f}% fort (-18)")

        if len(hist) >= 63:
            price_3m = float(hist["Close"].iloc[-63])
            mom_3m = (current_price / price_3m - 1) * 100
            if mom_3m > 15:
                sent_score += 10
                sent_details.append(f"Momentum 3M: +{mom_3m:.1f}% (+10)")
            elif mom_3m > 5:
                sent_score += 5
                sent_details.append(f"Momentum 3M: +{mom_3m:.1f}% (+5)")
            elif mom_3m < -15:
                sent_score -= 12
                sent_details.append(f"Momentum 3M: {mom_3m:.1f}% (-12)")
            elif mom_3m < -5:
                sent_score -= 6
                sent_details.append(f"Momentum 3M: {mom_3m:.1f}% (-6)")

        avg_vol = float(hist["Volume"].mean())
        recent_vol = float(hist["Volume"].tail(5).mean())
        if avg_vol > 0:
            vol_ratio = recent_vol / avg_vol
            if vol_ratio > 2.0:
                sent_score += 8
                sent_details.append(f"Volume tres eleve x{vol_ratio:.1f} (+8)")
            elif vol_ratio > 1.5:
                sent_score += 5
                sent_details.append(f"Volume eleve x{vol_ratio:.1f} (+5)")
            elif vol_ratio < 0.5:
                sent_score -= 8
                sent_details.append(f"Volume tres faible x{vol_ratio:.1f} (-8)")
            elif vol_ratio < 0.7:
                sent_score -= 4
                sent_details.append(f"Volume faible x{vol_ratio:.1f} (-4)")

        sent_score = max(0, min(100, sent_score))
        result["scores"]["sentiment"] = sent_score
        result["details"]["sentiment"] = sent_details

        # 4. SCORE SMART MONEY (20%)
        smart_score = 40
        smart_details = []

        inst_hold = info.get("heldPercentInstitutions")
        if inst_hold is not None:
            smart_score = 45
            if inst_hold > 0.80:
                smart_score += 10
                smart_details.append(f"Instit: {inst_hold*100:.0f}% (+10)")
            elif inst_hold > 0.60:
                smart_score += 8
                smart_details.append(f"Instit: {inst_hold*100:.0f}% (+8)")
            elif inst_hold > 0.40:
                smart_score += 5
                smart_details.append(f"Instit: {inst_hold*100:.0f}% (+5)")
            elif inst_hold < 0.20:
                smart_score -= 5
                smart_details.append(f"Instit: {inst_hold*100:.0f}% faible (-5)")
        else:
            smart_details.append("Pas de donnees instit (base 40)")

        insider_hold = info.get("heldPercentInsiders")
        if insider_hold and insider_hold > 0.10:
            smart_score += 8
            smart_details.append(f"Insiders: {insider_hold*100:.1f}% (+8)")
        elif insider_hold and insider_hold > 0.05:
            smart_score += 5
            smart_details.append(f"Insiders: {insider_hold*100:.1f}% (+5)")

        forward_pe = info.get("forwardPE")
        trailing_pe = info.get("trailingPE")
        if forward_pe and trailing_pe and forward_pe > 0 and trailing_pe > 0:
            pe_ratio = forward_pe / trailing_pe
            if pe_ratio < 0.8:
                smart_score += 8
                smart_details.append("Forward PE < Trailing PE (+8)")
            elif pe_ratio > 1.3:
                smart_score -= 8
                smart_details.append("Forward PE > Trailing PE (-8)")

        smart_score = max(0, min(100, smart_score))
        result["scores"]["smart_money"] = smart_score
        result["details"]["smart_money"] = smart_details

        # SCORE GLOBAL
        global_score = (
            result["scores"]["technical"] * 0.30
            + result["scores"]["fundamental"] * 0.30
            + result["scores"]["sentiment"] * 0.20
            + result["scores"]["smart_money"] * 0.20
        )
        result["scores"]["global"] = global_score

        if global_score >= 78:
            result["recommendation"] = "ACHAT FORT"
        elif global_score >= 62:
            result["recommendation"] = "ACHAT"
        elif global_score >= 42:
            result["recommendation"] = "CONSERVER"
        elif global_score >= 30:
            result["recommendation"] = "VENDRE"
        else:
            result["recommendation"] = "VENTE FORTE"

        return result

    except Exception as e:
        import traceback
        traceback.print_exc()
        return None


def print_result(r):
    if not r:
        print("ERREUR: scoring a retourne None")
        return
    print(f"Nom: {r['name']}")
    print(f"Prix: {r['price']} {r['currency']}")
    print(f"Secteur: {r['sector']}")
    print()
    print("=== SCORES ===")
    print(f"Technique:   {r['scores']['technical']:.1f}/100")
    print(f"Fondamental: {r['scores']['fundamental']:.1f}/100")
    print(f"Sentiment:   {r['scores']['sentiment']:.1f}/100")
    print(f"Smart Money: {r['scores']['smart_money']:.1f}/100")
    print("-" * 30)
    print(f"GLOBAL:      {r['scores']['global']:.1f}/100")
    print(f">>> RECOMMANDATION: {r['recommendation']} <<<")
    print()
    print("=== DETAILS ===")
    for cat in ["technical", "fundamental", "sentiment", "smart_money"]:
        print(f"--- {cat.upper()} ---")
        for d in r["details"][cat]:
            print(f"  {d}")


if __name__ == "__main__":
    tickers = ["TTE.PA", "AAPL", "AI.PA"]
    for t in tickers:
        print("=" * 60)
        print(f"TEST {t}")
        print("=" * 60)
        r = calculate_full_score(t)
        print_result(r)
        print()
