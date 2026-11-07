# API-002 竞彩比赛进程接口测试方案

> 接口：`GET /sporttery/match-monitor/live`（管理端 BFF 路径：`/data-backend/sporttery/match-monitor/live`）  
> 方案模式：单接口测试方案；方案状态：`ready`，测试点 1～47 已由用户于 2026-11-03 确认审核通过；2026-11-04 重构后执行，33 通过、14 失败，详见[自动化实施方案](./api-test-automation-plan.md)第七节。

## 一、测试类型

接口功能测试：验证请求和关联校验、纳米与贝泰足球进程查询、字段及空值、事件过滤和排序、竞彩主客队序，以及查询只读性。数据库用于后续独立准备数据和核对结果；本方案不包含 SQL、Excel 用例或测试脚本。

## 二、测试依据与范围

- [接口分析](./interface-analysis.md)、[接口问题清单](./clarification-questions.md)：API-002 Q-001 已确认沿用旧足球进程逻辑并增加 `if_change` 判断，旧代码没有的篮球进程本轮不新增。
- [模块问题清单](../../preanalysis/03-clarification-questions.md)：模块 Q-003 已确认集合无元素时返回 `[]`，集合元素内无值的具体字段返回 `null`。
- [当前需求及 RSU 映射](../../preanalysis/02-sentence-test-point-map.md)：RSU-011 的比赛状态入口；[历史比赛进程需求](../../../../../global/source-materials/automation-contracts/data-bff/match-monitoring/legacy-match-live/比赛进程信息需求.md)第（9）节提供经用户确认沿用的事件和顺序规则。
- [模块 FC-002](../../preanalysis/context-cards/FC-002-竞彩进程解析链路.md)、[模块 DC-002](../../preanalysis/data-closures/DC-002-进程解析数据闭包.md)、[接口 ADC-001](./data-closures/ADC-001-live数据路径.md)：来源关联、方向及空值的数据语义。
- [当前 OpenAPI](../../../../../global/source-materials/api-docs/league-api-definition/league-core-api/data-backend-openapi.json)：`/paths/~1sporttery~1match-monitor~1live/get` 和 `SMatchLiveIncidentsResponse`、`SMatchLiveIncidentsDTO`、`BeitaiFootballEventEntity`。
- [历史复用回顾](../../reference-analysis/match-monitoring-reuse-review.md)、[旧进程测试方案](../../../../../../test-league-platform/docs/接口测试方案/比赛监控/比赛赛程监控/比赛进程信息接口测试方案.md)：逐项识别原有场景；旧参数、旧空值和旧 SQL 不直接作为当前预期。

本方案表格中的 `Q-001` 指 API-002 接口问题，`Q-003` 指模块问题；两套问题编号独立。

### 共用条件与判定方式

1. 除明确测试缺参或非法参数的行外，均使用已认证的管理端上下文，发送 `GET /sporttery/match-monitor/live`，携带 `sportId=1` 和目标竞彩官方 ID `sportteryMatchId=P`；`matchId` 默认不传。各行的目标比赛和事件须相互隔离，数据在请求和核对期间不被其他任务改变。
2. 有效关联比赛的 `sporttery_football_match.match_id=P`，`s_match_id=S`，对应标准比赛及该场景所需的来源数据存在。涉及旧方向状态的场景还需满足该状态的有效数据关联。标记为 `ADC-001` 的行按该闭包准备和核对，不直接复制旧服务 SQL。
3. 正常成功统一核对 HTTP `200`、业务 `code=0`、`message=OK` 和行内指定的 `data` 字段；业务错误只核对该行明确列出的 `code`，不假设错误 HTTP 状态、精确 message 或 data 形态。
4. 下文以 A、B 表示同一场比赛的两支不同球队。方向场景中，标准化及来源赛事原主客为 A/B；`if_change=0` 时竞彩队序为 A/B，`if_change=1` 时为 B/A。源事件若给出 A/B 比分 `2:1`，竞彩 A/B 对应 `2:1`，竞彩 B/A 对应 `1:2`。球队身份必须从当前场景数据核对，不以固定 ID 或接口返回反推。
5. `position` 为 `0/1/2` 分别表示中立/竞彩主队/竞彩客队；中立事件仍以 `0` 表示。来源字段为 `null` 或缺失时，适用模块 Q-003，不把该字段人为填为 `0`、`[]` 或空字符串。
6. 单来源事件用例只在目标来源创建事件。贝泰目标场景保留纳米来源并准备 `incidents=[]`；纳米目标场景保留贝泰来源 ID 但不创建贝泰事件。36～41 按行指定贝泰或纳米目标来源，另一来源仅返回空集合、不添加额外事件；42～47 覆盖双来源。

## 三、测试内容

| 序号 | 测试项 | 测试点 | 备注 |
| --- | --- | --- | --- |
| 1 | 必传参数 | 【缺少运动项目】携带合法 `sportteryMatchId=P`，不传 `sportId` 请求接口 → 返回业务 `code=2`。 | API-002；OpenAPI 必传描述 |
| 2 | 必传参数 | 【缺少竞彩比赛 ID】携带 `sportId=1`，不传 `sportteryMatchId` 请求接口 → 返回业务 `code=2`。 | API-002；OpenAPI 必传描述 |
| 3 | 参数范围 | 【不支持的运动项目】携带合法 `sportteryMatchId=P`，以 `sportId=3` 请求接口 → 返回业务 `code=2`。 | FC-002；模块运动项目范围 |
| 4 | 参数范围 | 【非正数竞彩 ID】携带 `sportId=1`，以 `sportteryMatchId=0` 请求接口 → 返回业务 `code=2`。 | FC-002；DC-002 |
| 5 | 竞彩比赛校验 | 【官方比赛不存在】足球竞彩表不存在 ID 为 P 的比赛，以 P 请求接口 → 返回业务 `code=2`。 | API-002；DC-002 |
| 6 | 标准关联校验 | 【竞彩比赛未关联】足球竞彩比赛 P 存在但 `s_match_id=null`，以 P 请求接口 → 返回业务 `code=2`。 | API-002；DC-002 |
| 7 | 标准关联校验 | 【可选标准比赛 ID 不一致】P 关联标准比赛 S，携带不等于 S 的 `matchId=T` 请求 → 返回业务 `code=2`。 | API-002；DC-002 |
| 8 | 标准关联校验 | 【不传可选 matchId】P 关联 S，S 仅有一条可识别的纳米进程且无贝泰进程，不传 `matchId` 请求 → `liveIncidents` 返回该条进程，`beitaiLiveIncidents=[]`。 | API-002；ADC-001；Q-003 |
| 9 | 标准关联校验 | 【传入一致的 matchId】P 关联 S、来源进程在两次请求间不变，分别不传 `matchId` 和传 `matchId=S` 请求 → 两次成功响应的 `data` 相同。 | API-002；ADC-001 |
| 10 | 比赛隔离 | 【不同竞彩比赛】P 关联 S、另一官方比赛关联另一标准比赛，两场各有可区分的纳米和贝泰事件；请求 P → 两个响应数组仅包含 S 对应的来源事件，不包含另一场事件。 | API-002；ADC-001 |
| 11 | 来源聚合 | 【双来源均有进程】S 同时关联有事件的纳米及贝泰来源，请求 P → `liveIncidents` 和 `beitaiLiveIncidents` 分别包含对应来源的全部符合规则的事件，不相互混入。 | API-002；ADC-001；Q-001 |
| 12 | 来源聚合 | 【仅纳米有来源 ID】S 的纳米 ID 对应一条进程事件、贝泰 ID 为 `null`，请求 P → `liveIncidents` 返回该事件，`beitaiLiveIncidents=[]`。 | ADC-001；Q-003 |
| 13 | 来源聚合 | 【仅贝泰有来源 ID】S 的贝泰 ID 对应一条允许类型的事件、纳米 ID 为 `null`，请求 P → `beitaiLiveIncidents` 返回该事件，`liveIncidents=[]`。 | ADC-001；Q-003 |
| 14 | 空集合 | 【两来源均无 ID】S 的纳米和贝泰来源 ID 均为 `null`，请求 P → `liveIncidents=[]` 且 `beitaiLiveIncidents=[]`。 | ADC-001；Q-003 |
| 15 | 空集合 | 【纳米来源行不存在】S 关联纳米 ID，但该 ID 无 live 行；贝泰来源有一条允许类型事件，请求 P → `liveIncidents=[]`，贝泰事件正常返回。 | ADC-001；Q-003 |
| 16 | 空集合 | 【纳米进程为 null】S 关联的纳米 live 行存在且 `incidents` 为 SQL `NULL`，请求 P → `liveIncidents=[]`。 | ADC-001；Q-003 |
| 17 | 空集合 | 【纳米进程为空数组】S 关联的纳米 live 行 `incidents=[]`，请求 P → `liveIncidents=[]`。 | ADC-001；Q-003 |
| 18 | 空集合 | 【贝泰无事件】S 的贝泰 ID 存在但没有对应事件，纳米来源有一条事件，请求 P → `beitaiLiveIncidents=[]`，纳米事件正常返回。 | ADC-001；Q-003 |
| 19 | 贝泰事件范围 | 【允许的九类事件】当前贝泰来源各有一条 `match_started`、`break_start`、`injury_time_shown`、`match_ended`、`red_card`、`yellow_card`、`yellow_red_card`、`substitution`、`score_change` 事件，请求 P → 九条事件均在 `beitaiLiveIncidents` 中各返回一次。 | ADC-001；旧需求 3.1；Q-001 |
| 20 | 贝泰事件范围 | 【非允许类型】当前贝泰来源同时有一条 `score_change` 和一条 `period_start` 事件，请求 P → 返回 `score_change`，不返回 `period_start`。 | ADC-001；旧进程承接 |
| 21 | 贝泰排序 | 【不同顺序号】当前贝泰事件按 `order_id=3、1、2` 的顺序准备，请求 P → 数组对应的 `orderId` 依次为 `1、2、3`。 | ADC-001；旧需求 3 |
| 22 | 贝泰事件保留 | 【相同顺序号的不同事件】当前贝泰来源存在两条 `order_id` 相同但 `event_id` 不同的允许类型事件，请求 P → 两个事件 ID 均各出现一次；不要求两者之间的固定顺序。 | ADC-001；旧方案 B6 |
| 23 | 贝泰字段映射 | 【事件身份和时间字段】当前贝泰事件的 `event_id`、来源 `match_id`、`order_id`、`event_type`、`clock`、`match_time`、`stoppage_time`、`stoppage_time_clock`、`period`、`team` 均有可区分值，请求 P → 同一事件的 `eventId`、`matchId`、`orderId`、`eventType`、`clock`、`matchTime`、`stoppageTime`、`stoppageTimeClock`、`period`、`team` 分别对应来源值。 | ADC-001；旧方案 B4 |
| 24 | 贝泰字段映射 | 【换人球员字段】当前贝泰换人事件的两名球员 ID、姓名和类型有不同值，请求 P → 该事件的 `playerId1/2`、`playerName1/2`、`playerType1/2` 与各自来源字段一致，不交换两名球员。 | ADC-001；旧需求 3.2 |
| 25 | 贝泰字段映射 | 【补时字段】当前贝泰事件为 `injury_time_shown` 且 `injury_time_announced` 有值，请求 P → 该事件 `injuryTimeAnnounced` 等于来源值。 | ADC-001；旧需求 3.4 |
| 26 | 贝泰字段映射 | 【其他事件的补时原始字段】当前贝泰事件为非 `injury_time_shown` 的允许类型，且来源 `injury_time_announced` 有值，请求 P → 该事件 `injuryTimeAnnounced` 保留来源值；是否展示由页面决定。 | ADC-001；旧方案 B5 |
| 27 | 贝泰字段映射 | 【其他实体属性】当前贝泰事件的 `method`、`status`、`coord_x`、`coord_y`、`text`、`card_description` 具有可区分值，请求 P → 对应 `method`、`status`、`coordX`、`coordY`、`text`、`cardDescription` 分别与来源一致。 | ADC-001；旧方案 B4 |
| 28 | 贝泰时间字段 | 【事件时间元数据】当前贝泰事件的 `create_time`、`update_time`、`event_time` 为不同的非空日期时间，请求 P → 该事件的 `createTime`、`updateTime`、`eventTime` 分别对应各自来源的日期时间值。 | ADC-001；旧方案 B4；不额外规定时区或字符串格式 |
| 29 | 贝泰字段空值 | 【可选字段为 null】当前贝泰事件的球员姓名、补时及描述字段分别为数据库 `NULL`，请求 P → 对应 `playerName1`、`injuryTimeAnnounced`、`cardDescription` 均为 JSON `null`。 | ADC-001；Q-003 |
| 30 | 贝泰字段空值 | 【事件球队无值】当前贝泰来源有一条允许类型事件，其 `team` 为数据库 `NULL`，其余数据满足正常查询条件，请求 P → 该事件仍返回，且元素中的 `team=null`。 | ADC-001；Q-003；不预设缺失球队的 position |
| 31 | 纳米事件顺序 | 【来源顺序非时间排序】纳米 `incidents` 按顺序保存时间为 `60、10、30` 的三条事件，请求 P → `liveIncidents` 中对应事件顺序仍为 `60、10、30`。 | ADC-001；旧需求 4 |
| 32 | 纳米事件保留 | 【不同事件类型】纳米 `incidents` 按顺序包含 `type=11、12、26、99` 的四条事件，其中 `99` 用于验证未列举的整型来源类型；请求 P → 四条事件的 `type` 按来源顺序全部返回，不按贝泰事件类型过滤。 | ADC-001；旧需求 4.3；旧方案 C3；Q-001 |
| 33 | 纳米字段映射 | 【事件基础字段】纳米事件的 `time`、`type`、`second`、`player_name`、`in_player_name`、`out_player_name` 有可区分值，请求 P → 同一元素的 `time`、`type`、`second`、`playerName`、`inPlayerName`、`outPlayerName` 分别对应来源值。 | ADC-001；旧方案 C2 |
| 34 | 纳米字段空值 | 【球员字段无值】纳米事件的 `player_name` 为 `null`、`in_player_name` 不存在，请求 P → 对应 `playerName=null`、`inPlayerName=null`，不得补成空字符串。 | ADC-001；Q-003 |
| 35 | 纳米字段空值 | 【事件方无值】纳米事件的 `position` 不存在，请求 P → 对应元素 `position=null`，不得将缺失字段转成中立事件 `0`。 | ADC-001；Q-003；旧 D13 已调整 |
| 36 | 贝泰竞彩方向 | 【竞彩与标准同序】未确认、当前用户未审核，竞彩队序 A/B、`if_change=0`；贝泰源各有 A 队、B 队和中立事件，源比分 A/B 为 `2:1`，请求 P → 三个事件的 `position` 分别为 `1、2、0`，有比分的事件返回 `homeScore=2、awayScore=1`。 | ADC-001；旧 D1～D3、D10；Q-001 |
| 37 | 贝泰竞彩方向 | 【竞彩与标准反序】未确认、当前用户未审核，竞彩队序 B/A、`if_change=1`；贝泰源各有 A 队、B 队和中立事件，源比分 A/B 为 `2:1`，请求 P → 三个事件的 `position` 分别为 `2、1、0`，有比分的事件返回 `homeScore=1、awayScore=2`。 | ADC-001；Q-001 |
| 38 | 纳米竞彩方向 | 【竞彩与标准同序】未确认、当前用户未审核，竞彩队序 A/B、`if_change=0`；纳米源包含 A 队、B 队及中立事件，源 `position` 为 `1、2、0`、比分 A/B 为 `2:1`，请求 P → 对应 `position` 为 `1、2、0`，有比分的事件返回 `homeScore=2、awayScore=1`。 | ADC-001；旧 D11～D13、D17；Q-001 |
| 39 | 纳米竞彩方向 | 【竞彩与标准反序】未确认、当前用户未审核，竞彩队序 B/A、`if_change=1`；纳米源包含 A 队、B 队及中立事件，源 `position` 为 `1、2、0`、比分 A/B 为 `2:1`，请求 P → 对应 `position` 为 `2、1、0`，有比分的事件返回 `homeScore=1、awayScore=2`。 | ADC-001；Q-001 |
| 40 | 贝泰比分空值 | 【反序时单侧比分无值】竞彩队序 B/A、`if_change=1`，贝泰来源 A 队比分为 `null`、B 队比分为 `3`，请求 P → 对应事件 `homeScore=3`、`awayScore=null`。 | ADC-001；Q-003 |
| 41 | 纳米比分空值 | 【反序时单侧比分无值】竞彩队序 B/A、`if_change=1`，纳米来源 A 队比分为 `null`、B 队比分为 `3`，请求 P → 对应事件 `homeScore=3`、`awayScore=null`。 | ADC-001；Q-003 |
| 42 | 审核与竞彩方向 | 【审核队序与竞彩一致】比赛未确认、当前用户已审核为 B/A；竞彩队序 B/A、`if_change=1`，两来源均有 A 队及 B 队事件且源比分 A/B 为 `2:1`，请求 P → 两个数组中 A 队事件 `position=2`、B 队事件 `position=1`，有比分的事件均为 `homeScore=1`、`awayScore=2`，不因重复换向回到 A/B。 | ADC-001；旧 D5～D6、D14～D16；Q-001 |
| 43 | 审核与竞彩方向 | 【审核队序与竞彩相反】比赛未确认、当前用户已审核为 B/A；竞彩队序 A/B、`if_change=0`，两来源均有 A 队事件且源比分 A/B 为 `2:1`，请求 P → 两个数组各自对应事件 `position=1`、`homeScore=2`、`awayScore=1`。 | ADC-001；Q-001 |
| 44 | 确认与竞彩方向 | 【确认和审核方向不同】比赛已确认为 B/A，当前用户审核队序为 A/B；竞彩队序 B/A、`if_change=1`，两来源均有 A 队事件且源比分 A/B 为 `2:1`，请求 P → 两个数组各自对应事件 `position=2`、`homeScore=1`、`awayScore=2`。 | ADC-001；旧 D8；Q-001 |
| 45 | 确认与竞彩方向 | 【确认同序且审核反序】比赛已确认为 A/B，当前用户审核队序为 B/A；竞彩队序 A/B、`if_change=0`，两来源均有 A 队事件且源比分 A/B 为 `2:1`，请求 P → 两个数组各自对应事件 `position=1`、`homeScore=2`、`awayScore=1`。 | ADC-001；旧 D8；Q-001 |
| 46 | 审核与竞彩方向 | 【审核和竞彩均与标准同序】比赛未确认、当前用户已审核为 A/B；竞彩队序 A/B、`if_change=0`，贝泰来源有 A 队事件且源比分 A/B 为 `2:1`，请求 P → 该事件 `position=1`、`homeScore=2`、`awayScore=1`。 | ADC-001；旧 D7、D10；Q-001 |
| 47 | 查询只读性 | 【进程查询不改来源】在隔离数据中记录 P 的关联和 `if_change`、S 的来源 ID 及贝泰事件来源比分；执行一次 `if_change=1` 的有效查询后重新读取这些字段 → 所有记录值与请求前一致。 | ADC-001；接口分析第 6 节 |

## 四、承接与测试归属

- 旧 A1～A5 的单来源与无来源场景由序号 11～18 改为通过标准比赛来源关联查询，并将旧 `null` 集合统一改为 `[]`；新增双来源同时有数据场景，不继续使用旧接口的来源选择参数。
- 旧 B1～B6 由序号 19～30 承接：保留九类事件、过滤、排序、实体字段、补时字段和相同顺序号不同事件的保留；不额外约定相同 `order_id` 的相对顺序。
- 旧 C1～C3 由序号 31～35 承接：纳米来源顺序、类型及字段映射保留；具体无值字段按 Q-003 返回 `null`。
- 旧 D1～D17 的主客、中立、比分及审核/确认方向由序号 36～46 承接，并补上 `if_change`；旧 D3/D13 的“缺失转中立 0”与 Q-003 不一致，不沿用；旧 D4 对未知球队 ID 固定按中立兜底缺乏当前契约依据，不纳入确定预期。
- 旧方案中的 `matchBaseStatus` 已废弃，当前响应 schema 未声明，不作为本接口字段测试。篮球进程不在本轮范围；不推断篮球请求应返回 `[]` 或指定错误。
- 列表状态对象属于 API-001；点击状态、默认 tab、图标、补时文本格式、中立事件双侧显示和弹窗布局属于页面功能。相关接口测试尚未实际执行，不能据此认定功能已覆盖。

## 五、自动化适配与边界

- 序号 1～7：API 业务错误码可观察；现有 `DataBff` 请求默认校验 HTTP `200`，但本接口错误 HTTP 状态尚未约定，后续需确认实际传输行为并按需适配，不将默认值当作业务预期。
- 序号 10～47：API 的响应和只读字段可观察；现有 `DataBff` 支持 GET、登录和 JSON 响应比较，旧进程测试提供来源事件、审核/确认辅助函数。竞彩官方比赛与标准比赛的可控关联和清理是否已有合适 helper 尚未确认，由后续自动化设计核实；不因 helper 未确认删除测试点。
- 序号 22：API 可观察同顺序号的事件集合，框架默认完整 JSON 对比可能受相同 `orderId` 的未约定次序影响；后续适配需核对两个事件 ID 均各一次，不能强行规定它们的相对次序。
- 序号 42～46：只断言各种历史状态下的最终竞彩方向；相同最终队序不能单凭接口响应证明内部确认、审核和标准化分支的执行顺序。来源字段、当前用户审核及确认状态应由后续设计独立核对，不能复制旧 SQL 的取首条或最新规则。
- 请求参数格式转换、鉴权失败、`matchId` 指向已不存在的标准比赛、缺北单赛程及服务异常的精确响应尚无足够的当前业务契约；不以本地实现观察或旧接口错误消息作为确定预期。OpenAPI 未定义错误响应 HTTP 状态及完整 message，不对其作固定断言。
- 上述为设计阶段的可执行性评估；实际执行、失败证据和覆盖限制以[自动化实施方案](./api-test-automation-plan.md)第七节为准。
