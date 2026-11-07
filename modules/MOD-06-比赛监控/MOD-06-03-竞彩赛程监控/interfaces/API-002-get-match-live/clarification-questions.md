# API-002 比赛进程接口问题确认清单

## 引用入口
- [接口分析](./interface-analysis.md)
- [模块问题清单](../../preanalysis/03-clarification-questions.md)：Q-003 已确认空集合和元素字段空值，沿用原编号。
- [API-001 问题清单](../API-001-get-match-monitor/clarification-questions.md)：列表状态展示字段归属由该接口 Q-001 记录，与篮球进程范围不同。

## 已确认问题与结论
模块 Q-003 已回答，不重复登记。

| Q-ID | 关联来源 | 状态 | 确认结论 | 回填位置 |
|---|---|---|---|---|
| Q-001 | 当前需求比赛列表规则 1.1、6；OpenAPI `/sporttery/match-monitor/live`；旧 `/s-match/live` 服务 `getSMatchLive`；[历史进程需求](../../../../../global/source-materials/automation-contracts/data-bff/match-monitoring/legacy-match-live/比赛进程信息需求.md)；[历史复用回顾](../../reference-analysis/match-monitoring-reuse-review.md) | answered | 原问题：列表包含篮球，但当前响应和读取逻辑使用足球实体，是否需要篮球进程。用户确认竞彩进程沿用原进程逻辑，只增加 `if_change` 调换；旧代码若未加篮球就不需要新增篮球进程。核对旧版 `SMatchService.getSMatchLive`（竞彩开发前提交 `a8aa07c3`）仅查询纳米足球 live 和贝泰足球事件，无篮球进程分支，因此本接口本轮只分析足球进程，不虚构篮球专属数据源或返回规则。`sportId=2` 在当前入口被接受不等于已实现篮球进程；其返回为空数组或错误均未经确认。 | [接口分析](./interface-analysis.md)第 1、2、3、4、7、8 节；[ADC-001](./data-closures/ADC-001-live数据路径.md)；模块 FC-002、接口总览 IAF-004。 |

## 待确认问题
| Q-ID | 关联来源 | 状态 | 问题与影响 | 需要确认 | 未确认时的处理 |
|---|---|---|---|---|---|

当前无待确认问题。
