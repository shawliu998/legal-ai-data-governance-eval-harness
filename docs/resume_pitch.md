# Resume And Pitch Notes

## Project Name

Legal AI Data Governance Eval Harness

中文项目名可写：

法律 AI 数据闭环治理评测原型

## One-Line Summary

Built a leakage-safe legal AI evaluation and data-loop governance prototype that turns legal model failures into structured data actions: eval, SFT, preference, badcase, and human review.

中文一句话：

构建法律 AI 数据闭环治理原型，覆盖 gold label 防泄漏、多任务 rubric 评测、normalized run log、错误标签标准化、人审队列和 badcase-to-data routing。

## Resume Bullets

中文简历版：

- 设计并实现法律 AI 数据闭环治理评测原型，覆盖 85 条法律诊断样本、380 条 rubric item、546 条 normalized model run，任务类型包括咨询、案例分析和文书起草。
- 拆分 `Eval_Input`、`Gold_Labels`、`Rubric_Items` 三层数据结构，保证被测 Agent 不读取 gold label，仅 Judge 和 Human Review 使用标注与 rubric。
- 实现多版本 prompt 评测、task-specific LLM Judge、标准化错误标签和 data router，将 badcase 自动路由到 `eval`、`sft`、`preference`、`badcase`、`human_review`。
- 生成 Executive Dashboard，用于展示任务覆盖、错误模式、人审队列和推荐数据生产动作，强调数据治理决策而非模型排名。

英文简历版：

- Built a leakage-safe Legal AI Data Governance Eval Harness with 85 diagnostic samples, 380 rubric items, and 546 normalized model runs across consultation, case analysis, and document drafting tasks.
- Designed strict `Eval_Input` / `Gold_Labels` / `Rubric_Items` separation so tested agents cannot access gold labels while Judge and Human Review can use full annotation context.
- Implemented task-specific rubric-based LLM judges, standardized error taxonomy, human review queueing, and error-to-data routing across eval, SFT, preference, badcase, and human-review workflows.
- Generated an executive dashboard for dataset coverage, error patterns, badcase cards, routing mix, and recommended data actions, positioning the project as data governance rather than model ranking.

## 150-250 字中文投递摘要

我做了一个法律 AI 数据闭环治理评测原型，重点不是搭建法律问答系统，也不是做模型排行榜，而是展示法律数据产品能力。项目将样本拆成 Agent 可见的 `Eval_Input`、Judge/Human Review 可见的 `Gold_Labels` 和 `Rubric_Items`，避免 gold label 泄漏；支持咨询、案例分析、文书起草三类任务；用 normalized run log 支持多模型、多 prompt version、多 run；通过 task-specific LLM Judge 生成评分、错误标签和风险判断；再由 router 将失败样本路由到 eval、SFT、preference、badcase 或 human_review。最终 dashboard 展示任务覆盖、错误模式、人审队列和推荐数据动作，用于支撑法律 AI 数据生产决策。

## 1 分钟面试讲稿

这个项目我定位成法律 AI 数据闭环治理原型，不是法律咨询产品，也不是模型排行榜。核心问题是：当法律 Agent 输出有风险时，我们怎么把失败转化成可复用的数据资产。

我把数据拆成 `Eval_Input`、`Gold_Labels` 和 `Rubric_Items`，保证被测 Agent 只能看到输入，Judge 和 Human Review 才能看到标注。实验层使用 normalized run log，一行一个 run，支持多模型、多 prompt version 和三类法律任务。评分层使用 task-specific judge prompts，分别评价咨询、案例分析和文书起草。最后 router 根据错误类型、风险等级和 judge confidence，把样本路由到 eval、SFT、preference、badcase 或 human_review。

最终 dashboard 展示的不是哪个模型最好，而是下一步应该生产什么数据、哪些 badcase 需要人审、哪些错误适合训练或回归评测。

## 3 分钟面试讲稿

我做这个项目时先划定边界：不做 RAG、不做 Web UI、不做数据库、不做自动法条检索。因为两天内投递项目最应该体现的是数据产品能力，包括任务拆解、标注隔离、评测结构、错误归因和数据回流。

第一层是数据结构。我把样本拆成三层：`Eval_Input` 只给 Agent，包括用户问题、已知事实、法律概念、地区、任务类型等；`Gold_Labels` 只给 Judge 和 Human Review，包括关键缺失事实、预期追问、预期答案点、风险点和人审备注；`Rubric_Items` 是可评分的原子 rubric。这样可以避免评测里常见的 gold label 泄漏。

第二层是实验流程。项目支持 V0 直接回答、V1 固定法律回答结构、V2 blind review agent、V3 workflow agent。V2 只能看用户问题、已知事实、法律概念和 V0 输出，不能看 gold label。所有输出进入 normalized run log，一行代表一次模型运行，所以可以扩展到多模型、多版本、多 run。

第三层是治理闭环。Judge 按任务类型选择不同 prompt：咨询看缺失事实和追问质量，案例分析看结论、事实、推理和依据，文书起草看结构、诉请或抗辩、事实组织和风险遗漏。Judge 输出统一评分维度、错误标签、风险等级和置信度。Router 再把错误转成固定 data route：`eval`、`sft`、`preference`、`badcase`、`human_review`。

我会重点展示两个案例：L-004 调岗降薪咨询被路由到 human_review，因为模型不能直接建议用户拒绝到岗；L-008 定金/订金争议被路由到 preference，因为它适合构造成“直接下结论”与“先区分术语和违约方”的偏好对。这个项目的价值在于把法律 AI 输出失败转成数据生产决策，而不是只停留在打分。

## Interview Talking Points

- Gold label 防泄漏是项目可信度的底线。
- V2 blind review 的设计说明评测流程里也要控制信息可见性。
- normalized run log 让实验矩阵能扩展，而不是宽表堆列。
- error taxonomy 的价值是让 badcase 能被聚合、统计和路由。
- data route 的价值是把评测结果转化成下一步数据动作。
- dashboard 的定位是数据生产决策面板，不是模型排行榜。

## GitHub Link Template

```text
https://github.com/shawliu998/legal-ai-data-governance-eval-harness
```

投递消息里可写：

```text
我附上一个两天内完成的法律 AI 数据治理评测项目，重点展示 gold label 防泄漏、多任务 rubric 评测、badcase 分析、人审队列和 error-to-data routing。项目不是法律问答 demo，而是面向法律 AI 数据生产决策的闭环原型。
```
