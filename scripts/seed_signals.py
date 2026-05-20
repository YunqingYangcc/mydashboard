"""预置信号定义种子数据 - AI/半导体领域

运行: python scripts/seed_signals.py

信号框架通用设计，维度和信号可扩展到任意领域：
- 估值、需求、基本面、宏观、情绪 五大通用维度
- comparator: gt=超过阈值不利(如PE>60偏贵), lt=低于阈值不利(如增速<15%预警)
- 录入观测值后自动评估信号状态
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from kb.storage import init_db, upsert_signal_definition

init_db()

SIGNALS = [
    # ===== 估值信号 =====
    {"signal_key": "nvda_pe", "name": "NVDA PE(TTM)", "dimension": "估值",
     "frequency": "daily", "comparator": "gt", "threshold": 60.0,
     "metric_key": "nvda_pe", "description": "英伟达市盈率>60偏贵"},
    {"signal_key": "nvda_ps", "name": "NVDA PS(TTM)", "dimension": "估值",
     "frequency": "daily", "comparator": "gt", "threshold": 25.0,
     "metric_key": "nvda_ps", "description": "英伟达市销率>25偏贵"},
    {"signal_key": "sox_pe", "name": "SOX PE", "dimension": "估值",
     "frequency": "daily", "comparator": "gt", "threshold": 30.0,
     "metric_key": "sox_pe", "description": "费城半导体指数PE>30偏贵"},
    {"signal_key": "nvda_gross_margin", "name": "NVDA毛利率", "dimension": "估值",
     "frequency": "quarterly", "comparator": "lt", "threshold": 70.0,
     "metric_key": "nvda_gross_margin", "description": "毛利率<70%预警竞争力下降"},

    # ===== 需求信号 =====
    {"signal_key": "cloud_capex_growth", "name": "四大云CapEx增速", "dimension": "需求",
     "frequency": "quarterly", "comparator": "lt", "threshold": 15.0,
     "metric_key": "cloud_capex_growth", "description": "CapEx增速<15%需求下行预警"},
    {"signal_key": "tsmc_revenue_growth", "name": "台积电月营收增速", "dimension": "需求",
     "frequency": "monthly", "comparator": "lt", "threshold": 20.0,
     "metric_key": "tsmc_revenue_growth", "description": "台积电增速<20%半导体需求走弱"},
    {"signal_key": "hbm_supply_gap", "name": "HBM产能缺口", "dimension": "需求",
     "frequency": "monthly", "comparator": "gt", "threshold": 5.0,
     "metric_key": "hbm_supply_gap", "description": "缺口>5%利好存储厂商"},
    {"signal_key": "gpu_rental_price_change", "name": "算力租赁价格月变化", "dimension": "需求",
     "frequency": "weekly", "comparator": "lt", "threshold": -20.0,
     "metric_key": "gpu_rental_price_change", "description": "月跌>20%供过于求"},

    # ===== 基本面信号 =====
    {"signal_key": "nvda_dc_ratio", "name": "NVDA数据中心营收占比", "dimension": "基本面",
     "frequency": "quarterly", "comparator": "lt", "threshold": 70.0,
     "metric_key": "nvda_dc_ratio", "description": "占比<70%多元化风险"},
    {"signal_key": "nvda_qoq_growth", "name": "NVDA季度环比增速", "dimension": "基本面",
     "frequency": "quarterly", "comparator": "lt", "threshold": 5.0,
     "metric_key": "nvda_qoq_growth", "description": "环比<5%增速放缓预警"},
    {"signal_key": "asic_share", "name": "自研芯片替代率", "dimension": "基本面",
     "frequency": "quarterly", "comparator": "gt", "threshold": 10.0,
     "metric_key": "asic_share", "description": "替代率>10%威胁英伟达份额"},

    # ===== 宏观信号 =====
    {"signal_key": "us_10y_yield", "name": "10Y美债收益率", "dimension": "宏观",
     "frequency": "daily", "comparator": "gt", "threshold": 4.5,
     "metric_key": "us_10y_yield", "description": ">4.5%利空成长股估值"},
    {"signal_key": "sox_vs_spy", "name": "SOX相对SPY强度", "dimension": "宏观",
     "frequency": "daily", "comparator": "lt", "threshold": 0.0,
     "metric_key": "sox_vs_spy", "description": "跑输=半导体周期见顶信号"},
    {"signal_key": "vix", "name": "VIX恐慌指数", "dimension": "宏观",
     "frequency": "daily", "comparator": "gt", "threshold": 25.0,
     "metric_key": "vix", "description": ">25市场恐慌"},

    # ===== 情绪信号 =====
    {"signal_key": "nvda_put_call", "name": "NVDA Put/Call比", "dimension": "情绪",
     "frequency": "daily", "comparator": "gt", "threshold": 1.5,
     "metric_key": "nvda_put_call", "description": ">1.5看空情绪浓厚"},
    {"signal_key": "nvda_analyst_spread", "name": "分析师目标价偏离度", "dimension": "情绪",
     "frequency": "weekly", "comparator": "gt", "threshold": 20.0,
     "metric_key": "nvda_analyst_spread", "description": "偏离>20%分歧大"},
]


def seed():
    count = 0
    for sig in SIGNALS:
        upsert_signal_definition(sig)
        count += 1
    print(f"✅ 已写入 {count} 个信号定义")


if __name__ == "__main__":
    seed()
