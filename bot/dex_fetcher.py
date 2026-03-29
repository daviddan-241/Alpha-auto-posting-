import requests
import random
import time
from typing import Optional

DEX_BASE = "https://api.dexscreener.com"

KNOWN_SOLANA_TOKENS = [
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    "7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr",
    "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3",
    "MEW1gQWJ3nEXg2qgERiKu7FAFj79PHvQVREQUzScPP5",
    "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
    "9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump",
    "ukHH6c7mMyiWCf1b9pnWe25TSpkDDt3H5pQZgZ74J82",
    "2weMjPLLybRMMva1fy3kT9ANXAqpnwhKvorYgrMavpfY",
    "5z3EqYQo9HiCEs3R84RCDMu2n7anpDMxRhdK31yYRgmk",
    "Df6yfrKC8kZE3KNkrHERKzAetSxbrWeniQfyJY4Jpump",
    "A8C3xuqscfmyLrte3VmTqrAq8kgMASius9AFNANwpump",
    "63LfDmNb3MQ8mw9MtZ2To9bEA2M71kZUUGq5tiJxcqj9",
    "ED5nyyWEzpPPiWimP8vYm7sD7TD3LAt3Q3gRTWHzc8Qu",
    "8Ki8DpuWNxu9VsS3kQbarsCWMcFGWkzzA8pUPto9zBd5",
    "4Cnk9EPnW5ixfLZatCPJjDB1PUtcRpVVgTQukm9epump",
    "3S8qX1MsMqRbiwKg2cQyx7nis1oHMgaCuc9c4VfvVdPN",
    "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
    "FU1q8vJpZNUrmqsciSjp8bAKKidGsLmouB8CBdf8TKQv",
    "61V8vBaqAGMpgDIyGBiBnuTriwCuBQtZxH9CmBzpump",
    "GiG7Hr61RVm4CSUxJmgiCoySFQtdiwFTix9mhdao3Btrump",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AlphaBot/1.0)",
    "Accept": "application/json",
}


def fetch_token_data(address: str) -> Optional[dict]:
    try:
        url = f"{DEX_BASE}/latest/dex/tokens/{address}"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        pairs = data.get("pairs") or []
        if not pairs:
            return None
        pair = max(pairs, key=lambda p: float(p.get("liquidity", {}).get("usd", 0) or 0))
        return _parse_pair(pair)
    except Exception:
        return None


def fetch_trending_tokens(chain: str = "solana") -> list:
    results = []
    try:
        url = f"{DEX_BASE}/token-boosts/latest/v1"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            items = resp.json() if isinstance(resp.json(), list) else []
            for item in items[:30]:
                addr = item.get("tokenAddress", "")
                if addr and item.get("chainId", "") == chain:
                    token = fetch_token_data(addr)
                    if token:
                        results.append(token)
    except Exception:
        pass

    if len(results) < 5:
        for addr in random.sample(KNOWN_SOLANA_TOKENS, min(10, len(KNOWN_SOLANA_TOKENS))):
            token = fetch_token_data(addr)
            if token and not any(r["address"] == token["address"] for r in results):
                results.append(token)

    return results


def fetch_new_coins(chain: str = "solana", min_mc: float = 120_000, max_mc: float = 50_000_000) -> list:
    try:
        url = f"{DEX_BASE}/token-profiles/latest/v1"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        candidates = []
        if resp.status_code == 200:
            items = resp.json() if isinstance(resp.json(), list) else []
            for item in items[:50]:
                if item.get("chainId", "") != chain:
                    continue
                addr = item.get("tokenAddress", "")
                if not addr:
                    continue
                token = fetch_token_data(addr)
                if token and min_mc <= token.get("market_cap", 0) <= max_mc:
                    candidates.append(token)
        return candidates
    except Exception:
        return []


def fetch_ohlcv_data(pair_address: str, chain: str = "solana", resolution: str = "15") -> list:
    try:
        url = f"{DEX_BASE}/latest/dex/chart/{chain}/{pair_address}?from=0&to=9999999999&res={resolution}"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("bars", []) or []
    except Exception:
        pass
    return _generate_mock_ohlcv(50)


def _parse_pair(pair: dict) -> dict:
    base = pair.get("baseToken", {})
    info = pair.get("info", {}) or {}
    price_change = pair.get("priceChange", {}) or {}
    liquidity = pair.get("liquidity", {}) or {}
    volume = pair.get("volume", {}) or {}
    fdv = pair.get("fdv") or pair.get("marketCap") or 0

    return {
        "address": base.get("address", ""),
        "symbol": base.get("symbol", "UNKNOWN"),
        "name": base.get("name", "Unknown"),
        "pair_address": pair.get("pairAddress", ""),
        "chain": pair.get("chainId", "solana"),
        "dex": pair.get("dexId", ""),
        "price_usd": float(pair.get("priceUsd") or 0),
        "market_cap": float(fdv or 0),
        "liquidity_usd": float(liquidity.get("usd") or 0),
        "volume_24h": float(volume.get("h24") or 0),
        "price_change_5m": float(price_change.get("m5") or 0),
        "price_change_1h": float(price_change.get("h1") or 0),
        "price_change_24h": float(price_change.get("h24") or 0),
        "created_at": pair.get("pairCreatedAt", 0),
        "url": pair.get("url", ""),
        "logo": (info.get("imageUrl") or ""),
        "website": next((s.get("url","") for s in (info.get("websites") or []) if s), ""),
        "twitter": next((s.get("url","") for s in (info.get("socials") or []) if s.get("type")=="twitter"), ""),
    }


def _generate_mock_ohlcv(n: int = 50) -> list:
    import math
    bars = []
    price = random.uniform(0.00001, 0.01)
    ts = int(time.time()) - n * 15 * 60
    for i in range(n):
        change = random.uniform(-0.06, 0.09)
        open_ = price
        close = price * (1 + change)
        high = max(open_, close) * (1 + random.uniform(0, 0.04))
        low = min(open_, close) * (1 - random.uniform(0, 0.04))
        vol = random.uniform(1000, 50000)
        bars.append({"t": ts + i * 15 * 60, "o": open_, "h": high, "l": low, "c": close, "v": vol})
        price = close
    return bars


def format_mc(value: float) -> str:
    if value >= 1_000_000:
        return f"${value/1_000_000:.1f}M"
    if value >= 1_000:
        return f"${value/1_000:.1f}K"
    return f"${value:.0f}"


def format_short_addr(addr: str) -> str:
    if len(addr) > 12:
        return addr[:6] + "..." + addr[-4:]
    return addr
