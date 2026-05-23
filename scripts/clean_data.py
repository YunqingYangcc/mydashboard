#!/usr/bin/env python3
"""清理数据库中的行情数据和判定结果"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from kb.storage import get_knowledge_db

def main():
    print("🗑️  开始清理数据库...")
    
    with get_knowledge_db() as conn:
        # 清理行情数据
        conn.execute('DELETE FROM stock_daily_quotes')
        quotes_count = conn.execute("SELECT COUNT(*) as cnt FROM stock_daily_quotes").fetchone()["cnt"]
        
        # 清理判定结果
        conn.execute('DELETE FROM market_phases')
        phases_count = conn.execute("SELECT COUNT(*) as cnt FROM market_phases").fetchone()["cnt"]
        
        conn.commit()
    
    print(f"✅ 清理完成:")
    print(f"   - 行情数据: {quotes_count} 条")
    print(f"   - 判定结果: {phases_count} 条")

if __name__ == "__main__":
    main()
