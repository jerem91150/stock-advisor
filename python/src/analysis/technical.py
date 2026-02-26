"""
Analyse Technique - Calcul d'indicateurs et scoring
"""

from dataclasses import dataclass
from typing import Optional
import pandas as pd
import numpy as np
from loguru import logger


@dataclass
class TechnicalSignal:
    """Signal technique individuel."""
    name: str
    value: float
    signal: str  # "bullish", "bearish", "neutral"
    weight: float
    description: str
    score: Optional[float] = None  # Score gradue 0-100


@dataclass
class TechnicalAnalysis:
    """Résultat complet de l'analyse technique."""
    ticker: str
    score: float  # 0-100
    signals: list[TechnicalSignal]
    trend: str  # "uptrend", "downtrend", "sideways"
    momentum: str  # "strong", "moderate", "weak"
    volatility: float


class TechnicalAnalyzer:
    """Analyseur technique pour les actions."""

    def __init__(self):
        # Pondérations des indicateurs
        self.weights = {
            "ma_crossover": 0.20,      # Croisement moyennes mobiles
            "price_vs_ma": 0.15,       # Prix vs MA50/MA200
            "rsi": 0.15,               # RSI
            "macd": 0.15,              # MACD
            "volume": 0.10,            # Volume
            "bollinger": 0.10,         # Bandes de Bollinger
            "support_resistance": 0.10, # Support/Résistance
            "atr": 0.05                # ATR (volatilité)
        }

    def calculate_sma(self, prices: pd.Series, period: int) -> pd.Series:
        """Calcule la moyenne mobile simple."""
        return prices.rolling(window=period).mean()

    def calculate_ema(self, prices: pd.Series, period: int) -> pd.Series:
        """Calcule la moyenne mobile exponentielle."""
        return prices.ewm(span=period, adjust=False).mean()

    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """
        Calcule le RSI (Relative Strength Index).

        RSI = 100 - (100 / (1 + RS))
        RS = Average Gain / Average Loss
        """
        delta = prices.diff()

        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss.replace(0, np.inf)
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def calculate_macd(
        self,
        prices: pd.Series,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calcule le MACD (Moving Average Convergence Divergence).

        Returns:
            (macd_line, signal_line, histogram)
        """
        ema_fast = self.calculate_ema(prices, fast_period)
        ema_slow = self.calculate_ema(prices, slow_period)

        macd_line = ema_fast - ema_slow
        signal_line = self.calculate_ema(macd_line, signal_period)
        histogram = macd_line - signal_line

        return macd_line, signal_line, histogram

    def calculate_bollinger_bands(
        self,
        prices: pd.Series,
        period: int = 20,
        std_dev: float = 2.0
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calcule les bandes de Bollinger.

        Returns:
            (upper_band, middle_band, lower_band)
        """
        middle_band = self.calculate_sma(prices, period)
        std = prices.rolling(window=period).std()

        upper_band = middle_band + (std_dev * std)
        lower_band = middle_band - (std_dev * std)

        return upper_band, middle_band, lower_band

    def calculate_atr(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """
        Calcule l'ATR (Average True Range).

        Mesure de volatilité.
        """
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        return atr

    def identify_support_resistance(
        self,
        prices: pd.Series,
        window: int = 20
    ) -> tuple[float, float]:
        """
        Identifie les niveaux de support et résistance récents.

        Returns:
            (support, resistance)
        """
        recent_prices = prices.tail(window)
        support = recent_prices.min()
        resistance = recent_prices.max()

        return support, resistance

    def analyze(self, df: pd.DataFrame, ticker: str = "") -> Optional[TechnicalAnalysis]:
        """
        Analyse technique complète d'une action.

        Args:
            df: DataFrame avec colonnes Open, High, Low, Close, Volume
            ticker: Symbole de l'action

        Returns:
            TechnicalAnalysis avec score et signaux
        """
        if df is None or len(df) < 200:
            logger.warning(f"Données insuffisantes pour {ticker} (min 200 jours)")
            return None

        try:
            close = df['Close']
            high = df['High']
            low = df['Low']
            volume = df['Volume']

            signals = []
            current_price = close.iloc[-1]

            # 1. Moyennes Mobiles
            ma20 = self.calculate_sma(close, 20)
            ma50 = self.calculate_sma(close, 50)
            ma200 = self.calculate_sma(close, 200)

            # Signal croisement MA50/MA200 (Golden Cross / Death Cross)
            ma_crossover_signal = self._analyze_ma_crossover(ma50, ma200)
            signals.append(ma_crossover_signal)

            # Signal prix vs MAs
            price_vs_ma_signal = self._analyze_price_vs_ma(current_price, ma50.iloc[-1], ma200.iloc[-1])
            signals.append(price_vs_ma_signal)

            # 2. RSI
            rsi = self.calculate_rsi(close)
            rsi_signal = self._analyze_rsi(rsi.iloc[-1])
            signals.append(rsi_signal)

            # 3. MACD
            macd_line, signal_line, histogram = self.calculate_macd(close)
            macd_signal = self._analyze_macd(macd_line.iloc[-1], signal_line.iloc[-1], histogram.iloc[-1])
            signals.append(macd_signal)

            # 4. Volume
            volume_signal = self._analyze_volume(volume)
            signals.append(volume_signal)

            # 5. Bandes de Bollinger
            upper, middle, lower = self.calculate_bollinger_bands(close)
            bollinger_signal = self._analyze_bollinger(current_price, upper.iloc[-1], middle.iloc[-1], lower.iloc[-1])
            signals.append(bollinger_signal)

            # 6. Support/Résistance
            support, resistance = self.identify_support_resistance(close)
            sr_signal = self._analyze_support_resistance(current_price, support, resistance)
            signals.append(sr_signal)

            # 7. ATR (volatilité)
            atr = self.calculate_atr(high, low, close)
            atr_signal = self._analyze_atr(atr.iloc[-1], current_price)
            signals.append(atr_signal)

            # Calcul du score global
            score = self._calculate_score(signals)

            # Déterminer la tendance
            trend = self._determine_trend(current_price, ma50.iloc[-1], ma200.iloc[-1])

            # Déterminer le momentum
            momentum = self._determine_momentum(rsi.iloc[-1], histogram.iloc[-1])

            # Volatilité normalisée
            volatility = (atr.iloc[-1] / current_price) * 100

            return TechnicalAnalysis(
                ticker=ticker,
                score=score,
                signals=signals,
                trend=trend,
                momentum=momentum,
                volatility=volatility
            )

        except Exception as e:
            logger.error(f"Erreur analyse technique {ticker}: {e}")
            return None

    def _analyze_ma_crossover(self, ma50: pd.Series, ma200: pd.Series) -> TechnicalSignal:
        """Analyse le croisement des moyennes mobiles."""
        current_diff = ma50.iloc[-1] - ma200.iloc[-1]
        previous_diff = ma50.iloc[-2] - ma200.iloc[-2] if len(ma50) > 1 else current_diff

        if current_diff > 0 and previous_diff <= 0:
            signal = "bullish"
            score = 85
            description = "Golden Cross (MA50 croise MA200 a la hausse)"
        elif current_diff < 0 and previous_diff >= 0:
            signal = "bearish"
            score = 15
            description = "Death Cross (MA50 croise MA200 a la baisse)"
        elif current_diff > 0:
            signal = "bullish"
            # Score gradue selon l'ecart MA50/MA200
            pct_diff = (current_diff / ma200.iloc[-1]) * 100 if ma200.iloc[-1] != 0 else 0
            score = min(80, 60 + pct_diff * 2)
            description = "MA50 au-dessus de MA200 (tendance haussiere)"
        else:
            signal = "bearish"
            pct_diff = (current_diff / ma200.iloc[-1]) * 100 if ma200.iloc[-1] != 0 else 0
            score = max(20, 40 + pct_diff * 2)
            description = "MA50 en-dessous de MA200 (tendance baissiere)"

        return TechnicalSignal(
            name="ma_crossover",
            value=current_diff,
            signal=signal,
            weight=self.weights["ma_crossover"],
            description=description,
            score=score
        )

    def _analyze_price_vs_ma(self, price: float, ma50: float, ma200: float) -> TechnicalSignal:
        """Analyse la position du prix par rapport aux moyennes mobiles."""
        above_ma50 = price > ma50
        above_ma200 = price > ma200

        pct_from_ma200 = ((price - ma200) / ma200) * 100 if ma200 != 0 else 0

        if above_ma50 and above_ma200:
            # Penaliser si trop etire au-dessus de MA200
            if pct_from_ma200 > 30:
                signal = "bearish"
                score = 30
                description = f"Prix trop etire au-dessus des MAs (+{pct_from_ma200:.0f}% vs MA200)"
            elif pct_from_ma200 > 20:
                signal = "neutral"
                score = 50
                description = f"Prix etire au-dessus des MAs (+{pct_from_ma200:.0f}% vs MA200)"
            else:
                signal = "bullish"
                score = 70 + min(10, pct_from_ma200 * 0.5)
                description = "Prix au-dessus de MA50 et MA200"
        elif above_ma200:
            signal = "neutral"
            score = 50
            description = "Prix entre MA50 et MA200"
        else:
            signal = "bearish"
            score = max(5, 35 + pct_from_ma200 * 0.5)
            description = "Prix en-dessous de MA50 et MA200"

        return TechnicalSignal(
            name="price_vs_ma",
            value=pct_from_ma200,
            signal=signal,
            weight=self.weights["price_vs_ma"],
            description=description,
            score=score
        )

    def _analyze_rsi(self, rsi: float) -> TechnicalSignal:
        """Analyse le RSI avec scoring gradue continu."""
        # Score gradue: RSI 20->95, 30->90, 50->55, 65->40, 70->25, 80->10
        score = float(np.interp(rsi, [15, 25, 30, 50, 65, 70, 80, 90], [98, 92, 85, 55, 40, 25, 10, 2]))

        if rsi >= 80:
            signal = "bearish"
            description = f"RSI en forte zone de surachat ({rsi:.1f})"
        elif rsi >= 70:
            signal = "bearish"
            description = f"RSI en zone de surachat ({rsi:.1f})"
        elif rsi <= 25:
            signal = "bullish"
            description = f"RSI en forte zone de survente ({rsi:.1f})"
        elif rsi <= 30:
            signal = "bullish"
            description = f"RSI en zone de survente ({rsi:.1f})"
        elif rsi >= 55:
            signal = "neutral"
            description = f"RSI neutre-haut ({rsi:.1f})"
        elif rsi >= 45:
            signal = "neutral"
            description = f"RSI neutre ({rsi:.1f})"
        else:
            signal = "neutral"
            description = f"RSI neutre-bas ({rsi:.1f})"

        return TechnicalSignal(
            name="rsi",
            value=rsi,
            signal=signal,
            weight=self.weights["rsi"],
            description=description,
            score=score
        )

    def _analyze_macd(self, macd: float, signal: float, histogram: float) -> TechnicalSignal:
        """Analyse le MACD avec scoring gradue."""
        if histogram > 0 and macd > signal:
            sig = "bullish"
            # Plus l'histogramme est grand, plus le signal est fort
            score = min(85, 65 + abs(histogram) * 100)
            description = "MACD au-dessus de la ligne de signal"
        elif histogram < 0 and macd < signal:
            sig = "bearish"
            score = max(15, 35 - abs(histogram) * 100)
            description = "MACD en-dessous de la ligne de signal"
        else:
            sig = "neutral"
            score = 50
            description = "MACD en transition"

        return TechnicalSignal(
            name="macd",
            value=histogram,
            signal=sig,
            weight=self.weights["macd"],
            description=description,
            score=score
        )

    def _analyze_volume(self, volume: pd.Series) -> TechnicalSignal:
        """Analyse le volume avec scoring gradue."""
        avg_volume = volume.rolling(window=20).mean().iloc[-1]
        current_volume = volume.iloc[-1]
        ratio = current_volume / avg_volume if avg_volume > 0 else 1

        # Score gradue selon le ratio de volume
        score = float(np.interp(ratio, [0.3, 0.5, 0.8, 1.2, 1.5, 2.5], [25, 35, 45, 55, 65, 80]))

        if ratio > 1.5:
            signal = "bullish"
            description = f"Volume eleve ({ratio:.1f}x moyenne)"
        elif ratio < 0.5:
            signal = "bearish"
            description = f"Volume faible ({ratio:.1f}x moyenne)"
        else:
            signal = "neutral"
            description = f"Volume normal ({ratio:.1f}x moyenne)"

        return TechnicalSignal(
            name="volume",
            value=ratio,
            signal=signal,
            weight=self.weights["volume"],
            description=description,
            score=score
        )

    def _analyze_bollinger(
        self,
        price: float,
        upper: float,
        middle: float,
        lower: float
    ) -> TechnicalSignal:
        """Analyse les bandes de Bollinger avec scoring gradue."""
        # Position relative dans les bandes (0 = lower, 1 = upper)
        band_position = (price - lower) / (upper - lower) if upper != lower else 0.5

        # Score gradue selon la position dans les bandes
        # Proche de lower = bullish (score eleve), proche de upper = bearish (score bas)
        score = float(np.interp(band_position, [0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0, 1.1],
                                               [90, 80, 65, 50, 35, 20, 10, 5]))

        if price >= upper:
            signal = "bearish"
            description = "Prix au-dessus de la bande superieure (surachat)"
        elif price <= lower:
            signal = "bullish"
            description = "Prix en-dessous de la bande inferieure (survente)"
        elif band_position > 0.7:
            signal = "bearish"
            description = "Prix dans la partie haute des bandes"
        elif band_position < 0.3:
            signal = "bullish"
            description = "Prix dans la partie basse des bandes"
        else:
            signal = "neutral"
            description = "Prix au milieu des bandes"

        return TechnicalSignal(
            name="bollinger",
            value=band_position,
            signal=signal,
            weight=self.weights["bollinger"],
            description=description,
            score=score
        )

    def _analyze_support_resistance(
        self,
        price: float,
        support: float,
        resistance: float
    ) -> TechnicalSignal:
        """Analyse par rapport aux supports/resistances avec scoring gradue."""
        range_size = resistance - support
        position = (price - support) / range_size if range_size > 0 else 0.5

        # Score gradue: proche du support = bullish (score eleve)
        score = float(np.interp(position, [0.0, 0.2, 0.5, 0.8, 1.0], [85, 70, 50, 30, 15]))

        if position >= 0.8:
            signal = "bearish"
            description = "Prix proche de la resistance"
        elif position <= 0.2:
            signal = "bullish"
            description = "Prix proche du support"
        elif position > 0.6:
            signal = "bearish"
            description = "Prix dans la moitie haute du range"
        elif position < 0.4:
            signal = "bullish"
            description = "Prix dans la moitie basse du range"
        else:
            signal = "neutral"
            description = "Prix au milieu du range"

        return TechnicalSignal(
            name="support_resistance",
            value=position,
            signal=signal,
            weight=self.weights["support_resistance"],
            description=description,
            score=score
        )

    def _analyze_atr(self, atr: float, price: float) -> TechnicalSignal:
        """Analyse l'ATR (volatilite)."""
        atr_percent = (atr / price) * 100

        # Volatilite elevee = leger malus, faible = neutre, normale = neutre
        if atr_percent > 4:
            signal = "bearish"
            score = 35
            description = f"Volatilite tres elevee ({atr_percent:.1f}%)"
        elif atr_percent > 3:
            signal = "neutral"
            score = 42
            description = f"Volatilite elevee ({atr_percent:.1f}%)"
        elif atr_percent < 1:
            signal = "neutral"
            score = 50
            description = f"Volatilite faible ({atr_percent:.1f}%)"
        else:
            signal = "neutral"
            score = 50
            description = f"Volatilite normale ({atr_percent:.1f}%)"

        return TechnicalSignal(
            name="atr",
            value=atr_percent,
            signal=signal,
            weight=self.weights["atr"],
            description=description,
            score=score
        )

    def _calculate_score(self, signals: list[TechnicalSignal]) -> float:
        """Calcule le score global (0-100) en utilisant les scores gradues."""
        total_weight = sum(s.weight for s in signals)
        weighted_score = 0

        for signal in signals:
            # Utiliser le score gradue si disponible, sinon fallback binaire
            if signal.score is not None:
                s_score = signal.score
            elif signal.signal == "bullish":
                s_score = 75
            elif signal.signal == "bearish":
                s_score = 25
            else:
                s_score = 50

            weighted_score += s_score * (signal.weight / total_weight)

        return round(max(0, min(100, weighted_score)), 2)

    def _determine_trend(self, price: float, ma50: float, ma200: float) -> str:
        """Détermine la tendance générale."""
        if price > ma50 > ma200:
            return "uptrend"
        elif price < ma50 < ma200:
            return "downtrend"
        else:
            return "sideways"

    def _determine_momentum(self, rsi: float, macd_histogram: float) -> str:
        """Détermine la force du momentum."""
        if (rsi > 60 and macd_histogram > 0) or (rsi < 40 and macd_histogram < 0):
            return "strong"
        elif 40 <= rsi <= 60:
            return "weak"
        else:
            return "moderate"


# Instance singleton
analyzer = TechnicalAnalyzer()


def main():
    """Test de l'analyseur technique."""
    from ..scrapers.yahoo_finance import scraper

    ticker = "AAPL"
    print(f"=== Analyse Technique {ticker} ===")

    # Récupérer l'historique
    df = scraper.get_price_history(ticker, period="1y")

    if df is not None:
        analysis = analyzer.analyze(df, ticker)

        if analysis:
            print(f"\nScore: {analysis.score}/100")
            print(f"Tendance: {analysis.trend}")
            print(f"Momentum: {analysis.momentum}")
            print(f"Volatilité: {analysis.volatility:.2f}%")

            print("\n--- Signaux ---")
            for signal in analysis.signals:
                emoji = "🟢" if signal.signal == "bullish" else "🔴" if signal.signal == "bearish" else "🟡"
                print(f"{emoji} {signal.name}: {signal.description}")


if __name__ == "__main__":
    main()
