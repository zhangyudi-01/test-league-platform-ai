# 五接口共享契约

## 资源入口

| 资源 | 链接 | 用途 |
|---|---|---|
| 当前需求和问题答案 | [Preanalysis Context Pack](../preanalysis/01-context-pack.md)、[问题确认清单](../preanalysis/03-clarification-questions.md) | 模块逻辑和已确认答案 |
| 当前 OpenAPI | [data-backend OpenAPI](../../../../global/source-materials/api-docs/league-api-definition/league-core-api/data-backend-openapi.json) | 五个 operation 和 schema |
| 当前实现 | [Controller](../../../../../../apps/league-platform/data-backend/src/main/java/com/league/backend/controller/sporttery/SportteryMatchMonitorController.java)、[Service](../../../../../../apps/league-platform/data-backend/src/main/java/com/league/backend/service/sporttery/SportteryMatchMonitorService.java) | 参数校验、统一结果和具体读取行为 |
| DB 设计 | [第十三轮设计](../../../../global/source-materials/database-docs/第十三轮冲刺竞彩抓取数据库设计和变更.md)、[DDL](../../../../global/source-materials/database-docs/北单运营系统-test2_newgoal-202610261418.sql) | sporttery 表结构和键 |

## 通用请求与响应

| 约定 | 当前分析口径 |
|---|---|
| 传输 | 当前 API 描述的是 data-backend 的 `/sporttery/...` 路径；设计/权限表中对应管理端 BFF 路径以 `/data-backend/sporttery/...` 开始。测试使用既有 `DataBff` 客户端和 `DATA_BFF_URL`，按该项目封装路由。 |
| 通用包装 | 成功响应外层 `code=0`，`message` 为成功文案，业务内容位于 `data`；具体字段以各接口当前 schema 为准。 |
| 业务错误码 | 已声明的参数/业务校验失败通常是业务 `code=2`；live 另声明未预期服务异常 `code=31`。不要把 `HTTP status` 和 JSON `code` 混为一个断言。 |
| HTTP 响应 | 当前 OpenAPI 的 operation 主要只声明 HTTP 200 和成功 schema，没有系统性声明 4xx/鉴权错误 schema；错误 HTTP status 必须以真实 BFF 契约/项目基类为准，不能由 errorCode 描述推断。 |
| 认证 | 备注读/写明确依赖登录；live 下游处理审核方向时也访问当前用户上下文。接口测试从项目既有登录流程取得会话；凭据不写在本文档或 case 参数中。 |
| 列表与对象空值 | `data` 集合无成员时预期 `[]`；集合元素中的可空字段可为 `null`。备注保存的 `data` 是单个对象，不是单元素数组。此为 `preanalysis/Q-003` 已确认口径。 |
| ID 域 | `sportId` 是赛事类型隔离键：1 足球、2 篮球。竞彩官方比赛 `matchId` 不等于 `s_match.match_id`；列表 `matchId` 是竞彩官方 ID，进程 API 用 `sportteryMatchId` 找竞彩赛程，再解析其 `s_match_id`，可选 `matchId` 仅作关联校验。 |
| 错误参数建模 | OpenAPI 中 query/body fields 的 `required` 约束不完整；当前 Controller 对部分参数使用 `required=false` 接收后由 Service 返回业务 code=2。接口分析同时记录 schema 与 runtime validation，不用 schema 的 optional 误判为业务可省略。 |

## 四类数据域

| 域 | 当前表/来源 | 当前接口使用规则 |
|---|---|---|
| 竞彩源赛程 | `sporttery_football_match`、`sporttery_basketball_match` | 列表主表；业务日、竞彩编号、官方 `matchId`、竞彩队名/比分来源均来自对应运动表。 |
| 标准比赛和 live | `s_match`、下游 Nami/Beitai 足球 live 表 | 列表补标准状态/排名/比分和 provider match IDs；进程 API 按竞彩源行关联 `s_match_id` 读取 live。 |
| 当前竞彩事件和任务 | `sporttery_match_event`、`sporttery_task` | 列表事件计数/颜色读取当前事件域；事件详情从事件表读取，具体字段见模块 Q-004。旧实现额外限制 `source_type=SPORTTERY`；不要替换成旧 `s_event`/`task`。 |
| 竞彩备注 | `sporttery_match_remark` | 统一以 `sport_id + official match_id + remark_type=1` 隔离；账号唯一键由服务端当前用户提供。 |

## 分析与测试实现边界

- 当前 OpenAPI 和需求原文是被测契约；Service/Rules 是差异核查对象，不是“代码怎样就测怎样”的充分依据。
- DB 查询用于准备数据、独立计算预期、验证写入/清理；查询必须使用对应运动项目与 ID 域，不能只用相同数值的 `match_id`。
- `DataBff.test` 和 Excel/`CaseDict` 是历史团队脚本模式，可以复用框架外壳；一接口一脚本的映射见 [manifest](./interface-analysis-manifest.json)。
- 共享 fixture 应负责独立可执行的数据生命周期；每个 API 文件只编排该 operation 的场景，避免脚本互相依赖执行顺序。
