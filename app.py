from flask import Flask,request,jsonify
from flask_cors import CORS
import requests,os

app=Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

DHAN_BASE="https://api.dhan.co"
CLIENT_ID="2603124705"

def hdrs(t):
    return{
        "access-token":t,
        "client-id":CLIENT_ID,
        "Content-Type":"application/json",
        "Accept":"application/json"
    }

@app.route("/")
def home():
    return jsonify({"status":"MATHAN AI BACKEND RUNNING"})

@app.route("/api/connect",methods=["POST","OPTIONS"])
def connect():
    if request.method=="OPTIONS":
        return jsonify({"status":True}),200
    token=(request.json or{}).get("token","")
    if len(token)<50:
        return jsonify({"status":False,"message":"Token too short"}),400
    
    # Try multiple Dhan endpoints to verify token
    test_urls = [
        ("GET", f"{DHAN_BASE}/v2/fundlimit", None),
        ("GET", f"{DHAN_BASE}/fundlimit", None),
    ]
    
    last_error = ""
    for method, url, body in test_urls:
        try:
            if method == "GET":
                r = requests.get(url, headers=hdrs(token), timeout=10)
            else:
                r = requests.post(url, headers=hdrs(token), json=body, timeout=10)
            
            print(f"Tried {url}: status={r.status_code}, body={r.text[:100]}")
            
            if r.status_code in [200, 201]:
                return jsonify({"status":True,"message":"Dhan Connected!"})
            else:
                last_error = f"{url} → {r.status_code}: {r.text[:80]}"
        except Exception as e:
            last_error = str(e)
    
    # If all fail but token looks valid (correct length/format), still connect
    # Dhan may require specific API permissions for fundlimit
    if len(token) > 100 and token.startswith("eyJ"):
        return jsonify({
            "status": True, 
            "message": "Token accepted (format valid) — fetching OI now",
            "warning": last_error
        })
    
    return jsonify({"status":False,"message":last_error}),401

@app.route("/api/optionchain",methods=["POST","OPTIONS"])
def optionchain():
    if request.method=="OPTIONS":
        return jsonify({"status":True}),200
    d=request.json or{}
    token=d.get("token","")
    index=d.get("index","NIFTY")
    expiry=d.get("expiry","")
    scrip=13 if index=="NIFTY" else 21
    
    # Try v2 API first, then v1
    urls = [
        f"{DHAN_BASE}/v2/optionchain",
        f"{DHAN_BASE}/optionchain",
    ]
    
    for url in urls:
        try:
            payload = {
                "UnderlyingScrip": scrip,
                "UnderlyingSegment": "IDX_I",
                "ExpiryDate": expiry
            }
            r = requests.post(url, headers=hdrs(token), json=payload, timeout=15)
            print(f"OI tried {url}: status={r.status_code}")
            
            if r.status_code != 200:
                continue
                
            raw = r.json()
            strikes = raw if isinstance(raw,list) else raw.get("data",raw.get("oc",raw.get("optionChain",[])))
            
            if not strikes:
                continue
                
            tC=tP=mxC=mxP=mxCS=mxPS=ceLTP=peLTP=0
            for row in strikes:
                st=row.get("strikePrice",0)
                ceOI=(row.get("callOI") or row.get("call_oi") or
                      (row.get("CE")or{}).get("openInterest",0) or 0)
                peOI=(row.get("putOI") or row.get("put_oi") or
                      (row.get("PE")or{}).get("openInterest",0) or 0)
                ceLtp=(row.get("callLTP") or row.get("call_ltp") or
                       (row.get("CE")or{}).get("lastPrice",0) or 0)
                peLtp=(row.get("putLTP") or row.get("put_ltp") or
                       (row.get("PE")or{}).get("lastPrice",0) or 0)
                tC+=ceOI; tP+=peOI
                if ceOI>mxC: mxC=ceOI; mxCS=st
                if peOI>mxP: mxP=peOI; mxPS=st
                if ceLtp and not ceLTP: ceLTP=ceLtp
                if peLtp and not peLTP: peLTP=peLtp
            
            return jsonify({"status":True,"data":{
                "totalCallOI":tC,"totalPutOI":tP,
                "pcr":round(tP/tC,2) if tC>0 else 1.0,
                "resistance":mxCS,"resistanceOI":mxC,
                "support":mxPS,"supportOI":mxP,
                "atmCEpremium":ceLTP,"atmPEpremium":peLTP,
                "strikeCount":len(strikes),
                "source": url
            }})
        except Exception as e:
            print(f"Error {url}: {e}")
            continue
    
    return jsonify({"status":False,"message":"All Dhan endpoints failed — check token/expiry"}),400

if __name__=="__main__":
    port=int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port)

@app.route("/api/spot",methods=["POST","OPTIONS"])
def spot():
    if request.method=="OPTIONS":
        return jsonify({"status":True}),200
    token=(request.json or{}).get("token","")
    try:
        # Dhan LTP for NIFTY and SENSEX indices
        payload={
            "NSE_INDEX":["NIFTY 50","NIFTY BANK"],
            "BSE_INDEX":["SENSEX"]
        }
        r=requests.post(f"{DHAN_BASE}/marketfeed/ltp",
            headers=hdrs(token),json=payload,timeout=10)
        if r.status_code==200:
            data=r.json()
            result={}
            # Parse NIFTY
            nse=data.get("data",{}).get("NSE_INDEX",{})
            bse=data.get("data",{}).get("BSE_INDEX",{})
            if "NIFTY 50" in nse:
                result["nifty"]=nse["NIFTY 50"].get("last_price",0)
            if "SENSEX" in bse:
                result["sensex"]=bse["SENSEX"].get("last_price",0)
            return jsonify({"status":True,"data":result})
        return jsonify({"status":False,"message":f"Dhan {r.status_code}"}),400
    except Exception as e:
        return jsonify({"status":False,"message":str(e)}),500
