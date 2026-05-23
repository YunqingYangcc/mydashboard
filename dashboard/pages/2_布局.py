import sys
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dashboard.components import init_page_style, render_signature
from kb.storage import (
    fetch_latest_documents,
    get_all_knowledge_doc_links,
    get_learned_items,
    init_db,
    link_document_to_knowledge,
    list_claims,
    reset_knowledge_progress,
    unlink_document_from_knowledge,
    upsert_knowledge_item,
    bind_signal_to_knowledge,
    unbind_signal_from_knowledge,
    get_knowledge_signal_bindings,
    get_knowledge_signal_status,
    list_signal_definitions,
)

init_db()
init_page_style()

# ===== 完整知识框架（含学习目标）=====
KNOWLEDGE_TREE = {
    "P0 基础设施层": {
        "intro": {
            "goal": "🎯 目标：看懂AI算力的供给瓶颈在哪里，谁能涨价谁被替代",
            "output": "📊 看到'台积电CoWoS产能扩张50%'，能判断对英伟达/光模块/服务器的传导影响",
            "insight": "🔑 关键认知：算力链的价值分配=谁垄断谁赚最多，GPU>HBM>封装>光模块>服务器",
        },
        "💻 AI芯片": {
            "companies": "英伟达H100/B200/Rubin、AMD MI300/325、博通TPU、华为昇腾910B/950、寒武纪、地平线J6",
            "goal": "🎯 理解不同芯片的定位和护城河差异",
            "output": "📊 看到'博通ASIC拿下Google订单'时，能判断对英伟达是威胁还是共存",
            "children": {
                "GPU训练": {"companies": "英伟达H100/B200/Rubin", "goal": "掌握英伟达每代产品的性能跃迁节奏、出货量、定价权", "output": "能算英伟达单颗GPU利润率、市场规模天花板"},
                "GPU推理": {"companies": "英伟达L40/H200、AMD MI325", "goal": "理解推理市场vs训练市场的规模比例", "output": "能判断推理芯片商品化风险对英伟达估值的影响"},
                "ASIC定制": {"companies": "博通Google TPU、Marvell", "goal": "理解ASIC vs GPU的优劣势", "output": "能回答博通的TPU业务能多大程度威胁英伟达"},
                "NPU/端侧": {"companies": "华为昇腾910B/950、寒武纪、地平线", "goal": "理解端侧AI的市场规模和国产替代进度", "output": "能判断华为昇腾能否3年内替代英伟达中国区份额"},
                "FPGA": {"companies": "AMD/Xilinx、紫光同创", "goal": "了解即可，不是投资主线"},
                "车载AI芯片": {"companies": "英伟达Orin/Thor、高通8775", "goal": "了解车载AI芯片格局"},
            }
        },
        "🧠 存储与内存": {
            "companies": "SK海力士60%、三星25%、美光15%、Montage澜起",
            "goal": "🎯 理解HBM是GPU产能的核心瓶颈",
            "output": "📊 看到'SK海力士HBM产能扩张'，能推算对英伟达出货量的影响",
            "insight": "🔑 HBM是GPU的'限速器'，谁控制HBM谁控制GPU出货量上限",
            "children": {
                "HBM": {"companies": "SK海力士60%、三星25%、美光15%", "goal": "掌握HBM3e→HBM4代际演进、产能爬坡节奏", "output": "能算HBM缺口5%对应多少GPU出货量受限"},
                "DRAM": {"companies": "三星42%、SK海力士30%、美光22%", "goal": "理解DRAM周期位置、价格拐点信号", "output": "能判断当前处于库存周期的哪个阶段"},
                "NAND": {"companies": "三星34%、铠侠15%", "goal": "了解即可，与AI关系相对间接"},
                "CXL内存扩展": {"companies": "三星、SK海力士、Montage澜起", "goal": "理解CXL解决内存墙问题", "output": "能判断CXL是否会成为新的投资主线"},
            }
        },
        "🖥️ AI服务器": {
            "companies": "戴尔、HPE、工业富联、浪潮、维谛、英维克、高澜",
            "goal": "🎯 理解服务器是'组装生意'还是'有壁垒的生意'",
            "output": "📊 看到'戴尔AI服务器订单暴增'时，能判断利润率变化",
            "insight": "🔑 服务器利润率5-8%，远低于芯片60%+，是量的逻辑不是价的逻辑",
            "children": {
                "整机": {"companies": "戴尔、HPE、工业富联、浪潮", "goal": "理解AI服务器营收占比差异", "output": "能算AI服务器vs传统服务器的利润贡献"},
                "液冷": {"companies": "维谛、英维克、高澜", "goal": "理解三种液冷路线优劣和渗透率", "output": "能算液冷渗透率从37%→50%对应多大增量市场"},
                "电源": {"companies": "台达电、Eaton、麦格米特", "goal": "理解AI服务器功率从1kW→3kW+升级趋势"},
            }
        },
        "🔌 高速互联": {
            "companies": "中际旭创、Coherent、NVIDIA Mellanox、Arista",
            "goal": "🎯 理解互联是AI集群的'血管'，决定集群规模上限",
            "output": "📊 看到'1.6T光模块量产'，能判断对中际旭创的影响",
            "insight": "🔑 光模块是AI算力链中'换机周期最清晰'的环节，GPU换代=光模块换代",
            "children": {
                "800G光模块": {"companies": "中际旭创、Coherent、新易盛", "goal": "掌握当前出货量、ASP、毛利率"},
                "1.6T光模块": {"companies": "中际旭创、天孚通信", "goal": "掌握1.6T量产时间与Rubin GPU配合节奏"},
                "InfiniBand": {"companies": "NVIDIA Mellanox垄断", "goal": "理解IB vs 以太网竞争格局"},
                "NVLink/NVSwitch": {"companies": "NVIDIA私有协议", "goal": "理解NVLink是GPU集群的粘合剂和护城河"},
            }
        },
        "📡 云计算/CapEx": {
            "companies": "AWS/Azure/GCP、CoreWeave、优刻得",
            "goal": "🎯 CapEx是整个产业链的'总开关'",
            "output": "📊 看到'四大云Q2 CapEx'数据，能判断对英伟达下季度营收的影响",
            "insight": "🔑 CapEx增速拐点=整个AI产业链的牛熊分界线",
            "children": {
                "超大规模云": {"companies": "AWS $1300亿、Azure $800亿、GCP $500亿", "goal": "掌握每家云厂商AI CapEx占比", "output": "能算四大云CapEx×GPU采购占比×英伟达市占率"},
                "算力租赁": {"companies": "CoreWeave、Lambda、Nebius", "goal": "理解算力租赁是CapEx的'溢出效应'", "output": "能判断租赁价格涨跌=供需关系的实时指标"},
                "CapEx周期": {"companies": "四大云$7250亿/2026", "goal": "掌握历史上CapEx周期见顶的信号", "output": "能预警当前CapEx/现金流比例是否危险"},
                "自研芯片": {"companies": "Google TPU、AWS Trainium、Meta MTIA", "goal": "理解各云自研进度", "output": "能判断自研是'降本'还是'替代'"},
            }
        },
    },
    "P0 数据层": {
        "intro": {
            "goal": "🎯 目标：理解数据是AI的'隐性成本'，数据质量决定模型质量",
            "output": "📊 看到'Reddit API涨价'或'NYT起诉OpenAI'时，能判断对大模型公司的影响",
            "insight": "🔑 高质量数据正在耗尽，谁掌握独家数据源谁有定价权",
        },
        "📊 训练数据": {
            "companies": "CommonCrawl、FineWeb、GitHub、arXiv、LAION",
            "goal": "🎯 理解公开数据池的规模和枯竭时间",
            "children": {}
        },
        "🏷️ 数据标注与RLHF": {
            "companies": "Scale AI $140亿估值、Snorkel、数据堂",
            "goal": "🎯 理解RLHF成本占大模型训练总成本的比例",
            "output": "📊 能判断Scale AI估值140亿是否合理",
            "children": {
                "人工标注": {"companies": "Scale AI、数据堂", "goal": "理解人工标注的规模成本"},
                "合成数据": {"companies": "OpenAI、Anthropic、微软", "goal": "判断合成数据能否解决'数据墙'问题"},
            }
        },
        "🔒 数据治理": {
            "companies": "NYT vs OpenAI诉讼、联邦学习",
            "goal": "🎯 理解版权诉讼走向和独家数据的定价逻辑",
            "children": {}
        },
        "🔢 向量数据库": {
            "companies": "Pinecone、Milvus、Weaviate、Chroma",
            "goal": "🎯 理解向量数据库在RAG架构中的定位",
            "output": "📊 能判断向量数据库是'数据库功能'还是'独立产品'",
            "children": {}
        },
    },
    "P0 软件层": {
        "intro": {
            "goal": "🎯 目标：理解软件层是英伟达真正的'隐性护城河'",
            "output": "📊 看到'AMD ROCm 6.0发布'时，能判断能否撼动CUDA",
            "insight": "🔑 CUDA生态迁移成本>硬件成本，这是英伟达最深的护城河",
        },
        "🛡️ CUDA生态": {
            "companies": "英伟达SDK、cuDNN、NCCL、AMD ROCm差距大",
            "goal": "🎯 掌握CUDA的用户基数（500万+开发者）、迁移成本",
            "output": "📊 能量化：一个企业从CUDA迁移到ROCm需要多少成本和时间",
            "insight": "🔥 CUDA生态=英伟达核心护城河",
            "children": {
                "Triton": {"companies": "开源替代尝试", "goal": "理解Triton能否成为CUDA的'安卓'"},
                "ROCm": {"companies": "AMD替代", "goal": "理解ROCm与CUDA的功能覆盖率差距"},
            }
        },
        "🔧 AI框架": {
            "companies": "PyTorch主导、JAX、TensorRT、vLLM、DeepSpeed",
            "goal": "🎯 理解框架竞争格局对芯片厂商的影响",
            "children": {
                "推理引擎": {"companies": "TensorRT、vLLM、Triton", "goal": "理解推理引擎的优化空间决定了推理成本"},
                "分布式训练": {"companies": "DeepSpeed、Megatron-LM、FSDP", "goal": "理解分布式训练框架"},
            }
        },
        "📦 MLOps": {
            "companies": "Kubernetes+Kubeflow、Ray、MLflow、W&B、Datadog",
            "goal": "🎯 理解MLOps市场规模和增长逻辑",
            "output": "📊 能判断哪些MLOps公司值得投资",
            "children": {}
        },
        "🔌 Agent框架": {
            "companies": "LangChain、LlamaIndex、CrewAI、MCP协议",
            "goal": "🎯 理解MCP是什么、为什么重要、对AI Agent生态的影响",
            "children": {}
        },
    },
    "P1 能源电力层": {
        "intro": {
            "goal": "🎯 目标：理解电力是AI的物理天花板，能源投资是AI的'确定性衍生需求'",
            "output": "📊 看到'微软签约核电站'时，能判断对电力股/核电概念的影响",
            "insight": "🔑 AI的尽头是电力，电力公用股是AI投资中PE最低、确定性最高的方向",
        },
        "⚡ 电力需求": {
            "companies": "2026年460TWh→2030年650-1050TWh",
            "goal": "🎯 理解用电量增速与GPU出货量的线性关系",
            "children": {
                "PUE优化": {"goal": "理解PUE每降0.1省多少电费"},
                "单机柜功耗": {"goal": "理解传统15kW→AI 600kW+的升级"},
            }
        },
        "🔋 电力供给": {
            "companies": "Helion/微软、阳光电源、宁德时代、特变电工",
            "goal": "🎯 理解SMR商业化时间线、投资标的",
            "output": "📊 能判断核电概念股是真机会还是炒作",
            "children": {
                "核电/SMR": {"companies": "微软签约Helion、亚马逊购买核电站", "goal": "理解SMR商业化时间线"},
                "电网基础设施": {"companies": "变压器/配电/特高压", "goal": "理解变压器订单排到2028年意味着什么"},
            }
        },
        "🌡️ 散热": {
            "companies": "液冷渗透率20%→37%→50%",
            "goal": "🎯 理解液冷市场的CAGR和主要玩家增速",
            "children": {}
        },
    },
    "P1 半导体制造": {
        "intro": {
            "goal": "🎯 目标：理解制造层的瓶颈和地缘风险定价",
            "output": "📊 看到'台积电CoWoS产能翻倍'时，能推算英伟达GPU出货量上限提升多少",
            "insight": "🔑 台积电是不可替代的，台海风险=英伟达最大尾部风险",
        },
        "🏭 晶圆代工": {
            "companies": "台积电TSMC 5nm/3nm/2nm 垄断90%+、中芯国际",
            "goal": "🎯 掌握台积电的定价权、产能分配逻辑",
            "output": "📊 能量化：台积电产能中断6个月对英伟达的损失",
            "children": {
                "先进制程": {"companies": "台积电5nm/3nm/2nm", "goal": "理解台积电先进制程的垄断地位"},
                "CoWoS封装": {"companies": "台积电垄断", "goal": "理解CoWoS是当前GPU产能瓶颈", "output": "能算CoWoS月产能→对应多少颗GPU→对应多少营收"},
                "成熟制程": {"companies": "中芯国际、联电、华虹", "goal": "理解国产替代进度"},
            }
        },
        "⚙️ 半导体设备": {
            "companies": "ASML EUV垄断、Lam Research、北方华创、中微公司",
            "goal": "🎯 理解国产设备在哪个环节有突破、哪个环节仍被卡脖子",
            "output": "📊 能判断北方华创vs中微公司哪个更值得投资",
            "children": {
                "光刻": {"companies": "ASML EUV垄断、尼康", "goal": "理解EUV是半导体的'终极武器'，ASML不可替代"},
                "刻蚀": {"companies": "Lam Research、中微公司", "goal": "理解国产刻蚀设备的突破"},
            }
        },
        "🧪 半导体材料": {
            "companies": "信越化学、SUMCO、沪硅产业、南大光电、安集科技",
            "goal": "🎯 理解材料国产化率在哪些环节最低（=投资机会最大）",
            "children": {}
        },
        "📦 封测": {
            "companies": "日月光、长电科技、通富微电、华天",
            "goal": "了解即可，不是投资主线",
            "children": {}
        },
    },
    "P2 模型层": {
        "intro": {
            "goal": "🎯 目标：理解模型能力边界，判断哪些应用'能做'哪些'做不了'",
            "output": "📊 看到'GPT-5发布'时，能判断对API定价、云厂商CapEx、应用层的连锁影响",
            "insight": "🔑 模型能力是应用层的'天花板'，但模型公司本身很难赚钱（API价格战）",
        },
        "🧠 基础大模型": {
            "companies": "GPT-4o/5、Claude、Gemini、Llama、Qwen、DeepSeek",
            "goal": "🎯 掌握各模型的能力对比、API定价、市场份额",
            "output": "📊 能判断OpenAI的商业模式是否可持续",
            "children": {
                "闭源模型": {"companies": "GPT-4o/5、Claude、Gemini", "goal": "理解闭源模型的定价权和护城河"},
                "开源模型": {"companies": "Llama、Qwen、DeepSeek", "goal": "理解开源对闭源的替代威胁、DeepSeek的定价策略"},
                "视频生成": {"companies": "Sora、Kling、Pika、Runway", "goal": "理解视频生成对算力的需求是文本的100倍+"},
            }
        },
        "🦾 Agent/具身智能": {
            "companies": "AutoGPT、Devin、Tesla Optimus、Figure、Unitree",
            "goal": "🎯 理解Agent的商业化进度和瓶颈",
            "children": {
                "AI Agent": {"companies": "AutoGPT、Devin、Manus", "goal": "理解Agent的商业化路径"},
                "人形机器人": {"companies": "Tesla Optimus、Figure、Unitree", "goal": "理解人形机器人的技术路线和量产时间线"},
            }
        },
    },
    "P2 安全/治理层": {
        "intro": {
            "goal": "🎯 目标：理解监管对AI投资的影响方向",
            "output": "📊 看到'EU AI Act生效'时，能判断对哪些公司是利好、哪些是利空",
            "insight": "🔑 监管=准入门槛=大公司利好小公司利空，AI安全是新的投资赛道",
        },
        "⚖️ 合规与审计": {
            "companies": "EU AI Act、中国算法备案、美国AI行政令",
            "goal": "🎯 理解EU AI Act的核心条款和罚款力度",
            "children": {}
        },
        "🛡️ AI安全": {
            "companies": "Anthropic红队、OpenAI对齐、xAI可解释性",
            "goal": "理解对齐/红队测试、可解释性的商业价值",
            "children": {}
        },
    },
    "P2 垂直应用层": {
        "intro": {
            "goal": "🎯 目标：判断哪个应用赛道最先产生规模化收入",
            "output": "📊 看到'Copilot企业用户突破100万'时，能算出对应微软的增量收入",
            "insight": "🔑 AI应用投资逻辑=渗透率×付费意愿×替换成本，编程>办公>搜索>创意",
        },
        "🖥️ 开发/编程": {
            "companies": "GitHub Copilot $19/月、Cursor、Claude Code、Devin",
            "goal": "🎯 理解AI编程对开发者效率的提升量化（3-5x）",
            "output": "📊 能算Copilot $19/月×用户数=微软增量收入",
            "priority": "⭐⭐⭐⭐⭐",
            "children": {}
        },
        "📝 办公/知识": {
            "companies": "Notion AI、飞书AI、Microsoft 365 Copilot",
            "goal": "🎯 理解办公AI的定价权在谁手里（平台vs插件）",
            "priority": "⭐⭐⭐⭐",
            "children": {}
        },
        "🔍 搜索/信息": {
            "companies": "Perplexity、Google AI Overviews",
            "goal": "🎯 理解AI搜索对Google广告模式的冲击",
            "priority": "⭐⭐⭐",
            "children": {}
        },
        "🚗 智能驾驶": {
            "companies": "特斯拉FSD、Waymo、华为ADS、小鹏XNGP",
            "goal": "🎯 理解L2→L4的技术路线和商业化时间线",
            "output": "📊 能判断FSD授权模式对特斯拉估值的影响",
            "priority": "⭐⭐",
            "children": {}
        },
        "🏥 医疗AI": {
            "companies": "AlphaFold、Google Health、医渡云、推想医疗",
            "goal": "🎯 理解医疗AI的监管壁垒和商业化路径",
            "priority": "⭐⭐",
            "children": {}
        },
        "💰 金融AI": {
            "companies": "Bloomberg GPT、蚂蚁、同花顺iFinD",
            "goal": "🎯 理解金融AI的合规要求和数据壁垒",
            "priority": "⭐⭐⭐",
            "children": {}
        },
    },
}

# ===== 侧边栏 =====
with st.sidebar:
    st.divider()
    st.subheader("📚 学习路径建议")
    st.markdown("""
**第一阶段：P0基础设施层（2-3周）**
优先学：AI芯片→HBM→云CapEx→CUDA生态
为什么：你持有英伟达，必须看懂它的上下游

**第二阶段：P0数据层+软件层（1-2周）**
优先学：数据标注→CUDA护城河→推理引擎
为什么：数据决定需求天花板，CUDA决定护城河深度

**第三阶段：P1能源+制造层（1-2周）**
优先学：电力需求→CoWoS封装→ASML
为什么：能源是物理约束，制造是产能瓶颈

**第四阶段：P2模型+应用层（2周）**
优先学：闭源vs开源→AI编程→自动驾驶
为什么：模型能力=应用天花板，AI编程是你最直接的能力杠杆
    """)
    st.divider()
    render_signature()

# ===== 页面 =====
st.title("🌳 AI产业链知识图谱")
st.caption("勾选已掌握的知识点 → 量化学习进度")

# 加载已学数据
learned_items = get_learned_items()

# ===== 进度 =====
total_count = 0
for layer, categories in KNOWLEDGE_TREE.items():
    for category, info in categories.items():
        if category == "intro":
            continue
        if isinstance(info, dict) and "children" in info:
            total_count += 1 + len(info.get("children", {}))
        else:
            total_count += 1

learned_count = len(learned_items)
progress = learned_count / total_count if total_count > 0 else 0

col1, col2 = st.columns([1, 3])
with col1:
    st.metric("已掌握", f"{learned_count}/{total_count}")
with col2:
    st.progress(progress, text=f"掌握度 {int(progress*100)}%")

if st.button("🔄 重置进度", use_container_width=True):
    reset_knowledge_progress()
    st.rerun()

st.divider()

# ===== 知识图谱展示 =====
def render_category(layer: str, category: str, info: dict, learned_items: set, col):
    if category == "intro":
        return
    
    item_key = f"{layer}|{category}"
    is_learned = item_key in learned_items
    
    with col:
        # 优先级标签
        priority = info.get("priority", "")
        if priority:
            st.markdown(f"{priority}")
        
        # 分类标题
        st.markdown(f"**{category}**")
        
        # 勾选框
        checked = st.checkbox(
            f"{'✅' if is_learned else '⬜'} 已掌握",
            value=is_learned,
            key=f"kb_{item_key.replace(' ', '_').replace('|', '_')}"
        )
        
        # 保存状态
        if checked != is_learned:
            upsert_knowledge_item(item_key, layer, None, category, checked)
            if checked:
                learned_items.add(item_key)
            else:
                learned_items.discard(item_key)
        
        # 🎯 学习目标
        if info.get("goal"):
            st.caption(f"{info['goal']}")
        
        # 📊 预期产出
        if info.get("output"):
            st.caption(f"{info['output']}")
        
        # 🔑 关键认知
        if info.get("insight"):
            st.caption(f"**{info['insight']}**")
        
        # 关联公司
        if info.get("companies"):
            st.caption(f"🏢 {info['companies']}")
        
        # 子项（直接列出，不嵌套expander）
        children = info.get("children", {})
        if children:
            st.markdown("**📂 子知识点：**")
            for child, child_info in children.items():
                child_key = f"{layer}|{category}|{child}"
                child_learned = child_key in learned_items
                checked_child = st.checkbox(
                    f"{'✅' if child_learned else '⬜'} {child}",
                    value=child_learned,
                    key=f"kb_{child_key.replace(' ', '_').replace('|', '_')}"
                )
                if checked_child != child_learned:
                    upsert_knowledge_item(child_key, layer, category, child, checked_child)
                    if checked_child:
                        learned_items.add(child_key)
                    else:
                        learned_items.discard(child_key)
                
                # 子项目标或公司
                if isinstance(child_info, dict):
                    if child_info.get("goal"):
                        st.caption(f"   🎯 {child_info['goal']}")
                    if child_info.get("companies"):
                        st.caption(f"   🏢 {child_info['companies']}")
        
        st.markdown("---")


# ===== 知识点-文档关联展示 =====
def _get_linked_claims(layer: str, category: str, info: dict):
    """根据章节映射，自动获取关联的断言"""
    # 分类级映射
    cat_key = f"{layer}|{category}"
    chapter = CHAPTER_MAP.get(cat_key)
    claims = []
    if chapter:
        # 精确匹配该章节
        claims = _claims_by_chapter.get(chapter, [])
        # 同时匹配所有子章节（如 chapter="P0-基础设施/AI芯片"，也匹配 "P0-基础设施/AI芯片/GPU训练"）
        for ch, cl in _claims_by_chapter.items():
            if ch.startswith(chapter + "/"):
                claims.extend(cl)
    # 子项章节映射
    children = info.get("children", {})
    child_claims = []
    for child in children:
        child_key = f"{layer}|{category}|{child}"
        ch = CHAPTER_MAP.get(child_key)
        if ch:
            child_claims.extend(_claims_by_chapter.get(ch, []))
            for ch2, cl2 in _claims_by_chapter.items():
                if ch2.startswith(ch + "/"):
                    child_claims.extend(cl2)
    return claims, child_claims


def render_category_with_docs(layer: str, category: str, info: dict, learned_items: set, col, doc_links: dict, starred_docs: list):
    """渲染知识点卡片，包含文档关联功能"""
    if category == "intro":
        return
    
    item_key = f"{layer}|{category}"
    is_learned = item_key in learned_items
    linked_docs = doc_links.get(item_key, [])
    
    # 自动关联断言
    cat_claims, child_claims = _get_linked_claims(layer, category, info)
    all_claims = cat_claims + child_claims
    claim_count = len(all_claims)
    
    with col:
        # 优先级标签
        priority = info.get("priority", "")
        if priority:
            st.markdown(f"{priority}")
        
        # 分类标题 + 文档数量 + 断言数量
        parts = [f"**{category}**"]
        if len(linked_docs) > 0:
            parts.append(f"📄 {len(linked_docs)}")
        if claim_count > 0:
            parts.append(f"🧠 {claim_count}")
        st.markdown(" ".join(parts))
        
        # 勾选框
        checked = st.checkbox(
            f"{'✅' if is_learned else '⬜'} 已掌握",
            value=is_learned,
            key=f"kb_{item_key.replace(' ', '_').replace('|', '_')}"
        )
        
        # 保存状态
        if checked != is_learned:
            upsert_knowledge_item(item_key, layer, None, category, checked)
            if checked:
                learned_items.add(item_key)
            else:
                learned_items.discard(item_key)
        
        # 🎯 学习目标
        if info.get("goal"):
            st.caption(f"{info['goal']}")
        
        # 📊 预期产出
        if info.get("output"):
            st.caption(f"{info['output']}")
        
        # 🔑 关键认知
        if info.get("insight"):
            st.caption(f"**{info['insight']}**")
        
        # 关联公司
        if info.get("companies"):
            st.caption(f"🏢 {info['companies']}")
        
        # 知识点关联信号状态
        bindings = signal_bindings_map.get(item_key, [])
        if bindings:
            sig_statuses = get_knowledge_signal_status(item_key)
            if sig_statuses:
                status_parts = []
                for ss in sig_statuses:
                    icon_map = {"positive": "🟢", "negative": "🔴", "neutral": "🟡"}
                    icon = icon_map.get(ss.get("status"), "⚪")
                    val = ss.get("raw_value")
                    name = ss.get("name", ss.get("signal_key", ""))
                    status_parts.append(f"{icon}{name}:{val}" if val is not None else f"⚪{name}")
                st.caption("🚦 " + " · ".join(status_parts))
        
        # 关联文档列表
        if linked_docs:
            for doc in linked_docs:
                doc_id = doc["id"]
                col_link, col_del = st.columns([4, 1])
                with col_link:
                    st.page_link(
                        "pages/知识库.py",
                        label=f"📄 {doc.get('title', '未命名')[:20]}",
                        icon="📄"
                    )
                with col_del:
                    if st.button("❌", key=f"del_{doc_id}_{item_key}", help="取消关联"):
                        unlink_document_from_knowledge(item_key, doc_id)
                        st.rerun()
        
        # 自动关联断言列表（无需手动关联）
        if all_claims:
            for claim in all_claims:
                claim_id = claim.get("id")
                status_icon = {"validated": "✅", "invalidated": "❌", "pending": "⏳"}.get(claim.get("verification_status", "pending"), "⏳")
                subject = claim.get("subject") or claim.get("statement", "")[:20]
                st.caption(f"🧠 {status_icon} {subject}")
        
        # 添加关联按钮（如果有收藏文档）
        if starred_docs:
            st.markdown("**🔗 关联文档**")
            for doc in starred_docs[:10]:  # 最多显示10个
                doc_id = doc["id"]
                already_linked = any(d["id"] == doc_id for d in linked_docs)
                if st.button(
                    f"{'✅' if already_linked else '➕'} {doc.get('title', '未命名')[:25]}",
                    key=f"link_{doc_id}_{item_key}",
                    use_container_width=True
                ):
                    if already_linked:
                        unlink_document_from_knowledge(item_key, doc_id)
                    else:
                        link_document_to_knowledge(item_key, doc_id)
                    st.rerun()
        
        # 子项
        children = info.get("children", {})
        if children:
            st.markdown("**📂 子知识点：**")
            for child, child_info in children.items():
                child_key = f"{layer}|{category}|{child}"
                child_learned = child_key in learned_items
                child_docs = doc_links.get(child_key, [])
                doc_cnt = len(child_docs)
                # 自动关联断言
                child_ch = CHAPTER_MAP.get(child_key)
                child_claim_list = _claims_by_chapter.get(child_ch, []) if child_ch else []
                claim_cnt = len(child_claim_list)
                
                child_col1, child_col2 = st.columns([3, 1])
                with child_col1:
                    checked_child = st.checkbox(
                        f"{'✅' if child_learned else '⬜'} {child}",
                        value=child_learned,
                        key=f"kb_{child_key.replace(' ', '_').replace('|', '_')}"
                    )
                    if doc_cnt > 0:
                        st.caption(f"   📄 {doc_cnt}篇")
                    if claim_cnt > 0:
                        st.caption(f"   🧠 {claim_cnt}条断言")
                with child_col2:
                    pass
                
                if checked_child != child_learned:
                    upsert_knowledge_item(child_key, layer, category, child, checked_child)
                    if checked_child:
                        learned_items.add(child_key)
                    else:
                        learned_items.discard(child_key)
                
                # 子项目标或公司
                if isinstance(child_info, dict):
                    if child_info.get("goal"):
                        st.caption(f"   🎯 {child_info['goal']}")
                    if child_info.get("companies"):
                        st.caption(f"   🏢 {child_info['companies']}")
                
                # 子知识点信号状态
                child_bindings = signal_bindings_map.get(child_key, [])
                if child_bindings:
                    child_sig_statuses = get_knowledge_signal_status(child_key)
                    if child_sig_statuses:
                        child_status_parts = []
                        for ss in child_sig_statuses:
                            icon_map = {"positive": "🟢", "negative": "🔴", "neutral": "🟡"}
                            icon = icon_map.get(ss.get("status"), "⚪")
                            val = ss.get("raw_value")
                            name = ss.get("name", ss.get("signal_key", ""))
                            child_status_parts.append(f"{icon}{name}:{val}" if val is not None else f"⚪{name}")
                        st.caption(f"   🚦 " + " · ".join(child_status_parts))
                
                # 显示子项关联的断言
                for claim in child_claim_list:
                    status_icon = {"validated": "✅", "invalidated": "❌", "pending": "⏳"}.get(claim.get("verification_status", "pending"), "⏳")
                    subject = claim.get("subject") or claim.get("statement", "")[:20]
                    st.caption(f"   🧠 {status_icon} {subject}")
        
        st.markdown("---")

# 获取收藏文档并按层级分组
all_docs = fetch_latest_documents(limit=200)
starred_docs = [d for d in all_docs if (d.get("metadata_json") or {}).get("starred", False)]

# 获取知识点-文档关联数据
doc_links = get_all_knowledge_doc_links()

# 获取知识点-信号绑定数据，按 item_key 分组
all_bindings = get_knowledge_signal_bindings()
signal_bindings_map = {}
for b in all_bindings:
    key = b["item_key"]
    signal_bindings_map.setdefault(key, []).append(b)

# 所有信号定义，供绑定用
all_signal_defs = list_signal_definitions()

# ===== 章节名映射：KNOWLEDGE_TREE 分类名 → claims.chapter =====
# 知识点 key 格式: "P0 基础设施层|💻 AI芯片"，需映射到 chapter 如 "P0-基础设施/AI芯片"
CHAPTER_MAP = {
    "P0 基础设施层|💻 AI芯片": "P0-基础设施/AI芯片",
    "P0 基础设施层|🧠 存储与内存": "P0-基础设施/存储与内存",
    "P0 基础设施层|🖥️ AI服务器": "P0-基础设施/AI服务器",
    "P0 基础设施层|🔌 高速互联": "P0-基础设施/高速互联",
    "P0 基础设施层|📡 云计算/CapEx": "P0-基础设施/云计算",
    "P0 数据层|📊 训练数据": "P0-数据/训练数据",
    "P0 数据层|🏷️ 数据标注与RLHF": "P0-数据/标注与RLHF",
    "P0 数据层|🔒 数据治理": "P0-数据/数据治理",
    "P0 数据层|🔢 向量数据库": "P0-数据/向量数据库",
    "P0 软件层|🗡️ CUDA生态": "P0-软件/CUDA生态",
    "P0 软件层|🔧 AI框架": "P0-软件/AI框架",
    "P0 软件层|📦 MLOps": "P0-软件/MLOps",
    "P0 软件层|🔌 Agent框架": "P0-软件/Agent框架",
    "P1 能源电力层|⚡ 电力需求": "P1-能源/电力需求",
    "P1 能源电力层|🔋 电力供给": "P1-能源/电力供给",
    "P1 能源电力层|🌡️ 散热": "P1-能源/散热",
    "P1 半导体制造|🏭 晶圆代工": "P1-制造/晶圆代工",
    "P1 半导体制造|⚙️ 半导体设备": "P1-制造/设备材料",
    "P1 半导体制造|🧪 半导体材料": "P1-制造/设备材料",
    "P1 半导体制造|📦 封测": "P1-制造/封装测试",
    "P2 模型层|🧠 基础大模型": "P2-应用/AI Agent",
    "P2 模型层|🦾 Agent/具身智能": "P2-应用/具身智能",
    "P2 安全/治理层|⚖️ 合规与审计": "P3-认知/思维模型",
    "P2 安全/治理层|🛡️ AI安全": "P3-认知/投资框架",
    "P2 垂直应用层|🖥️ 开发/编程": "P2-应用/AI Agent",
    "P2 垂直应用层|📝 办公/知识": "P2-应用/AI Agent",
    "P2 垂直应用层|🔍 搜索/信息": "P2-应用/AI Agent",
    "P2 垂直应用层|🚗 智能驾驶": "P2-应用/自动驾驶",
    "P2 垂直应用层|🏥 医疗AI": "P2-应用/AI Agent",
    "P2 垂直应用层|💰 金融AI": "P2-应用/AI Agent",
}

# ===== 加载所有断言，按 chapter 分组 =====
_all_claims = list_claims(limit=500)
_claims_by_chapter = {}
for c in _all_claims:
    ch = c.get("chapter") or "未分类"
    _claims_by_chapter.setdefault(ch, []).append(c)

# 🔧 扩展 CHAPTER_MAP：自动推导子章节映射
for layer_cat, chapter in list(CHAPTER_MAP.items()):
    if "|" in layer_cat and layer_cat.count("|") == 2:
        # 已是子章节映射，跳过
        continue
    # 这是分类级映射，推导出子章节
    for ch in _claims_by_chapter:
        if ch.startswith(chapter + "/"):
            child_name = ch.split("/")[-1]
            key = f"{layer_cat}|{child_name}"
            if key not in CHAPTER_MAP:
                CHAPTER_MAP[key] = ch

# 🔧 反向：分类级 chapter 也关联到对应知识点的所有子项
# 例如 chapter="P0-基础设施/AI芯片" 应关联到 "P0 基础设施层|💻 AI芯片" 下所有子项
_reverse_map = {}  # chapter_prefix -> list of (layer_cat, child_name)
for k, v in CHAPTER_MAP.items():
    if v not in _reverse_map:
        _reverse_map[v] = []
    if k.count("|") == 2:
        _layer_cat, _child = k.rsplit("|", 1)
        _reverse_map[v].append((_layer_cat, _child))

# 层级图标映射
LAYER_ICON_MAP = {
    "P0 基础设施层": "💻",
    "P0 数据层": "📊",
    "P0 软件层": "🔧",
    "P1 能源电力层": "⚡",
    "P1 半导体制造": "🏭",
    "P2 模型层": "🤖",
    "P2 安全/治理层": "🔒",
    "P2 垂直应用层": "🚗",
}

# 按层级分组展示
for section, categories in KNOWLEDGE_TREE.items():
    priority_icon = "🔴" if "P0" in section else ("🟡" if "P1" in section else "⚪")
    layer_icon = LAYER_ICON_MAP.get(section, "📁")
    
    with st.expander(f"{priority_icon} {section}", expanded=True):
        # 先展示层的总览
        if "intro" in categories:
            intro = categories["intro"]
            st.info(f"{intro.get('goal', '')}\n\n{intro.get('output', '')}\n\n**{intro.get('insight', '')}**")
        
        cols = st.columns(2)
        for idx, (category, info) in enumerate(categories.items()):
            if category != "intro":
                render_category_with_docs(section, category, info, learned_items, cols[idx % 2], doc_links, starred_docs)

# ===== AI产业链6条核心链路 =====
st.divider()
st.subheader("📊 关键链路解读")

# 链路1
with st.expander("🔴 链路1：英伟达价值捕获链（最强护城河）"):
    st.markdown("""
```
ASML EUV → 台积电3nm → CoWoS封装 → HBM(SK海力士) → GPU(B200/Rubin)
    ↓                                              ↓
CUDA生态锁定 ←─────────────────── 云厂商CapEx $7250亿采购
    ↓
PyTorch/DeepSpeed → 闭源/开源模型 → 全部应用层
```
**关键节点**：CUDA、CoWoS、HBM是三个垄断瓶颈，任一断裂都会传导至整个链路
""")

# 链路2
with st.expander("🔵 链路2：去NVIDIA化替代链（长期威胁）"):
    st.markdown("""
```
Google TPU ← 博通ASIC设计 ← 台积电7nm
    ↓
AWS Trainium ← 自研 ← 台积电5nm
    ↓
Meta MTIA ← Marvell设计 ← 台积电5nm
    ↓
华为昇腾950 ← 中芯国际7nm ← 国产设备
```
**关键节点**：都绕不开台积电，除非国产7nm良率突破50%
""")

# 链路3
with st.expander("🟢 链路3：数据→模型→应用价值链"):
    st.markdown("""
```
原始数据 → Scale AI标注/RLHF对齐 → GPT-5/Claude训练
    ↓                                    ↓
合成数据(自我增强) ←─────── 反馈循环 ←── API调用
    ↓                                    ↓
向量数据库 ←─────────── RAG检索 ←──── Perplexity/Copilot
```
**关键节点**：数据飞轮效应——用户越多→数据越多→模型越强→用户更多
""")

# 链路4
with st.expander("🟡 链路4：能源约束链（物理瓶颈）"):
    st.markdown("""
```
AI机柜600kW → 万卡集群50MW → 需要小型核电站供电
    ↓                                    ↓
PUE 1.2→1.1 → 液冷渗透37%→50% → 维谛/英维克增长
    ↓                                    ↓
数据中心460→1050TWh → 超过日本全国用电 → 电网投资$万亿
```
**关键节点**：电力是AI的物理天花板，核电/SMR是终极解法
""")

# 链路5
with st.expander("🟠 链路5：光模块迭代链（投资节奏）"):
    st.markdown("""
```
GPU H100/B200 → 需要800G光模块 → 中际旭创/新易盛
    ↓
Rubin(2026H2) → 需要1.6T光模块 → 中际旭创领先
    ↓
Feynman(2027) → 需要3.2T? → 硅光技术突破
    ↓
CXL内存扩展 → 澜起科技Montage
```
**关键节点**：每一代GPU换机周期=光模块升级周期，2年一代
""")

# 链路6
with st.expander("⚫ 链路6：国产替代链（地缘驱动）"):
    st.markdown("""
```
ASML DUV(非EUV) → 中芯国际7nm(良率50%) → 华为昇腾910B/950
    ↓                                        ↓
北方华创/中微 → 刻蚀/CVD国产化 → 寒武纪/地平线
    ↓                                        ↓
南大光电 → 光刻胶国产化 → 端侧NPU/车载芯片
    ↓
国产CUDA替代 → 昇思MindSpore → 华为盘古模型
```
**关键节点**：EUV光刻机无法获得=先进制程被锁死=训练芯片性能差2-3代，但推理和端侧可以绕开
""")

# ===== 信号绑定 =====
st.divider()
with st.expander("🚦 知识点-信号绑定", expanded=False):
    st.markdown("将信号绑定到知识点，在学习时直接看到市场验证状态")

    # 构建知识点选项
    knowledge_items = []
    for section, categories in KNOWLEDGE_TREE.items():
        for category, info in categories.items():
            if category == "intro":
                continue
            item_key = f"{section}|{category}"
            knowledge_items.append((item_key, f"{section} > {category}"))
            if isinstance(info, dict) and "children" in info:
                for child in info.get("children", {}):
                    child_key = f"{section}|{category}|{child}"
                    knowledge_items.append((child_key, f"{section} > {category} > {child}"))

    if knowledge_items and all_signal_defs:
        col_k, col_s = st.columns(2)
        with col_k:
            ki_options = {ki[1]: ki[0] for ki in knowledge_items}
            selected_ki = st.selectbox("选择知识点", list(ki_options.keys()), key="bind_ki")
        with col_s:
            sd_options = {f"{s['signal_key']} - {s['name']}": s for s in all_signal_defs}
            selected_sd = st.selectbox("选择信号", list(sd_options.keys()), key="bind_sd")

        if st.button("🔗 绑定信号到知识点"):
            item_key = ki_options[selected_ki]
            signal_key = sd_options[selected_sd]["signal_key"]
            metric_key = sd_options[selected_sd]["metric_key"]
            bind_signal_to_knowledge(item_key, signal_key, metric_key)
            st.success(f"✅ 已绑定 {signal_key} → {selected_ki}")
            st.rerun()

        # 显示已有绑定
        st.divider()
        st.markdown("**已有绑定**")
        for ki_name, ki_key in ki_options.items():
            bindings = signal_bindings_map.get(ki_key, [])
            if bindings:
                for b in bindings:
                    col1, col2 = st.columns([5, 1])
                    with col1:
                        st.caption(f"  🚦 {ki_name[:30]} ↔ {b['signal_key']}")
                    with col2:
                        if st.button("❌", key=f"unbind_{ki_key[:10]}_{b['signal_key']}", help="取消绑定"):
                            unbind_signal_from_knowledge(ki_key, b["signal_key"])
                            st.rerun()
    else:
        st.info("需要先有信号定义才能绑定")

