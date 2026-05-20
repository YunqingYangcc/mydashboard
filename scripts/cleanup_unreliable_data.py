#!/usr/bin/env python3
"""
清理不可靠数据脚本
删除无权威来源或推测性的数据记录
"""
from kb.storage import init_db, get_knowledge_db

init_db()

# 不可靠来源关键词（删除）
UNRELIABLE_SOURCES = [
    '预测', '预测值', 'estimate', 'forecast',
    '分析师', 'analyst', '券商',
    '高盛', 'Goldman', '摩根', 'Morgan', '花旗', 'Citi',
    '小摩', 'JP Morgan', '大摩', 'Morgan Stanley',
    '富国银行', 'Wells Fargo',
    'IDC', 'Gartner', 'TrendForce',
    '一致预期', 'consensus',
    '华尔街', 'Wall Street',
    '测算', 'calculated', '估算', 'estimated',
    'TradingEconomics',
    '同花顺', '东方财富', '雪球',
]

def is_unreliable(source):
    if not source:
        return True  # 无来源视为不可靠
    source_lower = source.lower()
    for unre in UNRELIABLE_SOURCES:
        if unre.lower() in source_lower:
            return True
    return False

with get_knowledge_db() as db:
    cursor = db.execute('SELECT id, metric_key, value, observed_at, source FROM observations ORDER BY metric_key, observed_at DESC')
    all_obs = cursor.fetchall()
    
    print(f"总记录数: {len(all_obs)}")
    print()
    
    # 分类记录
    delete_ids = []
    delete_list = []
    keep_list = []
    
    for obs in all_obs:
        source = obs.get('source', '')
        obs_id = obs['id']
        
        if is_unreliable(source):
            delete_ids.append(obs_id)
            delete_list.append(obs)
        else:
            keep_list.append(obs)
    
    print(f"✅ 保留记录: {len(keep_list)} 条")
    for o in keep_list:
        print(f"   {o['metric_key']}: {o['value']} | {o['source']}")
    
    print()
    print(f"🗑️  删除记录: {len(delete_ids)} 条")
    for o in delete_list:
        print(f"   {o['metric_key']}: {o['value']} | {o['source']}")
    
    # 执行删除
    if delete_ids:
        placeholders = ','.join(['?'] * len(delete_ids))
        db.execute(f'DELETE FROM observations WHERE id IN ({placeholders})', delete_ids)
        db.commit()
        print(f"\n✅ 已删除 {len(delete_ids)} 条不可靠记录")
    
    # 验证结果
    print("\n清理后数据库统计:")
    cursor = db.execute('SELECT COUNT(*) as cnt FROM observations')
    print(f"  总记录数: {cursor.fetchone()['cnt']}")
