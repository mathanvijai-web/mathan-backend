from flask import Flask, jsonify
from flask_cors import CORS
import requests
import json

app = Flask(__name__)
CORS(app)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}

session = requests.Session()

def get_nse_session():
    try:
        session.get("https://www.nseindia.com", headers=HEADERS, timeout=10)
    except:
        pass

get_nse_session()

@app.route("/")
def home():
    return jsonify({"status": "MATHAN AI BACKEND RUNNING", "version": "1.0"})

@app.route("/nifty")
def nifty():
    try:
        url = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%2050"
        r = session.get(url, headers=HEADERS, timeout=10)
        data = r.json()
        nifty = next((d for d in data["data"] if d["symbol"] == "NIFTY 50"), data["data"][0])
        return jsonify({
            "status": "ok",
            "price": nifty.get("lastPrice", 0),
            "change": nifty.get("change", 0),
            "pChange": nifty.get("pChange", 0),
            "open": nifty.get("open", 0),
            "high": nifty.get("dayHigh", 0),
            "low": nifty.get("dayLow", 0),
            "prev": nifty.get("previousClose", 0)
        })
    except Exception as e:
        get_nse_session()
        return jsonify({"status": "error", "msg": str(e)}), 500

@app.route("/option-chain")
def option_chain():
    try:
        url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
        r = session.get(url, headers=HEADERS, timeout=15)
        data = r.json()

        records = data["records"]["data"]
        expiry = data["records"]["expiryDates"][0]

        total_ce_oi = 0
        total_pe_oi = 0
        strikes = {}

        for rec in records:
            if rec.get("expiryDate") != expiry:
                continue
            strike = rec["strikePrice"]
            ce = rec.get("CE", {})
            pe = rec.get("PE", {})
            ce_oi = ce.get("openInterest", 0)
            pe_oi = pe.get("openInterest", 0)
            total_ce_oi += ce_oi
            total_pe_oi += pe_oi
            strikes[strike] = {
                "ce_oi": ce_oi,
                "pe_oi": pe_oi,
                "ce_ltp": ce.get("lastPrice", 0),
                "pe_ltp": pe.get("lastPrice", 0),
                "ce_change_oi": ce.get("changeinOpenInterest", 0),
                "pe_change_oi": pe.get("changeinOpenInterest", 0),
            }

        pcr = round(total_pe_oi / total_ce_oi, 2) if total_ce_oi > 0 else 1.0

        # Max pain
        max_pain = calculate_max_pain(strikes)

        # OI walls
        call_wall = max(strikes, key=lambda x: strikes[x]["ce_oi"]) if strikes else 0
        put_wall = max(strikes, key=lambda x: strikes[x]["pe_oi"]) if strikes else 0

        # Signal
        if pcr > 1.2:
            signal = "BULLISH"
            bull_prob = 70
        elif pcr < 0.8:
            signal = "BEARISH"
            bull_prob = 30
        else:
            signal = "SIDEWAYS"
            bull_prob = 50

        bear_prob = 100 - bull_prob - 10
        side_prob = 10

        return jsonify({
            "status": "ok",
            "expiry": expiry,
            "pcr": pcr,
            "total_ce_oi": total_ce_oi,
            "total_pe_oi": total_pe_oi,
            "call_wall": call_wall,
            "put_wall": put_wall,
            "max_pain": max_pain,
            "signal": signal,
            "bull_prob": bull_prob,
            "bear_prob": bear_prob,
            "side_prob": side_prob,
            "strikes": strikes
        })
    except Exception as e:
        get_nse_session()
        return jsonify({"status": "error", "msg": str(e)}), 500

def calculate_max_pain(strikes):
    try:
        min_pain = float("inf")
        max_pain_strike = 0
        for target in strikes:
            total_pain = 0
            for strike, data in strikes.items():
                ce_pain = max(0, strike - target) * data["ce_oi"]
                pe_pain = max(0, target - strike) * data["pe_oi"]
                total_pain += ce_pain + pe_pain
            if total_pain < min_pain:
                min_pain = total_pain
                max_pain_strike = target
        return max_pain_strike
    except:
        return 0

@app.route("/vix")
def vix():
    try:
        url = "https://www.nseindia.com/api/equity-stockIndices?index=India%20VIX"
        r = session.get(url, headers=HEADERS, timeout=10)
        data = r.json()
        vix_data = data["data"][0]
        return jsonify({
            "status": "ok",
            "vix": vix_data.get("lastPrice", 14.0),
            "change": vix_data.get("pChange", 0)
        })
    except Exception as e:
        return jsonify({"status": "error", "vix": 14.0}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)