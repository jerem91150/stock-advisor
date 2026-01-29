# Stock Advisor 📈

Outil d'aide à la décision pour l'achat d'actions sur PEA et CTO.

## 🎯 Fonctionnalités

- **Analyse Technique** : MM50/200, RSI, MACD, volumes
- **Analyse Fondamentale** : PER, PEG, ROE, dette/EBITDA
- **Sentiment Analysis** : News, Reddit, réseaux sociaux (via LLM local)
- **Smart Money Tracking** : Suivi des positions des grands investisseurs (13F)
- **Filtres Personnalisables** : Sectoriels, éthiques, fondamentaux
- **Éligibilité PEA/CTO** : Badge automatique

## 🏗️ Architecture

Architecture hybride **Python + Rust** :

- **Python** : Interface Streamlit, API FastAPI, intégration Ollama
- **Rust** : Scraping concurrent haute performance

## 📦 Installation

### Prérequis

- Python 3.11+
- Rust (stable)
- Ollama (pour LLM local)

### Installation Python

```bash
cd stock-advisor
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
.\venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

### Installation Rust

```bash
cd rust
cargo build --release
```

## 🚀 Utilisation

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

## 📊 Système de Scoring

Le score global (0-100) est calculé selon :

| Composant | Pondération |
|-----------|-------------|
| Technique | 25% |
| Fondamental | 25% |
| Sentiment | 25% |
| Smart Money | 25% |

## 📁 Structure du Projet

```
stock-advisor/
├── python/           # Application principale
│   ├── src/
│   │   ├── scrapers/     # Scrapers Python
│   │   ├── analysis/     # Analyse technique/fondamentale
│   │   ├── sentiment/    # Analyse sentiment (LLM)
│   │   ├── smart_money/  # Tracking gourous
│   │   ├── filters/      # Filtres personnalisables
│   │   ├── database/     # Modèles SQLAlchemy
│   │   ├── hardware/     # Détection GPU
│   │   └── api/          # FastAPI
│   └── ui/               # Interface Streamlit
├── rust/             # Composants haute performance
│   └── src/
│       ├── scraper/      # Scraping concurrent
│       └── parser/       # Parsing rapide
├── data/             # Données locales
├── config/           # Configuration
└── docs/             # Documentation
```

## 📝 Licence

MIT

## 🤝 Contribution

Voir `CONTRIBUTING.md` pour les guidelines de contribution.
