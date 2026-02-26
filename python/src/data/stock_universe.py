"""
Univers d'actions mondial - Stock Advisor v3.0
Contient les constituants des principaux indices mondiaux
"""

# =============================================================================
# S&P 500 - USA (Top 100 par capitalisation)
# =============================================================================
SP500_TOP100 = [
    # Technology
    'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'NVDA', 'META', 'TSLA', 'AVGO', 'ORCL',
    'ADBE', 'CRM', 'CSCO', 'ACN', 'IBM', 'INTC', 'AMD', 'QCOM', 'TXN', 'NOW',
    'INTU', 'AMAT', 'ADI', 'LRCX', 'MU', 'KLAC', 'SNPS', 'CDNS', 'MRVL', 'FTNT',

    # Financial
    'BRK-B', 'JPM', 'V', 'MA', 'BAC', 'WFC', 'GS', 'MS', 'SPGI', 'BLK',
    'C', 'AXP', 'SCHW', 'CB', 'MMC', 'PGR', 'AON', 'ICE', 'CME', 'MCO',

    # Healthcare
    'UNH', 'JNJ', 'LLY', 'PFE', 'ABBV', 'MRK', 'TMO', 'ABT', 'DHR', 'BMY',
    'AMGN', 'MDT', 'ISRG', 'GILD', 'VRTX', 'REGN', 'SYK', 'BSX', 'ZTS', 'BDX',

    # Consumer
    'WMT', 'PG', 'KO', 'PEP', 'COST', 'HD', 'MCD', 'NKE', 'SBUX', 'TGT',
    'LOW', 'EL', 'CL', 'MDLZ', 'GIS', 'KHC', 'KMB', 'HSY', 'K', 'CAG',

    # Industrial
    'CAT', 'DE', 'UNP', 'HON', 'UPS', 'BA', 'RTX', 'LMT', 'GE', 'MMM',
    'EMR', 'ITW', 'ETN', 'PH', 'ROK', 'CMI', 'IR', 'PCAR', 'FAST', 'GD',

    # Energy
    'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'PSX', 'VLO', 'OXY', 'KMI',

    # Communication
    'DIS', 'NFLX', 'CMCSA', 'T', 'VZ', 'TMUS', 'CHTR',

    # Real Estate
    'PLD', 'AMT', 'EQIX', 'SPG', 'PSA', 'O', 'WELL', 'DLR',

    # Utilities
    'NEE', 'DUK', 'SO', 'D', 'AEP', 'EXC', 'SRE', 'XEL',
]

# =============================================================================
# NASDAQ 100 - USA Tech Focus
# =============================================================================
NASDAQ100 = [
    'AAPL', 'MSFT', 'AMZN', 'NVDA', 'GOOGL', 'GOOG', 'META', 'TSLA', 'AVGO', 'COST',
    'ASML', 'PEP', 'AZN', 'ADBE', 'CSCO', 'NFLX', 'TMUS', 'AMD', 'TXN', 'CMCSA',
    'INTC', 'QCOM', 'INTU', 'AMGN', 'HON', 'AMAT', 'ISRG', 'BKNG', 'VRTX', 'SBUX',
    'GILD', 'ADI', 'ADP', 'MDLZ', 'REGN', 'LRCX', 'PANW', 'MU', 'SNPS', 'KLAC',
    'PYPL', 'CDNS', 'MELI', 'MAR', 'ORLY', 'ABNB', 'CHTR', 'FTNT', 'MNST', 'CTAS',
    'MRVL', 'KDP', 'DXCM', 'NXPI', 'KHC', 'AEP', 'PAYX', 'ADSK', 'EXC', 'MCHP',
    'LULU', 'PCAR', 'ROST', 'CPRT', 'ODFL', 'AZN', 'IDXX', 'WDAY', 'CRWD', 'FAST',
    'VRSK', 'EA', 'CTSH', 'CSGP', 'GEHC', 'BKR', 'FANG', 'DDOG', 'TEAM', 'ZS',
    'ANSS', 'ON', 'CDW', 'BIIB', 'TTD', 'GFS', 'ILMN', 'WBD', 'MRNA', 'DLTR',
    'CEG', 'XEL', 'WBA', 'ENPH', 'ZM', 'SIRI', 'LCID', 'RIVN', 'JD', 'PDD',
]

# =============================================================================
# CAC 40 - France
# =============================================================================
CAC40 = [
    'AI.PA',      # Air Liquide
    'AIR.PA',     # Airbus
    'ALO.PA',     # Alstom
    'MT.PA',      # ArcelorMittal (ou MT.AS)
    'CS.PA',      # AXA
    'BNP.PA',     # BNP Paribas
    'EN.PA',      # Bouygues
    'CAP.PA',     # Capgemini
    'CA.PA',      # Carrefour
    'ACA.PA',     # Crédit Agricole
    'BN.PA',      # Danone
    'DSY.PA',     # Dassault Systèmes
    'ENGI.PA',    # Engie
    'EL.PA',      # EssilorLuxottica
    'ERF.PA',     # Eurofins Scientific
    'RMS.PA',     # Hermès
    'KER.PA',     # Kering
    'LR.PA',      # Legrand
    'OR.PA',      # L'Oréal
    'MC.PA',      # LVMH
    'ML.PA',      # Michelin
    'ORA.PA',     # Orange
    'RI.PA',      # Pernod Ricard
    'PUB.PA',     # Publicis
    'RNO.PA',     # Renault
    'SAF.PA',     # Safran
    'SGO.PA',     # Saint-Gobain
    'SAN.PA',     # Sanofi
    'SU.PA',      # Schneider Electric
    'GLE.PA',     # Société Générale
    'STLA.PA',    # Stellantis (ou STLAP.PA)
    'STMPA.PA',   # STMicroelectronics (ou STM.PA)
    'TEP.PA',     # Teleperformance
    'HO.PA',      # Thales
    'TTE.PA',     # TotalEnergies
    'URW.PA',     # Unibail-Rodamco-Westfield (ou URW.AS)
    'VIE.PA',     # Veolia
    'DG.PA',      # Vinci
    'VIV.PA',     # Vivendi
    'WLN.PA',     # Worldline
]

# =============================================================================
# SBF 120 - France (Extensions CAC 40)
# =============================================================================
SBF120_EXTRA = [
    'AC.PA',      # Accor
    'AF.PA',      # Air France-KLM
    'AKE.PA',     # Arkema
    'ATO.PA',     # Atos
    'BB.PA',      # Bic
    'BIM.PA',     # Biomerieux
    'BOL.PA',     # Bolloré
    'CGG.PA',     # CGG
    'CO.PA',      # Casino
    'COV.PA',     # Covivio
    'DBG.PA',     # Deutsche Börse (Paris listing)
    'DIM.PA',     # Sartorius Stedim
    'EDF.PA',     # EDF
    'EDEN.PA',    # Edenred
    'FGR.PA',     # Eiffage
    'FDJ.PA',     # FDJ
    'GET.PA',     # Getlink
    'GFC.PA',     # Gecina
    'ILD.PA',     # ILIAD
    'IPN.PA',     # Ipsen
    'IPS.PA',     # Ipsos
    'JMT.PA',     # JCDecaux
    'MMB.PA',     # Lagardère
    'LI.PA',      # Klepierre
    'NEX.PA',     # Nexans
    'NK.PA',      # Imerys
    'ORAP.PA',    # Orapi
    'ORP.PA',     # Orpea
    'POM.PA',     # Plastic Omnium
    'QDT.PA',     # Quadient
    'RCO.PA',     # Rémy Cointreau
    'RXL.PA',     # Rexel
    'RBT.PA',     # Rubis
    'SK.PA',      # SEB
    'SOP.PA',     # Sopra Steria
    'SESG.PA',    # SES
    'SW.PA',      # Sodexo
    'SOI.PA',     # Soitec
    'SPB.PA',     # Spie
    'TFI.PA',     # TF1
    'UBI.PA',     # Ubisoft
    'VAC.PA',     # Valeo
    'VK.PA',      # Vallourec
    'VLA.PA',     # Valneva
    'VRLA.PA',    # Verallia
    'VRAP.PA',    # Virbac
]

# =============================================================================
# DAX 40 - Allemagne
# =============================================================================
DAX40 = [
    'ADS.DE',     # Adidas
    'AIR.DE',     # Airbus
    'ALV.DE',     # Allianz
    'BAS.DE',     # BASF
    'BAYN.DE',    # Bayer
    'BMW.DE',     # BMW
    'BNR.DE',     # Brenntag
    'CBK.DE',     # Commerzbank
    'CON.DE',     # Continental
    '1COV.DE',    # Covestro
    'DTG.DE',     # Daimler Truck
    'DBK.DE',     # Deutsche Bank
    'DB1.DE',     # Deutsche Börse
    'DPW.DE',     # Deutsche Post
    'DTE.DE',     # Deutsche Telekom
    'EOAN.DE',    # E.ON
    'FRE.DE',     # Fresenius
    'FME.DE',     # Fresenius Medical Care
    'HNR1.DE',    # Hannover Rück
    'HEI.DE',     # HeidelbergCement
    'HEN3.DE',    # Henkel
    'IFX.DE',     # Infineon
    'MBG.DE',     # Mercedes-Benz
    'MRK.DE',     # Merck KGaA
    'MTX.DE',     # MTU Aero Engines
    'MUV2.DE',    # Munich Re
    'P911.DE',    # Porsche
    'PAH3.DE',    # Porsche Auto Holding
    'QIA.DE',     # Qiagen
    'RHM.DE',     # Rheinmetall
    'RWE.DE',     # RWE
    'SAP.DE',     # SAP
    'SRT3.DE',    # Sartorius
    'SIE.DE',     # Siemens
    'ENR.DE',     # Siemens Energy
    'SHL.DE',     # Siemens Healthineers
    'SY1.DE',     # Symrise
    'VNA.DE',     # Vonovia
    'VOW3.DE',    # Volkswagen
    'ZAL.DE',     # Zalando
]

# =============================================================================
# EURO STOXX 50 - Zone Euro
# =============================================================================
EUROSTOXX50 = [
    # Allemagne
    'ADS.DE', 'ALV.DE', 'BAS.DE', 'BAYN.DE', 'BMW.DE', 'DBK.DE', 'DTE.DE',
    'EOAN.DE', 'IFX.DE', 'MBG.DE', 'MUV2.DE', 'SAP.DE', 'SIE.DE', 'VOW3.DE',
    # France
    'AI.PA', 'AIR.PA', 'BNP.PA', 'CS.PA', 'ENGI.PA', 'EL.PA', 'KER.PA',
    'OR.PA', 'MC.PA', 'ORA.PA', 'SAF.PA', 'SAN.PA', 'SU.PA', 'TTE.PA', 'DG.PA',
    # Pays-Bas
    'ASML.AS', 'INGA.AS', 'PHIA.AS', 'AD.AS',
    # Espagne
    'SAN.MC', 'IBE.MC', 'ITX.MC', 'TEF.MC', 'REP.MC',
    # Italie
    'ENEL.MI', 'ENI.MI', 'ISP.MI', 'UCG.MI', 'G.MI',
    # Belgique
    'ABI.BR', 'KBC.BR',
    # Finlande
    'NOKIA.HE',
    # Irlande
    'CRH.L',
]

# =============================================================================
# FTSE 100 - Royaume-Uni
# =============================================================================
FTSE100 = [
    'SHEL.L',     # Shell
    'AZN.L',      # AstraZeneca
    'HSBA.L',     # HSBC
    'ULVR.L',     # Unilever
    'BP.L',       # BP
    'RIO.L',      # Rio Tinto
    'GSK.L',      # GSK
    'DGE.L',      # Diageo
    'BATS.L',     # British American Tobacco
    'REL.L',      # RELX
    'LSEG.L',     # London Stock Exchange
    'AAL.L',      # Anglo American
    'RKT.L',      # Reckitt
    'CRH.L',      # CRH
    'GLEN.L',     # Glencore
    'NG.L',       # National Grid
    'PRU.L',      # Prudential
    'CPGX.L',     # Compass Group
    'VOD.L',      # Vodafone
    'LLOY.L',     # Lloyds
    'BARC.L',     # Barclays
    'RR.L',       # Rolls-Royce
    'BA.L',       # BAE Systems
    'EXPN.L',     # Experian
    'SSE.L',      # SSE
    'NWG.L',      # NatWest
    'ABF.L',      # Associated British Foods
    'INF.L',      # Informa
    'ANTO.L',     # Antofagasta
    'III.L',      # 3i Group
    'BT-A.L',     # BT Group
    'SMT.L',      # Scottish Mortgage
    'STAN.L',     # Standard Chartered
    'AVV.L',      # AVEVA
    'TSCO.L',     # Tesco
    'WPP.L',      # WPP
    'SGE.L',      # Sage Group
    'IMB.L',      # Imperial Brands
    'LAND.L',     # Land Securities
    'SVT.L',      # Severn Trent
]

# =============================================================================
# SMI - Suisse
# =============================================================================
SMI = [
    'NESN.SW',    # Nestlé
    'ROG.SW',     # Roche
    'NOVN.SW',    # Novartis
    'UBSG.SW',    # UBS
    'ZURN.SW',    # Zurich Insurance
    'CSGN.SW',    # Credit Suisse
    'ABBN.SW',    # ABB
    'SREN.SW',    # Swiss Re
    'GIVN.SW',    # Givaudan
    'LONN.SW',    # Lonza
    'CFR.SW',     # Richemont
    'SGSN.SW',    # SGS
    'GEBN.SW',    # Geberit
    'SLHN.SW',    # Swiss Life
    'SIKA.SW',    # Sika
    'SCMN.SW',    # Swisscom
    'HOLN.SW',    # Holcim
    'PGHN.SW',    # Partners Group
    'SOON.SW',    # Sonova
    'ALC.SW',     # Alcon
]

# =============================================================================
# AEX - Pays-Bas
# =============================================================================
AEX = [
    'ASML.AS',    # ASML
    'SHEL.AS',    # Shell
    'PRX.AS',     # Prosus
    'INGA.AS',    # ING
    'AD.AS',      # Ahold Delhaize
    'PHIA.AS',    # Philips
    'DSM.AS',     # DSM
    'AKZA.AS',    # Akzo Nobel
    'HEIA.AS',    # Heineken
    'WKL.AS',     # Wolters Kluwer
    'KPN.AS',     # KPN
    'NN.AS',      # NN Group
    'RAND.AS',    # Randstad
    'UNA.AS',     # Unilever
    'REN.AS',     # RELX
    'ABN.AS',     # ABN AMRO
    'BESI.AS',    # BE Semiconductor
    'IMCD.AS',    # IMCD
    'ASM.AS',     # ASM International
]

# =============================================================================
# IBEX 35 - Espagne
# =============================================================================
IBEX35 = [
    'SAN.MC',     # Santander
    'BBVA.MC',    # BBVA
    'IBE.MC',     # Iberdrola
    'ITX.MC',     # Inditex
    'TEF.MC',     # Telefonica
    'REP.MC',     # Repsol
    'AMS.MC',     # Amadeus IT
    'FER.MC',     # Ferrovial
    'ACS.MC',     # ACS
    'CABK.MC',    # CaixaBank
    'GRF.MC',     # Grifols
    'CLNX.MC',    # Cellnex
    'ENG.MC',     # Enagas
    'REE.MC',     # Red Electrica
    'MAP.MC',     # Mapfre
    'ANA.MC',     # Acciona
    'ELE.MC',     # Endesa
    'NTGY.MC',    # Naturgy
    'SAB.MC',     # Banco Sabadell
    'MRL.MC',     # Merlin Properties
]

# =============================================================================
# MIB - Italie
# =============================================================================
MIB = [
    'ENEL.MI',    # Enel
    'ENI.MI',     # Eni
    'ISP.MI',     # Intesa Sanpaolo
    'UCG.MI',     # UniCredit
    'G.MI',       # Generali
    'STM.MI',     # STMicroelectronics
    'TIT.MI',     # Telecom Italia
    'RACE.MI',    # Ferrari
    'MONC.MI',    # Moncler
    'STLA.MI',    # Stellantis
    'PRY.MI',     # Prysmian
    'SRG.MI',     # Snam
    'TRN.MI',     # Terna
    'A2A.MI',     # A2A
    'LDO.MI',     # Leonardo
    'BAMI.MI',    # Banco BPM
    'PST.MI',     # Poste Italiane
    'BMED.MI',    # Banca Mediolanum
    'CPR.MI',     # Campari
    'DIA.MI',     # DiaSorin
]

# =============================================================================
# NIKKEI 225 - Japon (Top 50)
# =============================================================================
NIKKEI_TOP50 = [
    '7203.T',     # Toyota
    '6758.T',     # Sony
    '9984.T',     # SoftBank
    '6861.T',     # Keyence
    '9432.T',     # NTT
    '6902.T',     # Denso
    '8306.T',     # Mitsubishi UFJ
    '6501.T',     # Hitachi
    '4502.T',     # Takeda
    '6367.T',     # Daikin
    '7974.T',     # Nintendo
    '8035.T',     # Tokyo Electron
    '4063.T',     # Shin-Etsu Chemical
    '6954.T',     # Fanuc
    '6098.T',     # Recruit
    '7267.T',     # Honda
    '8766.T',     # Tokio Marine
    '9433.T',     # KDDI
    '6981.T',     # Murata
    '4568.T',     # Daiichi Sankyo
    '6273.T',     # SMC
    '6594.T',     # Nidec
    '8316.T',     # Sumitomo Mitsui
    '7751.T',     # Canon
    '6857.T',     # Advantest
    '9983.T',     # Fast Retailing
    '4519.T',     # Chugai Pharma
    '8058.T',     # Mitsubishi Corp
    '8031.T',     # Mitsui & Co
    '7741.T',     # HOYA
    '6702.T',     # Fujitsu
    '6503.T',     # Mitsubishi Electric
    '6762.T',     # TDK
    '4503.T',     # Astellas
    '7733.T',     # Olympus
    '8001.T',     # Itochu
    '6301.T',     # Komatsu
    '3382.T',     # Seven & I
    '7269.T',     # Suzuki
    '2802.T',     # Ajinomoto
    '2914.T',     # Japan Tobacco
    '4901.T',     # Fujifilm
    '6988.T',     # Nitto Denko
    '9020.T',     # JR East
    '6326.T',     # Kubota
    '4661.T',     # Oriental Land
    '8002.T',     # Marubeni
    '8801.T',     # Mitsui Fudosan
    '6752.T',     # Panasonic
    '5108.T',     # Bridgestone
]

# =============================================================================
# HANG SENG - Hong Kong / Chine (Top 30)
# =============================================================================
HANGSENG = [
    '0700.HK',    # Tencent
    '9988.HK',    # Alibaba
    '0005.HK',    # HSBC
    '0941.HK',    # China Mobile
    '2318.HK',    # Ping An
    '0939.HK',    # CCB
    '1398.HK',    # ICBC
    '0883.HK',    # CNOOC
    '3988.HK',    # Bank of China
    '0388.HK',    # HKEX
    '0027.HK',    # Galaxy Entertainment
    '2628.HK',    # China Life
    '0001.HK',    # CK Hutchison
    '0016.HK',    # SHK Properties
    '1928.HK',    # Sands China
    '0267.HK',    # CITIC
    '0011.HK',    # Hang Seng Bank
    '0066.HK',    # MTR
    '0003.HK',    # HK & China Gas
    '1109.HK',    # China Resources
    '0688.HK',    # China Overseas
    '0012.HK',    # Henderson Land
    '0002.HK',    # CLP Holdings
    '0006.HK',    # Power Assets
    '0017.HK',    # New World Dev
    '0823.HK',    # Link REIT
    '0857.HK',    # PetroChina
    '0386.HK',    # Sinopec
    '1299.HK',    # AIA
    '9618.HK',    # JD.com
]

# =============================================================================
# ADR Chinois cotés aux USA
# =============================================================================
CHINA_ADR = [
    'BABA',       # Alibaba
    'JD',         # JD.com
    'PDD',        # Pinduoduo
    'BIDU',       # Baidu
    'NIO',        # NIO
    'XPEV',       # XPeng
    'LI',         # Li Auto
    'NTES',       # NetEase
    'TCOM',       # Trip.com
    'BILI',       # Bilibili
    'ZTO',        # ZTO Express
    'VNET',       # Vnet Group
    'QFIN',       # Qifu Technology
    'TAL',        # TAL Education
    'EDU',        # New Oriental
    'MNSO',       # Miniso
    'YUMC',       # Yum China
    'FUTU',       # Futu Holdings
    'DIDI',       # DiDi Global
    'IQ',         # iQIYI
]

# =============================================================================
# ASX 50 - Australie
# =============================================================================
ASX50 = [
    'BHP.AX',     # BHP
    'CBA.AX',     # Commonwealth Bank
    'CSL.AX',     # CSL
    'NAB.AX',     # National Australia Bank
    'WBC.AX',     # Westpac
    'ANZ.AX',     # ANZ
    'WES.AX',     # Wesfarmers
    'MQG.AX',     # Macquarie Group
    'WOW.AX',     # Woolworths
    'RIO.AX',     # Rio Tinto
    'FMG.AX',     # Fortescue Metals
    'TLS.AX',     # Telstra
    'NCM.AX',     # Newcrest Mining
    'WPL.AX',     # Woodside Petroleum
    'STO.AX',     # Santos
    'AMC.AX',     # Amcor
    'TCL.AX',     # Transurban
    'GMG.AX',     # Goodman Group
    'ALL.AX',     # Aristocrat Leisure
    'COL.AX',     # Coles
    'SUN.AX',     # Suncorp
    'QBE.AX',     # QBE Insurance
    'IAG.AX',     # Insurance Australia
    'ORG.AX',     # Origin Energy
    'APA.AX',     # APA Group
]

# =============================================================================
# TSX 60 - Canada
# =============================================================================
TSX60 = [
    'RY.TO',      # Royal Bank of Canada
    'TD.TO',      # TD Bank
    'ENB.TO',     # Enbridge
    'CNR.TO',     # Canadian National Railway
    'BMO.TO',     # Bank of Montreal
    'BNS.TO',     # Bank of Nova Scotia
    'CP.TO',      # Canadian Pacific
    'TRP.TO',     # TC Energy
    'CNQ.TO',     # Canadian Natural Resources
    'SU.TO',      # Suncor
    'BCE.TO',     # BCE
    'MFC.TO',     # Manulife
    'SHOP.TO',    # Shopify
    'ATD.TO',     # Alimentation Couche-Tard
    'T.TO',       # Telus
    'CVE.TO',     # Cenovus
    'RCI-B.TO',   # Rogers Communications
    'IMO.TO',     # Imperial Oil
    'PPL.TO',     # Pembina Pipeline
    'CSU.TO',     # Constellation Software
    'ABX.TO',     # Barrick Gold
    'WCN.TO',     # Waste Connections
    'FNV.TO',     # Franco-Nevada
    'QSR.TO',     # Restaurant Brands
    'NTR.TO',     # Nutrien
]

# =============================================================================
# CRYPTO (via Yahoo Finance)
# =============================================================================
CRYPTO = [
    'BTC-USD',    # Bitcoin
    'ETH-USD',    # Ethereum
    'BNB-USD',    # Binance Coin
    'XRP-USD',    # Ripple
    'ADA-USD',    # Cardano
    'SOL-USD',    # Solana
    'DOGE-USD',   # Dogecoin
    'DOT-USD',    # Polkadot
    'MATIC-USD',  # Polygon
    'AVAX-USD',   # Avalanche
    'LINK-USD',   # Chainlink
    'UNI-USD',    # Uniswap
    'ATOM-USD',   # Cosmos
    'LTC-USD',    # Litecoin
    'XLM-USD',    # Stellar
]

# =============================================================================
# FONCTION D'AGGREGATION
# =============================================================================

def get_all_stocks() -> list:
    """Retourne tous les tickers uniques de l'univers."""
    all_tickers = set()

    # USA
    all_tickers.update(SP500_TOP100)
    all_tickers.update(NASDAQ100)

    # Europe
    all_tickers.update(CAC40)
    all_tickers.update(SBF120_EXTRA)
    all_tickers.update(DAX40)
    all_tickers.update(EUROSTOXX50)
    all_tickers.update(FTSE100)
    all_tickers.update(SMI)
    all_tickers.update(AEX)
    all_tickers.update(IBEX35)
    all_tickers.update(MIB)

    # Asie
    all_tickers.update(NIKKEI_TOP50)
    all_tickers.update(HANGSENG)
    all_tickers.update(CHINA_ADR)

    # Autres
    all_tickers.update(ASX50)
    all_tickers.update(TSX60)

    return sorted(list(all_tickers))


def get_stocks_by_region(region: str) -> list:
    """Retourne les tickers par région."""
    regions = {
        'USA': list(set(SP500_TOP100 + NASDAQ100)),
        'FRANCE': list(set(CAC40 + SBF120_EXTRA)),
        'ALLEMAGNE': DAX40,
        'EUROPE': list(set(CAC40 + SBF120_EXTRA + DAX40 + EUROSTOXX50 + FTSE100 + SMI + AEX + IBEX35 + MIB)),
        'JAPON': NIKKEI_TOP50,
        'CHINE': list(set(HANGSENG + CHINA_ADR)),
        'ASIE': list(set(NIKKEI_TOP50 + HANGSENG + CHINA_ADR)),
        'AUSTRALIE': ASX50,
        'CANADA': TSX60,
        'UK': FTSE100,
        'SUISSE': SMI,
        'CRYPTO': CRYPTO,
    }
    return regions.get(region.upper(), [])


def get_pea_eligible() -> list:
    """Retourne les tickers éligibles PEA (Europe)."""
    pea_eligible = set()

    # France
    pea_eligible.update(CAC40)
    pea_eligible.update(SBF120_EXTRA)

    # Allemagne
    pea_eligible.update(DAX40)

    # Pays-Bas
    pea_eligible.update(AEX)

    # Espagne
    pea_eligible.update(IBEX35)

    # Italie
    pea_eligible.update(MIB)

    # Euro Stoxx (majorité éligible)
    pea_eligible.update([t for t in EUROSTOXX50 if any(x in t for x in ['.PA', '.DE', '.AS', '.MC', '.MI'])])

    return sorted(list(pea_eligible))


def get_stock_count() -> dict:
    """Retourne le nombre d'actions par indice/région."""
    return {
        'S&P 500 (Top 100)': len(SP500_TOP100),
        'NASDAQ 100': len(NASDAQ100),
        'CAC 40': len(CAC40),
        'SBF 120 (extras)': len(SBF120_EXTRA),
        'DAX 40': len(DAX40),
        'Euro Stoxx 50': len(EUROSTOXX50),
        'FTSE 100': len(FTSE100),
        'SMI (Suisse)': len(SMI),
        'AEX (Pays-Bas)': len(AEX),
        'IBEX 35 (Espagne)': len(IBEX35),
        'MIB (Italie)': len(MIB),
        'Nikkei (Top 50)': len(NIKKEI_TOP50),
        'Hang Seng': len(HANGSENG),
        'China ADR': len(CHINA_ADR),
        'ASX 50 (Australie)': len(ASX50),
        'TSX 60 (Canada)': len(TSX60),
        'Crypto': len(CRYPTO),
        'TOTAL UNIQUE': len(get_all_stocks()),
    }


if __name__ == "__main__":
    print("=" * 60)
    print("UNIVERS D'ACTIONS - STOCK ADVISOR v3.0")
    print("=" * 60)

    counts = get_stock_count()
    for index, count in counts.items():
        print(f"  {index}: {count}")

    print(f"\n  Éligibles PEA: {len(get_pea_eligible())}")
