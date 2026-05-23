#!/usr/bin/env python3
"""批量获取120天历史行情数据并入库"""
import sys
import logging
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

from kb.storage import init_db
from kb.data_fetcher import batch_fetch_and_store


def main():
    print("🔧 初始化数据库...")
    init_db()

    print("📡 批量获取历史行情(120天)...")
    print("  ⏳ 这可能需要较长时间，美股标的间隔5秒以避免限频...")

    results = batch_fetch_and_store(days=120, sleep_interval=5.0)

    print("\n📊 获取结果:")
    total_rows = 0
    success = 0
    failed = 0
    for symbol, count in results.items():
        from kb.market_constants import SYMBOL_MAP
        name = SYMBOL_MAP.get(symbol, {}).get("name", symbol)
        total_rows += count
        if count > 0:
            success += 1
            print(f"  ✅ {name}({symbol}): {count} 条")
        else:
            failed += 1
            print(f"  ❌ {name}({symbol}): 无数据")

    print(f"\n总计: {total_rows} 行数据 | 成功 {success} | 失败 {failed}")

    if success > 0:
        print("\n💡 下一步: 运行 python scripts/seed_market_phases.py 判定行情阶段")


if __name__ == "__main__":
    main()
