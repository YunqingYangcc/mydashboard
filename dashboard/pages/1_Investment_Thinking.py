import sys
from pathlib import Path

import streamlit as st
from streamlit_mermaid import st_mermaid

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dashboard.components import init_page_style, render_signature

init_page_style()

st.title("🧠 Investment Thinking")

# ============================================================================
# 流程图1：投资决策总思路
# ============================================================================

st.subheader("📊 Investment Decision Framework")

mermaid_chart = """
flowchart LR
    A["🚀 选择大趋势<br/>如AI/老龄化/能源革命"] --> B
    B["🔍 深挖细分领域<br/>找上/中/下游确定性环节"] --> C
    C["📡 跟踪产业周期信号<br/>等发令枪"] --> D{"🎯 关键信号<br/>是否出现?"}
    
    D -- "否" --> E["🔄 持续跟踪<br/>验证逻辑是否破坏"]
    E --> C
    
    D -- "是" --> F["💰 在业绩兑现前夜<br/>或市场错杀时买入"]
    F --> G["📊 持有并持续验证"]
    G --> H{"❓ 逻辑是否<br/>仍然成立?"}
    
    H -- "是" --> I{"🔥 市场是否<br/>过度疯狂?"}
    H -- "否" --> J["⛔ 认错止损离场"]
    
    I -- "是" --> K["✅ 分批卖出<br/>兑现利润"]
    I -- "否" --> G

    %% 样式定义 - WCAG AA 无障碍配色
    style A fill:#0173B2,stroke:#014F86,stroke-width:2px,color:#FFFFFF,font-weight:bold
    style B fill:#0173B2,stroke:#014F86,stroke-width:2px,color:#FFFFFF,font-weight:bold
    style C fill:#0173B2,stroke:#014F86,stroke-width:2px,color:#FFFFFF,font-weight:bold
    
    style D fill:#DE8F05,stroke:#A56803,stroke-width:2px,color:#FFFFFF,font-weight:bold
    style H fill:#DE8F05,stroke:#A56803,stroke-width:2px,color:#FFFFFF,font-weight:bold
    style I fill:#DE8F05,stroke:#A56803,stroke-width:2px,color:#FFFFFF,font-weight:bold
    
    style E fill:#808080,stroke:#505050,stroke-width:2px,color:#FFFFFF
    style F fill:#029E73,stroke:#016B4E,stroke-width:2px,color:#FFFFFF,font-weight:bold
    style G fill:#029E73,stroke:#016B4E,stroke-width:2px,color:#FFFFFF,font-weight:bold
    
    style J fill:#A30000,stroke:#6B0000,stroke-width:2px,color:#FFFFFF,font-weight:bold
    style K fill:#029E73,stroke:#016B4E,stroke-width:2px,color:#FFFFFF,font-weight:bold
"""

# 使用容器控制宽度，自适应大小
with st.container():
    st.markdown(
        """
        <style>
        /* 让 mermaid 图表自适应宽度 */
        [data-testid="stMarkdownContainer"] svg {
            width: 100% !important;
            height: auto !important;
            max-width: 100% !important;
        }
        /* 增大节点文字 */
        [data-testid="stMarkdownContainer"] .nodeLabel {
            font-size: 16px !important;
        }
        /* 增大边标签文字 */
        [data-testid="stMarkdownContainer"] .edgeLabel {
            font-size: 14px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st_mermaid(mermaid_chart)

st.divider()

# ============================================================================
# 流程图2：判断周期的四层知识框架总览
# ============================================================================

st.subheader("🔄 4-Layer Cycle Judgment Framework")

mermaid_chart2 = """
flowchart TD
    A[四层知识工具箱] --> B[第一层：基础规律<br>搞懂产业为什么有周期]
    A --> C[第二层：跟踪信号<br>盯住什么数据能验证周期来了]
    A --> D[第三层：交叉验证<br>把信号串起来下判断]
    A --> E[第四层：排除噪音<br>识别哪些是假启动]

    B --> B1[技术成熟度曲线<br>认清现在是在<br>狂热/绝望/复苏的哪一档]
    B --> B2[创新扩散曲线<br>判断产品是<br>极客玩具还是大众刚需]
    B --> B3[价值链微笑曲线<br>看清产业链里<br>谁在吃肉谁在喝汤]

    C --> C1[需求爆发的信号<br>付费用户加速/成本优化/大客户买了]
    C --> C2[供给出清的信号<br>技术路线统一/龙头份额集中/毛利率升]
    C --> C3[催化剂辨别<br>是真正的发令枪<br>还是最后的狂欢]

    D --> D1[四道必答题]
    D1 --> D1a[1. 它是否已离开绝望谷底?]
    D1 --> D1b[2. 它是否找到让普通人<br>不得不用的理由?]
    D1 --> D1c[3. 增速和利润数据<br>真在变好吗?]
    D1 --> D1d[4. 现在产业链上谁最赚钱<br>且确定性最高?]

    E --> E1[融资额高≠周期来了]
    E --> E2[大佬站台≠周期来了]
    E --> E3[自己和朋友在用≠周期来了]
    E --> E4[研报说万亿市场≠周期来了]
"""

with st.container():
    # 为第二张图添加更大的样式
    st.markdown(
        """
        <style>
        /* 第二张图专用样式 - 更大的节点 */
        .stMarkdown .mermaid .node rect,
        .stMarkdown .mermaid .node polygon {
            stroke-width: 3px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st_mermaid(mermaid_chart2)

st.divider()

# ============================================================================
# 流程图3：技术成熟度曲线和买卖时机
# ============================================================================

st.subheader("📈 Hype Cycle & Buy/Sell Timing")

mermaid_chart3 = """
flowchart LR
    A["💡技术触发<br/>极早期概念"] --> B["📈期望膨胀<br/>市场开始发疯"]
    B --> C["📉泡沫破裂<br/>绝望低谷"]
    C --> D["📈稳步复苏<br/>业绩开始兑现"]
    D --> E["🚀实质生产<br/>黄金增长期"]

    A -.->|"❌避免"| A
    B -.->|"⚠️风险极高<br/>可分批卖出"| B
    C -.->|"🔍深入研究<br/>寻找幸存者"| C
    D -.->|"✅理想买入区<br/>提前布局"| D
    E -.->|"✅持有并享受主升浪"| E
    E -.->|"⚠️当渗透率见顶<br/>考虑离场"| E

    style A fill:#9E9E9E,stroke:#616161,stroke-width:2px,color:#FFFFFF,font-weight:bold
    style B fill:#F44336,stroke:#C62828,stroke-width:2px,color:#FFFFFF,font-weight:bold
    style C fill:#FF9800,stroke:#E65100,stroke-width:2px,color:#FFFFFF,font-weight:bold
    style D fill:#4CAF50,stroke:#2E7D32,stroke-width:2px,color:#FFFFFF,font-weight:bold
    style E fill:#2196F3,stroke:#1565C0,stroke-width:2px,color:#FFFFFF,font-weight:bold
"""

with st.container():
    st_mermaid(mermaid_chart3)

st.divider()

# ============================================================================
# 流程图4：创新扩散的"黄金买入点"
# ============================================================================

st.subheader("🏆 Golden Buy Point in Innovation Diffusion")

mermaid_chart4 = """
flowchart LR
    subgraph 鸿沟 ["跨越鸿沟"]
        direction LR
        早期使用者 -->|"跨越的关键<br/>杀手级应用/易用工具/必买理由"| 早期大众
    end

    创新者["👨‍💻创新者<br/>2.5%"] --> 早期使用者["🔧早期使用者<br/>13.5%"]
    早期使用者 --> 早期大众["🏢早期大众<br/>34%"]
    早期大众 --> 晚期大众["👨‍👩‍👧晚期大众<br/>34%"]
    晚期大众 --> 落后者["🐌落后者<br/>16%"]

    早期使用者 -.->|"🚦等待信号确认"| 早期使用者
    早期大众 -.->|"🏁黄金买入与持有期"| 早期大众

    style 创新者 fill:#E8EAF6,stroke:#3F51B5,stroke-width:2px,color:#333
    style 早期使用者 fill:#C5CAE9,stroke:#3F51B5,stroke-width:2px,color:#333
    style 早期大众 fill:#3F51B5,stroke:#1A237E,stroke-width:3px,color:#FFFFFF,font-weight:bold
    style 晚期大众 fill:#C5CAE9,stroke:#3F51B5,stroke-width:2px,color:#333
    style 落后者 fill:#E8EAF6,stroke:#3F51B5,stroke-width:2px,color:#333
    style 鸿沟 fill:#FFF3E0,stroke:#FF9800,stroke-width:2px,color:#333
"""

with st.container():
    st_mermaid(mermaid_chart4)

st.divider()

# ============================================================================
# 流程图5：产业价值链的权力转移
# ============================================================================

st.subheader("💰 Value Chain Power Shift")

mermaid_chart5 = """
flowchart LR
    subgraph 初期 ["产业初期"]
        direction TB
        U1["上游<br/>关键技术/核心硬件"] -->|"高利润 强话语权"| M1["中游<br/>制造/集成"]
        M1 -->|"低利润"| D1["下游<br/>品牌/服务"]
    end

    subgraph 成熟期 ["产业成熟期"]
        direction TB
        U2["上游<br/>标准化/毛利下降"] -->|"话语权减弱"| M2["中游<br/>利润稳定"]
        M2 -->|"权力开始转移"| D2["下游<br/>拥有用户和数据"]
        D2 -->|"品牌与服务<br/>利润最高"| U2
    end

    初期 -->|"演变"| 成熟期

    style 初期 fill:#E3F2FD,stroke:#1976D2,stroke-width:2px,color:#333
    style 成熟期 fill:#E8F5E9,stroke:#4CAF50,stroke-width:2px,color:#333

    style U1 fill:#1976D2,stroke:#0D47A1,stroke-width:2px,color:#FFFFFF,font-weight:bold
    style M1 fill:#90CAF9,stroke:#1976D2,stroke-width:1px,color:#333
    style D1 fill:#BBDEFB,stroke:#1976D2,stroke-width:1px,color:#333

    style U2 fill:#A5D6A7,stroke:#4CAF50,stroke-width:1px,color:#333
    style M2 fill:#C8E6C9,stroke:#4CAF50,stroke-width:1px,color:#333
    style D2 fill:#4CAF50,stroke:#2E7D32,stroke-width:2px,color:#FFFFFF,font-weight:bold
"""

with st.container():
    st_mermaid(mermaid_chart5)

st.divider()

# ============================================================================
# 流程图6：启动型 vs 尾声型催化剂
# ============================================================================

st.subheader("🚀 Starter vs Ender Catalysts")

mermaid_chart6 = """
flowchart LR
    subgraph 启动 ["✅ 发令枪：周期开启的信号"]
        direction TB
        A1["某行业出现<br/>AI降本增效实绩"]
        A2["关键法律/法规<br/>扫清商业化障碍"]
        A3["巨头发布平台<br/>应用开发门槛骤降"]
    end

    subgraph 尾声 ["🚨 离场钟：疯狂见顶的信号"]
        direction TB
        B1["非主营公司<br/>改名蹭概念"]
        B2["媒体开始计算<br/>多年后市场规模"]
        B3["各种八竿子打不着的<br/>行业大会全冠上AI"]
    end

    启动 -.->|"✅ 买入/持有"| 启动
    尾声 -.->|"⚠️ 逐步卖出/清仓"| 尾声

    style 启动 fill:#E8F5E9,stroke:#4CAF50,stroke-width:2px,color:#333
    style 尾声 fill:#FFEBEE,stroke:#F44336,stroke-width:2px,color:#333

    style A1 fill:#66BB6A,stroke:#2E7D32,stroke-width:1px,color:#FFFFFF
    style A2 fill:#66BB6A,stroke:#2E7D32,stroke-width:1px,color:#FFFFFF
    style A3 fill:#66BB6A,stroke:#2E7D32,stroke-width:1px,color:#FFFFFF

    style B1 fill:#EF5350,stroke:#C62828,stroke-width:1px,color:#FFFFFF
    style B2 fill:#EF5350,stroke:#C62828,stroke-width:1px,color:#FFFFFF
    style B3 fill:#EF5350,stroke:#C62828,stroke-width:1px,color:#FFFFFF
"""

with st.container():
    st_mermaid(mermaid_chart6)

st.divider()

# ============================================================================
# 流程图7：常见错误信号
# ============================================================================

st.subheader("⚠️ Common False Signals")

mermaid_chart7 = """
flowchart LR
    W["⚠️ 不等于<br/>周期来临的信号"] --> X1["行业融资额<br/>屡创新高"]
    W --> X2["顶级大佬<br/>频繁为行业站台"]
    W --> X3["你或身边朋友<br/>觉得很好用"]
    W --> X4["研报预测<br/>万亿蓝海市场"]

    X1 -.->|"可能是资本在制造风口"| X1
    X2 -.->|"大佬可能有自身利益"| X2
    X3 -.->|"你们可能是小众人群"| X3
    X4 -.->|"他们几乎永远在预测"| X4

    style W fill:#FF9800,stroke:#E65100,stroke-width:3px,color:#FFFFFF,font-weight:bold
    style X1 fill:#FFE0B2,stroke:#FF9800,stroke-width:1px,color:#333
    style X2 fill:#FFE0B2,stroke:#FF9800,stroke-width:1px,color:#333
    style X3 fill:#FFE0B2,stroke:#FF9800,stroke-width:1px,color:#333
    style X4 fill:#FFE0B2,stroke:#FF9800,stroke-width:1px,color:#333
"""

with st.container():
    st_mermaid(mermaid_chart7)

# 签名
render_signature()
