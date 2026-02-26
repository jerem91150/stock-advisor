# Roadmap - Stock Advisor v4.0

## Ce qu'on a (v4.0) ✅

### Core Features
- [x] 593 actions de 17 indices mondiaux
- [x] Multi-portefeuilles (PEA, CTO, AV, PER, Crypto)
- [x] Scoring 4 composantes (Tech/Fond/Sent/Smart)
- [x] Scores Moning (Dividende, Croissance, Fair Value)
- [x] Monte Carlo 5000 simulations
- [x] Calculateur FIRE
- [x] Tracker dividendes
- [x] ETF Screener + Comparateur
- [x] Analyse IA (Ollama)
- [x] Score diversification

### Nouvelles fonctionnalités v4.0 ✅
- [x] **Import CSV** - Degiro, Boursorama, Trade Republic, Interactive Brokers
- [x] **Alertes** - Prix, dividendes, scores, notifications email/webhook
- [x] **Benchmark** - S&P 500, CAC 40, MSCI World, Alpha/Beta
- [x] **Rapports PDF** - Mensuel, synthèse, dividendes, fiscal
- [x] **Immobilier** - Biens, crédits, rendement, cash-flow
- [x] **Objectifs d'épargne** - Tracker, projections, suggestions
- [x] **Transactions récurrentes (DCA)** - Planification, exécution, suivi
- [x] **Multi-devises** - Conversion EUR/USD/GBP/CHF, impact change

---

## 🟡 PRIORITÉ MOYENNE - À venir

### 1. Dark Mode
```
- Thème sombre complet
- Sauvegarde préférence
- Mode auto (système)
```
**Effort:** Faible | **Impact:** Moyen

### 2. Watchlists avancées
```
- Plusieurs watchlists nommées
- Alertes par watchlist
- Notes personnelles
- Tri et filtres avancés
```
**Effort:** Faible | **Impact:** Moyen

### 3. Optimisation fiscale
```
- Suivi plus/moins-values
- Suggestions Tax-Loss Harvesting
- Simulation impôts (PFU vs IR)
- Export pour déclaration
```
**Effort:** Élevé | **Impact:** Fort

### 4. Rééquilibrage automatique
```
- Définir allocation cible
- Détecter les dérives
- Suggérer les trades
- Simulation rééquilibrage
```
**Effort:** Moyen | **Impact:** Moyen

### 5. News Feed intégré
```
- Actualités par position
- Sentiment des news
- Alertes breaking news
- Sources multiples
```
**Effort:** Moyen | **Impact:** Moyen

### 6. PWA / Mobile
```
- Progressive Web App
- Installation sur mobile
- Mode hors-ligne
- Notifications push
```
**Effort:** Élevé | **Impact:** Fort

### 7. Partage social
```
- Partager portefeuille (anonymisé)
- Classement communauté
- Copier les portefeuilles
```
**Effort:** Élevé | **Impact:** Moyen

---

## Comparaison avec la concurrence (Mise à jour v4.0)

| Fonctionnalité | Stock Advisor v4.0 | Moning | Finary | Yahoo Finance |
|----------------|:------------------:|:------:|:------:|:-------------:|
| **Gratuit** | ✅ | ❌ | ❌ | ✅ |
| **100% local** | ✅ | ❌ | ❌ | ❌ |
| **IA intégrée** | ✅ | ❌ | ❌ | ❌ |
| **593 actions** | ✅ | ✅ | ✅ | ✅ |
| **Multi-portefeuilles** | ✅ | ✅ | ✅ | ❌ |
| **Monte Carlo** | ✅ | ❌ | ✅ | ❌ |
| **FIRE Calculator** | ✅ | ❌ | ✅ | ❌ |
| **Scores Moning** | ✅ | ✅ | ❌ | ❌ |
| **Import CSV** | ✅ | ❌ | ✅ | ❌ |
| **Alertes** | ✅ | ✅ | ✅ | ✅ |
| **Immobilier** | ✅ | ❌ | ✅ | ❌ |
| **Rapports PDF** | ✅ | ✅ | ✅ | ❌ |
| **Benchmark** | ✅ | ❌ | ✅ | ✅ |
| **Objectifs épargne** | ✅ | ❌ | ✅ | ❌ |
| **DCA automatique** | ✅ | ❌ | ❌ | ❌ |
| **Multi-devises** | ✅ | ❌ | ✅ | ✅ |
| **Connexion banque** | ❌ | ❌ | ✅ | ❌ |
| **App mobile** | 🔜 | ❌ | ✅ | ✅ |

---

## Architecture des modules v4.0

```
stock-advisor/python/src/
├── alerts/
│   ├── __init__.py
│   └── manager.py           # Système d'alertes complet
├── analysis/
│   ├── benchmark.py         # Comparaison vs indices ✅ NEW
│   ├── moning_scores.py     # Scores style Moning
│   ├── projections.py       # Monte Carlo & FIRE
│   ├── etf_analyzer.py      # Screener ETF
│   └── ai_advisor.py        # Analyse IA Ollama
├── currency/
│   ├── __init__.py
│   └── currency_manager.py  # Multi-devises ✅ NEW
├── data/
│   └── stock_universe.py    # 593 actions
├── goals/
│   ├── __init__.py
│   └── savings_goals.py     # Objectifs épargne ✅ NEW
├── import_export/
│   ├── __init__.py
│   └── csv_importer.py      # Import CSV multi-broker ✅ NEW
├── portfolio/
│   ├── manager.py           # Gestion portefeuilles
│   ├── dividend_tracker.py  # Suivi dividendes
│   └── recurring_transactions.py  # DCA ✅ NEW
├── real_estate/
│   ├── __init__.py
│   └── property_manager.py  # Gestion immobilier ✅ NEW
└── reports/
    ├── __init__.py
    └── pdf_generator.py     # Rapports PDF ✅ NEW
```

---

## Statistiques du projet

- **Actions couvertes:** 593 (17 indices)
- **Régions:** USA, Europe, Asie, Océanie
- **Modules Python:** 15+
- **Lignes de code:** ~10,000+
- **Tests:** Unitaires et intégration

---

## Conclusion

Stock Advisor v4.0 est maintenant **LA** solution la plus complète pour le suivi de patrimoine:

✅ **100% gratuit et local** - Vos données restent chez vous
✅ **IA intégrée** - Analyse avec Ollama (LLM local)
✅ **Multi-assets** - Actions, ETF, Crypto, Immobilier
✅ **Import automatique** - Plus besoin de saisie manuelle
✅ **Rapports pro** - PDF exportables
✅ **Objectifs** - Planification financière complète

Seules fonctionnalités manquantes par rapport à Finary:
- Connexion bancaire automatique (impossible sans agrégateur payant)
- Application mobile native (PWA prévu)
