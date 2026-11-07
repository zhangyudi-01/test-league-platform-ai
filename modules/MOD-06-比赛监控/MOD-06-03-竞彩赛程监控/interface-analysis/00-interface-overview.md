# MOD-06-03 竞彩赛程监控接口总览

## 分析范围

当前后端接口为五个独立 operation：列表、进程、事件查询、备注列表、备注保存。接口分析与前端功能分析分层：自动刷新、列头筛选、弹窗显示/关闭、滚动位置等仍属于功能侧；接口侧验证请求到响应、数据来源、过滤、排序和写入结果。RSU-008 是列表行颜色规则，属于 API-001 可观察字段及页面颜色渲染两层；RSU-010 才是列头筛选功能。当前列表 operation 只有 sportIds 与 businessDateStart/End，不含状态/事件/备注/开奖筛选字段。

## 契约优先级

| 来源 | 本分析中的用途 | 限制 |
|---|---|---|
| [当前模块需求包](../preanalysis/00-module-requirement-pack.md) 与 [已确认问题](../preanalysis/03-clarification-questions.md) | 当前业务可观察行为和用户确认的 null/集合语义 | 需求没有说明的技术细节不从旧模块自动补入 |
| [data-backend OpenAPI](../../../../global/source-materials/api-docs/league-api-definition/league-core-api/data-backend-openapi.json) | 当前 operation 路径、请求字段、响应 schema | `required`、校验边界和错误响应建模存在不完整处，见发现清单 |
| [第十三轮数据库设计](../../../../global/source-materials/database-docs/第十三轮冲刺竞彩抓取数据库设计和变更.md) 与 [DDL](../../../../global/source-materials/database-docs/北单运营系统-test2_newgoal-202610261418.sql) | 当前表/键/数据所有权 | 不能用旧 `/s-match` 的 `s_event`、`task` 查询替代新表 |
| [当前 Controller](../../../../../../apps/league-platform/data-backend/src/main/java/com/league/backend/controller/sporttery/SportteryMatchMonitorController.java)、[Service](../../../../../../apps/league-platform/data-backend/src/main/java/com/league/backend/service/sporttery/SportteryMatchMonitorService.java)、[Rules](../../../../../../apps/league-platform/data-backend/src/main/java/com/league/backend/service/sporttery/SportteryMatchMonitorRules.java) | 确认实现当前如何处理输入、聚合和错误，发现实现差异 | 代码不是需求真值；发现差异后按当前需求/API 断言并报告实现风险 |
| [历史复用回顾](../reference-analysis/match-monitoring-reuse-review.md) | 只复用测试数据组织、动态预期、清理方法的经验 | 旧接口参数、旧页面规则和旧数据库 SQL 不构成当前接口合同 |

data-backend operation 使用 `/sporttery/...`；设计文档/权限配置列出的管理端 BFF 路由为 `/data-backend/sporttery/...`。pytest 的 `DataBff` 应走项目现有 BFF session/client 封装，不要把数据库连接、认证凭据复制到接口分析或测试文件。

## 五接口与追溯

| API-ID | Method / path | Operation | 主要契约 | RSU / 数据闭包 | 计划脚本 |
|---|---|---|---|---|---|
| API-001 | `GET /sporttery/match-monitor` | `listMatchMonitor` | 足球/篮球竞彩列表、标准化补充、状态/比分/计数/颜色 | RSU-001～008；FC-001、DC-001 | `test_get_match_monitor.py` |
| API-002 | `GET /sporttery/match-monitor/live` | `getSMatchLive` | 以运动项目+竞彩官方 ID 路由到 s_match 和来源 live | RSU-004、011；FC-002、DC-002 | `test_get_match_live.py` |
| API-003 | `GET /sporttery/match-monitor/events` | `listEvents` | 按运动项目和官方比赛 ID 查询事件，不分页并稳定倒序返回数组 | RSU-012；DC-003 | `test_get_match_events.py` |
| API-004 | `GET /sporttery/match-monitor/remarks` | `listRemarks` | 当前及其他用户备注、登录账号标识、置顶排序 | RSU-013～015；FC-003、DC-004 | `test_get_match_remarks.py` |
| API-005 | `POST /sporttery/match-monitor/remark` | `saveRemark` | 当前用户备注校验、按唯一键新增/更新、返回对象 | RSU-016；FC-003、DC-004 | `test_save_match_remark.py` |

脚本路径当前只在 manifest 中登记为 `planned-not-created`。一接口一脚本是执行组织，不意味着五个脚本必须各自复制 fixture；主赛程造数、登录和逐表清理应评估放在新套件的公共 `conftest.py`/helper。

## 当前模块已有输入

- `preanalysis/Q-002` 已确认使用本机配置中指向开发环境的 `DATA_BFF_URL` 和全权限账号 `zhangyudi`；密码只从本机配置/既有认证封装取得，不写进文档或脚本。具体样本动态从开发库确认。
- `preanalysis/Q-003` 已确认集合无元素时为 `[]`，集合元素内无值为 `null`，备注保存仍返回单个对象。进程响应的当前实现可能在来源 ID/来源行缺失时返回 `null` 数组，这是已知实现风险，不改变接口预期。
- 事件详情必须区分当前 `sporttery_match_event` 与历史 `s_event`；标题、时间和异常详情分别取 `event_name`、`create_time`、`reason_desc`。本地旧事件详情实现额外过滤 `source_type=SPORTTERY`；列表事件数实现目前按 `sport_id + source_id` 批量统计。
- 竞彩官方 `matchId` 与 `s_match.match_id` 是不同 ID 域。事件/备注接口和列表 identity 使用官方 ID；进程接口先从官方赛程记录解析 `s_match_id`。

## 接口级发现与待澄清项

这些条目是“来源/实现差异登记”，不是新需求，也不直接变更 RSU。测试点阶段应按模块需求和已确认答案写预期；实现偏离时记录为实现缺陷风险。需开发/产品确认时再回填普通问题清单或正式需求，不把本表当成私自裁决。

| Finding ID | 等级 | 发现 | 依据与后续处理 |
|---|---|---|---|
| IAF-001 | 高 | 模块需求要求按事件更新时间最大值决定行颜色，详细设计 §8.2 明确 `update_time DESC,event_id DESC`；当前 Rules 排序键是事件 `createTime DESC,eventId DESC`。 | 业务预期按 update_time 口径确定；API-001 分析记录实现偏差，测试构造 create/update 时间顺序交叉的数据，不把 create_time 写成预期。 |
| IAF-002 | 中 | 用户确认详细设计中的事件快照和关联任务描述是旧口径，并最新更正事件标题取 `event_name`；当前本地 Service 仍取 `reason_title`。 | 按模块 Q-004 设计预期，不加入旧任务或快照字段；记录字段映射实现差异，实际接口返回尚未验证。 |
| IAF-003 | 中 | 多个 OpenAPI 参数标记 `required:false`，但 Service 将其作为必需并返回业务 code=2；备注 POST schema 也没有 `required` 字段或 `remark` 长度边界。 | 接口测试可按运行时业务校验测试缺参；建议接口文档补齐 required、maxLength、响应错误 schema 与参数格式错误行为。 |
| IAF-004 | 已确认 | Live operation 接受 sportId=1/2；当前链路分别查竞彩赛程，但旧版 `/s-match/live` 只实现纳米/贝泰足球进程，未发现篮球进程分支。 | 用户确认沿用旧进程并增加 `if_change`，旧代码没有的篮球进程本轮不新增；见 [API-002 Q-001](../interfaces/API-002-get-match-live/clarification-questions.md)。入口接受 `2` 不等于篮球进程已支持，也不推定篮球请求的空数组或错误响应。 |
| IAF-005 | 中 | Live 返回 DTO 两个集合字段未初始化；当前服务在 Nami ID 缺失或 Nami live 行不存在的分支不设置字段，可能序列化 `null`，与 Q-003 已确认 `[]` 契约不一致。 | 空数据场景按 Q-003 断言 `[]`；若实际 `null`，作为实现差异报告，不因现状改写预期。 |
| IAF-006 | 中 | 本地代码中，竞彩列表计数按 `sport_id + source_id` 读取事件，旧事件详情实现额外限制 `source_type=SPORTTERY`。 | 开发调整后核对 source type 实际取值和两条链路的过滤差异；不要默默假设计数与弹窗条数恒等。 |
| IAF-007 | 低 | OpenAPI 将数组/对象元素字段大多声明为可选，没有精确 required/nullability 和字段长度约束；多数错误仅在 description 里提到 code，HTTP 状态与错误 body schema 未建模。 | JSON 主体断言依已确认字段语义；HTTP 状态、框架参数绑定错误在脚本阶段按实际 BFF 契约补充，不先猜 4xx/200。 |
| IAF-008 | 低 | 备注保存用 Java `String.length()` 校验 300，OpenAPI 仅文字描述字符数，Unicode 补充平面字符按 UTF-16 code unit 计数可能与“字符”理解不同。 | 先覆盖空白、300/301 普通字符边界；Emoji/代理对边界在产品确认字符定义后再定断言。 |
| IAF-009 | 中 | 竞彩管理详细设计第 8 节把《竞彩赛程监控接口设计》列为详细参数、字段和示例的接口契约，但本次可访问工作区中未找到该独立文档；当前可用接口 schema 是 data-backend OpenAPI。 | 本轮先以用户指定的当前 OpenAPI、模块需求和实现证据完成五个接口分析；后续若找到接口设计稿，应核对并登记差异，不静默覆盖当前分析。 |
| IAF-010 | 高 | 列表需求 RSU-004 及 API-001 Q-001 已确认五字段 `beitaiFootballMatchLiveDTO`；用户反馈开发已修复，新版 OpenAPI 已引用该对象，本地子模块 `95884a32` 未体现修复。 | 业务口径已确认，可进入方案设计；修复版本及部署情况待核验。OpenAPI 的对象/字段可空性仍需与已确认口径对齐。数据路径见 API-001 ADC-001。 |

## 不属于接口测试的要求

自动刷新、查询与筛选状态保留、表头筛选控件、列表滚动位置、行颜色实际渲染、点击后弹窗布局和取消按钮不保存属于功能测试。接口脚本可核对这些 UI 所消费的 API 数据，但不能声称通过接口响应验证了视觉/交互行为。
