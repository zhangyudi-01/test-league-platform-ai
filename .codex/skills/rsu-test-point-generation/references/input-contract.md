# Input Contract

## 定位与来源

调用参数中的模块目录是工作区根目录。优先使用显式 `--manifest`，否则只接受唯一可解析的 `preanalysis/v1` manifest；所有相对路径必须通过模块边界校验。旧项目才允许固定文件名兼容扫描。

manifest、RSU map、问题清单、Context/Data Closure Card 与其引用来源是需求事实。Runner 的简单/复杂判断只是本次调度计划，不写回前置分析产物。

## 逐 RSU 完整权威输入

`inputs/<RSU-ID>-input.md` 必须形成可独立复现的完整语义输入，并绑定业务 SHA-256。它至少包含：

1. 当前 RSU 的父级条件、原文内容、来源、位置、状态和顺序。
2. 当前 RSU 显式关联且已物化的支持 RSU。
3. manifest 三类固定资源角色对应的全局需求、模块需求和模块上下文正文。
4. 当前 RSU 关联问题的状态与结论。
5. 显式动态 FC/DC、配置、API、数据库或附件正文；纯追溯证据只保留路径、用途和 SHA-256，不递归复制整份附件。
6. 允许引用和必须引用的 RSU、Q、Context/Data Closure ID。
7. 生成规则、输出契约和候选模板。

数据库依赖应优先通过 DC 卡闭合当前规则涉及的表、字段、过滤、造数和观察方式，不为每个 RSU 默认注入整份数据库设计。

以下情况不得进入候选生成：相关 Q 为 `pending`、固定输入缺失、显式动态依赖缺失、来源状态不可接受、父级存在独立行为但没有对应 RSU 映射。`answered`、`deferred`、`out-of-scope` 是明确边界，可以进入输入。

## Foundation

Foundation 只加载：

- `SKILL.md` 与当前阶段所需稳定契约；
- 固定需求来源正文；
- manifest、资源角色、RSU map/Q 索引的稳定结构与 SHA-256 锚点；
- Data Closure 启用时的稳定闭包契约。

Foundation 不加载任何批次候选、兄弟 Worker 输出或后续阶段结果。状态记录 Foundation thread ID、固定来源指纹和创建时间；来源指纹变化后不得复用。

## Planning 输入

`planning-input.md` 包含全部 RSU 的语义摘要、稳定顺序、动态依赖集合、确定性上下文签名原料、来源指纹和计划 schema。Planner 只输出复杂度、批次和理由；不得修改 preanalysis。

计划必须覆盖全部且仅覆盖 manifest RSU。普通且签名兼容的 RSU 目标每批 4～6 个、最多 10 个；复杂 RSU 独立成批。

## 批次输入

每个计划批次包含：

- `batches/<BATCH-ID>-input.md`：批次模式、成员稳定顺序、上下文签名、动态依赖、完整 INPUT、delta、授权输出和各自 SHA-256。
- `session-inputs/<RSU-ID>-delta.md`：当前/支持 RSU、关联 Q、动态 FC/DC、证据、允许引用集合、完整输入哈希及 Foundation 锚点。
- `batches/<BATCH-ID>/<RSU-ID>.md`：Worker 唯一允许写的逐 RSU staging 候选。
- `batch-results/<BATCH-ID>/result.json`：批次聚合状态使用 `draft`、`partial`、`complete`、`replan-required`；逐成员使用 `draft`、`complete`、`failed`、`replan-required`。`failed` / `replan-required` 必须写具体理由。

delta 不重复 Foundation 已加载的固定需求和契约正文。它只能在 Foundation 身份与固定来源指纹一致的 fork 内使用。路径或哈希冲突时必须改读对应完整 INPUT；仍无法一致则停止。

父 Runner 中断后，聚合仍为 `draft` 但已有成员为 `complete` / `failed` / `replan-required` 的文件可作为部分恢复现场；全员仍为 `draft` 不构成进度。父 Runner 校验并提交合法完成成员后，只为未完成成员重新生成批次输入和 result 模板，已完成成员不再进入下一次活动成员集合。

`isolated` 模式不依赖 Foundation 记忆：每个 RSU 新建会话并读取该 RSU 完整输入，按顺序一次处理一个；finalization 和 readiness 同样各自读取完整阶段输入。

## Finalization 与 readiness

- `finalization-input.md`：完整模块汇总输入，包含规则、契约、全部已验证候选和模块来源。
- `finalization-session-input.md`：Foundation fork 轻量输入；不重复固定正文，但保留全部候选、RSU-MAP、Q-INDEX、动态来源、路径和 SHA-256。
- `case-readiness-input.md`：完整 readiness 输入。
- `case-readiness-session-input.md`：Foundation fork 轻量输入；保留最终测试点、覆盖矩阵、动态来源、路径和 SHA-256。

轻量阶段输入的文档 SHA-256 写入状态。固定来源、动态来源、候选、最终测试点或覆盖矩阵变化时，相关哈希必须变化并使下游失效。

## 事实优先级

物化文件内容与 SHA-256高于会话记忆。模型发现上下文被摘要、无法准确回忆、Foundation 身份不符或锚点冲突时，不得凭记忆继续；先读取阶段完整输入，仍不一致则停止并由父 Runner重新准备。
# 模块级基线输入补充

默认 `module-baseline` 路径先使用 `baseline-input.md` 汇集一次性模块业务事实：全部 RSU 清单、来源指纹、实际引用的问题、所有 RSU 已物化依赖的去重并集，以及未展开证据的路径/用途/哈希索引。不得把 manifest 中已登记但没有被 RSU 输入物化的超大来源正文无条件复制进基线，也不得将同一文件同时按 artifact 与 resource 别名重复展开。

父 Runner随后生成 `baseline-worker-packet.md`，把 `baseline-input.md` 的完整正文、精简生成 policy、结构化风险事实、当前来源指纹和精确 JSON output schema 合并为一个版本化 stdin payload。子 Worker 不读取 `baseline-input.md`、Skill、仓库路径、runner 日志或兄弟会话历史；它只返回 `semantic-baseline-v5` JSON。Baseline 必须先路由 simple/complex，并只为 simple RSU 生成候选。父 Runner保存私有结果后，为每个复杂 Scope 编译独立 packet，显式嵌入授权 RSU 与专属 FC/Q/DC 正文，再从 Baseline thread Fork 做首次生成。

packet 的恢复指纹必须覆盖 packet version、business input、policy、output schema、risk facts 和 current source fingerprints。超过 `--worker-packet-budget-bytes` 时记录 `context-pressure` 并停止，不允许静默退回模型分段读取文件。
