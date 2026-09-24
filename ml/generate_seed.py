"""Build the seed corpus.

These are message *templates* written by the team from public scam advisories, news
reports and messages on our own phones, with every real name, number and link replaced
by a slot. The generator fills the slots to create training rows.

Two things matter for honest numbers:

1. The test templates are written separately and never appear in training, so the test
   set measures new wording, not memorised strings.
2. Real forwarded messages collected during the pilot go into data/collected.csv and are
   merged here, so the model improves as the team gathers more.

Run:  python ml/generate_seed.py
"""
from __future__ import annotations

import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "ml" / "data"
DATA.mkdir(parents=True, exist_ok=True)

rng = random.Random(7)

SLOTS = {
    "amount": ["499", "999", "1,999", "2,000", "4,500", "5,000", "10,000", "25,000", "49,999"],
    "phone": ["9876543221", "7012345689", "8890012345", "6303456789", "9123456780"],
    "link": ["http://kyc-update-bnk.in", "http://sbi-rewards.xyz", "http://verify-account.top",
             "http://bit.ly/3xKyc9", "http://india-post-parcel.online", "http://loan-approve.site",
             "http://electricity-bill-pay.click", "http://upi-cashback.vip"],
    "bank": ["SBI", "HDFC Bank", "ICICI Bank", "Axis Bank", "Punjab National Bank", "Bank of Baroda"],
    "time": ["9:30 PM", "10 PM", "midnight", "6 PM today", "8:30 PM"],
    "name": ["Rahul", "Priya", "Amit", "Sunita", "Vikram", "Meena"],
    "app": ["Paytm", "PhonePe", "Google Pay", "BHIM"],
    "code": ["887312", "445120", "902344", "771205"],
    "days": ["24 hours", "2 hours", "today", "tonight"],
    "upi": ["rahul.verma@okaxis", "winner2026@ybl", "support.care@ibl", "refund.help@paytm"],
    "company": ["Amazon", "Flipkart", "Blue Dart", "India Post", "Delhivery"],
    "hours": ["2", "3", "4"],
}


def fill(template: str, rng: random.Random) -> str:
    out = template
    for key, options in SLOTS.items():
        token = "{" + key + "}"
        while token in out:
            out = out.replace(token, rng.choice(options), 1)
    return out


# --------------------------------------------------------------- TRAIN SCAMS
TRAIN_SCAM = [
    ("kyc_account_block", "en", "Dear Customer, your KYC has expired and your account will be BLOCKED today. Update now: {link}"),
    ("kyc_account_block", "en", "{bank} alert: your account is suspended due to incomplete KYC. Complete verification within {days} at {link}"),
    ("kyc_account_block", "en", "Your PAN card is not linked with your bank account. Account will be frozen. Click {link} to update immediately."),
    ("kyc_account_block", "hinglish", "Aapka {bank} account band ho jayega. KYC turant update karein {link} par."),
    ("kyc_account_block", "hi", "आपका खाता आज बंद हो जाएगा। केवाईसी तुरंत अपडेट करें: {link}"),
    ("kyc_account_block", "en", "Dear user, your net banking will be deactivated tonight. Verify your details here {link} and share the OTP with our executive."),
    ("electricity_bill", "en", "Dear consumer, your electricity connection will be disconnected tonight at {time} as your last bill was not updated. Call officer {phone} immediately."),
    ("electricity_bill", "en", "Electricity bill pending. Power supply will be cut {days}. Pay Rs {amount} now at {link} or call {phone}."),
    ("electricity_bill", "hinglish", "Bijli connection aaj raat {time} par kaat diya jayega. Turant officer {phone} ko call karein."),
    ("electricity_bill", "hi", "आपका बिजली बिल बकाया है। आज रात कनेक्शन काट दिया जाएगा। तुरंत {phone} पर संपर्क करें।"),
    ("parcel_digital_arrest", "en", "This is Cyber Crime Branch. A parcel in your name contains illegal items. Stay on this video call or face arrest."),
    ("parcel_digital_arrest", "en", "Customs has seized your parcel. Your Aadhaar is linked to money laundering. Call {phone} to avoid arrest warrant."),
    ("parcel_digital_arrest", "en", "{company} courier: your package is held at customs. Pay Rs {amount} clearance fee at {link} within {days}."),
    ("parcel_digital_arrest", "hi", "यह साइबर क्राइम ब्रांच है। आपके नाम से आए पार्सल में ड्रग्स मिली है। वीडियो कॉल पर बने रहें।"),
    ("job_task", "en", "Congratulations! You are selected for a part-time job. Earn Rs {amount} daily by liking YouTube videos. Pay Rs 499 registration fee to start."),
    ("job_task", "en", "Work from home job. {hours} hours daily, salary Rs {amount} per day. Join our Telegram group and complete simple tasks. Deposit Rs {amount} to unlock tasks."),
    ("job_task", "hinglish", "Ghar baithe kaam karein, roz Rs {amount} kamayein. Registration fee Rs 499 jama karein, HR se WhatsApp par baat karein {phone}."),
    ("job_task", "en", "HR here from a hiring company. Your resume is shortlisted for online data entry. Pay a refundable security deposit of Rs {amount} to get your ID."),
    ("investment", "en", "Join our VIP stock group. Our expert's tips gave members 3X returns in 30 days. Guaranteed profit. Only 20 seats left. Pay Rs {amount} to join."),
    ("investment", "en", "Invest Rs {amount} in our trading app and get assured returns of 15% every month. Limited time offer, click {link}."),
    ("investment", "hinglish", "Crypto trading se roz ka profit! Guaranteed return, koi risk nahi. Abhi {link} par register karein."),
    ("investment", "hi", "हमारे ट्रेडिंग ग्रुप से जुड़ें और हर महीने पक्का मुनाफ़ा पाएं। सिर्फ़ आज के लिए {link} पर रजिस्टर करें।"),
    ("upi_cashback_collect", "en", "Rs {amount} cashback received! Accept the request and enter your UPI PIN to claim it now."),
    ("upi_cashback_collect", "en", "{app} reward: you have won Rs {amount}. Scan the QR and enter your PIN to receive the money in your account."),
    ("upi_cashback_collect", "hinglish", "Aapko Rs {amount} ka refund mila hai. Paisa lene ke liye UPI PIN daalein aur request accept karein."),
    ("upi_cashback_collect", "en", "Your payment of Rs {amount} failed. To receive the refund, send a collect request approval and share the OTP {code}."),
    ("lottery_prize", "en", "Congratulations! Your number has won Rs 25,00,000 in the KBC lucky draw. Call {phone} and pay Rs {amount} processing fee to claim."),
    ("lottery_prize", "en", "You have won an {company} lucky draw prize. Claim your gift by paying delivery charges of Rs {amount} at {link}."),
    ("lottery_prize", "hi", "बधाई हो! आपका नंबर लकी ड्रॉ में चुना गया है। इनाम पाने के लिए {phone} पर कॉल करें।"),
    ("loan_app", "en", "Instant loan approved! Rs {amount} credited in 5 minutes, no documents needed. Download the app from {link} and share your OTP."),
    ("loan_app", "hinglish", "Bina document ke loan Rs {amount} turant. Abhi apply karein {link} aur apna Aadhaar number bhejein."),
    ("fake_payment", "en", "Sir, I sent Rs {amount} to your number by mistake. Please return it to {upi}. Screenshot attached."),
    ("fake_payment", "en", "Payment of Rs {amount} done, screenshot attached. Please deliver the order, the amount will reflect in {hours} hours."),
    ("relative_emergency", "en", "Papa, my phone is broken, this is my new number. I need Rs {amount} urgently for a hospital payment. Send it to {upi}."),
    ("relative_emergency", "hinglish", "Mummy mera accident ho gaya hai, {amount} rupay turant is number par bhej do, phone baad me karta hoon."),
    ("other_scam", "en", "Your {app} account will be closed for suspicious activity. Verify with the OTP {code} that our officer sends you now."),
    ("other_scam", "en", "Install this APK to check your electricity bill: {link}. Only this app works for bill payment now."),
    ("other_scam", "hi", "आपके नंबर पर आया ओटीपी हमारे अधिकारी को बताएं, वरना सेवा बंद कर दी जाएगी।"),
]

# ------------------------------------------------------------- TRAIN GENUINE
TRAIN_GENUINE = [
    ("en", "Your OTP for the transaction of Rs {amount} is {code}. Do not share this OTP with anyone. - {bank}"),
    ("en", "{code} is your one time password for login. Valid for 10 minutes. Never share it with anyone, including bank staff."),
    ("en", "Rs {amount} debited from A/c XX4412 on 12-09-26 to {name}. Not you? Call {bank} customer care on the number printed on your card."),
    ("en", "Rs {amount} credited to your account XX9032 as salary for September 2026. Available balance Rs 62,410."),
    ("en", "Your {company} order has been shipped and will arrive today between 2 PM and 6 PM. Track it in the app."),
    ("en", "Your {company} package was delivered to {name}. Thank you for shopping with us."),
    ("en", "Your electricity bill of Rs {amount} for August is due on 28-09-2026. Pay through your provider's official app or website."),
    ("en", "Your gas cylinder booking is confirmed. Delivery within {hours} days. Booking number {code}."),
    ("en", "Appointment confirmed at City Hospital on 26 September at 11:00 AM with Dr. {name}. Reference {code}. Please arrive 15 minutes early."),
    ("en", "Your train ticket PNR {code} is confirmed. Coach S4, seat 42. Happy journey, {name}."),
    ("en", "Dear parent of {name}, the school will remain closed tomorrow due to heavy rain. Classes resume on Monday."),
    ("en", "Your mobile recharge of Rs {amount} is successful. Validity 28 days. Enjoy unlimited calls."),
    ("en", "Reminder: your credit card statement of Rs {amount} is due on 30-09-2026. Pay through the bank app."),
    ("en", "{bank}: your new debit card has been dispatched to {name} and will reach you in 5 working days."),
    ("en", "Your UPI transaction of Rs {amount} to {name} is successful. UPI reference 447120311902."),
    ("en", "Your loan EMI of Rs {amount} has been processed successfully for this month. No action needed."),
    ("en", "Thank you for visiting our clinic, {name}. Report {code} is ready and can be collected from the reception."),
    ("en", "Your booking at Hotel Meera for 2 nights is confirmed under {name}. Booking id {code}. Check-in 2 PM on 30 September."),
    ("hinglish", "Aapka OTP {code} hai. Kisi ke saath share na karein. - {bank}"),
    ("hinglish", "Aapke account se Rs {amount} debit hue hain. Balance Rs 12,340. Koi kaam karne ki zarurat nahi."),
    ("hinglish", "Aapka {company} order kal shaam tak {name} ko deliver ho jayega. Dhanyavaad."),
    ("hi", "आपके खाते में {amount} रुपये जमा हुए हैं। यह जानकारी केवल आपकी सूचना के लिए है।"),
    ("hi", "आपका ओटीपी {code} है। इसे किसी के साथ साझा न करें।"),
    ("hi", "आपका बिजली बिल {amount} रुपये का है, अंतिम तारीख 28 सितंबर। कृपया आधिकारिक ऐप से भुगतान करें।"),
    ("hi", "आपकी ट्रेन टिकट कन्फर्म हो गई है। पीएनआर {code}, कोच एस4। यात्रा शुभ हो, {name}।"),
    ("en", "Power shutdown notice: supply will be off in your area on Sunday from 10 AM to 1 PM for maintenance work. Helpline {phone}."),
    ("en", "Your insurance premium receipt for Rs {amount} has been emailed to {name}. Policy {code}. No action is needed."),
    ("en", "Class 12 results are out. Check them on the official board website using roll number {code}."),
    ("en", "Your PF passbook has been updated with the employer contribution of Rs {amount} for August 2026."),
    ("en", "Water supply in your area will be closed tomorrow from 9 AM to 12 PM for pipeline repair. Complaints: {phone}."),
    ("en", "Payment of Rs {amount} received against your water bill. Receipt number {code}. No action needed."),
    ("en", "We have received your {bank} credit card payment of Rs {amount}. Thank you."),
    ("en", "Your municipal tax payment of Rs {amount} is successful. This is a computer generated receipt."),
    ("en", "Thank you {name}. Your bill payment of Rs {amount} through the official app was successful."),
    ("hi", "आपका {amount} रुपये का भुगतान प्राप्त हुआ। यह कंप्यूटर से बनी रसीद है, किसी कार्रवाई की ज़रूरत नहीं।"),
    ("hinglish", "Aapka Rs {amount} ka bill payment mil gaya hai. Receipt number {code}. Dhanyavaad."),
]

# ------------------------- TEST TEMPLATES (never used for training or prompts)
TEST_SCAM = [
    ("kyc_account_block", "en", "URGENT: {bank} netbanking access ends tonight. Re-verify your Aadhaar here {link} or the account stays locked."),
    ("electricity_bill", "en", "Power department final notice. Meter reading not updated, supply stops in {days}. Contact junior engineer {phone} right now."),
    ("parcel_digital_arrest", "en", "Narcotics control bureau: a courier booked with your ID has banned substances. Join the video verification call or an arrest warrant will be issued."),
    ("job_task", "en", "Daily payout offer: complete 20 app reviews and earn Rs {amount}. Membership activation costs Rs 999, refundable after the first payout."),
    ("investment", "en", "Our algorithm gives fixed 12 percent monthly profit on any deposit. Start with Rs {amount} today, withdrawal anytime, link in bio {link}."),
    ("upi_cashback_collect", "en", "Festival bonus of Rs {amount} is waiting. Approve the payment request on your UPI app and type your PIN to collect it."),
    ("lottery_prize", "en", "Final call: your SIM number won a lucky draw of Rs 10,00,000. Send your bank details and Rs {amount} as tax to release the prize."),
    ("loan_app", "en", "Pre approved personal loan of Rs 2,00,000 with zero paperwork. Install our app from {link}, then share the OTP our agent reads out."),
    ("fake_payment", "en", "Bhai maine galti se aapke number par Rs {amount} bhej diya, screenshot dekh lo, please {upi} par wapas kar do."),
    ("relative_emergency", "en", "Uncle, I am in a police station, do not tell papa. Transfer Rs {amount} to {upi} right now, I will explain later."),
    ("other_scam", "hi", "आपका मोबाइल नंबर बंद होने वाला है। सेवा जारी रखने के लिए अधिकारी को ओटीपी बताएं और {link} पर जानकारी भरें।"),
    ("other_scam", "hinglish", "Aapka account hack hone wala hai. Suraksha ke liye yeh app install karein {link} aur apna PIN confirm karein."),
    ("investment", "hi", "सिर्फ़ तीन घंटे में पैसा दोगुना करें। हमारे व्हाट्सएप ग्रुप में शामिल हों और आज ही {amount} रुपये लगाएं।"),
    ("kyc_account_block", "hinglish", "Dear customer, aapka wallet KYC pending hai. Aaj hi {link} par update karein warna balance block ho jayega."),
]

TEST_GENUINE = [
    ("en", "Transaction alert: Rs {amount} spent on your card ending 7781 at a grocery store. Call the number on your card if this was not you."),
    ("en", "Your parcel from {company} is out for delivery. The courier partner {name} will call you before arriving."),
    ("en", "Dear customer, your {bank} statement for Rs {amount} of spends is now available in the app under Statements."),
    ("en", "{code} is the verification code for your account login. Our staff will never ask you for this code."),
    ("en", "Your appointment at the Aadhaar centre is booked for 28 September, 11:30 AM. Carry the original documents."),
    ("en", "Your cab is arriving in 3 minutes. Driver {name}, white car, number plate ends {code}."),
    ("en", "Your electricity payment of Rs {amount} was received. Thank you. This is a system generated receipt."),
    ("en", "Library reminder: the book borrowed by {name} is due back on Friday. Please return or renew it."),
    ("hi", "आपके खाते से {amount} रुपये का भुगतान सफल रहा। यह संदेश केवल जानकारी के लिए है।"),
    ("hi", "आपका ओटीपी {code} है, यह 10 मिनट तक मान्य है। कृपया इसे किसी को न बताएं।"),
    ("hinglish", "Aapka gas cylinder kal subah deliver hoga, delivery boy {name} call karega. Booking {code}."),
    ("en", "Result declared for roll number {code}. Log in to the official university portal to download the marksheet."),
]


def build(scam_rows: int, genuine_rows: int, scam_templates, genuine_templates,
          seed: int = 7) -> list[dict[str, str]]:
    """Each set gets its own seed, so changing the training templates never
    reshuffles the held-out test set."""
    rng = random.Random(seed)
    rows: list[dict[str, str]] = []
    for category, language, template in scam_templates:
        for _ in range(scam_rows):
            rows.append({"text": fill(template, rng), "label": "1", "category": category,
                         "language": language, "source": "seed_template"})
    for language, template in genuine_templates:
        for _ in range(genuine_rows):
            rows.append({"text": fill(template, rng), "label": "0", "category": "not_scam",
                         "language": language, "source": "seed_template"})
    # remove duplicates that the slot filler happened to repeat
    seen, unique = set(), []
    for row in rows:
        if row["text"] not in seen:
            seen.add(row["text"])
            unique.append(row)
    rng.shuffle(unique)
    return unique


def merge_collected(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Real messages the team collects go in ml/data/collected.csv with the same columns."""
    path = DATA / "collected.csv"
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("text") and row.get("label") in {"0", "1"}:
                rows.append({"text": row["text"].strip(), "label": row["label"],
                             "category": row.get("category", ""),
                             "language": row.get("language", "en"),
                             "source": row.get("source", "collected")})
    return rows


def write(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["text", "label", "category", "language", "source"])
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    train = merge_collected(build(9, 10, TRAIN_SCAM, TRAIN_GENUINE, seed=7))
    test = build(5, 6, TEST_SCAM, TEST_GENUINE, seed=99)
    write(DATA / "train.csv", train)
    write(DATA / "test_set.csv", test)
    scams = sum(1 for r in train if r["label"] == "1")
    print(f"train.csv     {len(train):4d} rows  ({scams} scam / {len(train) - scams} genuine)")
    scams = sum(1 for r in test if r["label"] == "1")
    print(f"test_set.csv  {len(test):4d} rows  ({scams} scam / {len(test) - scams} genuine)")
