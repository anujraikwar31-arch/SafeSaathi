"""Link checks: lookalike domains, domain age, shorteners, Google Safe Browsing.

Every call has a short timeout and swallows its own errors. A check that fails is
simply left out of the evidence; it never breaks an answer.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import difflib
import re
from typing import Any

import httpx

from ..config import settings

# Real sites people are made to think they are visiting. M6 keeps this list growing.
OFFICIAL = {
    "sbi.co.in", "onlinesbi.sbi", "hdfcbank.com", "icicibank.com", "axisbank.com",
    "kotak.com", "pnbindia.in", "bankofbaroda.in", "unionbankofindia.co.in",
    "paytm.com", "phonepe.com", "gpay.app.goo.gl", "npci.org.in", "bhimupi.org.in",
    "uidai.gov.in", "incometax.gov.in", "epfindia.gov.in", "indiapost.gov.in",
    "cybercrime.gov.in", "sancharsaathi.gov.in", "irctc.co.in", "amazon.in", "flipkart.com",
}
BRANDS = [
    "sbi", "hdfc", "icici", "axis", "kotak", "pnb", "baroda", "canara", "union",
    "paytm", "phonepe", "gpay", "googlepay", "bhim", "npci", "upi",
    "aadhaar", "uidai", "incometax", "epfo", "indiapost", "irctc", "amazon", "flipkart",
]
SHORTENERS = {"bit.ly", "tinyurl.com", "cutt.ly", "is.gd", "rb.gy", "t.ly", "shorturl.at",
              "rebrand.ly", "linktr.ee", "surl.li", "shorturl.com", "ow.ly", "buff.ly"}
RISKY_TLDS = {"xyz", "top", "click", "online", "site", "live", "icu", "buzz", "vip",
              "shop", "fit", "rest", "cfd", "sbs", "bond", "info", "link", "work"}
MULTI_SUFFIXES = {"co.in", "net.in", "org.in", "gen.in", "firm.in", "ind.in", "gov.in",
                  "nic.in", "ac.in", "edu.in", "res.in", "bank.in", "fin.in", "co.uk",
                  "org.uk", "com.au", "co.jp", "com.br", "app.goo.gl"}

_URL_RE = re.compile(
    r"\b((?:https?://|www\.)[^\s<>\"']+|(?:[a-z0-9][a-z0-9\-]{1,62}\.)+(?:com|in|net|org|co|io|me|xyz|top|click|online|site|live|icu|buzz|vip|shop|info|link|app|dev|store|fit|cfd|sbs)(?:/[^\s<>\"']*)?)",
    re.I,
)


def undefang(text: str) -> str:
    """Turn site[.]in or hxxp:// back into something we can parse."""
    out = re.sub(r"\[\s*\.\s*\]", ".", text or "")
    out = re.sub(r"\(\s*\.\s*\)", ".", out)
    return re.sub(r"\bhxxp", "http", out, flags=re.I)


def extract(text: str) -> list[str]:
    seen, urls = set(), []
    for match in _URL_RE.finditer(undefang(text or "")):
        url = match.group(1).rstrip(".,);:!?'\"")
        if not url.lower().startswith("http"):
            url = "http://" + url
        if url.lower() not in seen:
            seen.add(url.lower())
            urls.append(url)
    return urls[:5]


def host_of(url: str) -> str:
    host = re.sub(r"^https?://", "", url, flags=re.I).split("/")[0].split("?")[0]
    return host.split("@")[-1].split(":")[0].lower().strip(".")


def registered_domain(host: str) -> str:
    parts = [p for p in host.split(".") if p]
    if len(parts) <= 2:
        return ".".join(parts)
    if ".".join(parts[-2:]) in MULTI_SUFFIXES:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def lookalike(domain: str) -> str | None:
    if not domain or domain in OFFICIAL:
        return None
    if domain.endswith((".gov.in", ".nic.in", ".bank.in")):
        return None                      # RBI moved Indian banks to .bank.in addresses
    name = domain.split(".")[0]
    rest = domain.rsplit(".", 1)[0]
    for brand in BRANDS:
        if brand in name or brand in rest.replace(".", ""):
            return f"uses the name '{brand}' but is not an official site"
    for official in OFFICIAL:
        if difflib.SequenceMatcher(None, domain, official).ratio() >= 0.85:
            return f"looks almost the same as {official}"
    return None


async def expand(url: str, client: httpx.AsyncClient) -> str | None:
    try:
        response = await client.get(url, follow_redirects=True)
        return str(response.url)
    except Exception:
        return None


async def domain_age_days(domain: str, client: httpx.AsyncClient) -> int | None:
    try:
        response = await client.get(f"https://rdap.org/domain/{domain}")
        if response.status_code != 200:
            return None
        for event in response.json().get("events", []):
            if event.get("eventAction") == "registration":
                born = dt.datetime.fromisoformat(
                    event["eventDate"].replace("Z", "+00:00"))
                return (dt.datetime.now(dt.timezone.utc) - born).days
    except Exception:
        return None
    return None


async def safe_browsing(urls: list[str], client: httpx.AsyncClient) -> set[str]:
    if not settings.safe_browsing_key or not urls:
        return set()
    body = {
        "client": {"clientId": "safesaathi", "clientVersion": "1.0"},
        "threatInfo": {
            "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE",
                            "POTENTIALLY_HARMFUL_APPLICATION"],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": u} for u in urls],
        },
    }
    try:
        response = await client.post(
            "https://safebrowsing.googleapis.com/v4/threatMatches:find",
            params={"key": settings.safe_browsing_key}, json=body)
        matches = response.json().get("matches", [])
        return {m["threat"]["url"] for m in matches}
    except Exception:
        return set()


async def check_all(text: str, timeout: float = 5.0) -> list[dict[str, Any]]:
    urls = extract(text)
    if not urls:
        return []
    out: list[dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False,
                                     headers={"User-Agent": "SafeSaathi/1.0"}) as client:
            flagged = await safe_browsing(urls, client)
            for url in urls:
                host = host_of(url)
                domain = registered_domain(host)
                signal: dict[str, Any] = {
                    "url": url, "domain": domain,
                    "shortened": domain in SHORTENERS,
                    "expanded_to": None, "age_days": None, "lookalike": None,
                    "risky_tld": domain.rsplit(".", 1)[-1] in RISKY_TLDS,
                    "safe_browsing": url in flagged,
                }
                if signal["shortened"]:
                    expanded = await expand(url, client)
                    if expanded and host_of(expanded) != host:
                        signal["expanded_to"] = expanded
                        host = host_of(expanded)
                        domain = registered_domain(host)
                        signal["domain"] = domain
                        signal["risky_tld"] = domain.rsplit(".", 1)[-1] in RISKY_TLDS
                signal["lookalike"] = lookalike(domain)
                signal["age_days"] = await domain_age_days(domain, client)
                out.append(signal)
    except Exception:
        return out
    return out


def link_reasons(links: list[dict[str, Any]], lang: str = "en") -> list[str]:
    out: list[str] = []
    for link in links:
        domain = link.get("domain", "")
        if link.get("safe_browsing"):
            out.append(f"{domain} को गूगल ने खतरनाक बताया है।" if lang == "hi"
                       else f"Google has flagged {domain} as dangerous.")
        elif link.get("lookalike"):
            out.append(f"लिंक {domain} असली साइट जैसा दिखता है, पर है नहीं।" if lang == "hi"
                       else f"The link {domain} {link['lookalike']}.")
        elif link.get("age_days") is not None and link["age_days"] < 30:
            out.append(f"यह वेबसाइट सिर्फ़ {link['age_days']} दिन पुरानी है।" if lang == "hi"
                       else f"The website {domain} was registered only {link['age_days']} days ago.")
        elif link.get("shortened"):
            out.append("छोटा लिंक असली पता छिपा रहा है।" if lang == "hi"
                       else "A shortened link hides where it really goes.")
        elif link.get("risky_tld"):
            out.append(f"{domain} जैसे पते अक्सर ठगी में इस्तेमाल होते हैं।" if lang == "hi"
                       else f"Addresses like {domain} are often used in scams.")
    return out[:2]


def worst(links: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not links:
        return None

    def score(link: dict[str, Any]) -> int:
        value = 0
        value += 100 if link.get("safe_browsing") else 0
        value += 60 if link.get("lookalike") else 0
        value += 40 if (link.get("age_days") is not None and link["age_days"] < 30) else 0
        value += 20 if link.get("shortened") else 0
        value += 15 if link.get("risky_tld") else 0
        return value

    return max(links, key=score)
