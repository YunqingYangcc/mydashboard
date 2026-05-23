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
    TARGET_STOCKS, SYMBOL_MAP, CHAIN_TARGETS,
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
    """计算量能分析所需的中间指标

    需要输入至少60天的OHLCV数据
    返回新增列: vol_ma20, vol_ratio, ma5, ma20, price_position, price_change_pct, high_60, low_60
    """
    if df is None or len(df) < 5:
        return df

    df = df.copy()

    # 成交量均线
    df["vol_ma5"] = df["volume"].rolling(window=5, min_periods=3).mean()
    df["vol_ma20"] = df["volume"].rolling(window=20, min_periods=10).mean()

    # 量比 = 当日成交量 / 20日均量
    df["vol_ratio"] = np.where(
        df["vol_ma20"] > 0,
        df["volume"] / df["vol_ma20"],
        1.0
    )

    # 短期量比 = 5日均量 / 20日均量（捕捉量能趋势变化）
    df["vol_ratio_short"] = np.where(
        df["vol_ma20"] > 0,
        df["vol_ma5"] / df["vol_ma20"],
        1.0
    )

    # 量能趋势: 近5日均量 vs 前5日均量(5日前的5日)
    df["vol_ma5_prev"] = df["vol_ma5"].shift(5)
    df["vol_trend"] = np.where(
        (df["vol_ma5_prev"] > 0) & (df["vol_ma5"] > 0),
        df["vol_ma5"] / df["vol_ma5_prev"],
        1.0
    )

    # 收盘价均线
    df["ma5"] = df["close"].rolling(window=5, min_periods=3).mean()
    df["ma20"] = df["close"].rolling(window=20, min_periods=10).mean()

    # 60日价格区间
    df["high_60"] = df["close"].rolling(window=60, min_periods=20).max()
    df["low_60"] = df["close"].rolling(window=60, min_periods=20).min()

    # 价格位置 = (close - low_60) / (high_60 - low_60)，0=最低，1=最高
    df["price_position"] = np.where(
        (df["high_60"] - df["low_60"]) > 0,
        (df["close"] - df["low_60"]) / (df["high_60"] - df["low_60"]),
        0.5
    )

    # 当日涨跌幅
    df["price_change_pct"] = df["close"].pct_change() * 100

    # 连续3日波动幅度（用于筑底判定）
    df["daily_range_pct"] = ((df["high"] - df["low"]) / df["close"] * 100).fillna(0)
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


def determine_market_phase(df: pd.DataFrame, date: Optional[str] = None) -> dict:
    """判定指定日期的行情阶段

    Args:
        df: DataFrame with OHLCV data (至少60天)
        date: 判定日期 (YYYY-MM-DD)，默认取最新一天

    Returns:
        dict with keys: phase, vol_condition, price_condition, vol_ratio,
                        price_position, price_change_pct, reasoning, action_suggestion
    """
    if df is None or len(df) < 20:
        return _default_result("数据不足(需至少20天)")

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
    vol_ratio_short = float(row.get("vol_ratio_short", 1.0) or 1.0)
    vol_trend = float(row.get("vol_trend", 1.0) or 1.0)
    price_position = float(row.get("price_position", 0.5) or 0.5)
    price_change_pct = float(row.get("price_change_pct", 0.0) or 0.0)
    ma5 = row.get("ma5")
    ma20 = row.get("ma20")
    low_volatility_3d = bool(row.get("low_volatility_3d", False))
    drop_30d_pct = float(row.get("drop_30d_pct", 0.0) or 0.0)
    prev_high_vol = row.get("prev_high_vol")

    # 综合量能判定: vol_ratio(当日/20日均) + vol_ratio_short(5日均/20日均) + vol_trend(近5日/前5日)
    # 当vol_ratio不够高但vol_ratio_short或vol_trend显著时，仍判定为放量
    is_volume_up = vol_ratio > 1.3 or vol_ratio_short > 1.4 or vol_trend > 1.5
    is_volume_down = vol_ratio < 0.7 and vol_ratio_short < 0.8
    is_volume_extreme = vol_ratio > 2.0 or vol_ratio_short > 2.2

    # 安全转换
    ma5_val = float(ma5) if pd.notna(ma5) else None
    ma20_val = float(ma20) if pd.notna(ma20) else None
    prev_high_vol_val = float(prev_high_vol) if pd.notna(prev_high_vol) else None

    trade_date = str(row.get("trade_date", ""))

    # ===== 优先级判定（从高到低） =====

    # 1. 恐慌见底: 极端放量+暴跌+30日深跌
    if is_volume_extreme and price_change_pct < -5.0 and drop_30d_pct < -15.0:
        return _build_result(
            PHASE_PANIC_BOTTOM, trade_date,
            vol_met=is_volume_extreme, price_met=price_change_pct < -5.0 and drop_30d_pct < -15.0,
            vol_ratio=vol_ratio, price_position=price_position, price_change_pct=price_change_pct,
            reason=f"恐慌性放量(量比{vol_ratio:.1f}x/短比{vol_ratio_short:.1f}x)且暴跌({price_change_pct:.1f}%)，30日跌幅{drop_30d_pct:.1f}%"
        )

    # 2. 见顶: 价格创新高但量能萎缩 + 价格位置>70%
    if (prev_high_vol_val is not None and prev_high_vol_val > 0
            and row.get("volume", 0) < prev_high_vol_val * 0.8
            and price_position > 0.70):
        return _build_result(
            PHASE_TOP, trade_date,
            vol_met=row.get("volume", 0) < prev_high_vol_val * 0.8,
            price_met=price_position > 0.70,
            vol_ratio=vol_ratio, price_position=price_position, price_change_pct=price_change_pct,
            reason=f"价格位置{price_position:.0%}高位但量能萎缩(量比{vol_ratio:.1f}x)，量价背离"
        )

    # 3. 派发: 放量+价格不涨+高位
    if is_volume_up and abs(price_change_pct) < 1.0 and price_position > 0.80:
        return _build_result(
            PHASE_DISTRIBUTE, trade_date,
            vol_met=is_volume_up, price_met=abs(price_change_pct) < 1.0 and price_position > 0.80,
            vol_ratio=vol_ratio, price_position=price_position, price_change_pct=price_change_pct,
            reason=f"高位({price_position:.0%})放量(量比{vol_ratio:.1f}x/短比{vol_ratio_short:.1f}x)但价格不涨({price_change_pct:+.1f}%)，派发信号"
        )

    # 4. 吸筹: 放量+低位+未再跌
    if is_volume_up and price_position < 0.40 and price_change_pct > -1.0:
        return _build_result(
            PHASE_ACCUMULATE, trade_date,
            vol_met=is_volume_up, price_met=price_position < 0.40 and price_change_pct > -1.0,
            vol_ratio=vol_ratio, price_position=price_position, price_change_pct=price_change_pct,
            reason=f"低位({price_position:.0%})放量(量比{vol_ratio:.1f}x/短比{vol_ratio_short:.1f}x)且未再跌，主力吸筹"
        )

    # 5. 拉升: 放量+上涨+MA5>MA20
    if is_volume_up and price_change_pct > 1.0 and ma5_val and ma20_val and ma5_val > ma20_val:
        return _build_result(
            PHASE_RALLY, trade_date,
            vol_met=is_volume_up, price_met=price_change_pct > 1.0 and ma5_val > ma20_val,
            vol_ratio=vol_ratio, price_position=price_position, price_change_pct=price_change_pct,
            reason=f"量价齐升(量比{vol_ratio:.1f}x, 涨{price_change_pct:+.1f}%)，MA5>MA20趋势确立"
        )

    # 6. 洗盘: 缩量+小幅回调+趋势仍向上
    if is_volume_down and -3.0 < price_change_pct < 0.0 and ma5_val and ma20_val and ma5_val > ma20_val:
        return _build_result(
            PHASE_WASH, trade_date,
            vol_met=is_volume_down, price_met=-3.0 < price_change_pct < 0.0 and ma5_val > ma20_val,
            vol_ratio=vol_ratio, price_position=price_position, price_change_pct=price_change_pct,
            reason=f"缩量回调(量比{vol_ratio:.1f}x, 跌{price_change_pct:+.1f}%)但趋势仍向上，洗盘"
        )

    # 7. 筑底: 缩量+低位+低波动
    if is_volume_down and price_position < 0.40 and low_volatility_3d:
        return _build_result(
            PHASE_BOTTOM, trade_date,
            vol_met=is_volume_down, price_met=price_position < 0.40 and low_volatility_3d,
            vol_ratio=vol_ratio, price_position=price_position, price_change_pct=price_change_pct,
            reason=f"低位({price_position:.0%})缩量(量比{vol_ratio:.1f}x)且波动极小，筑底中"
        )

    # 8. 下跌: 下跌+MA5<MA20
    if price_change_pct < -1.0 and ma5_val and ma20_val and ma5_val < ma20_val:
        return _build_result(
            PHASE_DECLINE, trade_date,
            vol_met=True, price_met=price_change_pct < -1.0 and ma5_val < ma20_val,
            vol_ratio=vol_ratio, price_position=price_position, price_change_pct=price_change_pct,
            reason=f"下跌趋势(跌{price_change_pct:+.1f}%)且MA5<MA20，空头排列"
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
    if df is None or len(df) < 20:
        return []

    df = compute_indicators(df)

    # 取最近N天
    recent = df.tail(last_n_days)
    results = []

    for idx in recent.index:
        trade_date = str(df.loc[idx, "trade_date"])
        result = determine_market_phase(df, date=trade_date)
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

        df = get_quotes_from_db(symbol, days=120)
        if df is None or len(df) < 20:
            logger.warning(f"{name}({symbol}) 数据不足，跳过")
            results[symbol] = _default_result(f"{name}数据不足")
            continue

        result = determine_market_phase(df)
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
