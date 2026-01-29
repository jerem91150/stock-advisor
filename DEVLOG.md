# Journal de Développement - Stock Advisor

## 📋 Résumé du Projet
Outil d'aide à la décision pour l'achat d'actions sur PEA et CTO combinant analyse technique, fondamentale, sentiment analysis et tracking des grands investisseurs.

---

## 2025-01-29 - Initialisation du Projet et MVP

### ✅ Phase 1 : Setup Initial (Complété)

#### 1.1 Initialisation du projet
- [x] Création de la structure de dossiers complète
- [x] Initialisation du repository Git
- [x] Création du fichier `.gitignore`
- [x] Création du fichier `requirements.txt` avec toutes les dépendances
- [x] Création du fichier `DEVLOG.md`
- [x] Création du fichier `README.md`
- [x] Création du fichier de configuration `config/config.yaml`

### ✅ Phase 2 : MVP (En cours)

#### 2.1 Détection Hardware (Complété)
- [x] Module `python/src/hardware/detector.py`
  - Détection GPU NVIDIA (via nvidia-smi)
  - Détection GPU AMD (via rocm-smi / WMI)
  - Détection GPU Intel
  - Lecture VRAM disponible
  - Recommandation modèle LLM adapté au hardware
  - Vérification installation Ollama
  - Génération de rapport complet

#### 2.2 Base de Données (Complété)
- [x] Module `python/src/database/models.py`
  - Modèle Stock (actions)
  - Modèle PriceHistory (historique des prix)
  - Modèle Fundamentals (données fondamentales)
  - Modèle Score (scores calculés)
  - Modèle Watchlist / WatchlistItem
  - Modèle Filter (filtres sauvegardés)
  - Modèle GuruPosition (positions 13F)
  - Modèle NewsArticle (articles pour sentiment)
  - Modèle SocialMention (mentions réseaux sociaux)
  - Modèle Catalyst (événements/catalyseurs)
  - Modèle IndexConstituent (composition indices)

#### 2.3 Scraping Données Financières (Complété)
- [x] Module `python/src/scrapers/yahoo_finance.py`
  - Récupération infos stock (prix, volumes, secteur, etc.)
  - Récupération données fondamentales
  - Historique des prix
  - Dividendes et calendrier earnings
  - Vérification éligibilité PEA
  - Résumé du marché (indices)
  - Référentiel CAC40 et S&P500 (partiel)

#### 2.4 Analyse Technique (Complété)
- [x] Module `python/src/analysis/technical.py`
  - SMA (20, 50, 200)
  - EMA
  - RSI (14)
  - MACD (12, 26, 9)
  - Bandes de Bollinger
  - ATR (volatilité)
  - Support/Résistance
  - Score technique (0-100)
  - Signaux détaillés

#### 2.5 Analyse Fondamentale (Complété)
- [x] Module `python/src/analysis/fundamental.py`
  - Valorisation (P/E, PEG, P/B, EV/EBITDA)
  - Rentabilité (ROE, ROA, marges)
  - Croissance (CA, bénéfices)
  - Santé financière (dette, current ratio)
  - Dividendes
  - Seuils ajustables par secteur
  - Score fondamental (0-100)

#### 2.6 Système de Filtres (Complété)
- [x] Module `python/src/filters/base.py`
  - Filtre sectoriel (tabac, armement, etc.)
  - Filtre éthique (ESG simplifié)
  - Filtre fondamental (P/E max, dette max, etc.)
  - Filtre géographique (PEA only, pays exclus)
  - Filtre actionnariat (État, fonds souverains)
  - FilterManager pour combiner les filtres

#### 2.7 Interface Streamlit MVP (Complété)
- [x] Module `python/ui/app.py`
  - Dashboard avec résumé du marché
  - Recherche d'actions
  - Analyse complète (scores, graphiques)
  - Graphique candlestick avec MAs
  - Gauge charts pour scores
  - Badge PEA/CTO
  - Page configuration filtres
  - Page hardware/LLM
  - Page À propos

#### 2.8 API FastAPI (Complété)
- [x] Module `python/src/api/main.py`
  - GET /stock/{ticker} - Infos action
  - GET /stock/{ticker}/fundamentals - Fondamentaux
  - GET /stock/{ticker}/technical - Analyse technique
  - GET /stock/{ticker}/fundamental-analysis - Score fondamental
  - GET /stock/{ticker}/full-analysis - Analyse complète
  - GET /market/summary - Résumé du marché
  - GET /market/indices/{name} - Constituants indice
  - GET /hardware - Infos hardware
  - POST /filters/apply - Appliquer filtres

### ✅ Composants Rust (Complété)

#### Scraper Finviz haute performance
- [x] `rust/Cargo.toml` - Configuration projet
- [x] `rust/src/lib.rs` - Point d'entrée bibliothèque
- [x] `rust/src/scraper/mod.rs` - Module scraping
- [x] `rust/src/scraper/finviz.rs` - Scraper Finviz
  - Scraping concurrent avec rate limiting
  - Parsing complet des données stock
  - CLI pour utilisation standalone
- [x] `rust/src/parser/mod.rs` - Utilitaires parsing

---

## Structure Finale du Projet

```
stock-advisor/
├── python/
│   ├── src/
│   │   ├── scrapers/
│   │   │   └── yahoo_finance.py     ✅
│   │   ├── analysis/
│   │   │   ├── technical.py         ✅
│   │   │   └── fundamental.py       ✅
│   │   ├── sentiment/               (Phase 3)
│   │   ├── smart_money/             (Phase 4)
│   │   ├── filters/
│   │   │   └── base.py              ✅
│   │   ├── database/
│   │   │   └── models.py            ✅
│   │   ├── hardware/
│   │   │   └── detector.py          ✅
│   │   └── api/
│   │       └── main.py              ✅
│   ├── ui/
│   │   └── app.py                   ✅
│   └── tests/
├── rust/
│   ├── src/
│   │   ├── lib.rs                   ✅
│   │   ├── scraper/
│   │   │   ├── mod.rs               ✅
│   │   │   └── finviz.rs            ✅
│   │   ├── parser/
│   │   │   └── mod.rs               ✅
│   │   └── bin/
│   │       └── finviz_scraper.rs    ✅
│   └── Cargo.toml                   ✅
├── data/
├── config/
│   └── config.yaml                  ✅
├── docs/
├── DEVLOG.md                        ✅
├── README.md                        ✅
├── requirements.txt                 ✅
└── .gitignore                       ✅
```

---

## 🔧 Prochaines Étapes

### Phase 3 : Sentiment Analysis
- [ ] Scraping Google News
- [ ] Intégration Reddit API (r/stocks, r/vosfinances)
- [ ] Intégration Stocktwits
- [ ] Google Trends
- [ ] Intégration Ollama pour analyse sentiment
- [ ] Score Sentiment (25%)

### Phase 4 : Smart Money
- [ ] Parsing 13F (SEC EDGAR)
- [ ] Scraping DataRoma
- [ ] YouTube transcripts (yt-dlp)
- [ ] Score Smart Money (25%)

### Phase 5 : Gouvernance & Actionnariat
- [ ] AMF BDIF
- [ ] Pappers.fr / Societe.com

### Phase 6 : Fonctionnalités Avancées
- [ ] Watchlists
- [ ] Calendrier catalyseurs
- [ ] Backtest des recommandations

---

## Notes Techniques

### Architecture Hybride
- **Python** : Application principale (Streamlit, FastAPI, Ollama)
- **Rust** : Composants haute performance (scraping concurrent Finviz)

### Règles de Développement
1. Commits réguliers en français
2. Pas d'API payante - tout en scraping gratuit
3. LLM local via Ollama
4. Tests unitaires pour chaque module

### Système de Scoring
| Composant | Pondération | Status |
|-----------|-------------|--------|
| Technique | 25% | ✅ Implémenté |
| Fondamental | 25% | ✅ Implémenté |
| Sentiment | 25% | ⏳ Phase 3 |
| Smart Money | 25% | ⏳ Phase 4 |

---

## Commandes Utiles

### Lancer l'interface Streamlit
```bash
cd python
streamlit run ui/app.py
```

### Lancer l'API FastAPI
```bash
cd python
uvicorn src.api.main:app --reload
```

### Compiler les composants Rust
```bash
cd rust
cargo build --release
```

### Utiliser le CLI Finviz (après compilation)
```bash
./target/release/finviz-scraper stock AAPL MSFT
./target/release/finviz-scraper screen --sector technology
```
