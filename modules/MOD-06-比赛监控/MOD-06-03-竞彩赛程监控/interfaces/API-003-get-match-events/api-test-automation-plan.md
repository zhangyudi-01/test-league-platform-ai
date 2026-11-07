# 竞彩比赛事件查询接口自动化实施方案

> API-003：`GET /sporttery/match-monitor/events`；方案范围为 1～22；当前实现回归为 `integration-passed`，详见实施进度。

## 1. 范围与依据

本轮按用户审核通过的 [接口测试方案](./api-test-plan.md) 序号 **1～22** 和本方案设计实现合法参数场景。接口问题 [Q-001](./clarification-questions.md) 已确认参数异常只需返回错误，不固定错误码或文案；本轮对部分参数进行了探索性探测，但尚未新增相应自动化用例，不能将探测结果计入自动化覆盖。

依据：[接口分析](./interface-analysis.md)、[DC-003 事件查询数据闭包](../../preanalysis/data-closures/DC-003-事件查询数据闭包.md)、当前 OpenAPI、事件及竞彩比赛表 DDL、测试工程规范，以及旧比赛监控复用回顾。以已确认需求和表结构为预期依据，不使用旧 `s_event`、开售时间窗口、告警或任务筛选。

## 2. 文件与职责

| 计划文件 | 用途 |
| --- | --- |
| [api-query-oracle.sql](./api-query-oracle.sql) | 本轮范围独立查询预期及只读性快照；SQL 状态 `ready`，对应查询已随自动化在开发环境执行。 |
| `tests/test-league-platform/data/init/竞彩比赛事件查询基础数据.xlsx` | 拟新增专用共享数据 Workbook，保存比赛和事件基线。 |
| `tests/test-league-platform/data/data-bff/接口测试用例_竞彩比赛事件查询.xlsx` | 拟新增 Excel 用例及参数，预期骨架在主 Sheet。 |
| `tests/test-league-platform/testsuites/data-bff/sporttery_match_monitoring/conftest.py` | 拟新增显式 module fixture，初始化和清理共享基线。 |
| `tests/test-league-platform/testsuites/data-bff/sporttery_match_monitoring/test_get_match_events.py` | 拟新增本接口 pytest 入口、业务处理函数与动态预期。 |

以上 `tests/test-league-platform/` 路径相对于外层 `sdd-league-platform` 仓库；现阶段不创建这些文件，不修改既有代码、配置或 Excel。若实施前发现目标路径已有权威文件，应复核后复用而不重复新建。不新增公共 helper、类、额外场景控制列或子级规则文件；SQL 文件用于人工复核，实施时按现有测试风格在测试脚本内使用同口径参数化查询，不依赖运行时读取此文件。

## 3. 独立预期与断言

- 用当前请求的 `sportId` 和竞彩官方 `matchId` 参数化查 `sporttery_match_event.sport_id + source_id`，不关联 `s_match_id`；选择 `event_id`、`create_time`、`event_name`、`reason_desc`，按 `create_time DESC, event_id DESC` 返回全部记录，不分页。空查询结果构造 `data=[]`。每次都以请求实际参数取预期，不使用接口响应反推预期。
- 所有成功用例均验证 HTTP 200、`code=0`、`message=OK`、`data` 为数组；逐项严格比较 `eventId` 的存在性、字符串类型和值，标题、详情及记录数、顺序。除相应业务断言外，SQL 结果必须先核对预设数据画像，例如目标条数、干扰数据确实存在，否则空数据和缺失数据不能误判通过。
- `eventTime` 要求响应是日期时间字符串，解析后比较年月日时分秒；不因序列化格式不同而误报，也不抹去真实时间差。由于框架还会做整包比较，必须先独立断言实际时间的类型和解析结果与 SQL 时间相等，再在该断言通过后对时间字段做等价格式适配，其他字段仍按 SQL 严格比较；不能先照搬响应时间当作预期。数据库连接时区、服务时区和实际序列化必须在实施前核验；当前不假定 UTC 换算或固定后缀。
- 排序以实际数据库字段排序规则为依据；DDL 为 `utf8mb4_bin`，相同时间测试数据选取能够明确区分顺序的短 ASCII 字符串。时间及 ID 双重排序用显式断言验证，不能仅依赖查询本身。
- 第 20 条在请求前后对同一 `(sport_id, source_id)` 完整范围执行 SQL 中的快照查询，比较主键集合及名称、原因标题、详情、创建/更新时间；不限制为预先知道的事件 ID，以发现新增和删除。SQL 不能证明其他表没有副作用，该测试点只断言事件表约定范围。
- 当前 DDL 将 `source_type` 标为竞彩固定 `SPORTTERY`，本地 Repository 额外使用来源过滤；本轮有效基线均填 `SPORTTERY`，独立 SQL 不擅自添加该过滤。非竞彩来源值的语义未确认，本轮不声称验证其过滤行为。
- 本地 Service 当前标题取 `reason_title`，与用户已确认的 `event_name` 不同，实际部署未验证。第 13 条必须令两者不同；如实际接口仍取旧字段，应报告接口与确认口径差异，不修改预期以求通过。

## 4. 数据准备与清理

### 4.1 方式选择

已静态检查 `common/draw.py::create_bd_batch_matchup` 及 `delete_bd_game_draw_data`：前者创建北单奖期、批次和正式赛程，返回标准比赛等 ID；后者清理北单关联及旧 `s_event`，不负责当前竞彩事件和竞彩官方赛程。`common/monitoring_data.py` 的旧异常函数也不是本表造数。它们不足以直接建立本接口闭包，不调用它们制造额外跨表依赖。

选用专用初始化 Workbook：多个用例需要稳定的足球/篮球比赛、精确事件 ID、错序时间、空串及隔离关系，且没有查到对应竞彩事件业务创建/清理函数。为每个独立画像分配不同官方比赛 ID，个别隔离场景按下表设置关联；共享数据只读，不在用例间更改。25 条事件属于单一明确的完整性画像，直接放在对应比赛的事件 Sheet 中，不引入批量生成框架。与每次重造整条业务链或在 fixture 逐字段分支相比，这使数据、关联和所有权可从 Workbook 直接审阅。

### 4.2 Workbook 与 fixture

Workbook 依次保存足球联赛、足球球队、篮球联赛、篮球球队、足球比赛、篮球比赛和事件表的真实字段，Sheet 名分别为 `sporttery_football_league`、`sporttery_football_team`、`sporttery_basketball_league`、`sporttery_basketball_team`、`sporttery_football_match`、`sporttery_basketball_match`、`sporttery_match_event`；清理按相反顺序。每个 Sheet 第一列是该表主键，第二行说明，第三行起为可直接入库的值；比赛通过 `league_id`、`home_team_id`、`away_team_id` 关联专用的联赛和球队。使用 `xlsxwriter` 写入，按项目 `Excel`/`pylightxl` 规则读取。

比赛表按 DDL 准备所需官方 ID，其余列以表约束和测试需要决定；DDL 中两张竞彩比赛表的 `match_id` 为 bigint，事件 `source_id` 为 bigint，`s_match_id` 为可空 int。事件至少提供 `event_id`、`event_type`、`event_name`、`event_level`、合法 JSON `identity_data`、`source_type='SPORTTERY'`、`source_id`、`reason_title`、`reason_desc`、`sport_id` 和确定的创建/更新时间；实际值须符合目标库与项目 Excel 读取方式。旧 DDL 包含必填的 `event_code`，但 2026-11-03 检查的开发库与本地实体均无此列，当前 Workbook 按实际库不再包含该列；在其他环境执行前必须核实表结构，若该列仍为必填则需先适配造数方案。`identity_data` 在 Workbook 中保存合法 JSON 文本并按字符串读取，不用 `|json` 将其转为 Python 字典后直接传给 PyMySQL；日期时间以项目支持的文本形式读回。事件 ID 不超过 11 字符，不能以 Excel 数字破坏前导零或大小写。标题和详情的空串直接保存为空串，不能写成 `null`；普通场景中的 `s_match_id` 可为 SQL NULL。

固定 ID 仅是本次测试基线，不代表真实环境样本：实施时为每个画像分配正整数 ID，既提供足球/篮球同值 ID，也提供超过 `2147483647` 的合法官方 ID；高位 ID 选在 Excel 精确整数范围内并核对读回的 Python int 和 HTTP 参数。第 5 条 A、B 使用不同且在 int 范围内的官方 ID，事件 `source_id=A`、`s_match_id=B`，以故意相同的数值检查两个 ID 域不能混淆；该字段是标准比赛关联快照，不宣称 B 是真实标准比赛 ID。当前 DDL 未声明该字段外键；若实际库有额外约束，应在实施前重新核实并补足合法标准比赛，不能绕过或改写测试预期。

`conftest.py` 计划提供一个显式 `module` fixture：读取所有 Sheet 和行，检查待插入主键及每个目标 `(sport_id, source_id)` 是否已有记录，冲突则停止，不覆盖环境数据；按 Sheet 顺序用现有 `Excel` 和 `DB_CONN` 插入并只登记成功插入的主键，`yield` 所需基线数据，`finally` 按逆序和登记的精确主键删除。初始化中途失败也清理已成功插入记录；不能根据比赛 ID 范围、标题或不受控来源批量删数据。测试入口显式依赖该 fixture，因此只选择一条参数化用例也会创建其所需基线。每次运行串行；固定 ID 被其他进程占用、测试环境无法隔离、写入后无法确认归属或安全清理时停止并报告，不删除冲突记录。

每条用例使用各自的只读画像；第 3、5 条各自的两条 Excel 行使用同一完整画像，但两行都不修改它，任意单行均能独立通过。无需每条用例再次创建共同闭包；每个 generator 只构造当前请求和预期、核对该场景画像及需要的前后快照，不负责删除 fixture 基线。测试函数内实际请求异常和断言失败也由 fixture 负责最终清理；generator 如将来增加单例写入，须在第一次写之前进入 `try/finally`，仅按成功创建的键清理。强制终止进程无法保证 teardown，应在环境核查后由负责人根据本次登记主键处理，不自动扩大清理范围。

## 5. Excel、处理函数与测试点映射

沿用项目 `接口路径`、`竞彩比赛事件查询`、`竞彩比赛事件查询-参数` 三个 Sheet；主 Sheet 保存 `测试内容`、`处理数据`、`请求方式`、`是否登录`、`预期|json` 等项目已有列。参数 Sheet 仅有 `sportId|int`、`matchId|json` 两列：普通用例在 `matchId` 中填写 `[赛事名称, 主队名称, 客队名称]`；涉及对照比赛时在该列表末尾再放一个 `[对照赛事名称, 对照主队名称, 对照客队名称]` 列表。初始化数据与用例使用 `zyd竞彩赛事`、`zyd竞彩球队` 专用名称，由 fixture 创建和清理；处理函数按运动项目、赛事和主客队名称查询比赛 ID，发送请求前将 `matchId` 替换成整数；名称不传给接口。无结果或多结果均使测试失败，不引入测试标题路由或场景 Key；专用名称仍需防范其他进程或环境残留造成同名冲突。共 24 行：第 3、5 条各两行，其余各一行。

处理函数按业务范围、字段画像、排序和只读性划分，并通过 `assert_event_response` 共用 SQL 预期，不使用标题或编号二次分流。Excel 处理表达式不传布尔场景开关或预期数量；各字段边界分别验证确切前提，避免其他字段满足条件时误判。`sporttery_event_data` 仅由测试入口触发初始化和清理；重复请求另复用 `data_bff` 登录会话。下表的每个测试点均复用 DC-003；画像在 Workbook 固定，生成器从实际请求定位，响应经 `data_bff.test` 比较。表中“基线清理”均指第 4 节 fixture 精确清理本次成功创建的主键。

| 测试点 | 数据画像与 Excel 行 | 处理函数与关键独立断言 | 清理 |
| --- | --- | --- | --- |
| 1 | 足球比赛一条事件，1 行 | `assert_single_event`；SQL 及响应均恰好一条，四字段一致 | 基线清理 |
| 2 | 篮球比赛一条事件，1 行 | `assert_single_event`；同 1，验证篮球 | 基线清理 |
| 3 | 足球、篮球官方 ID 相同且事件内容不同，2 行分别请求 | `assert_other_sport_events`；各只返回本运动事件，并确认另一运动干扰事件存在 | 基线清理 |
| 4 | 同运动 A、B 各有不同事件，请求 A，1 行 | `assert_match_isolation`；确认 B 存在且不混入 A | 基线清理 |
| 5 | 官方 A、B；仅 A 有事件，事件 `source_id=A, s_match_id=B`，2 行分别请求 | `assert_linked_match_events`；A 有该事件，B 空数组，明确比较两个数值不同的官方 ID | 基线清理 |
| 6 | 匹配事件 `s_match_id=NULL`，1 行 | `assert_unlinked_event`；确认事件仍返回 | 基线清理 |
| 7 | 官方 ID 大于 32 位有符号上限，1 行 | `assert_large_match_id`；核对请求 ID 不截断 | 基线清理 |
| 8 | 目标 25 条可区分事件及另一比赛干扰事件，1 行 | `assert_all_events`；画像恰好 25，响应完整且不混入干扰 | 基线清理 |
| 9 | 目标无事件、其他比赛有事件，1 行 | `assert_empty_events`；确认干扰存在，目标严格为 `[]` | 基线清理 |
| 10 | `create_time != update_time`，1 行 | `assert_event_time_source`；时间为字符串且秒精度等于创建时间而非更新时间 | 基线清理 |
| 11 | 多日期事件，ID 顺序与创建时间冲突，1 行 | `assert_time_order`；确认画像有冲突并按创建时间倒序 | 基线清理 |
| 12 | 同创建时间、可区分的不同字符串 ID，1 行 | `assert_same_time_order`；核对同时间按 DB 字符排序降序 | 基线清理 |
| 13 | `event_name != reason_title`，1 行 | `assert_event_title_source`；标题等于前者且不等于后者 | 基线清理 |
| 14 | 详情含中文、换行和引号，1 行 | `assert_special_detail`；JSON 解码后全文一致 | 基线清理 |
| 15 | 名称恰为 64 个合法字符，1 行 | `assert_title_limit`；预查长度和响应全文，不截断 | 基线清理 |
| 16 | 详情恰为 2048 个合法字符，1 行 | `assert_detail_limit`；预查长度和响应全文，不截断 | 基线清理 |
| 17 | 两事件标题、详情相同但 ID 和创建时间不同，1 行 | `assert_same_content_events`；保留两条并按时间倒序 | 基线清理 |
| 18 | ID 包含大小写字母及前导零，1 行 | `assert_event_id_format`；`eventId` 必返、为字符串且原值一致 | 基线清理 |
| 19 | 一组不变事件，1 行 | `assert_event_repeat`；同一登录会话连续请求两次，比较两次完整内容及顺序，且与独立 SQL 一致 | 基线清理 |
| 20 | 一组固定事件，1 行 | `assert_event_read_only`；比较请求前后同范围完整事件快照及响应 | 基线清理 |
| 21 | `event_name=''` 且详情非空，1 行 | `assert_empty_title`；断言字段存在且是空串，不为 null | 基线清理 |
| 22 | `reason_desc=''` 且名称非空，1 行 | `assert_empty_detail`；断言字段存在且是空串，不为 null | 基线清理 |

框架实际行为以 `common/api.py` 为准：`test()` 先启动 generator 再登录，`request()` 在 `finally` 中将响应发送回 generator，随后核验 HTTP 与预期；不能假设文档中的步骤顺序。第 19 条保留第一次 `yield` 获得的实际响应，通过同一已登录 `data_bff` 会话对同一路径和真实参数发第二次请求，比较两次完整响应；首次响应由框架核验 HTTP 状态与 SQL 预期，第二次只比较本测试点需要的结果一致性。

## 6. 实施前提与验证

1. 先确认独立测试库、可写及可精确清理权限、登录配置、部署版本、比赛 ID 范围无碰撞；核验实际 DDL、约束、时区以及测试数据是否可能被后台采集任务修改。安全隔离或清理无法确认时，该环境阻塞实施。
2. 审核通过后再创建初始化 Workbook、fixture、用例 Workbook 与脚本；每条用例单独执行，测试写库部分串行。首轮失败按数据、代码、环境或接口差异分类，不能改正确预期迎合实现。
3. 编写后分别验证 Python 语法；`xlsxwriter` 写入、Microsoft Excel 实际打开、`pylightxl/Excel` 读回和 `api_test_data()` 用例读取；`pytest --collect-only`；代表性单用例和完整模块串行运行；代表性用例连续运行两次；检查成功与失败路径数据清理及数据库残留。空串、JSON、ID 前导零、64 位参数和时间类型须单独核对。
4. 以上是验证要求，实际执行证据和未覆盖项见下方实施进度；不能将静态检查或探索请求等同于自动化通过。

### 实施进度

- 首组计划实施测试点 1、2，其他场景的历史状态以当时记录为准，当前状态见最后的实施进度。
- 2026-11-02：用户确认允许在当前环境为本次测试新增并按本次创建的主键清理数据；只读核查当前数据库 `dev_newgoal` 有所需三张表，首组 ID 无冲突。根级自动 fixture 会清理匹配规则的快照表，执行前实际检查除项目排除的两张业务表外无待删除表；不能据此推断其他时间或环境也安全。
- 首组新增 `data/init/竞彩比赛事件查询基础数据.xlsx`、`data/data-bff/接口测试用例_竞彩比赛事件查询.xlsx`、`testsuites/data-bff/sporttery_match_monitoring/conftest.py`、`testsuites/data-bff/sporttery_match_monitoring/test_get_match_events.py`。两条用例分别对应测试点 1、2，通过 `assert_event_scope` 使用本文件所述 SQL 动态预期；显式 fixture 建立基线并按实际插入的主键清理。
- 验证：Python 语法通过；两本 Workbook 用 Microsoft Excel 只读打开、项目 `Excel` 和 `api_test_data()` 读取成功；收集 2 条；首组完整串行执行两次均为 `2 passed`，足球单条另外独立执行及重跑均通过。执行结束只读核查两个官方比赛 ID 和事件 ID 在对应三张表中均无残留。使用模拟 DB 检查初始化中途失败的逆序清理，以及单条清理异常时继续尝试清理其他已创建行；未模拟真实数据库连接中断。
- 首组完成时，两条数据的 `event_name` 与 `reason_title` 不同，目标环境响应已按 `event_name` 通过字段断言；当时测试点 3～22 为 `planned`，接口 Q-001 为 `deferred`，当前状态见后续记录。
- 2026-11-03：事件测试引用的 `sporttery_event_data` 不再出现在当前 `conftest.py`，已追加恢复，保留现有列表 fixture。首次验证时目标库没有旧 Workbook 的 `event_code` 列，导致两条用例在 setup 阶段报错；核查目标库及本地实体后从事件基础 Workbook 移除该过期列。修复后项目读取通过，首组真实执行 `2 passed`，足球单例重跑 `1 passed`，本次比赛及事件记录均无残留；部分 setup 失败与清理错误路径另以模拟验证。
- 2026-11-03：追加测试点 3～22，对应 Excel 现有共 24 条用例；运动隔离及官方/标准 ID 域各拆成两条独立请求。初始化 Workbook 共 25 条足球比赛、2 条篮球比赛、52 条事件，沿用原 fixture 按插入主键逆序清理。完整模块首次执行 `23 passed, 1 failed`：排序画像前置检查误将 DB 返回的字符串当 `datetime`；修正后完整串行执行 `24 passed`，排序用例单独连续执行两次均通过。完整执行后及两次单例重跑结束后检查，测试主键均无残留。Python 语法、Microsoft Excel 打开、项目 Excel 和 `api_test_data` 读取、24 条收集均通过。
- Q-001 按用户最新口径记录为只要求接口报错；部分异常参数的开发环境探测见问题清单，未编入本轮 24 条自动化用例。上述通过结果不代表参数异常已自动化覆盖。
- 2026-11-03：按用户要求将用例参数中的固定比赛 ID 改为联赛和主客队名称，增加对应足球、篮球联赛及球队基础记录，通过 `set_match_query` 查出本次基线比赛 ID；对照比赛也按名称查询，64 位比赛 ID 场景保留独立边界断言。Excel 打开及项目读取、语法检查和 24 条收集通过；完整模块串行执行 `24 passed`，标准比赛 ID 隔离用例单独连续执行两次均通过，7 张基线表的本次主键无残留。
- 2026-11-03：按用户进一步明确的格式，参数 Sheet 改为仅有 `sportId|int`、`matchId|json` 两列，比赛及可选对照比赛名称均写入 `matchId` 列表；请求前解析成实际比赛 ID。Excel 打开、项目读取、语法检查和 24 条收集通过；完整模块串行执行 `24 passed`，带对照比赛的用例单独连续执行两次均通过。
- 2026-11-03：按处理函数规范去掉 Excel 中的布尔开关和数量参数，按上述业务断言调整处理函数；保留两个真实接口参数列与原有场景。Python 语法、Excel 只读打开、项目读取和 24 条收集通过；开发环境完整串行执行 `24 passed`，标准 ID 隔离用例单独连续执行两次均 `1 passed`。运行前核对数据库与快照表范围，运行后七张基线表的本次主键均无残留。
- 2026-11-03：按用户要求取消处理函数传递 `sporttery_event_data`，名称查询改为全表严格唯一。语法、Excel 打开与项目读取、24 条收集通过；开发环境完整串行执行 `9 passed, 15 failed`，失败均为名称对应多场比赛，请求前定位失败，非接口结果失败。测试结束核查七张基础表本次主键无残留。需确认附加的业务定位字段或其他可隔离办法；上次 24 条通过属于修改前结果。
- 2026-11-03：按用户要求将基础数据及用例定位名称改为专用 `zyd竞彩赛事1/2`、`zyd竞彩球队1～29`，保留原比赛、事件关联和两个接口参数列，不新增日期字段；仍由 fixture 按主键清理。两本 Excel 经 Microsoft Excel 与项目读取校验，24 条均可收集；开发环境完整串行执行 `24 passed`，标准比赛 ID 隔离用例独立连续两次各 `1 passed`。每次运行后检查七张基础表的本次主键及专用赛事、球队名称，均无残留。
- 2026-11-03：移除与客户端完整 JSON 比较重复的首次响应条数和事件 ID 类型断言，保留 SQL 数据条数前提、时间等价校验及重复查询和只读性校验。模拟缺失、多余、类型和字段错误等响应，确认框架比对或时间校验能够拒绝；实际开发环境完整串行执行 `24 passed`，多事件及无事件用例连续两轮各 `2 passed`，运行后基线数据无残留。
