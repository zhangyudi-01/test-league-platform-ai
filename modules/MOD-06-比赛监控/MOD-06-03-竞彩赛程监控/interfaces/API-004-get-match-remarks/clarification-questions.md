# API-004 `listRemarks` 问题确认清单

## 引用入口
- [接口分析](./interface-analysis.md)
- [模块问题清单](../../preanalysis/03-clarification-questions.md)

## 已确认问题与结论
模块 Q-003 确认无元素返回 `[]`、元素字段无值为 `null`；保留原 ID。模块 Q-002 记录环境和登录准备，不作为业务预期。

| Q-ID | 关联来源 | 状态 | 确认结论 | 回填位置 |
|---|---|---|---|---|
| Q-001 | OpenAPI 参数及错误；[通用错误码](../../../../../global/source-materials/api-docs/Vegas2.0接口错误码.md)；本地 `listRemarks`；用户答复 | answered | 本轮不考虑参数必填或可选。用户确认已登录时非法参数按业务 `code=2`（参数错误）判定，不严格限定 HTTP 状态、具体文案或错误 `data`。同时未登录时仍不限定认证与参数校验的优先级；若确认进入 operation 的参数校验分支则核对 `code=2`，不得要求认证层拦截也返回该 code。本次更新替代此前“只要报错即可”的宽松判据。 | 接口分析第 3、7、8 节 |
| Q-002 | 用户先后答复；[通用错误码](../../../../../global/source-materials/api-docs/Vegas2.0接口错误码.md)；竞彩监控列表及备注调用链；本地 `listRemarks` | answered | 正常页面先查列表，再传选中比赛 ID；用户确认已登录时比赛不存在按参数错误业务 `code=2` 判定，不严格限定 HTTP 状态、具体文案或错误 `data`，替代此前“只要报错即可”的宽松判据。本地查询未检查比赛是否存在，可能成功返回空列表或残留备注，部署行为未验证。 | 接口分析第 1、3、4、5、7、8 节 |
| Q-003 | 用户 2026-11-02 答复；模块 Q-003；[响应模型](../../../../../global/source-materials/api-docs/monitor/SportteryMatchRemarkItem.java)；[后端服务](../../../../../../../apps/league-platform/data-backend/src/main/java/com/league/backend/service/sporttery/SportteryMatchMonitorService.java) `toRemarkItem` | answered | 暂按集合无记录返回 `[]`，记录内字段无值返回 `null`；参照响应模型及服务映射核对八个字段。用户确认先采用此口径，调试不一致再调整；本地实现观察不是线上验证。 | 接口分析第 5、7、8 节 |

## 待确认问题

当前无待确认问题。
