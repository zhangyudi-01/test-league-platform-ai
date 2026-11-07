# MOD-06-03 竞彩赛程监控需求前置分析

## 当前目标

建立竞彩赛程监控模块的完整逻辑基线、RSU 原文映射、问题清单、可复用上下文和最小数据库闭包，供后续生成接口测试点、功能测试点、测试方案、测试用例和五个测试脚本。本阶段不生成后续正式产物。

## 文件职责

| 文件 | 职责 |
|---|---|
| preanalysis-manifest.json | 前置分析产物和固定资源的机器契约 |
| 00-module-requirement-pack.md | 当前模块需求原文单一事实源 |
| 01-context-pack.md | 模块定位、能力、主链路和边界 |
| 02-sentence-test-point-map.md | 来源原文到 RSU-ID 的无损映射 |
| 03-clarification-questions.md | 已确认结论和待确认问题 |
| context-cards/ | 跨 RSU 可复用上下文 |
| data-closures/ | 最小业务数据路径和准备/清理契约 |

## 快速索引

- [Manifest](./preanalysis-manifest.json)
- [当前模块需求](./00-module-requirement-pack.md)
- [Context Pack](./01-context-pack.md)
- [RSU 映射](./02-sentence-test-point-map.md)
- [问题清单](./03-clarification-questions.md)
- [Context Cards](./context-cards/README.md)
- [Data Closures](./data-closures/README.md)
- [项目全局上下文](../../../../global/project-context.md)

## 补充分析阶段

- [历史比赛监控复用回顾](../reference-analysis/match-monitoring-reuse-review.md)：历史资料只作为复用参考，不取代当前需求/API 契约。
- [竞彩接口分析](../interface-analysis/README.md)：五个当前 API 的逐 operation 契约分析；不属于本 Skill 的产物，也不修改 RSU 原文。

## 分析流程

1. 通读当前模块两个需求包、全局上下文、第十三轮 PRD/PBL、当前 data-backend OpenAPI、数据库设计和既有比赛监控资料。
2. 以当前五个 sporttery match-monitor 路径为主契约，旧 /s-match 与 /s-match/live 仅作为历史参考。
3. 按语义完整契约建立来源结构、拆分决策和 RSU 映射，不按字段或标点机械拆分。
4. 区分接口返回、前端功能、数据库状态和历史复用边界。
5. 按列表、进程、事件、备注四条最小路径建立数据闭包。
6. 通过强校验后停止，后续阶段再生成正式测试点。

## 后续测试点生成输入

1. SRC-GLOBAL 项目全局上下文全文。
2. SRC-MOD 当前模块需求全文。
3. CTX 中的模块背景、能力、详细逻辑和理解边界。
4. 当前 RSU-ID 的完整映射行。

## 后续追溯关系

原始需求/接口/数据库/代码/确认 -> RSU-ID -> FC-ID/DC-ID -> 测试点 -> 方案/用例/脚本

## 约束

- 当前模块契约优先于旧比赛监控模块。
- 不把用户说明、代码实现或测试策略改写成需求原文。
- 不创建 ATP/STP、复杂度清单、测试点批次或正式测试点/方案/用例/Excel/脚本。
- 后续测试覆盖足球与篮球、默认参数、日期边界、空结果、未关联标准比赛、if_change、比分来源、事件任务颜色和备注用户唯一更新。
