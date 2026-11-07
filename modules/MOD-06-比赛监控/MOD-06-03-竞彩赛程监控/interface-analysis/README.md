# 竞彩赛程监控接口分析

## 目的

逐 operation 分析 MOD-06-03 的五个当前 data-backend 接口，为后续接口测试点、接口脚本和用例提供契约输入。此阶段不生成正式测试点、用例或脚本，也不改写 `preanalysis/` 中的需求原文与 RSU。

## 文件索引

| 文件 | 职责 |
|---|---|
| [Manifest](./interface-analysis-manifest.json) | API-ID、OpenAPI operation、RSU/DC、分析文件和计划脚本的机器索引 |
| [接口总览](./00-interface-overview.md) | 权威边界、五接口拓扑、追溯关系和接口分析发现 |
| [共享接口约定](./01-shared-contract.md) | 通用响应、ID 域、认证和数组/null 口径 |
| [API-001 列表](../interfaces/API-001-get-match-monitor/interface-analysis.md) | 赛程列表查询和聚合字段 |
| [API-001 问题单](../interfaces/API-001-get-match-monitor/clarification-questions.md) | 列表接口专属问题及确认结果 |
| [API-001 数据闭包](../interfaces/API-001-get-match-monitor/data-closures/README.md) | 列表贝泰直播状态数据路径 |
| [API-002 进程](../interfaces/API-002-get-match-live/interface-analysis.md) | 竞彩比赛到标准比赛及两类 live 响应 |
| [API-002 问题单](../interfaces/API-002-get-match-live/clarification-questions.md) | 篮球进程范围及历史逻辑承接确认 |
| [API-003 事件](../interfaces/API-003-get-match-events/interface-analysis.md) | 竞彩事件列表查询 |
| [API-003 问题单](../interfaces/API-003-get-match-events/clarification-questions.md) | 事件接口专属问题及模块问题引用 |
| [API-004 备注查询](../interfaces/API-004-get-match-remarks/interface-analysis.md) | 当前用户和其他用户备注列表 |
| [API-004 问题单](../interfaces/API-004-get-match-remarks/clarification-questions.md) | 参数、比赛存在性和字段必返性 |
| [API-005 保存备注](../interfaces/API-005-save-match-remark/interface-analysis.md) | 当前登录用户备注新增/更新 |

## 使用顺序

1. 先读 [历史复用回顾](../reference-analysis/match-monitoring-reuse-review.md)，了解可复用经验及已由当前需求或用户确认沿用的历史行为；其余旧行为不自动成为当前契约。
2. 再读 [preanalysis Context Pack](../preanalysis/01-context-pack.md)、[RSU 映射](../preanalysis/02-sentence-test-point-map.md)、[问题清单](../preanalysis/03-clarification-questions.md) 和接口实际引用的 FC/DC。
3. 生成或实现一个 API 时，读取本索引对应的接口分析、问题单（如已整理）、当前 OpenAPI operation、该 API 关联的 RSU/DC 和当前实现证据。
4. 对 [总览中的接口发现](./00-interface-overview.md) 未关闭项，不可把当前实现行为当作需求预期；优先按当前模块需求/已确认口径形成断言，并将差异记录为实现风险。

Manifest 中 `FC`/`DC` 引用模块级卡片；`AFC`/`ADC` 编号在各接口目录内独立，须结合对应 API 的分析文件和卡片索引定位，不能仅按编号跨接口查找。

## 当前状态

- API-001、API-002、API-003、API-004、API-005 已按单接口目录整理。
- API-005 的 Q-001 已回答，分析状态为 `ready`；长度按用户感知字符计算并包含首尾空格，OpenAPI 和源码差异待验证。
- API-004 分析状态为 `ready`；参数必填/可选不考虑，非法请求和比赛不存在暂按用户要求报错，空值口径待调试核对。本地 GET 未校验比赛存在，可能与暂定预期不同。
- API-001 的 Q-001 已回答，分析状态为 `ready`；用户反馈列表直播对象已修复，新版 OpenAPI 已定义该对象，本地源码版本及实际返回待核验。模块级 Q-001～Q-004 沿用原文件和 ID。
- API-002 的 Q-001 已回答，分析状态为 `ready`；沿用足球进程旧逻辑并增加竞彩队序判断，本轮不新增篮球进程。接口级 ADC-001 保留物理数据准备待核事项。
- API-003 引用已回答的模块 Q-003、Q-004；接口 Q-002 的事件 ID 必返和 Q-003 的空字符串原样返回已确认。接口 Q-001 中通用参数错误码已明确为 `2`，具体参数边界延期，分析状态为 `blocked`，已确定部分可先审核。本地 Service 的标题映射与用户确认口径存在差异，尚未验证实际部署。
- 各接口复用所需模块级 Context Card 和 Data Closure，未复制模块级闭包或问题答案。
- 五个测试脚本仍未创建。接口级差异只记录来源差异/实现风险，不自动改变需求口径。
