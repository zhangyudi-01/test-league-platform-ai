# MOD-06-03 竞彩赛程监控历史复用回顾

## 分析结论

旧比赛监控可以提供测试工程组织、来源数据造数、动态预期和清理方面的经验，但不能作为当前五个 `/sporttery/match-monitor*` 接口的契约。特别是旧列表和进程接口的参数、ID 域、SQL 表、筛选逻辑及页面交互均不同。

## 当前契约优先级

| 顺序 | 资料 | 用途 |
|---|---|---|
| 1 | [当前竞彩模块需求](../preanalysis/00-module-requirement-pack.md)、[模块已确认问题](../preanalysis/03-clarification-questions.md)、[API-001 已确认问题](../interfaces/API-001-get-match-monitor/clarification-questions.md) | 当前可观察业务行为和人工确认边界 |
| 2 | [当前 data-backend OpenAPI](../../../../global/source-materials/api-docs/league-api-definition/league-core-api/data-backend-openapi.json) | 当前五个接口的路径、参数和响应 schema |
| 3 | [第十三轮竞彩数据库设计](../../../../global/source-materials/database-docs/第十三轮冲刺竞彩抓取数据库设计和变更.md)、[最新 DDL](../../../../global/source-materials/database-docs/北单运营系统-test2_newgoal-202610261418.sql) | 当前竞彩来源表、事件、任务、备注表和约束 |
| 4 | 当前 `SportteryMatchMonitorController`、`SportteryMatchMonitorService`、`SportteryMatchMonitorRules`、Repository 和 DTO | 发现实现与契约差异、设计查询预期和测试数据要求；不替代需求验收标准 |
| 5 | 本回顾登记的历史需求、SQL、旧 OpenAPI、pytest、fixture 和 helper | 仅复用明确标记为可复用的测试工程经验 |

## 历史资料登记

| Ref ID | 资料 | 应阅读范围 | 复用判断 |
|---|---|---|---|
| REF-001 | [历史资料目录说明](../../../../global/source-materials/automation-contracts/data-bff/match-monitoring/README.md) | 全文，尤其“重要边界”和“使用规则” | 可复用：历史资料用途和契约隔离原则；不可沿用：其中旧 API 作为当前 API |
| REF-002 | [旧比赛列表需求](../../../../global/source-materials/automation-contracts/data-bff/match-monitoring/legacy-match-list/比赛列表模块需求.md) | 比赛列表和进程章节 | 可复用：历史页面字段来源与曾经处理的主客方向；不可沿用：奖期、批次、筛选、赛果审核及事件计数规则 |
| REF-003 | [旧列表数据准备分析 V2](../../../../global/source-materials/automation-contracts/data-bff/match-monitoring/legacy-match-list/查询结果数据准备需求分析V2.md) | 全文作为历史数据准备案例 | 可复用：逐字段追查数据来源、动态 SQL 预期、边界数据矩阵、清理策略的分析方法；不可沿用：SQL、表映射及字段优先级作为当前接口口径 |
| REF-004 | [旧列表 OpenAPI](../../../../global/source-materials/automation-contracts/data-bff/match-monitoring/legacy-match-list/查询比赛列表s-match.openapi.json) | `/s-match` operation 与响应 schema | 仅作 ID 域/字段演进对比；当前接口参数和响应必须重新从当前 OpenAPI 读取 |
| REF-005 | [旧进程需求](../../../../global/source-materials/automation-contracts/data-bff/match-monitoring/legacy-match-live/比赛进程信息需求.md) | 贝泰、纳米两节 | 可复用：事件顺序、position、比分主客映射等历史观察项；不可沿用：标签默认值、单来源调用方式、前端时间格式化成为当前接口断言 |
| REF-006 | [旧进程查询 SQL](../../../../global/source-materials/automation-contracts/data-bff/match-monitoring/legacy-match-live/比赛进程信息查询接口.sql) | 贝泰 SQL 和纳米 `JSON_TABLE` SQL | 可复用：通过独立 SQL 建立 position/score 方向预期的思路；不可沿用：旧审核/确认 CTE 作为当前接口过滤或关联谓词 |
| REF-007 | [旧进程 OpenAPI](../../../../global/source-materials/automation-contracts/data-bff/match-monitoring/legacy-match-live/s-match-live.openapi.json) | `/s-match/live` operation 与 response | 仅作字段历史参考；当前参数为 `sportId`、`sportteryMatchId`、可选 `matchId`，不得改用旧的 `namiMatchId` / `beitaiMatchId` 参数 |
| REF-008 | [旧进程实际返回示例](../../../../global/source-materials/automation-contracts/data-bff/match-monitoring/legacy-match-live/s-match-live实际接口返回内容.md) | 响应示例 | 可复用：识别历史字段的实际序列化形态；不作为当前响应完整性或 null 语义依据 |
| REF-009 | [旧列表 fixture](../../../../../test-league-platform/testsuites/data-bff/match_monitoring/conftest.py) | `monitoring_matches` | 可复用：测试池 fixture、yield teardown、由 `delete_bd_game_draw_data` 清理整批自造比赛的模式；需按当前真实数据依赖改造 |
| REF-010 | [旧列表脚本](../../../../../test-league-platform/testsuites/data-bff/match_monitoring/test_get_monitoring_list.py) | helper 结构、动态预期、临时修改后的 `finally` 恢复、pytest/Excel 参数化 | 可复用：单场选择、SQL 动态预期、数据快照恢复和参数化组织；不可沿用：旧接口查询参数和旧 `s-match` 返回断言 |
| REF-011 | [旧进程脚本](../../../../../test-league-platform/testsuites/data-bff/match_monitoring/test_get_match_live.py) | `assert_beitai_live`、`assert_nami_live`、方向预期、case 参数化 | 可复用：来源事件 helper、来源独立清理、事件列表逐字段动态预期和审核/确认方向场景；不可沿用：旧接口请求参数、旧 SQL 口径及旧测试假设 |
| REF-012 | [旧接口用例 Excel](../../../../../test-league-platform/data/data-bff/接口测试用例_查询比赛监控列表.xlsx)、[旧进程用例 Excel](../../../../../test-league-platform/data/data-bff/接口测试用例_查询比赛进程信息.xlsx) | 工作表结构、参数/处理数据约定和断言组织 | 可复用：团队 Excel 到 `CaseDict` 的数据驱动方式；不是当前五接口的用例清单 |
| REF-013 | [monitoring_data.py](../../../../../test-league-platform/common/monitoring_data.py) | `add_beitai_live_event`、`add_nami_football_live`、`audit_match_result`、`confirm_match_result` 及对应 delete helper；另核对 `add_match_anomaly`、`add_match_pre_warning` | 贝泰/纳米 live 和审核确认 helper 可作为当前 live 依赖的候选；`add_match_anomaly` / `add_match_pre_warning` 写入旧 `s_event`/`task`，不可用于当前竞彩事件表造数 |
| REF-014 | [draw.py](../../../../../test-league-platform/common/draw.py) | `create_bd_batch_matchup`、`filter_match_progress`、`set_bd_batch_matchup_on_sale`、`delete_bd_game_draw_data` | 可作为标准化比赛/正式赛程基础数据和 teardown 的候选；函数的明确职责是创建北单赛程，不可假定它创建竞彩官方 `sporttery_*_match` 行 |
| REF-015 | [source_events.py](../../../../../test-league-platform/common/source_events.py) | `add_match_on_sale_event` 与删除/清理实现 | 仅供旧 `s_event` 开售事件准备参考；当前 `/sporttery/match-monitor/events` 不查询 `s_event`，不要用它制造当前事件接口结果 |
| REF-016 | [旧人工事件说明](../../../../global/source-materials/automation-contracts/data-bff/match-monitoring/legacy-match-list/event-behavior/填写监控记录-新增异常函数.md)、[旧预警说明](../../../../global/source-materials/automation-contracts/data-bff/match-monitoring/legacy-match-list/event-behavior/填写监控记录-新增预警函数.md) | 事件写入表、任务表和清理逻辑 | 可复用：先查 helper 实际数据落点再采用的原则；不可沿用：目标表、event_type、task 计数或开售时间条件 |

## 复用决策

**API-002 已确认的进程承接**：用户确认竞彩进程沿用旧进程逻辑，额外增加 `if_change` 队序判断；按用户给出的范围决策，旧版代码未实现的篮球进程本轮不新增。旧版 `SMatchService.getSMatchLive`（竞彩开发前提交 `a8aa07c3`）仅访问纳米足球 live 和贝泰足球事件，旧进程 SQL 与 REF-011 测试也只覆盖足球来源。旧确认/当前用户审核/标准化方向处理因此作为进程承接背景；但旧接口请求参数、null 数组和旧 SQL 的具体取数条件不替代当前接口契约。详见 [API-002 问题单](../interfaces/API-002-get-match-live/clarification-questions.md)和[数据闭包](../interfaces/API-002-get-match-live/data-closures/ADC-001-live数据路径.md)。

**API-001 已确认的直播对象**：用户确认列表项沿用历史比赛监控的 `beitaiFootballMatchLiveDTO`。旧列表测试 REF-010 的 `_query_beitai_live_dto_map` 和 [历史列表服务](../../../../../../apps/league-platform/data-backend/src/main/java/com/league/backend/service/monitor/SMatchService.java) `buildMatch`、[当前贝泰 DTO](../../../../../../apps/league-platform/apiclient/src/main/java/com/league/client/dto/BeitaiFootballMatchLiveDTO.java) 支持 `matchId`、`status`、`matchStatus`、`matchClock`、`stoppageClock` 五个字段。REF-003 旧数据准备分析及 REF-004 旧 OpenAPI 只列四字段，不能据此省略 `matchStatus`；用户反馈开发已修复，新版 OpenAPI 已包含对象，本地源码版本及实际返回待核验。此确认只承接直播对象，不意味着旧列表筛选、事件 SQL 或整体响应均可沿用。详细路径见 [API-001 ADC-001](../interfaces/API-001-get-match-monitor/data-closures/ADC-001-列表贝泰直播数据路径.md)。

**造数清理审计补充**：`add_nami_football_live` 不只新增 Nami live 事件行，还会更新共享的 `s_match.nami_match_id`；配套 `delete_nami_football_live` 只删新增 live 行，不恢复该关联字段。若后续复用，调用方必须在准备前保存 `nami_match_id` 原值并在 `finally` 恢复；若比赛属于同次 fixture 且 teardown 会删除整条 `s_match`，也要确认依赖删除顺序后才能省略恢复。

| 主题 | 可带入的经验 | 不得继承的旧行为 | 当前落点 |
|---|---|---|---|
| 查询列表 | fixture 一次建立独立数据池；预期从 DB 独立查询；临时改动必须在 `finally` 恢复 | `/s-match` 的奖期/批次/编号筛选、手动排序、置顶、结果状态字段 | `preanalysis/DC-001` 描述当前 Sporttery 来源表和标准化补充链路 |
| 比赛进程 | 分来源准备事件，检查排序、主客 position、比分方向，按唯一 ID 清理；成功/异常路径分开 | 旧参数中的 `namiMatchId`/`beitaiMatchId`/`txMatchId`；旧“点击 tab 只请求一个来源”的 UI 请求约定 | `preanalysis/FC-002`、`preanalysis/DC-002` 和 `API-002` |
| 事件 | 用独立事件 ID 准备目标记录；核对 sport、source ID、来源及相同时间排序；写数据必须可删除 | 旧 `s_event` 开售前/后窗口、告警/变更/预警计数公式、`add_match_on_sale_event` 作为当前事件数据 | `preanalysis/DC-003` 和 `API-003`；数据准备 helper 需新增/确认写 `sporttery_match_event` 的实现 |
| 备注 | 多账号、唯一键、当前用户优先、重复保存后查询数据库验证；每次测试收尾精确清除账号/比赛/运动项目对应行 | 旧 `m_match_remark` 等备注表和非同一备注类型的写入路径 | `preanalysis/FC-003`、`preanalysis/DC-004`、`API-004`/`API-005` |
| 数据驱动 | 沿用 `api_test_data`、`CaseDict` 和 `DataBff` 的组织形式；一脚本一 operation | 把旧 Excel 工作表当作新 API 测试清单或将多个 operation 混到一个测试主体 | 新测试建议按当前 API ID 单独编写五个模块脚本；公共 fixture/helper 放到该新套件 `conftest.py`/common |

## 关键禁止项

- 不把旧 `/s-match` 和 `/s-match/live` 的路径、请求参数、成功/错误语义或完整响应实体复制到当前接口测试。
- 不将旧 `s_event` 和 `task` 的预警/告警/变更/开售时间 SQL 改名后当作 `sporttery_match_event` 查询。
- 不因 `create_bd_batch_matchup(filter_match_progress=True)` 选到有 progress 的标准比赛，就假定它已创建当前竞彩官方足球/篮球赛程行；必须从当前数据库读回并验证 `sporttery_*_match.match_id/s_match_id` 的真实关联。
- 不把 `common/monitoring_data.py` 中旧异常/预警 helper 当成当前事件 API 的构造器；先确认它实际 `INSERT` 的表。
- 不把账号密码、开发环境凭据、访问令牌或本机 `setting` 内容复制到分析文档、Excel 或测试代码。沿用项目既有认证 fixture/配置读取。

## 当前遗留输入

- 旧 Nami live helper 的 teardown 不恢复 `s_match.nami_match_id`；不得只调用它的 delete helper 后就认为现场完全清理。
- 当前模块确认了开发环境与账号来源原则，但没有固定可复用的竞彩官方足球/篮球样本，也未找到现成写入 `sporttery_match_event` 的通用 test helper。后续接口用例需要查询开发库确认样本，或在公共测试 helper 中新增精确、可清理的构造方法。
- `filter_match_progress=True` 只作为标准比赛进程样本的可选筛选方式；若共享测试数据不含进程事件，应使用当前已有 live source helper 或新增受控数据准备逻辑，不改变接口预期。
