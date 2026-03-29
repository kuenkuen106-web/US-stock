#@title ⚙️ V3.13 機構級量化系統 { display-mode: "form" }
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  C1  QUANT MASTER V3.13  —  機構級量化選股系統                         ║
# ║  穩定性驗證參數 · Top-10預設 · 毒月提醒 · 觸發面板回測圖放大           ║
# ║──────────────────────────────────────────────────────────────────────────║
# ║  VERSION HISTORY                                                         ║
# ║  V3.8  PQR評分+精簡型態 (VCP/P2/P4/P5/P6恐慌)   Win~48%  PF~1.36     ║
# ║  V3.10 P6開放正常模式→失敗 (P6淹沒84.6%交易)     Win~42%  PF~1.14     ║
# ║  V3.11 P6恢復恐慌·ATR=2.5·TS=20·Top-10驗證       Win~52%  PF~1.66     ║
# ║  V3.13 訊號首次日期追蹤·SPX大圖·TV預設MA50/MA20·佈局重整           ║
# ║──────────────────────────────────────────────────────────────────────────║
# ║  KEY METRICS  Win: 52-55%  |  PF: 1.66  |  All 4 windows PF ≥ 1.48    ║
# ╚══════════════════════════════════════════════════════════════════════════╝
# ── Colab Form Parameters ────────────────────────────────────────────────────
LOOKBACK_YEARS        = 3     #@param {type:"slider", min:1, max:20, step:1}
FTD_VALID_DAYS        = 20    #@param {type:"integer"}
MAX_VOLATILITY_PCT    = 0.06  #@param {type:"number"}
MAX_ACCOUNT_RISK_PCT  = 0.01  #@param {type:"number"}
VIX_PANIC_THRESHOLD   = 25    #@param {type:"slider", min:15, max:40, step:5}

# ── Top-10 Preset Selector (stability-validated across 4 x 5yr windows) ──────
# Preset PQRv VTP  TS  20yr-PF   Notes
#   1     75  4.0  20  1.66   ← DEFAULT: best full-period PF
#   2     75  4.5  20  1.66      Higher TP
#   3     75  3.5  20  1.66      Faster exits
#   4     75  4.0  15  1.61      Faster turnover
#   5     75  4.5  15  1.61
#   6     75  3.5  15  1.61
#   7     82  4.0  15  1.59      Tighter VCP gate
#   8     82  3.5  15  1.59
#   9     82  4.5  15  1.59
#  10     78  4.0  15  1.57
TOP10_PRESET = 1  #@param {type:"slider", min:1, max:10, step:1}
_T10 = {1:(75,4.0,20),2:(75,4.5,20),3:(75,3.5,20),4:(75,4.0,15),5:(75,4.5,15),
        6:(75,3.5,15),7:(82,4.0,15),8:(82,3.5,15),9:(82,4.5,15),10:(78,4.0,15)}
PQR_VCP_MIN, _VCP_TP, TIME_STOP_DAYS = _T10[TOP10_PRESET]
ATR_STOP_LOSS_MULT = 2.5   # Stability: +0.142 PF vs 2.0
PQR_ENTRY_MIN  = 75   # Biggest lever: +0.252 PF (optimizer + stability confirmed)
PQR_TECH_MIN   = 78
PATTERN_TP_MULT = {'VCP':_VCP_TP,'P4_TightCoil':4.5,'P2_PostEarnings':3.5,'P5_RSI_Bounce':3.0,'P6_XS_Mom':4.0}
DEFAULT_TP_MULT = 4.0
TRAIL_TRIGGER_ATR = 3.0
TRAIL_DISTANCE_ATR = 1.5
# V3.11: P6 RESTORED to panic_only (stability: panic_only PF=1.605 vs normal+panic 1.420)
VIX_PANIC_ALLOWED_PATTERNS = frozenset({'P2_PostEarnings','P5_RSI_Bounce','P6_XS_Mom'})
NORMAL_MODE_PATTERNS       = frozenset({'VCP','P2_PostEarnings','P4_TightCoil'})
CRASH_PROTECT_SPY_MONTHLY  = -0.12
# V3.11: NO hard month blocking — poison month is dashboard advisory only
# Stability: blocking Jun/Jul/Sep → +0.105 PF over 20yr; user chose advisory mode
BLOCKED_MONTHS = set()       # No hard block
POISON_MONTHS  = {6, 7, 9}  # Advisory: Jun PF=0.97, Jul PF=1.05, Sep PF=0.89
# ── Sector settings ───────────────────────────────────────────────────────────
SECTOR_FILTER_ENABLED = True  #@param {type:"boolean"}
BLACKLIST_SECTORS = [
    'Real Estate',            # 36.9% win
    'Healthcare',             # 37.1% win
    'Consumer Defensive',     # 38.6% win
    'Basic Materials',        # 39.0% win
]
ELEVATED_BAR_SECTORS = {'Technology'}

# =============================================================================
import subprocess, sys
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
OUTPUT_DIR = "public"  # Use a static folder for GitHub Pages
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
    except Exception:
        pass

ALL_TICKERS = list(dict.fromkeys(_ALL_HARDCODED + _wiki_extra))
print(f"      ✅ Total universe: {len(ALL_TICKERS)} tickers (hardcoded: {len(_ALL_HARDCODED)-1}, wiki: {len(_wiki_extra)})")

# =============================================================================
# MODULE 2 — Fundamentals
# =============================================================================
print(f"⏳ [2/7] 獲取基本面資料 (共 {len(ALL_TICKERS)} 檔)...")
fund_data = {}

def _fetch_fund(tk):
    try:
        info = yf.Ticker(tk).info
        return tk, {'sector': info.get('sector', 'ETF/Index'), 'mktcap': info.get('marketCap', 0) or 0}
    except Exception:
        return tk, {'sector': 'Unknown', 'mktcap': 0}

with concurrent.futures.ThreadPoolExecutor(max_workers=15) as _ex:
    for _r in _ex.map(_fetch_fund, ALL_TICKERS):
        fund_data[_r[0]] = _r[1]
# =============================================================================
# MODULE 3 — Batched price download
# =============================================================================
print("⏳ [3/7] 下載歷史價格數據 (批次下載防封鎖版)...")

import time

def _dl(tks, period):
    try:
        # 取消 session 參數，讓 yfinance 自己用最新的 curl_cffi 底層處理
        # 保持 threads=False 避免並發過多被封鎖
        return yf.download(tks, period=period, progress=False, threads=False)
    except Exception as e:
        print(f"      下載錯誤: {e}")
        return pd.DataFrame()

_non_vix = [t for t in ALL_TICKERS if t != '^VIX']
_BSZ = 80  # 縮小批次大小，每次只下載 80 檔
_cls_l, _vol_l, _low_l, _hi_l = [], [], [], []

for _b in range(0, len(_non_vix), _BSZ):
    _chunk = _non_vix[_b:_b + _BSZ]
    print(f"      Batch {_b//_BSZ+1}/{-(-len(_non_vix)//_BSZ)}: {len(_chunk)} tickers...")
    _raw = _dl(_chunk, f"{LOOKBACK_YEARS}y")
    
    time.sleep(1.5)  # 每個批次之間強迫休息 1.5 秒
    
    if _raw.empty:
        continue
        
    def _e(d, f):
        if isinstance(d.columns, pd.MultiIndex):
            return d[f].ffill() if f in d.columns.get_level_values(0) else pd.DataFrame()
        return d[[f]].ffill() if f in d.columns else pd.DataFrame()
        
    _cls_l.append(_e(_raw, 'Close'))
    _vol_l.append(_e(_raw, 'Volume'))
    _low_l.append(_e(_raw, 'Low'))
    _hi_l.append(_e(_raw, 'High'))

def _mg(lst):
    if not lst: return pd.DataFrame()
    df = pd.concat(lst, axis=1)
    return df.loc[:, ~df.columns.duplicated()]

closes = _mg(_cls_l); vols = _mg(_vol_l)
lows   = _mg(_low_l); highs = _mg(_hi_l)

# 防呆機制：如果全部下載失敗，提早結束避免後續崩潰
if closes.empty:
    raise ValueError("嚴重錯誤：所有股票資料下載失敗，請檢查 Yahoo Finance 連線狀態。")

# 下載 VIX
_vraw = _dl(['^VIX'], f"{LOOKBACK_YEARS}y")
if not _vraw.empty:
    vix_c = (_vraw['Close']['^VIX'] if isinstance(_vraw.columns, pd.MultiIndex)
              and '^VIX' in _vraw['Close'].columns
              else _vraw['Close'] if 'Close' in _vraw.columns
              else pd.Series(20, index=closes.index)).ffill()
else:
    vix_c = pd.Series(20, index=closes.index)

spy_c = closes['SPY'] if 'SPY' in closes.columns else closes.iloc[:, 0]
spy_l = lows['SPY']   if 'SPY' in lows.columns   else lows.iloc[:, 0]
spy_v = vols['SPY']   if 'SPY' in vols.columns   else vols.iloc[:, 0]
vix_c = vix_c.reindex(spy_c.index).ffill().bfill()

spy_20  = spy_c.rolling(20).mean()
spy_50  = spy_c.rolling(50).mean()
spy_200 = spy_c.rolling(200).mean()

# ── Crash protection: 21-day SPY return ───────────────────────────────────────
spy_monthly_ret = spy_c.pct_change(21)   
is_crash_series = spy_monthly_ret < CRASH_PROTECT_SPY_MONTHLY

r126        = closes / closes.shift(126) - 1
r252        = closes / closes.shift(252) - 1
rs_rank     = ((0.6 * r126) + (0.4 * r252)).rank(axis=1, pct=True) * 99 + 1
rs_momentum = rs_rank - rs_rank.shift(20)

print(f"      ✅ {closes.shape[1]} tickers × {len(closes)} days loaded")
# =============================================================================
# MODULE 4 — Market breadth, FTD, SPY chart (ENLARGED)
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

# ── SPY anatomy chart — ENLARGED (14×5 instead of 8×3) ───────────────────────
fig, ax = plt.subplots(figsize=(14, 5), dpi=120)
ax.plot(spy_c.index[-200:], spy_c.iloc[-200:], color='#cbd5e1', lw=2.0, label='SPX')
ax.plot(spy_20.index[-200:],  spy_20.iloc[-200:],  color='#3b82f6', lw=1.3, alpha=0.85, label='20MA')
ax.plot(spy_50.index[-200:],  spy_50.iloc[-200:],  color='#f59e0b', lw=1.3, alpha=0.85, label='50MA')
ax.plot(spy_200.index[-200:], spy_200.iloc[-200:], color='#dc2626', lw=2.0, ls='-.', label='200MA')
_rf = [d for d in ftd_dates  if d >= spy_c.index[-200]]
_rd = [d for d in dist_dates if d >= spy_c.index[-200]]
if _rf: ax.scatter(_rf, spy_c.loc[_rf] * 0.97, marker='^', color='#10b981', s=140, label='FTD', zorder=5)
if _rd: ax.scatter(_rd, spy_c.loc[_rd] * 1.02, marker='v', color='#ef4444', s=55,  label='Dist', zorder=5)
# Shade crash periods
_crash_dates = is_crash_series.reindex(spy_c.index[-200:]).fillna(False)
_in_crash = False
for _di, _cd in zip(spy_c.index[-200:], _crash_dates):
    if _cd and not _in_crash:
        _crash_start = _di; _in_crash = True
    elif not _cd and _in_crash:
        ax.axvspan(_crash_start, _di, alpha=0.12, color='#ef4444')
        _in_crash = False
if _in_crash:
    ax.axvspan(_crash_start, spy_c.index[-1], alpha=0.12, color='#ef4444', label='崩潰保護')
fig.patch.set_facecolor('#0f172a'); ax.set_facecolor('#0f172a')
ax.tick_params(colors='white', labelsize=9)
ax.xaxis.set_major_formatter(mdates.DateFormatter('%y-%m'))
plt.xticks(rotation=20)
ax.legend(facecolor='#1e293b', labelcolor='white', loc='upper left', ncol=4, fontsize=9)
for sp in ax.spines.values(): sp.set_edgecolor('#334155')
plt.tight_layout()
plt.savefig(os.path.join(CHARTS_DIR, "SPY_Trend.png"), transparent=True)
plt.close(fig)

breadth_color = "text-emerald-400" if curr_breadth > 40 else "text-red-400"
dist_color    = "text-red-400" if curr_dist_days >= 5 else "text-emerald-400"
if is_curr_crash and is_curr_panic:
    ftd_status = "💥 崩潰保護 (SPY月跌>12%+VIX恐慌)"
    ftd_color  = "text-red-300 bg-red-900/30 border-red-500/50"
elif is_curr_panic:
    ftd_status = f"🚨 VIX 恐慌 ≥{VIX_PANIC_THRESHOLD}"
    ftd_color  = "text-orange-400 bg-orange-500/20 border-orange-500/40"
elif is_bull_market:
    ftd_status = "🟢 牛市 (SPX>200MA)"
    ftd_color  = "text-emerald-500 bg-emerald-500/10 border-emerald-500/20"
elif current_ftd_days <= FTD_VALID_DAYS:
    ftd_status = f"✅ FTD 確認 ({current_ftd_days}d)"
    ftd_color  = "text-blue-400 bg-blue-500/10 border-blue-500/20"
else:
    ftd_status = "❌ 熊市 (等待 FTD)"
    ftd_color  = "text-red-500 bg-red-500/10 border-red-500/20"

# =============================================================================
# MODULE 4.5 — PQR + Pattern detection (P7 REMOVED, P6 opens to Normal)
# =============================================================================
print("⏳ [4.5/7] 載入 PQR 評分系統 + 型態偵測 (移除P7 / P6開放正常模式)...")

def _compute_pqr_score(c, h, l, v, sma50, sma200, rs, rs_mom, atr):
    score = pd.Series(0.0, index=c.index)
    # P — Price Structure [0-40]
    score += (sma50 > sma200).fillna(False).astype(float) * 10
    score += (sma50 > sma50.shift(10)).fillna(False).astype(float) * 12
    score += (c > sma50).fillna(False).astype(float) * 8
    score += ((l <= sma50 * 1.015) & (c >= sma50 * 0.97)).fillna(False).astype(float) * 10
    # Q — Quality / RS [0-40]
    score += (rs > 70).fillna(False).astype(float) * 10
    score += (rs > 85).fillna(False).astype(float) * 8
    score += (rs_mom > 0).fillna(False).astype(float) * 12
    score += (rs_mom > 5).fillna(False).astype(float) * 10
    # R — Risk / Volume [0-20]
    score += ((atr / c.replace(0, np.nan)) < 0.03).fillna(False).astype(float) * 8
    avg_v20 = v.rolling(20).mean()
    score += (avg_v20 > avg_v20.shift(20)).fillna(False).astype(float) * 7
    avg_prev = v.rolling(20).mean().shift(1)
    vr5 = v.rolling(5).mean() / avg_prev.replace(0, np.nan)
    score += ((vr5 >= 1.1) & (vr5 < 2.0)).fillna(False).astype(float) * 5
    return score.clip(0, 100)

def detect_vcp(prices, volumes,
               lookback=60, seg_len=20, seg_step=15, min_contractions=2,
               contraction_thr=0.95, min_first_swing=0.08, max_ratio=0.55,
               vol_dryup=0.85, pivot_tol=0.03, bo_vol_mult=1.30, vol_lb=10):
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
            signals.append({'breakout_idx': bo, 'pivot': round(rh, 4),
                'n_contractions': len(conts), 'swing_contraction': round(ls / fs, 3),
                'vol_contraction': round(vl / ve, 3), 'vol_expansion': round(bove, 2),
                'vol_confirmed': bove >= bo_vol_mult, 'base_start_idx': st, 'pivot_idx': i})
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
    """V3.10: P7 REMOVED. P2, P4, P5 only (P6 is cross-sectional, computed separately)."""
    out = {}
    # P2: Post-earnings gap ≥5% + vol ≥2×
    try:
        _gap = c.pct_change(); _avp = v.rolling(20).mean().shift(1)
        out['P2_PostEarnings'] = ((_gap >= 0.05) & (v / _avp.replace(0, np.nan) >= 2.0)).fillna(False)
    except Exception: out['P2_PostEarnings'] = pd.Series(False, index=c.index)
    # P4: Tight 3-week coil + RS momentum accelerating
    try:
        _rmax = c.rolling(16).max(); _rmin = c.rolling(16).min()
        _cr   = (_rmax - _rmin) / _rmin.replace(0, np.nan)
        _pm   = c.shift(16).rolling(15, min_periods=10).max()
        _pmi  = c.shift(16).rolling(15, min_periods=10).min()
        _pr   = (_pm - _pmi) / _pmi.replace(0, np.nan)
        _bref = c.shift(1).rolling(15, min_periods=10).max()
        out['P4_TightCoil'] = ((_cr <= 0.04) & (_pr > _cr) & (c > _bref * 1.005) & (rs_mom_s > 0)).fillna(False)
    except Exception: out['P4_TightCoil'] = pd.Series(False, index=c.index)
    # P5: RSI oversold bounce (gate applied in loop — panic only)
    try:
        _d  = c.diff(); _g = _d.clip(lower=0).ewm(span=14, adjust=False).mean()
        _ls = (-_d.clip(upper=0)).ewm(span=14, adjust=False).mean()
        _rsi = 100 - (100 / (1 + _g / _ls.replace(0, np.nan)))
        _hi  = c.rolling(10).max(); _dd = (_hi - c) / _hi.replace(0, np.nan)
        out['P5_RSI_Bounce'] = ((_rsi < 35) & (_dd > 0.10) & (c > c.shift(1))).fillna(False)
    except Exception: out['P5_RSI_Bounce'] = pd.Series(False, index=c.index)
    return out

# P6 cross-sectional — pre-computed ONCE for entire universe
print("      P6：預計算橫截面動能排名 (正常+恐慌模式均開放)...")
try:
    _r20h = closes.pct_change(20)
    _th   = _r20h.quantile(0.90, axis=1)
    _top10 = _r20h.ge(_th, axis=0)
    _hi10  = highs.rolling(10).max().shift(1)
    _notx  = closes <= _hi10 * 1.05
    xs_signal_hist = _top10 & _notx
    print(f"      P6 完成: {xs_signal_hist.shape[0]}日 × {xs_signal_hist.shape[1]}股")
except Exception as _xe:
    xs_signal_hist = pd.DataFrame(dtype=bool)
    print(f"      P6 失敗: {_xe}")

def _collect_patterns(bar_date, i, vec_sigs, vcp_lk, xs_hist, ticker, bar_vix):
    triggered, details = [], {}
    vcp = vcp_lk.get(bar_date)
    if vcp:
        triggered.append('VCP')
        details['VCP'] = {'n_contractions': vcp['n_contractions'],
                          'swing_contraction': vcp['swing_contraction'],
                          'vol_contraction': vcp['vol_contraction'],
                          'vol_expansion': vcp['vol_expansion'],
                          'vol_confirmed': vcp.get('vol_confirmed', False)}
    for pk in ['P2_PostEarnings', 'P4_TightCoil', 'P5_RSI_Bounce']:
        ss = vec_sigs.get(pk)
        if ss is not None and bool(ss.iloc[i]):
            triggered.append(pk); details[pk] = {'bar_idx': i, 'vix': round(bar_vix, 1)}
    if (not xs_hist.empty and ticker in xs_hist.columns
            and bar_date in xs_hist.index and bool(xs_hist.loc[bar_date, ticker])):
        triggered.append('P6_XS_Mom'); details['P6_XS_Mom'] = {'bar_idx': i}
    return triggered, details

def _apply_vix_pattern_gate(triggered_pats, bar_vix, in_panic):
    """
    V3.10 mode rules:
      Normal: VCP, P2, P4, P6  (P6 now ALLOWED in normal — 20yr PF=1.43)
      Panic:  P2, P5, P6       (same as before, plus P6)
    """
    if in_panic:
        effective = [p for p in triggered_pats if p in VIX_PANIC_ALLOWED_PATTERNS]
    else:
        effective = [p for p in triggered_pats if p in NORMAL_MODE_PATTERNS]
    return effective, in_panic

def _get_tp_mult(patterns):
    return max((PATTERN_TP_MULT.get(p, DEFAULT_TP_MULT) for p in patterns), default=DEFAULT_TP_MULT)

# =============================================================================
# MODULE 5 — V3.10 Backtest Engine
# =============================================================================
print("⏳ [5/7] V3.11 回測引擎：20年月份過濾 + P6正常模式 + 崩潰保護...")

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

        sma20  = c.rolling(20).mean()
        sma50  = c.rolling(50).mean()
        sma200 = c.rolling(200).mean()
        atr    = (pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1)
                  .max(axis=1).ewm(alpha=1/14, adjust=False).mean())
        too_v  = (atr / c) > MAX_VOLATILITY_PCT

        rs     = rs_rank[ticker]
        rs_mom = rs_momentum[ticker]

        spy_al  = spy_c.reindex(c.index).ffill().bfill()
        vix_al  = vix_c.reindex(c.index).ffill().bfill()
        s200_al = _spy200_ser.reindex(c.index).ffill().bfill()
        bull_s  = spy_al > s200_al
        crash_al = is_crash_series.reindex(c.index).ffill().bfill()

        pqr_score = _compute_pqr_score(c, h, l, v, sma50, sma200, rs, rs_mom, atr)
        vec_sigs  = _precompute_vec_signals(c, h, l, v, sma20, rs_mom)
        _cc = c.dropna(); _vc = v.reindex(_cc.index).fillna(0)
        vcp_lk = _build_vcp_lookup(_cc.values.astype(float), _vc.values.astype(float), _cc.index)

        trades_log    = []
        in_trade      = False
        entry_px = sl = tp = 0.0
        entry_date    = None; days_held = 0; initial_atr = 0.0
        entry_patterns = []; entry_in_panic = False
        running_high  = 0.0; tp_mult_used = DEFAULT_TP_MULT
        extended_done = False; entry_conv = 1.0; entry_pqr = 0.0

        for i in range(200, len(c)):
            bar_date   = c.index[i]
            bar_vix    = float(vix_al.iloc[i])
            in_panic   = bar_vix >= VIX_PANIC_THRESHOLD
            bar_month  = bar_date.month
            bar_pqr    = float(pqr_score.iloc[i])
            bar_crash  = bool(crash_al.iloc[i])

            ticker_safe = (not SECTOR_FILTER_ENABLED or not is_bl) and not bool(too_v.iloc[i])

            # ═══════════════════════════════════════════════════════════════
            # ENTRY BLOCK
            # ═══════════════════════════════════════════════════════════════
            if not in_trade and ticker_safe:

                # V3.11: no hard month blocking (advisory only)

                # ── Macro gate ────────────────────────────────────────────
                if in_panic:
                    # V3.10 CRASH PROTECTION: if SPY down >12% this month,
                    # suspend Panic entries (systemic crisis ≠ ordinary panic)
                    if bar_crash:
                        continue
                    smart_macro_safe = True
                else:
                    spy_ok  = bool(bull_s.iloc[i])
                    ftd_idx = spy_idx_map.get(bar_date, -1)
                    ftd_ok  = ftd_idx >= 0 and 0 < ftd_history[ftd_idx] <= FTD_VALID_DAYS
                    smart_macro_safe = spy_ok or ftd_ok
                if not smart_macro_safe: continue

                # ── PQR pre-filter (raised to 75) ─────────────────────────
                pqr_min = PQR_TECH_MIN if is_elev else PQR_ENTRY_MIN
                if bar_pqr < pqr_min: continue

                # ── Collect and gate patterns ─────────────────────────────
                raw_t, pat_det = _collect_patterns(bar_date, i, vec_sigs, vcp_lk,
                                                   xs_signal_hist, ticker, bar_vix)
                effective, bar_in_panic = _apply_vix_pattern_gate(raw_t, bar_vix, in_panic)
                if not effective: continue

                # VCP requires premium PQR
                if 'VCP' in effective and bar_pqr < PQR_VCP_MIN:
                    effective = [p for p in effective if p != 'VCP']
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

            # ═══════════════════════════════════════════════════════════════
            # EXIT BLOCK
            # ═══════════════════════════════════════════════════════════════
            elif in_trade:
                days_held += 1; exit_date = bar_date
                h_i = float(h.iloc[i]); l_i = float(l.iloc[i]); c_i = float(c.iloc[i])
                running_high = max(running_high, c_i)

                gain_atr = (running_high - entry_px) / initial_atr if initial_atr > 0 else 0
                if gain_atr >= TRAIL_TRIGGER_ATR:
                    sl = max(sl, running_high - TRAIL_DISTANCE_ATR * initial_atr)
                elif gain_atr >= 2.0:
                    sl = max(sl, entry_px)

                _rsm_now = float(rs_mom.iloc[i]) if not pd.isna(rs_mom.iloc[i]) else 0
                _s50_now = float(sma50.iloc[i])  if not pd.isna(sma50.iloc[i])  else 0
                if days_held == TIME_STOP_DAYS and _rsm_now > 0 and c_i >= _s50_now * 0.99:
                    extended_done = True
                time_limit = TIME_STOP_DAYS + (5 if extended_done else 0)
                time_stop  = days_held >= time_limit and c_i < (entry_px + initial_atr)

                if l_i <= sl:
                    ret = sl / entry_px - 1
                    trades_log.append({'entry': entry_date, 'exit': exit_date, 'ret': ret,
                        'type': 'LOSS', 'px': sl, 'reason': 'Stop Loss/BE',
                        'patterns': entry_patterns, 'in_panic': entry_in_panic,
                        'conv': entry_conv, 'tp_mult': tp_mult_used, 'pqr': entry_pqr})
                    in_trade = False
                elif h_i >= tp:
                    ret = tp / entry_px - 1
                    trades_log.append({'entry': entry_date, 'exit': exit_date, 'ret': ret,
                        'type': 'WIN', 'px': tp, 'reason': 'Take Profit',
                        'patterns': entry_patterns, 'in_panic': entry_in_panic,
                        'conv': entry_conv, 'tp_mult': tp_mult_used, 'pqr': entry_pqr})
                    in_trade = False
                elif time_stop:
                    ret = c_i / entry_px - 1
                    trades_log.append({'entry': entry_date, 'exit': exit_date, 'ret': ret,
                        'type': 'TIME_STOP', 'px': c_i, 'reason': 'Time Stop',
                        'patterns': entry_patterns, 'in_panic': entry_in_panic,
                        'conv': entry_conv, 'tp_mult': tp_mult_used, 'pqr': entry_pqr})
                    in_trade = False

                if not in_trade:
                    ed  = entry_date
                    vix_at  = float(vix_c.loc[ed])         if ed in vix_c.index         else float('nan')
                    spy_at  = float(spy_c.loc[ed])          if ed in spy_c.index          else float('nan')
                    s200_at = float(_spy200_ser.loc[ed])    if ed in _spy200_ser.index    else float('nan')
                    brd_at  = float(market_breadth.loc[ed]) if ed in market_breadth.index else float('nan')
                    rs_at   = float(rs.loc[ed])             if ed in rs.index             else float('nan')
                    sm50_at = float(sma50.loc[ed])          if ed in sma50.index          else float('nan')
                    lt = trades_log[-1]
                    all_trade_records.append({
                        'Ticker':           ticker, 'Sector': sector,
                        'Entry_Date':       ed.strftime('%Y-%m-%d'),
                        'Exit_Date':        exit_date.strftime('%Y-%m-%d'),
                        'Hold_Days':        days_held, 'Reason': lt['reason'],
                        'Entry_Price':      round(entry_px, 2), 'Exit_Price': round(lt['px'], 2),
                        'Return_%':         round(ret * 100, 2),
                        'Outcome':          'WIN' if ret > 0 else 'LOSS',
                        'Signal_Pattern':   '|'.join(lt['patterns']),
                        'Num_Patterns':     len(lt['patterns']),
                        'Panic_Mode_Entry': lt['in_panic'],
                        'PQR_Score_Entry':  lt['pqr'],
                        'Conviction_Mult':  round(lt['conv'], 2),
                        'TP_Mult_Used':     lt['tp_mult'],
                        'VCP_Trigger':      'VCP'             in lt['patterns'],
                        'P2_Trigger':       'P2_PostEarnings' in lt['patterns'],
                        'P4_Trigger':       'P4_TightCoil'    in lt['patterns'],
                        'P5_Trigger':       'P5_RSI_Bounce'   in lt['patterns'],
                        'P6_Trigger':       'P6_XS_Mom'       in lt['patterns'],
                        'VIX_At_Entry':     round(vix_at, 1) if not np.isnan(vix_at) else '',
                        'VIX_Regime':       _vix_regime(vix_at) if not np.isnan(vix_at) else '',
                        'SPY_Above_200MA':  ('Yes' if not np.isnan(spy_at) and not np.isnan(s200_at)
                                             and spy_at > s200_at else 'No'),
                        'Market_Breadth_%': round(brd_at, 1) if not np.isnan(brd_at) else '',
                        'Breadth_Status':   ('Strong(>60)' if brd_at > 60
                                             else 'Weak(<40)' if brd_at < 40
                                             else 'Neutral') if not np.isnan(brd_at) else '',
                        'RS_Score_Entry':   round(rs_at, 0)  if not np.isnan(rs_at) else '',
                        'Entry_Dist_SMA50_%': (round((entry_px / sm50_at - 1) * 100, 2)
                                               if not np.isnan(sm50_at) and sm50_at > 0 else ''),
                        'Entry_Month': ed.month, 'Sector_Filter_ON': SECTOR_FILTER_ENABLED,
                    })

        returns  = [t['ret'] for t in trades_log]
        win_rate = (len([r for r in returns if r > 0]) / len(returns) * 100) if returns else 0
        avg_ret  = (np.mean(returns) * 100) if returns else 0

        # ── Today's dashboard state ───────────────────────────────────────────
        last_vix      = float(vix_al.iloc[-1])
        last_in_panic = last_vix >= VIX_PANIC_THRESHOLD
        curr_pqr      = float(pqr_score.iloc[-1])
        curr_month    = datetime.datetime.now().month
        curr_crash    = bool(crash_al.iloc[-1])

        if last_in_panic and curr_crash:
            curr_macro_safe = False   # crash protection blocks panic entries
        elif last_in_panic:
            curr_macro_safe = True
        else:
            _spy_ok  = bool(bull_s.iloc[-1])
            _ftd_idx = spy_idx_map.get(c.index[-1], -1)
            _ftd_ok  = _ftd_idx >= 0 and 0 < ftd_history[_ftd_idx] <= FTD_VALID_DAYS
            curr_macro_safe = _spy_ok or _ftd_ok

        curr_tk_safe  = (not SECTOR_FILTER_ENABLED or not is_bl) and not bool(too_v.iloc[-1])
        curr_month_ok = last_in_panic or (curr_month not in BLOCKED_MONTHS)
        pqr_min_now   = PQR_TECH_MIN if is_elev else PQR_ENTRY_MIN
        curr_pqr_ok   = curr_pqr >= pqr_min_now

        curr_raw_t, curr_det = _collect_patterns(c.index[-1], len(c) - 1,
                                                  vec_sigs, vcp_lk, xs_signal_hist,
                                                  ticker, last_vix)
        curr_triggered, curr_in_panic = _apply_vix_pattern_gate(curr_raw_t, last_vix, last_in_panic)
        if 'VCP' in curr_triggered and curr_pqr < PQR_VCP_MIN:
            curr_triggered = [p for p in curr_triggered if p != 'VCP']

        is_active = (bool(curr_triggered) and curr_macro_safe
                     and curr_tk_safe and curr_month_ok and curr_pqr_ok)

        if SECTOR_FILTER_ENABLED and is_bl:
            st = "🚫 板塊過濾"
        elif bool(too_v.iloc[-1]):
            st = "🚫 波動過高"
        elif curr_crash and last_in_panic:
            st = "💥 崩潰保護"
        elif not curr_month_ok and not last_in_panic:
            st = f"📅 月份封鎖"
        elif is_active:
            st = "🔥 Active (恐慌)" if curr_in_panic else "🔥 Active"
        elif bool(curr_triggered) and curr_macro_safe and curr_tk_safe and not curr_pqr_ok:
            st = f"📊 PQR {curr_pqr:.0f}"
        elif bool(curr_triggered) and not curr_macro_safe:
            st = "⚠️ 宏觀未就緒"
        elif curr_pqr >= PQR_ENTRY_MIN:
            st = "👀 觀察 (PQR)"
        else:
            st = "Idle"

        cp     = float(c.iloc[-1]); catr = float(atr.iloc[-1])
        ctpm   = _get_tp_mult(curr_triggered) if curr_triggered else DEFAULT_TP_MULT
        csl2   = cp - ATR_STOP_LOSS_MULT * catr
        ctp2   = cp + ctpm * catr
        trail_px = cp + TRAIL_TRIGGER_ATR * catr     # trailing stop activation level
        rps    = max(cp - csl2, 0.001)
        is_hc_n = 'VCP' in curr_triggered and curr_det.get('VCP', {}).get('vol_confirmed', False)
        cconv  = 1.5 if is_hc_n else 1.0
        ssize  = min((MAX_ACCOUNT_RISK_PCT / (rps / cp)) * 100 * cconv, 20.0)

        # Moved distance from ideal entry (1 ATR = "late")
        dist_from_ideal = (cp - csl2 - ATR_STOP_LOSS_MULT * catr) / catr if catr > 0 else 0
        is_late_join    = dist_from_ideal > 1.0  # price moved >1 ATR from ideal entry

        # ── Streak detection: how many CONSECUTIVE days has each pattern been True? ──
        # Scan backward from today through the boolean arrays already in memory.
        # No log file needed — derives the answer directly from this run's data.
        _streak = 0
        if curr_triggered:
            # Build a combined "any pattern True" series for streak counting
            _any_true = pd.Series(False, index=c.index)
            for _p in curr_triggered:
                if _p == 'VCP':
                    # VCP is a dict of {date: signal} — mark those dates True
                    _vcp_s = pd.Series(False, index=c.index)
                    for _vd in vcp_lk:
                        if _vd in _vcp_s.index: _vcp_s[_vd] = True
                    _any_true = _any_true | _vcp_s
                elif _p == 'P6_XS_Mom':
                    if ticker in xs_signal_hist.columns:
                        _any_true = _any_true | xs_signal_hist[ticker].reindex(c.index).fillna(False)
                elif _p in vec_sigs:
                    _any_true = _any_true | vec_sigs[_p]
            # Count consecutive True from the end
            _vals = _any_true.values
            for _i in range(len(_vals) - 1, -1, -1):
                if _vals[_i]: _streak += 1
                else: break
        _first_seen = (c.index[-1] - pd.Timedelta(days=_streak - 1)).strftime('%Y-%m-%d') if _streak > 0 else c.index[-1].strftime('%Y-%m-%d')
        _days_active = max(0, _streak - 1)  # 0 = today is first day

        ps = 0
        if curr_triggered and curr_macro_safe:
            if curr_in_panic:
                ps = 3
            else:
                ps = 3 if any(p in curr_triggered for p in ['VCP', 'P4_TightCoil']) and curr_pqr >= 82 else 2
        elif curr_triggered:
            ps = 1

        # Chart (active tickers only)
        has_chart = False
        if is_active:
            try:
                _pd2 = pd.DataFrame({'Close': c, 'SMA50': sma50, 'SMA20': sma20}).last('252D')
                _PC  = {'VCP': '#06b6d4', 'P2_PostEarnings': '#f97316',
                        'P4_TightCoil': '#14b8a6', 'P5_RSI_Bounce': '#ef4444',
                        'P6_XS_Mom': '#6366f1'}
                fig2, ax2 = plt.subplots(figsize=(8, 4), dpi=100)
                ax2.plot(_pd2.index, _pd2.Close, color='#cbd5e1', lw=1.5)
                ax2.plot(_pd2.index, _pd2.SMA50,  color='#f59e0b', lw=1.8)
                ax2.plot(_pd2.index, _pd2.SMA20,  color='#3b82f6', lw=1.0, ls='--', alpha=0.6)
                for t in [t for t in trades_log if t['entry'] >= _pd2.index[0]]:
                    _ep = t['entry']; _xp = t['exit']
                    if _ep in _pd2.index:
                        ax2.scatter(_ep, _pd2.loc[_ep, 'Close'] * 0.95, marker='^',
                            color='#ff6b35' if t.get('in_panic') else '#3b82f6', s=120, zorder=5)
                    if _xp in _pd2.index:
                        if   t['type'] == 'WIN':  ax2.scatter(_xp, t['px'] * 1.05, marker='v', color='#10b981', s=120, zorder=5)
                        elif t['type'] == 'LOSS': ax2.scatter(_xp, t['px'] * 0.95, marker='X', color='#ef4444', s=100, zorder=5)
                        else:                     ax2.scatter(_xp, t['px'] * 1.05, marker='s', color='#f59e0b', s=80,  zorder=5)
                # Mark current entry/stop/trail
                ax2.axhline(cp,     color='#22c55e',  lw=1.2, ls='--', alpha=0.9, label=f'Entry ${cp:.2f}')
                ax2.axhline(csl2,   color='#ef4444',  lw=1.2, ls='--', alpha=0.9, label=f'Stop ${csl2:.2f}')
                ax2.axhline(trail_px,color='#3b82f6', lw=0.8, ls=':',  alpha=0.7, label=f'Trail@ ${trail_px:.2f}')
                ax2.text(0.01, 0.97, f"PQR={curr_pqr:.0f} TP×{ctpm:.1f} Conv×{cconv:.1f}",
                         transform=ax2.transAxes, color='#94a3b8', fontsize=7, va='top')
                ax2.set_facecolor('#1e293b'); fig2.patch.set_facecolor('#1e293b')
                ax2.tick_params(colors='white', labelsize=8)
                ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                ax2.legend(facecolor='#0f172a', labelcolor='white', fontsize=7, loc='upper left')
                plt.xticks(rotation=30); plt.tight_layout()
                plt.savefig(os.path.join(CHARTS_DIR, f"{ticker}_bt.png"), transparent=True)
                plt.close(fig2); has_chart = True
            except Exception: has_chart = False

        if is_active or len(trades_log) > 0 or curr_triggered or curr_pqr >= PQR_ENTRY_MIN:
            _rsm = round(float(rs_mom.iloc[-1]), 1) if not pd.isna(rs_mom.iloc[-1]) else 0
            etf_js_data.append({
                'ticker': ticker, 'sector': sector,
                'rs': round(float(rs.iloc[-1]), 0) if not pd.isna(rs.iloc[-1]) else 0,
                'rs_mom': _rsm, 'status': st, 'in_panic_now': curr_in_panic,
                'is_crash_now': curr_crash,
                'pqr': round(curr_pqr, 0), 'pqr_ok': curr_pqr_ok,
                'win_rate': round(win_rate, 1), 'avg_ret': round(avg_ret, 1),
                'trades_cnt': len(trades_log), 'has_chart': has_chart,
                'pos_size': f"{round(ssize, 1)}%",
                'curr_price': round(cp, 2), 'sl_price': round(csl2, 2),
                'tp_price': round(ctp2, 2), 'trail_price': round(trail_px, 2),
                'risk_per_share': rps, 'patterns': curr_triggered,
                'pattern_score': ps, 'pattern_details': curr_det,
                'is_blacklisted': is_bl, 'is_high_conviction': is_hc_n,
                'vix_now': round(last_vix, 1), 'tp_mult': ctpm, 'conviction': cconv,
                'month_blocked': not curr_month_ok, 'atr': round(catr, 2),
                'is_late_join': is_late_join,
                'ideal_entry': round(csl2 + ATR_STOP_LOSS_MULT * catr, 2),
                'trigger_date': c.index[-1].strftime('%Y-%m-%d'),
                'days_since': (datetime.date.today() - c.index[-1].date()).days,
                'first_seen': _first_seen,
                'days_active': _days_active,
            })
    except Exception: pass

# Console summary
_dfq = pd.DataFrame(all_trade_records)
if not _dfq.empty:
    _w = 70
    print(f"\n{'═'*_w}")
    print(f"  QUANT MASTER V3.13 — Stability-Validated Results")
    print(f"{'─'*_w}")
    print(f"  {'Pattern':<22} {'N':>5}  {'Win%':>6}  {'Mean':>7}  {'Median':>7}")
    for _p in ['VCP', 'P2_PostEarnings', 'P4_TightCoil', 'P5_RSI_Bounce', 'P6_XS_Mom']:
        _m = _dfq['Signal_Pattern'].str.contains(_p, na=False)
        _s = _dfq.loc[_m, 'Return_%']
        if len(_s) < 3: continue
        print(f"  {_p:<22} {len(_s):>5}  {(_s>0).mean()*100:>5.1f}%  {_s.mean():>+6.2f}%  {_s.median():>+6.2f}%")
    print(f"{'─'*_w}")
    for _lbl, _msk in [('Normal', ~_dfq['Panic_Mode_Entry']), ('Panic', _dfq['Panic_Mode_Entry'])]:
        _s = _dfq.loc[_msk, 'Return_%']
        if len(_s) >= 3:
            pf_s = _s[_s>0].sum()/abs(_s[_s<=0].sum()) if _s[_s<=0].sum()!=0 else 99
            print(f"  {_lbl:<10} N={len(_s):>5} Win={(_s>0).mean()*100:.1f}%  Mean={_s.mean():+.2f}%  PF={pf_s:.2f}")
    pf_tot = _dfq.loc[_dfq['Return_%']>0,'Return_%'].sum()/abs(_dfq.loc[_dfq['Return_%']<=0,'Return_%'].sum())
    print(f"  Total: {len(_dfq)} | Win: {(_dfq['Return_%']>0).mean()*100:.1f}% | Mean: {_dfq['Return_%'].mean():+.2f}% | PF: {pf_tot:.2f}")
    print(f"{'═'*_w}\n")

# =============================================================================
# MODULE 6 — CSV + Analytics
# =============================================================================
print("⏳ [6/7] 匯出 CSV + 分析統計...")

df_trades = pd.DataFrame(all_trade_records)
if not df_trades.empty:
    df_trades.to_csv(os.path.join(OUTPUT_DIR, "trade_records_enriched.csv"), index=False, encoding='utf-8-sig')

def _stats(s):
    s = s.dropna()
    if len(s) < 3: return None
    pf = s[s>0].sum()/abs(s[s<=0].sum()) if s[s<=0].sum() != 0 else float('inf')
    return {'n': int(len(s)), 'win': round((s>0).mean()*100, 1),
            'mean': round(s.mean(), 2), 'median': round(s.median(), 2), 'pf': round(pf, 2)}

analytics_data = {}
if not df_trades.empty:
    _rc = 'Return_%'
    analytics_data['overall']        = _stats(df_trades[_rc])
    analytics_data['panic_vs_normal'] = {}
    for lbl, msk in [('Normal', ~df_trades['Panic_Mode_Entry']), ('Panic', df_trades['Panic_Mode_Entry'])]:
        s = _stats(df_trades[msk][_rc])
        if s: analytics_data['panic_vs_normal'][lbl] = s
    analytics_data['vix_regime'] = {}
    for reg in ['calm', 'elevated', 'fear', 'panic']:
        s = _stats(df_trades[df_trades['VIX_Regime'] == reg][_rc])
        if s: analytics_data['vix_regime'][reg] = s
    analytics_data['pqr_bands'] = {}
    df_trades['PQR_Band'] = pd.cut(df_trades['PQR_Score_Entry'].astype(float),
        bins=[0, 75, 80, 85, 90, 100], labels=['75-80', '80-85', '85-90', '90-95', '95+'])
    for b in ['75-80', '80-85', '85-90', '90-95', '95+']:
        s = _stats(df_trades[df_trades['PQR_Band'].astype(str) == b][_rc])
        if s: analytics_data['pqr_bands'][b] = s
    analytics_data['by_sector'] = {}
    for sec in df_trades['Sector'].unique():
        s = _stats(df_trades[df_trades['Sector'] == sec][_rc])
        if s: analytics_data['by_sector'][sec] = s
    analytics_data['by_reason'] = {}
    for r in df_trades['Reason'].unique():
        s = _stats(df_trades[df_trades['Reason'] == r][_rc])
        if s: analytics_data['by_reason'][r] = s
    analytics_data['hold_dist'] = {
        'mean':   round(df_trades['Hold_Days'].mean(), 1),
        'median': round(df_trades['Hold_Days'].median(), 1),
        'max':    int(df_trades['Hold_Days'].max()),
    }
    df_trades['Entry_Month'] = pd.to_datetime(df_trades['Entry_Date']).dt.month
    _mn = {1:'Jan',2:'Feb',3:'Mar',4:'Apr',5:'May',8:'Aug',10:'Oct',11:'Nov',12:'Dec'}
    analytics_data['monthly'] = {}
    for m, nm in _mn.items():
        s = _stats(df_trades[df_trades['Entry_Month'] == m][_rc])
        if s: analytics_data['monthly'][nm] = s

pattern_rows = []
for d in etf_js_data:
    if d['patterns'] or d['pqr'] >= PQR_ENTRY_MIN:
        pattern_rows.append({
            'Ticker': d['ticker'], 'Sector': d['sector'],
            'RS_Score': d['rs'], 'RS_Momentum': d['rs_mom'], 'PQR_Score': d['pqr'],
            'Signal_Status': d['status'], 'Pattern_Score': d['pattern_score'],
            'Patterns': '|'.join(d['patterns']),
            'Win_Rate_%': d['win_rate'], 'Avg_Ret_%': d['avg_ret'],
            'Curr_Price': d['curr_price'], 'Stop_Loss': d['sl_price'],
            'Take_Profit': d['tp_price'], 'Trail_Trigger': d['trail_price'],
            'ATR': d['atr'], 'Is_Late_Join': d['is_late_join'],
            'TP_Mult': d['tp_mult'], 'Conviction_Mult': d['conviction'],
            'VIX_Now': d['vix_now'], 'In_Panic_Now': d['in_panic_now'],
            'SPY_Above_200MA_Now': is_bull_market, 'Market_Breadth_Now': curr_breadth,
        })
if pattern_rows:
    pd.DataFrame(pattern_rows).sort_values(['Pattern_Score', 'PQR_Score'], ascending=[False, False]).to_csv(
        os.path.join(OUTPUT_DIR, "pattern_signals.csv"), index=False, encoding='utf-8-sig')

# =============================================================================
# MODULE 7 — Dashboard V3.10
# =============================================================================
print("⏳ [7/7] 生成 V3.13 Dashboard (大圖SPX + 中文圖例 + 觸發股票面板)...")

class _NpEnc(json.JSONEncoder):
    def default(self,o):
        if hasattr(o,'item'): return o.item()
        return super().default(o)
_jd=lambda x:json.dumps(x,cls=_NpEnc)

_PMETA = _jd({
    "VCP":             {"label":"VCP",    "color":"#06b6d4","win":"52%","note":f"波動收縮突破|TP×{_VCP_TP}|PQR≥{PQR_VCP_MIN}+量確認"},
    "P2_PostEarnings": {"label":"P2 財報","color":"#f97316","win":"50%","note":"財報跳空≥5%+量≥2x|TP×3.5|正常+恐慌"},
    "P4_TightCoil":    {"label":"P4 緊縮","color":"#14b8a6","win":"48%","note":"3週振幅≤4%+突破+RS↑|TP×4.5"},
    "P5_RSI_Bounce":   {"label":"P5 RSI", "color":"#ef4444","win":"45%","note":"RSI<35+跌≥10%|TP×3.0|恐慌專用"},
    "P6_XS_Mom":       {"label":"P6 橫截","color":"#6366f1","win":"47%","note":"橫截面前10%|TP×4.0|恐慌專用"},
})
_ETF  = _jd(etf_js_data)
_ANA  = _jd(analytics_data)
_ANA  = json.dumps(analytics_data)
_VTHR = VIX_PANIC_THRESHOLD; _MRSK = MAX_ACCOUNT_RISK_PCT
_PQR_MIN = PQR_ENTRY_MIN; _PQR_VCP = PQR_VCP_MIN; _TRAIL_T = TRAIL_TRIGGER_ATR

html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://s3.tradingview.com/tv.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<title>Quant Master V3.13</title>
<style>
.pb{{display:inline-flex;align-items:center;gap:2px;font-size:9px;font-weight:700;padding:1px 5px;border-radius:3px;cursor:pointer}}
.s3{{background:rgba(16,185,129,.22);border:1px solid rgba(16,185,129,.5)}}
.s2{{background:rgba(59,130,246,.18);border:1px solid rgba(59,130,246,.4)}}
.s1{{background:rgba(100,116,139,.18);border:1px solid rgba(100,116,139,.3)}}
.pqr-bar{{height:7px;border-radius:3px;background:linear-gradient(90deg,#D85A30 0%,#f59e0b 50%,#1D9E75 100%);position:relative}}
.pqr-needle{{position:absolute;top:-3px;width:3px;height:13px;background:#fff;border-radius:1px;transform:translateX(-50%);transition:left .4s}}
#ptip{{position:fixed;z-index:9999;background:#1e293b;border:1px solid #334155;border-radius:8px;padding:10px 14px;font-size:11px;max-width:260px;pointer-events:none;display:none}}
.tb{{font-size:10px;font-weight:600;padding:4px 8px;cursor:pointer;border-bottom:2px solid transparent;color:#64748b;white-space:nowrap}}
.tb.on{{color:#f1f5f9;border-bottom-color:#3b82f6}}
.mpnl{{display:none;height:100%}}.mpnl.on{{display:flex;height:100%}}
.apnl{{display:none}}.apnl.on{{display:block;height:100%}}
.manpnl{{display:none;overflow-y:auto}}.manpnl.on{{display:block}}
/* Filter buttons — Chinese legend */
.flt-btn{{font-size:10px;font-weight:600;padding:3px 8px;border-radius:4px;cursor:pointer;border:1px solid transparent;white-space:nowrap;transition:all .15s}}
.flt-btn:hover{{opacity:.8}}
.flt-btn.active-flt{{ring:2px}}
/* Triggered tickers panel */
.trig-card{{background:#111827;border:1px solid #1e293b;border-radius:8px;padding:10px 12px;margin-bottom:6px;position:relative}}
.trig-ticker{{font-size:15px;font-weight:700;color:#60a5fa}}
.trig-late{{position:absolute;top:8px;right:10px;font-size:9px;font-weight:700;padding:2px 7px;border-radius:3px;background:rgba(234,179,8,.2);color:#ca8a04;border:1px solid rgba(234,179,8,.4)}}
.trig-row{{display:flex;gap:6px;margin-top:6px;flex-wrap:wrap}}
.trig-cell{{flex:1;min-width:70px;background:#1e293b;border-radius:5px;padding:6px 8px;text-align:center}}
.trig-cell .lbl{{font-size:9px;color:#64748b;margin-bottom:2px}}
.trig-cell .val{{font-size:12px;font-weight:700}}
.trig-bar{{height:4px;border-radius:2px;margin-top:5px;background:#1e293b;overflow:hidden}}
.trig-fill{{height:100%;border-radius:2px}}
.pm-warn{{background:rgba(234,179,8,.15);border:1px solid rgba(234,179,8,.45);border-radius:6px;padding:5px 11px;font-size:10px;color:#fbbf24;display:flex;align-items:center;gap:6px;margin-bottom:4px}}
#lbox{{display:none;position:fixed;inset:0;background:rgba(0,0,0,.9);z-index:99999;cursor:zoom-out;align-items:center;justify-content:center}}
#lbox.on{{display:flex}}
#lbox img{{max-width:95vw;max-height:92vh;object-fit:contain;border-radius:6px}}
.zoomable{{cursor:zoom-in;transition:opacity .12s}}.zoomable:hover{{opacity:.82}}
.sec-tag{{font-size:9px;padding:1px 6px;border-radius:3px;font-weight:600;white-space:nowrap}}
.flt-wrap{{position:relative;display:inline-block}}
.flt-tip{{display:none;position:absolute;bottom:calc(100% + 6px);left:50%;transform:translateX(-50%);background:#0f172a;border:1px solid #334155;border-radius:6px;padding:7px 11px;font-size:10px;color:#cbd5e1;white-space:nowrap;z-index:9999;line-height:1.55;pointer-events:none}}
.flt-tip::after{{content:'';position:absolute;top:100%;left:50%;transform:translateX(-50%);border:5px solid transparent;border-top-color:#334155}}
.flt-wrap:hover .flt-tip{{display:block}}
.trig-chart-wrap{{margin-top:7px;background:#0f172a;border-radius:5px;overflow:hidden;cursor:zoom-in;border:1px solid #1e293b}}
.trig-chart-wrap img{{width:100%;display:block;transition:opacity .12s}}.trig-chart-wrap:hover img{{opacity:.85}}
</style>
</head>
<body class="bg-[#0f172a] text-slate-200 h-screen overflow-hidden flex flex-col font-sans">
<div id="lbox" onclick="closeLbox()"><img id="lbox-img" src=""></div>
<div id="ptip"></div>

<header class="bg-slate-900 border-b border-slate-800 p-2 flex justify-between items-center shrink-0 gap-2 flex-wrap">
  <div>
    <h1 class="text-xl font-black text-white">QUANT <span class="text-blue-500">MASTER V3.13</span></h1>
    <p class="text-[9px] text-slate-400">預設#{TOP10_PRESET}·PQRv={PQR_VCP_MIN}·TP×{_VCP_TP}·TS={TIME_STOP_DAYS}d·ATR×{ATR_STOP_LOSS_MULT}·P6恐慌·毒月提醒</p>
  </div>
  <div class="flex gap-1.5 flex-wrap items-center">
    <div class="px-2 py-1 rounded-lg border border-slate-700 bg-slate-800/50">
      <div class="text-[9px] text-slate-400">寬度</div>
      <div class="font-black {breadth_color} text-sm">{curr_breadth}%</div>
    </div>
    <div class="px-2 py-1 rounded-lg border border-slate-700 bg-slate-800/50">
      <div class="text-[9px] text-slate-400">派發</div>
      <div class="font-black {dist_color} text-sm">{curr_dist_days}d</div>
    </div>
    <div class="px-2 py-1 rounded-lg border {ftd_color}">
      <div class="text-[9px] opacity-70 font-bold">市況</div>
      <div class="font-black text-xs">{ftd_status}</div>
    </div>
    <div class="px-2 py-1 rounded-lg border border-slate-700 bg-slate-800/50">
      <div class="text-[9px] text-slate-400">VIX {round(curr_vix_val,1)}</div>
      <div class="font-black text-sm {'text-red-300' if is_curr_crash else 'text-orange-400' if is_curr_panic else 'text-amber-400' if curr_vix_val>20 else 'text-emerald-400'}">{_vix_regime(curr_vix_val).upper()}{'💥' if is_curr_crash else ''}</div>
    </div>
    <div class="px-2 py-1 rounded-lg border border-cyan-700/50 bg-cyan-900/20 text-[10px]">
      <span class="text-cyan-400 font-bold">PQR≥{PQR_ENTRY_MIN}</span>
      <span class="text-slate-500 mx-1">|</span>
      <span class="text-slate-400">封鎖:Jun/Jul/Sep</span>
    </div>
  </div>
</header>

<div class="bg-slate-900 border-b border-slate-800 flex gap-1 px-3 shrink-0">
  <button class="tb on" onclick="sw('signals',this)">🎯 訊號</button>
  <button class="tb" onclick="sw('triggered',this)">🔔 觸發股票</button>
  <button class="tb" onclick="sw('analytics',this)">📊 分析</button>
  <button class="tb" onclick="sw('manual',this)">📖 說明書</button>
</div>
<div style="flex:1;overflow:hidden;display:flex;flex-direction:column;min-height:0">
<!-- ══ TAB 1: SIGNALS ══ -->
<div class="mpnl on flex-1 overflow-hidden p-2 gap-2" id="pnl-signals">

  <!-- LEFT: narrow list panel -->
  <div style="width:260px;flex-shrink:0;display:flex;flex-direction:column;gap:6px;overflow:hidden;height:100%">

    <!-- Filter buttons -->
    <div style="background:#1e293b;border-radius:8px;padding:8px;flex-shrink:0">
      <div style="font-size:9px;color:#64748b;margin-bottom:5px">篩選</div>
      <div style="display:flex;flex-wrap:wrap;gap:3px">
        <div class="flt-wrap"><button class="flt-btn" style="background:#334155;color:#f1f5f9" onclick="af('all')">全部</button><div class="flt-tip">顯示所有股票</div></div>
        <div class="flt-wrap"><button class="flt-btn" style="background:rgba(59,130,246,.2);color:#93c5fd;border-color:rgba(59,130,246,.4)" onclick="af('active')">🔥觸發</button><div class="flt-tip">今日出現買入訊號</div></div>
        <div class="flt-wrap"><button class="flt-btn" style="background:rgba(34,211,238,.15);color:#67e8f9;border-color:rgba(34,211,238,.35)" onclick="af('pqr75')">PQR≥75</button><div class="flt-tip">綜合品質評分≥75</div></div>
        <div class="flt-wrap"><button class="flt-btn" style="background:rgba(167,139,250,.2);color:#a78bfa;border-color:rgba(167,139,250,.4)" onclick="af('hc')">⚡HC</button><div class="flt-tip">VCP突破+成交量確認</div></div>
        <div class="flt-wrap"><button class="flt-btn" style="background:rgba(249,115,22,.2);color:#fb923c;border-color:rgba(249,115,22,.4)" onclick="af('panic')">🚨恐慌</button><div class="flt-tip">VIX&gt;25恐慌期</div></div>
        <div class="flt-wrap"><button class="flt-btn" style="background:rgba(6,182,212,.2);color:#67e8f9;border-color:rgba(6,182,212,.4)" onclick="af('VCP')">VCP</button><div class="flt-tip">縮量整理後放量突破</div></div>
        <div class="flt-wrap"><button class="flt-btn" style="background:rgba(20,184,166,.2);color:#5eead4;border-color:rgba(20,184,166,.4)" onclick="af('P4_TightCoil')">P4</button><div class="flt-tip">三週窄幅盤整後突破</div></div>
        <div class="flt-wrap"><button class="flt-btn" style="background:rgba(249,115,22,.15);color:#fdba74;border-color:rgba(249,115,22,.35)" onclick="af('P2_PostEarnings')">P2</button><div class="flt-tip">財報後大漲≥5%+爆量</div></div>
        <div class="flt-wrap"><button class="flt-btn" style="background:rgba(99,102,241,.15);color:#a5b4fc;border-color:rgba(99,102,241,.35)" onclick="af('P6_XS_Mom')">P6</button><div class="flt-tip">恐慌期最強前10%</div></div>
        <div class="flt-wrap"><button class="flt-btn" style="background:rgba(100,116,139,.2);color:#94a3b8;border-color:rgba(100,116,139,.4)" onclick="af('rs80')">RS&gt;80</button><div class="flt-tip">相對強度&gt;80</div></div>
        <div class="flt-wrap"><button class="flt-btn" style="background:rgba(30,41,59,.8);color:#64748b;border-color:rgba(100,116,139,.3)" onclick="af('watch')">👀觀察</button><div class="flt-tip">評分達標等待訊號</div></div>
      </div>
    </div>

    <!-- Poison month banner -->
    <div id="pm-banner" class="pm-warn" style="display:none;flex-shrink:0">
      🌙 <strong>毒月</strong>：<span id="pm-text"></span>建議半倉
    </div>

    <!-- Signal table — fills remaining space -->
    <div style="background:#1e293b;border-radius:8px;flex:1;overflow:hidden;display:flex;flex-direction:column">
      <table style="width:100%;border-collapse:collapse;font-size:11px">
        <thead style="background:#111827;position:sticky;top:0;z-index:10">
          <tr style="border-bottom:1px solid #334155">
            <th style="padding:5px 6px;text-align:left;color:#64748b;font-size:9px;cursor:pointer" onclick="sb('ticker')">股票↕</th>
            <th style="padding:5px 6px;text-align:left;color:#64748b;font-size:9px;cursor:pointer" onclick="sb('pqr')">PQR↕</th>
            <th style="padding:5px 6px;text-align:left;color:#64748b;font-size:9px;cursor:pointer" onclick="sb('pattern_score')">型態</th>
            <th style="padding:5px 6px;text-align:left;color:#64748b;font-size:9px;cursor:pointer" onclick="sb('win_rate')">勝率</th>
          </tr>
        </thead>
      </table>
      <div style="overflow-y:auto;flex:1">
        <table style="width:100%;border-collapse:collapse;font-size:11px">
          <tbody id="signal-table"></tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- RIGHT: charts + trade plan -->
  <div style="flex:1;display:flex;flex-direction:column;gap:6px;overflow:hidden;min-width:0">

    <!-- Top row: SPX (zoomable) + Backtest side by side -->
    <div style="display:flex;gap:6px;height:200px;flex-shrink:0">
      <!-- SPX chart -->
      <div style="flex:1;background:#0f172a;border-radius:8px;border:1px solid #1e293b;display:flex;align-items:center;justify-content:center;position:relative;overflow:hidden">
        <div style="position:absolute;top:6px;left:8px;z-index:10;display:flex;gap:4px;align-items:center;flex-wrap:wrap">
          <span style="font-size:10px;font-weight:600;color:#cbd5e1">SPX</span>
          <span style="font-size:8px;background:rgba(59,130,246,.2);color:#60a5fa;padding:1px 4px;border-radius:3px">20MA</span>
          <span style="font-size:8px;background:rgba(245,158,11,.2);color:#fbbf24;padding:1px 4px;border-radius:3px">50MA</span>
          <span style="font-size:8px;background:rgba(239,68,68,.2);color:#f87171;padding:1px 4px;border-radius:3px">200MA</span>
          <span style="font-size:8px;color:#34d399">▲FTD</span>
          <span style="font-size:8px;color:#ef4444">▼派發</span>
        </div>
        <img src="charts/SPY_Trend.png" class="zoomable" onclick="openLbox(this.src)" title="點擊放大" style="max-height:100%;max-width:100%;object-fit:contain;image-rendering:crisp-edges">
      </div>
      <!-- Backtest chart -->
      <div style="width:220px;flex-shrink:0;background:#111827;border-radius:8px;border:1px solid #1e293b;display:flex;flex-direction:column;overflow:hidden">
        <div style="font-size:9px;color:#64748b;padding:5px 8px;background:#0f172a;flex-shrink:0" id="bt_title">回測圖 · 點擊放大</div>
        <div style="flex:1;display:flex;align-items:center;justify-content:center;overflow:hidden;padding:4px">
          <p id="bt_ph" style="color:#475569;font-size:10px">選擇股票</p>
          <img id="bt_img" src="" style="display:none;max-height:100%;max-width:100%;object-fit:contain;border-radius:4px;cursor:zoom-in" onclick="openLbox(this.src)" title="點擊放大" class="zoomable">
        </div>
      </div>
    </div>

    <!-- Trade plan bar — compact single row -->
    <div style="background:#1e293b;border-radius:8px;padding:8px 10px;flex-shrink:0">
      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
        <span style="font-size:11px;font-weight:600;color:#f59e0b">🧮</span>
        <span id="ctk" style="font-size:11px;font-weight:700;color:#fff;background:#334155;padding:1px 7px;border-radius:4px">-</span>
        <span id="panic_badge" style="display:none;font-size:9px;font-weight:700;padding:1px 6px;border-radius:3px;background:rgba(249,115,22,.2);color:#fb923c">🚨恐慌</span>
        <span id="hc_badge"    style="display:none;font-size:9px;font-weight:700;padding:1px 6px;border-radius:3px;background:rgba(167,139,250,.2);color:#a78bfa">⚡HC</span>
        <span id="late_badge"  style="display:none;font-size:9px;font-weight:700;padding:1px 6px;border-radius:3px;background:rgba(234,179,8,.2);color:#ca8a04">⚠️延遲</span>
        <div style="display:flex;gap:6px;flex-wrap:wrap;margin-left:4px">
          <div style="background:#0f172a;border-radius:5px;padding:4px 8px;text-align:center"><div style="font-size:8px;color:#64748b">進場</div><div style="font-size:12px;font-weight:700;color:#fff" id="ce">-</div></div>
          <div style="background:rgba(239,68,68,.1);border-radius:5px;padding:4px 8px;text-align:center"><div style="font-size:8px;color:#ef4444" id="sl_lbl">止損</div><div style="font-size:12px;font-weight:700;color:#ef4444" id="csl">-</div></div>
          <div style="background:rgba(16,185,129,.1);border-radius:5px;padding:4px 8px;text-align:center"><div style="font-size:8px;color:#34d399" id="tp_lbl">止盈</div><div style="font-size:12px;font-weight:700;color:#34d399" id="ctp">-</div></div>
          <div style="background:rgba(59,130,246,.1);border-radius:5px;padding:4px 8px;text-align:center"><div style="font-size:8px;color:#60a5fa">追蹤</div><div style="font-size:12px;font-weight:700;color:#60a5fa" id="ctr">-</div></div>
          <div style="background:#0f172a;border-radius:5px;padding:4px 8px;text-align:center"><div style="font-size:8px;color:#f59e0b">股數</div><div style="font-size:12px;font-weight:700;color:#f59e0b" id="csh">-</div></div>
          <div style="background:#0f172a;border-radius:5px;padding:4px 8px;text-align:center"><div style="font-size:8px;color:#64748b">成本</div><div style="font-size:12px;font-weight:700;color:#93c5fd" id="cco">-</div></div>
        </div>
        <div style="display:flex;align-items:center;gap:6px;margin-left:auto">
          <span style="font-size:9px;color:#22d3ee">PQR</span>
          <div class="pqr-bar" style="width:80px"><div class="pqr-needle" id="pqr_needle" style="left:0%"></div></div>
          <span id="pqr_val" style="font-size:10px;font-weight:600;color:#22c55e">-</span>
          <label style="font-size:9px;color:#64748b">帳戶$</label>
          <input type="number" id="acc_size" value="100000" style="background:#111827;border:1px solid #334155;color:#fff;font-size:10px;padding:3px 6px;border-radius:4px;width:80px;text-align:right" onchange="uc()" onkeyup="uc()">
        </div>
      </div>
    </div>

    <!-- Pattern cards (collapsible, hidden until ticker selected) -->
    <div id="pat-panel" style="display:none;background:#1e293b;border-radius:8px;padding:8px 10px;flex-shrink:0">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
        <span style="font-size:11px;font-weight:600;color:#a78bfa">⬡ 型態 — <span id="pat-tk">-</span></span>
        <span id="pat-score" style="font-size:10px;padding:1px 6px;border-radius:3px;font-weight:600"></span>
      </div>
      <div id="pat-cards" style="display:flex;gap:6px;flex-wrap:wrap"></div>
    </div>

    <!-- TradingView — fills ALL remaining space -->
    <div id="tv_chart_container" style="flex:1;min-height:250px;background:#0f172a;border-radius:8px;overflow:hidden;position:relative"></div>
  </div>
</div>
<!-- ══ TAB 2: TRIGGERED TICKERS ══ -->
<div class="apnl flex-1 overflow-y-auto p-3" id="pnl-triggered">
  <div class="max-w-4xl mx-auto">
    <div class="flex items-center gap-3 mb-3">
      <h2 class="text-sm font-bold text-white">🔔 觸發股票面板</h2>
      <span class="text-[10px] text-slate-500">進場 / 止損 / 止盈 · 黃色⚠️表示已延遲進場超過1ATR</span>
    </div>
    <div class="mb-3 flex items-center gap-2">
      <label class="text-[10px] text-slate-400">帳戶 ($):</label>
      <input type="number" id="trig_acc" value="100000"
             class="bg-slate-800 border border-slate-600 text-white text-xs px-2 py-1 rounded w-24 text-right focus:outline-none focus:border-amber-500"
             onchange="renderTriggered()" onkeyup="renderTriggered()">
      <span class="text-[10px] text-slate-500 ml-2">每筆風險 {int(MAX_ACCOUNT_RISK_PCT*100)}% 帳戶</span>
    </div>
    <div id="trig-list"></div>
    <div id="trig-empty" class="text-center text-slate-500 text-sm py-8">目前沒有觸發訊號</div>
  </div>
</div>

<!-- ══ TAB 3: ANALYTICS ══ -->
<div class="apnl flex-1 overflow-y-auto p-3" id="pnl-analytics">
  <div class="max-w-5xl mx-auto">
    <div class="grid grid-cols-4 gap-3 mb-4" id="sum-cards"></div>
    <div class="grid grid-cols-2 gap-4 mb-4">
      <div class="bg-[#0f172a] border border-[#1e293b] rounded-lg p-3"><div class="text-xs font-bold text-slate-300 mb-2">PQR 分數帶勝率</div><div style="position:relative;height:190px"><canvas id="pqrC"></canvas></div></div>
      <div class="bg-[#0f172a] border border-[#1e293b] rounded-lg p-3"><div class="text-xs font-bold text-slate-300 mb-2">Normal vs Panic</div><div style="position:relative;height:190px"><canvas id="pvnC"></canvas></div></div>
    </div>
    <div class="grid grid-cols-2 gap-4 mb-4">
      <div class="bg-[#0f172a] border border-[#1e293b] rounded-lg p-3"><div class="text-xs font-bold text-slate-300 mb-2">月份績效 (已修正)</div><div style="position:relative;height:190px"><canvas id="monC"></canvas></div></div>
      <div class="bg-[#0f172a] border border-[#1e293b] rounded-lg p-3"><div class="text-xs font-bold text-slate-300 mb-2">VIX 環境績效</div><div style="position:relative;height:190px"><canvas id="vixC"></canvas></div></div>
    </div>
    <div class="grid grid-cols-2 gap-4 mb-4">
      <div class="bg-[#0f172a] border border-[#1e293b] rounded-lg p-3"><div class="text-xs font-bold text-slate-300 mb-2">行業勝率排名</div><div style="position:relative;height:260px"><canvas id="secC"></canvas></div></div>
      <div class="bg-[#0f172a] border border-[#1e293b] rounded-lg p-3"><div class="text-xs font-bold text-slate-300 mb-2">出場原因分析</div><div style="position:relative;height:190px"><canvas id="rsC"></canvas></div></div>
    </div>
    <div id="ins-boxes" class="grid grid-cols-2 gap-3 mb-4"></div>
  </div>
</div>

<!-- ══ TAB 4: MANUAL ══ -->
<div class="manpnl flex-1 p-4 overflow-y-auto" id="pnl-manual" style="background:#0b0f1a">
<div style="max-width:800px;margin:0 auto;font-family:serif">
<div style="text-align:center;padding:1.75rem 2rem;border:1px solid #7a5c12;border-radius:10px;background:#0e1929;margin-bottom:1.75rem">
  <div style="font-size:9px;letter-spacing:.18em;color:#d4a832;text-transform:uppercase;margin-bottom:.5rem">使用說明書 V3.12</div>
  <div style="font-size:1.9rem;font-weight:700;color:#fff">Quant Master <span style="color:#d4a832">V3.12</span></div>
  <div style="color:#475569;font-size:12px;margin-top:.5rem">穩定性驗證 · PQR≥{PQR_ENTRY_MIN} · P6恐慌模式 · ATR×{ATR_STOP_LOSS_MULT} · 毒月提醒</div>
  <div style="display:flex;gap:.5rem;justify-content:center;flex-wrap:wrap;margin-top:1rem">
    <span style="font-size:10px;padding:2px 10px;border-radius:20px;border:1px solid #0e5a6b;color:#22d3ee;background:rgba(34,211,238,.06)">PQR≥{PQR_ENTRY_MIN}</span>
    <span style="font-size:10px;padding:2px 10px;border-radius:20px;border:1px solid #4c1d95;color:#a78bfa;background:rgba(139,92,246,.06)">P6 恐慌模式</span>
    <span style="font-size:10px;padding:2px 10px;border-radius:20px;border:1px solid #7a5c12;color:#d4a832;background:rgba(212,168,50,.07)">毒月提醒 Jun/Jul/Sep</span>
    <span style="font-size:10px;padding:2px 10px;border-radius:20px;border:1px solid #633806;color:#fdba74;background:rgba(249,115,22,.06)">ATR×{ATR_STOP_LOSS_MULT} 止損</span>
    <span style="font-size:10px;padding:2px 10px;border-radius:20px;border:1px solid #791F1F;color:#fca5a5;background:rgba(248,113,113,.06)">崩潰保護 -12%</span>
  </div>
</div>

<div style="background:#0a1628;border:1.5px solid #1D9E75;border-radius:10px;padding:1.1rem 1.3rem;margin-bottom:1.4rem">
  <div style="font-size:.95rem;font-weight:700;color:#1D9E75;margin-bottom:.8rem">🚀 快速開始 — 三步上手</div>
  <div style="display:grid;grid-template-columns:auto 1fr;gap:.4rem .8rem;font-size:12px;line-height:1.65">
    <div style="color:#1D9E75;font-weight:700;font-size:1rem">①</div>
    <div><span style="color:#fff;font-weight:600">看頂部燈號</span> — 決定今天能否交易<br><span style="color:#64748b">🟢牛市/✅FTD → 可做多 · 🚨恐慌(VIX&gt;25) → 只做恐慌型態 · 💥崩潰 → 全部暫停</span></div>
    <div style="color:#1D9E75;font-weight:700;font-size:1rem">②</div>
    <div><span style="color:#fff;font-weight:600">點「觸發股票」標籤</span> — 找到今日訊號<br><span style="color:#64748b">看進場/止損/止盈三個價位。⚠️黃色延遲→縮半倉。🌙毒月→縮半倉。回測圖直接顯示在卡片上。</span></div>
    <div style="color:#1D9E75;font-weight:700;font-size:1rem">③</div>
    <div><span style="color:#fff;font-weight:600">填帳戶金額 → 系統自動算股數</span><br><span style="color:#64748b">每筆最多虧1%帳戶。⚡HC標記可加到1.5倍。止損是最重要規則，任何情況都不能省。</span></div>
  </div>
  <div style="margin-top:.75rem;padding:.5rem .75rem;background:#0f172a;border-radius:5px;font-size:10.5px;color:#64748b">⚠️ 此系統是篩股輔助工具，不是自動交易。進場前請自行確認大盤環境，不構成投資建議。</div>
</div>
<div style="font-size:1.1rem;font-weight:700;color:#d4a832;margin:1.5rem 0 .4rem;padding-bottom:.3rem;border-bottom:1px solid #1e293b">V3.12 版本改動（基於 5,141 筆 20 年回測）</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:.65rem 0">
  <div style="background:#1a2233;border:1px solid rgba(239,68,68,.3);border-radius:7px;padding:.8rem">
    <div style="font-size:11px;color:#f87171;font-weight:700;margin-bottom:.3rem">❌ 移除 P7（量能堆積）</div>
    <div style="font-size:11px;color:#64748b;line-height:1.5">20年 PF=1.16，是所有型態中最弱。佔全部交易量 24.9%，但貢獻最少。移除後整體 PF 提升。</div>
  </div>
  <div style="background:#1a2233;border:1px solid rgba(34,197,94,.3);border-radius:7px;padding:.8rem">
    <div style="font-size:11px;color:#86efac;font-weight:700;margin-bottom:.3rem">✅ P6 恢復恐慌模式（V3.12）</div>
    <div style="font-size:11px;color:#64748b;line-height:1.5">V3.10錯誤開放正常→84.6%被P6淹沒、PF=1.14。穩定性測試：恐慌模式PF=1.605 vs 1.420。</div>
  </div>
  <div style="background:#1a2233;border:1px solid rgba(34,211,238,.3);border-radius:7px;padding:.8rem">
    <div style="font-size:11px;color:#a5f3fc;font-weight:700;margin-bottom:.3rem">✅ 毒月提醒（不硬封鎖）</div>
    <div style="font-size:11px;color:#64748b;line-height:1.5">Jun/Jul/Sep在Dashboard顯示黃色警告，建議半倉。穩定性測試：封鎖可提升PF +0.105（20yr）。</div>
  </div>
  <div style="background:#1a2233;border:1px solid rgba(239,68,68,.3);border-radius:7px;padding:.8rem">
    <div style="font-size:11px;color:#fca5a5;font-weight:700;margin-bottom:.3rem">💥 崩潰保護</div>
    <div style="font-size:11px;color:#64748b;line-height:1.5">SPY 21 日跌幅 &gt; 12% → 暫停所有恐慌入場。2008 P2 恐慌 Win=18.8%，系統性危機令型態失效。</div>
  </div>
</div>

<div style="font-size:1.1rem;font-weight:700;color:#d4a832;margin:1.5rem 0 .4rem;padding-bottom:.3rem;border-bottom:1px solid #1e293b">觸發股票面板說明</div>
<p style="font-size:13px;color:#94a3b8;line-height:1.75;margin-bottom:.65rem">「觸發股票」標籤顯示所有當前出現型態訊號的股票，並提供三個關鍵價格點讓你快速決策是否追入。</p>
<div style="background:#1a2233;border:1px solid rgba(234,179,8,.3);border-radius:7px;padding:.9rem;margin:.65rem 0;font-size:12px;color:#e9d08a;line-height:1.7">
  <strong>⚠️ 已延遲（黃色標記）</strong>：當前價格已高於理想進場點超過 1 個 ATR，建議縮減倉位至 50% 或等待回落至止損上方 0.5 ATR 再進場。延遲進場的止損不變，但盈虧比下降。
</div>
<div style="background:#1a2233;border:1px solid rgba(34,211,238,.3);border-radius:7px;padding:.9rem;margin:.65rem 0;font-size:12px;color:#a5f3fc;line-height:1.7">
  <strong>進度條</strong>：藍色條代表當前價格在「止損到止盈」區間中的位置。條越靠近右邊（綠色），說明價格越接近目標，延遲進場風險越高。
</div>

<p style="color:#334155;font-size:11px;text-align:center;margin-top:1.5rem">Quant Master V3.12 · 基於 5,141 筆 20 年回測 + 穩定性驗證 · 不構成投資建議</p>
</div>
</div>

<script>
const PM={_PMETA};let rawData={_ETF};let curData=[...rawData];
const SEC_C={{'Technology':'#3b82f6','Energy':'#f59e0b','Industrials':'#10b981','Financial Services':'#6366f1','Consumer Cyclical':'#f97316','Communication Services':'#06b6d4','Healthcare':'#a78bfa','Basic Materials':'#78716c','Real Estate':'#84cc16','Consumer Defensive':'#14b8a6','Utilities':'#94a3b8','ETF/Index':'#64748b','Unknown':'#475569'}};
const SEC_ZH={{'Technology':'科技','Energy':'能源','Industrials':'工業','Financial Services':'金融','Consumer Cyclical':'消費','Communication Services':'通訊','Healthcare':'醫療','Basic Materials':'原料','Real Estate':'地產','Consumer Defensive':'必消','Utilities':'公用','ETF/Index':'ETF','Unknown':'—'}};
function secTag(sec){{const c=SEC_C[sec]||'#475569';const z=SEC_ZH[sec]||sec.slice(0,4);return `<span class="sec-tag" style="background:${{c}}22;color:${{c}};border:1px solid ${{c}}44">${{z}}</span>`;}}
const ANA={_ANA};const MAX_RSK={_MRSK};const VIX_THR={_VTHR};
const PQR_MIN={_PQR_MIN};const PQR_VCP={_PQR_VCP};const TRAIL_T={_TRAIL_T};
const ATR_SL={ATR_STOP_LOSS_MULT};
let sc='pqr',sa=false,curTk=null,tvW=null;
const tip=document.getElementById('ptip');

function showTip(e,k){{const m=PM[k];if(!m)return;
  tip.innerHTML=`<b style="color:${{m.color}}">${{m.label}}</b><div style="color:#94a3b8;margin-top:3px">Win:${{m.win}}</div><div style="color:#64748b;font-size:10px;margin-top:2px">${{m.note}}</div>`;
  tip.style.cssText=`display:block;left:${{e.clientX+12}}px;top:${{e.clientY-10}}px;position:fixed;z-index:9999;background:#1e293b;border:1px solid #334155;border-radius:8px;padding:10px 14px;font-size:11px;max-width:260px;pointer-events:none`;}}
function hideTip(){{tip.style.display='none';}}

function sw(id,el){{
  document.querySelectorAll('.tb').forEach(b=>b.classList.remove('on'));
  document.querySelectorAll('.mpnl,.apnl,.manpnl').forEach(p=>p.classList.remove('on'));
  el.classList.add('on');
  document.getElementById('pnl-'+id).classList.add('on');
  if(id==='triggered')renderTriggered();
}}

function loadContent(tk){{
  curTk=tk;if(tvW)tvW.remove();
  tvW=new TradingView.widget({{"autosize":true,"symbol":tk,"interval":"D","timezone":"Etc/UTC","theme":"dark","style":"1","locale":"en","container_id":"tv_chart_container",
    "studies":["MASimple@tv-basicstudies","MASimple@tv-basicstudies"],
    "studies_overrides":{{"moving average.length":20,"moving average.plot.color":"#3b82f6",
      "moving average.2.length":50,"moving average.2.plot.color":"#f59e0b"}},
    "overrides":{{"mainSeriesProperties.showCountdown":true}},
    "hide_side_toolbar":false}});
  const d=rawData.find(x=>x.ticker===tk);
  document.getElementById('bt_title').innerText=tk+(d&&d.has_chart?' 回測圖':' (無圖)');
  document.getElementById('bt_img').classList.toggle('hidden',!(d&&d.has_chart));
  document.getElementById('bt_ph').classList.toggle('hidden',!!(d&&d.has_chart));
  if(d&&d.has_chart)document.getElementById('bt_img').src='charts/'+tk+'_bt.png';
  document.getElementById('panic_badge').classList.toggle('hidden',!(d&&d.in_panic_now));
  document.getElementById('hc_badge').classList.toggle('hidden',!(d&&d.is_high_conviction));
  document.getElementById('late_badge').classList.toggle('hidden',!(d&&d.is_late_join));
  if(d){{
    const pqr=d.pqr||0;
    document.getElementById('pqr_needle').style.left=Math.min(pqr,100)+'%';
    document.getElementById('pqr_val').innerText=pqr.toFixed(0);
    document.getElementById('pqr_val').style.color=pqr>=82?'#22c55e':pqr>=75?'#f59e0b':'#f87171';
  }}
  if(d&&d.patterns&&d.patterns.length>0){{
    document.getElementById('pat-panel').style.display='block';
    document.getElementById('pat-tk').innerText=tk;
    const sb2=document.getElementById('pat-score');
    const sl=[,'★','★★','★★★'];const scc=[,'s1 text-slate-400','s2 text-blue-300','s3 text-emerald-300'];
    sb2.className='text-xs px-2 py-0.5 rounded font-bold '+(scc[d.pattern_score]||'');
    sb2.innerText=sl[d.pattern_score]||'';
    const cc=document.getElementById('pat-cards');cc.innerHTML='';
    d.patterns.forEach(p=>{{const m=PM[p]||{{label:p,color:'#94a3b8',note:'-'}};
      const det=d.pattern_details[p]||{{}};let dh='';
      Object.entries(det).forEach(([k,v])=>{{if(['bar_idx','vix'].includes(k))return;
        dh+=`<div style="display:flex;justify-content:space-between;font-size:9px"><span style="color:#475569">${{k}}</span><span style="color:#94a3b8">${{typeof v==='boolean'?(v?'✓':'✗'):v}}</span></div>`;;}});
      cc.innerHTML+=`<div style="background:#1e293b;border-radius:6px;padding:7px 9px;border:1px solid ${{m.color}}44;cursor:pointer" onmouseenter="showTip(event,'${{p}}')" onmouseleave="hideTip()"><div style="font-weight:700;font-size:10px;color:${{m.color}};margin-bottom:3px">${{m.label}}</div><div style="color:#475569;font-size:9px">${{m.win}} 勝率</div>${{dh}}</div>`;;}});
  }}else{{document.getElementById('pat-panel').style.display='none';}}
  uc();
}}

function uc(){{
  if(!curTk)return;
  const d=rawData.find(x=>x.ticker===curTk);if(!d)return;
  document.getElementById('ctk').innerText=d.ticker;
  const acc=parseFloat(document.getElementById('acc_size').value)||100000;
  const conv=d.is_high_conviction?1.5:1.0;
  const sh=Math.floor(acc*MAX_RSK*conv/d.risk_per_share)||0;
  const cost=sh*d.curr_price;
  document.getElementById('ce').innerText='$'+d.curr_price.toFixed(2);
  document.getElementById('csl').innerText='$'+d.sl_price.toFixed(2);
  document.getElementById('ctp').innerText='$'+d.tp_price.toFixed(2);
  document.getElementById('tp_lbl').innerText='止盈×'+((d.tp_mult)||4).toFixed(1);
  document.getElementById('ctr').innerText='$'+(d.trail_price||d.curr_price).toFixed(2);
  document.getElementById('csh').innerText=sh+(conv>1?' (HC)':'');
  document.getElementById('cco').innerText='$'+cost.toLocaleString(undefined,{{maximumFractionDigits:0}})+'('+(acc>0?(cost/acc*100).toFixed(1):0)+'%)';
}}

function renderTriggered(){{
  const acc=parseFloat(document.getElementById('trig_acc').value)||100000;
  const active=rawData.filter(d=>d.patterns&&d.patterns.length>0&&d.status.includes('🔥'));
  const el=document.getElementById('trig-list');
  const empty=document.getElementById('trig-empty');
  if(!active.length){{el.innerHTML='';empty.style.display='block';return;}}
  empty.style.display='none';
  el.innerHTML=active.sort((a,b)=>b.pqr-a.pqr).map(d=>{{
    const conv=d.is_high_conviction?1.5:1.0;
    const sh=Math.floor(acc*MAX_RSK*conv/d.risk_per_share)||0;
    const cost=sh*d.curr_price;
    const lateLabel=d.is_late_join?'<div class="trig-late">⚠️ 已延遲</div>':'';
    // Price progress bar between sl and tp
    const range=d.tp_price-d.sl_price;
    const pos=range>0?Math.min(Math.max((d.curr_price-d.sl_price)/range,0),1):0;
    const posPct=Math.round(pos*100);
    const barColor=pos<0.4?'#22c55e':pos<0.7?'#f59e0b':'#ef4444';
    let patBadges=d.patterns.map(p=>{{
      const m=PM[p]||{{label:p,color:'#94a3b8'}};
      return `<span class="pb" style="background:${{m.color}}22;border:1px solid ${{m.color}}55;color:${{m.color}};margin-right:3px;margin-bottom:3px">${{m.label}}</span>`;
    }}).join('');
    const adjustedEntry=d.is_late_join?
      `<div style="font-size:9px;color:#ca8a04;margin-top:3px">延遲進場建議: ${{(d.sl_price+ATR_SL*d.atr*0.5).toFixed(2)}} (½ATR 上方)</div>`:
      '';
    return `<div class="trig-card" onclick="loadContent('${{d.ticker}}');sw('signals',document.querySelector('.tb'))">
      ${{lateLabel}}
      <div class="flex items-center gap-2 mb-1 flex-wrap">
        <span class="trig-ticker">${{d.ticker}}</span>
        ${{secTag(d.sector)}}
        ${{d.is_high_conviction?'<span style="font-size:9px;color:#a78bfa;font-weight:700">⚡HC</span>':''}}
        ${{d.in_panic_now?'<span style="font-size:9px;color:#fb923c;font-weight:700">🚨</span>':''}}
        <span style="font-size:9px;color:#64748b;margin-left:auto">PQR ${{d.pqr}} · RS ${{d.rs}}</span>
      </div>
      <div style="font-size:9px;color:#475569;margin-bottom:4px">
        📅 首次觸發：${{d.first_seen||d.trigger_date||'—'}}
        ${{(d.days_active||0)===0?'<span style="color:#22c55e;font-weight:600"> ✦ 今日新訊號</span>':
           (d.days_active||0)<=2?`<span style="color:#22c55e"> · 持續 ${{d.days_active}} 天（新鮮）</span>`:
           (d.days_active||0)<=7?`<span style="color:#f59e0b"> · 持續 ${{d.days_active}} 天（留意）</span>`:
           `<span style="color:#ef4444"> · 持續 ${{d.days_active}} 天（已老化）</span>`}}
      </div>
      <div style="margin-bottom:6px">${{patBadges}}</div>
      <div class="trig-row">
        <div class="trig-cell"><div class="lbl">現價/進場</div><div class="val" style="color:#22c55e">$${{d.curr_price.toFixed(2)}}</div>${{adjustedEntry}}</div>
        <div class="trig-cell"><div class="lbl">止損 (-${{ATR_SL}}ATR)</div><div class="val" style="color:#ef4444">$${{d.sl_price.toFixed(2)}}</div><div style="font-size:9px;color:#64748b">ATR=${{d.atr.toFixed(2)}}</div></div>
        <div class="trig-cell"><div class="lbl">止盈 (×${{(d.tp_mult||4).toFixed(1)}}ATR)</div><div class="val" style="color:#22c55e">$${{d.tp_price.toFixed(2)}}</div></div>
        <div class="trig-cell"><div class="lbl">追蹤觸發</div><div class="val" style="color:#60a5fa">$${{(d.trail_price||d.curr_price).toFixed(2)}}</div></div>
        <div class="trig-cell"><div class="lbl">建議股數</div><div class="val" style="color:#f59e0b">${{sh}}${{conv>1?' ×1.5':''}}</div><div style="font-size:9px;color:#64748b">$${{Math.round(cost).toLocaleString()}}</div></div>
      </div>
      <!-- Price progress bar (sl→tp) -->
      <div style="margin-top:7px">
        <div style="font-size:9px;color:#475569;margin-bottom:3px">價格位置：止損 ← ${{posPct}}% → 止盈</div>
        <div class="trig-bar"><div class="trig-fill" style="width:${{posPct}}%;background:${{barColor}}"></div></div>
        <div style="display:flex;justify-content:space-between;font-size:9px;color:#334155;margin-top:2px"><span>$${{d.sl_price.toFixed(2)}}</span><span>$${{d.tp_price.toFixed(2)}}</span></div>
      </div>
      ${{d.has_chart?`<div class="trig-chart-wrap" onclick="event.stopPropagation();openLbox('charts/${{d.ticker}}_bt.png')" title="點擊放大">
        <img src="charts/${{d.ticker}}_bt.png" loading="lazy" alt="回測圖">
        <div style="font-size:8px;color:#334155;text-align:center;padding:2px 0">回測圖 · 點擊全螢幕</div>
      </div>`:'<div style="margin-top:6px;font-size:9px;color:#334155;text-align:center;padding:4px;background:#0f172a;border-radius:4px">（需Active狀態才有回測圖）</div>'}}
    </div>`;
  }}).join('');
}}

function rt(){{
  let html='';
  curData.forEach(d=>{{
    const fire=d.status.includes('🔥');const panic=d.status.includes('恐慌');const blk=d.status.includes('🚫');
    const crash=d.status.includes('崩潰');
    const sc2=fire?(panic||crash?'text-orange-400 font-bold':'text-emerald-400 font-bold'):blk?'text-red-500/50':'text-slate-500';
    const rb=fire?(panic?'bg-orange-900/15 border-orange-500/30':crash?'bg-red-900/20 border-red-500/30':'bg-blue-900/20 border-blue-500/30'):'hover:bg-slate-800 border-slate-800/50';
    const mc=d.rs_mom>0?'text-emerald-400':d.rs_mom<0?'text-red-400':'text-slate-500';
    const pc=d.pqr>=82?'#22c55e':d.pqr>=75?'#f59e0b':'#94a3b8';
    let ph='';
    if(d.patterns&&d.patterns.length>0){{d.patterns.slice(0,3).forEach(p=>{{
      const m=PM[p]||{{label:p,color:'#94a3b8'}};
      ph+=`<span class="pb" style="background:${{m.color}}22;border:1px solid ${{m.color}}55;color:${{m.color}}" onmouseenter="showTip(event,'${{p}}')" onmouseleave="hideTip()">${{m.label}}</span>`;;}});}}
    const ss=[,'s1','s2','s3'][d.pattern_score]||'';const st=[,'★','★★','★★★'][d.pattern_score]||'';
    html+=`<tr class="border-b cursor-pointer ${{rb}}" onclick="loadContent('${{d.ticker}}')">
      <td class="p-1.5"><span class="font-black text-blue-400 text-xs">${{d.ticker}}</span>${{d.is_high_conviction?'<span style="font-size:8px;color:#a78bfa;margin-left:2px">⚡</span>':''}}<span class="${{sc2}} text-[8px] block leading-tight">${{d.status}}</span>${{secTag(d.sector)}}${{(d.days_active||0)===0?'<span style="font-size:7px;color:#22c55e;margin-left:2px">✦新</span>':(d.days_active||0)>7?'<span style="font-size:7px;color:#ef4444;margin-left:2px">老</span>':(d.days_active||0)>2?'<span style="font-size:7px;color:#f59e0b;margin-left:2px">'+d.days_active+'d</span>':''}}</td>
      <td class="p-1.5"><span style="font-weight:700;color:${{pc}};font-size:11px">${{d.pqr}}</span><span class="text-[8px] ${{mc}} block">${{d.rs_mom>0?'+':''}}${{d.rs_mom}}</span></td>
      <td class="p-1.5"><div style="display:flex;flex-wrap:wrap;gap:2px">${{ph}}</div><span class="text-[8px] font-bold ${{ss}}">${{st}}</span></td>
      <td class="p-1.5 text-[11px]">${{d.win_rate}}%<span class="text-[8px] text-slate-500 block">(${{d.trades_cnt}})</span></td>
    </tr>`;
  }});
  document.getElementById('signal-table').innerHTML=html||'<tr><td colspan="4" class="p-4 text-center text-slate-500 text-xs">無結果</td></tr>';
}}

function sb(col){{if(sc===col)sa=!sa;else{{sc=col;sa=false;}}
  curData.sort((a,b)=>{{let vA=a[col],vB=b[col];if(typeof vA==='string'){{vA=vA.toLowerCase();vB=vB.toLowerCase();}}if(vA<vB)return sa?-1:1;if(vA>vB)return sa?1:-1;return 0;}});rt();}}

function af(type){{
  if(type==='all')curData=[...rawData];
  else if(type==='active')curData=rawData.filter(d=>d.status.includes('🔥'));
  else if(type==='rs80')curData=rawData.filter(d=>d.rs>=80);
  else if(type==='pqr75')curData=rawData.filter(d=>d.pqr>=75);
  else if(type==='hc')curData=rawData.filter(d=>d.is_high_conviction);
  else if(type==='panic')curData=rawData.filter(d=>d.in_panic_now&&d.patterns.length>0);
  else if(type==='watch')curData=rawData.filter(d=>d.status.includes('觀察')||d.pqr>=PQR_MIN);
  else curData=rawData.filter(d=>d.patterns&&d.patterns.includes(type));
  sb(sc);
}}

const gc='rgba(255,255,255,0.05)',tc='#475569';
function mk(id,type,labels,datasets,opts={{}}){{
  const el=document.getElementById(id);if(!el)return;
  new Chart(el,{{type,data:{{labels,datasets}},options:{{responsive:true,maintainAspectRatio:false,
    plugins:{{legend:{{display:false}},...(opts.plugins||{{}})}},
    scales:type==='bar'||type==='line'?{{x:{{ticks:{{color:tc,font:{{size:10}}}},grid:{{color:gc}}}},
      y:{{ticks:{{color:tc,font:{{size:10}},callback:v=>v+'%'}},grid:{{color:gc}},...(opts.y||{{}})}},
      ...(opts.y2?{{y2:{{position:'right',ticks:{{color:'#BA7517',font:{{size:10}},callback:v=>(v>=0?'+':'')+v.toFixed(2)+'%'}},grid:{{display:false}}}}}}:{{}})}}:{{}},...(opts.extra||{{}})}}}});
}}

function ba(){{
  const A=ANA;
  const sc3=document.getElementById('sum-cards');
  if(A.overall){{
    const pf=A.overall.pf;
    const cards=[
      {{v:A.overall.n,k:'總交易筆數',c:'text-blue-300'}},
      {{v:A.overall.win+'%',k:'整體勝率',c:A.overall.win>=50?'text-emerald-400':A.overall.win>=47?'text-amber-400':'text-red-400'}},
      {{v:(A.overall.mean>=0?'+':'')+A.overall.mean+'%',k:'平均報酬',c:A.overall.mean>1.2?'text-emerald-400':A.overall.mean>0?'text-amber-400':'text-red-400'}},
      {{v:pf?pf.toFixed(2):'-',k:'Profit Factor',c:pf>=1.5?'text-emerald-400':pf>=1.3?'text-amber-400':'text-red-400'}},
    ];
    sc3.innerHTML=cards.map(c=>`<div style="background:#111827;border:1px solid #1e293b;border-radius:8px;padding:10px 12px"><div style="font-size:18px;font-weight:700;margin-bottom:2px" class="${{c.c}}">${{c.v}}</div><div style="font-size:10px;color:#475569">${{c.k}}</div></div>`).join('');
  }}
  if(A.pqr_bands){{
    const ent=Object.entries(A.pqr_bands).sort((a,b)=>a[0].localeCompare(b[0]));
    mk('pqrC','bar',ent.map(e=>'PQR '+e[0]),[
      {{label:'Win%',data:ent.map(e=>e[1].win),backgroundColor:ent.map(e=>e[1].win>=55?'#1D9E75CC':e[1].win>=48?'#378ADDCC':'#D85A30CC'),yAxisID:'y'}},
      {{label:'Mean%',data:ent.map(e=>e[1].mean),type:'line',borderColor:'#f59e0b',pointRadius:5,backgroundColor:'transparent',yAxisID:'y2'}},
    ],{{y2:true,y:{{min:35,max:75}}}});
  }}
  if(A.panic_vs_normal){{
    const pn=A.panic_vs_normal;
    mk('pvnC','bar',['正常模式','恐慌模式'],[
      {{label:'Win%',data:[pn['Normal']?pn['Normal'].win:0,pn['Panic']?pn['Panic'].win:0],backgroundColor:['#378ADDCC','#f97316CC'],yAxisID:'y'}},
      {{label:'Mean%',data:[pn['Normal']?pn['Normal'].mean:0,pn['Panic']?pn['Panic'].mean:0],type:'line',borderColor:'#1D9E75',pointRadius:6,backgroundColor:'transparent',yAxisID:'y2'}},
    ],{{y2:true,y:{{min:35,max:65}}}});
  }}
  if(A.monthly){{
    const mns=Object.keys(A.monthly);
    const ws=mns.map(m=>A.monthly[m].win);
    mk('monC','bar',mns,[{{label:'Win%',data:ws,backgroundColor:ws.map(w=>w>=52?'#1D9E75CC':w>=47?'#378ADDCC':'#D85A30CC')}}],{{y:{{min:38,max:65}}}});
  }}
  if(A.vix_regime){{
    const regs=['calm','elevated','fear','panic'];
    const wins=regs.map(r=>A.vix_regime[r]?A.vix_regime[r].win:null);
    mk('vixC','bar',['平靜<15','偏高15-20','恐懼20-25','恐慌>25'],[
      {{label:'Win%',data:wins,backgroundColor:wins.map(w=>w===null?'#1e293b':w>=50?'#1D9E75CC':w>=47?'#378ADDCC':'#D85A30CC'),yAxisID:'y'}},
      {{label:'Mean%',data:regs.map(r=>A.vix_regime[r]?A.vix_regime[r].mean:null),type:'line',borderColor:'#f59e0b',pointRadius:5,backgroundColor:'transparent',yAxisID:'y2'}},
    ],{{y2:true,y:{{min:38,max:58}}}});
  }}
  if(A.by_sector){{
    const ent=Object.entries(A.by_sector).filter(([,v])=>v.n>=5).sort((a,b)=>b[1].win-a[1].win);
    mk('secC','bar',ent.map(e=>e[0]),[{{label:'Win%',data:ent.map(e=>e[1].win),
      backgroundColor:ent.map(e=>e[1].win>=52?'#1D9E75CC':e[1].win>=48?'#378ADDCC':'#D85A30CC')}}],
      {{extra:{{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},
        scales:{{x:{{min:0,max:80,ticks:{{color:tc,font:{{size:10}},callback:v=>v+'%'}},grid:{{color:gc}}}},y:{{ticks:{{color:tc,font:{{size:9}}}},grid:{{color:gc}}}}}}}}}});
  }}
  if(A.by_reason){{
    const ent=Object.entries(A.by_reason);
    mk('rsC','bar',ent.map(e=>e[0]),[{{label:'Win%',data:ent.map(e=>e[1].win),backgroundColor:ent.map(e=>e[1].win>=50?'#1D9E75CC':e[1].win>=40?'#378ADDCC':'#D85A30CC')}}],{{y:{{min:0,max:110}}}});
  }}
  const ins=[];
  if(A.overall){{ins.push({{color:'#22c55e',text:`V3.10 整體：N=${{A.overall.n}}，勝率 ${{A.overall.win}}%，均值 ${{A.overall.mean>=0?'+':''}}${{A.overall.mean}}%，PF=${{A.overall.pf||'-'}} — 基於 20 年月份過濾修正後結果`}});}}
  if(A.pqr_bands){{
    const best=Object.entries(A.pqr_bands).sort((a,b)=>b[1].win-a[1].win)[0];
    if(best)ins.push({{color:'#22d3ee',text:`最佳 PQR 帶 (${{best[0]}})：N=${{best[1].n}}，勝率 ${{best[1].win}}%，均值 ${{best[1].mean>=0?'+':''}}${{best[1].mean}}%，PF=${{best[1].pf}}`}});
  }}
  const ib=document.getElementById('ins-boxes');
  ib.innerHTML=ins.map(i=>`<div style="background:#0f172a;border-left:3px solid ${{i.color}};border-radius:0 8px 8px 0;padding:10px 14px;font-size:12.5px;color:#e2e8f0;line-height:1.6">${{i.text}}</div>`).join('');
}}

window.onload=()=>{{
  sb('pqr');loadContent('SPY');ba();
  const PM={{6:'Jun(PF=0.97)',7:'Jul(PF=1.05)',9:'Sep(PF=0.89)'}};
  const m=new Date().getMonth()+1;
  if(PM[m]){{
    document.getElementById('pm-banner').style.display='flex';
    document.getElementById('pm-text').innerText=PM[m]+' — ';
  }}
}};
function openLbox(s){{document.getElementById('lbox-img').src=s;document.getElementById('lbox').classList.add('on');}}
function closeLbox(){{document.getElementById('lbox').classList.remove('on');document.getElementById('lbox-img').src='';}}
document.addEventListener('keydown',e=>{{if(e.key==='Escape')closeLbox();}});
</script>
</div>
</body>
</html>"""

with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as _f:
    _f.write(html)

# =============================================================================
# MODULE 8 — Save + ZIP
# =============================================================================
print("⏳ [8/8] 儲存腳本並打包...")

_dest = os.path.join(OUTPUT_DIR, "Quant_Master_V3_13.py")
try:
    with open(__file__, 'r', encoding='utf-8') as sf:
        with open(_dest, 'w', encoding='utf-8') as df: df.write(sf.read())
except (NameError, FileNotFoundError):
    with open(_dest, 'w', encoding='utf-8') as df:
        df.write(f"# Quant Master V3.10\n# Generated: {timestamp}\n# File > Download .ipynb\n")

shutil.make_archive(OUTPUT_DIR, 'zip', OUTPUT_DIR)

_an  = sum(1 for d in etf_js_data if '🔥' in d['status'])
_wn  = sum(1 for d in etf_js_data if '觀察' in d['status'])
_hcn = sum(1 for d in etf_js_data if d.get('is_high_conviction'))
_pn  = sum(1 for d in etf_js_data if d.get('in_panic_now') and d['patterns'])
_ln  = sum(1 for d in etf_js_data if d.get('is_late_join') and '🔥' in d['status'])
_crash = "💥 崩潰保護啟動" if is_curr_crash else "✅ 正常"

print(f"\n🎉 V3.13 建置完成！輸出: {OUTPUT_DIR}.zip")
print(f"   📈 股票池: {len([t for t in ALL_TICKERS if t!='^VIX'])} 支")
print(f"   🔥 Active: {_an}  |  ⚡ HC: {_hcn}  |  🚨 Panic: {_pn}  |  ⚠️ 延遲: {_ln}")
print(f"   📊 預設#{TOP10_PRESET}: PQRv={PQR_VCP_MIN}·TP×{_VCP_TP}·TS={TIME_STOP_DAYS}d·ATR×{ATR_STOP_LOSS_MULT}")
print(f"   💥 崩潰保護: {_crash} (SPY月跌 {curr_spy_mret*100:.1f}% vs 閾值 {CRASH_PROTECT_SPY_MONTHLY*100:.0f}%)")
print(f"   ❌ 移除: P7_VolAccum (20yr PF=1.16)")
print(f"   ✅ P6 恐慌模式專用 (穩定性測試: PF=1.605 vs 1.420)")
print(f"   📅  毒月提醒模式: Jun/Jul/Sep 在 Dashboard 顯示警告 (不封鎖)")
print(f"   📁 輸出: HMI_Dashboard.html | trade_records_enriched.csv | pattern_signals.csv")

try:
    from google.colab import files
    files.download(f"{OUTPUT_DIR}.zip")
except Exception: pass
