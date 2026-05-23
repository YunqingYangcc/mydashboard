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
    """批量获取所有标的的历史行情并存入数据库（智能增量模式）

    数据源:
    - A股/ETF: baostock (免费稳定)
    - 美股: Yahoo Finance Chart API (直接调用)

    Args:
        days: 获取最近N天的数据（首次导入或数据不足时使用）
        sleep_interval: 美股每次请求间隔(秒)

    Returns:
        dict: {symbol: rows_fetched}
    """
    from kb.storage import get_knowledge_db
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    results = {}
    
    for target in TARGET_STOCKS:
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
        need_full_fetch = False
        
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
        
        # 执行数据获取
        fetch_start_str = fetch_start_date.strftime("%Y%m%d")
        fetch_end_str = end_date.strftime("%Y%m%d")
        
        df = pd.DataFrame()
        try:
            if market in ("A股", "ETF"):
                df = _fetch_baostock(symbol, fetch_start_str, fetch_end_str, market=market)
            elif market == "美股":
                df = fetch_us_daily(symbol, fetch_start_str, fetch_end_str)
                time.sleep(sleep_interval)
        except Exception as e:
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
        df = fetch_us_daily(symbol, start_str, end_str)
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
