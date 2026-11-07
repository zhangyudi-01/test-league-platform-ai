# ADC-001 竞彩比赛至来源进程数据路径

## 引用入口

- [接口分析](../interface-analysis.md)、[接口已回答问题 Q-001](../clarification-questions.md)
- [模块 DC-002](../../../preanalysis/data-closures/DC-002-进程解析数据闭包.md)、[FC-002](../../../preanalysis/context-cards/FC-002-竞彩进程解析链路.md)、[模块 Q-003](../../../preanalysis/03-clarification-questions.md)
- [竞彩服务](../../../../../../../../apps/league-platform/data-backend/src/main/java/com/league/backend/service/sporttery/SportteryMatchMonitorService.java)、[下游服务](../../../../../../../../apps/league-platform/data-backend/src/main/java/com/league/backend/service/monitor/SMatchService.java)、[DDL](../../../../../../global/source-materials/database-docs/北单运营系统-test2_newgoal-202610261418.sql)
- [旧进程 SQL](../../../../../../global/source-materials/automation-contracts/data-bff/match-monitoring/legacy-match-live/比赛进程信息查询接口.sql)：贝泰 `match_direction` 和纳米 `incident_detail`；[旧进程测试](../../../../../../../test-league-platform/testsuites/data-bff/match_monitoring/test_get_match_live.py)：`_is_display_swapped`、`_expected_nami_incidents` 和方向处理函数。

## 定位

状态：`test-point-ready`，限本轮足球进程及通用请求规则。DC-002 未给出具体来源表、北单及用户审核依赖；本卡补足数据路径，不复制模块闭包。Q-001 已依用户指示和旧版代码证据确认不新增篮球进程，不再阻断。

## 关联范围

`sportId`、官方 ID、可选标准 ID、`if_change`、足球来源进程和方向；不包括列表筛选、竞彩事件及备注。

## 闭包目标

识别来源、缺失分支、方向和清理边界；不提供可执行 SQL 或具体样本。

## 输入与输出

输入为竞彩官方赛程、标准比赛及来源数据；输出为纳米、贝泰数组。业务预期为空集合 `[]`，元素字段缺值 `null`，事件方和比分与竞彩队序一致。物理读取及潜在不一致是实现观察，不覆盖预期。

## 关系图

```text
sporttery_{football|basketball}_match --s_match_id--> s_match
  if_change                                         |--nami_match_id--> nami_football_match_live
                                                    |--beitai_match_id--> beitai_football_event --> beitai_football_match
                                                    |--match_id--> bd_batch_matchup
                                                    `--match_id + 当前用户 + 赛果类型--> event_match_check
```

## 表角色

| 表 | 角色与关键字段 | 依据 |
|---|---|---|
| `sporttery_football_match` / `sporttery_basketball_match` | 按官方 `match_id` 定位，读取 `s_match_id`、`if_change` | 竞彩服务 `getSMatchLive` |
| `s_match` | `match_id`、`sport_id`、`nami_match_id`、`beitai_match_id`、队伍关系和主队 ID | 下游服务、DDL `s_match` |
| `nami_football_match_live` | `match_id` 主键及 `incidents` JSON | 下游服务 `buildSMatchLiveIncidents`、DDL |
| `beitai_football_event` / `beitai_football_match` | 比赛事件、时间、得分、球队及来源主队 | 下游服务 `getSMatchLive`、实体与 DDL |
| `bd_batch_matchup` / `event_match_check` | 旧进程使用确认状态和当前用户赛果审核影响队序；本轮确认承接旧进程逻辑，再处理竞彩 `if_change` | 用户答复、旧服务 `getSMatchLive`、旧进程 SQL、DDL |

## 连接与过滤契约

| 路径 | 当前实现关系和边界 |
|---|---|
| 竞彩至标准 | 项目决定竞彩表，`match_id=sportteryMatchId`，再以 `s_match_id` 查 `s_match.match_id`；可选请求 ID 与关联 ID 相等。当前代码未对 `s_match.sport_id` 再校验，DC-002 的“sport_id一致”不能当成已验证实现过滤。 |
| 纳米 | `s_match.nami_match_id=nami_football_match_live.match_id`，按主键至多一条；按 `incidents` JSON 数组顺序构造。ID 为空或行不存在时当前分支可能不赋数组；命中行但内容空时生成空数组。 |
| 贝泰 | `beitai_football_event.match_id=s_match.beitai_match_id`，0..N；实现筛选 `match_started`、`break_start`、`injury_time_shown`、`match_ended`、`red_card`、`yellow_card`、`yellow_red_card`、`substitution`、`score_change`，`order_id` 升序、null 最后；同值次序无额外保证。以事件 `match_id` 查 `beitai_football_match.match_id` 判定主队；缺来源比赛或 team 为 0 时当前 position 为 0。 |
| 旧方向依赖 | 旧方向规则按确认、当前用户审核、标准化优先。当前本地服务在任一来源 ID 存在时按 `bd_batch_matchup.match_id=s_match.match_id` 取首条，未指定排序；审核按 `check_type=RESULT`、`check_source_id=标准比赛 ID 字符串`、`create_account=当前账号` 查询并按来源 ID 建 Map。缺北单、缺登录用户或重复审核键可能导致服务异常；历史 SQL 的“最新/正式”取值条件与当前代码取首条不等同，不把该 SQL 原样作为当前约束。 |

依据下游服务 `getSMatchLive/buildSMatchLiveIncidents` 和竞彩服务 `getSMatchLive`；DDL 证明列与主键，不证明跨表外键或环境数据完整性。

## 数据状态与准备契约

后续需区分官方比赛、标准关联和两来源各自缺失/存在，保留可辨识的主客来源顺序；考虑旧确认、当前用户审核及标准化队序与竞彩队序的关系。多条北单记录时当前首条选择不确定，未查证唯一性前不能假定顺序。按用户确认，本轮不新增篮球进程；不推定篮球请求的返回。

## 查询与断言契约

来源记录提供事件和比分事实；承接旧确认、当前用户审核及标准化方向规则，并增加竞彩 `if_change` 判断，最终独立核对事件方和比分是否与竞彩主客一致。旧方向可能不同于标准方向，不能仅凭 `if_change` 推定最终队序。当前本地服务外层仅交换 `position`，未交换比分，是否造成实际不一致待验证；不可把当前实现直接当作唯一预期。集合及元素空值按模块 Q-003。贝泰九类事件及来源顺序沿用旧规则；旧 SQL 的首条/最新记录选取、null 转 0 和旧测试的额外排序不能不加核对地承接。

## 清理与隔离

优先隔离来源与比赛记录；共享标准比赛的来源 ID、队序及审核记录须恢复，来源事件按可识别范围精确清理。实现修改读取的贝泰实体但未显式保存，持久化副作用未验证。参考回顾指出现有纳米 helper 修改 `s_match.nami_match_id`，其删除 helper 不恢复该字段。

## 当前缺口

环境数据、北单多记录约束、认证、序列化和持久化副作用尚未运行验证。篮球不属于本轮新增进程范围；可执行 SQL、样本和最终清理方式留给自动化设计阶段。
