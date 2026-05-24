#!/usr/bin/env python3
"""测试智能增量更新功能"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from kb.data_fetcher import print_db_status, batch_fetch_and_store

def main():
    print("=" * 70)
    print("🧪 测试智能增量更新功能")
    print("=" * 70)
    
    # 1. 查看当前数据库状态
    print("\n【步骤1】查看数据库当前状态")
    print_db_status()
    
    # 2. 执行增量更新
    print("\n【步骤2】执行智能增量更新")
    print("-" * 70)
    results = batch_fetch_and_store(days=60, sleep_interval=0.5)
    
    # 3. 统计结果
    total_symbols = len(results)
    success_count = sum(1 for count in results.values() if count > 0)
    fail_count = total_symbols - success_count
    total_rows = sum(results.values())
    
    print("\n" + "=" * 70)
    print("📊 导入结果统计")
    print("=" * 70)
    print(f"总标的: {total_symbols}只")
    print(f"成功: {success_count}只")
    print(f"失败: {fail_count}只")
    print(f"新增数据: {total_rows}行")
    
    # 4. 查看更新后的状态
    print("\n【步骤3】查看更新后的数据库状态")
    print_db_status()
    
    print("\n✅ 测试完成！")
    print("\n💡 提示:")
    print("  - 首次运行会全量导入60天数据")
    print("  - 如果已有数据，会看到增量更新（通常只有1天）")
    print("  - 再次运行此脚本，应该看到大部分标的跳过（数据已是最新）")

if __name__ == "__main__":
    main()
