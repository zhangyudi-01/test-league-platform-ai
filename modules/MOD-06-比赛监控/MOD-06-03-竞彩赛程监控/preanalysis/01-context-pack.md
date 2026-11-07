# MOD-06-03 竞彩赛程监控 Context Pack

## 目标

建立竞彩赛程监控模块的接口与功能测试前置基线。模块包含竞彩赛程监控比赛列表和备注两个需求单元；当前接口主契约为五个 data-backend 接口，功能规则还包含筛选、自动刷新、进程/事件/备注弹窗和状态颜色。本文件只保存背景、能力、逻辑、边界和输入契约，不生成正式测试点。

## 资源索引

| 资源 ID | 可点击文件 | 用途 |
|---|---|---|
| SRC-MOD | [当前模块需求](./00-module-requirement-pack.md) | 当前模块两个需求单元原文 |
| SRC-UPSTREAM-LIST | [比赛列表上游需求包](../MOD-06-03-01-比赛列表/00-module-requirement-pack.md) | 比赛列表原始拆分输入 |
| SRC-UPSTREAM-REMARK | [备注上游需求包](../MOD-06-03-02-备注/00-module-requirement-pack.md) | 备注原始拆分输入 |
| SRC-GLOBAL | [项目全局上下文](../../../../global/project-context.md) | 第十三轮主题、工程规范、权威优先级 |
| SRC-PRD13 | [第十三轮 PRD](../../../../global/source-materials/current-requirement/竞猜赛事运营系统需求PRD文档-13轮冲刺.md) | PBL-634 原始需求全文定位 |
| SRC-PBL13 | [第十三轮 PBL CSV](../../../../global/source-materials/current-requirement/赛事运营系统第十三轮冲刺-PBL研发需求.csv) | 模块任务归属和迭代范围 |
| SRC-API-BACKEND | [data-backend OpenAPI](../../../../global/source-materials/api-docs/league-api-definition/league-core-api/data-backend-openapi.json) | 五个当前接口的路径、参数和响应 schema |
| SRC-DB13 | [第十三轮竞彩数据库设计](../../../../global/source-materials/database-docs/第十三轮冲刺竞彩抓取数据库设计和变更.md) | 竞彩表、事件、备注和审计设计 |
| SRC-DB-SCHEMA | [最新数据库 DDL](../../../../global/source-materials/database-docs/北单运营系统-test2_newgoal-202610261418.sql) | 当前表字段、主键、索引和约束 |
| SRC-CODE-MONITOR | [当前监控服务](../../../../../../apps/league-platform/data-backend/src/main/java/com/league/backend/service/sporttery/SportteryMatchMonitorService.java) | 当前接口实现与聚合逻辑 |
| SRC-CODE-RULES | [状态/比分/颜色规则](../../../../../../apps/league-platform/data-backend/src/main/java/com/league/backend/service/sporttery/SportteryMatchMonitorRules.java) | 派生字段规则 |
| SRC-CODE-CONTROLLER | [监控 Controller](../../../../../../apps/league-platform/data-backend/src/main/java/com/league/backend/controller/sporttery/SportteryMatchMonitorController.java) | 参数验证和接口入口 |
| SRC-CODE-EVENT | [竞彩事件实体](../../../../../../apps/league-platform/coredb-entity/src/main/java/com/league/coredb/entity/SportteryMatchEventEntity.java) | 事件字段与唯一标识 |
| SRC-CODE-REMARK | [竞彩备注实体](../../../../../../apps/league-platform/coredb-entity/src/main/java/com/league/coredb/entity/SportteryMatchRemarkEntity.java) | 备注唯一键和持久化字段 |
| SRC-CODE-EVENT-REPO | [事件 Repository](../../../../../../apps/league-platform/coredb-repo/src/main/java/com/league/coredb/repository/SportteryMatchEventRepository.java) | 事件过滤和排序的本地实现观察 |
| SRC-CODE-REMARK-REPO | [备注 Repository](../../../../../../apps/league-platform/coredb-repo/src/main/java/com/league/coredb/repository/SportteryMatchRemarkRepository.java) | 备注查询和当前用户定位 |
| SRC-HIST-LIVE | [旧进程需求](../../../../global/source-materials/automation-contracts/data-bff/match-monitoring/legacy-match-live/比赛进程信息需求.md) | 历史进程语义参考 |
| SRC-HIST-LIVE-SQL | [旧进程 SQL](../../../../global/source-materials/automation-contracts/data-bff/match-monitoring/legacy-match-live/比赛进程信息查询接口.sql) | live 来源参考 |
| SRC-OLD-TESTS | [旧比赛列表脚本](../../../../../../tests/test-league-platform/testsuites/data-bff/match_monitoring/test_get_monitoring_list.py)、[旧进程脚本](../../../../../../tests/test-league-platform/testsuites/data-bff/match_monitoring/test_get_match_live.py) | 复用 fixture、动态预期、清理和 Excel 风格 |
| CTX | [本 Context Pack](./01-context-pack.md) | 模块背景、能力、逻辑和边界 |
| RSU-INDEX | [RSU 映射](./02-sentence-test-point-map.md) | 原文单元和后续输入 |
| Q-INDEX | [问题清单](./03-clarification-questions.md) | 问题、答案和状态 |
| FC-INDEX | [Context Cards](./context-cards/README.md) | 可复用局部上下文 |
| DC-INDEX | [Data Closures](./data-closures/README.md) | 最小数据路径 |

## 当前阶段边界

### In Scope

- 五个当前接口：竞彩赛程列表、竞彩进程、竞彩事件查询、备注查询、备注保存。
- 列表的足球/篮球分流、业务日闭区间、默认值和错误参数。
- 竞彩官方比赛源数据与标准化比赛补充信息的合并、排序、空标准比赛留行。
- 排名、状态、比分、开奖状态、事件/备注计数和行背景色的后端契约。
- if_change 对标准化排名、比分和进程 position 的影响。
- 事件查询与倒序排序、SPORTTERY 来源过滤。
- 备注登录、当前用户置顶、其他用户排序、300 字符限制、去首尾空白、按当前用户唯一记录更新。
- 前端功能测试所需的筛选、刷新、进程弹窗、事件弹窗和备注弹窗行为。

### Out of Scope

- 竞彩数据采集任务、赔率接口、竞彩赛事/球队管理接口的独立功能。
- 旧 /s-match 与 /s-match/live 的原接口测试；旧内容仅作标准化和 live 语义参考。
- 自动刷新真实计时稳定性、滚动条像素位置和视觉颜色像素级校验。
- 未在当前模块需求或当前 API 中声明的导出、赛果确认、异常管理写入链路。

## 资料优先级

1. 当前模块需求包和第十三轮 PRD/PBL。
2. 用户本次明确范围：接口+功能测试、五个测试脚本、使用当前 OpenAPI 和已新增数据库表。
3. 当前 OpenAPI、当前实现代码和最新数据库设计/DDL。
4. 旧比赛监控自动化契约、旧测试脚本和旧 SQL，仅作复用参考。

## 模块在需求全文中的背景与定位

PBL-634“竞彩赛程监控”将中国竞彩官方足球/篮球赛程接入现有比赛监控视图。列表以竞彩官方比赛为主体，以 sporttery_*_match 为来源，通过 s_match_id 补充标准化比赛状态、排名、比分和直播进程；事件与备注以竞彩官方 match_id 为业务身份，并使用 sport_id 隔离足球/篮球相同 ID 域。第十三轮 PRD 的对应范围为竞彩赛程监控章节中的比赛列表与备注。

## 模块目标与能力

1. 查询按运动项目和业务日过滤的竞彩赛程。
2. 标准化比赛缺失时仍保留竞彩源赛程并显示未匹配。
3. 标准化比赛存在时补充排名、状态、比分和足球直播进程。
4. 统计竞彩事件和用户备注；按竞彩事件标题与更新时间确定颜色，无事件为 NONE，本期不使用任务表。
5. 提供事件查询、进程查询和备注查询/保存接口。
6. 支持列筛选、自动刷新、进程弹窗、事件弹窗和备注弹窗。

## 已确认的详细逻辑

### 主链路

请求参数 -> Controller 参数校验 -> 按 sportId 读取足球/篮球竞彩赛程 -> 批量读取联赛和球队 -> 按 sport_id + s_match_id 读取 s_match -> 按 sport_id + 官方 match_id 读取事件和备注 -> 组装排名、状态、比分、开奖、计数和颜色 -> 返回列表。本期不使用任务表。

进程请求 -> sportId + sportteryMatchId 解析竞彩比赛 -> 校验可选 matchId 与 s_match_id 一致 -> 读取标准比赛和 live -> 按 if_change 将 live 进程队序对齐到竞彩赛程主客顺序 -> 返回两个进程数组。

事件请求 -> 根据 sportId、官方 matchId 查询 sporttery_match_event 中匹配记录 -> create_time DESC、event_id DESC 不分页返回全部事件；标题、时间和异常详情分别取 event_name、create_time、reason_desc。本地旧实现还过滤 source_type=SPORTTERY；不按开售时间裁剪。

备注查询/保存 -> 校验 sportId、官方 matchId、登录态 -> remark_type=1 查询或 upsert 当前用户 -> 当前用户置顶，其余按更新时间和备注 ID升序。

### 逻辑说明

- 列表默认 sportIds 为足球和篮球；显式传入时去重，非法运动项目返回参数错误。
- 业务日默认上海时区当天至当天+6，开始/结束包含；结束早于开始返回参数错误；源数据为空返回空数组。
- 列表主体始终是竞彩源比赛，s_match 缺失不丢行；用户确认关联到已替换标准比赛时追随新比赛 ID，异常替换链处理待确认。
- 联赛简称/全称、球队全称/名称存在回退规则；列表球队名称与竞彩比赛表的 home/away 顺序一致，不受 if_change 影响。排名来自 s_match，按 if_change 对齐到竞彩主客队顺序。
- 已开奖只取竞彩比分，不用标准比分补齐，有比分时 `source=SPORTTERY`；未开奖取标准比分，有比分时 `source=S_MATCH`，标准比分按 if_change 对齐。选定来源无任何有效比分时 score 为 null。
- 两项目均删除 `periods`，篮球 `half=null`，竞彩篮球全场取 `home_score/away_score`。
- sell_status=4 表示已开奖（0待开售、1已开售、2暂停销售、3已停售、4已开奖）；标准化比赛缺失时状态名为未匹配。
- 行颜色按事件更新时间和 `reason_title` 确定，无事件为 NONE；本期不使用任务表或解除状态。
- 事件计数按 sport_id + 官方 match_id。事件弹窗按创建时间、事件 ID 倒序展示竞彩事件表中的记录，标题取 `event_name`，异常详情取 `reason_desc`；不套用旧模块开售前/开售后筛选。本地旧实现还按 SPORTTERY 来源过滤。
- 备注计数只统计 remark_type=1。
- 进程接口只接受有效 sportId 和 sportteryMatchId；可选 matchId 必须等于关联 s_match_id；竞彩比赛不存在、未关联或标准比赛不存在均返回参数错误。
- 事件接口不分页，返回全部匹配事件；无匹配记录时集合字段返回 `[]`。备注接口必须登录，当前用户置顶但返回全部用户，并返回 isCurrentUser；没有备注时集合字段返回 `[]`。
- 五个接口的集合没有元素时返回 `[]`；集合元素内部的具体字段无值时保持 `null`，不做空数组/空字符串替换。POST 备注保存仍返回单条对象，不适用集合空值规则。
- 保存备注最多 300 个用户感知字符，首尾空格计入（[API-005 Q-001](../interfaces/API-005-save-match-remark/clarification-questions.md)）；OpenAPI 描述去首尾空白后非空，保存值是否保留空格不由该答复单独决定。账号和 remark_type 服务端决定；当前用户唯一记录更新而非新增。

## 已确认的理解边界

- 赛程绿色背景对应事件 `reason_title` 的当前名称为“比赛方变更”，替代需求原文中的“球队变更”；确认记录见 [API-001 Q-011](../interfaces/API-001-get-match-monitor/clarification-questions.md)。
- 当前模块五接口以当前 OpenAPI 为准；旧接口参数不迁移。
- 竞彩官方 matchId 与标准化 s_match.match_id 是不同 ID 域；事件/备注用前者，标准化补充用后者。
- sport_id 必须参与比赛、事件、备注查询，不能只按 match_id。
- API-002 进程按用户确认沿用旧足球进程逻辑并增加竞彩 `if_change` 判断，旧代码没有篮球进程，故本轮不新增；旧接口参数和空值表现不迁移，细节见 [API-002 Q-001](../interfaces/API-002-get-match-live/clarification-questions.md)。不迁移旧模块开售前后事件筛选，竞彩事件表是事件弹窗的数据源。
- if_change 不改变竞彩源主客队名称；只用于把 s_match/live 来源数据的队序转换到竞彩赛程主客队顺序。
- 测试使用本地 setting 指向的开发环境和全权限账号 zhangyudi；密码只从本机安全配置读取，不写入产物。
- 用户要求后续产出接口+功能测试及五个脚本；本阶段不提前写这些产物。
- OpenAPI 未声明的必填细节和前端视觉细节不能凭空假设，后续以实现/框架补齐。

## 领域契约边界

- 当前主契约：data-backend OpenAPI 五个 sporttery match-monitor 路径、schema 和当前 Controller/Service。
- 数据契约：第十三轮竞彩表设计、最新 DDL、实体和 Repository。
- 历史契约：旧比赛监控 live/list 只用于标准化比赛、贝泰/纳米进程和主客顺序参考。
- 功能契约：筛选、刷新、弹窗、颜色和取消属于功能测试输入；只有接口可观察字段进入接口断言。

## 原文、上下文和验证信息的边界

| 信息类型 | 保存位置 | 示例 |
|---|---|---|
| 需求原文 | 00-module-requirement-pack.md | 业务日默认范围、备注300字符 |
| 模块逻辑 | 01-context-pack.md | 列表主体、ID域、比分来源、备注upsert |
| 原文映射 | 02-sentence-test-point-map.md | RSU-001～RSU-016 |
| 人工确认 | 03-clarification-questions.md | Q-001～Q-004 |
| 链路上下文 | context-cards/ | FC-001～FC-003 |
| 数据契约 | data-closures/ | DC-001～DC-004 |
| 验证/实现证据 | 资源索引、FC/DC入口 | OpenAPI、Service、Entity、Repository |

## 后续测试点生成输入规则

### 固定输入

1. SRC-GLOBAL 项目全局上下文全文。
2. SRC-MOD 当前模块需求全文。
3. CTX 本文件的模块背景、能力、详细逻辑和理解边界。
4. 当前 RSU-ID 完整映射行。

### 动态输入

- 当前 RSU 对应的 OpenAPI 片段和 Controller/Service 代码。
- 相关 Q、FC、DC 实际内容；数据库 RSU 必须显式读取对应 DC。
- 当前 DDL、竞彩数据库设计、旧接口/SQL和现有 pytest/fixture/Excel，仅限 RSU 声明范围。
- 开发环境 URL 和账号已确认；具体样本 ID、数据库连接及 SQL 在用例就绪性阶段实例化，密码从本机安全配置注入。

## 当前缺口

- 当前 setting 中 DATA_BFF_URL 已指向开发环境，登录账号已确认；可用样本与清理型数据准备在用例就绪性阶段从开发库动态定位。
- BFF 代理路径和登录 fixture 的实际组合需在脚本阶段核对；当前 OpenAPI 的 data-backend 路径已确定。
- getSMatchLiveForResolvedMatch 仍需动态检查实现字段映射；无数据集合预期已按人工确认统一为 `[]`。当前进程响应 DTO/服务存在未命中路径可能留下 null 的风险，接口测试应按 `[]` 契约验证。已确认承接旧足球进程规则的范围见 API-002 Q-001，旧接口参数与旧空值表现不自动继承。
