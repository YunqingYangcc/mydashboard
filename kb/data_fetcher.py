"""行情数据获取模块 - baostock(A股/ETF) + Yahoo Chart API(美股)

📋 Prompt绑定: prompts/数据导入.md
修改本文件前必须先阅读该 prompt，确保改动符合数据源规则和存储结构定义。
"""
import time
import logging
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import requests

from kb.config import ensure_directories
from kb.market_constants import TARGET_STOCKS, SYMBOL_MAP

logger = logging.getLogger(__name__)


# ===== A股/ETF: baostock =====

def _bs_symbol(symbol: str, market: str) -> str:
    """将6位代码转为 baostock 格式: sh.600000 / sz.000001"""
    if '.' in symbol:
        return symbol
    if market == 'ETF':
        # ETF根据代码首位判断交易所: 5开头=沪, 1开头=深
        prefix = 'sh' if symbol.startswith('5') else 'sz'
    elif symbol.startswith(('6', '9')):
        prefix = 'sh'
    else:
        prefix = 'sz'
    return f'{prefix}.{symbol}'


def fetch_a_share_daily(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """获取A股日线行情(后复权)

    Args:
        symbol: A股6位代码 (如 688041)
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD
    """
    return _fetch_baostock(symbol, start_date, end_date, market='A股')


def fetch_etf_daily(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """获取ETF日线行情(后复权)

    Args:
        symbol: ETF代码 (如 512460)
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD
    """
    return _fetch_baostock(symbol, start_date, end_date, market='ETF')


def _fetch_baostock(symbol: str, start_date: str, end_date: str, market: str = 'A股') -> pd.DataFrame:
    """通过 baostock 获取 A股/ETF 日线数据"""
    try:
        import baostock as bs
    except ImportError:
        logger.error("baostock 未安装，请 pip install baostock")
        return pd.DataFrame()

    bs_symbol = _bs_symbol(symbol, market)
    start_fmt = f'{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}'
    end_fmt = f'{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}'

    lg = bs.login()
    if lg.error_code != '0':
        logger.error(f"baostock login failed: {lg.error_msg}")
        return pd.DataFrame()

    try:
        rs = bs.query_history_k_data_plus(
            bs_symbol,
            'date,open,high,low,close,volume,amount,turn,pctChg',
            start_date=start_fmt,
            end_date=end_fmt,
            frequency='d',
            adjustflag='2'  # 2=后复权
        )

        if rs.error_code != '0':
            logger.error(f"baostock query {symbol} failed: {rs.error_msg}")
            return pd.DataFrame()

        data = []
        while rs.next():
            data.append(rs.get_row_data())

        if not data:
            logger.warning(f"baostock {symbol} 无数据返回")
            return pd.DataFrame()

        col_map = {
            'date': 'trade_date',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume',
            'amount': 'turnover',
            'turn': 'turnover_rate',
            'pctChg': 'change_pct',
        }
        df = pd.DataFrame(data, columns=['trade_date', 'open', 'high', 'low', 'close', 'volume', 'turnover', 'turnover_rate', 'change_pct'])

        for col in ['open', 'high', 'low', 'close', 'volume', 'turnover', 'change_pct']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # 过滤掉空行
        df = df.dropna(subset=['close'])
        df = df[df['close'] > 0]

        result_cols = ['trade_date', 'open', 'high', 'low', 'close', 'volume', 'turnover', 'change_pct']
        return df[result_cols]

    except Exception as e:
        logger.error(f"baostock {symbol} 异常: {e}")
        return pd.DataFrame()
    finally:
        bs.logout()


# ===== 美股: AKShare 批量获取 + Yahoo Finance Chart API =====

# Yahoo Finance 会话（懒初始化，复用 cookie）
_yahoo_session = None


def _get_yahoo_session() -> requests.Session:
    """获取带 cookie 的 Yahoo Finance 会话（query2 域名 + 先访问页面获取 cookie）"""
    global _yahoo_session
    if _yahoo_session is not None:
        return _yahoo_session

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Referer': 'https://finance.yahoo.com/',
    })

    # 先访问 Yahoo Finance 页面获取 cookie（绕过 401/429 限制）
    try:
        session.get('https://finance.yahoo.com/quote/NVDA/', timeout=15)
        time.sleep(0.5)
    except Exception as e:
        logger.warning(f"Yahoo cookie 获取失败: {e}")

    _yahoo_session = session
    return session


def fetch_us_daily_batch_akshare(symbols: list, days: int = 120) -> dict:
    """使用 AKShare 批量获取美股历史数据（优先方案，避免逐个请求限频）
    
    Args:
        symbols: 美股Ticker列表 (如 ['NVDA', 'AMD', 'AVGO'])
        days: 获取最近N天的数据
    
    Returns:
        dict: {symbol: DataFrame}
    """
    try:
        import akshare as ak
        logger.info(f"使用 AKShare 批量获取 {len(symbols)} 只美股数据...")
        
        # AKShare 提供的美股历史数据接口
        results = {}
        for symbol in symbols:
            try:
                # 获取美股历史行情
                df = ak.stock_us_hist(symbol=symbol, period="daily", adjust="qfq")
                
                if df is None or df.empty:
                    logger.warning(f"AKShare {symbol} 无数据")
                    continue
                
                # 字段映射
                col_map = {
                    '日期': 'trade_date',
                    '开盘': 'open',
                    '最高': 'high',
                    '最低': 'low',
                    '收盘': 'close',
                    '成交量': 'volume',
                    '成交额': 'turnover',
                    '涨跌幅': 'change_pct'
                }
                
                df = df.rename(columns=col_map)
                
                # 确保日期格式正确
                df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y-%m-%d')
                
                # 数值转换
                for col in ['open', 'high', 'low', 'close', 'volume', 'turnover', 'change_pct']:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # 过滤掉无效数据
                df = df.dropna(subset=['close'])
                df = df[df['close'] > 0]
                
                # 按日期排序并限制天数
                df = df.sort_values('trade_date').tail(days).reset_index(drop=True)
                
                # 选择需要的列
                result_cols = ['trade_date', 'open', 'high', 'low', 'close', 'volume', 'turnover', 'change_pct']
                available_cols = [c for c in result_cols if c in df.columns]
                results[symbol] = df[available_cols]
                
                logger.info(f"  AKShare {symbol}: 获取 {len(results[symbol])} 行数据")
                
            except Exception as e:
                logger.warning(f"AKShare {symbol} 获取失败: {e}")
                continue
        
        logger.info(f"AKShare 批量获取完成: {len(results)}/{len(symbols)} 成功")
        return results
        
    except ImportError:
        logger.error("akshare 未安装，请 pip install akshare")
        return {}
    except Exception as e:
        logger.error(f"AKShare 批量获取异常: {e}")
        return {}


# ============================================================================
# 以下函数已弃用 - 不稳定的数据源（保留供参考）
# ============================================================================

# def fetch_us_daily(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
#     """获取美股日线行情数据 (Yahoo Finance Chart API - query2)
# 
#     ⚠️ 已弃用：频繁403限频，不稳定
#     """
#     # ... 原有代码 ...
#
#
# def _fetch_yfinance_backup(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
#     """yfinance 备用数据源
# 
#     ⚠️ 已弃用：也会被限频
#     """
#     # ... 原有代码 ...
#
#
# def fetch_fmp(symbol: str, api_key: str = None, days: int = 100) -> pd.DataFrame:
#     """使用 FMP API 获取美股历史数据
# 
#     ⚠️ 已弃用：当前返回403错误
#     """
#     # ... 原有代码 ...
#
#
# def fetch_us_daily_batch_akshare(symbols: list, days: int = 120) -> dict:
#     """使用 AKShare 批量获取美股历史数据
# 
#     ⚠️ 已弃用：网络连接不稳定
#     """
#     # ... 原有代码 ...

# ============================================================================
# 稳定数据源
# ============================================================================


def fetch_alpha_vantage(symbol: str, api_key: str = None) -> pd.DataFrame:
    """使用 Alpha Vantage API 获取美股历史数据
    
    Args:
        symbol: 美股Ticker (如 NVDA)
        api_key: Alpha Vantage API Key，默认从环境变量读取
    
    Returns:
        DataFrame with OHLCV data
    """
    import os
    
    if not api_key:
        api_key = os.getenv('ALPHAVANTAGE_API_KEY', '')
    
    if not api_key:
        logger.warning("Alpha Vantage API Key 未配置，跳过")
        return pd.DataFrame()
    
    try:
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "apikey": api_key,
            "outputsize": "compact"  # 最近100天数据
        }
        
        resp = requests.get(url, params=params, timeout=15)
        
        if resp.status_code != 200:
            logger.error(f"Alpha Vantage {symbol} HTTP {resp.status_code}")
            logger.error(f"响应内容: {resp.text[:200]}")
            return pd.DataFrame()
        
        data = resp.json()
        
        # 检查是否有错误信息
        if "Error Message" in data:
            logger.error(f"Alpha Vantage {symbol}: {data['Error Message']}")
            return pd.DataFrame()
        
        if "Note" in data:
            logger.warning(f"Alpha Vantage {symbol}: {data['Note']}")
            return pd.DataFrame()
        
        # 打印完整响应用于调试（仅前500字符）
        logger.debug(f"Alpha Vantage {symbol} 响应: {str(data)[:500]}")
        
        # 解析时间序列数据
        time_series = data.get('Time Series (Daily)', {})
        
        if not time_series:
            logger.warning(f"Alpha Vantage {symbol}: 无数据返回")
            return pd.DataFrame()
        
        # 转换为DataFrame
        records = []
        for date_str, values in time_series.items():
            records.append({
                'trade_date': date_str,
                'open': float(values['1. open']),
                'high': float(values['2. high']),
                'low': float(values['3. low']),
                'close': float(values['4. close']),
                'volume': int(values['5. volume'])
            })
        
        df = pd.DataFrame(records)
        df = df.sort_values('trade_date').reset_index(drop=True)
        
        # 计算衍生指标
        df['change_pct'] = df['close'].pct_change() * 100
        df['turnover'] = df['volume'] * df['close']
        
        return df
    
    except Exception as e:
        logger.error(f"Alpha Vantage {symbol} 异常: {e}")
        return pd.DataFrame()


# ===== 存储 =====

def _fetch_yfinance_backup(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """yfinance 备用数据源（当 Yahoo API 彻底失效时启用）"""
    try:
        import yfinance as yf
        start_fmt = start_date if '-' in start_date else f'{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}'
        end_fmt = end_date if '-' in end_date else f'{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}'
        
        ticker = yf.Ticker(symbol)
        hist = ticker.history(start=start_fmt, end=end_fmt)
        
        if hist.empty:
            return pd.DataFrame()
            
        df = pd.DataFrame()
        df['trade_date'] = hist.index.strftime('%Y-%m-%d')
        df['open'] = hist['Open'].values
        df['high'] = hist['High'].values
        df['low'] = hist['Low'].values
        df['close'] = hist['Close'].values
        df['volume'] = hist['Volume'].values
        df['turnover'] = df['close'] * df['volume']
        df['change_pct'] = df['close'].pct_change() * 100
        
        logger.info(f"yfinance 成功获取 {symbol} {len(df)} 行数据")
        return df
    except Exception as e:
        logger.error(f"yfinance 获取 {symbol} 失败: {e}")
        return pd.DataFrame()


def fetch_alpha_vantage(symbol: str, api_key: str = None) -> pd.DataFrame:
    """使用 Alpha Vantage API 获取美股历史数据
    
    Args:
        symbol: 美股Ticker (如 NVDA)
        api_key: Alpha Vantage API Key，默认从环境变量读取
    
    Returns:
        DataFrame with OHLCV data
    """
    import os
    
    if not api_key:
        api_key = os.getenv('ALPHAVANTAGE_API_KEY', '')
    
    if not api_key:
        logger.warning("Alpha Vantage API Key 未配置，跳过")
        return pd.DataFrame()
    
    try:
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "apikey": api_key,
            "outputsize": "compact"  # 最近100天数据
        }
        
        resp = requests.get(url, params=params, timeout=15)
        
        if resp.status_code != 200:
            logger.error(f"Alpha Vantage {symbol} HTTP {resp.status_code}")
            return pd.DataFrame()
        
        data = resp.json()
        
        # 检查是否有错误信息
        if "Error Message" in data:
            logger.error(f"Alpha Vantage {symbol} 错误: {data['Error Message']}")
            return pd.DataFrame()
        
        if "Note" in data:
            logger.warning(f"Alpha Vantage {symbol} 限频: {data['Note']}")
            return pd.DataFrame()
        
        # 解析数据
        time_series = data.get('Time Series (Daily)', {})
        if not time_series:
            logger.warning(f"Alpha Vantage {symbol} 无数据")
            return pd.DataFrame()
        
        records = []
        for date_str, values in time_series.items():
            records.append({
                'trade_date': date_str,
                'open': float(values['1. open']),
                'high': float(values['2. high']),
                'low': float(values['3. low']),
                'close': float(values['4. close']),
                'volume': int(values['5. volume'])
            })
        
        df = pd.DataFrame(records)
        df = df.sort_values('trade_date').reset_index(drop=True)
        
        # 计算衍生指标
        df['turnover'] = df['close'] * df['volume']
        df['change_pct'] = df['close'].pct_change() * 100
        
        logger.info(f"Alpha Vantage 成功获取 {symbol} {len(df)} 行数据")
        return df
        
    except Exception as e:
        logger.error(f"Alpha Vantage {symbol} 异常: {e}")
        return pd.DataFrame()


def fetch_fmp(symbol: str, api_key: str = None, days: int = 100) -> pd.DataFrame:
    """使用 Financial Modeling Prep API 获取美股历史数据
    
    Args:
        symbol: 美股Ticker (如 NVDA)
        api_key: FMP API Key，默认从环境变量读取
        days: 获取天数，默认100天
    
    Returns:
        DataFrame with OHLCV data
    """
    import os
    
    if not api_key:
        api_key = os.getenv('FMP_API_KEY', '')
    
    if not api_key:
        logger.warning("FMP API Key 未配置，跳过")
        return pd.DataFrame()
    
    try:
        # FMP API endpoint
        url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}"
        params = {
            "apikey": api_key,
            "timeseries": days
        }
        
        resp = requests.get(url, params=params, timeout=15)
        
        if resp.status_code != 200:
            logger.error(f"FMP {symbol} HTTP {resp.status_code}")
            return pd.DataFrame()
        
        data = resp.json()
        
        # 检查是否有错误
        if "Error Message" in data:
            logger.error(f"FMP {symbol} 错误: {data['Error Message']}")
            return pd.DataFrame()
        
        historical = data.get('historical', [])
        if not historical:
            logger.warning(f"FMP {symbol} 无数据")
            return pd.DataFrame()
        
        # 解析数据（FMP返回的是从新到旧，需要反转）
        records = []
        for item in historical:
            records.append({
                'trade_date': item['date'],
                'open': float(item['open']),
                'high': float(item['high']),
                'low': float(item['low']),
                'close': float(item['close']),
                'volume': int(item['volume'])
            })
        
        df = pd.DataFrame(records)
        df = df.sort_values('trade_date').reset_index(drop=True)
        
        # 计算衍生指标
        df['turnover'] = df['close'] * df['volume']
        df['change_pct'] = df['close'].pct_change() * 100
        
        logger.info(f"FMP 成功获取 {symbol} {len(df)} 行数据")
        return df
        
    except Exception as e:
        logger.error(f"FMP {symbol} 异常: {e}")
        return pd.DataFrame()


def store_quotes_to_db(df: pd.DataFrame, symbol: str, market: str, chain: str) -> int:
    """将行情数据存入 stock_daily_quotes 表

    Returns:
        插入的行数
    """
    if df is None or df.empty:
        return 0

    from kb.storage import get_knowledge_db
    from kb.utils import now_iso

    count = 0

    with get_knowledge_db() as conn:
        for _, row in df.iterrows():
            try:
                trade_date = str(row.get("trade_date", ""))
                if not trade_date:
                    continue

                conn.execute("""
                    INSERT OR REPLACE INTO stock_daily_quotes
                    (symbol, trade_date, open, high, low, close, volume, turnover, change_pct, market, industry_chain)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    symbol,
                    trade_date,
                    float(row.get("open", 0) or 0),
                    float(row.get("high", 0) or 0),
                    float(row.get("low", 0) or 0),
                    float(row.get("close", 0) or 0),
                    float(row.get("volume", 0) or 0),
                    float(row.get("turnover", 0) or 0),
                    float(row.get("change_pct", 0) or 0) if pd.notna(row.get("change_pct")) else None,
                    market,
                    chain,
                ))
                count += 1
            except Exception as e:
                logger.warning(f"存储 {symbol} {trade_date} 行情失败: {e}")

    return count


def get_quotes_from_db(symbol: str, days: int = 120) -> pd.DataFrame:
    """从数据库读取行情数据"""
    from kb.storage import get_knowledge_db

    with get_knowledge_db() as conn:
        rows = conn.execute("""
            SELECT * FROM stock_daily_quotes
            WHERE symbol = ?
            ORDER BY trade_date DESC
            LIMIT ?
        """, (symbol, days)).fetchall()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df = df.sort_values("trade_date").reset_index(drop=True)

    for col in ["open", "high", "low", "close", "volume", "turnover", "change_pct"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def batch_fetch_and_store(days: int = 120, sleep_interval: float = 5.0, force_full: bool = False) -> dict:
    """批量获取所有标的的历史行情并存入数据库（智能增量 + 交叉验证模式）

    数据源:
    - A股/ETF: baostock (免费稳定)
    - 美股: Yahoo Finance Chart API / yfinance (备用)

    Args:
        days: 获取最近N天的数据（首次导入或数据不足时使用）
        sleep_interval: 美股每次请求间隔(秒)，默认5秒平衡安全性和效率
        force_full: 是否强制全量拉取（忽略已有数据）

    Returns:
        dict: {symbol: rows_fetched}
    """
    from kb.storage import get_knowledge_db
    from kb.cross_validator import cross_validate_production
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    results = {}
    
    # 1. 执行多数据源交叉验证 (V2.0)
    logger.info("正在执行多数据源交叉验证...")
    validation_report = cross_validate_production()
    if validation_report:
        anomalies = [k for k, v in validation_report.items() if '异常' in v.get('status', '')]
        if anomalies:
            logger.warning(f"发现 {len(anomalies)} 个数据分歧标的: {anomalies[:5]}...")
    
    # 按市场分组，先处理A股/ETF，最后处理美股
    a_shares_targets = [t for t in TARGET_STOCKS if t["market"] in ("A股", "ETF")]
    us_shares_targets = [t for t in TARGET_STOCKS if t["market"] == "美股"]
    
    all_targets = a_shares_targets + us_shares_targets
    
    for target in all_targets:
        symbol = target["symbol"]
        market = target["market"]
        chain = target["chain"]
        name = target["name"]
        
        logger.info(f"获取 {name}({symbol}) 行情...")
        
        # 查询数据库中该标的的最新日期和数据量
        with get_knowledge_db() as conn:
            latest_row = conn.execute(
                "SELECT MAX(trade_date) as max_date, COUNT(*) as cnt FROM stock_daily_quotes WHERE symbol = ?",
                (symbol,)
            ).fetchone()
        
        latest_date_str = latest_row["max_date"] if latest_row else None
        data_count = latest_row["cnt"] if latest_row else 0
        
        # 决策：是否需要全量拉取
        need_full_fetch = force_full  # 如果强制全量，则直接设置为True
        
        if not need_full_fetch:
            if not latest_date_str or data_count == 0:
                # 情况1: 无数据，首次导入
                fetch_start_date = start_date
                need_full_fetch = True
                logger.info(f"  {name}: 首次导入，全量拉取 {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
            
            elif data_count < days * 0.5:
                # 情况2: 数据量不足一半，可能数据不完整，全量拉取
                fetch_start_date = start_date
                need_full_fetch = True
                logger.info(f"  {name}: 数据不足({data_count}行 < {int(days*0.5)}行)，全量拉取")
            
            else:
                # 情况3: 增量更新，只拉取最新日期之后的数据
                latest_date = datetime.strptime(latest_date_str, "%Y-%m-%d")
                
                # 如果最新数据已经是今天或昨天，跳过
                if latest_date >= end_date - timedelta(days=1):
                    logger.info(f"  {name}: 数据已是最新({latest_date_str})，跳过")
                    results[symbol] = 0
                    continue
                
                # 从最新日期的下一天开始拉取
                fetch_start_date = latest_date + timedelta(days=1)
                
                # 检查是否有数据缺口（最新日期距离今天超过7天）
                days_gap = (end_date - latest_date).days
                if days_gap > 7:
                    logger.warning(f"  {name}: 数据缺口{days_gap}天，建议检查数据源")
                
                logger.info(f"  {name}: 增量更新 {fetch_start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
        else:
            # 强制全量模式
            fetch_start_date = start_date
            logger.info(f"  {name}: [强制全量] 拉取 {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
        
        # 执行数据获取
        fetch_start_str = fetch_start_date.strftime("%Y%m%d")
        fetch_end_str = end_date.strftime("%Y%m%d")
        
        df = pd.DataFrame()
        try:
            if market in ("A股", "ETF"):
                df = _fetch_baostock(symbol, fetch_start_str, fetch_end_str, market=market)
            elif market == "美股":
                # 优先使用 Alpha Vantage（稳定可靠）
                logger.info(f"  {name}: 使用 Alpha Vantage API...")
                df = fetch_alpha_vantage(symbol, api_key=None)
                
                if df.empty:
                    # Alpha Vantage 失败，降级到 Yahoo API
                    logger.warning(f"  {name}: Alpha Vantage 失败，尝试 Yahoo API...")
                    df = fetch_us_daily(symbol, fetch_start_str, fetch_end_str)
                    # 美股API限频保护：随机化间隔时间 (7-9秒)
                    import random
                    actual_sleep = sleep_interval + random.uniform(2, 4)
                    time.sleep(max(6, actual_sleep))
                else:
                    # Alpha Vantage 成功，间隔10-12秒避免限频
                    import random
                    time.sleep(10 + random.uniform(0, 2))
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "Too Many Requests" in error_msg:
                logger.error(f"  {name}: API限频，等待15秒后重试...")
                time.sleep(15)
                # Alpha Vantage 重试一次
                try:
                    if market == "美股":
                        df = fetch_alpha_vantage(symbol, api_key=None)
                        if not df.empty:
                            import random
                            time.sleep(10 + random.uniform(0, 2))
                except Exception as retry_e:
                    logger.error(f"  {name}: 重试失败 - {retry_e}")
                    results[symbol] = 0
                    continue
            else:
                logger.error(f"  {name}: 获取失败 - {e}")
                results[symbol] = 0
                continue
        
        if not df.empty:
            # 数据验证
            validation = validate_data_quality(symbol, df)
            
            if not validation['passed']:
                logger.error(f"  {name}: 数据验证失败 - {'; '.join(validation['errors'])}")
                results[symbol] = 0
                continue
            
            if validation['warnings']:
                for warning in validation['warnings']:
                    logger.warning(f"  {name}: {warning}")
            
            count = store_quotes_to_db(df, symbol, market, chain)
            results[symbol] = count
            mode = "全量" if need_full_fetch else "增量"
            logger.info(f"  {name}: {mode}获取 {len(df)} 行，入库 {count} 行")
        else:
            results[symbol] = 0
            logger.warning(f"  {name}: 无新数据")
    
    return results


def fetch_single_latest(symbol: str, days: int = 5) -> int:
    """获取单只标的的最新行情（增量更新）"""
    target = SYMBOL_MAP.get(symbol)
    if not target:
        logger.error(f"未知标的: {symbol}")
        return 0

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")

    market = target["market"]
    chain = target["chain"]

    if market in ("A股", "ETF"):
        df = _fetch_baostock(symbol, start_str, end_str, market=market)
    elif market == "美股":
        # 只使用 Alpha Vantage（稳定可靠）
        df = fetch_alpha_vantage(symbol, api_key=None)
    else:
        df = pd.DataFrame()

    if not df.empty:
        return store_quotes_to_db(df, symbol, market, chain)
    return 0


def get_db_status() -> dict:
    """获取数据库中各标的的数据状态
    
    Returns:
        dict: {symbol: {latest_date, data_count, market, name}}
    """
    from kb.storage import get_knowledge_db
    
    status = {}
    
    with get_knowledge_db() as conn:
        for target in TARGET_STOCKS:
            symbol = target["symbol"]
            row = conn.execute(
                """
                SELECT MAX(trade_date) as latest_date, COUNT(*) as data_count
                FROM stock_daily_quotes
                WHERE symbol = ?
                """,
                (symbol,)
            ).fetchone()
            
            status[symbol] = {
                "name": target["name"],
                "market": target["market"],
                "latest_date": row["latest_date"] if row else None,
                "data_count": row["data_count"] if row else 0,
            }
    
    return status


def print_db_status():
    """打印数据库状态摘要"""
    status = get_db_status()
    
    print("\n📊 数据库状态:")
    print("-" * 70)
    print(f"{'标的':<12} {'名称':<15} {'市场':<6} {'最新日期':<12} {'数据量':<8}")
    print("-" * 70)
    
    for symbol, info in sorted(status.items()):
        latest = info["latest_date"] or "无数据"
        count = info["data_count"]
        status_icon = "✅" if count > 100 else "⚠️" if count > 0 else "❌"
        
        print(f"{status_icon} {symbol:<10} {info['name']:<15} {info['market']:<6} {latest:<12} {count:<8}")
    
    total_symbols = len(status)
    has_data = sum(1 for s in status.values() if s["data_count"] > 0)
    total_rows = sum(s["data_count"] for s in status.values())
    
    print("-" * 70)
    print(f"总计: {has_data}/{total_symbols} 个标的数据 | 共 {total_rows} 行")
    print()


def validate_data_quality(symbol: str, df: pd.DataFrame) -> dict:
    """验证数据质量，返回验证报告
    
    Args:
        symbol: 标的代码
        df: 行情数据 DataFrame
    
    Returns:
        dict: 验证结果 {
            'passed': bool,
            'warnings': list,
            'errors': list,
            'metrics': dict
        }
    """
    warnings = []
    errors = []
    
    if df is None or df.empty:
        return {
            'passed': False,
            'warnings': [],
            'errors': ['数据为空'],
            'metrics': {}
        }
    
    # Level 2: 数据质量验证
    
    # 1. 数值范围检查
    if (df['close'] <= 0).any():
        errors.append('存在收盘价<=0的异常数据')
    
    if (df['volume'] < 0).any():
        errors.append('存在成交量<0的异常数据')
    
    # 2. OHLC逻辑检查
    if (df['high'] < df['low']).any():
        errors.append('存在最高价<最低价的异常数据')
    
    if (df['high'] < df['close']).any():
        warnings.append('部分日期最高价<收盘价（可能数据有误）')
    
    if (df['low'] > df['open']).any():
        warnings.append('部分日期最低价>开盘价（可能数据有误）')
    
    # 3. 涨跌幅合理性检查（A股涨跌停10%，美股无限制但通常<20%）
    if 'change_pct' in df.columns:
        extreme_changes = df[df['change_pct'].abs() > 20]
        if len(extreme_changes) > 0:
            warnings.append(f"存在{len(extreme_changes)}天涨跌幅超过20%")
    
    # Level 3: 业务逻辑验证
    
    # 4. 数据量检查
    if len(df) < 60:
        warnings.append(f'数据量不足: {len(df)}行 < 60行')
    
    # 5. 日期连续性检查
    if len(df) > 1:
        df_sorted = df.sort_values('trade_date')
        dates = pd.to_datetime(df_sorted['trade_date'])
        date_diffs = dates.diff().dt.days
        # 找出超过3天的缺口（周末+节假日最多3天）
        gaps = date_diffs[date_diffs > 3]
        if len(gaps) > 0:
            warnings.append(f'存在{len(gaps)}个数据缺口（>3天）')
    
    # 计算质量指标
    metrics = {
        'total_rows': len(df),
        'date_range': f"{df['trade_date'].min()} ~ {df['trade_date'].max()}" if len(df) > 0 else "N/A",
        'avg_volume': float(df['volume'].mean()) if 'volume' in df.columns else 0,
        'avg_close': float(df['close'].mean()) if 'close' in df.columns else 0,
    }
    
    passed = len(errors) == 0
    
    return {
        'passed': passed,
        'warnings': warnings,
        'errors': errors,
        'metrics': metrics
    }
