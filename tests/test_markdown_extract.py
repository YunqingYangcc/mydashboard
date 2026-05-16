from kb.markdown_extract import extract_from_markdown


def test_extract_markdown_sections():
    content = """
# NVDA 周观察

## 判断
- AI 基础设施周期仍未结束
- CoWoS 仍然限制 NVDA 出货

## 关系
- Hyperscaler CapEx -> drives -> GPU demand
- CoWoS constrains NVDA delivery

## 下周跟踪
- 看 Meta 最新资本开支表述
- 补一篇 HBM 供给链笔记
""".strip()

    result = extract_from_markdown(content)

    assert len(result.claims) == 2
    assert len(result.relations) == 2
    assert len(result.tasks) == 2
    assert result.relations[0]["relation_type"] == "drives"
    assert result.relations[1]["relation_type"] == "constrains"


def test_extract_markdown_header_variants():
    content = """
## 判断（更新）
- NVDA 护城河仍成立

## 下周跟踪（优先）
- 看 forward PE
""".strip()

    result = extract_from_markdown(content)

    assert len(result.claims) == 1
    assert len(result.tasks) == 1


def test_extract_markdown_paragraphs_and_prefixes():
    content = """
判断：NVDA 护城河仍成立
任务：复核下季度 forward PE
关系：HBM -> drives -> GPU demand

## 核心判断
AI 周期还处在基础设施扩张阶段。

## 关键关系
CoWoS 约束 NVDA delivery

## 待验证
观察微软最新资本开支口径
""".strip()

    result = extract_from_markdown(content)

    assert len(result.claims) == 2
    assert len(result.relations) == 2
    assert len(result.tasks) == 2
    assert {item["subject"] for item in result.claims} == {"NVDA", "AI 周期"}
    assert {item["relation_type"] for item in result.relations} == {"drives", "constrains"}


def test_guess_subject_from_claim_text():
    content = """
## 判断
- Meta 资本开支仍将支撑 GPU 需求
- AI 基础设施没有进入衰退期
""".strip()

    result = extract_from_markdown(content)

    assert result.claims[0]["subject"] == "Meta"
    assert result.claims[1]["subject"] == "AI 基础设施"
