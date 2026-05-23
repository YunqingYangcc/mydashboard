"""行情阶段判定常量 - 基于"量在价先"方法论的可枚举行情阶段"""

# ===== 行情阶段定义 =====
# 9种可枚举行情阶段: 8种明确阶段 + 1种默认(震荡)

PHASE_BOTTOM = "筑底"        # 🏗️ 低位无量，等待
PHASE_ACCUMULATE = "吸筹"    # 🧲 低位放量，跟主力
PHASE_RALLY = "拉升"          # 🚀 量价齐升，持股
PHASE_WASH = "洗盘"           # 🔄 缩量回调，持股不动
PHASE_DISTRIBUTE = "派发"     # 📤 高位放量滞涨，减仓
PHASE_TOP = "见顶"            # ⚠️ 量价背离，清仓
PHASE_DECLINE = "下跌"        # 📉 放量/量平价跌，空仓
PHASE_PANIC_BOTTOM = "恐慌见底"  # 💀 恐慌放量暴跌，关注反转
PHASE_SIDeways = "震荡"       # ⚖️ 无明显量能特征，区间波动

ALL_PHASES = [
    PHASE_BOTTOM, PHASE_ACCUMULATE, PHASE_RALLY, PHASE_WASH,
    PHASE_DISTRIBUTE, PHASE_TOP, PHASE_DECLINE, PHASE_PANIC_BOTTOM,
    PHASE_SIDeways,
]

# 利好阶段（绿色系）
BULLISH_PHASES = {PHASE_ACCUMULATE, PHASE_RALLY, PHASE_PANIC_BOTTOM}
# 利空阶段（红色系）
BEARISH_PHASES = {PHASE_DISTRIBUTE, PHASE_TOP, PHASE_DECLINE}
# 中性阶段（灰色/黄色系）
NEUTRAL_PHASES = {PHASE_BOTTOM, PHASE_WASH, PHASE_SIDeways}

# ===== 行情阶段视觉配置 =====
PHASE_CONFIG = {
    PHASE_BOTTOM: {
        "emoji": "🏗️",
        "bg_color": "#1E3A5F",
        "text_color": "#60A5FA",
        "label": "低位无量·等待",
        "action": "不急入场，等待放量信号",
        "attention": "关注是否出现低位放量(吸筹信号)",
        "formula": "低位无量就要等",
        "sort_order": 0,
    },
    PHASE_ACCUMULATE: {
        "emoji": "🧲",
        "bg_color": "#1B4332",
        "text_color": "#34D399",
        "label": "低位放量·跟主力",
        "action": "逐步建仓，跟随主力资金",
        "attention": "关注放量持续性+主力净买入方向",
        "formula": "低位放量就要跟",
        "sort_order": 1,
    },
    PHASE_RALLY: {
        "emoji": "🚀",
        "bg_color": "#064E3B",
        "text_color": "#10B981",
        "label": "量价齐升·持股",
        "action": "持股待涨，趋势确立可加仓",
        "attention": "关注量能是否持续放大，缩量则警惕洗盘",
        "formula": "量增价升持股",
        "sort_order": 2,
    },
    PHASE_WASH: {
        "emoji": "🔄",
        "bg_color": "#3B2F1E",
        "text_color": "#FBBF24",
        "label": "缩量回调·持股不动",
        "action": "持股不动，不加不减，等量能恢复",
        "attention": "关注回调幅度是否有限，MA20支撑是否有效",
        "formula": "缩量上涨可持有",
        "sort_order": 3,
    },
    PHASE_DISTRIBUTE: {
        "emoji": "📤",
        "bg_color": "#4A2C1A",
        "text_color": "#F97316",
        "label": "高位放量滞涨·减仓",
        "action": "减仓离场，不追高",
        "attention": "警惕主力出货，关注放量是否伴随大单净卖出",
        "formula": "放量滞涨转阴",
        "sort_order": 4,
    },
    PHASE_TOP: {
        "emoji": "⚠️",
        "bg_color": "#4A1C1C",
        "text_color": "#EF4444",
        "label": "量价背离·清仓出局",
        "action": "清仓出局，落袋为安",
        "attention": "价创新高但量萎缩=趋势衰竭，关注是否转下跌",
        "formula": "量价背离早出局",
        "sort_order": 5,
    },
    PHASE_DECLINE: {
        "emoji": "📉",
        "bg_color": "#3B1010",
        "text_color": "#DC2626",
        "label": "放量/量平价跌·空仓",
        "action": "空仓观望，不要抄底",
        "attention": "关注是否出现缩量止跌(筑底信号)或恐慌性暴跌(见底信号)",
        "formula": "量平价跌出逃",
        "sort_order": 6,
    },
    PHASE_PANIC_BOTTOM: {
        "emoji": "💀",
        "bg_color": "#1A0A0A",
        "text_color": "#F87171",
        "label": "恐慌见底·关注反转",
        "action": "极度恐慌时准备抄底，但需等量能确认",
        "attention": "恐慌暴跌后常反弹，但需确认不再创新低+量能回升",
        "formula": "恐慌抛售见底",
        "sort_order": 7,
    },
    PHASE_SIDeways: {
        "emoji": "⚖️",
        "bg_color": "#2D2D2D",
        "text_color": "#9CA3AF",
        "label": "区间震荡·观望",
        "action": "观望为主，等待方向明确",
        "attention": "关注量能异动(突然放量或缩量)，可能预示突破",
        "formula": "量能无明显特征",
        "sort_order": 8,
    },
}


# ===== 产业链环节定义 =====
CHAIN_GPU = "GPU芯片"
CHAIN_HBM = "HBM/存储"
CHAIN_OPTICAL = "光模块"
CHAIN_PACKAGE = "封装"
CHAIN_EQUIPMENT = "设备/PCB"
CHAIN_NETWORK = "AI网络"
CHAIN_COMPOSITE = "综合"

ALL_CHAINS = [CHAIN_GPU, CHAIN_HBM, CHAIN_OPTICAL, CHAIN_PACKAGE, CHAIN_EQUIPMENT, CHAIN_NETWORK, CHAIN_COMPOSITE]

# 产业链环节颜色
CHAIN_COLORS = {
    CHAIN_GPU: "#6366F1",
    CHAIN_HBM: "#8B5CF6",
    CHAIN_OPTICAL: "#A78BFA",
    CHAIN_PACKAGE: "#F59E0B",
    CHAIN_EQUIPMENT: "#10B981",
    CHAIN_NETWORK: "#3B82F6",
    CHAIN_COMPOSITE: "#6B7280",
}

# 产业链流程顺序
CHAIN_FLOW = [CHAIN_GPU, CHAIN_HBM, CHAIN_OPTICAL, CHAIN_PACKAGE, CHAIN_EQUIPMENT]


# ===== 标的定义 =====
# 每只标的: symbol, name, market, chain, exchange(可选)

TARGET_STOCKS = [
    # === A股 (8只) ===
    {
        "symbol": "688041",
        "name": "海光信息",
        "market": "A股",
        "chain": CHAIN_GPU,
        "ak_code": "688041",
        "yf_code": None,
        "desc": "国产GPU龙头，深算系列",
    },
    {
        "symbol": "688981",
        "name": "中芯国际",
        "market": "A股",
        "chain": CHAIN_GPU,
        "ak_code": "688981",
        "yf_code": None,
        "desc": "先进制程代工",
    },
    {
        "symbol": "603501",
        "name": "韦尔股份",
        "market": "A股",
        "chain": CHAIN_HBM,
        "ak_code": "603501",
        "yf_code": None,
        "desc": "存储+CIS",
    },
    {
        "symbol": "688008",
        "name": "澜起科技",
        "market": "A股",
        "chain": CHAIN_HBM,
        "ak_code": "688008",
        "yf_code": None,
        "desc": "DDR5/CXL内存接口",
    },
    {
        "symbol": "300308",
        "name": "中际旭创",
        "market": "A股",
        "chain": CHAIN_OPTICAL,
        "ak_code": "300308",
        "yf_code": None,
        "desc": "800G/1.6T光模块全球龙头",
    },
    {
        "symbol": "600584",
        "name": "长电科技",
        "market": "A股",
        "chain": CHAIN_PACKAGE,
        "ak_code": "600584",
        "yf_code": None,
        "desc": "先进封装OSAT",
    },
    {
        "symbol": "002371",
        "name": "北方华创",
        "market": "A股",
        "chain": CHAIN_EQUIPMENT,
        "ak_code": "002371",
        "yf_code": None,
        "desc": "刻蚀/薄膜设备",
    },
    {
        "symbol": "002463",
        "name": "沪电股份",
        "market": "A股",
        "chain": CHAIN_EQUIPMENT,
        "ak_code": "002463",
        "yf_code": None,
        "desc": "AI服务器高速PCB",
    },
    # === 美股 (10只) ===
    {
        "symbol": "NVDA",
        "name": "NVIDIA",
        "market": "美股",
        "chain": CHAIN_GPU,
        "ak_code": None,
        "yf_code": "NVDA",
        "desc": "GPU绝对龙头，HBM核心采购方",
    },
    {
        "symbol": "AMD",
        "name": "AMD",
        "market": "美股",
        "chain": CHAIN_GPU,
        "ak_code": None,
        "yf_code": "AMD",
        "desc": "MI300系列，HBM集成",
    },
    {
        "symbol": "AVGO",
        "name": "Broadcom",
        "market": "美股",
        "chain": CHAIN_NETWORK,
        "ak_code": None,
        "yf_code": "AVGO",
        "desc": "AI ASIC+网络交换芯片",
    },
    {
        "symbol": "MRVL",
        "name": "Marvell",
        "market": "美股",
        "chain": CHAIN_NETWORK,
        "ak_code": None,
        "yf_code": "MRVL",
        "desc": "定制芯片+光通信DSP",
    },
    {
        "symbol": "MU",
        "name": "Micron",
        "market": "美股",
        "chain": CHAIN_HBM,
        "ak_code": None,
        "yf_code": "MU",
        "desc": "HBM3E核心供应商",
    },
    {
        "symbol": "TSM",
        "name": "TSMC",
        "market": "美股",
        "chain": CHAIN_PACKAGE,
        "ak_code": None,
        "yf_code": "TSM",
        "desc": "CoWoS封装垄断者",
    },
    {
        "symbol": "AMKR",
        "name": "Amkor",
        "market": "美股",
        "chain": CHAIN_PACKAGE,
        "ak_code": None,
        "yf_code": "AMKR",
        "desc": "OSAT封装测试龙头",
    },
    {
        "symbol": "ANET",
        "name": "Arista",
        "market": "美股",
        "chain": CHAIN_NETWORK,
        "ak_code": None,
        "yf_code": "ANET",
        "desc": "AI数据中心网络设备",
    },
    {
        "symbol": "COHR",
        "name": "Coherent",
        "market": "美股",
        "chain": CHAIN_OPTICAL,
        "ak_code": None,
        "yf_code": "COHR",
        "desc": "光模块上游器件",
    },
    {
        "symbol": "LITE",
        "name": "Lumentum",
        "market": "美股",
        "chain": CHAIN_OPTICAL,
        "ak_code": None,
        "yf_code": "LITE",
        "desc": "光通信收发器",
    },
    # === ETF (2只) ===
    {
        "symbol": "512460",
        "name": "国联安半导体ETF",
        "market": "ETF",
        "chain": CHAIN_COMPOSITE,
        "ak_code": "512460",
        "yf_code": None,
        "desc": "国联安半导体ETF",
    },
    {
        "symbol": "512480",
        "name": "中华半导体ETF",
        "market": "ETF",
        "chain": CHAIN_COMPOSITE,
        "ak_code": "512480",
        "yf_code": None,
        "desc": "中华半导体ETF",
    },
]

# 快速查找表
SYMBOL_MAP = {s["symbol"]: s for s in TARGET_STOCKS}
A_SHARE_SYMBOLS = [s["symbol"] for s in TARGET_STOCKS if s["market"] == "A股"]
US_SHARE_SYMBOLS = [s["symbol"] for s in TARGET_STOCKS if s["market"] == "美股"]
ETF_SYMBOLS = [s["symbol"] for s in TARGET_STOCKS if s["market"] == "ETF"]

# 按产业链分组
CHAIN_TARGETS = {}
for s in TARGET_STOCKS:
    chain = s["chain"]
    CHAIN_TARGETS.setdefault(chain, []).append(s)
