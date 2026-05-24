"""行情阶段判定引擎 - 基于"量在价先"方法论

📋 Prompt绑定: prompts/行情算法.md
修改本文件前必须先阅读该 prompt，确保改动符合9阶段判定规则和量能阈值定义。

8种可枚举行情阶段:
1. 筑底   - 低位无量，等待
2. 吸筹   - 低位放量，跟主力
3. 拉升   - 量价齐升，持股
4. 洗盘   - 缩量回调，持股不动
5. 派发   - 高位放量滞涨，减仓
6. 见顶   - 量价背离，清仓出局
7. 下跌   - 放量/量平价跌，空仓
8. 恐慌见底 - 恐慌放量暴跌，关注反转

默认: 震荡 - 无明显量能特征
"""
import logging
from typing import Optional

import numpy as np
import pandas as pd

from kb.market_constants import (
    PHASE_BOTTOM, PHASE_ACCUMULATE, PHASE_RALLY, PHASE_WASH,
    PHASE_DISTRIBUTE, PHASE_TOP, PHASE_DECLINE, PHASE_PANIC_BOTTOM,
    PHASE_SIDeways, PHASE_CONFIG, BULLISH_PHASES, BEARISH_PHASES, NEUTRAL_PHASES,
    TARGET_STOCKS, SYMBOL_MAP, CHAIN_TARGETS, SECTOR_COEFFICIENT,
)

logger = logging.getLogger(__name__)


def _safe_series(s: pd.Series) -> np.ndarray:
    """安全转numpy数组"""
    if s is None or len(s) == 0:
        return np.array([])
    vals = s.values
    if hasattr(vals, 'to_numpy'):
        vals = vals.to_numpy()
    return np.where(pd.isna(vals), 0, vals).astype(float)


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """计算量能分析所需的中间指标 (V2.0 修正版)

    需要输入至少60天的OHLCV数据（用于计算MA20、MA60等指标）
    新增: vol_ratio (5日均量基准), vol_trend_ratio (5日/20日趋势比)
    """
    if df is None or len(df) < 5:
        return df

    df = df.copy()

    # 成交量均线
    df["vol_ma5"] = df["volume"].rolling(window=5, min_periods=3).mean()
    df["vol_ma20"] = df["volume"].rolling(window=20, min_periods=10).mean()

    # 标准量比 = 当日成交量 / 近5日平均成交量 (市场通用定义)
    df["vol_ratio"] = np.where(
        df["vol_ma5"] > 0,
        df["volume"] / df["vol_ma5"],
        1.0
    )

    # 量能趋势比 = 5日均量 / 20日均量 (捕捉量能方向变化)
    df["vol_trend_ratio"] = np.where(
        df["vol_ma20"] > 0,
        df["vol_ma5"] / df["vol_ma20"],
        1.0
    )

    # 收盘价均线（动态调整窗口，支持30天数据）
    df["ma5"] = df["close"].rolling(window=5, min_periods=3).mean()
    ma10_window = min(10, len(df))
    df["ma10"] = df["close"].rolling(window=ma10_window, min_periods=max(3, ma10_window//2)).mean()
    ma20_window = min(20, len(df))
    df["ma20"] = df["close"].rolling(window=ma20_window, min_periods=max(5, ma20_window//2)).mean()
    
    ma60_window = min(60, len(df))
    ma60_min_periods = max(10, ma60_window // 2)
    df["ma60"] = df["close"].rolling(window=ma60_window, min_periods=ma60_min_periods).mean()

    # 60日价格区间（动态调整窗口）
    high_low_window = min(60, len(df))
    high_low_min_periods = max(10, high_low_window // 2)
    df["high_60"] = df["close"].rolling(window=high_low_window, min_periods=high_low_min_periods).max()
    df["low_60"] = df["close"].rolling(window=high_low_window, min_periods=high_low_min_periods).min()

    # 价格位置 = (close - low_60) / (high_60 - low_60)，0=最低，1=最高
    df["price_position"] = np.where(
        (df["high_60"] - df["low_60"]) > 0,
        (df["close"] - df["low_60"]) / (df["high_60"] - df["low_60"]),
        0.5
    )

    # 当日涨跌幅
    df["price_change_pct"] = df["close"].pct_change() * 100

    # 连续3日波动幅度（用于筑底判定）
    df["daily_range_pct"] = np.where(
        df["close"] > 0,
        (df["high"] - df["low"]) / df["close"] * 100,
        0
    )
    df["low_volatility_3d"] = df["daily_range_pct"].rolling(window=3, min_periods=3).max() < 2.0

    # 30日跌幅（用于恐慌见底判定）
    df["drop_30d_pct"] = (df["close"] / df["close"].shift(30) - 1) * 100

    # 前高对应量（用于量价背离判定）
    df["prev_high_vol"] = _compute_prev_high_volume(df)

    return df


def _compute_prev_high_volume(df: pd.DataFrame) -> pd.Series:
    """计算前一个价格高点对应的成交量"""
    result = pd.Series(np.nan, index=df.index)

    close_vals = df["close"].values if "close" in df.columns else np.array([])
    vol_vals = df["volume"].values if "volume" in df.columns else np.array([])

    if len(close_vals) < 5:
        return result

    for i in range(len(close_vals)):
        if i < 5:
            continue
        # 在前5~60日中找价格最高点
        lookback = min(i, 60)
        window_close = close_vals[max(0, i - lookback):i]
        window_vol = vol_vals[max(0, i - lookback):i]

        if len(window_close) == 0:
            continue

        # 当前价格是否接近或超过近期高点
        max_close_idx = np.argmax(window_close)
        if close_vals[i] >= window_close[max_close_idx] * 0.98:
            # 价格在高位区域，取前高对应量
            result.iloc[i] = window_vol[max_close_idx]

    return result


def determine_market_phase(df: pd.DataFrame, date: Optional[str] = None, symbol: str = None) -> dict:
    """判定指定日期的行情阶段

    Args:
        df: DataFrame with OHLCV data (至少30天，已优化)
        date: 判定日期 (YYYY-MM-DD)，默认取最新一天
        symbol: 标的代码（用于获取行业系数）

    Returns:
        dict with keys: phase, vol_condition, price_condition, vol_ratio,
                        price_position, price_change_pct, reasoning, action_suggestion
    """
    if df is None or len(df) < 15:
        return _default_result("数据不足(需至少15天)")

    df = compute_indicators(df)

    # 确定判定日
    if date:
        mask = df["trade_date"] == date
        if not mask.any():
            # 尝试找最近的
            mask = df["trade_date"] <= date
        if not mask.any():
            return _default_result(f"无 {date} 数据")
        idx = df.index[mask][-1]
    else:
        idx = df.index[-1]

    row = df.loc[idx]

    # 提取指标
    vol_ratio = float(row.get("vol_ratio", 1.0) or 1.0)
    vol_trend_ratio = float(row.get("vol_trend_ratio", 1.0) or 1.0)
    price_position = float(row.get("price_position", 0.5) or 0.5)
    price_change_pct = float(row.get("price_change_pct", 0.0) or 0.0)
    
    # 安全转换均线值
    ma5_val = float(row.get("ma5")) if pd.notna(row.get("ma5")) else None
    ma10_val = float(row.get("ma10")) if pd.notna(row.get("ma10")) else None
    ma20_val = float(row.get("ma20")) if pd.notna(row.get("ma20")) else None
    ma60_val = float(row.get("ma60")) if pd.notna(row.get("ma60")) else None
    prev_high_vol_val = float(row.get("prev_high_vol")) if pd.notna(row.get("prev_high_vol")) else None
    
    # 动态获取行业系数
    if symbol:
        target = SYMBOL_MAP.get(symbol, {})
        chain = target.get("chain", "default")
    else:
        chain = "default"
    coeff = SECTOR_COEFFICIENT.get(chain, SECTOR_COEFFICIENT["default"])
    
    # 综合量能判定 (V2.0 修正)
    is_volume_up = vol_ratio > coeff["volume_up"] or vol_trend_ratio > 1.4
    is_volume_down = vol_ratio < coeff["volume_down"] and vol_trend_ratio < 0.8
    is_volume_extreme = vol_ratio > coeff["extreme_vol"]

    # 趋势强度因子: 识别主升浪中的缩量上涨（筹码锁定）
    # V2.1 修正：必须满足 MA5 > MA20 > MA60 才是真正的主升浪
    is_uptrend = (ma5_val is not None and ma20_val is not None and ma60_val is not None 
                  and ma5_val > ma20_val and ma20_val > ma60_val)
    recent_gain_5d = float(df.loc[idx, "close"] / df.loc[max(0, idx-4), "close"] - 1) * 100 if idx >= 4 else 0
    is_strong_uptrend = is_uptrend and recent_gain_5d > 8.0

    trade_date = str(row.get("trade_date", ""))

    # ===== 优先级判定（从高到低，风险优先） =====

    # 1. 恐慌见底: 极端放量 + 暴跌(<-5%) + 30日深跌(<-15%) + 振幅>8%
    drop_30d_pct = float(row.get("drop_30d_pct", 0.0) or 0.0)
    daily_range_pct = float(row.get("daily_range_pct", 0.0) or 0.0)
    
    if is_volume_extreme and price_change_pct < -5.0 and drop_30d_pct < -15.0 and daily_range_pct > 8.0:
        return _build_result(
            PHASE_PANIC_BOTTOM, trade_date,
            vol_met=is_volume_extreme, price_met=True,
            vol_ratio=vol_ratio, price_position=price_position, price_change_pct=price_change_pct,
            reason=f"恐慌性放量(量比{vol_ratio:.1f}x)且暴跌({price_change_pct:.1f}%)，振幅{daily_range_pct:.1f}%"
        )

    # 2. 派发: 高位放量滞涨 (优先级高于见顶，作为预警)
    if is_volume_up and abs(price_change_pct) < 0.5 and price_position > 0.80:
        return _build_result(
            PHASE_DISTRIBUTE, trade_date,
            vol_met=is_volume_up, price_met=True,
            vol_ratio=vol_ratio, price_position=price_position, price_change_pct=price_change_pct,
            reason=f"高位({price_position:.0%})放量(量比{vol_ratio:.1f}x)但价格不涨，派发信号"
        )

    # 3. 见顶: 价格创60日新高 AND 量能萎缩 (<前高对应量的80%) AND 非主升浪
    # V2.1 修正：必须明确价格创60日新高，而不仅仅是位置>95%
    is_new_high = row["close"] >= row.get("high_60", 0) * 0.99  # 接近或达到60日新高
    if (prev_high_vol_val is not None and prev_high_vol_val > 0
            and row.get("volume", 0) < prev_high_vol_val * 0.8
            and is_new_high
            and price_position > 0.95
            and not is_strong_uptrend):
        return _build_result(
            PHASE_TOP, trade_date,
            vol_met=row.get("volume", 0) < prev_high_vol_val * 0.8,
            price_met=is_new_high and price_position > 0.95,
            vol_ratio=vol_ratio, price_position=price_position, price_change_pct=price_change_pct,
            reason=f"价格创60日新高但量能萎缩(量比{vol_ratio:.1f}x)，量价背离"
        )

    # 4. 吸筹: 放量+低位+未再跌
    if is_volume_up and price_position < 0.40 and price_change_pct > -1.0:
        return _build_result(
            PHASE_ACCUMULATE, trade_date,
            vol_met=is_volume_up, price_met=True,
            vol_ratio=vol_ratio, price_position=price_position, price_change_pct=price_change_pct,
            reason=f"低位({price_position:.0%})放量(量比{vol_ratio:.1f}x)且未再跌，主力吸筹"
        )

    # 5. 拉升: 放量+上涨+MA5>MA20+价格在MA20之上
    # V2.2 修正：强化量能权重，量比必须达到行业阈值才能判定为拉升
    if (is_volume_up and price_change_pct > 1.0 
            and ma5_val and ma20_val and ma5_val > ma20_val
            and row["close"] > ma20_val):
        return _build_result(
            PHASE_RALLY, trade_date,
            vol_met=is_volume_up, price_met=True,
            vol_ratio=vol_ratio, price_position=price_position, price_change_pct=price_change_pct,
            reason=f"量价齐升(量比{vol_ratio:.1f}x, 涨{price_change_pct:+.1f}%)，趋势确立"
        )

    # 5.5 温和拉升 (V2.2新增): 中等涨幅 + 平量/轻微缩量 + 趋势向上
    # 适用场景：涨幅3-6%，量比0.8-1.2x，筹码锁定良好
    is_moderate_gain = 3.0 <= price_change_pct <= 6.0
    is_flat_volume = 0.8 <= vol_ratio <= 1.2
    if (is_moderate_gain and is_flat_volume
            and ma5_val and ma20_val and ma5_val > ma20_val
            and row["close"] > ma20_val):
        return _build_result(
            PHASE_RALLY, trade_date,
            vol_met=True, price_met=True,
            vol_ratio=vol_ratio, price_position=price_position, price_change_pct=price_change_pct,
            reason=f"温和拉升(量比{vol_ratio:.1f}x, 涨{price_change_pct:+.1f}%)，筹码锁定，趋势向上"
        )

    # 5.6 加速上涨修正 (V2.0): 强势主升浪中任何上涨都是最强信号
    # V2.2 修正：增加量能要求，即使是主升浪也需要基本量能支撑
    if is_strong_uptrend and price_change_pct > 0.5:
        # 主升浪中至少需要平量（量比>=0.7）
        if vol_ratio >= 0.7:
            return _build_result(
                PHASE_RALLY, trade_date,
                vol_met=True, price_met=True,
                vol_ratio=vol_ratio, price_position=price_position, price_change_pct=price_change_pct,
                reason=f"强势主升浪中(5日涨{recent_gain_5d:.1f}%)，量比{vol_ratio:.1f}x，筹码锁定良好，加速上涨"
            )
        else:
            # 量能严重不足，降级为洗盘或震荡
            return _build_result(
                PHASE_WASH if price_change_pct < 0 else PHASE_SIDeways, trade_date,
                vol_met=False, price_met=False,
                vol_ratio=vol_ratio, price_position=price_position, price_change_pct=price_change_pct,
                reason=f"主升浪但量能严重不足(量比{vol_ratio:.1f}x)，需警惕"
            )

    # 6. 洗盘: 缩量+小幅回调+趋势仍向上+价格未跌破MA20
    # V2.1 修正：增加价格未跌破MA20的条件，确保是洗盘而非趋势反转
    low_volatility_3d = bool(row.get("low_volatility_3d", False))
    if (is_volume_down and -3.0 < price_change_pct < 0.0 
            and ma5_val and ma20_val and ma5_val > ma20_val
            and row["close"] > ma20_val):
        return _build_result(
            PHASE_WASH, trade_date,
            vol_met=is_volume_down, price_met=-3.0 < price_change_pct < 0.0 and ma5_val > ma20_val,
            vol_ratio=vol_ratio, price_position=price_position, price_change_pct=price_change_pct,
            reason=f"缩量回调(量比{vol_ratio:.1f}x, 跌{price_change_pct:+.1f}%)但趋势仍向上，洗盘"
        )

    # 7. 筑底: 缩量+低位+低波动+充分下跌
    # V2.1 修正：增加30日跌幅>10%的条件，确保是真正的底部而非高位横盘
    if (is_volume_down and price_position < 0.40 
            and low_volatility_3d
            and drop_30d_pct < -10.0):
        return _build_result(
            PHASE_BOTTOM, trade_date,
            vol_met=is_volume_down, price_met=price_position < 0.40 and low_volatility_3d,
            vol_ratio=vol_ratio, price_position=price_position, price_change_pct=price_change_pct,
            reason=f"低位({price_position:.0%})缩量(量比{vol_ratio:.1f}x)且波动极小，30日跌{drop_30d_pct:.1f}%，筑底中"
        )

    # 8. 下跌: (MA5<MA20 AND MA10<MA20) OR (连续3日累计跌幅>5%)
    # V2.1 修正：补充连续3日累计跌幅判定，及时识别极端暴跌
    is_ma_broken = (ma5_val and ma20_val and ma10_val 
                    and ma5_val < ma20_val and ma10_val < ma20_val)
    
    # 计算连续3日累计跌幅
    if idx >= 3:
        close_3d_ago = df.loc[idx-3, "close"]
        cumulative_drop = (row["close"] / close_3d_ago - 1) * 100 if close_3d_ago > 0 else 0
    else:
        cumulative_drop = 0
    
    is_cumulative_drop = cumulative_drop < -5.0
    
    if (price_change_pct < -1.0 and is_ma_broken) or is_cumulative_drop:
        return _build_result(
            PHASE_DECLINE, trade_date,
            vol_met=True, price_met=True,
            vol_ratio=vol_ratio, price_position=price_position, price_change_pct=price_change_pct,
            reason=f"趋势破坏(MA5/MA10均跌破MA20 或 3日累计跌{cumulative_drop:.1f}%)，空仓观望"
        )

    # 9. 默认: 震荡
    return _build_result(
        PHASE_SIDeways, trade_date,
        vol_met=False, price_met=False,
        vol_ratio=vol_ratio, price_position=price_position, price_change_pct=price_change_pct,
        reason=f"量比{vol_ratio:.1f}x·位置{price_position:.0%}·涨跌{price_change_pct:+.1f}%，无明显量能特征"
    )


def _default_result(reason: str) -> dict:
    """默认结果"""
    config = PHASE_CONFIG[PHASE_SIDeways]
    return {
        "phase": PHASE_SIDeways,
        "emoji": config["emoji"],
        "vol_condition": "数据不足",
        "price_condition": "数据不足",
        "vol_ratio": None,
        "price_position": None,
        "price_change_pct": None,
        "reasoning": reason,
        "action_suggestion": config["action"],
        "attention": config["attention"],
    }


def _build_result(phase: str, trade_date: str,
                  vol_met: bool, price_met: bool,
                  vol_ratio: float, price_position: float, price_change_pct: float,
                  reason: str) -> dict:
    """构建行情阶段判定结果"""
    config = PHASE_CONFIG[phase]
    return {
        "phase": phase,
        "emoji": config["emoji"],
        "trade_date": trade_date,
        "vol_condition": "✅ 满足" if vol_met else "❌ 未满足",
        "price_condition": "✅ 满足" if price_met else "❌ 未满足",
        "vol_ratio": round(vol_ratio, 2),
        "price_position": round(price_position, 3),
        "price_change_pct": round(price_change_pct, 2),
        "reasoning": reason,
        "action_suggestion": config["action"],
        "attention": config["attention"],
        "label": config["label"],
        "formula": config["formula"],
        "bg_color": config["bg_color"],
        "text_color": config["text_color"],
    }


def batch_determine_phases(symbol: str, df: pd.DataFrame, last_n_days: int = 5) -> list[dict]:
    """批量判定最近N天的行情阶段

    Returns:
        list of phase result dicts, most recent first
    """
    if df is None or len(df) < 15:
        return []

    df = compute_indicators(df)

    # 取最近N天
    recent = df.tail(last_n_days)
    results = []

    for idx in recent.index:
        trade_date = str(df.loc[idx, "trade_date"])
        result = determine_market_phase(df, date=trade_date, symbol=symbol)
        result["symbol"] = symbol
        target = SYMBOL_MAP.get(symbol, {})
        result["name"] = target.get("name", symbol)
        result["market"] = target.get("market", "")
        result["chain"] = target.get("chain", "")
        results.append(result)

    return results


def determine_all_current() -> dict:
    """判定所有标的的当前行情阶段

    Returns:
        dict: {symbol: phase_result}
    """
    from kb.data_fetcher import get_quotes_from_db

    results = {}
    for target in TARGET_STOCKS:
        symbol = target["symbol"]
        name = target["name"]

        df = get_quotes_from_db(symbol, days=60)
        if df is None or len(df) < 15:
            logger.warning(f"{name}({symbol}) 数据不足，跳过")
            results[symbol] = _default_result(f"{name}数据不足")
            continue

        result = determine_market_phase(df, symbol=symbol)
        result["symbol"] = symbol
        result["name"] = name
        result["market"] = target["market"]
        result["chain"] = target["chain"]
        results[symbol] = result

    return results


def compute_chain_phase_summary(phases: dict) -> dict:
    """计算各产业链环节的整体行情阶段

    Args:
        phases: determine_all_current() 的输出

    Returns:
        dict: {chain: {phase, bullish_count, bearish_count, neutral_count, dominant_phase}}
    """
    chain_summary = {}

    for chain, targets in CHAIN_TARGETS.items():
        chain_phases = []
        for t in targets:
            sym = t["symbol"]
            if sym in phases:
                chain_phases.append(phases[sym]["phase"])

        if not chain_phases:
            continue

        bullish = sum(1 for p in chain_phases if p in BULLISH_PHASES)
        bearish = sum(1 for p in chain_phases if p in BEARISH_PHASES)
        neutral = sum(1 for p in chain_phases if p in NEUTRAL_PHASES)

        # 主导阶段
        from collections import Counter
        phase_counts = Counter(chain_phases)
        dominant = phase_counts.most_common(1)[0][0] if phase_counts else PHASE_SIDeways

        chain_summary[chain] = {
            "phase": dominant,
            "bullish_count": bullish,
            "bearish_count": bearish,
            "neutral_count": neutral,
            "total": len(chain_phases),
            "phases": chain_phases,
        }

    return chain_summary


def save_phases_to_db(phases: dict) -> int:
    """将行情阶段判定结果存入 market_phases 表

    Returns:
        存入的记录数
    """
    from kb.storage import get_knowledge_db
    from kb.utils import now_iso
    import json

    count = 0
    now = now_iso()

    with get_knowledge_db() as conn:
        for symbol, phase_data in phases.items():
            trade_date = phase_data.get("trade_date", now[:10])
            config = PHASE_CONFIG.get(phase_data["phase"], PHASE_CONFIG[PHASE_SIDeways])

            try:
                conn.execute("""
                    INSERT OR REPLACE INTO market_phases
                    (symbol, phase_date, phase, vol_condition, price_condition,
                     vol_ratio, price_position, price_change_pct, params_json,
                     reasoning, action_suggestion, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    symbol,
                    trade_date,
                    phase_data.get("phase", PHASE_SIDeways),
                    phase_data.get("vol_condition", ""),
                    phase_data.get("price_condition", ""),
                    phase_data.get("vol_ratio"),
                    phase_data.get("price_position"),
                    phase_data.get("price_change_pct"),
                    json.dumps({
                        "name": phase_data.get("name", ""),
                        "market": phase_data.get("market", ""),
                        "chain": phase_data.get("chain", ""),
                        "attention": phase_data.get("attention", ""),
                        "formula": phase_data.get("formula", ""),
                    }, ensure_ascii=False),
                    phase_data.get("reasoning", ""),
                    config.get("action", ""),
                    now,
                ))
                count += 1
            except Exception as e:
                logger.warning(f"存储 {symbol} 行情阶段失败: {e}")

    return count


def get_phases_from_db(symbol: str, days: int = 5) -> list[dict]:
    """从数据库获取标的的最近N天行情阶段

    Returns:
        list of phase dicts, most recent first
    """
    from kb.storage import get_knowledge_db

    with get_knowledge_db() as conn:
        rows = conn.execute("""
            SELECT * FROM market_phases
            WHERE symbol = ?
            ORDER BY phase_date DESC
            LIMIT ?
        """, (symbol, days)).fetchall()

    return [dict(r) for r in rows]
