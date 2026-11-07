# API-002 竞彩比赛进程接口分析

> operation：`GET /sporttery/match-monitor/live`，`getSMatchLive`  
> 分析状态：`ready`（本轮范围为足球进程）

## 1. 接口定位与结论摘要

调用方以运动项目和竞彩官方比赛 ID 获取比赛进程，服务先解析关联的标准比赛，再返回纳米和贝泰两个来源的足球进程集合。用户本轮确认：沿用原比赛进程逻辑，只增加竞彩 `if_change` 队序判断；旧代码没有篮球进程分支，本轮不新增。事件主客方和比分应与竞彩列表队序一致；集合无元素返回 `[]`，元素内无值字段为 `null`。本次补读旧代码、SQL 和测试脚本，恢复上一版遗漏的确认/审核方向上下文，并关闭篮球范围问题；旧请求参数及旧空值表现不因此成为当前契约。

## 2. 分析范围与依据

管理端 BFF 路径 `/data-backend/sporttery/match-monitor/live`；调用关系见[接口总览](../../interface-analysis/00-interface-overview.md)。本接口与列表、事件、备注读写分开，不含来源选择、分页或排序参数。认证字段及失效响应未在此 operation 单独定义，不记录凭据。

| 来源 | 定位及用途 |
|---|---|
| [当前需求](../../preanalysis/00-module-requirement-pack.md) | 比赛列表规则 2.6、2.8、2.9、规则 6：队序、状态和点击进程；规则 6 引用“比赛赛程监控” |
| [进程需求](../../../../../global/source-materials/automation-contracts/data-bff/match-monitoring/legacy-match-live/比赛进程信息需求.md) | 当前需求引用的第（9）节规则 1、3、4；不继承旧接口参数和单来源 tab 请求方式 |
| [旧进程 SQL](../../../../../global/source-materials/automation-contracts/data-bff/match-monitoring/legacy-match-live/比赛进程信息查询接口.sql) | 贝泰 `match_base/match_direction` 和纳米 `JSON_TABLE`：来源字段、旧确认/审核/标准方向及事件顺序；历史 SQL 的筛选、取首条逻辑不是当前直接可用的独立预期 |
| [旧进程脚本](../../../../../../test-league-platform/testsuites/data-bff/match_monitoring/test_get_match_live.py) | `_query_expected_beitai_events`、`_is_display_swapped`、`_expected_nami_incidents`、`assert_beitai_live/assert_nami_live`：复核来源字段、方向和历史测试范围；旧单来源参数及 null 数组不继承 |
| 旧版 `SMatchService.getSMatchLive`，提交 `a8aa07c3`；竞彩开发提交 `6b35db01` 的同文件差异 | 旧版仅查询 `namiFootballMatchLiveRepository`、`beitaiFootballEventRepository` 和 `beitaiFootballMatchRepository`；竞彩开发将其提取为可接收已解析比赛的公共分支，未新增篮球分支。作为本轮 Q-001 的代码证据，而非推定篮球返回体。 |
| [模块问题](../../preanalysis/03-clarification-questions.md) | Q-003：空集合及元素字段空值；已确认逻辑摘要：进程方向对齐竞彩队序 |
| [接口问题 Q-001](./clarification-questions.md) | 用户确认承接旧进程逻辑并增加 `if_change`；按旧实现结果确定不新增篮球进程 |
| [OpenAPI](../../../../../global/source-materials/api-docs/league-api-definition/league-core-api/data-backend-openapi.json) | `/paths/~1sporttery~1match-monitor~1live/get`；`components/schemas/CommonResultSMatchLiveIncidentsResponse`、`SMatchLiveIncidentsResponse`、`SMatchLiveIncidentsDTO`、`BeitaiFootballEventEntity` |
| [FC-002](../../preanalysis/context-cards/FC-002-竞彩进程解析链路.md)、[DC-002](../../preanalysis/data-closures/DC-002-进程解析数据闭包.md) | 复用官方比赛、标准比赛和队序语义；物理路径缺口由 [ADC-001](./data-closures/ADC-001-live数据路径.md) 补充 |
| [竞彩服务](../../../../../../../apps/league-platform/data-backend/src/main/java/com/league/backend/service/sporttery/SportteryMatchMonitorService.java) `getSMatchLive/changeSMatchLiveIncidentsResponse`、[下游服务](../../../../../../../apps/league-platform/data-backend/src/main/java/com/league/backend/service/monitor/SMatchService.java) `getSMatchLiveForResolvedMatch/getSMatchLive/buildSMatchLiveIncidents` | 当前实现与差异证据，不替代需求 |
| [DDL](../../../../../global/source-materials/database-docs/北单运营系统-test2_newgoal-202610261418.sql) | `s_match`、`beitai_football_event`、`nami_football_match_live`、`beitai_football_match`、`bd_batch_matchup`、`event_match_check` 的表字段和键 |
| [参考复用回顾](../../reference-analysis/match-monitoring-reuse-review.md) | REF-005～008、REF-011 及“比赛进程”复用决策；本轮确认承接原进程行为，不套用旧接口参数或旧 SQL 作为新接口最终判据 |

## 3. 请求与接口契约

| 参数 | 位置及类型 | 契约与现状 |
|---|---|---|
| `sportId` | query，int32 | description 必传，参数却标 `required:false`；当前入口接受足球 `1`、篮球 `2`，分别选对应竞彩表。本轮按已回答 [Q-001](./clarification-questions.md) 只覆盖足球进程，不据入口接受 `2` 推断存在篮球进程或其返回结果。 |
| `sportteryMatchId` | query，int64 | description 必传，参数却标 `required:false`；竞彩官方比赛 ID，不是标准比赛 ID。当前实现要求正数。 |
| `matchId` | query，int32 | 可选，传入时必须等于竞彩记录关联的 `s_match.match_id`，不能替代官方 ID；无默认值。 |

OpenAPI 未定义空字符串、重复参数、显式 null 或类型转换失败的结果；Java `@ModelAttribute` 绑定失败是否进入控制器及 HTTP 状态未验证。当前服务先校验项目/官方 ID，再查竞彩行、检查关联及可选 ID，最后查标准比赛；多个错误并存的优先级不是已确认业务契约。

| 条件 | OpenAPI 描述 | 当前服务观察 |
|---|---|---|
| 请求参数错误 | code `2`，描述“请求参数错误” | message `比赛进程查询参数错误`；包括不支持项目、缺必需值或官方 ID 非正数 |
| 竞彩比赛不存在 | code `2`，描述“竞彩比赛不存在” | message `竞彩比赛不存在` |
| 未关联标准比赛 | code `2`，描述“尚未关联标准比赛” | message `竞彩比赛尚未关联标准比赛` |
| `matchId` 不一致 | description 要求一致，归参数错误 code `2` | message `matchId 与竞彩比赛关联的标准比赛不一致` |
| 标准比赛不存在 | 未单列 | code `2`，message `标准比赛不存在`，为实现观察 |
| 服务异常 | code `31`，描述“服务异常” | 下游捕获异常返回服务异常，message 可能包含系统信息 |

OpenAPI 仅声明 HTTP `200` 成功响应 schema，未分别定义错误 HTTP 状态、错误 `data` 和精确 message；条件描述不等于 HTTP 状态。框架绑定错误不猜测，实际 message 不是已确认业务文案。

## 4. 业务规则与数据处理流程

1. 以项目和官方 ID 查询对应竞彩赛程，取 `s_match_id`、验证可选 `matchId`，再定位标准比赛。官方 ID 与标准比赛 ID 是不同 ID 域。[FC-002](../../preanalysis/context-cards/FC-002-竞彩进程解析链路.md)
2. 根据标准比赛的纳米与贝泰来源标识分别定位进程；没有 provider 参数，不能沿用旧接口按 tab 传来源 ID 的请求规则。物理读取和缺失分支见 [ADC-001](./data-closures/ADC-001-live数据路径.md)。
3. 贝泰承接旧进程的九类事件：`match_started`、`break_start`、`injury_time_shown`、`match_ended`、`red_card`、`yellow_card`、`yellow_red_card`、`substitution`、`score_change`，按 `order_id` 升序；纳米按来源 incidents 原有顺序。规则来源为[进程需求](../../../../../global/source-materials/automation-contracts/data-bff/match-monitoring/legacy-match-live/比赛进程信息需求.md)第（9）节 3～4、旧服务筛选和本轮用户确认。相同 `order_id` 的次序没有确定契约；不将旧测试额外使用的 `event_id` 排序当作接口承诺。
4. 旧进程保留方向处理上下文：优先已确认的赛程队序，其次当前用户的赛果审核队序，最后标准化比赛队序；相关历史数据路径和字段见 [ADC-001](./data-closures/ADC-001-live数据路径.md)。竞彩在此基础上增加 `if_change` 判断，以竞彩官方比赛队序为最终对齐目标；事件 `position` 的 0/1/2 分别为中立/主/客，比分 `homeScore/awayScore` 也须与对应队序一致。`if_change=1` 表示标准化与竞彩来源队序相反；`if_change=0` 表示不增加该反向判断。队序变更时需同时核对主客事件及比分，中立 0 不变，字段缺值按 Q-003。
5. 历史审核/确认方向与标准化方向可能不同；不能只看 `if_change` 就假定已处理过的旧结果必然与竞彩队序一致，也不能直接搬用旧 SQL 的正式赛程或审核记录选取条件。具体旧处理与竞彩方向应结合球队身份独立判定，最终以竞彩队序为准；现有实现的差异见第 7 节。
6. 补时显示格式、图标、默认 tab 和中立事件双侧显示属于页面表现。[API-001 Q-001](../API-001-get-match-monitor/clarification-questions.md) 已确认列表接口返回贝泰直播状态对象；该确认不意味着本进程响应包含相同对象或字段。

纳米事件字段映射承接旧逻辑：`time/type/second/position` 同名取 `incidents` 元素，`player_name/in_player_name/out_player_name` 对应 `playerName/inPlayerName/outPlayerName`，`home_score/away_score` 对应 `homeScore/awayScore` 并受队序影响。贝泰事件字段来自对应事件记录，`position` 结合事件球队和来源主队计算；两者的业务队序再按上述规则核对。[旧进程 SQL](../../../../../global/source-materials/automation-contracts/data-bff/match-monitoring/legacy-match-live/比赛进程信息查询接口.sql)、旧脚本 `_expected_nami_incidents/_query_expected_beitai_events`。

## 5. 响应字段与结果分支

成功包装 `code=0`、`message=OK`，`data` 为进程对象。OpenAPI 未声明属性 required，字段是否省略仍需验证。Q-003 确认空集合为 `[]`、元素具体字段无值为 `null`，不能把数组 null、缺字段、空字符串视为相同结果。

| 字段 | 类型及含义 |
|---|---|
| `liveIncidents` | 纳米进程数组；元素含 `time`（分钟）、`second`、`type`、`position`、`playerName`、`inPlayerName`、`outPlayerName`、`homeScore`、`awayScore`。 |
| `beitaiLiveIncidents` | 贝泰数组；元素含 `eventId`、`matchId`、`clock`、`orderId`、`matchTime`、`stoppageTime`、`stoppageTimeClock`、`injuryTimeAnnounced`、`period`、`eventType`、`team`、`playerId1/2`、`playerName1/2`、`playerType1/2`、`method`、`status`、`coordX/Y`、`text`、`homeScore`、`awayScore`、`cardDescription`、`eventTime`、`createTime`、`updateTime` 和计算的 `position`。类型及长度见 OpenAPI schema；`position` 是实体 transient 字段。 |

某来源无事件时对应 `[]`，两来源均无事件时两个字段均为 `[]`。错误分支见第 3 节；服务异常不能冒充空成功。实际 JSON 包含策略和时间序列化尚未验证。

## 6. 职责边界与副作用

本接口职责是读取、转换进程，不负责修改赛程、赛果、备注或事件；结果可随来源采集、关联、审核或登录用户变化。代码对贝泰实体调用 setter，方法未显式保存；是否因持久化上下文产生写回未运行验证，不能断言数据库绝无变化。见 ADC。

## 7. 来源差异、假设与待确认问题

- **篮球范围已确认**：旧服务无篮球进程分支，按用户指示本轮不新增；当前入口接受 `sportId=2` 不构成篮球进程支持或确定返回值。详见 [Q-001](./clarification-questions.md)。
- **方向差异**：旧方向处理经用户确认应承接；当前本地源码在外层 `if_change=1` 时只交换两数组 `position`，未交换比分。旧处理与竞彩方向的叠加也不能仅凭标志位保证结果一致；这些是源码静态观察，不代表已验证线上行为，最终按已确认的竞彩方向判断。
- **依赖和空值差异**：任一来源 ID 存在时，本地旧服务先取北单正式赛程首条和登录账号，缺失可触发 code 31；保留其历史依赖作为数据路径，但不能据此臆造缺数据的业务预期。两来源 ID 均无时可提前返回，但 DTO 集合未初始化，纳米未命中也可能留 null，与 Q-003 冲突。均未运行复现。
- **资料缺口**：OpenAPI 的必填标记与 description 冲突；独立接口设计文档尚未找到；跨运动项目关联、同一标准比赛多条北单赛程顺序和时间格式未验证。历史 SQL 不作为独立预期。

## 8. 测试方案交接

可按足球进程承接规则、竞彩方向、模块 Q-003、FC-002、DC-002 和 [ADC-001](./data-closures/ADC-001-live数据路径.md) 进入测试方案；篮球进程不在本轮范围。列表直播状态对象已由 API-001 Q-001 确认，本接口不复制该对象契约。本阶段不生成测试点或用例。

**分析状态：ready**  
**测试方案就绪：是**。足球进程承接规则、竞彩队序和空集合口径已足以进入测试方案。
