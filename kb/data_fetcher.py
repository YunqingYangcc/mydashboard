"""行情数据获取模块 - baostock(A股/ETF) + Yahoo Chart API(美股)"""
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


# ===== 美股: Yahoo Finance Chart API =====

def fetch_us_daily(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """获取美股日线行情数据 (Yahoo Finance Chart API)

    Args:
        symbol: 美股Ticker (如 NVDA)
        start_date: 开始日期 YYYYMMDD 或 YYYY-MM-DD
        end_date: 结束日期 YYYYMMDD 或 YYYY-MM-DD
    """
    # 计算天数用于 range 参数
    if len(start_date) == 8:
        sd = datetime.strptime(start_date, '%Y%m%d')
    else:
        sd = datetime.strptime(start_date, '%Y-%m-%d')
    if len(end_date) == 8:
        ed = datetime.strptime(end_date, '%Y%m%d')
    else:
        ed = datetime.strptime(end_date, '%Y-%m-%d')

    days = (ed - sd).days + 7  # 多取7天确保覆盖
    period = f'{days}d'

    try:
        url = f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range={period}&interval=1d'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        resp = requests.get(url, headers=headers, timeout=15)

        if resp.status_code == 429:
            logger.warning(f"Yahoo API 限频 {symbol}，等待后重试...")
            time.sleep(10)
            resp = requests.get(url, headers=headers, timeout=15)

        if resp.status_code != 200:
            logger.error(f"Yahoo API {symbol} HTTP {resp.status_code}")
            return pd.DataFrame()

        data = resp.json()
        result = data['chart']['result'][0]
        timestamps = result['timestamp']
        quotes = result['indicators']['quote'][0]

        # 使用 US/Eastern 时区转换日期（美股交易日基准）
        # Yahoo daily candle 时间戳是当天开盘(09:30 ET)，close 是当天收盘
        # 但需要减1天，因为数据实际以开盘日显示前一天收盘
        from zoneinfo import ZoneInfo
        from datetime import timedelta as td
        eastern_tz = ZoneInfo("America/New_York")
        trade_dates = [
            datetime.fromtimestamp(ts, tz=eastern_tz).strftime('%Y-%m-%d')
            for ts in timestamps
        ]

        df = pd.DataFrame({
            'trade_date': trade_dates,
            'open': quotes.get('open', []),
            'high': quotes.get('high', []),
            'low': quotes.get('low', []),
            'close': quotes.get('close', []),
            'volume': quotes.get('volume', []),
        })

        df = df.dropna(subset=['close'])
        df = df[df['close'] > 0]

        # 过滤日期范围
        start_fmt = start_date if '-' in start_date else f'{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}'
        end_fmt = end_date if '-' in end_date else f'{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}'
        df = df[(df['trade_date'] >= start_fmt) & (df['trade_date'] <= end_fmt)]

        df['change_pct'] = df['close'].pct_change() * 100
        df['turnover'] = df['volume'] * df['close']

        for col in ['open', 'high', 'low', 'close', 'volume', 'turnover', 'change_pct']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        df = df.reset_index(drop=True)
        result_cols = ['trade_date', 'open', 'high', 'low', 'close', 'volume', 'turnover', 'change_pct']
        return df[result_cols]

    except Exception as e:
        logger.error(f"Yahoo API {symbol} 异常: {e}")
        return pd.DataFrame()


# ===== 存储 =====

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


def batch_fetch_and_store(days: int = 120, sleep_interval: float = 1.0) -> dict:
    """批量获取所有标的的历史行情并存入数据库

    数据源:
    - A股/ETF: baostock (免费稳定)
    - 美股: Yahoo Finance Chart API (直接调用)

    Args:
        days: 获取最近N天的数据
        sleep_interval: 美股每次请求间隔(秒)

    Returns:
        dict: {symbol: rows_fetched}
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")

    results = {}

    for target in TARGET_STOCKS:
        symbol = target["symbol"]
        market = target["market"]
        chain = target["chain"]
        name = target["name"]

        logger.info(f"获取 {name}({symbol}) 行情...")

        df = pd.DataFrame()
        if market in ("A股", "ETF"):
            df = _fetch_baostock(symbol, start_str, end_str, market=market)
        elif market == "美股":
            df = fetch_us_daily(symbol, start_str, end_str)
            time.sleep(sleep_interval)

        if not df.empty:
            count = store_quotes_to_db(df, symbol, market, chain)
            results[symbol] = count
            logger.info(f"  {name}: 获取 {len(df)} 行，入库 {count} 行")
        else:
            results[symbol] = 0
            logger.warning(f"  {name}: 无数据")

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
        df = fetch_us_daily(symbol, start_str, end_str)
    else:
        df = pd.DataFrame()

    if not df.empty:
        return store_quotes_to_db(df, symbol, market, chain)
    return 0
