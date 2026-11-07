# 竞彩赛程监控列表接口分析
> operation：`GET /sporttery/match-monitor` (`listMatchMonitor`)
> 分析状态：ready（当前范围的业务口径已确认；文档及环境仍需核验）

## 1. 接口定位与结论摘要

本接口按运动项目和竞彩业务日查询竞彩官方赛程，返回以竞彩源赛程为主体的列表，并补充标准化比赛字段、贝泰足球直播对象、竞彩事件/备注数量、开奖信息、比分和行颜色。请求范围只有运动项目与起止业务日；自动刷新、列筛选、弹窗和滚动位置属于前端功能。接口成功空结果是 `data: []`。

列表身份及事件/备注关联使用竞彩官方比赛 ID；`s_match` 通过竞彩来源行的 `s_match_id` 关联，并必须按 `sport_id` 隔离。`if_change=1` 只调整标准化来源的排名、比分主客顺序，不调整竞彩源队名或已开奖官方比分。用户确认列表沿用历史比赛监控的五字段贝泰直播对象，本地源码版本和实际返回仍需核验。颜色根据事件更新时间和 `reason_title` 计算，无事件返回 `NONE`，本期不依赖任务表。

## 2. 分析范围与依据

| 来源 | 本次用途 | 关键定位/状态 |
|---|---|---|
| [当前模块需求](../../preanalysis/00-module-requirement-pack.md) | 列表字段、来源优先级、功能边界 | 比赛列表业务规则 1～8 |
| [RSU 映射](../../preanalysis/02-sentence-test-point-map.md) | 追溯本接口覆盖范围 | RSU-001～RSU-008；RSU-009/010 为前端行为 |
| [已确认问题](../../preanalysis/03-clarification-questions.md) | 模块范围、环境边界、空集合/null 语义 | Q-001～Q-003 均已回答 |
| [API-001 问题清单](./clarification-questions.md) | 用户对直播对象归属和结构的确认 | Q-001 answered：列表项返回五字段贝泰 live DTO |
| [模块 Context Pack](../../preanalysis/01-context-pack.md) | 已确认列表逻辑和来源边界 | “已确认的详细逻辑”“领域契约边界” |
| [FC-001](../../preanalysis/context-cards/FC-001-竞彩监控列表聚合链路.md) | 可复用列表组装语义 | 主链路、队序、比分、事件/任务规则 |
| [DC-001](../../preanalysis/data-closures/DC-001-列表聚合数据闭包.md)、[DC-002](../../preanalysis/data-closures/DC-002-进程解析数据闭包.md) | 复用的模块数据路径 | 列表聚合与可能的足球 live 解析；DC-001 状态 `test-point-ready` |
| [ADC-001](./data-closures/ADC-001-列表贝泰直播数据路径.md) | 补充列表贝泰直播状态的接口专属数据路径 | `s_match.beitai_match_id` 到直播表及五字段映射；`test-point-ready` |
| [历史复用回顾](../../reference-analysis/match-monitoring-reuse-review.md) | 识别旧列表和当前接口的复用边界 | REF-002～004、REF-010；仅经用户确认沿用直播对象，不搬用旧事件 SQL 和列表筛选 |
| [旧列表需求](../../../../../global/source-materials/automation-contracts/data-bff/match-monitoring/legacy-match-list/比赛列表模块需求.md)、[旧列表脚本](../../../../../../test-league-platform/testsuites/data-bff/match_monitoring/test_get_monitoring_list.py) | 旧状态展示规则、直播字段及空对象行为 | 比赛状态第 9 条；`assert_beitai_match_live`、`_query_beitai_live_dto_map`、`_fill_extra_fields` |
| [历史列表服务](../../../../../../../apps/league-platform/data-backend/src/main/java/com/league/backend/service/monitor/SMatchService.java)、[贝泰 DTO](../../../../../../../apps/league-platform/apiclient/src/main/java/com/league/client/dto/BeitaiFootballMatchLiveDTO.java) | 核对旧列表的足球直播组装及五字段定义 | `getSMatch` / `buildMatch` 的贝泰直播查询/组装；DTO 的 `matchStatus` 对应 `match_status` |
| [当前 OpenAPI](../../../../../global/source-materials/api-docs/league-api-definition/league-core-api/data-backend-openapi.json) | operation、参数、响应 schema | `#/paths/~1sporttery~1match-monitor/get`；`SportteryMatchMonitorItem.properties.beitaiFootballMatchLiveDTO` 引用五字段 `BeitaiFootballMatchLiveDTO` |
| [竞彩管理详细设计](../../../../../global/source-materials/api-docs/竞彩管理详细设计文档.md) | 更具体的列表查询及颜色规则 | §8.1～§8.2；live 显示引用、事件更新时间、任务解除、计数和排序 |
| [数据库设计](../../../../../global/source-materials/database-docs/第十三轮冲刺竞彩抓取数据库设计和变更.md) 与 [DDL](../../../../../global/source-materials/database-docs/北单运营系统-test2_newgoal-202610261418.sql) | 当前表字段和数据域 | 竞彩足球/篮球赛程；`sporttery_match_event`、`sporttery_task`、`sporttery_match_remark` |
| [Controller](../../../../../../../apps/league-platform/data-backend/src/main/java/com/league/backend/controller/sporttery/SportteryMatchMonitorController.java)、[Service](../../../../../../../apps/league-platform/data-backend/src/main/java/com/league/backend/service/sporttery/SportteryMatchMonitorService.java)、[Rules](../../../../../../../apps/league-platform/data-backend/src/main/java/com/league/backend/service/sporttery/SportteryMatchMonitorRules.java) | 参数绑定、查询实现及差异识别 | `listMatchMonitor`、`enrich`、`rank`、`footballScore`、`basketballScore`、`latestUnresolvedEvent`；实现观察，不高于需求 |

本接口复用模块级 FC-001/DC-001；由于 DC-001 没有细化列表直播对象到贝泰 live 表的路径，使用接口级 ADC-001 补充该部分，不复制整个模块闭包。本次读取的后端子模块处于 `95884a32`，该版本未体现用户反馈的直播对象修复；不能以此判断开发最新版本。开发环境样本、实际序列化和执行细节仍由后续阶段验证。

## 3. 请求与接口契约

data-backend operation 为 `GET /sporttery/match-monitor`；管理端 BFF 路径为 `/data-backend/sporttery/match-monitor`。成功 envelope 为 `CommonResult<List<SportteryMatchMonitorItem>>`，成功码 `0`；OpenAPI 只描述 HTTP 200，不定义完整错误响应及框架绑定错误状态。

| 参数 | 位置/类型 | OpenAPI | 已确认/当前服务行为 | 边界与错误 |
|---|---|---|---|---|
| `sportIds` | query integer 数组 | optional | 缺失或空集合默认 `[1,2]`；显式值去重；支持 `1` 足球、`2` 篮球 | 任一不支持值使请求失败，业务 code `2`。重复值不重复返回赛程。空字符串如何绑定属于 BFF/框架行为，OpenAPI 未定义 |
| `businessDateStart` | query ISO date | optional | 缺失时使用上海时区当天 | 明确传入的日期作为闭区间起点；非法格式的 HTTP/body 形态未由 OpenAPI 定义 |
| `businessDateEnd` | query ISO date | optional | 缺失时独立使用上海时区当天 + 6 天 | 结束日包含；早于开始日返回业务 code `2`；自定义 start 不改变 end 的独立默认值 |

| 错误条件 | OpenAPI 描述 | 当前 Service 实现观察 | HTTP/body 契约 |
|---|---|---|---|
| `sportIds` 含不支持项目 | code `2`：运动项目不支持 | `sportIds 仅支持 1（足球）和 2（篮球）` | OpenAPI 未完整定义错误 schema/status；不要把实现 message 当作已确认的固定文案 |
| `businessDateEnd < businessDateStart` | code `2`：结束日期早于开始日期 | `businessDateEnd 不得早于 businessDateStart` | 同上 |
| 日期格式无法绑定 | 未描述 | Controller 使用 ISO DATE 参数绑定；错误由框架/BFF 层产生 | 未知；与 Service 业务 code `2` 分层，不预设状态码 |

无分页参数。自动刷新选项不在接口参数中。当前 Controller 将参数以 optional 接收后由 Service 做业务校验；不要从 OpenAPI `required:false` 推断非法 sportId 可忽略。

## 4. 业务规则与数据处理流程

1. 按 `sportIds` 和 `business_date BETWEEN start AND end` 分别读取竞彩足球/篮球赛程；起止日期均包含。两种运动的查询结果合并后全局排序。
2. 竞彩赛程是主记录。联赛、球队以竞彩源表 ID 补充名称；球队名称优先全称、为空时回退简称。缺少球队/赛事补充信息时字段按可空值返回。列表官方 `matchId` 是竞彩 ID，不是 `s_match.match_id`。
3. 通过来源行 `s_match_id` 与同一 `sport_id` 下 `s_match.match_id` 关联；用户确认若标准比赛已被替换，应追随新比赛 ID，而非直接视为未匹配。替换链断链、多跳及跨运动项目异常尚无确认口径。没有有效标准比赛关联时仍保留竞彩赛程行；标准化 ID、来源 match IDs、排名和状态等可空字段为 `null`，页面显示“未匹配”。
4. 主队/客队名称与 ID 始终采用竞彩赛程的原始主客顺序。排名来自标准比赛的 `home_position/away_position`；`if_change=1` 时交换标准化排名以对齐竞彩顺序。无标准排名时返回 `null`，前端是否隐藏该排名不属于 API。
5. 列表项的 `matchStatus` 是标准比赛 `status_id` 的数值，未匹配时为 null。用户确认沿用旧列表：足球通过贝泰比赛 ID 查询 live，记录存在就组装五字段对象，不按比赛状态过滤，完场也返回；非足球或无记录为 null。新版 OpenAPI 的“仅比赛中”注释需同步，实际返回尚未核验。
6. 比分来源按运动项目处理：
   - `sell_status=4` 时只使用竞彩比分，部分或全部为空均不使用标准比分补齐；有有效比分时 `source=SPORTTERY`。未开奖时（`sell_status in (0,1,2,3)`）使用标准比分，`source=S_MATCH`；标准来源按 `if_change=1` 交换为竞彩主客顺序，竞彩官方比分不交换。选定来源无任何有效比分时 `score=null`。
   - 足球返回 `half`、`full`，篮球返回 `full` 且 `half=null`；两项目均移除 `periods`。篮球官方全场取 `home_score`、`away_score`，不取 `part_end`。`full` 格式为 `主队:客队`；`--:--` 是页面按空值展示的占位符。
7. `drawStatus` 由竞彩 `sell_status` 派生：`sell_status=4` 为 1/“已开奖”，其他值（0待开售/1已开售/2暂停销售/3已停售）为 0/“未开奖”。
8. `eventCount` 按 `sport_id + source_id(竞彩官方 matchId)` 统计当前竞彩事件表匹配行数；列表计数查询不加事件详情接口使用的 `source_type=SPORTTERY` 条件。`remarkCount` 按 `sport_id + official matchId + remark_type=1` 统计。事件计数可能与事件详情接口返回条数不同，若存在同键的其他 source_type 事件，这是两个查询口径的差异，不可假设相等。
9. 颜色异常类型由竞彩事件 `reason_title` 判定，当前不使用 `sporttery_task` 和 `confirm_result`。按事件更新时间选择：比赛提前为 `RED`，推迟为 `YELLOW`，取消/中断/腰斩为 `ORANGE`，比赛方变更为 `GREEN`；无事件返回 `NONE`。同更新时间按详细设计中事件 ID 倒序决胜。用户最新确认的“比赛方变更”替代原需求与详细设计中的“球队变更”，见 Q-011。
10. 返回列表不分页。空开赛时间行保留且排在有开赛时间行之后；其余按竞彩编号中的数字部分升序，无法解析编号的记录置后，同号按官方 `matchId` 排序。

排序、行颜色及集合/null 语义依据当前需求、用户确认和 FC-001/DC-001；历史详细设计中的任务解除规则本期不适用。

## 5. 响应字段与结果分支

成功数据为数组；匹配不到竞彩赛程时 `code=0`、`data=[]`。集合内部可空字段使用 null，不改为空字符串或数组。

| 字段 | 含义/来源 | 空值与条件 |
|---|---|---|
| `sportId`,`sportName`,`businessDate`,`matchId`,`matchNo` | 竞彩源赛程身份和业务日；`matchId` 为官方竞彩 ID | 赛程身份字段来自源行 |
| `sMatchId`,`beitaiMatchId`,`namiMatchId` | 关联标准比赛及两来源 ID | 未关联标准比赛时为 null |
| `leagueId`,`leagueName`,`matchTime` | 竞彩源赛程及联赛映射 | 对应源值或补充行缺失时为 null |
| `homeTeamId`,`homeTeamName`,`awayTeamId`,`awayTeamName` | 竞彩源主客队及球队名称回退映射 | 不受 `if_change` 交换 |
| `homePosition`,`awayPosition` | 对齐竞彩队序的标准化排名 | 无标准比赛/排名时 null |
| `matchStatus` | 标准比赛原始状态码 | 无标准关联时为 null；状态文案由页面映射，不返回 `matchStatusName` |
| `beitaiFootballMatchLiveDTO` | 用户确认沿用的贝泰足球直播对象 | 足球通过贝泰比赛 ID 关联；无有效来源记录或非足球时按历史行为为 null；修复后的实际返回待核验 |
| `score` | 半场/全场比分对象 | 无任何有效比分时整个对象 null；`periods` 本期删除，篮球 `half=null` |
| `sellStatus`,`drawStatus` | 竞彩销售/开奖状态 | `sellStatus` 为 0待开售/1已开售/2暂停销售/3已停售/4已开奖；`sellStatus=4` 时 `drawStatus=1`，否则为 0；开奖文案由页面映射，不返回 `drawStatusName` |
| `eventCount`,`remarkCount` | 当前竞彩事件数和类型 1 备注数 | 无匹配行计数为 0 |
| `rowColor`,`taskType` | 事件颜色；任务当前不使用 | 无事件 `rowColor=NONE`；任务表未使用，`taskType` 字段保留与否未确认，不设字段存在性预期 |

### 贝泰足球直播对象

用户确认列表项对象的结构如下；其中 ID 和状态值是示例，不是固定测试数据：

```json
{
  "matchId": 72149636,
  "status": "closed",
  "matchStatus": "ended",
  "matchClock": "",
  "stoppageClock": ""
}
```

| 对象字段 | 贝泰 live 表字段 | 语义 |
|---|---|---|
| `matchId` | `match_id` | 贝泰比赛 ID；不同于列表项的竞彩官方 `matchId` 和标准比赛 `sMatchId` |
| `status` | `status` | 贝泰比赛状态，字符串原值 |
| `matchStatus` | `match_status` | 贝泰比赛详细状态，字符串原值；与对象内 `status` 及列表顶层数值 `matchStatus` 是不同字段 |
| `matchClock` | `match_clock` | 比赛时钟，字符串原值 |
| `stoppageClock` | `stoppage_clock` | 实际补时时钟，字符串原值 |

对象及其字段按历史列表映射返回：没有关联或 live 行时对象为 `null`；字段源值为 `null` 与空字符串 `""` 不混同。历史服务仅对足球查找直播记录，字段只读、不做主客方向转换。用户示例和当前 DTO 源码支持五字段；旧 OpenAPI 和旧数据准备分析只列四字段，不能遗漏 `matchStatus`。

新版 OpenAPI 3.1 已列出该对象及五个字段，但列表项及直播对象都未声明 `required`；对象 schema 为 `object`，状态和时钟字段为 `string`，未将 `null` 纳入类型。严格按该 schema 校验时，显式 `null` 会与 schema 冲突，而缺少字段不会因 `required` 失败。业务预期仍按已确认的空值口径处理；文档定义和实际序列化应进一步核对。

业务参数错误至少包括不支持的 sportId 和 end 早于 start，返回业务 `code=2`；OpenAPI 只描述错误条件/code，未提供完整 message/data 与 HTTP 非 200 契约。上表中的实际 message 仅为当前 Service 实现观察。日期格式绑定失败与 Service 业务错误分开处理，具体 HTTP/body 由 BFF 实际契约决定，分析不预设。

## 6. 职责边界与副作用

- 本接口只查询并组装列表，不写竞彩赛程、标准比赛、事件、任务或备注。
- 列头赛事/状态/事件/备注/开奖筛选、自动刷新及刷新后的状态保留、滚动位置属于前端功能；接口只提供筛选所消费的数据，不接收这些筛选条件。
- 行颜色字段 `rowColor` 是 API 可断言的数据；页面实际背景颜色及布局是功能测试。
- 列表接口返回直播原始对象；足球比赛中显示分钟、补时、阶段和缺数据时的回退文案属于页面逻辑，沿用[旧列表需求](../../../../../global/source-materials/automation-contracts/data-bff/match-monitoring/legacy-match-list/比赛列表模块需求.md)第 9 条，不由本接口拼装展示字符串。
- 点击比赛状态后的进程事件内容由 `GET /sporttery/match-monitor/live` 负责；它不替代本列表的直播状态对象。事件详情由 `/events` 负责；备注读取/保存由 `/remarks`、`/remark` 负责。
- 列表查询重复调用没有业务写入副作用。

## 7. 来源差异、假设与待确认问题

### 已处理的主要差异

| 事项 | 业务依据 | 当前实现/契约差异 | 本分析处理 |
|---|---|---|---|
| 行颜色事件选取时间 | 需求 RSU-008 写“事件更新时间最大”；竞彩管理详细设计 §8.2 明确 `update_time DESC,event_id DESC` | 当前 Rules 使用 `create_time DESC,event_id DESC` | 按更具体的业务详细设计作为预期；当前实现记为高风险偏差，测试需使用 create/update 时间顺序交叉数据，不把 create_time 改写成需求 |
| 足球 live 对象 | 需求 RSU-004 与用户回答 Q-001 确认列表返回五字段对象，沿用历史列表映射；用户反馈开发已修复 | 新版 OpenAPI 已引用五字段 DTO；本地子模块 `95884a32` 的列表 DTO/Service 未体现该修复 | 不以旧源码否定用户反馈；需取得修复后的源码或运行证据，核验映射及部署状态 |
| 直播对象的 null/字段存在性 | 模块 Q-003 及沿用的历史列表空值口径 | OpenAPI 3.1 未声明字段 `required`，对象和状态/时钟字段的类型未包含 `null` | 按业务口径设计断言；建议补充文档的字段存在性及可空定义，实际返回待验证 |
| 状态文案字段 | 需求要求页面显示状态、开奖文案 | 当前列表 DTO/OpenAPI 仅提供数值 `matchStatus`、`drawStatus`，没有 `matchStatusName`、`drawStatusName` | 文案及“未匹配”是页面展示；不把两个人造 Name 字段作为 API 响应预期 |
| 历史 live DTO 文档 | 用户确认五字段；当前 DTO 源码和旧列表测试均包含 `matchStatus` | 旧列表 OpenAPI 与旧数据准备分析只列四字段 | 以本轮确认及五字段 DTO 为准，旧文档保留为历史版本差异 |
| 事件计数过滤 | 详细设计 §8.2 为 `(sport_id, source_id)` | 事件详情 API 另加 `source_type=SPORTTERY` | 保留两接口独立过滤口径，不假定列表 eventCount 等于详情列表 total |
| OpenAPI required/error schema | operation 参数 optional，错误码只在 description 列举 | 当前 Controller/Service 有业务校验，HTTP 错误封装未完整建模 | 参数边界以业务校验为准；框架绑定错误的 HTTP/body 不从 schema 猜测 |

本轮确认已开奖只使用竞彩比分、无事件颜色为 `NONE`；此前逐项补齐的回答以本轮为准。当前 OpenAPI 的 periods、直播条件及旧任务说明需要开发同步。赛事简称为 null 暂缓，异常替换链不在本轮确定范围。

## 8. 测试方案交接

- 数据路径和可复用数据语义：复用 [DC-001](../../preanalysis/data-closures/DC-001-列表聚合数据闭包.md) 和补充直播对象的 [ADC-001](./data-closures/ADC-001-列表贝泰直播数据路径.md)；两者为 `test-point-ready`，用例阶段仍需确认开发库样本、数据准备/清理和独立 SQL。
- 复用 [FC-001](../../preanalysis/context-cards/FC-001-竞彩监控列表聚合链路.md)；不复制模块级 Context Card 或整个数据闭包。
- 当前 operation 覆盖 RSU-001～RSU-008 的可观察查询/响应字段；RSU-009 自动刷新与 RSU-010 列头筛选不由接口验证。RSU-011 点击进程后属于相邻 Live operation/功能链路。
- 关键覆盖面包括 sport/date 参数边界、业务日闭区间、足球篮球隔离、缺标准比赛仍保留、排名/比分 `if_change`、开奖比分源、无比分 null、事件/备注计数、事件最新更新时间颜色及列表排序。
- 行颜色测试需显式构造事件 `update_time` 顺序与 `create_time` 顺序相反的记录；旧实现差异仅为静态风险，不等同于已验证缺陷。
- 列表直播对象按 Q-001 和 ADC-001 的已确认口径设计，关注五字段、来源 ID、空对象、字段空值与页面展示边界；用户反馈修复完成，但本地源码及目标环境仍待核验。

分析状态：ready。

测试方案就绪：是，限已确认范围。直播对象修复与部署情况、行颜色实现差异均需后续核验，不能当作已测试通过。
