# TUYUL V5.3.40-G - TABLE COLOR + WINRATE - REF F
import os, time, threading, requests, hmac, hashlib, json, math, datetime, urllib.parse
from collections import deque, defaultdict
from pathlib import Path
from dotenv import load_dotenv

base_dir = Path(__file__).parent
dotenv_path = Path(r"D:\BOT TRADE\bot sol\.env")
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path, override=True)
else:
    load_dotenv(base_dir / ".env", override=True)

import customtkinter as ctk
import tkinter.ttk as ttk
try:
    from sklearn.ensemble import RandomForestClassifier
    AI_READY=True
except:
    AI_READY=False
try:
    from openai import OpenAI
    GROQ_KEY = (os.getenv("GROQ_API_KEY") or "").strip().strip('"').strip("'").strip()
    llm_client=None; LLM_READY=False
    if GROQ_KEY.startswith("gsk_") and len(GROQ_KEY)>20:
        llm_client=OpenAI(api_key=GROQ_KEY, base_url="https://api.groq.com/openai/v1")
        LLM_READY=True
except:
    LLM_READY=False; llm_client=None

llm_cache={}; last_ask=defaultdict(float)
API_KEY = (os.getenv("TOKOCRYPTO_API_KEY") or os.getenv("TOKO_API_KEY") or os.getenv("API_KEY") or "").strip().strip('"').strip("'").strip()
API_SECRET = (os.getenv("TOKOCRYPTO_API_SECRET") or os.getenv("TOKO_API_SECRET") or os.getenv("API_SECRET") or "").strip().strip('"').strip("'").strip()

MIN_AI_BUY=45; MAX_POS=3; MIN_ORDER_USDT=1.0
TP_PCT=3.5; SL_PCT=-1.5
FEE_CACHE={"buy":0,"sell":0,"time":0,"source":"none"}
COINS=["SHIB","PEPE","BONK","DOGE","BOME","MEME","WIF","FLOKI"]
MEME_KEYWORDS=["PEPE","BONK","FLOKI","WIF","BOME","MEME","TURBO","PNUT","NEIRO","BRETT","POPCAT","MOODENG","GOAT","MEW","WEN","DOG","SHIB","ELON","MOG","APU"]
REVERSE_COINS={"DOGS","BABY","1MBABYDOGE","BABYDOGE","1000BABYDOGE"}
BASKET_FILE=base_dir/"basket_v5.json"; STATS_FILE=base_dir/"trade_stats_v5.json"
SCANNED_META={}; BUY_BLOCK_COOLDOWN={}
USDT_IDR_CACHE={"price":0,"time":0}
PRICE_CACHE={"idr":{},"usdt":{},"time":0}
balance_cache={"idr":0,"usdt":0,"time":0,"assets":[]}
stats_data=[]

def fetch_kurs_live_now():
    for url in [
        "https://www.tokocrypto.com/api/v3/ticker/bookTicker?symbol=USDT_IDR",
        "https://www.tokocrypto.com/api/v3/ticker/price?symbol=USDT_IDR",
        "https://www.tokocrypto.site/api/v3/ticker/price?symbol=USDT_IDR",
        "https://www.tokocrypto.com/api/v3/ticker/price?symbol=USDTIDR",
    ]:
        try:
            r=requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=6).json()
            if not isinstance(r, dict): continue
            bid=float(r.get('bidPrice',0) or 0); ask=float(r.get('askPrice',0) or 0)
            if bid>1000 and ask>1000:
                mid=(bid+ask)/2
                if 14000 < mid < 25000: return mid
            p=float(r.get('price',0) or 0)
            if 14000 < p < 25000: return p
        except: continue
    return 0

def load_stats():
    global stats_data
    if STATS_FILE.exists():
        try: stats_data=json.load(open(STATS_FILE, encoding='utf-8'))
        except: stats_data=[]
load_stats()
def save_stats():
    try: json.dump(stats_data, open(STATS_FILE,'w', encoding='utf-8'), indent=2)
    except: pass
def add_trade_record(coin,is_tp,entry_price,curr_price,amount,fee_total,kotor,bersih,pnl_pct,buy_fee_live,sell_fee_live):
    record={"timestamp":time.time(),"date_str":datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"date_only":datetime.datetime.now().strftime("%Y-%m-%d"),"coin":coin,"type":"TP" if is_tp else "SL","pnl_pct":round(pnl_pct,2),"gross_idr":int(kotor),"net_idr":int(bersih),"fee_idr":int(fee_total),"fee_buy_pct":buy_fee_live*100,"fee_sell_pct":sell_fee_live*100,"amount":amount,"entry":entry_price,"exit":curr_price}
    stats_data.append(record); save_stats()
def get_summary_for_period(filter_func):
    tp=[r for r in stats_data if r['type']=='TP' and filter_func(r)]; sl=[r for r in stats_data if r['type']=='SL' and filter_func(r)]
    return {"tp_count":len(tp),"sl_count":len(sl),"tp_gross":sum(r['gross_idr'] for r in tp),"tp_net":sum(r['net_idr'] for r in tp),"sl_gross":sum(r['gross_idr'] for r in sl),"sl_net":sum(r['net_idr'] for r in sl),"total_gross":sum(r['gross_idr'] for r in tp+sl),"total_net":sum(r['net_idr'] for r in tp+sl)}
def summary_today(): return get_summary_for_period(lambda r: r.get('date_only')==datetime.datetime.now().strftime("%Y-%m-%d"))
def summary_week():
    now=datetime.datetime.now(); start=now-datetime.timedelta(days=now.weekday()); start=start.replace(hour=0,minute=0,second=0,microsecond=0)
    return get_summary_for_period(lambda r: r['timestamp']>=start.timestamp())
def summary_month():
    now=datetime.datetime.now(); start=now.replace(day=1,hour=0,minute=0,second=0,microsecond=0)
    return get_summary_for_period(lambda r: r['timestamp']>=start.timestamp())
def summary_all(): return get_summary_for_period(lambda r: True)
def format_rp(n): return f"{'-' if n<0 else ''}Rp{abs(int(n)):,}"
def format_price_idr_smart(p):
    if p <= 0: return "Rp0"
    if p < 0.01: return f"Rp{p:.6f}"
    if p < 1: return f"Rp{p:.4f}"
    if p < 100: return f"Rp{p:.2f}"
    return f"Rp{p:.0f}"
def gui_log(m):
    t=f"[{time.strftime('%H:%M:%S')}] {m}"; print(t)
    try:
        if 'log_box' in globals(): app.after(0, lambda: (log_box.insert("end", t+"\n"), log_box.see("end")))
    except: pass
def signed_request(method,path,params={}):
    if not API_KEY or not API_SECRET: return None
    try:
        ts=int(time.time()*1000); par=params.copy(); par['timestamp']=ts; par['recvWindow']=5000
        qs=urllib.parse.urlencode(sorted(par.items())); sig=hmac.new(API_SECRET.encode(),qs.encode(),hashlib.sha256).hexdigest()
        url=f"https://www.tokocrypto.com{path}?{qs}&signature={sig}"; h={"X-MBX-APIKEY":API_KEY}
        r=requests.get(url,headers=h,timeout=12) if method=="GET" else requests.post(url,headers=h,timeout=12)
        try: return r.json()
        except: return None
    except: return None
def is_order_success(res):
    if not res or not isinstance(res,dict): return False
    if res.get('code')==0 or res.get('orderId'): return True
    if res.get('data') and isinstance(res.get('data'),dict) and res.get('data').get('orderId'): return True
    return False
def get_fee_from_tokocrypto_api():
    global FEE_CACHE
    if time.time()-FEE_CACHE["time"]<60 and FEE_CACHE["buy"]>0: return FEE_CACHE["buy"],FEE_CACHE["sell"]
    try:
        res=signed_request("GET","/open/v1/account/spot",{})
        if res and res.get('code')==0:
            taker=float(str(res.get('data',{}).get('takerCommission','0')))
            if taker>1: taker/=10000
            if taker>0:
                total=taker*1.55; FEE_CACHE.update({"buy":total,"sell":total,"time":time.time(),"source":f"SPOT {taker*100:.4f}%"})
                return total,total
    except: pass
    emergency=0.002325; FEE_CACHE.update({"buy":emergency,"sell":emergency,"time":time.time(),"source":"emergency"}); return emergency,emergency
def get_usdt_idr():
    if USDT_IDR_CACHE["price"]==0 or time.time()-USDT_IDR_CACHE["time"]>30:
        live=fetch_kurs_live_now()
        if live>0: USDT_IDR_CACHE.update({"price":live,"time":time.time()}); return live
    if time.time()-USDT_IDR_CACHE["time"]<30: return USDT_IDR_CACHE["price"]
    return USDT_IDR_CACHE["price"] if USDT_IDR_CACHE["price"]>0 else 17719.13
def get_usdt_idr_cached():
    if USDT_IDR_CACHE["price"]==0:
        live=fetch_kurs_live_now()
        if live>0: USDT_IDR_CACHE.update({"price":live,"time":time.time()}); return live
        return 17719.13
    return USDT_IDR_CACHE["price"]
def refresh_all_prices(force=False):
    global PRICE_CACHE
    if not force and time.time()-PRICE_CACHE["time"]<10: return
    headers={"User-Agent":"Mozilla/5.0"}; idr_map={}; usdt_map={}
    for api_url in ["https://www.tokocrypto.com/api/v3/ticker/price","https://www.tokocrypto.site/api/v3/ticker/price"]:
        try:
            r=requests.get(api_url, headers=headers, timeout=8).json()
            if isinstance(r,list) and len(r)>20:
                for it in r:
                    sym=str(it.get('symbol','')).upper()
                    try: p=float(it.get('price',0))
                    except: continue
                    if p<=0: continue
                    if sym.endswith('IDR'): idr_map[sym[:-3].replace('_','')]=p
                    elif sym.endswith('USDT'): usdt_map[sym[:-4].replace('_','')]=p
                if len(usdt_map)>20: break
        except: continue
    kurs=get_usdt_idr()
    for k,v in usdt_map.items():
        if k not in idr_map or idr_map.get(k,0) < 0.000001: idr_map[k]=v*kurs
    if len(usdt_map)>0: PRICE_CACHE={"idr":idr_map,"usdt":usdt_map,"time":time.time()}
def get_idr_price(coin): return PRICE_CACHE["idr"].get(coin.upper(),0)
def get_usdt_price(coin): return PRICE_CACHE["usdt"].get(coin.upper(),0)
def is_coin_live(coin):
    if coin.upper() in REVERSE_COINS: return False
    return get_idr_price(coin) > 0.000001 or get_usdt_price(coin) > 0.00000001
def get_initial_price(c):
    kurs=get_usdt_idr_cached(); idr=PRICE_CACHE["idr"].get(c.upper(),0)
    if idr>0.000001: return idr
    usdt=PRICE_CACHE["usdt"].get(c.upper(),0)
    if usdt>0: return usdt*kurs
    try:
        r=requests.get(f"https://www.tokocrypto.com/api/v3/ticker/price?symbol={c.upper()}_IDR", timeout=4).json()
        p=float(r.get('price',0)) if isinstance(r,dict) else 0
        if p>0: return p
        r=requests.get(f"https://www.tokocrypto.com/api/v3/ticker/price?symbol={c.upper()}USDT", timeout=4).json()
        p=float(r.get('price',0)) if isinstance(r,dict) else 0
        if p>0: return p*kurs
    except: pass
    return 0.0
def get_balances_detail(force=False):
    global balance_cache
    if not force and time.time()-balance_cache["time"]<8: return balance_cache["idr"],balance_cache["usdt"],balance_cache["assets"]
    res=signed_request("GET","/open/v1/account/spot",{})
    try:
        bals=res.get('data',{}).get('accountAssets',[]) or []
        idr=usdt=0
        for b in bals:
            asset=(b.get('asset') or '').upper(); free=float(b.get('free',0) or 0)
            if asset in ('IDR','BIDR'): idr+=free
            if asset=='USDT': usdt+=free
        balance_cache={"idr":idr,"usdt":usdt,"time":time.time(),"assets":bals}
        return idr,usdt,bals
    except: return balance_cache["idr"],balance_cache["usdt"],balance_cache["assets"]
def get_coin_balance(coin):
    _,_,bals=get_balances_detail(force=True)
    for b in bals:
        if (b.get('asset') or '').upper()==coin.upper(): return float(b.get('free',0) or 0)
    return 0
def get_real_avg_idr(coin):
    try:
        total_qty=0.0; total_cost=0.0; found=False
        for sym in [f"{coin.upper()}_USDT", f"{coin.upper()}_IDR"]:
            res=signed_request("GET","/open/v1/account/myTrades",{"symbol":sym,"limit":200})
            if not res: continue
            for t in res.get('data',[]) or []:
                is_buy=t.get('isBuyer')==True or str(t.get('side','')).upper()=='BUY' or str(t.get('side'))=='0'
                if not is_buy and t.get('isBuyer')==False: continue
                qty=float(t.get('qty',0) or 0); price=float(t.get('price',0) or 0)
                if qty<=0 or price<=0: continue
                if 'USDT' in sym: price*=get_usdt_idr_cached()
                total_cost+=qty*price; total_qty+=qty; found=True
        if found and total_qty>0: return total_cost/total_qty
    except: pass
    return 0
def get_real_avg_idr_v2(coin, free_balance):
    try:
        total_buy_qty=0.0; total_buy_cost=0.0; total_sell_qty=0.0; total_sell_cost=0.0
        for sym in [f"{coin.upper()}_USDT"]:
            res = signed_request("GET","/open/v1/account/myTrades",{"symbol":sym,"limit":500})
            if not res: continue
            for t in res.get('data',[]) or []:
                qty=float(t.get('qty',0) or 0); price=float(t.get('price',0) or 0)
                if qty<=0 or price<=0: continue
                price_idr = price * get_usdt_idr_cached()
                is_buyer = t.get('isBuyer')==True or str(t.get('side','')).upper()=='BUY' or str(t.get('side'))=='0'
                if is_buyer: total_buy_qty+=qty; total_buy_cost+=qty*price_idr
                else: total_sell_qty+=qty; total_sell_cost+=qty*price_idr
        if free_balance>0 and total_buy_qty>total_sell_qty:
            sisa_modal = total_buy_cost - total_sell_cost
            if sisa_modal>0:
                avg_real = sisa_modal / free_balance
                if avg_real>0.000001: return avg_real
    except: pass
    return 0
def get_unrealized_summary():
    total_gross=0; total_net=0; detail=[]
    buy_fee,sell_fee=get_fee_from_tokocrypto_api(); kurs=get_usdt_idr_cached()
    for coin,pos in list(positions.items()):
        curr=get_idr_price(coin)
        if curr<=0.000001: curr=get_usdt_price(coin)*kurs if get_usdt_price(coin)>0 else 0
        if curr<=0.000001: curr=prices.get(coin,0)
        if curr<=0.000001: curr=get_initial_price(coin)
        entry=pos.get('entry_price',0)
        if entry<=0.000001: entry=curr
        amount=pos.get('amount',0)
        if entry<=0.000001 or amount<=0 or curr<=0.000001: continue
        pnl=(curr-entry)/entry*100; kotor=(curr-entry)*amount; fee=(entry*amount*buy_fee)+(curr*amount*sell_fee); bersih=kotor-fee
        total_gross+=kotor; total_net+=bersih; detail.append(f"{coin}: {pnl:+.2f}% Net {format_rp(bersih)}")
    return {"gross":total_gross,"net":total_net,"detail":detail}
def summary_real_porto():
    real=summary_all(); unreal=get_unrealized_summary()
    return {"realized_net":real['total_net'],"unrealized_net":unreal['net'],"total_net_asli":real['total_net']+unreal['net']}
def ask_llm_safe(coin,prob_ai,vol=""):
    now=time.time()
    if coin in llm_cache and now-last_ask.get(coin,0)<300: return llm_cache[coin]
    if not LLM_READY or llm_client is None: return prob_ai>=MIN_AI_BUY
    if prob_ai>=50: return True
    try:
        prompt=f"{coin} AI {prob_ai}% Vol {vol} YES/NO"
        res=llm_client.chat.completions.create(model="openai/gpt-oss-20b", messages=[{"role":"user","content":prompt}], max_tokens=30, temperature=0.1)
        ans=res.choices[0].message.content.upper().strip()
        result="YES" in ans or "BUY" in ans
        llm_cache[coin]=result; last_ask[coin]=now; return result
    except: return prob_ai>=MIN_AI_BUY
def load_basket():
    try:
        idr,usdt,_=get_balances_detail(force=True); kurs=get_usdt_idr_cached(); real_lock=usdt+idr/kurs if kurs>0 else 0
    except: real_lock=0
    default={"lock_modal":real_lock,"total_gaji_idr":0,"level":1}
    if BASKET_FILE.exists():
        try:
            data=json.load(open(BASKET_FILE))
            if data.get('lock_modal',0)<real_lock and real_lock>0: data['lock_modal']=real_lock
            return data
        except: pass
    return default

print("[INIT] Fetch kurs live...")
kurs_awal = fetch_kurs_live_now()
if kurs_awal>0: USDT_IDR_CACHE.update({"price":kurs_awal,"time":time.time()})
else: USDT_IDR_CACHE.update({"price":17719.13,"time":time.time()})

basket_data=load_basket()
def save_basket(data):
    try: json.dump(data, open(BASKET_FILE,'w'), indent=2)
    except: pass
def cek_basket_and_level_up(profit_usdt_net=0,profit_idr_net=0,profit_idr_kotor=0,fee_total=0):
    global basket_data
    if profit_usdt_net<=0: return
    basket_data["lock_modal"]+=profit_usdt_net; basket_data["total_gaji_idr"]+=profit_idr_net; save_basket(basket_data)
def cleanup_coins():
    global COINS,prices,history,trained
    now=time.time(); new=[]
    for coin in COINS:
        if coin in positions: new.append(coin); continue
        meta=SCANNED_META.get(coin)
        if not meta: new.append(coin); continue
        if now-meta['time']>2700 and not is_coin_live(coin):
            prices.pop(coin,None); history.pop(coin,None); trained.pop(coin,None); SCANNED_META.pop(coin,None); continue
        new.append(coin)
    COINS=new
def scan_tokocrypto_agresif():
    global COINS,prices,history,trained
    try:
        cleanup_coins(); kurs=get_usdt_idr_cached(); refresh_all_prices(force=True)
        gui_log(f"[SCANNER] START Coins:{len(COINS)} POS:{list(positions.keys())} Harga:{len(PRICE_CACHE['idr'])} IDR kurs Rp{kurs:.0f}")
        r_toko=None
        for url in ["https://www.tokocrypto.com/api/v3/ticker/24hr","https://www.tokocrypto.site/api/v3/ticker/24hr"]:
            try:
                r=requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10).json()
                if isinstance(r,list) and len(r)>50: r_toko=r; break
            except: continue
        if not r_toko: gui_log("[SCAN] API 24hr kosong"); return
        candidates=[]
        for t in r_toko:
            if not isinstance(t,dict): continue
            sym=str(t.get('symbol','')).upper()
            if not sym.endswith('USDT'): continue
            coin=sym.replace('USDT','').replace('_','')
            if coin in REVERSE_COINS or len(coin)>12 or len(coin)<2: continue
            if coin in ['BTC','ETH','BNB','USDT','IDR','BIDR']: continue
            is_meme = any(k == coin or k in coin for k in MEME_KEYWORDS)
            if not is_meme: continue
            vol=float(t.get('quoteVolume',0) or 0); last=float(t.get('lastPrice',0) or 0); change=float(t.get('priceChangePercent',0) or 0)
            if last<=0 or vol<200000: continue
            if last>5: continue
            candidates.append((coin,vol,last,change))
        candidates=sorted(candidates, key=lambda x: x[1], reverse=True); added=0
        for coin,vol,last,change in candidates[:30]:
            if added>=4: break
            if coin in COINS: continue
            if BUY_BLOCK_COOLDOWN.get(coin,0)>time.time(): continue
            p_idr=get_idr_price(coin); p_usdt=get_usdt_price(coin) or last; p=p_idr if p_idr>0 else p_usdt*kurs
            if p<0.000001: continue
            COINS.append(coin); SCANNED_META[coin]={'time':time.time()}
            prices[coin]=p; history[coin]=deque([p]*50, maxlen=200); trained[coin]=0; added+=1
            gui_log(f"[FOUND] {coin} ${last:.6f} Vol:{vol:,.0f} {change:+.1f}% -> {format_price_idr_smart(p)}")
        if added>0: gui_log(f"[SCAN DONE] Added {added} Total:{len(COINS)}")
        else: gui_log(f"[SCAN] No new")
    except Exception as e: gui_log(f"[SCAN ERR] {e}")
def scanner_thread_loop():
    while True:
        time.sleep(300)
        try: scan_tokocrypto_agresif()
        except: pass
try: refresh_all_prices(force=True); get_usdt_idr()
except: pass
def get_prices_init(c): return get_initial_price(c) or 0.01
prices={c: get_prices_init(c) for c in COINS}; history={c: deque([prices[c]]*50, maxlen=200) for c in COINS}
models={}; trained={c:0 for c in COINS}; positions={}; POS_FILE=base_dir/"positions_toko_v5.json"; TRAINED_FILE=base_dir/"trained_v5.json"
ai_stats={}; BUY_FAIL_COOLDOWN={}
def save_positions():
    try: json.dump(positions, open(POS_FILE,'w'), indent=2); json.dump(trained, open(TRAINED_FILE,'w'))
    except: pass
def restore_positions_from_exchange():
    global positions,COINS,prices,history,trained
    try:
        refresh_all_prices(force=True); get_usdt_idr()
        idr,usdt,assets=get_balances_detail(force=True); kurs=get_usdt_idr_cached(); valid=[]
        for b in assets:
            try:
                if float(b.get('free',0) or 0)>0.000001: valid.append(b)
            except: continue
        gui_log(f"[SYNC] Valid aset: {len(valid)} | USDT {usdt:.2f} IDR {idr:.0f} kurs Rp{kurs:.0f}")
        new_pos={}
        for b in valid:
            asset=(b.get('asset') or '').upper(); free=float(b.get('free',0) or 0)
            if asset in ('IDR','BIDR','USDT','BTC','ETH','BNB','FDUSD') or asset in REVERSE_COINS: continue
            if free<=0: continue
            pu=get_usdt_price(asset); pi=get_idr_price(asset); val_usdt = free*pu if pu>0 else 0
            if val_usdt>0 and val_usdt<0.15: continue
            curr=pi if pi>0.000001 else (pu*kurs if pu>0 else get_initial_price(asset))
            if curr<=0.000001: curr=get_initial_price(asset)
            if curr<=0.000001: continue
            real_avg=get_real_avg_idr_v2(asset,free) or get_real_avg_idr(asset); entry=real_avg if real_avg>0.000001 else curr
            if asset not in COINS: COINS.append(asset)
            prices[asset]=curr
            if asset not in history: history[asset]=deque([curr]*50, maxlen=200)
            new_pos[asset]={"entry_price":entry,"amount":free,"time":time.time(),"entry_usdt":val_usdt,"restored":True}
            gui_log(f"[SYNC OK] {asset} {free} @ {format_price_idr_smart(entry)} = ${val_usdt:.2f}")
        if new_pos:
            positions.clear(); positions.update(new_pos); save_positions(); gui_log(f"[SYNC DONE] POS {list(positions.keys())}"); return True
        else:
            if len(positions)>0: positions.clear(); save_positions()
            gui_log(f"[SYNC DONE] Dompet kosong / cuma USDT ${usdt:.2f} - siap BUY"); return False
    except Exception as e: gui_log(f"[SYNC ERR] {e}"); return False
def load_positions(): restore_positions_from_exchange()
load_positions()
def train_ai(c):
    if prices.get(c,0)<0.000001 or len(history.get(c,[]))<25: return 50,0
    if not AI_READY: return 50,0
    try:
        data=list(history[c]); X=[]; y=[]
        for i in range(15,len(data)-3):
            sma10=sum(data[i-10:i])/10; sma20=sum(data[i-20:i])/20 if i>=20 else sma10
            vol=sum(abs(data[j]-data[j-1]) for j in range(i-5,i))/5
            X.append([data[i]-data[i-1],data[i]-data[i-3],data[i]-sma10,data[i]-sma20,vol]); y.append(1 if data[i+3]>data[i]*1.0015 else 0)
        if len(X)<12 or len(set(y))<2: return 50,0
        clf=RandomForestClassifier(n_estimators=15,max_depth=5,random_state=42); clf.fit(X,y); models[c]=clf; trained[c]+=1; save_positions()
        s10=sum(data[-11:-1])/10; s20=sum(data[-21:-1])/20; vol=sum(abs(data[j]-data[j-1]) for j in range(-5,0))/5
        feat=[[data[-1]-data[-2],data[-1]-data[-4],data[-1]-s10,data[-1]-s20,vol]]
        proba=clf.predict_proba(feat)[0]; prob=round(proba[list(clf.classes_).index(1)]*100,1) if 1 in clf.classes_ else 50.0
        prob=max(40,min(90,prob)); ai_stats[c]={"prob":prob}; return prob,85
    except: return 50.0,0
def predict_ai(c):
    if c in REVERSE_COINS: return 0.0
    if BUY_BLOCK_COOLDOWN.get(c,0)>time.time(): return 0.0
    if prices.get(c,0)<=0.000001: return 0.0
    if trained.get(c,0)<5: return ai_stats.get(c,{}).get('prob',40.0)
    return ai_stats.get(c,{}).get('prob',50.0)
def format_qty(coin,amount): return int(math.floor(amount*0.998))
def place_buy(coin,_=0):
    if coin.upper() in REVERSE_COINS: return False
    if BUY_FAIL_COOLDOWN.get(coin,0)>time.time() or BUY_BLOCK_COOLDOWN.get(coin,0)>time.time(): return False
    if len(positions)>=MAX_POS or coin in positions: return False
    if not is_coin_live(coin): return False
    idr_free,usdt_free,_=get_balances_detail(force=True)
    if usdt_free<1.0 and idr_free<15000: gui_log(f"[BUY SKIP] USDT ${usdt_free:.2f} < $1"); return False
    pi=get_idr_price(coin)
    if pi<=0.000001: pi=get_initial_price(coin)
    pu=get_usdt_price(coin); price_check=pi if pi>0.000001 else (pu*get_usdt_idr_cached() if pu>0 else get_initial_price(coin))
    if price_check<=0.000001: return False
    if predict_ai(coin)<MIN_AI_BUY: return False
    if not ask_llm_safe(coin, predict_ai(coin), vol=f"{pu}"): return False
    slots_left=MAX_POS-len(positions); use_usdt=(usdt_free/slots_left)*0.85 if usdt_free>=1 else usdt_free*0.95
    if use_usdt<1.0: use_usdt=usdt_free
    if use_usdt<1.0: return False
    res=signed_request("POST","/open/v1/orders",{"symbol":f"{coin.upper()}_USDT","side":0,"type":2,"quoteOrderQty":round(use_usdt,2)})
    if is_order_success(res):
        real_bal=get_coin_balance(coin); amt=real_bal if real_bal>0 else use_usdt/(pu if pu>0 else price_check/get_usdt_idr_cached())
        entry_price=pi if pi>0.000001 else price_check
        positions[coin]={"entry_price":entry_price,"amount":amt,"time":time.time(),"entry_usdt":use_usdt,"restored":False}
        save_positions(); balance_cache["time"]=0; gui_log(f"[BUY OK] {coin} ${use_usdt:.2f} @ {format_price_idr_smart(entry_price)}"); return True
    else: gui_log(f"[BUY FAIL] {coin} ${use_usdt:.2f} resp {str(res)[:150]}")
    return False
def place_sell(coin,is_tp=False):
    bal=get_coin_balance(coin)
    if bal<=0: bal=positions.get(coin,{}).get('amount',0)
    if bal<=0: return False
    qty=format_qty(coin,bal)
    if qty<=0: return False
    curr_price=get_idr_price(coin)
    if curr_price<=0.000001: curr_price=get_usdt_price(coin)*get_usdt_idr_cached() if get_usdt_price(coin)>0 else prices.get(coin,0)
    if curr_price<=0.000001: curr_price=get_initial_price(coin)
    entry_price=positions.get(coin,{}).get('entry_price',0)
    if entry_price<=0.000001: entry_price=curr_price
    amount=positions.get(coin,{}).get('amount',0)
    if curr_price<=0.000001 or entry_price<=0.000001 or amount<=0:
        for sym in [f"{coin.upper()}_USDT"]:
            res=signed_request("POST","/open/v1/orders",{"symbol":sym,"side":1,"type":2,"quantity":qty})
            if is_order_success(res):
                if coin in positions: del positions[coin]
                save_positions(); balance_cache["time"]=0; return True
        return False
    pnl_pct=(curr_price-entry_price)/entry_price*100; kurs=get_usdt_idr_cached(); buy_fee,sell_fee=get_fee_from_tokocrypto_api()
    entry_val=entry_price*amount; curr_val=curr_price*amount; fee_total=(entry_val*buy_fee)+(curr_val*sell_fee); kotor=curr_val-entry_val; bersih=kotor-fee_total; bersih_usdt=bersih/kurs if kurs else 0
    for sym in [f"{coin.upper()}_USDT"]:
        res=signed_request("POST","/open/v1/orders",{"symbol":sym,"side":1,"type":2,"quantity":qty})
        if is_order_success(res):
            gui_log(f"[SELL OK] {coin} PNL {pnl_pct:.2f}% Net {format_rp(bersih)}")
            add_trade_record(coin,is_tp,entry_price,curr_price,amount,fee_total,kotor,bersih,pnl_pct,buy_fee,sell_fee)
            if is_tp and bersih_usdt>0: cek_basket_and_level_up(bersih_usdt,bersih,kotor,fee_total); BUY_BLOCK_COOLDOWN[coin]=time.time()+3600
            if coin in positions: del positions[coin]
            SCANNED_META.pop(coin,None); save_positions(); balance_cache["time"]=0; return True
    return False

# ==== UI G - COLOR TABLE ====
ctk.set_appearance_mode("dark")
app=ctk.CTk()
app.geometry("1400x900")
app.title(f"TUYUL V5.3.40-G COLOR Rp{get_usdt_idr_cached():.0f} LOCK ${basket_data['lock_modal']:.2f}")
is_running=False

header=ctk.CTkFrame(app, fg_color="#1a1d27"); header.pack(fill="x", padx=10, pady=10, side="top")
ctk.CTkLabel(header, text=f"TUYUL V5.3.40-G COLOR Rp{get_usdt_idr_cached():.0f} | Lock ${basket_data['lock_modal']:.2f} | TP {TP_PCT}% SL {SL_PCT}%", font=("Segoe UI", 14, "bold")).pack(side="left", padx=15, pady=10)
bal_label=ctk.CTkLabel(header, text="BAL Rp0", font=("Consolas", 13, "bold"), text_color="#00ff88"); bal_label.pack(side="right", padx=15)

btn_frame=ctk.CTkFrame(app, fg_color="#0f1115", height=60); btn_frame.pack(fill="x", padx=10, pady=10, side="bottom")
log_box=ctk.CTkTextbox(app, font=("Consolas", 11), height=120); log_box.pack(fill="x", padx=10, pady=5, side="bottom")
tabview=ctk.CTkTabview(app, width=1330, height=550); tabview.pack(fill="both", expand=True, padx=10, pady=5)
tabview.add("TRADING"); tabview.add("STATS HARIAN/MINGGUAN/BULANAN"); tabview.add("HISTORY TRADE")
top_frame=ctk.CTkFrame(tabview.tab("TRADING")); top_frame.pack(fill="both", expand=True, padx=5, pady=5)
columns=("coin","price_idr","price_usdt","ai","trained","pos","pnl","live")
tree=ttk.Treeview(top_frame, columns=columns, show="headings", height=16)
for col,w in zip(columns,[70,130,110,60,60,260,80,50]):
    tree.heading(col,text=col.upper()); tree.column(col,width=w,anchor="center")
tree.pack(fill="both", expand=True, padx=10, pady=10)

stats_tab = tabview.tab("STATS HARIAN/MINGGUAN/BULANAN")
stats_frame=ctk.CTkScrollableFrame(stats_tab, fg_color="#0f0f0f"); stats_frame.pack(fill="both", expand=True, padx=10, pady=10)

def make_table_card(parent, title, color):
    card=ctk.CTkFrame(parent, fg_color="#1a1d27", corner_radius=12, border_width=1, border_color=color)
    card.pack(fill="x", padx=10, pady=8)
    top_row=ctk.CTkFrame(card, fg_color="#1a1d27"); top_row.pack(fill="x", padx=15, pady=(12,6))
    ctk.CTkLabel(top_row, text=title, font=("Segoe UI", 15, "bold"), text_color=color).pack(side="left")
    win_label=ctk.CTkLabel(top_row, text="Winrate: 0%", font=("Segoe UI", 12, "bold"), text_color="#ffffff")
    win_label.pack(side="right")
    hdr=ctk.CTkFrame(card, fg_color="#23263a"); hdr.pack(fill="x", padx=12, pady=2)
    for i,txt in enumerate(["JENIS","COUNT","GROSS","NET"]):
        ctk.CTkLabel(hdr, text=txt, font=("Segoe UI", 12, "bold"), text_color="#ffffff", width=150 if i>0 else 80, anchor="w").pack(side="left", padx=10, pady=4)
    rows={}
    for rname in ["TP","SL","TOTAL"]:
        fr=ctk.CTkFrame(card, fg_color="#1e2235" if rname!="TOTAL" else "#2a2d45"); fr.pack(fill="x", padx=12, pady=1)
        ctk.CTkLabel(fr, text=rname, font=("Segoe UI", 13, "bold"), width=80, anchor="w", text_color="#00ff88" if rname=="TP" else "#ff5555" if rname=="SL" else "#ffcc00").pack(side="left", padx=10, pady=5)
        c_lbl=ctk.CTkLabel(fr, text="0x", font=("Segoe UI", 13), width=150, anchor="w"); c_lbl.pack(side="left", padx=10)
        g_lbl=ctk.CTkLabel(fr, text="Rp0", font=("Segoe UI", 13), width=150, anchor="w"); g_lbl.pack(side="left", padx=10)
        n_lbl=ctk.CTkLabel(fr, text="Rp0", font=("Segoe UI", 13, "bold"), width=150, anchor="w"); n_lbl.pack(side="left", padx=10)
        rows[rname]= (c_lbl,g_lbl,n_lbl)
    return rows, win_label

daily_rows, daily_win = make_table_card(stats_frame, "📅 HARI INI", "#00ff88")
weekly_rows, weekly_win = make_table_card(stats_frame, "📆 MINGGU INI", "#00ccff")
monthly_rows, monthly_win = make_table_card(stats_frame, "🗓️ BULAN INI", "#ffcc00")
total_rows, total_win = make_table_card(stats_frame, "💰 TOTAL KESELURUHAN (REALIZED)", "#cc88ff")

real_frame=ctk.CTkFrame(stats_frame, fg_color="#1a0f1f", corner_radius=12, border_width=2, border_color="#ff00ff")
real_frame.pack(fill="x", padx=10, pady=12)
ctk.CTkLabel(real_frame, text="🔴 REAL PORTO SYNC - FEE LIVE API", font=("Segoe UI", 15, "bold"), text_color="#ff44ff").pack(anchor="w", padx=15, pady=(12,4))
floating_label=ctk.CTkLabel(real_frame, text="Loading floating...", font=("Segoe UI", 13), justify="left", text_color="#ffffff", anchor="w")
floating_label.pack(anchor="w", padx=15, pady=4, fill="x")
total_real_label=ctk.CTkLabel(real_frame, text="Loading total real...", font=("Segoe UI", 14, "bold"), justify="left", text_color="#ff88ff", anchor="w")
total_real_label.pack(anchor="w", padx=15, pady=(4,12), fill="x")

hist_frame=ctk.CTkFrame(tabview.tab("HISTORY TRADE")); hist_frame.pack(fill="both", expand=True, padx=5, pady=5)
h_columns=("date","coin","type","pnl","gross","net","fee")
history_tree=ttk.Treeview(hist_frame, columns=h_columns, show="headings", height=20)
for col,w in zip(h_columns,[150,70,60,80,110,110,90]):
    history_tree.heading(col,text=col.upper()); history_tree.column(col,width=w,anchor="center")
history_tree.pack(fill="both", expand=True, padx=10, pady=10)

gui_log(f"V5.3.40 READY - KURS LIVE Rp{get_usdt_idr_cached():.0f} - TP {TP_PCT}%")

def update_stats_ui():
    try:
        d=summary_today(); w=summary_week(); m=summary_month(); a=summary_all()
        unreal=get_unrealized_summary(); real_porto=summary_real_porto()
        kurs=get_usdt_idr_cached(); buy_fee,sell_fee=get_fee_from_tokocrypto_api()
        def apply(rows, win_lbl, s):
            # TP hijau, SL merah, TOTAL kuning + winrate
            rows["TP"][0].configure(text=f"{s['tp_count']}x"); rows["TP"][1].configure(text=format_rp(s['tp_gross']), text_color="#00ff88" if s['tp_gross']>=0 else "#ff5555"); rows["TP"][2].configure(text=format_rp(s['tp_net']), text_color="#00ff88" if s['tp_net']>=0 else "#ff5555")
            rows["SL"][0].configure(text=f"{s['sl_count']}x"); rows["SL"][1].configure(text=format_rp(s['sl_gross']), text_color="#ff5555"); rows["SL"][2].configure(text=format_rp(s['sl_net']), text_color="#ff5555")
            rows["TOTAL"][0].configure(text=f"{s['tp_count']} TP / {s['sl_count']} SL");
            rows["TOTAL"][1].configure(text=format_rp(s['total_gross']), text_color="#00ff88" if s['total_gross']>=0 else "#ff5555");
            rows["TOTAL"][2].configure(text=format_rp(s['total_net']), text_color="#00ff88" if s['total_net']>=0 else "#ff5555")
            total_trades = s['tp_count'] + s['sl_count']
            winrate = (s['tp_count']/total_trades*100) if total_trades>0 else 0
            win_lbl.configure(text=f"Winrate {winrate:.1f}% ({s['tp_count']}W/{s['sl_count']}L) | Net {format_rp(s['total_net'])}", text_color="#00ff88" if winrate>=50 else "#ffaa00" if total_trades>0 else "#ffffff")
        apply(daily_rows,daily_win,d); apply(weekly_rows,weekly_win,w); apply(monthly_rows,monthly_win,m); apply(total_rows,total_win,a)

        if positions:
            lines=[]
            for coin,pos in list(positions.items()):
                curr=get_idr_price(coin)
                if curr<=0.000001: curr=get_usdt_price(coin)*kurs if get_usdt_price(coin)>0 else prices.get(coin,0)
                entry=pos.get('entry_price',0)
                if entry<=0.000001 or curr<=0.000001: continue
                pnl=(curr-entry)/entry*100; amount=pos.get('amount',0); kotor=(curr-entry)*amount; fee=(entry*amount*buy_fee)+(curr*amount*sell_fee); bersih=kotor-fee
                lines.append(f"• {coin}: {pnl:+.2f}% → Net {format_rp(bersih)} | Gross {format_rp(kotor)} | Fee Rp{int(fee)}")
            floating_text = f"REALIZED Net {format_rp(a['total_net'])}\n\nFLOATING:\n" + "\n".join(lines) + f"\n\nFloating Gross {format_rp(unreal['gross'])} Net {format_rp(unreal['net'])}"
        else:
            floating_text = f"REALIZED Net {format_rp(a['total_net'])}\nFLOATING: No POS"
        floating_label.configure(text=floating_text)
        total_real_label.configure(text=f"TOTAL PORTO ASLI = Realized + Floating = {format_rp(real_porto['total_net_asli'])} | Floating {', '.join(list(positions.keys())) or 'KOSONG'} Net {format_rp(real_porto['unrealized_net'])} | Fee {buy_fee*100:.4f}%/{sell_fee*100:.4f}% | Kurs Rp{kurs:.0f} Lock ${basket_data.get('lock_modal',0):.2f}")
        for i in history_tree.get_children(): history_tree.delete(i)
        for r in reversed(stats_data[-100:]):
            history_tree.insert("", "end", values=(r['date_str'], r['coin'], r['type'], f"{r['pnl_pct']}%", format_rp(r['gross_idr']), format_rp(r['net_idr']), format_rp(r['fee_idr'])))
    except Exception as e:
        gui_log(f"[STATS ERR] {e}")

def update_table():
    kurs=get_usdt_idr_cached(); idr=balance_cache["idr"]; usdt=balance_cache["usdt"]; bal=idr+usdt*kurs if kurs>0 else 0
    bal_label.configure(text=f"Rp{int(bal):,} | USDT:{usdt:.2f} IDR:{idr:.0f} kurs Rp{kurs:.0f} POS:{list(positions.keys())}")
    display_order=list(positions.keys())+[c for c in COINS if c not in positions]
    for coin in display_order:
        if coin not in prices and coin not in positions: continue
        price_idr=get_idr_price(coin)
        if price_idr<=0.000001:
            usdt_p=get_usdt_price(coin)
            if usdt_p>0: price_idr=usdt_p*kurs
            else: price_idr=prices.get(coin,0)
        if price_idr<=0.000001: price_idr=get_initial_price(coin)
        if price_idr>0.000001: prices[coin]=price_idr
        price=price_idr; prob=predict_ai(coin); tr=trained.get(coin,0)
        pu=get_usdt_price(coin) or (price/kurs if kurs>0 and price>0.000001 else 0)
        pos=positions.get(coin); live="OK" if is_coin_live(coin) else "OK" if coin in positions else "OFF"
        if pos:
            entry=pos.get('entry_price',0)
            if entry<=0.000001: entry=price; positions[coin]['entry_price']=entry
            pnl=(price-entry)/entry*100 if entry>0 and price>0.000001 else 0
            pt=f"{pos['amount']:.0f} @ {format_price_idr_smart(entry)}"; pn=f"{pnl:.2f}%"
        else:
            pt=f"NO POS {format_price_idr_smart(price)}"; pn="0%"
        rp_str = format_price_idr_smart(price)
        try: tree.item(coin, values=(coin, rp_str, f"${pu:.7f}", f"{prob:.1f}%", f"{tr}", pt, pn, live))
        except:
            try: tree.insert("", "end", iid=coin, values=(coin, rp_str, f"${pu:.7f}", f"{prob:.1f}%", f"{tr}", pt, pn, live))
            except: pass
    update_stats_ui()
    app.after(2000, update_table)

def bot_thread():
    global is_running,basket_data
    basket_data=load_basket(); gui_log(f"BOT STARTED V5.3.40 KURS LIVE Rp{get_usdt_idr_cached():.0f} READY")
    get_fee_from_tokocrypto_api(); get_usdt_idr(); get_balances_detail(force=True); refresh_all_prices(force=True)
    scan_tokocrypto_agresif(); restore_positions_from_exchange()
    threading.Thread(target=scanner_thread_loop, daemon=True).start()
    loop=0
    while is_running:
        try:
            loop+=1
            if loop%4==0: get_balances_detail(force=True); get_usdt_idr()
            if loop%30==0: get_fee_from_tokocrypto_api()
            refresh_all_prices(); kurs=get_usdt_idr_cached()
            for c in COINS:
                p_idr=PRICE_CACHE["idr"].get(c,0); p_usdt=PRICE_CACHE["usdt"].get(c,0); p=p_idr if p_idr>0 else (p_usdt*kurs if p_usdt>0 else 0)
                if p>0.000001:
                    prices[c]=p
                    if c not in history: history[c]=deque([p]*50, maxlen=200)
                    else: history[c].append(p)
            if loop%3==0:
                for c in COINS:
                    if prices.get(c,0)>0.000001: train_ai(c)
            for coin,pos in list(positions.items()):
                curr=prices.get(coin,0)
                if curr<=0.000001: curr=get_initial_price(coin)
                if curr<=0.000001 or pos['entry_price']<=0.000001: continue
                pnl=(curr-pos['entry_price'])/pos['entry_price']*100
                if pnl>=TP_PCT:
                    if place_sell(coin,is_tp=True): time.sleep(1.5)
                elif pnl<=SL_PCT: place_sell(coin,is_tp=False)
            if len(positions)<MAX_POS:
                idr,usdt,_=get_balances_detail()
                if usdt<1.0 and idr<15000:
                    if loop%20==0: gui_log(f"[WALLET] USDT ${usdt:.2f} - tunggu $1")
                    time.sleep(2.5); continue
                avail=[c for c in COINS if c not in positions and prices.get(c,0)>0.000001 and is_coin_live(c) and BUY_BLOCK_COOLDOWN.get(c,0)<=time.time()]
                if avail:
                    avail_sorted=sorted(avail, key=lambda x: predict_ai(x), reverse=True)
                    for candidate in avail_sorted[:5]:
                        if predict_ai(candidate)<MIN_AI_BUY: continue
                        if place_buy(candidate,0): break
        except Exception as e: gui_log(f"[ERR] {e}")
        time.sleep(4)

def start_bot():
    global is_running
    if is_running: return
    is_running=True
    try: start_btn.configure(state="disabled")
    except: pass
    threading.Thread(target=bot_thread, daemon=True).start()
    gui_log(f"START V5.3.40 KURS Rp{get_usdt_idr_cached():.0f}")

def buy_max_all():
    def do_buy():
        idr,usdt,_=get_balances_detail(force=True); slots=MAX_POS-len(positions)
        if slots<=0: gui_log("[BUY MAX] Slot penuh"); return
        avail=[c for c in COINS if c not in positions and prices.get(c,0)>0.000001 and is_coin_live(c)]
        avail_sorted=sorted(avail, key=lambda x: predict_ai(x), reverse=True)
        gui_log(f"[BUY MAX] top:{avail_sorted[:5]} USDT ${usdt:.2f} slots:{slots}")
        for coin in avail_sorted[:slots*2]:
            if len(positions)>=MAX_POS: break
            if predict_ai(coin)<MIN_AI_BUY: continue
            if BUY_BLOCK_COOLDOWN.get(coin,0)>time.time(): continue
            place_buy(coin,0); time.sleep(1.5)
    threading.Thread(target=do_buy, daemon=True).start()

def sell_all_max():
    def do_sell():
        for coin in list(positions.keys()): place_sell(coin,is_tp=False); time.sleep(1.2)
    threading.Thread(target=do_sell, daemon=True).start()

def manual_scan(): threading.Thread(target=scan_tokocrypto_agresif, daemon=True).start()
def manual_sync(): threading.Thread(target=restore_positions_from_exchange, daemon=True).start()

start_btn=ctk.CTkButton(btn_frame, text="START", fg_color="#00aa66", command=start_bot, width=100, height=42); start_btn.pack(side="left", padx=5)
ctk.CTkButton(btn_frame, text="BUY MAX", fg_color="#00cc88", command=buy_max_all, width=100, height=42).pack(side="left", padx=5)
ctk.CTkButton(btn_frame, text="SELL MAX", fg_color="#ffaa00", command=sell_all_max, width=90, height=42).pack(side="left", padx=5)
ctk.CTkButton(btn_frame, text="SCAN MEME", fg_color="#aa00ff", command=manual_scan, width=110, height=42).pack(side="left", padx=5)
ctk.CTkButton(btn_frame, text="SYNC WALLET", fg_color="#0066ff", command=manual_sync, width=110, height=42).pack(side="left", padx=5)

update_table()
app.mainloop()