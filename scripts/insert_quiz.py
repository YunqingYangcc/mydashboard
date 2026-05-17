"""录入P0-AI算力上游了解的试题"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from kb.storage import insert_quizzes, delete_quizzes_by_document_key

# 文档key
DOCUMENT_KEY = "6a5fd6267cedffcb"  # P0-AI算力上游了解

# 试题数据
questions = [
    # 一、技术本质辨析题
    {
        "question_type": "技术本质辨析题",
        "question_text": "HBM溢价的核心来源是什么？\n\n若认为'SK海力士HBM3e溢价5倍源于DRAM芯片成本'，错在哪里？",
        "options": [],
        "correct_answer": "普通DRAM与HBM的硅片成本差异仅约20%，溢价90%以上来自TSV堆叠工艺的良率损失与设备折旧。",
        "explanation": "关键陷阱：溢价主要来自工艺复杂度，而非材料成本。若某厂商宣称'自研HBM突破材料瓶颈'，需优先验证TSV堆叠工艺的良率数据。"
    },
    {
        "question_type": "技术本质辨析题",
        "question_text": "为何混合键合（Hybrid Bonding）是HBM4的必选项？\n\n传统热压键合（TCB）在16层堆叠时面临什么物理极限？",
        "options": [],
        "correct_answer": "混合键合使互连密度提升15倍，带宽密度达191倍，且HBM堆栈温度降低20%。传统TCB在16层堆叠时面临对齐精度和热应力导致的良率极限。",
        "explanation": "关键数据：若某设备厂商称其'热压键合可支持24层HBM'，需质疑其对齐精度是否能达到<1微米的要求。"
    },
    # 二、产业链博弈题
    {
        "question_type": "产业链博弈题",
        "question_text": "英伟达的'依赖-反制'双重策略如何运作？\n\n通过预付SK海力士20亿美元锁定产能，同时推动英特尔EMIB替代CoWoS，这两者是否存在矛盾？",
        "options": [],
        "correct_answer": "不矛盾。英伟达依赖HBM带宽实现GPU性能，但反制台积电垄断——EMIB产能扩张后，CoWoS议价权将从'60%产能占比'降至'50%以下'。",
        "explanation": "关键逻辑：若SK海力士要求HBM4e涨价30%，英伟达可能采取的反制手段包括：1) 引入三星作为第二供应商；2) 推动EMIB/自研封装技术；3) 调整GPU架构降低HBM依赖。"
    },
    {
        "question_type": "产业链博弈题",
        "question_text": "光模块毛利率分化的真实原因是什么？\n\n头部厂商（中际旭创）毛利率40%+ vs 二线厂商<25%，是否因'磷化铟材料成本差异'？",
        "options": [],
        "correct_answer": "材料成本仅占光模块总成本35%，核心差异在于客户绑定深度——英伟达认证厂商可跳过价格谈判直接进入供应名单。",
        "explanation": "关键事实：若某光模块公司宣称'自研硅光芯片降本20%'，仍难进入英伟达供应链的原因是缺乏客户认证和产能绑定。"
    },
    # 三、国产替代实操题
    {
        "question_type": "国产替代实操题",
        "question_text": "国产HBM量产的最大瓶颈是什么？\n\n若长江存储已量产232层3D NAND，是否意味着可直接复制HBM堆叠技术？",
        "options": [],
        "correct_answer": "HBM的TSV深宽比需达10:1（3D NAND仅5:1），且对齐精度要求<1微米（3D NAND容忍5微米）。两者工艺难度不在同一个量级。",
        "explanation": "关键差异：远见智存的'TSV冗余设计'通过预留部分TSV作为冗余来提升良率，需验证的测试数据包括：冗余TSV的激活率、温度循环后的可靠性、以及实际良率提升幅度。"
    },
    {
        "question_type": "国产替代实操题",
        "question_text": "先进封装国产替代的致命短板是什么？\n\n中微公司已推出TSV刻蚀设备，为何长电科技仍需进口应用材料设备？",
        "options": [],
        "correct_answer": "国产设备单机良率达标，但产线协同稳定性不足——HBM量产要求连续10万片晶圆的TSV孔径波动<±0.3微米。",
        "explanation": "核心矛盾：若某设备商称'国产混合键合设备良率达90%'，需追问的验证条件包括：1) 是否在实际产线上验证；2) 连续生产批次的良率稳定性；3) 与进口设备的对标测试数据。"
    },
    # 四、总结性判断题
    {
        "question_type": "总结性判断题",
        "question_text": "以下哪项是HBM产业链的长期确定性？",
        "options": ["A. HBM价格将随产能扩张持续下降", "B. 封装环节价值占比将从30%提升至50%+", "C. 英伟达将逐步放弃HBM转向定制化内存"],
        "correct_answer": "B",
        "explanation": "正确答案：B（HBM堆叠层数增加导致封装成本占比从HBM2的25%升至HBM4的48%）。关键依据：16层HBM中，TSV工艺成本占比超60%，且每增加4层堆叠，封装成本增幅达35%。"
    },
]

# 先删除旧数据（如果有）
delete_quizzes_by_document_key(DOCUMENT_KEY)
print(f"已清除文档 {DOCUMENT_KEY} 的旧试题")

# 插入新数据
count = insert_quizzes(DOCUMENT_KEY, questions)
print(f"✅ 成功录入 {count} 道试题！")
print(f"文档key: {DOCUMENT_KEY}")
