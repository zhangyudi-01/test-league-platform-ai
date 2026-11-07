# 竞彩赛程备注列表接口分析

> operation：`GET /sporttery/match-monitor/remarks`，`listRemarks`  
> 分析状态：`ready`

## 1. 接口定位与结论

备注弹窗查询指定运动项目和竞彩官方比赛的全部用户备注。当前用户置顶，其余按修改时间和备注 ID 正序；比赛存在但无备注时返回空数组。当前账号来自登录上下文。正常页面先查询竞彩监控列表，点击备注时使用列表中的 `matchId`；用户确认已登录时非法参数和比赛不存在均按参数错误业务 `code=2` 判定。本轮不考虑参数必填或可选。弹窗展示及保存不属于本接口。

## 2. 范围与依据

外部 BFF 路径为 `GET /data-backend/sporttery/match-monitor/remarks`；内部 operation 如上。调用方为备注弹窗，依赖登录；OpenAPI 未声明具体认证字段或 security scheme。相邻 POST `/sporttery/match-monitor/remark` 负责保存，不在本次范围。

| 来源 | 定位与用途 |
|---|---|
| [当前需求](../../preanalysis/00-module-requirement-pack.md) | 比赛列表规则 8、备注规则 1–2（81、96–104 行）；[RSU 映射](../../preanalysis/02-sentence-test-point-map.md) RSU-013–015。 |
| [模块问题](../../preanalysis/03-clarification-questions.md) | Q-003 确认无元素为 `[]`、元素字段无值为 `null`；Q-002 为环境和认证准备。 |
| [OpenAPI](../../../../../global/source-materials/api-docs/league-api-definition/league-core-api/data-backend-openapi.json) | `/paths/~1sporttery~1match-monitor~1remarks/get` 及 `components/schemas/SportteryMatchRemarkItem`、`CommonResultListSportteryMatchRemarkItem`。 |
| [Vegas2.0 接口错误码](../../../../../global/source-materials/api-docs/Vegas2.0接口错误码.md) | 通用错误码列表：`2` 为参数错误；交易服务的比赛不存在错误码不直接套用于管理平台接口。 |
| [用户提供的备注响应模型](../../../../../global/source-materials/api-docs/monitor/SportteryMatchRemarkItem.java)、[列表模型](../../../../../global/source-materials/api-docs/monitor/SportteryMatchMonitorItem.java) | record 成员及类型、创建账号、当前用户和官方比赛 ID；代码本身未声明 JSON 字段必返。用户说明接口文档格式正在修订。 |
| 用户答复 | 前端先查询竞彩监控列表，再将所选比赛 `matchId` 传给备注查询；不考虑参数可选/必选。用户后续结合通用错误码确认已登录时非法参数和比赛不存在均断言业务 `code=2`。 |
| [详细设计](../../../../../global/source-materials/api-docs/竞彩管理详细设计文档.md) | 第 4、5、11 节，37、53、195、198、204 行：ID、类型、路由、通用结果和未匹配标准比赛仍可查询。 |
| [DDL](../../../../../global/source-materials/database-docs/北单运营系统-test2_newgoal-202610261418.sql) | `sporttery_match_remark` 1937–1951 行：字段、唯一键、索引和时间精度；快照未作环境实测。 |
| [本地服务](../../../../../../../apps/league-platform/data-backend/src/main/java/com/league/backend/service/sporttery/SportteryMatchMonitorService.java)、[Repository](../../../../../../../apps/league-platform/coredb-repo/src/main/java/com/league/coredb/repository/SportteryMatchRemarkRepository.java) | `listRemarks`、`currentLoginUser`、`toRemarkItem`、`findBySportIdAndMatchIdAndRemarkTypeOrderByUpdateTimeAscRemarkIdAsc`；仅为实现观察，部署版本未验证。 |
| [序列化配置](../../../../../../../apps/league-platform/common/src/main/java/com/league/common/config/CommonConfigBeans.java) | `customJacksonLocalDateTime` 配置日期序列化；查阅后端、common、apiclient 源码及资源，未发现空字段排除配置。不能排除部署时外部配置。 |
| [历史复用回顾](../../reference-analysis/match-monitoring-reuse-review.md)、[旧列表需求](../../../../../global/source-materials/automation-contracts/data-bff/match-monitoring/legacy-match-list/比赛列表模块需求.md) 74、146 行 | 旧页面也有备注数量和弹窗；当前需求独立确认入口。旧 `m_match_remark` 和旧写入路径不沿用，多账号和精确清理仅作工程经验。 |

复用 [FC-003](../../preanalysis/context-cards/FC-003-竞彩备注生命周期.md)、[DC-004](../../preanalysis/data-closures/DC-004-备注读写数据闭包.md)：备注表、账号、键、排序和清理边界足够，不另建 DC。DC 中比赛存在性校验是保存路径的实现观察；GET 比赛不存在应报错由用户暂定，不能据此认定 GET 已实现该校验，具体查询及准备方法留待后续设计。

## 3. 请求与契约

| 参数 | OpenAPI | 语义与边界 |
|---|---|---|
| `sportId` | query int32、`required:false`、无默认值 | 1 足球、2 篮球；非法值暂按 Q-001 报错口径。 |
| `matchId` | query int64、`required:false`、无默认值 | 竞彩官方比赛 ID，非 `s_match` ID；来自列表所选比赛，与 `sportId` 一起确定比赛；非法值暂按 Q-001 报错口径。 |

未声明请求体、分页或排序参数。按用户指定，本轮不考虑参数可选或必填，也不确定缺参行为；旧 OpenAPI 正在修订，其可选标记不作为缺参行为的依据。非法文本、溢出等框架绑定错误的 HTTP 状态及响应未定义，不等同业务错误；多条件错误优先级未定义。

| 分支 | 文档约定 | 本地实现观察 |
|---|---|---|
| 成功 | HTTP 200 schema；通用 `code=0`、`message=OK`，`data` 为列表 | `CommonResult.ok(response)` |
| 查询参数错误 | 已登录时，不支持的运动或非正 `matchId` 按用户确认断言业务 `code=2`；HTTP、精确 message 和 data 不作严格限定 | 不支持的运动、缺参或 `matchId<=0` 返回 code 2，message“竞彩比赛备注查询参数错误”；缺参不在本轮测试范围 |
| 比赛不存在 | 已登录时按用户确认断言参数错误业务 `code=2`；HTTP、精确 message 和 data 不作严格限定 | 正数 ID 通过参数校验后直接查询备注，不检查比赛存在；可能返回成功空列表或残留备注，未实测 |
| 用户未登录 | operation 列 `code=2`、描述“用户未登录”；HTTP、data 和精确 message 未定义 | 账号不存在或空白时 code 2，message“请先登录” |
| 未预期异常 | 详细设计第 11 节列通用 code 31，operation 未单列异常 response | 外层包装、HTTP 和具体 message 未验证 |

用户确认已登录时上述非法参数与比赛不存在断言业务 `code=2`；同时未登录时不严格限定错误优先级或精确文案（接口 Q-001）。本地先校验参数再获取账号；若确认进入 operation 的参数校验分支则核对 `code=2`，认证过滤器可能先处理请求，不预设其错误码。

## 4. 业务规则与数据路径

需求规定当前用户置顶，其余按修改时间升序；OpenAPI 补充同时间按备注 ID 升序。详细设计第 4–5 节确定 `remark_type=1`、运动项目和官方比赛隔离。DDL 唯一键 `(sport_id, remark_type, match_id, create_account)` 在约束有效时保证每账号最多一条，运行环境未实测。

本地按 `sport_id`、`match_id`、`remark_type=1` 查询 `sporttery_match_remark`，以 `create_account` 和登录账号比较后排序映射；不连接比赛表或验证官方比赛存在。正常调用取列表所选比赛；比赛不存在时用户暂定应报错，与该本地查询路径可能不一致，需调试核实。账号大小写规范未定义，Java 精确比较仅为实现观察。DDL 时间为非空 `datetime`，未声明小数秒，同秒以 ID 排序；时区、环境精度和异常空时间语义未定义，本地空时间置后仅为观察。

## 5. 响应与分支

用户提供的 `SportteryMatchRemarkItem.java` 定义以下八个 record 成员；本地 `toRemarkItem` 构造时全部赋值。用户确认先按无记录为 `[]`、记录内字段无值为 `null` 的口径处理（接口 Q-003、模块 Q-003），结合模型核对这八个字段；调试如有差异再调整。模型无字段省略注解，查阅范围内未发现空字段排除配置，但部署 JSON 及外部配置未验证。

| 字段 | 类型 | 含义及来源 |
|---|---|---|
| `remarkId` | int32 | 备注身份 `remark_id` |
| `sportId` | int32 | 项目 `sport_id` |
| `matchId` | int64 | 官方比赛 `match_id` |
| `account` | string | 创建账号 `create_account`；OpenAPI 指明始终为创建人 |
| `remark` | string | 备注内容 `remark` |
| `isCurrentUser` | boolean | 是否当前用户；本地比较创建账号和登录账号 |
| `createTime`、`updateTime` | date-time 字符串 | 创建及修改时间；偏移和精度未进一步规定 |

成功有记录按上述顺序返回；比赛存在但无备注时按模块 Q-003 为 `data=[]`，不虚构当前用户记录。比赛不存在则按用户暂定口径报错，而非因无备注直接视为成功空列表。页面无备注显示空是 UI 表现，不等于返回空对象。错误 data 形态未明，不能混同 `null`、缺字段及空列表。DDL 允许备注或创建账号为空字符串，其业务语义未单独确认，不能自动等同 Q-003 的无值。

## 6. 职责与副作用

不负责保存、编辑、取消、弹窗布局、赛程标题或列表备注计数。未关联标准比赛仍可查询，不同于官方比赛不存在。GET 未定义写入副作用；本地 `@Transactional(readOnly=true)` 和代码路径为只读观察。同数据和账号下重复查询结果相同；并发保存可能改变结果，不保证跨请求快照一致。

## 7. 差异与问题

用户将参数必填/可选移出本轮，确认已登录时非法参数和比赛不存在均按业务 `code=2` 判定；字段空值口径详见[问题单](./clarification-questions.md)。本地 GET 无比赛存在性校验，与不存在时应返回 `code=2` 的预期存在潜在差异；部署结果尚未验证。用户提供的 Java record 不是已验证的线上 JSON 响应，调试时需复核并按用户意见调整。模块 FC/DC 将实现规则称为已确认的文字不覆盖本文证据分级。本轮未执行接口或数据库验证。

## 8. 测试方案交接

复用 FC-003、DC-004 的已确认部分及模块 Q-003，关注官方 ID 与项目隔离、用户身份、同时间排序、空集合及记录内空值。已登录时非法参数和比赛不存在断言业务 `code=2`，不严格限定 HTTP、文案和错误 data；多重错误不限定优先级，认证层错误码不预设。留意本地 GET 缺少比赛存在性校验的潜在差异。数据准备、清理和实际响应核验留给后续阶段。

**分析状态：ready**  
**测试方案就绪：是**。主要业务口径已足以进入测试方案；暂定的错误和空值口径在调试时核对。
