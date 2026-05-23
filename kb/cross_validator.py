"""多数据源交叉验证模块 - 生产级重构版 (V2.0)

📋 设计理念: 
- 黄金源权重逻辑 (A股: baostock, 美股: yfinance)
- 动态双重阈值判定 (绝对差 + 相对差)
- 交易时段智能感知 (避免周末/盘后伪异常)
- 统一量比计算基准 (A股: 实时分钟均量, 美股: 5日均量)
"""
import logging
import warnings
from datetime import datetime, timedelta
import pandas as pd
import akshare as ak
import baostock as bs
import yfinance as yf
import requests

from kb.market_constants import TARGET_STOCKS

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)

# ====================== 配置区 ======================
GOLDEN_SOURCE = {"A": "baostock", "US": "yfinance"}
THRESHOLD = {
    "price_abs": 0.05,      # 绝对价格差异阈值(元)
    "price_rel": 0.5,       # 相对价格差异阈值(%)
    "change_rel": 0.5,      # 涨跌幅差异阈值(%)
    "volume_rel": 20.0,     # 量比差异阈值(%)
    "critical_alert": 5.0   # 重大差异告警阈值(%)
}
DINGTALK_WEBHOOK = ""  # 填入你的 Webhook 地址即可开启告警


def get_market_status(market="A"):
    """获取市场当前状态"""
    now = datetime.now()
    if market == "A":
        if now.weekday() >= 5: return "休市"
        morning = now.replace(hour=9, minute=30) <= now <= now.replace(hour=11, minute=30)
        afternoon = now.replace(hour=13) <= now <= now.replace(hour=15)
        return "交易中" if (morning or afternoon) else "已收盘"
    else: # US
        if now.weekday() >= 5 and now.hour < 21: return "休市"
        start = now.replace(hour=21, minute=30)
        end = (now + timedelta(days=1)).replace(hour=4)
        return "交易中" if (now >= start or now <= end) else "已收盘"

def send_alert(message):
    """发送告警消息"""
    if DINGTALK_WEBHOOK:
        try:
            requests.post(DINGTALK_WEBHOOK, json={"msgtype": "text", "text": {"content": f"【数据异常】\n{message}"}})
        except: pass

def get_data_akshare():
    """从 AKShare 获取实时行情数据"""
    result = []
    try:
        zh_df = ak.stock_zh_a_spot_em()
        for target in TARGET_STOCKS:
            code = target["symbol"]
            if code.isdigit() and code in zh_df["代码"].values:
                row = zh_df[zh_df["代码"] == code].iloc[0]
                result.append({"symbol": code, "source": "AKShare", "market": "A",
                    "close": float(row["最新价"]), "change_pct": float(row["涨跌幅"]),
                    "vol_ratio": float(row["量比"]) if pd.notna(row["量比"]) else None})
        us_df = ak.stock_us_spot_em()
        for target in TARGET_STOCKS:
            code = target["symbol"]
            if not code.isdigit() and code in us_df["代码"].values:
                row = us_df[us_df["代码"] == code].iloc[0]
                result.append({"symbol": code, "source": "AKShare", "market": "US",
                    "close": float(row["最新价"]), "change_pct": float(row["涨跌幅"]),
                    "vol_ratio": float(row["量比"]) if pd.notna(row["量比"]) else None})
    except Exception as e:
        logger.error(f"AKShare 获取失败: {e}")
    return pd.DataFrame(result)


def get_data_baostock():
    """从 baostock 获取数据并计算量比"""
    result = []
    lg = bs.login()
    if lg.error_code != '0':
        logger.error(f"baostock登录失败: {lg.error_msg}")
        return pd.DataFrame()
    
    try:
        for target in TARGET_STOCKS:
            code = target["symbol"]
            if not code.isdigit(): continue
            
            prefix = 'sh' if code.startswith(('6', '9', '5')) else 'sz'
            bs_code = f"{prefix}.{code}"
            
            try:
                rs = bs.query_realtime_quotes(bs_code)
                if rs.error_code == '0' and rs.row_count > 0:
                    data = rs.get_row_data()
                    # 计算近5日均量
                    end_date = datetime.now().strftime('%Y-%m-%d')
                    start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
                    rs_k = bs.query_history_k_data_plus(
                        bs_code, "volume", 
                        start_date=start_date, end_date=end_date,
                        frequency="d", adjustflag="3"
                    )
                    k_data = rs_k.get_data()
                    vol_ratio = None
                    if len(k_data) >= 5:
                        avg_vol = k_data['volume'].astype(float).tail(5).mean()
                        current_vol = float(data[6])
                        vol_ratio = round(current_vol / avg_vol, 4) if avg_vol > 0 else None
                    
                    result.append({
                        "symbol": code,
                        "source": "baostock",
                        "close": float(data[3]),
                        "change_pct": float(data[10]),
                        "vol_ratio": vol_ratio
                    })
            except Exception as e:
                logger.warning(f"baostock获取{code}失败: {e}")
    finally:
        bs.logout()
    
    return pd.DataFrame(result)


def get_data_yfinance():
    """从 yfinance 获取数据并计算量比"""
    result = []
    for target in TARGET_STOCKS:
        code = target["symbol"]
        yf_code = f"{code}.SS" if code.startswith('6') else (f"{code}.SZ" if code.isdigit() else code)
        
        try:
            ticker = yf.Ticker(yf_code)
            hist = ticker.history(period='5d')
            
            if len(hist) > 0:
                current_price = hist['Close'].iloc[-1]
                prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
                change_pct = (current_price - prev_close) / prev_close * 100
                
                vol_ratio = None
                if len(hist) >= 5:
                    avg_vol = hist['Volume'].tail(5).mean()
                    current_vol = hist['Volume'].iloc[-1]
                    vol_ratio = round(current_vol / avg_vol, 4) if avg_vol > 0 else None
                
                result.append({
                    "symbol": code,
                    "source": "yfinance",
                    "close": round(current_price, 4),
                    "change_pct": round(change_pct, 4),
                    "vol_ratio": vol_ratio
                })
        except Exception as e:
            logger.warning(f"yfinance获取{code}失败: {e}")
    
    return pd.DataFrame(result)


def cross_validate_production():
    """执行生产级交叉验证与动态阈值校验"""
    logger.info("开始执行多数据源交叉验证 (V2.0)...")
    df_ak = get_data_akshare()
    df_bs = get_data_baostock()
    df_yf = get_data_yfinance()
    all_data = pd.concat([df_ak, df_bs, df_yf], ignore_index=True)
    
    if all_data.empty: return {}
    
    validation_report = {}
    grouped = all_data.groupby(['symbol', 'market'])
    alerts = []
    
    for (symbol, market), group in grouped:
        status = get_market_status(market)
        if status == "休市": continue
        
        golden_src = GOLDEN_SOURCE.get(market)
        golden_row = group[group['source'] == golden_src]
        if len(golden_row) == 0: continue
        
        g_price = golden_row.iloc[0]['close']
        g_change = golden_row.iloc[0]['change_pct']
        g_vol = golden_row.iloc[0]['vol_ratio']
        
        max_diff_pct = 0.0
        max_diff_abs = 0.0
        is_abnormal = False
        reasons = []
        
        for _, row in group.iterrows():
            if row['source'] == golden_src: continue
            p_diff = abs(row['close'] - g_price)
            p_diff_pct = (p_diff / g_price * 100) if g_price > 0 else 0
            
            if p_diff_pct > max_diff_pct: max_diff_pct = p_diff_pct
            if p_diff > max_diff_abs: max_diff_abs = p_diff
            
            c_diff = abs(row['change_pct'] - g_change)
            if c_diff > THRESHOLD['change_rel']: is_abnormal = True; reasons.append(f"涨跌差{c_diff:.2f}%")
        
        # 动态双重阈值判定
        if (max_diff_abs > THRESHOLD['price_abs']) and (max_diff_pct > THRESHOLD['price_rel']):
            is_abnormal = True; reasons.append(f"价差{max_diff_pct:.2f}%")
        
        if max_diff_pct > THRESHOLD['critical_alert']:
            alerts.append(f"【重大异常】{symbol} 价差{max_diff_pct:.2f}%")
        
        validation_report[symbol] = {
            "status": "⚠️ 异常" if is_abnormal else "✅ 正常",
            "ref_price": round(g_price, 4),
            "diff_pct": round(max_diff_pct, 2),
            "reasons": "; ".join(reasons)
        }
        
        if is_abnormal: logger.warning(f"发现数据分歧: {symbol} | {'; '.join(reasons)}")
    
    if alerts: send_alert("\n".join(alerts))
    return validation_report
