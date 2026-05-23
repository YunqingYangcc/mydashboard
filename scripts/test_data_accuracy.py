#!/usr/bin/env python3
"""测试数据准确性验证机制"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
from kb.data_fetcher import validate_data_quality

def test_validate_data_quality():
    """测试数据质量验证函数"""
    print("=" * 70)
    print("🧪 测试数据准确性验证机制")
    print("=" * 70)
    
    # 测试1: 正常数据
    print("\n【测试1】正常数据")
    normal_df = pd.DataFrame({
        'trade_date': ['2024-01-01', '2024-01-02', '2024-01-03'],
        'open': [100, 101, 102],
        'high': [105, 106, 107],
        'low': [99, 100, 101],
        'close': [103, 104, 105],
        'volume': [1000, 1100, 1200],
        'change_pct': [3.0, 1.0, 1.0]
    })
    
    result = validate_data_quality('TEST', normal_df)
    print(f"  验证结果: {'✅ 通过' if result['passed'] else '❌ 失败'}")
    print(f"  警告: {result['warnings']}")
    print(f"  错误: {result['errors']}")
    
    # 测试2: OHLC逻辑错误
    print("\n【测试2】OHLC逻辑错误（high < low）")
    error_df = pd.DataFrame({
        'trade_date': ['2024-01-01'],
        'open': [100],
        'high': [95],  # 错误：最高价 < 最低价
        'low': [100],
        'close': [98],
        'volume': [1000],
        'change_pct': [-2.0]
    })
    
    result = validate_data_quality('TEST', error_df)
    print(f"  验证结果: {'✅ 通过' if result['passed'] else '❌ 失败'}")
    print(f"  警告: {result['warnings']}")
    print(f"  错误: {result['errors']}")
    
    # 测试3: 负价格
    print("\n【测试3】负价格")
    negative_df = pd.DataFrame({
        'trade_date': ['2024-01-01'],
        'open': [100],
        'high': [105],
        'low': [99],
        'close': [-5],  # 错误：负价格
        'volume': [1000],
        'change_pct': [-105.0]
    })
    
    result = validate_data_quality('TEST', negative_df)
    print(f"  验证结果: {'✅ 通过' if result['passed'] else '❌ 失败'}")
    print(f"  警告: {result['warnings']}")
    print(f"  错误: {result['errors']}")
    
    # 测试4: 数据量不足
    print("\n【测试4】数据量不足")
    small_df = pd.DataFrame({
        'trade_date': ['2024-01-01', '2024-01-02'],
        'open': [100, 101],
        'high': [105, 106],
        'low': [99, 100],
        'close': [103, 104],
        'volume': [1000, 1100],
        'change_pct': [3.0, 1.0]
    })
    
    result = validate_data_quality('TEST', small_df)
    print(f"  验证结果: {'✅ 通过' if result['passed'] else '❌ 失败'}")
    print(f"  警告: {result['warnings']}")
    print(f"  错误: {result['errors']}")
    
    # 测试5: 涨跌幅过大
    print("\n【测试5】涨跌幅过大（>20%）")
    extreme_df = pd.DataFrame({
        'trade_date': ['2024-01-01', '2024-01-02'],
        'open': [100, 101],
        'high': [105, 150],
        'low': [99, 100],
        'close': [103, 150],  # 涨幅48%
        'volume': [1000, 50000],
        'change_pct': [3.0, 45.6]  # 超过20%
    })
    
    result = validate_data_quality('TEST', extreme_df)
    print(f"  验证结果: {'✅ 通过' if result['passed'] else '❌ 失败'}")
    print(f"  警告: {result['warnings']}")
    print(f"  错误: {result['errors']}")
    
    print("\n" + "=" * 70)
    print("✅ 测试完成！")
    print("\n💡 说明:")
    print("  - Level 2验证（数据质量）：检查OHLC逻辑、数值范围")
    print("  - Level 3验证（业务逻辑）：检查数据量、日期连续性、涨跌幅")
    print("  - 验证失败的数据会被拒绝入库，确保数据准确性")

if __name__ == "__main__":
    test_validate_data_quality()
