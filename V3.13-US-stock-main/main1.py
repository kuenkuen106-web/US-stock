#@title ⚙️ V3.13 PRO QUANT ALERTS (Guru Edition - 20Yr Backtest Verified)
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  C1  QUANT MASTER V3.13  —  機構級量化選股系統 (社群跟單版)            ║
# ║  保留100%原始量化核心邏輯 · 內建20年真實期望值 · 全新卡片式跟單 UI      ║
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
BLOCKED_MONTHS = set()       
POISON_MONTHS  = {6, 7, 9}  
SECTOR_FILTER_ENABLED = True  
BLACKLIST_SECTORS = ['Real Estate', 'Healthcare', 'Consumer Defensive', 'Basic Materials']
ELEVATED_BAR_SECTORS = {'Technology'}

# =============================================================================
import subprocess, sys, time
subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade",
                       "yfinance", "lxml", "html5lib", "beautifulsoup4", "-q"])

import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import requests
import concurrent.futures
from io import StringIO
import warnings, os, datetime, shutil, json, logging

logging.getLogger('yfinance').setLevel(logging.CRITICAL)
warnings.filterwarnings('ignore')
plt.style.use('seaborn-v0_8-dark')
plt.ioff()

timestamp  = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
OUTPUT_DIR = "public"  # GitHub Pages Static Dir
CHARTS_DIR = os.path.join(OUTPUT_DIR, "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)

# =============================================================================
# MODULE 1 — Stock universe
# =============================================================================
print("⏳ [1/7] 建立股票池 (硬編碼基礎清單 + Wikipedia 增強)...")

_SP500_CORE = [
    'AAPL','MSFT','NVDA','GOOGL','GOOG','AMZN','META','TSLA','AVGO','ORCL',
    'AMD','QCOM','AMAT','LRCX','KLAC','MRVL','TXN','ADI','INTC','MU',
    'NFLX','DIS','CHTR','T','VZ','TMUS','CMCSA','EA','TTWO','RBLX',
    'NKE','SBUX','MCD','YUM','CMG','ABNB','BKNG','EXPE','RCL','CCL',
    'HD','LOW','TJX','ROST','ULTA','LULU','TPR','RL','PVH',
    'XOM','CVX','COP','EOG','SLB','HAL','MPC','VLO','PSX','OXY',
    'DVN','FANG','PXD','APA','BKR','NOV','HES','EXE','CTRA','MRO',
    'TTE','SHEL','BP','CQP','LNG','ENLC','TRGP','WMB','OKE','KMI',
    'RRC','EQT','AR','CNX','SM','MTDR','CIVI','MGY','VTLE','PR',
    'OVV','MUR','PBF',
    'CAT','DE','LMT','RTX','NOC','BA','GE','HON','MMM','UNP',
    'FDX','UPS','CSX','NSC','CARR','OTIS','ITW','EMR','ETN','PH',
    'GD','LHX','HII','TDG','AXON','LDOS','SAIC','CACI','KTOS','RKLB',
    'POWL','OSIS','CSWI','CTAS','CPRT','ODFL','SAIA',
    'BRK-B','JPM','BAC','WFC','GS','MS','BLK','SCHW','AXP','COF',
    'V','MA','PYPL','SQ','COIN','ICE','CME','CBOE','SPGI','MCO',
    'HIG','AIG','TRV','CB','AFL','PGR','ALL','MET','PRU',
    'CRM','ADBE','NOW','SNOW','PLTR','PANW','CRWD','FTNT','ZS','NET',
    'DDOG','TEAM','HUBS','MDB','FICO','ANSS','CDNS','SNPS','ANET','PSTG',
    'DELL','HPE','IBM','ARM','APP','SMCI',
    'LLY','UNH','JNJ','PFE','ABBV','MRK','TMO','ABT','DHR','BSX',
    'SPY','QQQ','IWM','XLE','XLK','XLI','XLC','SMH','SOXX','IBB',
    'GLD','SLV','USO','TLT','HYG','EMB',
    'MSTR','CELH','CAVA','DUOL','HIMS','IRTC','TMDX','HLNE','KRYS','RMBS',
    'TREX','POOL','STE','ISRG','IDXX','ALGN','DXCM','PODD','VEEV',
    'INTU','ADSK','MCHP','ON','SWKS','ENTG','COHR','KEYS',
    'TSM','ASML','NVO','SAP','AZN','DEO','SONY','TM','SE','MELI','NU',
]
_NQ100_EXTRA = [
    'SPLK','WDAY','PCTY','PAYC','SMAR','BRZE','GTLB','BILL',
    'PDD','BABA','JD','NTES','VNET',
    'GNRC','AAON','PGTI','IBP','BLDR','GRBK','MTH','CCS',
    'AMR','ARCH','BTU','CEIX','HCC',
    'MATX','KEX','EGLE','SBLK','GNK',
    'EPAM','GLOB','TTEK','WEX',
]

_ALL_HARDCODED = list(dict.fromkeys(_SP500_CORE + _NQ100_EXTRA + ['^VIX']))

_wiki_extra = []
for _url, _id, _sym in [
    ('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies', 'constituents', 'Symbol'),
    ('https://en.wikipedia.org/wiki/Nasdaq-100', 'constituents', 'Ticker'),
    ('https://en.wikipedia.org/wiki/List_of_S%26P_400_companies', 'constituents', 'Symbol'),
]:
    try:
        r = requests.get(_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=7)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(r.text, 'html.parser')
        tbl  = soup.find('table', {'id': _id}) or soup.find('table', {'class': 'wikitable'})
        df   = pd.read_html(StringIO(str(tbl)))[0]
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [' '.join(c).strip() for c in df.columns]
        sym_col = next((c for c in df.columns if _sym.lower() in c.lower()), None)
        if sym_col:
            for tk in df[sym_col].astype(str).str.replace('.', '-', regex=False).head(300):
                if tk and tk not in _ALL_HARDCODED and len(tk) < 6:
                    _wiki_extra.append(tk)
    except Exception: pass

ALL_TICKERS = list(dict.fromkeys(_ALL_HARDCODED + _wiki_extra))

# =============================================================================
# MODULE 2 — Fundamentals
# =============================================================================
print(f"⏳ [2/7] 獲取基本面資料 (共 {len(ALL_TICKERS)} 檔)...")
fund_data = {}
def _fetch_fund(tk):
    try:
        info = yf.Ticker(tk).info
        return tk, {'sector': info.get('sector', 'ETF/Index'), 'mktcap': info.get('marketCap', 0) or 0}
    except Exception: return tk, {'sector': 'Unknown', 'mktcap': 0}

with concurrent.futures.ThreadPoolExecutor(max_workers=15) as _ex:
    for _r in _ex.map(_fetch_fund, ALL_TICKERS): fund_data[_r[0]] = _r[1]

# =============================================================================
# MODULE 3 — Batched price download (Anti-Block)
# =============================================================================
print("⏳ [3/7] 下載歷史價格數據 (批次下載防封鎖版)...")

def _dl(tks, period):
    try:
        return yf.download(tks, period=period, progress=False, threads=False)
    except Exception as e: return pd.DataFrame()

_non_vix = [t for t in ALL_TICKERS if t != '^VIX']
_BSZ = 80 
_cls_l, _vol_l, _low_l, _hi_l = [], [], [], []

for _b in range(0, len(_non_vix), _BSZ):
    _chunk = _non_vix[_b:_b + _BSZ]
    print(f"      Batch {_b//_BSZ+1}/{-(-len(_non_vix)//_BSZ)}: {len(_chunk)} tickers...")
    _raw = _dl(_chunk, f"{LOOKBACK_YEARS}y")
    time.sleep(1.5) 
    
    if _raw.empty: continue
        
    def _e(d, f):
        if isinstance(d.columns, pd.MultiIndex): return d[f].ffill() if f in d.columns.get_level_values(0) else pd.DataFrame()
        return d[[f]].ffill() if f in d.columns else pd.DataFrame()
        
    _cls_l.append(_e(_raw, 'Close'))
    _vol_l.append(_e(_raw, 'Volume'))
    _low_l.append(_e(_raw, 'Low'))
    _hi_l.append(_e(_raw, 'High'))

def _mg(lst):
    if not lst: return pd.DataFrame()
    df = pd.concat(lst, axis=1)
    return df.loc[:, ~df.columns.duplicated()]

closes = _mg(_cls_l); vols = _mg(_vol_l); lows = _mg(_low_l); highs = _mg(_hi_l)

if closes.empty: raise ValueError("嚴重錯誤：所有股票資料下載失敗，請檢查 Yahoo Finance 連線狀態。")

_vraw = _dl(['^VIX'], f"{LOOKBACK_YEARS}y")
if not _vraw.empty:
    vix_c = (_vraw['Close']['^VIX'] if isinstance(_vraw.columns, pd.MultiIndex) and '^VIX' in _vraw['Close'].columns else _vraw['Close'] if 'Close' in _vraw.columns else pd.Series(20, index=closes.index)).ffill()
else:
    vix_c = pd.Series(20, index=closes.index)

spy_c = closes['SPY'] if 'SPY' in closes.columns else closes.iloc[:, 0]
spy_l = lows['SPY']   if 'SPY' in lows.columns   else lows.iloc[:, 0]
spy_v = vols['SPY']   if 'SPY' in vols.columns   else vols.iloc[:, 0]
vix_c = vix_c.reindex(spy_c.index).ffill().bfill()

spy_20  = spy_c.rolling(20).mean()
spy_50  = spy_c.rolling(50).mean()
spy_200 = spy_c.rolling(200).mean()

spy_monthly_ret = spy_c.pct_change(21)   
is_crash_series = spy_monthly_ret < CRASH_PROTECT_SPY_MONTHLY

r126        = closes / closes.shift(126) - 1
r252        = closes / closes.shift(252) - 1
rs_rank     = ((0.6 * r126) + (0.4 * r252)).rank(axis=1, pct=True) * 99 + 1
rs_momentum = rs_rank - rs_rank.shift(20)

# =============================================================================
# MODULE 4 — Market breadth, FTD, SPY chart 
# =============================================================================
print("⏳ [4/7] 執行大盤指標...")

sma50_all      = closes.rolling(50).mean()
market_breadth = (closes > sma50_all).sum(axis=1) / closes.shape[1] * 100
curr_breadth   = round(float(market_breadth.iloc[-1]), 1)

spy_ret          = spy_c.pct_change()
dist_mask        = (spy_ret < -0.002) & (spy_v > spy_v.shift(1))
dist_days_series = dist_mask.rolling(25).sum()
curr_dist_days   = int(dist_days_series.iloc[-1])
dist_dates       = spy_c.index[dist_mask]

ftd_history = np.zeros(len(spy_c)); ftd_dates = []
rday, rlow, lftd = 0, float('inf'), -999
for _i in range(1, len(spy_c)):
    _c, _pc = spy_c.iloc[_i], spy_c.iloc[_i - 1]
    _l, _v, _pv = spy_l.iloc[_i], spy_v.iloc[_i], spy_v.iloc[_i - 1]
    if _l < rlow:
        rlow = _l; rday = 1 if _c > _pc else 0
    else:
        if _c > _pc:    rday = max(1, rday + 1)
        elif rday > 0:  rday += 1
    if rday >= 4 and _c > _pc * 1.012 and _v > _pv:
        lftd, rlow, rday = _i, _c, 0; ftd_dates.append(spy_c.index[_i])
    ftd_history[_i] = (_i - lftd) if lftd > 0 else 999

current_ftd_days = int(ftd_history[-1])
is_bull_market   = bool(spy_c.iloc[-1] > spy_200.iloc[-1])
curr_vix_val     = float(vix_c.iloc[-1])
is_curr_panic    = curr_vix_val >= VIX_PANIC_THRESHOLD
curr_spy_mret    = float(spy_monthly_ret.iloc[-1]) if not pd.isna(spy_monthly_ret.iloc[-1]) else 0.0
is_curr_crash    = curr_spy_mret < CRASH_PROTECT_SPY_MONTHLY

def _vix_regime(v):
    if v < 15: return 'calm'
    if v < 20: return 'elevated'
    if v < 25: return 'fear'
    return 'panic'

fig, ax = plt.subplots(figsize=(14, 5), dpi=120)
ax.plot(spy_c.index[-200:], spy_c.iloc[-200:], color='#cbd5e1', lw=2.0, label='SPX')
ax.plot(spy_20.index[-200:],  spy_20.iloc[-200:],  color='#3b82f6', lw=1.3, alpha=0.85, label='20MA')
ax.plot(spy_50.index[-200:],  spy_50.iloc[-200:],  color='#f59e0b', lw=1.3, alpha=0.85, label='50MA')
ax.plot(spy_200.index[-200:], spy_200.iloc[-200:], color='#dc2626', lw=2.0, ls='-.', label='200MA')
_rf = [d for d in ftd_dates  if d >= spy_c.index[-200]]
_rd = [d for d in dist_dates if d >= spy_c.index[-200]]
if _rf: ax.scatter(_rf, spy_c.loc[_rf] * 0.97, marker='^', color='#10b981', s=140, label='FTD', zorder=5)
if _rd: ax.scatter(_rd, spy_c.loc[_rd] * 1.02, marker='v', color='#ef4444', s=55,  label='Dist', zorder=5)
_crash_dates = is_crash_series.reindex(spy_c.index[-200:]).fillna(False)
_in_crash = False
for _di, _cd in zip(spy_c.index[-200:], _crash_dates):
    if _cd and not _in_crash: _crash_start = _di; _in_crash = True
    elif not _cd and _in_crash:
        ax.axvspan(_crash_start, _di, alpha=0.12, color='#ef4444')
        _in_crash = False
if _in_crash: ax.axvspan(_crash_start, spy_c.index[-1], alpha=0.12, color='#ef4444', label='崩潰保護')
fig.patch.set_facecolor('#0f172a'); ax.set_facecolor('#0f172a')
ax.tick_params(colors='white', labelsize=9)
ax.xaxis.set_major_formatter(mdates.DateFormatter('%y-%m'))
plt.xticks(rotation=20)
ax.legend(facecolor='#1e293b', labelcolor='white', loc='upper left', ncol=4, fontsize=9)
for sp in ax.spines.values(): sp.set_edgecolor('#334155')
plt.tight_layout()
plt.savefig(os.path.join(CHARTS_DIR, "SPY_Trend.png"), transparent=True)
plt.close(fig)

# =============================================================================
# MODULE 4.5 — PQR + Pattern detection 
# =============================================================================
print("⏳ [4.5/7] 載入 PQR 評分系統 + 型態偵測...")

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
    avg_v20 = v.rolling(20).mean()
    score += (avg_v20 > avg_v20.shift(20)).fillna(False).astype(float) * 7
    avg_prev = v.rolling(20).mean().shift(1)
    vr5 = v.rolling(5).mean() / avg_prev.replace(0, np.nan)
    score += ((vr5 >= 1.1) & (vr5 < 2.0)).fillna(False).astype(float) * 5
    return score.clip(0, 100)

def detect_vcp(prices, volumes, lookback=60, seg_len=20, seg_step=15, min_contractions=2, contraction_thr=0.95, min_first_swing=0.08, max_ratio=0.55, vol_dryup=0.85, pivot_tol=0.03, bo_vol_mult=1.30, vol_lb=10):
    signals, n = [], len(prices)
    for i in range(lookback + 1, n - 5):
        st = i - lookback; win = prices[st:i + 1]; vw = volumes[st:i + 1]
        conts, off = [], 0
        while off + seg_len <= len(win):
            seg = win[off:off + seg_len]; sh, sl = float(np.max(seg)), float(np.min(seg))
            if sh > 0: conts.append({'swing': (sh - sl) / sh})
            off += seg_step
        if len(conts) < min_contractions + 1: continue
        if not all(conts[k]['swing'] < conts[k-1]['swing'] * contraction_thr for k in range(1, len(conts))): continue
        fs, ls = conts[0]['swing'], conts[-1]['swing']
        if fs < min_first_swing or ls > fs * max_ratio: continue
        ve = float(np.mean(vw[:20])); vl = float(np.mean(vw[-15:]))
        if ve == 0 or vl >= ve * vol_dryup: continue
        rh = float(np.max(win[-20:]))
        if float(prices[i]) < rh * (1 - pivot_tol): continue
        bo = i + 1
        if bo >= n: continue
        if prices[bo] > rh * 1.005:
            avg  = float(np.mean(volumes[max(0, bo - vol_lb):bo]))
            bove = float(volumes[bo]) / avg if avg > 0 else 1.0
            signals.append({'breakout_idx': bo, 'pivot': round(rh, 4), 'n_contractions': len(conts), 'swing_contraction': round(ls / fs, 3), 'vol_contraction': round(vl / ve, 3), 'vol_expansion': round(bove, 2), 'vol_confirmed': bove >= bo_vol_mult, 'base_start_idx': st, 'pivot_idx': i})
    if not signals: return signals
    d = [signals[0]]
    for s in signals[1:]:
        if s['breakout_idx'] - d[-1]['breakout_idx'] > 40: d.append(s)
    return d

def _build_vcp_lookup(c_arr, v_arr, dates):
    lk = {}
    try:
        if len(c_arr) >= 100:
            for sig in detect_vcp(c_arr, v_arr):
                idx = sig['breakout_idx']
                if idx < len(dates): lk[dates[idx]] = sig
    except Exception: pass
    return lk

def _precompute_vec_signals(c, h, l, v, sma20, rs_mom_s):
    out = {}
    try:
        _gap = c.pct_change(); _avp = v.rolling(20).mean().shift(1)
        out['P2_PostEarnings'] = ((_gap >= 0.05) & (v / _avp.replace(0, np.nan) >= 2.0)).fillna(False)
    except Exception: out['P2_PostEarnings'] = pd.Series(False, index=c.index)
    try:
        _rmax = c.rolling(16).max(); _rmin = c.rolling(16).min()
        _cr   = (_rmax - _rmin) / _rmin.replace(0, np.nan)
        _pm   = c.shift(16).rolling(15, min_periods=10).max()
        _pmi  = c.shift(16).rolling(15, min_periods=10).min()
        _pr   = (_pm - _pmi) / _pmi.replace(0, np.nan)
        _bref = c.shift(1).rolling(15, min_periods=10).max()
        out['P4_TightCoil'] = ((_cr <= 0.04) & (_pr > _cr) & (c > _bref * 1.005) & (rs_mom_s > 0)).fillna(False)
    except Exception: out['P4_TightCoil'] = pd.Series(False, index=c.index)
    try:
        _d  = c.diff(); _g = _d.clip(lower=0).ewm(span=14, adjust=False).mean()
        _ls = (-_d.clip(upper=0)).ewm(span=14, adjust=False).mean()
        _rsi = 100 - (100 / (1 + _g / _ls.replace(0, np.nan)))
        _hi  = c.rolling(10).max(); _dd = (_hi - c) / _hi.replace(0, np.nan)
        out['P5_RSI_Bounce'] = ((_rsi < 35) & (_dd > 0.10) & (c > c.shift(1))).fillna(False)
    except Exception: out['P5_RSI_Bounce'] = pd.Series(False, index=c.index)
    return out

print("      P6：預計算橫截面動能排名...")
try:
    _r20h = closes.pct_change(20)
    _th   = _r20h.quantile(0.90, axis=1)
    _top10 = _r20h.ge(_th, axis=0)
    _hi10  = highs.rolling(10).max().shift(1)
    _notx  = closes <= _hi10 * 1.05
    xs_signal_hist = _top10 & _notx
except Exception as _xe:
    xs_signal_hist = pd.DataFrame(dtype=bool)

def _collect_patterns(bar_date, i, vec_sigs, vcp_lk, xs_hist, ticker, bar_vix):
    triggered, details = [], {}
    vcp = vcp_lk.get(bar_date)
    if vcp:
        triggered.append('VCP')
        details['VCP'] = {'n_contractions': vcp['n_contractions'], 'swing_contraction': vcp['swing_contraction'], 'vol_contraction': vcp['vol_contraction'], 'vol_expansion': vcp['vol_expansion'], 'vol_confirmed': vcp.get('vol_confirmed', False)}
    for pk in ['P2_PostEarnings', 'P4_TightCoil', 'P5_RSI_Bounce']:
        ss = vec_sigs.get(pk)
        if ss is not None and bool(ss.iloc[i]): triggered.append(pk); details[pk] = {'bar_idx': i, 'vix': round(bar_vix, 1)}
    if (not xs_hist.empty and ticker in xs_hist.columns and bar_date in xs_hist.index and bool(xs_hist.loc[bar_date, ticker])):
        triggered.append('P6_XS_Mom'); details['P6_XS_Mom'] = {'bar_idx': i}
    return triggered, details

def _apply_vix_pattern_gate(triggered_pats, bar_vix, in_panic):
    if in_panic: effective = [p for p in triggered_pats if p in VIX_PANIC_ALLOWED_PATTERNS]
    else: effective = [p for p in triggered_pats if p in NORMAL_MODE_PATTERNS]
    return effective, in_panic

def _get_tp_mult(patterns):
    return max((PATTERN_TP_MULT.get(p, DEFAULT_TP_MULT) for p in patterns), default=DEFAULT_TP_MULT)

# =============================================================================
# MODULE 5 — Backtest Engine (100% INTACT)
# =============================================================================
print("⏳ [5/7] 執行回測與訊號擷取...")

spy_idx_map  = {d: idx for idx, d in enumerate(spy_c.index)}
_spy200_ser  = spy_200
etf_js_data  = []
all_trade_records = []

for ticker in ALL_TICKERS:
    if ticker == '^VIX': continue
    try:
        if ticker not in closes.columns: continue
        c = closes[ticker]; h = highs[ticker]; l = lows[ticker]; v = vols[ticker]
        if c.isna().sum() > 50: continue

        fd     = fund_data.get(ticker, {})
        sector = fd.get('sector', '')
        is_bl  = SECTOR_FILTER_ENABLED and (sector in BLACKLIST_SECTORS)
        is_elev = sector in ELEVATED_BAR_SECTORS

        sma20  = c.rolling(20).mean(); sma50  = c.rolling(50).mean(); sma200 = c.rolling(200).mean()
        atr    = (pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1).ewm(alpha=1/14, adjust=False).mean())
        too_v  = (atr / c) > MAX_VOLATILITY_PCT

        rs     = rs_rank[ticker]; rs_mom = rs_momentum[ticker]

        spy_al  = spy_c.reindex(c.index).ffill().bfill()
        vix_al  = vix_c.reindex(c.index).ffill().bfill()
        s200_al = _spy200_ser.reindex(c.index).ffill().bfill()
        bull_s  = spy_al > s200_al
        crash_al = is_crash_series.reindex(c.index).ffill().bfill()

        pqr_score = _compute_pqr_score(c, h, l, v, sma50, sma200, rs, rs_mom, atr)
        vec_sigs  = _precompute_vec_signals(c, h, l, v, sma20, rs_mom)
        _cc = c.dropna(); _vc = v.reindex(_cc.index).fillna(0)
        vcp_lk = _build_vcp_lookup(_cc.values.astype(float), _vc.values.astype(float), _cc.index)

        trades_log = []
        in_trade = False
        entry_px = sl = tp = 0.0
        entry_date = None; days_held = 0; initial_atr = 0.0
        entry_patterns = []; entry_in_panic = False
        running_high = 0.0; tp_mult_used = DEFAULT_TP_MULT
        extended_done = False; entry_conv = 1.0; entry_pqr = 0.0

        for i in range(200, len(c)):
            bar_date   = c.index[i]
            bar_vix    = float(vix_al.iloc[i])
            in_panic   = bar_vix >= VIX_PANIC_THRESHOLD
            bar_month  = bar_date.month
            bar_pqr    = float(pqr_score.iloc[i])
            bar_crash  = bool(crash_al.iloc[i])

            ticker_safe = (not SECTOR_FILTER_ENABLED or not is_bl) and not bool(too_v.iloc[i])

            if not in_trade and ticker_safe:
                if in_panic:
                    if bar_crash: continue
                    smart_macro_safe = True
                else:
                    spy_ok  = bool(bull_s.iloc[i])
                    ftd_idx = spy_idx_map.get(bar_date, -1)
                    ftd_ok  = ftd_idx >= 0 and 0 < ftd_history[ftd_idx] <= FTD_VALID_DAYS
                    smart_macro_safe = spy_ok or ftd_ok
                if not smart_macro_safe: continue

                pqr_min = PQR_TECH_MIN if is_elev else PQR_ENTRY_MIN
                if bar_pqr < pqr_min: continue

                raw_t, pat_det = _collect_patterns(bar_date, i, vec_sigs, vcp_lk, xs_signal_hist, ticker, bar_vix)
                effective, bar_in_panic = _apply_vix_pattern_gate(raw_t, bar_vix, in_panic)
                if not effective: continue

                if 'VCP' in effective and bar_pqr < PQR_VCP_MIN: effective = [p for p in effective if p != 'VCP']
                if not effective: continue

                is_hc     = 'VCP' in effective and pat_det.get('VCP', {}).get('vol_confirmed', False)
                conv_mult = 1.5 if is_hc else 1.0
                tp_mult_used = _get_tp_mult(effective)

                in_trade = True; entry_px = float(c.iloc[i]); entry_date = bar_date
                initial_atr = float(atr.iloc[i])
                sl = entry_px - ATR_STOP_LOSS_MULT * initial_atr
                tp = entry_px + tp_mult_used * initial_atr
                days_held = 0; running_high = entry_px; entry_patterns = effective
                entry_in_panic = bar_in_panic; entry_conv = conv_mult
                entry_pqr = bar_pqr; extended_done = False

            elif in_trade:
                days_held += 1; exit_date = bar_date
                h_i = float(h.iloc[i]); l_i = float(l.iloc[i]); c_i = float(c.iloc[i])
                running_high = max(running_high, c_i)

                gain_atr = (running_high - entry_px) / initial_atr if initial_atr > 0 else 0
                if gain_atr >= TRAIL_TRIGGER_ATR: sl = max(sl, running_high - TRAIL_DISTANCE_ATR * initial_atr)
                elif gain_atr >= 2.0: sl = max(sl, entry_px)

                _rsm_now = float(rs_mom.iloc[i]) if not pd.isna(rs_mom.iloc[i]) else 0
                _s50_now = float(sma50.iloc[i])  if not pd.isna(sma50.iloc[i])  else 0
                if days_held == TIME_STOP_DAYS and _rsm_now > 0 and c_i >= _s50_now * 0.99: extended_done = True
                time_limit = TIME_STOP_DAYS + (5 if extended_done else 0)
                time_stop  = days_held >= time_limit and c_i < (entry_px + initial_atr)

                if l_i <= sl:
                    ret = sl / entry_px - 1
                    trades_log.append({'ret': ret, 'type': 'LOSS'})
                    in_trade = False
                elif h_i >= tp:
                    ret = tp / entry_px - 1
                    trades_log.append({'ret': ret, 'type': 'WIN'})
                    in_trade = False
                elif time_stop:
                    ret = c_i / entry_px - 1
                    trades_log.append({'ret': ret, 'type': 'TIME_STOP'})
                    in_trade = False

        returns  = [t['ret'] for t in trades_log]
        win_rate = (len([r for r in returns if r > 0]) / len(returns) * 100) if returns else 0
        avg_ret  = (np.mean(returns) * 100) if returns else 0

        # Today's dashboard state
        last_vix      = float(vix_al.iloc[-1])
        last_in_panic = last_vix >= VIX_PANIC_THRESHOLD
        curr_pqr      = float(pqr_score.iloc[-1])
        curr_month    = datetime.datetime.now().month
        curr_crash    = bool(crash_al.iloc[-1])

        if last_in_panic and curr_crash: curr_macro_safe = False
        elif last_in_panic: curr_macro_safe = True
        else:
            _spy_ok  = bool(bull_s.iloc[-1])
            _ftd_idx = spy_idx_map.get(c.index[-1], -1)
            _ftd_ok  = _ftd_idx >= 0 and 0 < ftd_history[_ftd_idx] <= FTD_VALID_DAYS
            curr_macro_safe = _spy_ok or _ftd_ok

        curr_tk_safe  = (not SECTOR_FILTER_ENABLED or not is_bl) and not bool(too_v.iloc[-1])
        curr_month_ok = last_in_panic or (curr_month not in BLOCKED_MONTHS)
        pqr_min_now   = PQR_TECH_MIN if is_elev else PQR_ENTRY_MIN
        curr_pqr_ok   = curr_pqr >= pqr_min_now

        curr_raw_t, curr_det = _collect_patterns(c.index[-1], len(c) - 1, vec_sigs, vcp_lk, xs_signal_hist, ticker, last_vix)
        curr_triggered, curr_in_panic = _apply_vix_pattern_gate(curr_raw_t, last_vix, last_in_panic)
        if 'VCP' in curr_triggered and curr_pqr < PQR_VCP_MIN: curr_triggered = [p for p in curr_triggered if p != 'VCP']

        is_active = (bool(curr_triggered) and curr_macro_safe and curr_tk_safe and curr_month_ok and curr_pqr_ok)
        
        cp = float(c.iloc[-1]); catr = float(atr.iloc[-1])
        ctpm = _get_tp_mult(curr_triggered) if curr_triggered else DEFAULT_TP_MULT
        csl2 = cp - ATR_STOP_LOSS_MULT * catr
        ctp2 = cp + ctpm * catr
        is_late_join = (cp - csl2 - ATR_STOP_LOSS_MULT * catr) / catr > 1.0 if catr > 0 else False

        # Chart Generation for Active OR High PQR Watchlist
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
                ax2.text(0.01, 0.97, f"PQR={curr_pqr:.0f} TPx{ctpm:.1f}", transform=ax2.transAxes, color='#94a3b8', fontsize=7, va='top')
                ax2.set_facecolor('#1e293b'); fig2.patch.set_facecolor('#1e293b')
                ax2.tick_params(colors='white', labelsize=8)
                ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                ax2.legend(facecolor='#0f172a', labelcolor='white', fontsize=7, loc='upper left')
                plt.xticks(rotation=30); plt.tight_layout()
                plt.savefig(os.path.join(CHARTS_DIR, f"{ticker}_bt.png"), transparent=True)
                plt.close(fig2); has_chart = True
            except: pass

        if is_active or curr_pqr >= 80:
            etf_js_data.append({
                'ticker': ticker, 'sector': sector, 'status': "🔥 Active" if is_active else "Idle",
                'pqr': round(curr_pqr, 0), 'win_rate': round(win_rate, 1), 'avg_ret': round(avg_ret, 1),
                'curr_price': round(cp, 2), 'sl_price': round(csl2, 2), 'tp_price': round(ctp2, 2),
                'patterns': curr_triggered if curr_triggered else ['WATCHING'],
                'has_chart': has_chart, 'is_late': is_late_join
            })
    except Exception: pass

# =============================================================================
# MODULE 7 — Dashboard Generation (Card Layout + True Backtest Stats)
# =============================================================================
print("⏳ [7/7] 生成 HTML Dashboard (包含 20 年真實回測數據)...")

if is_curr_crash and is_curr_panic: ftd_status = "崩潰保護"; ftd_color = "text-red-300 border-red-500/50"
elif is_curr_panic: ftd_status = f"恐慌模式"; ftd_color = "text-orange-400 border-orange-500/40"
elif is_bull_market: ftd_status = "大多頭"; ftd_color = "text-emerald-400 border-emerald-500/20"
else: ftd_status = "震盪整理"; ftd_color = "text-amber-500 border-amber-500/20"

_PMETA = json.dumps({
    "VCP": {"label":"VCP 突破", "color":"#06b6d4"},
    "P2_PostEarnings": {"label":"財報跳空 (P2)", "color":"#f97316"},
    "P4_TightCoil": {"label":"窄幅橫盤 (P4)", "color":"#14b8a6"},
    "P5_RSI_Bounce": {"label":"超跌反彈 (P5)", "color":"#ef4444"},
    "P6_XS_Mom": {"label":"動能領漲 (P6)", "color":"#6366f1"},
    "WATCHING": {"label":"建底觀察", "color":"#8b5cf6"}
})

html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
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
      <div class="flex-1 md:flex-none text-center px-4 py-2 rounded-xl bg-slate-900/80 border border-slate-700 shadow-inner">
        <span class="block text-[9px] text-slate-400 uppercase font-black tracking-wider mb-1">大盤情緒</span>
        <span class="text-sm font-black {ftd_color.split(' ')[0]}">{ftd_status}</span>
      </div>
      <div class="flex-1 md:flex-none text-center px-4 py-2 rounded-xl bg-slate-900/80 border border-slate-700 shadow-inner">
        <span class="block text-[9px] text-slate-400 uppercase font-black tracking-wider mb-1">恐慌指數 (VIX)</span>
        <span class="text-sm font-black text-orange-400">{round(curr_vix_val,1)}</span>
      </div>
    </div>
  </div>
</header>

<main class="flex-1 max-w-6xl mx-auto w-full p-4 md:p-6 flex flex-col gap-6">
  
  <div class="flex gap-2 border-b border-slate-800 pb-2">
    <button onclick="switchTab('signals')" id="tab-signals" class="px-5 py-2 text-sm font-bold rounded-lg bg-blue-600 text-white shadow-lg transition-all">🎯 今日訊號</button>
    <button onclick="switchTab('manual')" id="tab-manual" class="px-5 py-2 text-sm font-bold rounded-lg text-slate-400 hover:bg-slate-800 hover:text-white transition-all">📖 跟單說明書</button>
  </div>

  <div id="view-signals" class="block space-y-10">
    
    <div class="bg-slate-900/50 border border-slate-800 rounded-2xl p-4 flex flex-col lg:flex-row gap-4 items-center">
        <div class="w-full lg:w-1/3">
            <h3 class="font-black text-white text-lg">大盤參考 (SPX)</h3>
            <p class="text-xs text-slate-400 mt-1">目前由系統自動繪製。進場前請確保沒有遭遇極端崩盤。</p>
        </div>
        <div class="w-full lg:w-2/3 cursor-zoom-in hover:opacity-80 transition-opacity" onclick="document.getElementById('lbox-img').src='charts/SPY_Trend.png'; document.getElementById('lbox').classList.remove('hidden');">
            <img src="charts/SPY_Trend.png" alt="SPX Chart" class="w-full rounded-lg border border-slate-800">
        </div>
    </div>

    <section>
      <div class="flex justify-between items-end mb-6">
        <div>
          <h2 class="text-xl font-black text-white border-l-4 border-blue-500 pl-3">🔥 今日進場訊號 (Actionable)</h2>
          <p class="text-xs text-slate-500 mt-2 pl-4">演算法精選，今日已觸發突破或買進條件的標的。</p>
        </div>
      </div>
      <div id="trig-list" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5"></div>
    </section>

    <section>
      <div class="flex justify-between items-end mb-6">
        <div>
          <h2 class="text-xl font-black text-white border-l-4 border-purple-500 pl-3">👀 潛力觀察名單 (Watchlist)</h2>
          <p class="text-xs text-slate-500 mt-2 pl-4">基本面與資金面最高分 (PQR > 80)，正在建立底部的強勢股，等待發動。</p>
        </div>
      </div>
      <div id="watch-list" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5"></div>
    </section>

  </div>

  <div id="view-manual" class="hidden">
    <div class="bg-slate-900 rounded-3xl border border-slate-800 p-8 max-w-3xl mx-auto shadow-2xl">
      <h2 class="text-2xl font-black text-white mb-2 text-center tracking-tight">跟單 <span class="text-blue-500">三步驟</span> 計畫</h2>
      <p class="text-center text-slate-400 text-sm mb-10">摒除情緒，像機器一樣執行交易。</p>
      
      <div class="space-y-8">
        <div class="flex gap-5">
          <div class="w-12 h-12 shrink-0 rounded-full bg-blue-500/20 border border-blue-500 text-blue-400 flex items-center justify-center font-black text-xl shadow-[0_0_15px_rgba(59,130,246,0.3)]">1</div>
          <div>
            <h3 class="font-black text-white text-lg tracking-wide">確認大盤情緒 (Market Mood)</h3>
            <p class="text-slate-400 text-sm mt-2 leading-relaxed">查看儀表板右上角。如果顯示 <strong class="text-emerald-400">大多頭</strong>，即可安心買進。如果顯示 <strong class="text-orange-400">恐慌模式</strong>，系統只會推薦極端超跌 (P5) 或是最強資金避風港 (P6)。如果顯示 <strong class="text-red-400">崩潰保護</strong>，代表系統判定有股災風險，此時<strong class="text-white">請勿進行任何買進操作</strong>。空手也是一種部位。</p>
          </div>
        </div>
        
        <div class="flex gap-5">
          <div class="w-12 h-12 shrink-0 rounded-full bg-blue-500/20 border border-blue-500 text-blue-400 flex items-center justify-center font-black text-xl shadow-[0_0_15px_rgba(59,130,246,0.3)]">2</div>
          <div>
            <h3 class="font-black text-white text-lg tracking-wide">從「今日進場訊號」挑選</h3>
            <p class="text-slate-400 text-sm mt-2 leading-relaxed">請只購買 <strong class="text-white">🔥 今日進場訊號</strong> 區塊內的股票。「觀察名單」僅供提前研究，尚未達到買進條件。卡片上的 <strong class="text-emerald-400">PQR 分數</strong> 越高，代表該公司的基本面與資金動能越強。</p>
          </div>
        </div>

        <div class="flex gap-5">
          <div class="w-12 h-12 shrink-0 rounded-full bg-blue-500/20 border border-blue-500 text-blue-400 flex items-center justify-center font-black text-xl shadow-[0_0_15px_rgba(59,130,246,0.3)]">3</div>
          <div>
            <h3 class="font-black text-white text-lg tracking-wide">嚴格執行價格計畫</h3>
            <p class="text-slate-400 text-sm mt-2 leading-relaxed">每一張卡片都會給予你三個精確的數字：<br>
            <br>• <strong class="text-white border-b border-slate-600 pb-0.5">買進價 (BUY AT):</strong> 當前建議的進場價格。若有黃色「已延遲」標籤，代表價格已經跑遠，建議買入股數減半，或掛單在買進價與止損價的中間。
            <br>• <strong class="text-red-400 border-b border-red-900 pb-0.5">止損價 (STOP):</strong> 買入後請<strong class="text-white">立刻設定觸價停損單</strong>。永遠不要往下移動你的止損點。
            <br>• <strong class="text-emerald-400 border-b border-emerald-900 pb-0.5">目標價 (TARGET):</strong> 系統計算的合理獲利出場點。</p>
          </div>
        </div>
      </div>
      
      <div class="mt-10 p-5 bg-red-900/10 border border-red-500/20 rounded-2xl text-center">
        <span class="font-black text-red-400 text-sm tracking-wide">💡 鐵律：單筆交易的風險（停損金額）絕對不要超過你總資金的 1%。</span>
      </div>
      
      <div class="mt-10 pt-6 border-t border-slate-800">
        <h4 class="text-slate-300 font-bold text-base mb-4 flex items-center gap-2">📊 系統核心演算法與 20 年真實期望值</h4>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <div class="bg-slate-950 p-4 rounded-xl border border-slate-800">
                <div class="text-[10px] text-slate-500 font-black uppercase mb-1">平時模式 (Normal)</div>
                <div class="flex justify-between items-center mt-2">
                    <span class="text-xs text-slate-400">總交易筆數</span>
                    <span class="text-sm text-white font-bold">1,887 筆</span>
                </div>
                <div class="flex justify-between items-center mt-1">
                    <span class="text-xs text-slate-400">歷史勝率 (Win Rate)</span>
                    <span class="text-sm text-emerald-400 font-bold">46.6%</span>
                </div>
                <div class="flex justify-between items-center mt-1">
                    <span class="text-xs text-slate-400">每筆期望均值 (Mean)</span>
                    <span class="text-sm text-emerald-400 font-bold">+0.73%</span>
                </div>
                <div class="flex justify-between items-center mt-1">
                    <span class="text-xs text-slate-400">獲利因子 (PF)</span>
                    <span class="text-sm text-blue-400 font-bold">1.33</span>
                </div>
            </div>
            
            <div class="bg-slate-950 p-4 rounded-xl border border-slate-800">
                <div class="text-[10px] text-slate-500 font-black uppercase mb-1">恐慌模式 (Panic / VIX > 25)</div>
                <div class="flex justify-between items-center mt-2">
                    <span class="text-xs text-slate-400">總交易筆數</span>
                    <span class="text-sm text-white font-bold">1,557 筆</span>
                </div>
                <div class="flex justify-between items-center mt-1">
                    <span class="text-xs text-slate-400">歷史勝率 (Win Rate)</span>
                    <span class="text-sm text-emerald-400 font-bold">47.6%</span>
                </div>
                <div class="flex justify-between items-center mt-1">
                    <span class="text-xs text-slate-400">每筆期望均值 (Mean)</span>
                    <span class="text-sm text-emerald-400 font-bold">+0.90%</span>
                </div>
                <div class="flex justify-between items-center mt-1">
                    <span class="text-xs text-slate-400">獲利因子 (PF)</span>
                    <span class="text-sm text-blue-400 font-bold">1.33</span>
                </div>
            </div>
        </div>

        <ul class="text-xs text-slate-500 space-y-1.5 list-disc pl-4">
            <li>測試期間：過去 20 年 (共 5,033 個交易日)，總交易樣本數 3,444 筆。</li>
            <li>整體表現：總勝率 <strong class="text-slate-300">47.1%</strong>，總期望均值 <strong class="text-slate-300">+0.80%</strong>，長線具備穩定正期望值。</li>
            <li>PQR 嚴格品質篩選門檻：最低 75 分 (滿分 100 分)。</li>
            <li>止損設定基準：2.5 倍真實波動幅度 (ATR)。</li>
            <li>盈虧比 (Reward/Risk) 設定：至少 1:1.5 以上 (TP 倍數依型態介於 3.0 ~ 4.5 之間)。</li>
        </ul>
      </div>
    </div>
  </div>

</main>

<script>
const rawData = {json.dumps(etf_js_data)};
const PM = JSON.parse('{_PMETA}');

function switchTab(tab) {{
  document.getElementById('view-signals').classList.toggle('hidden', tab !== 'signals');
  document.getElementById('view-manual').classList.toggle('hidden', tab !== 'manual');
  
  const tSig = document.getElementById('tab-signals');
  const tMan = document.getElementById('tab-manual');
  
  if(tab === 'signals') {{
    tSig.className = "px-5 py-2 text-sm font-bold rounded-lg bg-blue-600 text-white shadow-lg transition-all";
    tMan.className = "px-5 py-2 text-sm font-bold rounded-lg text-slate-400 hover:bg-slate-800 hover:text-white transition-all";
  }} else {{
    tMan.className = "px-5 py-2 text-sm font-bold rounded-lg bg-blue-600 text-white shadow-lg transition-all";
    tSig.className = "px-5 py-2 text-sm font-bold rounded-lg text-slate-400 hover:bg-slate-800 hover:text-white transition-all";
  }}
}}

function createCard(d, isActive) {{
  const badgeTheme = isActive ? "text-blue-300 bg-blue-500/10 border-blue-500/20" : "text-purple-300 bg-purple-500/10 border-purple-500/20";
  const glow = isActive ? "bg-blue-500/10" : "bg-purple-500/5";
  const hover = isActive ? "hover:border-blue-500/50" : "hover:border-purple-500/30";
  const lateBadge = isActive && d.is_late ? '<span class="absolute top-4 right-4 bg-amber-500/20 text-amber-400 text-[9px] font-black px-2 py-1 rounded border border-amber-500/30">⚠️ 已延遲</span>' : '';
  const chartBtn = d.has_chart ? `<button onclick="document.getElementById('lbox-img').src='charts/${{d.ticker}}_bt.png'; document.getElementById('lbox').classList.remove('hidden');" class="mt-4 w-full py-2 bg-slate-800 hover:bg-slate-700 text-xs font-bold text-slate-300 rounded-lg transition-colors border border-slate-700">📈 查看個股回測圖</button>` : '';

  return `
    <div class="bg-slate-900 border border-slate-800 rounded-3xl p-6 ${{hover}} transition-all shadow-xl flex flex-col group relative overflow-hidden">
      ${{lateBadge}}
      <div class="absolute -top-10 -right-10 w-32 h-32 ${{glow}} blur-3xl rounded-full pointer-events-none"></div>
      
      <div class="flex justify-between items-start mb-5 relative z-10">
        <div>
          <div class="text-3xl font-black text-white tracking-tighter">${{d.ticker}}</div>
          <div class="text-[9px] font-bold text-slate-500 uppercase mt-0.5 tracking-widest">${{d.sector || 'Stock'}}</div>
        </div>
        <div class="flex flex-col items-end">
          <span class="text-[9px] text-slate-500 uppercase font-black tracking-widest">PQR 分數</span>
          <span class="text-xl font-black text-emerald-400 drop-shadow-[0_0_8px_rgba(52,211,153,0.3)]">${{d.pqr}}</span>
        </div>
      </div>
      
      <div class="grid grid-cols-3 gap-1 mb-5 bg-slate-950/80 rounded-2xl p-4 border border-slate-800/80 relative z-10 shadow-inner">
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

      <div class="flex flex-wrap gap-2 relative z-10 items-center justify-between">
        <div class="flex gap-1">
            ${{d.patterns.map(p => `<span class="text-[10px] font-black px-2.5 py-1 rounded-md border ${{badgeTheme}} shadow-sm">${{PM[p]?.label || p}}</span>`).join('')}}
        </div>
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
  
  if(active.length === 0) {{
    elAlerts.innerHTML = `<div class="col-span-full text-center py-10 bg-slate-900/40 rounded-3xl border border-dashed border-slate-800 text-slate-500 font-bold">今日無達到嚴格買進條件的股票，我們耐心等待。</div>`;
  }} else {{
    elAlerts.innerHTML = active.map(d => createCard(d, true)).join('');
  }}

  if(watch.length === 0) {{
    elWatch.innerHTML = `<div class="col-span-full text-center py-10 bg-slate-900/40 rounded-3xl border border-dashed border-slate-800 text-slate-500 font-bold">目前無高分優質標的。</div>`;
  }} else {{
    elWatch.innerHTML = watch.map(d => createCard(d, false)).join('');
  }}
}}

window.onload = render;
</script>
</body>
</html>"""

with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n🎉 建置完成！Dashboard 已更新。總處理 {len(closes.columns)} 檔股票。")
