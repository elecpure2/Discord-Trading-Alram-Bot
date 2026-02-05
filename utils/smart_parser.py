"""
Smart symbol detection for auto-detecting market type
"""

import re


# Known crypto symbols
CRYPTO_SYMBOLS = {
    "BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "MATIC", "DOT", "AVAX",
    "LINK", "UNI", "ATOM", "LTC", "ETC", "XLM", "ALGO", "VET", "ICP", "FIL",
    "NEAR", "AAVE", "GRT", "SAND", "MANA", "AXS", "APE", "CRV", "LDO", "ARB"
}

# Korean stock name to code mapping
KR_STOCK_NAMES = {
    "삼성전자": "005930",
    "SK하이닉스": "000660",
    "LG에너지솔루션": "373220",
    "삼성바이오로직스": "207940",
    "현대차": "005380",
    "기아": "000270",
    "NAVER": "035420",
    "네이버": "035420",
    "카카오": "035720",
    "삼성SDI": "006400",
    "현대모비스": "012330",
    "LG화학": "051910",
    "삼성물산": "028260",
    "포스코홀딩스": "005490",
    "KB금융": "105560",
    "신한지주": "055550",
    "셀트리온": "068270",
}


def detect_market(symbol: str) -> str:
    """
    Detect market type from symbol
    
    Args:
        symbol: Trading symbol
        
    Returns:
        'crypto', 'us_stock', or 'kr_stock'
    """
    symbol_upper = symbol.upper()
    
    # Check if it's a known crypto symbol
    if symbol_upper in CRYPTO_SYMBOLS:
        return "crypto"
    
    # Check if it's a Korean stock name
    if symbol in KR_STOCK_NAMES:
        return "kr_stock"
    
    # Check if it's a Korean stock code (6 digits)
    if re.match(r'^\d{6}$', symbol):
        return "kr_stock"
    
    # Check if it looks like crypto (ends with USDT, USD, etc.)
    if symbol_upper.endswith(('USDT', 'USD', 'BUSD', 'KRW')):
        return "crypto"
    
    # Default to US stock
    return "us_stock"


def parse_korean_number(text: str) -> float:
    """
    Parse Korean number expressions
    
    Args:
        text: Korean number text (e.g., "2천", "10만", "1억")
        
    Returns:
        Numeric value
    """
    text = text.strip()
    
    # Replace Korean units
    multipliers = {
        '천': 1000,
        '만': 10000,
        '억': 100000000,
        '조': 1000000000000
    }
    
    for unit, value in multipliers.items():
        if unit in text:
            # Extract number before unit
            parts = text.split(unit)
            if parts[0]:
                number = float(parts[0].replace(',', ''))
                return number * value
    
    # No Korean unit, just parse as number
    return float(text.replace(',', ''))


def parse_condition(text: str) -> tuple:
    """
    Parse condition from text
    
    Args:
        text: Condition text (e.g., "> 100", "100 이상", "above 100", "2천 달러 이상")
        
    Returns:
        (condition, price) tuple
        condition: 'above' or 'below'
        price: float
    """
    text = text.strip()
    
    # Remove common words like "달러", "원", etc.
    text = text.replace('달러', '').replace('원', '').replace('$', '').strip()
    
    # Pattern 1: > 100, < 100
    if match := re.match(r'^([><])[\s]*([0-9,.]+)$', text):
        operator, price = match.groups()
        condition = "above" if operator == ">" else "below"
        price = float(price.replace(',', ''))
        return condition, price
    
    # Pattern 2: 2천 이상, 10만 이하 (Korean numbers)
    if match := re.match(r'^([0-9,.]*[천만억조])[\s]*(이상|이하|위|아래)$', text):
        price_text, keyword = match.groups()
        condition = "above" if keyword in ["이상", "위"] else "below"
        price = parse_korean_number(price_text)
        return condition, price
    
    # Pattern 3: 100 이상, 100 이하
    if match := re.match(r'^([0-9,.]+)[\s]*(이상|이하|위|아래)$', text):
        price, keyword = match.groups()
        condition = "above" if keyword in ["이상", "위"] else "below"
        price = float(price.replace(',', ''))
        return condition, price
    
    # Pattern 4: above 100, below 100
    if match := re.match(r'^(above|below|over|under)[\s]+([0-9,.]+)$', text.lower()):
        keyword, price = match.groups()
        condition = "above" if keyword in ["above", "over"] else "below"
        price = float(price.replace(',', ''))
        return condition, price
    
    # Pattern 5: 2천 (Korean number without condition, default to above)
    if re.match(r'^[0-9,.]*[천만억조]$', text):
        price = parse_korean_number(text)
        return "above", price
    
    # Pattern 6: 100000 (just number, default to above)
    if match := re.match(r'^([0-9,.]+)$', text):
        price = float(text.replace(',', ''))
        return "above", price
    
    raise ValueError(f"Cannot parse condition: {text}")


def normalize_symbol(symbol: str, market: str) -> str:
    """
    Normalize symbol for API calls
    
    Args:
        symbol: Input symbol
        market: Market type
        
    Returns:
        Normalized symbol
    """
    # Korean stock: convert name to code
    if market == "kr_stock" and symbol in KR_STOCK_NAMES:
        return KR_STOCK_NAMES[symbol]
    
    # Crypto: add /USDT if needed
    if market == "crypto":
        symbol_upper = symbol.upper()
        if '/' not in symbol_upper and not symbol_upper.endswith(('USDT', 'USD', 'BUSD', 'KRW')):
            return f"{symbol_upper}/USDT"
        return symbol_upper
    
    # US stock: just uppercase
    if market == "us_stock":
        return symbol.upper()
    
    return symbol


def is_rsi_condition(text: str) -> bool:
    """
    Check if condition text is RSI-related
    
    Args:
        text: Condition text
        
    Returns:
        True if RSI condition
    """
    text_lower = text.lower()
    return 'rsi' in text_lower


def parse_rsi_condition(text: str) -> tuple:
    """
    Parse RSI condition from text
    
    Args:
        text: RSI condition text (e.g., "4h RSI < 20", "1d RSI > 70", "1시간 RSI 30미만")
        
    Returns:
        (timeframe, condition, value) tuple
        timeframe: '1h', '4h', '1d', etc.
        condition: 'above' or 'below'
        value: RSI threshold value
    """
    text = text.strip().lower()
    
    # Remove common words
    text = text.replace('봉', '').replace('rsi', '').strip()
    
    # Extract timeframe
    timeframe = None
    timeframe_patterns = {
        r'1h|1시간': '1h',
        r'4h|4시간': '4h',
        r'1d|일봉|하루': '1d',
        r'15m|15분': '15m',
        r'30m|30분': '30m',
        r'5m|5분': '5m',
        r'1m|1분': '1m'
    }
    
    for pattern, tf in timeframe_patterns.items():
        if re.search(pattern, text):
            timeframe = tf
            text = re.sub(pattern, '', text).strip()
            break
    
    # Default to 4h if not specified
    if not timeframe:
        timeframe = '4h'
    
    # Parse condition and value
    # Pattern 1: > 70, < 30
    if match := re.match(r'^([><])\s*(\d+)$', text):
        operator, value = match.groups()
        condition = "above" if operator == ">" else "below"
        return timeframe, condition, float(value)
    
    # Pattern 2: 30 미만, 70 초과
    if match := re.match(r'^(\d+)\s*(미만|이하|초과|이상)$', text):
        value, keyword = match.groups()
        condition = "above" if keyword in ["초과", "이상"] else "below"
        return timeframe, condition, float(value)
    
    # Pattern 3: above 70, below 30
    if match := re.match(r'^(above|below|over|under)\s+(\d+)$', text):
        keyword, value = match.groups()
        condition = "above" if keyword in ["above", "over"] else "below"
        return timeframe, condition, float(value)
    
    raise ValueError(f"Cannot parse RSI condition: {text}")
