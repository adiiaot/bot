import os
import sys
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

load_dotenv()

PROJECT_ID = os.getenv('FIREBASE_PROJECT_ID')
NOW = datetime.now(timezone.utc)
SERVER_TS = firestore.SERVER_TIMESTAMP

def init_firebase():
    print("[FIRE] Initializing Firebase Admin SDK...")
    cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH')
    if cred_path and os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        print(f"  [OK] Using credentials file: {cred_path}")
    else:
        cred = credentials.Certificate({
            'type': 'service_account',
            'project_id': PROJECT_ID,
            'private_key': os.getenv('FIREBASE_PRIVATE_KEY', '').replace('\\n', '\n'),
            'client_email': os.getenv('FIREBASE_CLIENT_EMAIL'),
            'token_uri': 'https://oauth2.googleapis.com/token',
        })
        print(f"  [OK] Using credentials from environment variables")
    try:
        firebase_admin.initialize_app(cred, {'projectId': PROJECT_ID})
    except ValueError as e:
        if 'already exists' in str(e):
            print("  [OK] Firebase already initialized")
        else:
            raise
    db = firestore.client()
    print(f"  [OK] Connected to project: {PROJECT_ID}")
    print()
    return db

USER_IDS = ['user_abc123', 'user_def456']
SIGNAL_IDS = ['signal_20260625_083000', 'signal_20260625_091500', 'signal_20260624_140000']
TRADE_IDS = ['trade_20260625_083500', 'trade_20260625_092000', 'trade_20260624_141000']
JOURNAL_IDS = ['journal_20260625_080000', 'journal_20260625_090000', 'journal_20260624_180000']
ANALYTICS_IDS = ['daily_20260625', 'weekly_20260623', 'monthly_20260601']
ECON_IDS = ['event_20260625_001', 'event_20260625_002', 'event_20260626_001']
LOG_IDS = ['log_20260625_083000', 'log_20260625_091500', 'log_20260624_140000']
BOTLOG_IDS = ['botlog_20260625_080000', 'botlog_20260625_090000', 'botlog_20260624_200000']

SAMPLE_USERS = [
    {
        'userId': USER_IDS[0],
        'email': 'trader1@example.com',
        'createdAt': SERVER_TS,
        'accountMode': 'demo',
        'accountBalance': 10000.00,
        'initialBalance': 10000.00,
        'maxRiskPerTrade': 2.0,
        'maxDailyLoss': 5.0,
        'maxWeeklyLoss': 10.0,
        'defaultRiskPercentage': 1.5,
        'preferences': {
            'theme': 'dark',
            'notifications': {
                'signals': True,
                'tradeClose': True,
                'econCalendar': True,
            },
            'tradingHours': {
                'sessionStart': '14:30',
                'sessionEnd': '22:00',
                'enableAutoTrade': False,
            },
        },
        'telegramUserId': 'telegram_12345',
        'lastActive': SERVER_TS,
    },
    {
        'userId': USER_IDS[1],
        'email': 'trader2@example.com',
        'createdAt': SERVER_TS,
        'accountMode': 'live',
        'accountBalance': 25000.00,
        'initialBalance': 20000.00,
        'maxRiskPerTrade': 1.5,
        'maxDailyLoss': 3.0,
        'maxWeeklyLoss': 7.0,
        'defaultRiskPercentage': 1.0,
        'preferences': {
            'theme': 'light',
            'notifications': {
                'signals': True,
                'tradeClose': False,
                'econCalendar': True,
            },
            'tradingHours': {
                'sessionStart': '08:00',
                'sessionEnd': '16:00',
                'enableAutoTrade': True,
            },
        },
        'telegramUserId': 'telegram_67890',
        'lastActive': SERVER_TS,
    },
]

SAMPLE_SIGNALS = [
    {
        'signalId': SIGNAL_IDS[0],
        'userId': USER_IDS[0],
        'timestamp': SERVER_TS,
        'trend': 'UP',
        'entries': [
            {'entryNumber': 1, 'price': 2325.45, 'tp': 2330.50, 'tpPips': 50.5, 'autoClose': True},
            {'entryNumber': 2, 'price': 2328.10, 'tp': 2333.00, 'tpPips': 49.0, 'autoClose': False},
            {'entryNumber': 3, 'price': 2330.75, 'tp': 2335.25, 'tpPips': 45.0, 'autoClose': False},
        ],
        'supportLevel': 2320.00,
        'resistanceLevel': 2340.00,
        'pullbackDetected': True,
        'entryConfirmation': True,
        'validUntil': NOW + timedelta(hours=3),
        'confidence': 0.75,
        'status': 'active',
        'executedEntries': [],
        'deliveredVia': 'both',
        'deliveredAt': SERVER_TS,
        'acknowledged': False,
        'analysis': {
            'reasonGenerated': 'Bullish breakout above 2320 resistance with strong volume. Pullback to 2325 support level confirmed. RSI showing room for upward movement.',
            'confidence_breakdown': {
                'trend_strength': 0.80,
                'level_proximity': 0.72,
                'volatility_score': 0.65,
                'reversal_pattern_quality': 0.78,
            },
        },
    },
    {
        'signalId': SIGNAL_IDS[1],
        'userId': USER_IDS[0],
        'timestamp': SERVER_TS,
        'trend': 'DOWN',
        'entries': [
            {'entryNumber': 1, 'price': 2345.30, 'tp': 2338.00, 'tpPips': 73.0, 'autoClose': True},
            {'entryNumber': 2, 'price': 2342.80, 'tp': 2336.50, 'tpPips': 63.0, 'autoClose': False},
        ],
        'supportLevel': 2330.00,
        'resistanceLevel': 2355.00,
        'pullbackDetected': True,
        'entryConfirmation': True,
        'validUntil': NOW + timedelta(hours=3),
        'confidence': 0.68,
        'status': 'active',
        'executedEntries': [],
        'deliveredVia': 'dashboard',
        'deliveredAt': SERVER_TS,
        'acknowledged': True,
        'analysis': {
            'reasonGenerated': 'Bearish rejection at 2355 resistance level. Double top pattern detected on 15M chart. Bearish engulfing candle on 5M timeframe.',
            'confidence_breakdown': {
                'trend_strength': 0.72,
                'level_proximity': 0.68,
                'volatility_score': 0.58,
                'reversal_pattern_quality': 0.82,
            },
        },
    },
    {
        'signalId': SIGNAL_IDS[2],
        'userId': USER_IDS[1],
        'timestamp': NOW - timedelta(hours=24),
        'trend': 'UP',
        'entries': [
            {'entryNumber': 1, 'price': 2310.00, 'tp': 2318.50, 'tpPips': 85.0, 'autoClose': True},
            {'entryNumber': 2, 'price': 2313.40, 'tp': 2321.00, 'tpPips': 76.0, 'autoClose': True},
            {'entryNumber': 3, 'price': 2316.80, 'tp': 2323.50, 'tpPips': 67.0, 'autoClose': False},
            {'entryNumber': 4, 'price': 2320.00, 'tp': 2326.00, 'tpPips': 60.0, 'autoClose': False},
        ],
        'supportLevel': 2305.00,
        'resistanceLevel': 2325.00,
        'pullbackDetected': True,
        'entryConfirmation': True,
        'validUntil': NOW - timedelta(hours=21),
        'confidence': 0.82,
        'status': 'expired',
        'executedEntries': [1, 2],
        'deliveredVia': 'both',
        'deliveredAt': NOW - timedelta(hours=24),
        'acknowledged': True,
        'analysis': {
            'reasonGenerated': 'Strong bullish momentum from 2300 support. Break above 2315 confirms continuation. Trendline support from 4H chart aligns with entry zone.',
            'confidence_breakdown': {
                'trend_strength': 0.85,
                'level_proximity': 0.80,
                'volatility_score': 0.72,
                'reversal_pattern_quality': 0.75,
            },
        },
    },
]

SAMPLE_TRADES = [
    {
        'tradeId': TRADE_IDS[0],
        'userId': USER_IDS[0],
        'signalId': SIGNAL_IDS[0],
        'timestamp': SERVER_TS,
        'entryPrice': 2325.50,
        'entrySize': 0.05,
        'entryTime': SERVER_TS,
        'exitPrice': None,
        'exitTime': None,
        'pnl': None,
        'pnlPercent': None,
        'result': None,
        'trend': 'UP',
        'supportLevel': 2320.00,
        'resistanceLevel': 2340.00,
        'stopLoss': 2318.00,
        'takeProfit': 2330.50,
        'riskRewardRatio': 2.17,
        'status': 'open',
        'holdTimeSeconds': None,
        'journalNotes': '',
        'tradingConditions': '',
        'analysis': {
            'performanceReason': None,
            'howSignalBenefited': None,
            'improvements': [],
            'confidence': None,
        },
    },
    {
        'tradeId': TRADE_IDS[1],
        'userId': USER_IDS[0],
        'signalId': SIGNAL_IDS[1],
        'timestamp': SERVER_TS,
        'entryPrice': 2345.30,
        'entrySize': 0.03,
        'entryTime': SERVER_TS,
        'exitPrice': None,
        'exitTime': None,
        'pnl': None,
        'pnlPercent': None,
        'result': None,
        'trend': 'DOWN',
        'supportLevel': 2330.00,
        'resistanceLevel': 2355.00,
        'stopLoss': 2348.50,
        'takeProfit': 2338.00,
        'riskRewardRatio': 2.29,
        'status': 'open',
        'holdTimeSeconds': None,
        'journalNotes': '',
        'tradingConditions': '',
        'analysis': {
            'performanceReason': None,
            'howSignalBenefited': None,
            'improvements': [],
            'confidence': None,
        },
    },
    {
        'tradeId': TRADE_IDS[2],
        'userId': USER_IDS[1],
        'signalId': SIGNAL_IDS[2],
        'timestamp': NOW - timedelta(hours=24),
        'entryPrice': 2310.00,
        'entrySize': 0.10,
        'entryTime': NOW - timedelta(hours=23, minutes=30),
        'exitPrice': 2318.50,
        'exitTime': NOW - timedelta(hours=22, minutes=45),
        'pnl': 42.50,
        'pnlPercent': 1.84,
        'result': 'win',
        'trend': 'UP',
        'supportLevel': 2305.00,
        'resistanceLevel': 2325.00,
        'stopLoss': 2307.00,
        'takeProfit': 2318.50,
        'riskRewardRatio': 2.83,
        'status': 'closed',
        'holdTimeSeconds': 2700,
        'journalNotes': 'Good entry on pullback to support. TP hit within 45 minutes.',
        'tradingConditions': 'Normal volatility, news-driven momentum',
        'analysis': {
            'performanceReason': 'Perfect entry at support bounce. TP hit as resistance gave way.',
            'howSignalBenefited': 'Signal identified the pullback entry zone accurately.',
            'improvements': ['Could have scaled out partially at 2315', 'Consider trailing SL on strong momentum'],
            'confidence': 0.82,
        },
    },
]

SAMPLE_JOURNAL = [
    {
        'entryId': JOURNAL_IDS[0],
        'userId': USER_IDS[0],
        'timestamp': SERVER_TS,
        'source': 'dashboard',
        'notes': 'Pre-market analysis complete. Watching 2320 support level for potential long entry. NFP data coming at 14:30.',
        'relatedTradeId': None,
        'marketCondition': 'ranging',
        'tradingState': 'focus',
        'lessonsLearned': ['Wait for confirmation before entry', 'Check economic calendar first'],
        'sentiment': 'positive',
        'analysis': {
            'theme': 'Pre-market preparation',
            'actionItems': ['Monitor 2320 support', 'Set alert at 2335', 'Check NFP expectations'],
            'relatedSignals': [],
        },
    },
    {
        'entryId': JOURNAL_IDS[1],
        'userId': USER_IDS[0],
        'timestamp': SERVER_TS,
        'source': 'dashboard',
        'notes': 'Closed first trade of the day. Signal entry 1 hit TP. Good momentum on the move.',
        'relatedTradeId': TRADE_IDS[0],
        'marketCondition': 'trending',
        'tradingState': 'confident',
        'lessonsLearned': ['Plan worked exactly as expected', 'Stick to the signal entries'],
        'sentiment': 'positive',
        'analysis': {
            'theme': 'Trade execution review',
            'actionItems': ['Log trade in journal', 'Review entry 2 potential'],
            'relatedSignals': [SIGNAL_IDS[0]],
        },
    },
    {
        'entryId': JOURNAL_IDS[2],
        'userId': USER_IDS[1],
        'timestamp': NOW - timedelta(hours=24),
        'source': 'telegram',
        'notes': 'Took a loss on the breakout trade. Entered too early before confirmation candle closed. Need to be more patient.',
        'relatedTradeId': TRADE_IDS[2],
        'marketCondition': 'breakout',
        'tradingState': 'tired',
        'lessonsLearned': ['Do not front-run breakouts', 'Wait for candle close confirmation', 'Reduce position size when tired'],
        'sentiment': 'negative',
        'analysis': {
            'theme': 'Learning from losses',
            'actionItems': ['Review entry timing', 'Set stricter confirmation rules', 'Take break after 2 consecutive losses'],
            'relatedSignals': [SIGNAL_IDS[2]],
        },
    },
]

SAMPLE_ANALYTICS = [
    {
        'analyticsId': ANALYTICS_IDS[0],
        'userId': USER_IDS[0],
        'period': 'daily',
        'periodStart': NOW.replace(hour=0, minute=0, second=0, microsecond=0),
        'periodEnd': NOW.replace(hour=23, minute=59, second=59, microsecond=999999),
        'totalTrades': 3,
        'wins': 2,
        'losses': 1,
        'breakEven': 0,
        'winRate': 66.67,
        'lossRate': 33.33,
        'totalPnl': 85.20,
        'totalPnlPercent': 0.85,
        'avgWin': 55.60,
        'avgLoss': -26.00,
        'largestWin': 68.40,
        'largestLoss': -26.00,
        'profitFactor': 2.14,
        'consecutiveWins': 2,
        'consecutiveLosses': 1,
        'maxDrawdown': 1.2,
        'totalRiskCapital': 10000.00,
        'riskPerTrade': 1.5,
        'sharpeRatio': 1.85,
        'signalHitRate': 75.0,
        'avgSignalWin': 52.30,
        'avgSignalLoss': -22.50,
        'upTrendWinRate': 70.0,
        'downTrendWinRate': 60.0,
        'entry1Stats': {'wins': 1, 'losses': 0, 'avg_pnl': 42.50},
        'entry2Stats': {'wins': 1, 'losses': 0, 'avg_pnl': 25.80},
        'entry3Stats': {'wins': 0, 'losses': 1, 'avg_pnl': -26.00},
        'entry4Stats': {'wins': 0, 'losses': 0, 'avg_pnl': 0.0},
        'lastUpdated': SERVER_TS,
    },
    {
        'analyticsId': ANALYTICS_IDS[1],
        'userId': USER_IDS[0],
        'period': 'weekly',
        'periodStart': NOW - timedelta(days=7),
        'periodEnd': NOW,
        'totalTrades': 15,
        'wins': 10,
        'losses': 4,
        'breakEven': 1,
        'winRate': 66.67,
        'lossRate': 26.67,
        'totalPnl': 340.50,
        'totalPnlPercent': 3.41,
        'avgWin': 52.40,
        'avgLoss': -28.75,
        'largestWin': 85.00,
        'largestLoss': -42.00,
        'profitFactor': 1.82,
        'consecutiveWins': 5,
        'consecutiveLosses': 2,
        'maxDrawdown': 3.5,
        'totalRiskCapital': 10000.00,
        'riskPerTrade': 1.5,
        'sharpeRatio': 1.62,
        'signalHitRate': 72.0,
        'avgSignalWin': 48.90,
        'avgSignalLoss': -25.30,
        'upTrendWinRate': 68.0,
        'downTrendWinRate': 65.0,
        'entry1Stats': {'wins': 4, 'losses': 1, 'avg_pnl': 38.20},
        'entry2Stats': {'wins': 3, 'losses': 1, 'avg_pnl': 22.40},
        'entry3Stats': {'wins': 2, 'losses': 1, 'avg_pnl': 15.80},
        'entry4Stats': {'wins': 1, 'losses': 1, 'avg_pnl': -8.50},
        'lastUpdated': SERVER_TS,
    },
    {
        'analyticsId': ANALYTICS_IDS[2],
        'userId': USER_IDS[0],
        'period': 'monthly',
        'periodStart': NOW.replace(day=1, hour=0, minute=0, second=0, microsecond=0),
        'periodEnd': NOW,
        'totalTrades': 62,
        'wins': 40,
        'losses': 18,
        'breakEven': 4,
        'winRate': 64.52,
        'lossRate': 29.03,
        'totalPnl': 1280.00,
        'totalPnlPercent': 12.80,
        'avgWin': 48.25,
        'avgLoss': -30.50,
        'largestWin': 120.00,
        'largestLoss': -55.00,
        'profitFactor': 1.58,
        'consecutiveWins': 7,
        'consecutiveLosses': 3,
        'maxDrawdown': 6.8,
        'totalRiskCapital': 10000.00,
        'riskPerTrade': 1.5,
        'sharpeRatio': 1.45,
        'signalHitRate': 70.0,
        'avgSignalWin': 45.60,
        'avgSignalLoss': -28.90,
        'upTrendWinRate': 66.0,
        'downTrendWinRate': 62.0,
        'entry1Stats': {'wins': 14, 'losses': 5, 'avg_pnl': 35.40},
        'entry2Stats': {'wins': 12, 'losses': 5, 'avg_pnl': 28.60},
        'entry3Stats': {'wins': 8, 'losses': 4, 'avg_pnl': 18.20},
        'entry4Stats': {'wins': 6, 'losses': 4, 'avg_pnl': 12.50},
        'lastUpdated': SERVER_TS,
    },
]

SAMPLE_ECON = [
    {
        'eventId': ECON_IDS[0],
        'timestamp': NOW.replace(hour=14, minute=30, second=0, microsecond=0),
        'eventName': 'US Non-Farm Employment Change (NFP)',
        'impact': 'high',
        'country': 'US',
        'forecast': 185000,
        'previous': 175000,
        'actual': None,
        'goldRelated': True,
        'expectedDirection': 'volatile',
        'rationale': 'NFP is the most impactful US economic indicator. Strong data strengthens USD, weakens gold.',
        'recommendedAction': 'Avoid new positions 30 min before and after. Close partial positions if already in trade.',
        'signalStrategy': 'Hold existing signals. No new signals generated 1 hour before NFP.',
        'analysis': {
            'historicalImpact': 'NFP historically causes 15-25 pip moves in XAU/USD within 5 minutes of release.',
            'currentMarketContext': 'Market expecting moderate employment growth. Any deviation above 200K or below 150K will cause outsized moves.',
            'goldPriceImplication': 'Strong NFP (>200K) = sell gold. Weak NFP (<150K) = buy gold.',
            'timeOfImpact': '14:30 - 15:00 UTC',
        },
    },
    {
        'eventId': ECON_IDS[1],
        'timestamp': NOW.replace(hour=12, minute=0, second=0, microsecond=0),
        'eventName': 'US Initial Jobless Claims',
        'impact': 'medium',
        'country': 'US',
        'forecast': 220000,
        'previous': 218000,
        'actual': 223000,
        'goldRelated': True,
        'expectedDirection': 'down',
        'rationale': 'Higher claims indicate labor market softening, which is slightly bearish USD and bullish gold.',
        'recommendedAction': 'Monitor for volatility. Consider long if claims exceed 230K.',
        'signalStrategy': 'Standard signal generation applies. Adjust confidence based on deviation from forecast.',
        'analysis': {
            'historicalImpact': 'Jobless claims typically cause 5-10 pip movements in XAU/USD.',
            'currentMarketContext': 'Claims have been stable around 215-220K range. Significant deviation unlikely.',
            'goldPriceImplication': 'Claims > forecast = gold up. Claims < forecast = gold down.',
            'timeOfImpact': '12:00 - 12:30 UTC',
        },
    },
    {
        'eventId': ECON_IDS[2],
        'timestamp': (NOW + timedelta(days=1)).replace(hour=14, minute=0, second=0, microsecond=0),
        'eventName': 'US CPI (YoY)',
        'impact': 'high',
        'country': 'US',
        'forecast': 3.1,
        'previous': 3.3,
        'actual': None,
        'goldRelated': True,
        'expectedDirection': 'volatile',
        'rationale': 'CPI is key inflation measure. Lower CPI = bearish USD (gold up). Higher CPI = bullish USD (gold down).',
        'recommendedAction': 'Reduce position sizes by 50% before release. Use wider stops.',
        'signalStrategy': 'Pause new signals 2 hours before CPI. Resume 1 hour after release.',
        'analysis': {
            'historicalImpact': 'CPI releases cause 20-40 pip XAU/USD swings in the first 15 minutes.',
            'currentMarketContext': 'Inflation expected to moderate slightly. Market pricing in 65% chance of rate cut in September.',
            'goldPriceImplication': 'CPI < 3.0% = gold rally. CPI > 3.3% = gold sell-off.',
            'timeOfImpact': '14:00 - 15:00 UTC',
        },
    },
]

SAMPLE_LOG = [
    {
        'logId': LOG_IDS[0],
        'userId': USER_IDS[0],
        'signalId': SIGNAL_IDS[0],
        'timestamp': SERVER_TS,
        'sentVia': 'telegram',
        'telegramChatId': 'chat_12345',
        'messageId': 101,
        'status': 'sent',
        'errorMessage': '',
        'userResponse': {
            'acknowledged': False,
            'acknowledgedAt': None,
            'commandsExecuted': [],
        },
    },
    {
        'logId': LOG_IDS[1],
        'userId': USER_IDS[0],
        'signalId': SIGNAL_IDS[1],
        'timestamp': SERVER_TS,
        'sentVia': 'dashboard',
        'telegramChatId': '',
        'messageId': 0,
        'status': 'sent',
        'errorMessage': '',
        'userResponse': {
            'acknowledged': True,
            'acknowledgedAt': SERVER_TS,
            'commandsExecuted': ['/signal acknowledge'],
        },
    },
    {
        'logId': LOG_IDS[2],
        'userId': USER_IDS[1],
        'signalId': SIGNAL_IDS[2],
        'timestamp': NOW - timedelta(hours=24),
        'sentVia': 'telegram',
        'telegramChatId': 'chat_67890',
        'messageId': 89,
        'status': 'acknowledged',
        'errorMessage': '',
        'userResponse': {
            'acknowledged': True,
            'acknowledgedAt': NOW - timedelta(hours=23),
            'commandsExecuted': ['/signal acknowledge', '/trade open 0.1'],
        },
    },
]

SAMPLE_BOTLOG = [
    {
        'logId': BOTLOG_IDS[0],
        'timestamp': SERVER_TS,
        'userId': USER_IDS[0],
        'command': '/signal',
        'arguments': 'trend=up timeframe=1H',
        'status': 'success',
        'response': 'Signal generated: UP trend detected on 1H timeframe. Entry zone: 2325-2328.',
        'errorLog': '',
        'processingTimeMs': 342,
        'debugInfo': {
            'apiCallsMade': ['tradingview_data', 'signal_generator'],
            'firestoreWrites': 1,
            'externalApiCalls': ['https://tradingview-data1.p.rapidapi.com'],
        },
    },
    {
        'logId': BOTLOG_IDS[1],
        'timestamp': SERVER_TS,
        'userId': USER_IDS[0],
        'command': '/stats',
        'arguments': 'period=daily',
        'status': 'success',
        'response': 'Daily Stats: Trades: 3, Win Rate: 66.67%, PnL: +$85.20',
        'errorLog': '',
        'processingTimeMs': 215,
        'debugInfo': {
            'apiCallsMade': ['firestore_query'],
            'firestoreWrites': 0,
            'externalApiCalls': [],
        },
    },
    {
        'logId': BOTLOG_IDS[2],
        'timestamp': NOW - timedelta(hours=24),
        'userId': USER_IDS[1],
        'command': '/trade',
        'arguments': 'action=open size=0.10 entry=2310',
        'status': 'success',
        'response': 'Trade opened: Buy 0.10 XAU/USD @ 2310. TP: 2318.50 SL: 2307.00',
        'errorLog': '',
        'processingTimeMs': 456,
        'debugInfo': {
            'apiCallsMade': ['firestore_query', 'firestore_write'],
            'firestoreWrites': 2,
            'externalApiCalls': [],
        },
    },
]

COLLECTIONS = [
    ('users', 'userId', SAMPLE_USERS),
    ('signals', 'signalId', SAMPLE_SIGNALS),
    ('trades', 'tradeId', SAMPLE_TRADES),
    ('journal', 'entryId', SAMPLE_JOURNAL),
    ('analytics', 'analyticsId', SAMPLE_ANALYTICS),
    ('econCalendar', 'eventId', SAMPLE_ECON),
    ('signals_sent_log', 'logId', SAMPLE_LOG),
    ('bot_logs', 'logId', SAMPLE_BOTLOG),
]

def seed_collection(db, collection_name, id_field, documents):
    print(f"  [FOLDER] {collection_name}/")
    col_ref = db.collection(collection_name)
    for doc in documents:
        doc_id = doc[id_field]
        try:
            col_ref.document(doc_id).set(doc)
            print(f"    [OK] {doc_id}")
        except Exception as e:
            print(f"    [FAIL] {doc_id}: {str(e)}")
    print()

def print_index_instructions():
    print("  [LIST] Required Composite Indexes (create in Firebase Console)")
    print("  " + ("-" * 72))
    print()
    indexes = [
        ("signals", "userId ASC, timestamp DESC", "Dashboard signal feed"),
        ("signals", "userId ASC, status ASC, timestamp DESC", "Filter by status"),
        ("trades", "userId ASC, timestamp DESC", "Dashboard trade history"),
        ("trades", "userId ASC, status ASC, timestamp DESC", "Filter open/closed trades"),
        ("journal", "userId ASC, timestamp DESC", "Journal entries feed"),
        ("analytics", "userId ASC, period ASC", "Analytics aggregation"),
        ("econCalendar", "timestamp ASC", "Calendar timeline view"),
        ("signals_sent_log", "userId ASC, timestamp DESC", "Signal delivery log"),
        ("bot_logs", "timestamp DESC", "Bot activity log"),
        ("bot_logs", "userId ASC, timestamp DESC", "Per-user bot logs"),
    ]
    print(f"  {'Collection':<20} {'Fields':<45} {'Purpose':<30}")
    print("  " + ("-" * 95))
    for col, fields, purpose in indexes:
        print(f"  {col:<20} {fields:<45} {purpose:<30}")
    print()
    print("  [DOWN] To create an index:")
    print("     1. Open https://console.firebase.google.com/project/{}/firestore/indexes".format(PROJECT_ID))
    print("     2. Click 'Add Index'")
    print("     3. Enter Collection and Fields as shown above")
    print("     4. Click 'Create'")

def print_security_rules():
    print("  [SHIELD] Recommended Security Rules (paste in Firebase Console)")
    print("  " + ("-" * 72))
    print()
    print(r"""  rules_version = '2';
  service cloud.firestore {
    match /databases/{database}/documents {
      // Users own their data
      match /users/{userId} {
        allow read, write: if request.auth != null && request.auth.uid == userId;
      }

      // Signals - read by authenticated users, write only by admin
      match /signals/{signalId} {
        allow read: if request.auth != null;
        allow write: if request.auth != null && request.auth.token.isAdmin == true;
      }

      // Trades - users own their trades
      match /trades/{tradeId} {
        allow read, write: if request.auth != null && resource.data.userId == request.auth.uid;
        allow create: if request.auth != null && request.resource.data.userId == request.auth.uid;
      }

      // Journal - users own their entries
      match /journal/{entryId} {
        allow read, write: if request.auth != null && resource.data.userId == request.auth.uid;
        allow create: if request.auth != null && request.resource.data.userId == request.auth.uid;
      }

      // Analytics - users see their own
      match /analytics/{analyticsId} {
        allow read: if request.auth != null && resource.data.userId == request.auth.uid;
        allow write: if request.auth != null && request.auth.token.isAdmin == true;
      }

      // Economic Calendar - public read, admin write
      match /econCalendar/{eventId} {
        allow read: if true;
        allow write: if request.auth != null && request.auth.token.isAdmin == true;
      }

      // Signals Sent Log - users see their own
      match /signals_sent_log/{logId} {
        allow read: if request.auth != null && resource.data.userId == request.auth.uid;
        allow write: if request.auth != null && request.auth.token.isAdmin == true;
      }

      // Bot Logs - admin only
      match /bot_logs/{logId} {
        allow read, write: if request.auth != null && request.auth.token.isAdmin == true;
      }
    }
  }""")
    print()

def main():
    print()
    print("  [ROCKET]  AOT Analyzer Bot -- Firestore Setup Script")
    print("  " + ("-" * 50))
    print()

    db = init_firebase()

    for collection_name, id_field, documents in COLLECTIONS:
        seed_collection(db, collection_name, id_field, documents)

    print("=" * 60)
    print("  [DONE] Firestore setup complete!")
    print()
    print(f"  [WWW]  Firebase Console: https://console.firebase.google.com/project/{PROJECT_ID}/firestore/data")
    print(f"  [COLL] Collections created: {len(COLLECTIONS)}")
    docs_count = sum(len(docs) for _, _, docs in COLLECTIONS)
    print(f"  [LIST] Sample documents: {docs_count}")
    print()
    print_index_instructions()
    print()
    print_security_rules()
    print("=" * 60)

if __name__ == '__main__':
    main()
