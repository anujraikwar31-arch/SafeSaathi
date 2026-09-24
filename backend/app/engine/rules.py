"""Red-flag rules: fast, explainable, and the reason text when Gemini is unavailable."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    name: str
    pattern: str
    reason_en: str
    reason_hi: str
    hard: bool = False          # hard flags alone are enough to call something a scam
    category: str | None = None


RULES: list[Rule] = [
    Rule("asks_secret",
         r"(share|send|tell|give|batao|bhejo|bata\s?do|forward)\W+(\w+\W+){0,4}(otp|o\.t\.p|pin|cvv|password|passcode)|(ओटीपी|पिन|पासवर्ड)\s*(\S+\s*){0,3}(बताएं|बताइए|भेजें|साझा)",
         "Asks you to share an OTP, PIN or password.",
         "यह मैसेज ओटीपी, पिन या पासवर्ड मांग रहा है।", hard=True),
    Rule("pin_to_receive",
         r"\b(pin|otp)\b.{0,40}(receive|claim|credit|get)|(receive|claim|credit)\b.{0,40}\b(pin|otp)\b",
         "Asks for a PIN to receive money. Receiving money never needs a PIN.",
         "पैसे पाने के लिए पिन मांगा जा रहा है। पैसे लेने में पिन कभी नहीं लगता।",
         hard=True, category="upi_cashback_collect"),
    Rule("kyc",
         r"\bk\.?y\.?c\b|\bpan\b.{0,20}(update|verify)|aadhaar.{0,20}(update|verify|link)|केवाईसी|आधार\s*(अपडेट|लिंक|सत्यापन)",
         "Talks about KYC or Aadhaar updates, a common bank-scam trick.",
         "केवाईसी या आधार अपडेट का बहाना, जो आम बैंक ठगी है।", category="kyc_account_block"),
    Rule("account_block",
         r"\b(block(ed)?|suspend(ed)?|deactivat\w*|freeze|frozen|band ho)\b|(खाता|अकाउंट|सेवा|नंबर)\s*(\S+\s*){0,3}(बंद|ब्लॉक|बन्द)",
         "Threatens to block or freeze your account.",
         "खाता बंद या फ्रीज़ करने की धमकी दी जा रही है।", category="kyc_account_block"),
    Rule("urgency",
         r"\b(today|tonight|immediately|urgent(ly)?|right now|within \d+ ?(hours?|hrs?|minutes?|mins?)|last chance|turant|abhi|aaj hi)\b|तुरंत|अभी|आज ही|आज रात|सिर्फ़ आज|अंतिम मौका",
         "Rushes you with a deadline so you act before you think.",
         "जल्दबाज़ी में फैसला कराने के लिए समय सीमा दी गई है।"),
    Rule("power_cut",
         r"(electricity|bijli|power|meter).{0,50}(disconnect|cut|kat|band)|(बिजली|कनेक्शन).{0,40}(काट|कट|बंद)",
         "Threatens to cut your electricity, a known scam script.",
         "बिजली काटने की धमकी, जो एक जानी-पहचानी ठगी है।", category="electricity_bill"),
    Rule("job_fee",
         r"(part[- ]?time|work from home|daily income|task|like.{0,15}(video|youtube)|telegram task).{0,90}(fee|pay|deposit|registration|joining|rs\.?\s?\d+|₹\s?\d+)|घर बैठे.{0,40}(कमाएं|कमाई)|रोज़?ाना.{0,20}कमाएं",
         "A job offer that asks you to pay or deposit money first.",
         "नौकरी के नाम पर पहले पैसे जमा करने को कहा जा रहा है।", category="job_task"),
    Rule("guaranteed",
         r"(guaranteed|assured|fixed|100%)\s+(return|returns|profit|income)|\b\d+\s?x\s+(return|returns|profit)|double (your )?money|paisa double|पैसा\s*(दोगुना|डबल)|(पक्का|गारंटी|निश्चित)\s*(मुनाफ़ा|मुनाफा|रिटर्न|लाभ)|दोगुना करें",
         "Promises guaranteed or fixed returns, which no real adviser can do.",
         "पक्के मुनाफ़े का वादा, जो कोई असली सलाहकार नहीं कर सकता।", category="investment"),
    Rule("digital_arrest",
         r"digital arrest|\bcbi\b|\bed\b\s+(officer|department)|narcotics|money laundering|arrest warrant|customs.{0,30}(parcel|seiz)|cyber (crime )?(branch|cell)|डिजिटल अरेस्ट|साइबर क्राइम (ब्रांच|सेल)|गिरफ्तार",
         "Pretends to be police, CBI or customs, which real officers never do by call or SMS.",
         "पुलिस, सीबीआई या कस्टम्स बनकर डराया जा रहा है।",
         hard=True, category="parcel_digital_arrest"),
    Rule("prize",
         r"lottery|lucky draw|\bkbc\b|you have won|jackpot|prize money|scratch card|लॉटरी|लकी ड्रॉ|इनाम|पुरस्कार जीत",
         "Offers a prize for a contest you never entered.",
         "बिना किसी प्रतियोगिता के इनाम का लालच दिया जा रहा है।", category="lottery_prize"),
    Rule("loan_app",
         r"(instant|quick|urgent)\s+loan|loan approved|pre[- ]?approved loan.{0,40}(click|link|apply)|तुरंत लोन|बिना दस्तावेज़.{0,20}लोन",
         "Offers an instant loan through a link, a common loan-app trap.",
         "लिंक के ज़रिए तुरंत लोन का झांसा, जो आम लोन ऐप जाल है।", category="loan_app"),
    Rule("refund_mistake",
         r"(sent|transferred|paid).{0,40}(by mistake|wrongly|galti se).{0,40}(return|refund|wapas)|screenshot attached",
         "Claims money was sent by mistake and asks you to return it.",
         "गलती से पैसे भेजने का दावा करके वापसी मांगी जा रही है।", category="fake_payment"),
    Rule("apk",
         r"\.apk\b|install (this )?(app|apk) (from|through) (the )?link|(ऐप|एप्प).{0,20}इंस्टॉल करें.{0,30}(लिंक|link)",
         "Asks you to install an app file from outside the app store.",
         "ऐप स्टोर के बाहर से ऐप इंस्टॉल करने को कहा जा रहा है।", hard=True),
    Rule("shortener",
         r"(bit\.ly|tinyurl|cutt\.ly|is\.gd|rb\.gy|t\.ly|shorturl|rebrand\.ly|linktr)",
         "Hides the real website behind a shortened link.",
         "असली वेबसाइट छिपाने के लिए छोटा लिंक इस्तेमाल हुआ है।"),
    Rule("relative_emergency",
         r"(mummy|papa|mom|dad|uncle|beta).{0,40}(accident|hospital|police|urgent money)|send money.{0,30}(urgent|emergency)",
         "Pretends a relative is in trouble and needs money now.",
         "रिश्तेदार की मुसीबत बताकर तुरंत पैसे मांगे जा रहे हैं।", category="relative_emergency"),
]

_SAFE_OTP = re.compile(
    r"(do not|don'?t|never|kabhi|mat)\s+(share|disclose|tell|give|batao|bhejo)", re.I)

_COMPILED = [(r, re.compile(r.pattern, re.I)) for r in RULES]
BY_NAME = {r.name: r for r in RULES}


def check(text: str) -> list[str]:
    """Return the names of the rules that matched."""
    if not text:
        return []
    hits = [rule.name for rule, pattern in _COMPILED if pattern.search(text)]
    # Genuine bank OTP messages say "do not share this OTP" - that is the opposite of a scam.
    if "asks_secret" in hits and _SAFE_OTP.search(text):
        hits.remove("asks_secret")
    if "pin_to_receive" in hits and _SAFE_OTP.search(text):
        hits.remove("pin_to_receive")
    return hits


def reasons(hits: list[str], lang: str = "en", limit: int = 3) -> list[str]:
    out = []
    for name in hits[:limit]:
        rule = BY_NAME.get(name)
        if not rule:
            continue
        out.append(rule.reason_hi if lang == "hi" else rule.reason_en)
    return out


def category_for(hits: list[str]) -> str | None:
    for name in hits:
        rule = BY_NAME.get(name)
        if rule and rule.category:
            return rule.category
    return None


def hard_hits(hits: list[str]) -> list[str]:
    return [h for h in hits if BY_NAME.get(h) and BY_NAME[h].hard]
