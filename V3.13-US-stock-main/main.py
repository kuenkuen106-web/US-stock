#@title ⚙️ V3.13 PRO QUANT ALERTS (Guru Edition - Track Record & Charts)
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  C1  QUANT MASTER V3.13  —  機構級量化選股系統 (社群跟單版)            ║
# ║  完整保留大盤 SPX 圖表 · 個股回測圖表 · 自動紙上交易追蹤 · 防封鎖下載  ║
# ╚══════════════════════════════════════════════════════════════════════════╝
LOOKBACK_YEARS        = 3     
FTD_VALID_DAYS        = 20    
MAX_VOLATILITY_PCT    = 0.06  
MAX_ACCOUNT_RISK_PCT  = 0.01  
VIX_PANIC_THRESHOLD   = 25    
TOP10_PRESET = 1  
_T10 = {1:(75,4.0,20),2:(75,4.5,20),3:(75,3.5,20),4:(75,4.0,15),5:(75,4.5,15),
        6:(75,3.5,15),7:(82,4.0,15),8:(82,3.5,15),9:(82,4.5,15),10:(78,4.0,15)}
PQR_VCP_MIN, _VCP_TP, TIME_STOP_DAYS = _T10[TOP10_PRESET]
ATR_STOP_LOSS_MULT = 2.5   
PQR_ENTRY_MIN  = 75   
PQR_TECH_MIN   = 78
PATTERN_TP_MULT = {'VCP':_VCP_TP,'P4_TightCoil':4.5,'P2_PostEarnings':3.5,'P5_RSI_Bounce':3.0,'P6_XS_Mom':4.0}
DEFAULT_TP_MULT = 4.0
TRAIL_TRIGGER_ATR = 3.0
TRAIL_DISTANCE_ATR = 1.5
VIX_PANIC_ALLOWED_PATTERNS = frozenset({'P2_PostEarnings','P5_RSI_Bounce','P6_XS_Mom'})
NORMAL_MODE_PATTERNS       = frozenset({'VCP','P2_PostEarnings','P4_TightCoil'})
CRASH_PROTECT_SPY_MONTHLY  = -0.12
SECTOR_FILTER_ENABLED = True  
BLACKLIST_SECTORS = ['Real Estate', 'Healthcare', 'Consumer Defensive', 'Basic Materials']
ELEVATED_BAR_SECTORS = {'Technology'}

# =============================================================================
import subprocess, sys, time
subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "yfinance", "lxml", "html5lib", "beautifulsoup4", "-q"])

import pandas as pd, numpy as np, yfinance as yf, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt, matplotlib.dates as mdates, requests, concurrent.futures
from io import StringIO
import warnings, os, datetime, shutil, json, logging

logging.getLogger('yfinance').setLevel(logging.CRITICAL)
warnings.filterwarnings('ignore')
plt.style.use('seaborn-v0_8-dark')
plt.ioff()

OUTPUT_DIR = "public"
CHARTS_DIR = os.path.join(OUTPUT_DIR, "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)

# 讀取追蹤紀錄 (Track Record)
TRACK_FILE = os.path.join(OUTPUT_DIR, "track_record.json")
if os.path.exists(TRACK_FILE):
    try:
        with open(TRACK_FILE, "r") as f: track_data = json.load(f)
    except: track_data = {"open": {}, "closed": []}
else:
    track_data = {"open": {}, "closed": []}

# =============================================================================
# MODULE 1 & 2 — Stock universe & Fundamentals
# =============================================================================
print("⏳ [1-2/7] 建立股票池與基本面...")
_SP500_CORE = ['AAPL','MSFT','NVDA','GOOGL','GOOG','AMZN','META','TSLA','AVGO','ORCL','AMD','QCOM','NFLX','DIS','NKE','SBUX','MCD','XOM','CVX','CAT','DE','LMT','JPM','BAC','GS','V','MA','PYPL','CRM','ADBE','NOW','PLTR','LLY','UNH','SPY','QQQ','IWM','SMH','^VIX']
_ALL_HARDCODED = list(dict.fromkeys(_SP500_CORE))
_wiki_extra = []
try:
    r = requests.get('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies', headers={'User-Agent': 'Mozilla/5.0'}, timeout=7)
    df = pd.read_html(StringIO(r.text))[0]
    _wiki_extra = df['Symbol'].str.replace('.', '-').head(250).tolist()
except: pass
ALL_TICKERS = list(dict.fromkeys(_ALL_HARDCODED + _wiki_extra))

fund_data = {}
def _fetch_fund(tk):
    try: return tk, {'sector': yf.Ticker(tk).info.get('sector', 'ETF/Index')}
    except: return tk, {'sector': 'Unknown'}
with concurrent.futures.ThreadPoolExecutor(max_workers=15) as _ex:
    for _r in _ex.map(_fetch_fund, ALL_TICKERS): fund_data[_r[0]] = _r[1]

# =============================================================================
# MODULE 3 — Price download
# =============================================================================
print(f"⏳ [3/7] 獲取歷史價格 (共 {len(ALL_TICKERS)} 檔)...")
def _dl(tks, period):
    try: return yf.download(tks, period=period, progress=False, threads=False)
    except: return pd.DataFrame()

_non_vix = [t for t in ALL_TICKERS if t != '^VIX']; _BSZ = 80 
_cls_l, _vol_l, _low_l, _hi_l = [], [], [], []
for _b in range(0, len(_non_vix), _BSZ):
    _chunk = _non_vix[_b:_b + _BSZ]
    print(f"      Batch {_b//_BSZ+1}/{-(-len(_non_vix)//_BSZ)}...")
    _raw = _dl(_chunk, f"{LOOKBACK_YEARS}y"); time.sleep(1.5) 
    if _raw.empty: continue
    def _e(d, f):
        if isinstance(d.columns, pd.MultiIndex): return d[f].ffill() if f in d.columns.get_level_values(0) else pd.DataFrame()
        return d[[f]].ffill() if f in d.columns else pd.DataFrame()
    _cls_l.append(_e(_raw, 'Close')); _vol_l.append(_e(_raw, 'Volume')); _low_l.append(_e(_raw, 'Low')); _hi_l.append(_e(_raw, 'High'))

def _mg(lst): return pd.concat(lst, axis=1).loc[:, ~pd.concat(lst, axis=1).columns.duplicated()] if lst else pd.DataFrame()
closes = _mg(_cls_l); vols = _mg(_vol_l); lows = _mg(_low_l); highs = _mg(_hi_l)
if closes.empty: raise ValueError("嚴重錯誤：所有股票資料下載失敗。")

_vraw = _dl(['^VIX'], f"{LOOKBACK_YEARS}y")
if not _vraw.empty: vix_c = (_vraw['Close']['^VIX'] if isinstance(_vraw.columns, pd.MultiIndex) and '^VIX' in _vraw['Close'].columns else _vraw['Close'] if 'Close' in _vraw.columns else pd.Series(20, index=closes.index)).ffill()
else: vix_c = pd.Series(20, index=closes.index)

spy_c = closes['SPY'] if 'SPY' in closes.columns else closes.iloc[:, 0]
spy_l = lows['SPY'] if 'SPY' in lows.columns else lows.iloc[:, 0]
spy_v = vols['SPY'] if 'SPY' in vols.columns else vols.iloc[:, 0]
vix_c = vix_c.reindex(spy_c.index).ffill().bfill()
spy_20 = spy_c.rolling(20).mean(); spy_50 = spy_c.rolling(50).mean(); spy_200 = spy_c.rolling(200).mean()
spy_monthly_ret = spy_c.pct_change(21); is_crash_series = spy_monthly_ret < CRASH_PROTECT_SPY_MONTHLY
r126 = closes / closes.shift(126) - 1; r252 = closes / closes.shift(252) - 1
rs_rank = ((0.6 * r126) + (0.4 * r252)).rank(axis=1, pct=True) * 99 + 1
rs_momentum = rs_rank - rs_rank.shift(20)

# =============================================================================
# MODULE 4 & 5 — Indicators & Engine
# =============================================================================
print("⏳ [4-5/7] 執行指標與大盤圖表繪製...")
sma50_all = closes.rolling(50).mean()
sma200_all = closes.rolling(200).mean()

curr_breadth_50 = round(float(((closes > sma50_all).sum(axis=1) / closes.shape[1] * 100).iloc[-1]), 1)
curr_breadth_200 = round(float(((closes > sma200_all).sum(axis=1) / closes.shape[1] * 100).iloc[-1]), 1)

# 大盤分布日計算
dist_mask = (spy_c.pct_change() < -0.002) & (spy_v > spy_v.shift(1))
dist_dates = spy_c.index[dist_mask]
ftd_history = np.zeros(len(spy_c)); ftd_dates = []; rday = 0; rlow = float('inf')
for _i in range(1, len(spy_c)):
    _c, _pc = spy_c.iloc[_i], spy_c.iloc[_i - 1]; _l, _v, _pv = spy_l.iloc[_i], spy_v.iloc[_i], spy_v.iloc[_i - 1]
    if _l < rlow: rlow = _l; rday = 1 if _c > _pc else 0
    else: rday = max(1, rday + 1) if _c > _pc else (rday + 1 if rday > 0 else 0)
    if rday >= 4 and _c > _pc * 1.012 and _v > _pv: rlow, rday = _c, 0; ftd_dates.append(spy_c.index[_i])

is_bull_market = bool(spy_c.iloc[-1] > spy_200.iloc[-1])
curr_vix_val = float(vix_c.iloc[-1]); is_curr_panic = curr_vix_val >= VIX_PANIC_THRESHOLD
curr_spy_mret = float(spy_monthly_ret.iloc[-1]) if not pd.isna(spy_monthly_ret.iloc[-1]) else 0.0
is_curr_crash = curr_spy_mret < CRASH_PROTECT_SPY_MONTHLY

# ── 繪製 SPX 大盤圖表 ──
fig, ax = plt.subplots(figsize=(14, 5), dpi=120)
ax.plot(spy_c.index[-200:], spy_c.iloc[-200:], color='#cbd5e1', lw=2.0, label='SPX')
ax.plot(spy_20.index[-200:],  spy_20.iloc[-200:],  color='#3b82f6', lw=1.3, alpha=0.85, label='20MA')
ax.plot(spy_50.index[-200:],  spy_50.iloc[-200:],  color='#f59e0b', lw=1.3, alpha=0.85, label='50MA')
ax.plot(spy_200.index[-200:], spy_200.iloc[-200:], color='#dc2626', lw=2.0, ls='-.', label='200MA')
_rf = [d for d in ftd_dates if d >= spy_c.index[-200]]; _rd = [d for d in dist_dates if d >= spy_c.index[-200]]
if _rf: ax.scatter(_rf, spy_c.loc[_rf] * 0.97, marker='^', color='#10b981', s=140, label='FTD', zorder=5)
if _rd: ax.scatter(_rd, spy_c.loc[_rd] * 1.02, marker='v', color='#ef4444', s=55, label='Dist', zorder=5)
fig.patch.set_facecolor('#0f172a'); ax.set_facecolor('#0f172a')
ax.tick_params(colors='white', labelsize=9); ax.xaxis.set_major_formatter(mdates.DateFormatter('%y-%m')); plt.xticks(rotation=20)
ax.legend(facecolor='#1e293b', labelcolor='white', loc='upper left', ncol=4, fontsize=9)
for sp in ax.spines.values(): sp.set_edgecolor('#334155')
plt.tight_layout(); plt.savefig(os.path.join(CHARTS_DIR, "SPY_Trend.png"), transparent=True); plt.close(fig)

def _compute_pqr_score(c, h, l, v, sma50, sma200, rs, rs_mom, atr):
    score = pd.Series(0.0, index=c.index)
    score += (sma50 > sma200).fillna(False).astype(float) * 10
    score += (sma50 > sma50.shift(10)).fillna(False).astype(float) * 12
    score += (c > sma50).fillna(False).astype(float) * 8
    score += ((l <= sma50 * 1.015) & (c >= sma50 * 0.97)).fillna(False).astype(float) * 10
    score += (rs > 70).fillna(False).astype(float) * 10
    score += (rs > 85).fillna(False).astype(float) * 8
    score += (rs_mom > 0).fillna(False).astype(float) * 12
    score += (rs_mom > 5).fillna(False).astype(float) * 10
    score += ((atr / c.replace(0, np.nan)) < 0.03).fillna(False).astype(float) * 8
    return score.clip(0, 100)

def _precompute_vec_signals(c, h, l, v, sma20, rs_mom_s):
    out = {}
    try: _gap = c.pct_change(); _avp = v.rolling(20).mean().shift(1); out['P2_PostEarnings'] = ((_gap >= 0.05) & (v / _avp.replace(0, np.nan) >= 2.0)).fillna(False)
    except: out['P2_PostEarnings'] = pd.Series(False, index=c.index)
    try: _rmax = c.rolling(16).max(); _rmin = c.rolling(16).min(); _cr = (_rmax - _rmin) / _rmin.replace(0, np.nan); _pm = c.shift(16).rolling(15, min_periods=10).max(); _pmi = c.shift(16).rolling(15, min_periods=10).min(); _pr = (_pm - _pmi) / _pmi.replace(0, np.nan); _bref = c.shift(1).rolling(15, min_periods=10).max(); out['P4_TightCoil'] = ((_cr <= 0.04) & (_pr > _cr) & (c > _bref * 1.005) & (rs_mom_s > 0)).fillna(False)
    except: out['P4_TightCoil'] = pd.Series(False, index=c.index)
    return out

try: _r20h = closes.pct_change(20); xs_signal_hist = _r20h.ge(_r20h.quantile(0.90, axis=1), axis=0) & (closes <= highs.rolling(10).max().shift(1) * 1.05)
except: xs_signal_hist = pd.DataFrame(dtype=bool)

def _apply_vix_pattern_gate(triggered_pats, bar_vix, in_panic):
    if in_panic: return [p for p in triggered_pats if p in VIX_PANIC_ALLOWED_PATTERNS]
    else: return [p for p in triggered_pats if p in NORMAL_MODE_PATTERNS]

etf_js_data = []; today_str = closes.index[-1].strftime('%Y-%m-%d')

for ticker in ALL_TICKERS:
    if ticker == '^VIX' or ticker not in closes.columns: continue
    try:
        c = closes[ticker]; h = highs[ticker]; l = lows[ticker]; v = vols[ticker]
        if c.isna().sum() > 50: continue
        sector = fund_data.get(ticker, {}).get('sector', ''); is_bl = SECTOR_FILTER_ENABLED and (sector in BLACKLIST_SECTORS)
        sma20 = c.rolling(20).mean(); sma50 = c.rolling(50).mean(); sma200 = c.rolling(200).mean()
        atr = (pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1).ewm(alpha=1/14, adjust=False).mean())
        too_v = (atr / c) > MAX_VOLATILITY_PCT; rs = rs_rank[ticker]; rs_mom = rs_momentum[ticker]
        bull_s = spy_c.reindex(c.index).ffill() > spy_200.reindex(c.index).ffill()
        
        pqr_score = _compute_pqr_score(c, h, l, v, sma50, sma200, rs, rs_mom, atr)
        vec_sigs = _precompute_vec_signals(c, h, l, v, sma20, rs_mom)

        # Update Existing Track Record (紙上交易更新)
        for k, t in list(track_data["open"].items()):
            if t["ticker"] == ticker:
                cp = float(c.iloc[-1]); hp = float(h.iloc[-1]); lp = float(l.iloc[-1])
                if lp <= t["sl"]:
                    t["exit_date"] = today_str; t["exit_price"] = t["sl"]; t["result"] = "LOSS"
                    t["return_pct"] = round((t["sl"] / t["entry_price"] - 1) * 100, 2)
                    track_data["closed"].insert(0, t); del track_data["open"][k]
                elif hp >= t["tp"]:
                    t["exit_date"] = today_str; t["exit_price"] = t["tp"]; t["result"] = "WIN"
                    t["return_pct"] = round((t["tp"] / t["entry_price"] - 1) * 100, 2)
                    track_data["closed"].insert(0, t); del track_data["open"][k]
                else:
                    t["curr_price"] = cp; t["return_pct"] = round((cp / t["entry_price"] - 1) * 100, 2)

        # PQR 分數計算：加上百分位數打破平局 (e.g. 85.99)
        curr_pqr = round(float(pqr_score.iloc[-1]) + float(rs.iloc[-1])/100.0, 2)
        
        curr_macro_safe = not is_curr_crash if is_curr_panic else bool(bull_s.iloc[-1])
        curr_raw_t = [pk for pk in ['P2_PostEarnings', 'P4_TightCoil'] if vec_sigs.get(pk) is not None and bool(vec_sigs[pk].iloc[-1])]
        if not xs_signal_hist.empty and ticker in xs_signal_hist.columns and c.index[-1] in xs_signal_hist.index and bool(xs_signal_hist.loc[c.index[-1], ticker]): curr_raw_t.append('P6_XS_Mom')
        
        curr_triggered = _apply_vix_pattern_gate(curr_raw_t, curr_vix_val, is_curr_panic)
        
        is_active = bool(curr_triggered) and curr_macro_safe and (not is_bl) and not bool(too_v.iloc[-1]) and curr_pqr >= PQR_ENTRY_MIN
        is_risk_blocked = bool(curr_triggered) and not is_active
        
        cp = float(c.iloc[-1]); catr = float(atr.iloc[-1])
        ctpm = max((PATTERN_TP_MULT.get(p, 4.0) for p in curr_triggered), default=4.0) if curr_triggered else 4.0
        csl2 = cp - ATR_STOP_LOSS_MULT * catr; ctp2 = cp + ctpm * catr
        is_late_join = (cp - csl2 - ATR_STOP_LOSS_MULT * catr) / catr > 1.0 if catr > 0 else False

        # ── 繪製個股回測圖表 ──
        has_chart = False
        if is_active or curr_pqr >= 80:
            try:
                _pd2 = pd.DataFrame({'Close': c, 'SMA50': sma50, 'SMA20': sma20}).last('252D')
                fig2, ax2 = plt.subplots(figsize=(8, 4), dpi=100)
                ax2.plot(_pd2.index, _pd2.Close, color='#cbd5e1', lw=1.5)
                ax2.plot(_pd2.index, _pd2.SMA50,  color='#f59e0b', lw=1.8)
                ax2.plot(_pd2.index, _pd2.SMA20,  color='#3b82f6', lw=1.0, ls='--', alpha=0.6)
                ax2.axhline(cp,     color='#22c55e',  lw=1.2, ls='--', alpha=0.9, label=f'Current ${cp:.2f}')
                ax2.axhline(csl2,   color='#ef4444',  lw=1.2, ls='--', alpha=0.9, label=f'Stop ${csl2:.2f}')
                ax2.text(0.01, 0.97, f"PQR={curr_pqr:.2f} TPx{ctpm:.1f}", transform=ax2.transAxes, color='#94a3b8', fontsize=7, va='top')
                ax2.set_facecolor('#1e293b'); fig2.patch.set_facecolor('#1e293b')
                ax2.tick_params(colors='white', labelsize=8)
                ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                ax2.legend(facecolor='#0f172a', labelcolor='white', fontsize=7, loc='upper left')
                plt.xticks(rotation=30); plt.tight_layout()
                plt.savefig(os.path.join(CHARTS_DIR, f"{ticker}_bt.png"), transparent=True)
                plt.close(fig2); has_chart = True
            except: pass

        # 加入新的紙上交易 (Paper Trading)
        if is_active:
            already_open = any(v["ticker"] == ticker for v in track_data["open"].values())
            if not already_open:
                trade_id = f"{ticker}_{today_str}"
                track_data["open"][trade_id] = {
                    "ticker": ticker, "entry_date": today_str,
                    "entry_price": round(cp, 2), "sl": round(csl2, 2), "tp": round(ctp2, 2),
                    "curr_price": round(cp, 2), "return_pct": 0.0, "patterns": curr_triggered
                }

        # Dashboard JS 數據
        if is_active or curr_pqr >= 80:
            etf_js_data.append({
                'ticker': ticker, 'sector': sector, 'status': "🔥 Active" if is_active else "Idle",
                'pqr': curr_pqr, 'curr_price': round(cp, 2), 'sl_price': round(csl2, 2), 'tp_price': round(ctp2, 2),
                'patterns': curr_triggered if curr_triggered else ['WATCHING'],
                'is_late': is_late_join, 'is_risk_blocked': is_risk_blocked, 'has_chart': has_chart
            })
    except Exception: pass

# 儲存 Track Record
with open(TRACK_FILE, "w", encoding="utf-8") as f:
    json.dump(track_data, f, indent=2)

# =============================================================================
# MODULE 7 — Dashboard Generation 
# =============================================================================
print("⏳ [6/7] 生成 HTML Dashboard...")

if is_curr_crash and is_curr_panic: ftd_status = "崩潰保護"; ftd_color = "text-red-300 border-red-500/50"
elif is_curr_panic: ftd_status = f"恐慌模式"; ftd_color = "text-orange-400 border-orange-500/40"
elif is_bull_market: ftd_status = "大多頭"; ftd_color = "text-emerald-400 border-emerald-500/20"
else: ftd_status = "震盪整理"; ftd_color = "text-amber-500 border-amber-500/20"

_PMETA = json.dumps({
    "P2_PostEarnings": {"label":"財報跳空", "color":"#f97316"},
    "P4_TightCoil": {"label":"窄幅橫盤", "color":"#14b8a6"},
    "P5_RSI_Bounce": {"label":"超跌反彈", "color":"#ef4444"},
    "P6_XS_Mom": {"label":"動能領漲", "color":"#6366f1"},
    "WATCHING": {"label":"建底觀察", "color":"#8b5cf6"}
})

html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<script src="https://cdn.tailwindcss.com"></script>
<title>量化交易達人 (PRO QUANT ALERTS)</title>
</head>
<body class="bg-[#0b0f1a] text-slate-200 font-sans min-h-screen flex flex-col">

<div id="lbox" onclick="this.classList.add('hidden')" class="hidden fixed inset-0 bg-black/90 z-50 flex items-center justify-center cursor-zoom-out p-4">
    <img id="lbox-img" src="" class="max-w-full max-h-full object-contain rounded-lg shadow-2xl">
    <p class="absolute bottom-10 text-slate-400 text-sm font-bold bg-black/50 px-4 py-2 rounded">點擊任意處關閉</p>
</div>

<header class="bg-gradient-to-r from-slate-900 to-blue-950 border-b border-blue-500/30 p-4 shrink-0 shadow-2xl relative overflow-hidden">
  <div class="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-10"></div>
  <div class="flex flex-col md:flex-row justify-between items-center max-w-6xl mx-auto gap-4 relative z-10">
    <div>
      <h1 class="text-2xl font-black text-white tracking-tight uppercase">PRO <span class="text-blue-400">Quant Alerts</span></h1>
      <p class="text-[10px] text-blue-200 opacity-80 mt-1 uppercase tracking-widest font-bold italic">資料驅動的機構級交易訊號</p>
    </div>
    
    <div class="flex gap-3 w-full md:w-auto">
      <div class="flex-1 text-center px-4 py-2 rounded-xl bg-slate-900/80 border border-slate-700">
        <span class="block text-[9px] text-slate-400 uppercase font-black tracking-wider mb-1">大盤情緒</span>
        <span class="text-sm font-black {ftd_color.split(' ')[0]}">{ftd_status}</span>
      </div>
      <div class="flex-1 text-center px-4 py-2 rounded-xl bg-slate-900/80 border border-slate-700">
        <span class="block text-[9px] text-slate-400 uppercase font-black tracking-wider mb-1">大盤廣度 (>MA)</span>
        <span class="text-xs font-black text-blue-400">50日: {curr_breadth_50}% | 200日: {curr_breadth_200}%</span>
      </div>
    </div>
  </div>
</header>

<main class="flex-1 max-w-6xl mx-auto w-full p-4 md:p-6 flex flex-col gap-6">
  
  <div class="flex gap-2 border-b border-slate-800 pb-2">
    <button onclick="switchTab('signals')" id="tab-signals" class="px-5 py-2 text-sm font-bold rounded-lg bg-blue-600 text-white shadow-lg transition-all">🎯 今日訊號</button>
    <button onclick="switchTab('track')" id="tab-track" class="px-5 py-2 text-sm font-bold rounded-lg text-slate-400 hover:bg-slate-800 hover:text-white transition-all">🏆 追蹤紀錄</button>
    <button onclick="switchTab('manual')" id="tab-manual" class="px-5 py-2 text-sm font-bold rounded-lg text-slate-400 hover:bg-slate-800 hover:text-white transition-all">📖 跟單說明書</button>
  </div>

  <div id="view-signals" class="block space-y-10">
  
    <div class="bg-slate-900/50 border border-slate-800 rounded-2xl p-4 flex flex-col lg:flex-row gap-4 items-center">
        <div class="w-full lg:w-1/3">
            <h3 class="font-black text-white text-lg">大盤參考 (SPX)</h3>
            <p class="text-xs text-slate-400 mt-1">進場前請確認大盤趨勢。圖中紅線為 200MA，黃線為 50MA。點擊圖表可放大。</p>
        </div>
        <div class="w-full lg:w-2/3 cursor-zoom-in hover:opacity-80 transition-opacity" onclick="document.getElementById('lbox-img').src='charts/SPY_Trend.png'; document.getElementById('lbox').classList.remove('hidden');">
            <img src="charts/SPY_Trend.png" alt="SPX Chart" class="w-full rounded-lg border border-slate-800">
        </div>
    </div>

    <section>
      <div class="flex justify-between items-end mb-6">
        <div>
          <h2 class="text-xl font-black text-white border-l-4 border-blue-500 pl-3">🔥 今日進場訊號 (Actionable)</h2>
          <p class="text-xs text-slate-500 mt-2 pl-4">通過全部風險檢測，並於今日觸發買進條件的強勢標的。</p>
        </div>
      </div>
      <div id="trig-list" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5"></div>
    </section>

    <section>
      <div class="flex justify-between items-end mb-6">
        <div>
          <h2 class="text-xl font-black text-white border-l-4 border-purple-500 pl-3">👀 潛力觀察名單 (Watchlist)</h2>
          <p class="text-xs text-slate-500 mt-2 pl-4">基本面與資金面最高分 (PQR > 80)。帶有「🛡️系統擋單」代表因震盪過大被安全機制攔截。</p>
        </div>
      </div>
      <div id="watch-list" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5"></div>
    </section>
  </div>

  <div id="view-track" class="hidden space-y-10">
    <section>
      <h2 class="text-xl font-black text-white border-l-4 border-amber-500 pl-3 mb-6">📈 系統自動追蹤 (Open Positions)</h2>
      <div id="open-list" class="grid grid-cols-1 md:grid-cols-2 gap-4"></div>
    </section>
    <section>
      <h2 class="text-xl font-black text-white border-l-4 border-slate-500 pl-3 mb-6">🏁 已平倉紀錄 (Closed Trades)</h2>
      <div id="closed-list" class="grid grid-cols-1 md:grid-cols-3 gap-4"></div>
    </section>
  </div>

  <div id="view-manual" class="hidden">
    <div class="bg-slate-900 rounded-3xl border border-slate-800 p-8 max-w-3xl mx-auto shadow-2xl">
      <h2 class="text-2xl font-black text-white mb-2 text-center tracking-tight">跟單 <span class="text-blue-500">三步驟</span> 計畫</h2>
      <p class="text-center text-slate-400 text-sm mb-10">摒除情緒，讓量化系統替你過濾雜訊。</p>
      
      <div class="space-y-8">
        <div class="flex gap-5">
          <div class="w-12 h-12 shrink-0 rounded-full bg-blue-500/20 border border-blue-500 text-blue-400 flex items-center justify-center font-black text-xl shadow-[0_0_15px_rgba(59,130,246,0.3)]">1</div>
          <div>
            <h3 class="font-black text-white text-lg tracking-wide">確認大盤情緒：自動切換模式</h3>
            <p class="text-slate-400 text-sm mt-2 leading-relaxed">
            系統會根據儀表板右上角的「恐慌指數 (VIX)」自動切換檔位：<br>
            • <strong class="text-emerald-400">平時模式 (VIX < 25)</strong>：尋找穩健的窄幅橫盤突破 (P4) 或財報利多 (P2)。<br>
            • <strong class="text-orange-400">恐慌模式 (VIX ≥ 25)</strong>：切換為尋找極端超跌 (P5) 或最強動能領漲股 (P6)。<br>
            • <strong class="text-red-400">崩潰保護 (Crash)</strong>：若大盤月跌幅過深，系統將鎖死買進訊號，強制空手。</p>
          </div>
        </div>
        
        <div class="flex gap-5">
          <div class="w-12 h-12 shrink-0 rounded-full bg-blue-500/20 border border-blue-500 text-blue-400 flex items-center justify-center font-black text-xl shadow-[0_0_15px_rgba(59,130,246,0.3)]">2</div>
          <div>
            <h3 class="font-black text-white text-lg tracking-wide">從「今日進場訊號」挑選</h3>
            <p class="text-slate-400 text-sm mt-2 leading-relaxed">請只購買 <strong class="text-white">🔥 今日進場訊號</strong> 區塊內的股票。卡片上的 <strong class="text-emerald-400">PQR 分數</strong> (如 85.99) 的小數點代表該股票在全市場的相對強度 (RS)，分數越高代表資金動能越強。</p>
          </div>
        </div>

        <div class="flex gap-5">
          <div class="w-12 h-12 shrink-0 rounded-full bg-blue-500/20 border border-blue-500 text-blue-400 flex items-center justify-center font-black text-xl shadow-[0_0_15px_rgba(59,130,246,0.3)]">3</div>
          <div>
            <h3 class="font-black text-white text-lg tracking-wide">嚴格執行價格計畫</h3>
            <p class="text-slate-400 text-sm mt-2 leading-relaxed">
            <br>• <strong class="text-white border-b border-slate-600 pb-0.5">買進價 (BUY AT):</strong> 當前建議的進場價格。
            <br>• <strong class="text-red-400 border-b border-red-900 pb-0.5">止損價 (STOP):</strong> 買入後請<strong class="text-white">立刻設定觸價停損單</strong>。
            <br>• <strong class="text-emerald-400 border-b border-emerald-900 pb-0.5">目標價 (TARGET):</strong> 系統計算的合理獲利出場點。</p>
          </div>
        </div>
      </div>
    </div>
  </div>

</main>

<script>
const rawData = {json.dumps(etf_js_data)};
const trackData = {json.dumps(track_data)};
const PM = JSON.parse('{_PMETA}');

function switchTab(tab) {{
  ['signals', 'track', 'manual'].forEach(t => {{
    document.getElementById('view-' + t).classList.toggle('hidden', tab !== t);
    const btn = document.getElementById('tab-' + t);
    if(tab === t) btn.className = "px-5 py-2 text-sm font-bold rounded-lg bg-blue-600 text-white shadow-lg transition-all";
    else btn.className = "px-5 py-2 text-sm font-bold rounded-lg text-slate-400 hover:bg-slate-800 hover:text-white transition-all";
  }});
}}

// createCard Function Restored with Backtest Chart Button
function createCard(d, isActive) {{
  const badgeTheme = isActive ? "text-blue-300 bg-blue-500/10 border-blue-500/20" : "text-purple-300 bg-purple-500/10 border-purple-500/20";
  const hover = isActive ? "hover:border-blue-500/50" : "hover:border-purple-500/30";
  const lateBadge = isActive && d.is_late ? '<span class="absolute top-4 right-4 bg-amber-500/20 text-amber-400 text-[9px] font-black px-2 py-1 rounded border border-amber-500/30 z-20">⚠️ 已延遲</span>' : '';
  const riskBlockBadge = !isActive && d.is_risk_blocked ? '<span class="absolute top-4 right-4 bg-red-500/20 text-red-400 text-[9px] font-black px-2 py-1 rounded border border-red-500/30 z-20">🛡️ 系統擋單</span>' : '';
  
  // RESTORED: Backtest Chart Button
  const chartBtn = d.has_chart ? `<button onclick="document.getElementById('lbox-img').src='charts/${{d.ticker}}_bt.png'; document.getElementById('lbox').classList.remove('hidden');" class="mt-4 w-full py-2 bg-slate-800 hover:bg-slate-700 text-xs font-bold text-slate-300 rounded-lg transition-colors border border-slate-700">📈 查看個股回測圖</button>` : '';

  return `
    <div class="bg-slate-900 border border-slate-800 rounded-3xl p-6 ${{hover}} transition-all shadow-xl flex flex-col relative overflow-hidden">
      ${{lateBadge}} ${{riskBlockBadge}}
      
      <div class="flex justify-between items-start mb-5">
        <div>
          <div class="text-3xl font-black text-white">${{d.ticker}}</div>
          <div class="text-[9px] font-bold text-slate-500 uppercase mt-0.5 tracking-widest">${{d.sector || 'Stock'}}</div>
        </div>
        <div class="flex flex-col items-end">
          <span class="text-[9px] text-slate-500 uppercase font-black">PQR 分數</span>
          <span class="text-xl font-black text-emerald-400 drop-shadow-[0_0_8px_rgba(52,211,153,0.3)]">${{d.pqr.toFixed(2)}}</span>
        </div>
      </div>
      
      <div class="grid grid-cols-3 gap-1 mb-5 bg-slate-950/80 rounded-2xl p-4 border border-slate-800/80">
        <div class="text-center">
          <div class="text-[9px] text-slate-500 font-bold mb-1 uppercase tracking-wider">${{isActive ? '買進價' : '當前價'}}</div>
          <div class="text-lg font-black text-white">$${{d.curr_price}}</div>
        </div>
        <div class="text-center border-x border-slate-800/80">
          <div class="text-[9px] text-red-500/80 font-bold mb-1 uppercase tracking-wider">止損價</div>
          <div class="text-lg font-black text-red-400">$${{d.sl_price}}</div>
        </div>
        <div class="text-center">
          <div class="text-[9px] text-emerald-500/80 font-bold mb-1 uppercase tracking-wider">目標價</div>
          <div class="text-lg font-black text-emerald-400">$${{d.tp_price}}</div>
        </div>
      </div>

      <div class="flex flex-wrap gap-2 mt-auto">
        ${{d.patterns.map(p => `<span class="text-[10px] font-black uppercase px-2.5 py-1 rounded-md border ${{badgeTheme}}">${{PM[p]?.label || p}}</span>`).join('')}}
      </div>
      
      ${{chartBtn}}
    </div>
  `;
}}

function render() {{
  const active = rawData.filter(d => d.status.includes('🔥')).sort((a,b) => b.pqr - a.pqr);
  const watch = rawData.filter(d => !d.status.includes('🔥') && d.pqr >= 80).sort((a,b) => b.pqr - a.pqr).slice(0, 6);
  
  const elAlerts = document.getElementById('trig-list');
  const elWatch = document.getElementById('watch-list');
  
  elAlerts.innerHTML = active.length ? active.map(d => createCard(d, true)).join('') : `<div class="col-span-full text-center py-10 text-slate-500 font-bold">今日無達到嚴格買進條件的股票。</div>`;
  elWatch.innerHTML = watch.length ? watch.map(d => createCard(d, false)).join('') : `<div class="col-span-full text-center py-10 text-slate-500 font-bold">目前無高分標的。</div>`;

  // Render Track Record
  const openTrades = Object.values(trackData.open).sort((a,b) => b.return_pct - a.return_pct);
  const closedTrades = trackData.closed;

  document.getElementById('open-list').innerHTML = openTrades.length ? openTrades.map(t => `
    <div class="bg-slate-900 border border-slate-800 p-4 rounded-2xl flex items-center justify-between">
      <div>
        <div class="text-xl font-black text-white">${{t.ticker}}</div>
        <div class="text-xs text-slate-500">進場: $${{t.entry_price}} (${{t.entry_date}})</div>
      </div>
      <div class="text-right">
        <div class="text-lg font-black ${{t.return_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}}">${{t.return_pct > 0 ? '+' : ''}}${{t.return_pct}}%</div>
        <div class="text-[10px] text-slate-500">現價: $${{t.curr_price}}</div>
      </div>
    </div>
  `).join('') : '<div class="text-slate-500">無持有部位</div>';

  document.getElementById('closed-list').innerHTML = closedTrades.length ? closedTrades.map(t => `
    <div class="bg-slate-900/50 border border-slate-800 p-4 rounded-xl flex justify-between items-center">
      <div>
        <span class="font-bold text-white">${{t.ticker}}</span>
        <span class="text-[10px] text-slate-500 ml-2">${{t.exit_date}}</span>
      </div>
      <span class="text-sm font-black ${{t.result === 'WIN' ? 'text-emerald-400' : 'text-red-400'}}">${{t.result}} (${{t.return_pct}}%)</span>
    </div>
  `).join('') : '<div class="text-slate-500">無平倉紀錄</div>';
}}

window.onload = render;
</script>
</body>
</html>"""

with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
    f.write(html)
print("\n🎉 建置完成！Dashboard 已更新。")
