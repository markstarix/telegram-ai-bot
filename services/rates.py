import aiohttp
from datetime import datetime


# ───────────── КРИПТА (CoinGecko) ─────────────

CRYPTO_IDS = {
    "btc": "bitcoin", "биткоин": "bitcoin", "bitcoin": "bitcoin",
    "eth": "ethereum", "эфир": "ethereum", "ethereum": "ethereum",
    "sol": "solana", "солана": "solana", "solana": "solana",
    "bnb": "binancecoin", "бнб": "binancecoin",
    "xrp": "ripple", "рипл": "ripple",
    "ton": "the-open-network", "тон": "the-open-network",
    "usdt": "tether", "юсдт": "tether",
    "ltc": "litecoin", "лайткоин": "litecoin",
    "doge": "dogecoin", "додж": "dogecoin", "dogecoin": "dogecoin",
    "avax": "avalanche-2", "аваланч": "avalanche-2",
    "dot": "polkadot", "полкадот": "polkadot",
    "ada": "cardano", "кардано": "cardano",
    "trx": "tron", "трон": "tron",
    "link": "chainlink", "чейнлинк": "chainlink",
}

# Валюты ЦБ РФ (ISO коды)
FIAT_KEYWORDS = {
    "доллар": "USD", "usd": "USD", "$": "USD", "dollar": "USD",
    "евро": "EUR", "euro": "EUR", "eur": "EUR",
    "юань": "CNY", "cny": "CNY", "yuan": "CNY",
    "фунт": "GBP", "gbp": "GBP",
    "франк": "CHF", "chf": "CHF",
    "йена": "JPY", "jpy": "JPY",
}


async def get_crypto_price(coin_id: str) -> str | None:
    """Получает курс крипты через CoinGecko (бесплатно, без ключа)"""
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd,rub&include_24hr_change=true"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                data = await resp.json()
                if coin_id not in data:
                    return None
                d = data[coin_id]
                usd = d.get("usd", 0)
                rub = d.get("rub", 0)
                change = d.get("usd_24h_change", 0)
                arrow = "📈" if change >= 0 else "📉"
                return (
                    f"{arrow} <b>{coin_id.upper()}</b>\n"
                    f"💵 ${usd:,.2f}\n"
                    f"🇷🇺 {rub:,.0f} ₽\n"
                    f"24ч: {change:+.2f}%"
                )
    except Exception:
        return None


async def get_cbr_rates() -> str | None:
    """Получает курсы валют ЦБ РФ"""
    url = "https://www.cbr-xml-daily.ru/daily_json.js"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                data = await resp.json(content_type=None)
                valutes = data.get("Valute", {})
                date = data.get("Date", "")[:10]
                lines = [f"💱 <b>Курсы ЦБ РФ на {date}</b>\n"]
                for code in ["USD", "EUR", "CNY", "GBP", "CHF"]:
                    if code in valutes:
                        v = valutes[code]
                        lines.append(f"{v['CharCode']}: {v['Value']:.2f} ₽")
                return "\n".join(lines)
    except Exception:
        return None


async def get_single_fiat_rate(currency_code: str) -> str | None:
    """Получает курс одной валюты ЦБ РФ"""
    url = "https://www.cbr-xml-daily.ru/daily_json.js"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                data = await resp.json(content_type=None)
                valutes = data.get("Valute", {})
                if currency_code in valutes:
                    v = valutes[currency_code]
                    change = v["Value"] - v["Previous"]
                    arrow = "📈" if change >= 0 else "📉"
                    return (
                        f"{arrow} <b>{v['Name']}</b> ({v['CharCode']})\n"
                        f"🇷🇺 {v['Value']:.2f} ₽\n"
                        f"Изменение: {change:+.2f} ₽"
                    )
    except Exception:
        return None


def detect_rates_request(text: str) -> tuple[str, str] | None:
    """
    Определяет запрос курса в тексте.
    Возвращает ('crypto', coin_id) или ('fiat', currency_code) или None
    """
    text_lower = text.lower()

    # Ключевые слова которые говорят что речь о курсе
    rate_keywords = ["курс", "цена", "стоит", "сколько", "почём", "rate", "price"]
    is_rate_request = any(kw in text_lower for kw in rate_keywords)

    # Проверяем крипту
    for keyword, coin_id in CRYPTO_IDS.items():
        if keyword in text_lower:
            return ("crypto", coin_id)

    # Проверяем фиат — только если явный запрос курса
    if is_rate_request:
        for keyword, code in FIAT_KEYWORDS.items():
            if keyword in text_lower:
                return ("fiat", code)

    return None
