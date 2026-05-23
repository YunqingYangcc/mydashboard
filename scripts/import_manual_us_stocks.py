"""手动导入美股数据的脚本

使用方法:
1. 将CSV文件放在 data/inbox/ 目录下
2. 文件名格式: {SYMBOL}.csv (如 NVDA.csv, AMD.csv)
3. CSV文件需要包含以下列: trade_date, open, high, low, close, volume
4. 运行: python3 scripts/import_manual_us_stocks.py
"""
import pandas as pd
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from kb.data_fetcher import store_quotes_to_db
from kb.market_constants import SYMBOL_MAP
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def import_csv_to_db(csv_dir: str = "data/inbox"):
    """从CSV文件导入美股数据到数据库
    
    Args:
        csv_dir: CSV文件所在目录
    """
    csv_path = Path(csv_dir)
    
    if not csv_path.exists():
        logger.error(f"目录不存在: {csv_dir}")
        return
    
    # 获取所有CSV文件
    csv_files = list(csv_path.glob("*.csv"))
    
    if not csv_files:
        logger.warning(f"在 {csv_dir} 中未找到CSV文件")
        return
    
    logger.info(f"找到 {len(csv_files)} 个CSV文件")
    
    results = {}
    
    for csv_file in csv_files:
        symbol = csv_file.stem.upper()  # 提取文件名作为股票代码
        
        # 检查是否在TARGET_STOCKS中
        if symbol not in SYMBOL_MAP:
            logger.warning(f"⚠️  {symbol} 不在目标股票列表中，跳过")
            continue
        
        target_info = SYMBOL_MAP[symbol]
        
        if target_info["market"] != "美股":
            logger.warning(f"⚠️  {symbol} 不是美股，跳过")
            continue
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 处理: {target_info['name']} ({symbol})")
        logger.info(f"{'='*60}")
        
        try:
            # 读取CSV文件
            df = pd.read_csv(csv_file)
            
            logger.info(f"原始数据: {len(df)} 行")
            logger.info(f"列名: {list(df.columns)}")
            
            # 标准化列名（支持多种命名方式）
            column_mapping = {
                '日期': 'trade_date',
                'date': 'trade_date',
                'Date': 'trade_date',
                '开盘价': 'open',
                '开盘': 'open',
                'Open': 'open',
                '最高价': 'high',
                '最高': 'high',
                'High': 'high',
                '最低价': 'low',
                '最低': 'low',
                'Low': 'low',
                '收盘价': 'close',
                '收盘': 'close',
                'Close': 'close',
                '成交量': 'volume',
                'Volume': 'volume',
                '成交额': 'turnover',
                'Turnover': 'turnover',
                '涨跌幅': 'change_pct',
                'Change_Pct': 'change_pct',
            }
            
            df = df.rename(columns=column_mapping)
            
            # 确保必要的列存在
            required_cols = ['trade_date', 'open', 'high', 'low', 'close', 'volume']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                logger.error(f"❌ 缺少必要列: {missing_cols}")
                results[symbol] = 0
                continue
            
            # 数据清洗和转换
            # 1. 处理日期格式
            if 'trade_date' in df.columns:
                # 尝试多种日期格式
                try:
                    df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y-%m-%d')
                except Exception as e:
                    logger.warning(f"日期转换失败: {e}，尝试其他格式...")
                    # 如果已经是字符串格式，保持不变
            
            # 2. 数值转换
            numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_cols:
                if col in df.columns:
                    # 移除千分位分隔符
                    df[col] = df[col].astype(str).str.replace(',', '').str.replace('，', '')
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 3. 计算衍生指标（如果不存在）
            if 'turnover' not in df.columns or df['turnover'].isna().all():
                df['turnover'] = df['close'] * df['volume']
                logger.info("✅ 自动计算成交额 (turnover = close × volume)")
            
            if 'change_pct' not in df.columns or df['change_pct'].isna().all():
                df['change_pct'] = df['close'].pct_change() * 100
                logger.info("✅ 自动计算涨跌幅 (change_pct)")
            
            # 4. 过滤无效数据
            df = df.dropna(subset=['close'])
            df = df[df['close'] > 0]
            df = df.sort_values('trade_date').reset_index(drop=True)
            
            logger.info(f"清洗后数据: {len(df)} 行")
            logger.info(f"日期范围: {df['trade_date'].min()} ~ {df['trade_date'].max()}")
            
            # 5. 数据存储
            market = target_info["market"]
            chain = target_info["chain"]
            
            count = store_quotes_to_db(df, symbol, market, chain)
            results[symbol] = count
            
            logger.info(f"✅ 成功入库 {count} 行数据")
            
        except Exception as e:
            logger.error(f"❌ 处理 {symbol} 失败: {e}")
            import traceback
            traceback.print_exc()
            results[symbol] = 0
    
    # 打印汇总报告
    print("\n" + "="*60)
    print("📊 导入汇总报告")
    print("="*60)
    
    total_symbols = len(results)
    success_count = sum(1 for v in results.values() if v > 0)
    total_rows = sum(results.values())
    
    print(f"\n总标的数: {total_symbols}")
    print(f"成功导入: {success_count}")
    print(f"失败: {total_symbols - success_count}")
    print(f"总行数: {total_rows}")
    
    print("\n详细结果:")
    print("-" * 60)
    for symbol, count in sorted(results.items()):
        status = "✅" if count > 0 else "❌"
        name = SYMBOL_MAP.get(symbol, {}).get('name', symbol)
        print(f"{status} {symbol:<8} {name:<20} {count:>6} 行")
    
    print("="*60)


if __name__ == "__main__":
    import_csv_to_db()
