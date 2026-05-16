# Markdown 研究模板

这是一版最小模板，目标是让你只写文档，系统自动抽取：

- `claims`
- `relations`
- `tasks`

## 推荐写法

```md
# 2026-05-16 NVDA 周观察

## 判断
- AI 基础设施周期仍未结束
- CoWoS 仍然限制 NVDA 出货
- NVDA 估值偏高，但还没到纯泡沫阶段

## 关系
- Hyperscaler CapEx -> drives -> GPU demand
- CoWoS -> constrains -> NVDA delivery
- Power constraints -> implies -> slower inference expansion

## 下周跟踪
- 看 Meta 最新资本开支表述
- 看 NVDA forward PE 是否回落
- 补一篇 HBM 供给链笔记
```

## 第一版规则

系统当前会识别这些标题：

- `## 判断`
- `## 断言`
- `## 结论`
- `## 观点`

会抽取为：

- `claims`

系统当前会识别这些标题：

- `## 关系`
- `## 图谱`
- `## 因果`

会抽取为：

- `relations`

关系写法支持两种：

```md
- CoWoS -> constrains -> NVDA delivery
- Hyperscaler CapEx drives GPU demand
```

支持的关系类型：

- `causes`
- `drives`
- `depends_on`
- `constrains`
- `competes_with`
- `supplies_to`
- `buys_from`
- `signals`
- `implies`
- `priced_by`
- `supports`
- `contradicts`

系统当前会识别这些标题：

- `## 下周跟踪`
- `## 任务`
- `## 下一步`
- `## Todo`

会抽取为：

- `tasks`

## 使用方式

1. 按上面模板写 Markdown
2. 放进 `data/inbox/`
3. 执行：

```bash
python3 -m kb.main ingest-all
```

## 当前边界

第一版是规则抽取，不是智能理解。

所以建议：

- 判断部分尽量一句话一条
- 关系部分尽量用英文关系词
- 任务部分尽量一条只写一个动作

这样抽取最稳定。

## 第二版更自由写法

如果你不想每次都写得很规整，当前也支持这些更自由的写法：

```md
判断：NVDA 护城河仍成立
关系：CoWoS 约束 NVDA delivery
任务：复核下季度 forward PE
```

也支持段落式内容：

```md
## 核心判断
AI 周期还处在基础设施扩张阶段。

## 待验证
观察微软最新资本开支口径
```

中文关系词也支持一部分：

- `驱动`
- `导致`
- `依赖`
- `约束`
- `限制`
- `意味着`
- `支持`
- `反驳`

推荐优先级还是：

1. 最稳：固定标题 + bullet
2. 次稳：固定标题 + 段落
3. 可用：`判断：...` / `关系：...` / `任务：...`
