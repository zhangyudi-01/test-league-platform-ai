# 输入契约

## 就绪门禁

开始规划前，模块前置分析、最终测试点和 `test-case-readiness.md` 必须通过上游校验；模块与全部 TP 为 `ready`，`execution-context.md` 无 `pending`。不满足时停止，不生成正式计划、SQL 或用例。

## 模块规划输入

`planning-input.md` 一次包含：

- 最终测试点全文；
- readiness 与执行上下文；
- 本模块最终 TP 实际引用的模块需求、Context、DC 和相关动态资源；
- SQL 边界、批次规则和来源 SHA-256。

该输入用于生成 `generation-plan.json`。规划必须给每个 TP 唯一批次归属，并在写 SQL 前确定哪些 TP 真正需要数据库查询核对。

## SQL 输入

有计划 SQL 时，`sql-generation-input.md` 包含已验证 SQL 计划、计划中 `tp_refs` 实际引用的模块需求与 Context、相关 DC/表结构事实以及执行上下文。SQL worker 不依赖规划分支记忆，只生成计划中的 SELECT，不扫描其他模块或临时增加 SQL。

## 批次输入

`inputs/BATCH-xxx-input.md` 列出当前批次的 TP、模式、计划 SQL、各 TP delta、输出路径和所需基线。批次 worker 只处理该清单。

完整 `inputs/<TP-ID>-input.md` 仍保留用于审计、复现、漂移检测和 `isolated` 模式；默认 `module-session` 使用模块基线、必要上下文基线和 TP delta，避免重复输入固定正文。`generation-state.json` 负责“执行到哪”，输入文件负责“依据什么事实”，二者职责不同。

## 漂移

状态锁定 manifest、最终测试点、readiness 和执行上下文哈希。任一来源变化后必须人工确认并运行 `init_generation.py --refresh`；旧产物归档到 `history/`，不得手改状态绕过。
