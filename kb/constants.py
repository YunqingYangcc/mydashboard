WATERMARK_TEXT = "@杨布拉德"

RENDER_MODE_TEXT = "text"
RENDER_MODE_MARKDOWN = "markdown"
RENDER_MODE_IMAGE = "image"
RENDER_MODES = {
    RENDER_MODE_TEXT,
    RENDER_MODE_MARKDOWN,
    RENDER_MODE_IMAGE,
}

EXTRACTION_SOURCE_TYPE = "markdown_extract"

CLAIM_HEADERS = {
    "判断",
    "断言",
    "结论",
    "观点",
    "核心判断",
    "我的判断",
    "关键判断",
    "判断更新",
    "结论摘要",
    "claims",
    "claim",
}

RELATION_HEADERS = {
    "关系",
    "relations",
    "relation",
    "因果",
    "图谱",
    "关键关系",
    "关系图谱",
}

TASK_HEADERS = {
    "任务",
    "行动",
    "todo",
    "tasks",
    "下周跟踪",
    "待跟踪",
    "下一步",
    "跟踪问题",
    "待验证",
    "后续动作",
    "todo list",
}

CLAIM_PREFIXES = ("判断", "结论", "观点", "断言", "claim")
TASK_PREFIXES = ("跟踪", "任务", "todo", "下一步", "行动")
RELATION_PREFIXES = ("关系", "relation")

RELATION_ALIASES = {
    "causes": "causes",
    "导致": "causes",
    "drives": "drives",
    "驱动": "drives",
    "带动": "drives",
    "depends_on": "depends_on",
    "依赖": "depends_on",
    "取决于": "depends_on",
    "constrains": "constrains",
    "约束": "constrains",
    "限制": "constrains",
    "competes_with": "competes_with",
    "竞争": "competes_with",
    "supplies_to": "supplies_to",
    "供应给": "supplies_to",
    "buys_from": "buys_from",
    "采购自": "buys_from",
    "signals": "signals",
    "指向": "signals",
    "预示": "signals",
    "implies": "implies",
    "意味着": "implies",
    "说明": "implies",
    "priced_by": "priced_by",
    "由": "priced_by",
    "supports": "supports",
    "支持": "supports",
    "contradicts": "contradicts",
    "反驳": "contradicts",
}

RELATION_TYPES = [
    "causes",
    "drives",
    "depends_on",
    "constrains",
    "competes_with",
    "supplies_to",
    "buys_from",
    "signals",
    "implies",
    "priced_by",
    "supports",
    "contradicts",
]

KNOWN_COMPANIES = {
    "nvda",
    "nvidia",
    "amd",
    "tsmc",
    "台积电",
    "meta",
    "microsoft",
    "微软",
    "google",
    "谷歌",
    "alphabet",
    "amazon",
    "亚马逊",
    "broadcom",
    "博通",
    "asml",
}

KNOWN_TECH = {
    "gpu",
    "hbm",
    "cowos",
    "cuda",
    "nvlink",
    "rdma",
    "inference",
    "training",
    "光模块",
    "封装",
    "先进封装",
    "算力",
    "推理",
    "训练",
}

KNOWN_THEME = {
    "ai 基础设施",
    "ai infrastructure",
    "gpu demand",
    "hyperscaler capex",
    "资本开支",
    "云计算",
    "ai 周期",
    "科技周期",
}

KNOWN_METRIC = {
    "pe",
    "forward pe",
    "估值",
    "capex",
    "real yield",
    "利率",
    "毛利率",
    "营收",
}
