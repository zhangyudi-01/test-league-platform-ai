# API-005 保存竞彩赛程备注接口分析
> operation：POST /sporttery/match-monitor/remark · saveRemark  
> 分析状态：ready

## 1. 接口定位与结论摘要

管理端保存指定竞彩官方比赛的当前登录用户备注：服务端确定账号及类型，已有该用户记录则更新，否则新增，成功返回单个备注对象。用户已确认最多 300 个前端用户感知字符，统计包含首尾空格（[Q-001](./clarification-questions.md)）；OpenAPI 的去空白描述和源码的长度计数与此存在差异，详见第 7 节。本轮回填答复，不将计数口径等同于保存值是否去空白。

## 2. 分析范围与依据

调用方为竞彩赛程监控页面；管理端路由 `POST /data-backend/sporttery/match-monitor/remark`，内部 operation 为 `POST /sporttery/match-monitor/remark`。`GET .../remarks` 为相邻查询接口。需登录；模块 Q-002 已确定开发环境及认证来源，本产物不复制凭据和账号标识。权限配置将 POST 列入备注权限，但此 operation 未规定权限拒绝的具体响应。

| 来源 | 范围和用途 |
|---|---|
| [需求包](../../preanalysis/00-module-requirement-pack.md) 备注规则 1～5；[RSU-016](../../preanalysis/02-sentence-test-point-map.md) | 编辑当前用户备注、300 字符及保存、取消行为 |
| [模块问题](../../preanalysis/03-clarification-questions.md) Q-002、Q-003 | 环境及认证来源；保存返回单对象 |
| [接口 Q-001](./clarification-questions.md) | 2026-11-02 确认用户感知字符计数及首尾空格计入 |
| [OpenAPI](../../../../../global/source-materials/api-docs/league-api-definition/league-core-api/data-backend-openapi.json) `/paths/~1sporttery~1match-monitor~1remark/post`，`SportteryMatchRemarkRequest`、`CommonResultSportteryMatchRemarkItem`、`SportteryMatchRemarkItem` | 请求、响应和四类错误合同 |
| [数据库设计](../../../../../global/source-materials/database-docs/第十三轮冲刺竞彩抓取数据库设计和变更.md) `sporttery_match_remark`、`audit_sporttery_match_remark`、权限 153；[DDL 快照](../../../../../global/source-materials/database-docs/北单运营系统-test2_newgoal-202610261418.sql) 1937～1950、3096～3110 | 字段、唯一键和审计表；快照不是运行库实测 |
| [Controller](../../../../../../../apps/league-platform/data-backend/src/main/java/com/league/backend/controller/sporttery/SportteryMatchMonitorController.java) `saveRemark`；[Service](../../../../../../../apps/league-platform/data-backend/src/main/java/com/league/backend/service/sporttery/SportteryMatchMonitorService.java) `saveRemark`、`matchExists`、`toRemarkItem`；[Entity](../../../../../../../apps/league-platform/coredb-entity/src/main/java/com/league/coredb/entity/SportteryMatchRemarkEntity.java)、[Repository](../../../../../../../apps/league-platform/coredb-repo/src/main/java/com/league/coredb/repository/SportteryMatchRemarkRepository.java) | 仅识别当前源码的校验顺序、数据路径和风险 |
| [历史索引](../../reference-analysis/README.md)、[复用回顾](../../reference-analysis/match-monitoring-reuse-review.md) 备注行；[旧数据准备分析](../../../../../global/source-materials/automation-contracts/data-bff/match-monitoring/legacy-match-list/查询结果数据准备需求分析V2.md) `q. 备注数`；[旧列表脚本](../../../../../../test-league-platform/testsuites/data-bff/match_monitoring/test_get_monitoring_list.py) `remark_count_map` | 历史使用 `m_match_remark`、type=3，不可沿用其表和过滤；可借鉴隔离和精确清理 |

复用 [FC-003](../../preanalysis/context-cards/FC-003-竞彩备注生命周期.md) 和 [DC-004](../../preanalysis/data-closures/DC-004-备注读写数据闭包.md)。DC-004 已覆盖项目、官方比赛、账号、类型及唯一写入路径；其中仅有源码支持的细节以本分析的实现观察为准。其 `test-point-ready` 不意味着运行库已验证，无须另建闭包或上下文卡。

## 3. 请求与接口契约

请求是 `application/json` 对象。OpenAPI 未声明 body `required`、字段 `required`、默认值、nullable、额外属性规则、长度及数值约束；不能将 schema 缺项视作允许无效输入。账号和备注类型由服务端决定，不是请求字段。

| 字段 | schema | 含义与边界 |
|---|---|---|
| `sportId` | integer/int32 | 运动项目；足球 1、篮球 2 的映射见 [相邻查询 operation](../../../../../global/source-materials/api-docs/league-api-definition/league-core-api/data-backend-openapi.json) `/paths/~1sporttery~1match-monitor~1remarks/get`；保存 schema 未列 enum，当前服务仅接受 1/2。 |
| `matchId` | integer/int64 | 竞彩官方比赛 ID，非标准比赛 ID；当前服务要求正数。 |
| `remark` | string | 上限 300 个前端用户感知字符，统计包含首尾空格（Q-001）；OpenAPI 另要求去除首尾空白后非空，且描述处理后不得超过 300 字符。Q-001 不单独裁定持久化值是否保留空格。 |

合同未规定多错误同时存在时的优先级。源码 `saveRemark` 依次校验 body/项目/正数 ID/remark 非 null，再 `strip()` 和 `String.length()`，再登录，再比赛存在性。缺失 body、字段或 null 在源码相应分支返回参数错误；格式错误、错误 JSON 类型等可能在框架绑定阶段拒绝，状态码和消息没有此 operation 的合同，未经实测不作断言。`strip()` 空白范围为实现行为，未等同于任意 Unicode 空白。

### 错误响应

OpenAPI operation 描述明确列出业务 code 和条件描述，但未建模独立错误 response schema，未逐项规定 HTTP 状态及 `data`。表内为合同错误描述，不假定必然逐字等于实际返回；公共响应允许附加或裁剪系统错误信息。

| 条件 | HTTP | 业务 code | 描述 | data |
|---|---|---|---|---|
| 请求参数错误 | 未单独规定 | 2 | 请求参数错误 | 未规定 |
| 用户未登录 | 未单独规定 | 2 | 用户未登录 | 未规定 |
| 比赛不存在或项目不匹配 | 未单独规定 | 2 | 竞彩比赛不存在或运动项目不匹配 | 未规定 |
| 保存冲突 | 未单独规定 | 2 | 备注保存冲突，请重试 | 未规定 |

源码参数错误分别为“竞彩比赛备注参数错误”和“备注去除首尾空白后不能为空且不可超过 300 个字符”；未登录为“请先登录”，其余两项与描述一致。Controller 捕获 `DataIntegrityViolationException` 返回冲突；注释称并发首次写入唯一键冲突是可能原因，不能断定所有完整性异常均由并发引起。网关认证或绑定可能先于业务方法，尚未实测。

## 4. 业务规则与数据处理流程

1. 输入定位竞彩项目和官方比赛。用户确认长度按页面用户感知字符计算，输入中的首尾空格也计入，最多 300；不得以去空白后的文本计数。OpenAPI 另描述去除首尾空白及非空；此答复只解决计数，不更改该描述中保存规范化的部分。合同未定义校验先后。
2. 服务端确定当前登录账号及监控备注类型。数据库设计约定 `remark_type=1`，以 `sport_id + remark_type + match_id + create_account` 唯一隔离；不同用户、项目及比赛互不覆盖。
3. 当前源码按项目分别在 `sporttery_football_match`、`sporttery_basketball_match` 以官方 `match_id` 检查存在性，不检查标准比赛关联；不存在或项目不匹配返回相应错误。再以完整键查找自身备注，存在更新，否则新增；没有依据要求按销售状态或比赛时间过滤。
4. 源码新增时设置项目、比赛、类型和创建账号；两条路径均设置规范化内容及更新账号，`saveAndFlush` 后映射响应。DDL 为 `varchar(300)`、唯一约束及创建/更新时间默认规则；实际库、审计字段填充和精度未运行验证。

重复提交同一账号/比赛不会产生第二条业务记录；相同文本是否产生新的更新时间、审计版本或操作日志未在接口合同中定义，不推断完全无副作用或保证更新时间变化。并发及事务效果尚需运行验证。

## 5. 响应字段与结果分支

成功为 HTTP 200 的 `CommonResultSportteryMatchRemarkItem`：`code=0`、`message=OK`、`data` 是保存后的单对象（模块 Q-003），非数组。字段 schema 未列 required/nullable；Q-003 的字段空值结论针对集合元素，不能自动扩展为单对象合同。

| 字段 | 含义及来源 |
|---|---|
| `remarkId` | 备注 ID，int32；源码来自保存实体 |
| `sportId`、`matchId` | 运动项目及竞彩官方比赛 ID，int32/int64 |
| `account` | 记录创建账号，OpenAPI 明示；服务端确定 |
| `remark` | 保存后的文本，源码返回规范化内容 |
| `isCurrentUser` | boolean；源码比较创建账号与当前账号，正常保存自身记录应为 true |
| `createTime`、`updateTime` | date-time 字符串，对应实体审计时间；时区、精度及格式细节未声明 |

业务错误见第 3 节；其他服务异常的状态、code、message 和 data 未在 operation 明确。无成功空数组分支；错误 data 是否为 null 或省略未规定。

## 6. 职责边界与副作用

本接口写用户备注，不修改竞彩来源赛程的官方 `remark` 字段；API-004 负责读取和排序。关闭弹窗、刷新、取消和视觉展示属于页面功能。权限拒绝属于认证/授权边界，不能用源码未登录分支替代网关实际行为。

实体标注 `@Audited`，DDL 存在 `audit_sporttery_match_remark`；[操作日志需求](../../../../MOD-13-操作日志/00-module-requirement-pack.md) 将竞彩赛程备注保存列为日志入口。具体触发和字段由操作日志职责核实，不能仅凭 DDL 或分析报告断言每种失败/重复请求都写日志。日志和审计可能涉及共享记录，后续准备清理需隔离并确认，不应删除其他用户数据。

## 7. 来源差异与待确认问题

用户于 2026-11-02 在 [Q-001](./clarification-questions.md) 明确计数包含首尾空格、按页面用户感知字符计算；测试可按用户感知字符（字素簇）组织预期，不将 UTF-16 代码单元或码点数直接当作同义词。具体分词版本及实现尚未指定。OpenAPI 仍描述先去首尾空白，源码 `strip()` 后用 Java `String.length()`（UTF-16 代码单元）判长，二者与已确认计数口径存在差异；这是静态实现风险，不声称已运行复现。用户答复未单独决定保存和返回文本是否保留首尾空格，仍按 OpenAPI 的去空白描述记录，不推断答复覆盖该部分。

OpenAPI 未形式化必填、枚举、数值范围、错误 HTTP/data 和时间细节；源码是当前实现，不自动补齐合同。未运行接口、认证、数据库或并发验证。

## 8. 测试方案交接

可沿用 RSU-016、FC-003、DC-004 分析当前用户保存、规范化、项目隔离、唯一写入和错误分类；长度以 Q-001 已确认的用户感知字符及包含首尾空格为准。页面输入限制与直接接口调用分别归属相应层次，当前代码偏差需后续验证；框架绑定、权限、审计和运行库行为需各自依据或后续实测，具体造数及清理由后续阶段设计。

分析状态：ready  
测试方案就绪：是，主要业务口径已明确；实现及 OpenAPI 差异需在后续验证中报告。
