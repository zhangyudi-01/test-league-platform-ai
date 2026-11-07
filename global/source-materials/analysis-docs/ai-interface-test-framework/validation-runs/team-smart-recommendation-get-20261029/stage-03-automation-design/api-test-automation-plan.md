# 球队智能推荐查询接口自动化实施方案

## 1. 范围与状态

- Operation：GET /relations/team/recommendations，operationId recommend。
- 对应 stage-02-api-test-plan/api-test-plan.md 现有 67 点；范围为足球、数据源 1/3 推荐方向、source 2 成功空结果及接口不支持值。
- 状态：awaiting-review。SQL 状态：候选字段查询待审核及数据库验证，排序 oracle 阻塞；未执行完整 SQL。自动化点13-14、41分别依赖受控服务时钟和故障注入，当前阻塞。
- 本文件只规划实现，不写测试代码、Workbook 或数据库数据。

## 2. 依据与当前基线

- 预期以唯一接口分析和当前 67 点方案为准。第13轮确认：先筛 A 源 source_season_id 非空，再依据数据库 NOW() 分别取全局过去最近5场和未来最近5场。
- 隔离运行输入快照中的脚本、旧独立 SQL 和旧自动化方案采用全局 Top-10，不能照搬为本轮 oracle；工作区脚本后续已更新，实施前仍须重新核对。新的只读查询已在本目录 api-query-oracle.sql 独立重建。
- 工程沿用 Excel -> api_test_data() -> DataBff.test() -> 业务 generator。最近比赛窗口断言必须重写，不能继续使用 assert_recent_ten_matches。
- 隔离输入快照中的 conftest 声明读取 data/data-bff/init/球队智能推荐查询基础数据.xlsx，当时未提供该文件或相关表 DDL。当前工作区 fixture 已改为读取 data/init/球队智能推荐查询基础数据.xlsx；实际实施仍须核验当前版本、schema 和清理责任。
- 未来真实实施前重新检查目标测试仓库的 Git 状态；本隔离运行不会触碰其文件。

## 3. 未来实现文件清单

| 类型 | 计划路径 | 处理方式 |
|---|---|---|
| pytest 脚本 | testsuites/data-bff/team/test_team_smart_recommendation_get.py | 以现有脚本为基线，重写 5+5 预期并补必要业务 generator；保留单一参数化入口 |
| 接口用例 Workbook | data/data-bff/接口测试用例_球队智能推荐查询.xlsx | 按测试点逐项映射，保留现有用例并按需追加；xlsxwriter 写入 |
| 基础数据 Workbook | data/init/球队智能推荐查询基础数据.xlsx | 当前 fixture 使用的路径；实施前核验版本、数据归属和清理责任 |
| module fixture | testsuites/data-bff/team/conftest.py | 仅通用共享闭包插入、记录主键和逆序精确清理 |
| 独立 SQL | testsuites/data-bff/team/test_dependent_file/球队智能推荐接口查询SQL.sql | 更新至 13 轮规则并与脚本 oracle 对齐 |

以上是未来目标路径；本次只产生隔离目录内的设计材料。

## 4. 独立 oracle 与预期策略

适用。SQL 无序计算候选及 9 个响应字段，不使用被测响应构造预期；顺序必须另按已确认排序口径核验。查询步骤为：

1. 由 team_id/current_data_source 推导 A、B 源。
2. 汇总人工球队关联的所有 A 源足球球队。
3. 只保留 source_season_id 非空的 A 源赛季比赛，计算两源有效时间和 A 球队主客角色。
4. 在同一语句 NOW() 下分别选过去时间 <= NOW() 的倒序前5场和未来时间 > NOW() 的正序前5场，合并后再桥接赛季。
5. 通过 manual_season_id 找 B 源赛季，匹配同秒、同角色比赛并累计候选。
6. 保留所有最高分候选，映射名称与匹配状态，按简称排序。

测试数据避开全局第5/6名有效时间相同的未定义边界。Oracle 依赖 MySQL 8+ 和对应 session time_zone；实际版本、列名和时区均需核验。归档设计 §D2 写明中文 Collator 排序；只读常量探测中，目标库 `gbk_chinese_ci` 与本地 Java `Locale.CHINA` Collator 对 `A/a` 的顺序不同，故已移除 SQL 排序，顺序须另用独立且可移植的 oracle 验证。完整 SQL 仅使用只读 SELECT；当前未执行。文件中的命名绑定变量若嵌入 DB_CONN，须按真实参数协议转换后再只读验证。

## 5. 测试点追踪映射

| 场景组 | 测试点 | 数据闭包与准备 | Workbook 处理函数 | 断言与清理 |
|---|---|---|---|---|
| 数据源方向 | 1-2 | 有效人工球队、两源关系及可区分候选 | assert_source_direction | 核对 sourceType 和目标源；只用本例数据 |
| 请求错误 | 3-7、67 | 缺少/非法参数及不存在的 teamId；另测公共枚举存在但接口不支持的值 4 | assert_documented_error / test_unsupported_recommendation_source | 3-7 核对已明确的 code/message；67 直接请求并仅断言参数错误 code=2，不固定未定义的 HTTP 状态、message/data |
| 空结果 | 8-10 | 无 A 关系、无已匹配赛季、已匹配赛季无比赛 | assert_response_contract | 核对 code=0、data=[]；按主键精确清理本例关系/赛季/比赛 |
| 赛季资格 | 11-12 | source_season_id 为空/非空及不同 relation_status 对照；制造可区分窗口候选 | assert_season_qualification | 核对资格与窗口占位；仅清理自有映射及比赛 |
| 5+5 窗口 | 13-20 | 13-14 固定服务判定时刻并传给 oracle；15-20 构造有足够时间缓冲的过去/未来场数、各侧第6场、跨多 A 队全局竞争、反向 ID 顺序 | assert_selected_match_window | 13-14 无固定时刻能力时保持 blocked；其他场景核对两侧入选集合和可区分响应，动态时间在 try/finally 恢复 |
| 时间解释与占位 | 21-24 | 贝泰 resumetime 优先/回退、纳米 Unix 秒、窗口内无 B 候选且窗口外有独有候选 | assert_effective_match_time / assert_selected_match_window | 核对时间侧别、秒级碰撞、不由窗口外补位；恢复修改字段 |
| 赛季/角色碰撞 | 25-29 | 同秒同人工赛季命中；秒差、赛季差、角色反转对照；不同比赛状态 | assert_season_bridge | 核对命中/不命中和状态不筛选；清理各自赛季/比赛/球队闭包 |
| 计分和最高分 | 30-32 | 同候选多次命中、低分候选、最高分并列候选 | assert_candidate_scoring | 核对 recommendCount 与最高分集合；清理自有闭包 |
| 候选字段/匹配状态 | 33-35、37 | 两源名称样本、已匹配/未匹配候选、同候选重复命中 | assert_team_info_and_sort / assert_candidate_relation_status | 核对名称、9字段、候选唯一性及状态；仅清理本例关系 |
| 排序 | 36 | 非空简称互异的最高分候选 | assert_team_info_and_sort | 核对非空简称正序；空简称和同简称按序号60-62覆盖 |
| 响应与只读幂等 | 38-40 | 完整候选；请求前关系快照；不跨 NOW 边界的重复请求数据 | assert_response_contract / assert_read_only / assert_repeated_result_stable | 核对 schema、请求前后关系不变及重复响应一致 |
| 服务错误契约 | 41 | 隔离环境提供可恢复的故障注入点；不关闭共享服务或数据库制造环境级故障 | assert_documented_error | 核对 code=31 和错误 message；无故障注入能力时该点保持 blocked |
| 关系/源/运动隔离 | 42-45 | 目标源但无 A 源关系；其他人工球队、source_type、sport_id 对照关系 | assert_base_source_team_scope | 用完整响应 oracle 核对不泄漏且仅足球/反向源关系参与；仅清理自有映射 |
| 赛季桥接延伸 | 46-49 | 缺 A 映射、缺 B 源赛季、一个人工赛季多个 B 源赛季、跨源同数值 season_id 对照 | assert_season_bridge | 核对资格、空候选、多赛季均可命中及不得按数值直接跨源命中 |
| B 侧碰撞与分数范围 | 50-55 | B 同秒多赛、A 主/客角色、B 不同比赛状态、删除标记球队、多场 B 命中使分数大于10 | assert_candidate_scoring / assert_season_bridge | 每条符合条件的 B 比赛计数，核对角色与状态过滤规则；清理各例闭包 |
| 候选绑定状态扩展 | 56-58 | 目标候选绑定其他人工球队；相同 ID 其他源/运动关系；最高分混合绑定状态 | assert_candidate_relation_status | 核对目标源+足球范围、manualTeamId 与 status 组合，并断言不返回 checkStatus=2 |
| 最高分排序扩展 | 59-62 | 简称更靠前的低分噪音；NULL/空简称、同简称和多空简称最高分样本 | assert_candidate_scoring / assert_team_info_and_sort | 先排除低分，再验证非空简称正序、空简称末尾、sourceTeamId 次级升序 |
| 桥接与候选细节 | 63-66 | A/B 赛事 ID 不同但映射一致；贝泰 B 源有效时间；贝泰 team_id 多赛事行；最高分候选全已绑定 | assert_season_bridge / assert_effective_match_time / assert_team_info_and_sort / assert_candidate_relation_status | 核对赛事 ID 不参与桥接、COALESCE B 时间、候选按球队折叠、已绑定候选完整返回 |

测试点须能单独执行且不依赖前序用例。序号67因现有 `DataBff.test()` 强制断言 HTTP 200，使用单独的直接请求测试来避免引入未确认的 HTTP 状态；其余场景优先沿用 Workbook 与业务 generator。成功数据场景按独立 SQL 核对候选字段，顺序按已确认排序规则独立核对；错误场景只比较契约明确的字段。不用总路由函数、标题判定、固定 ID 或重复控制列。需要组合断言时由主 generator 用 yield from 复用。

## 6. 数据闭包与清理责任

- 业务闭包涉及 m_team、r_team_data、r_basic_data、两源足球赛季/球队/比赛。真实字段、主键、外键次序须依据缺失的 DDL 和初始化 Workbook 核实。
- 稳定共享基线由 conftest 通用读取、按 Sheet 顺序插入、记录成功主键、yield、逆序按主键清理；不得在 fixture 按用例标题或场景分支。
- 每行测试有专属可定位数据或由其 generator 少量创建差异数据。无环境固定 ID，不依赖其他测试先执行。
- 时间场景只允许更新该用例拥有的比赛；保存原值并在 try/finally 恢复。新增行只按已记录主键删除。失败路径也必须恢复时间和清理数据。
- 只读/幂等请求前后比较相关 r_team_data 快照；造数和清理 DML 不计入接口副作用。
- 在 schema 与数据所有权确认前，不批准宽条件 DELETE、共享行 UPDATE 或模糊清理；数据实现状态 blocked。

## 7. Workbook 与执行方式

- 一个 operation 使用一个现有 pytest 文件和一个对应 Workbook，沿用 Excel 主 Sheet/列结构。用例文件写入必须使用 xlsxwriter。
- Workbook 用例逐点映射；序号67的直接请求测试单独追踪。参数列仅放真实 HTTP 参数，不新增请求外的场景控制列。
- DataBff 公共层处理首次请求和通用响应断言。业务 generator 只做本业务数据准备、独立 oracle 和副作用断言。
- 数据库写入用例串行；pytest 参数化行可独立选择。fixture 可共享稳定基线，但单条用例不能要求前置用例已运行。
- 动态时间场景使用测试库数据库时钟和约定会话时区；读取并恢复原会话时区，时间变更按用例自有比赛恢复。

## 8. 验证门禁与当前状态

1. 只读执行 oracle，核验 MySQL 版本、占位符适配、时区和字符集。
2. Python py_compile；xlsxwriter 写入；Microsoft Excel 打开；pylightxl/ExcelReader 和项目 api_test_data() 回读并核对测试点映射。
3. pytest --collect-only，核对收集数与 Workbook 一致。
4. DB/API 环境明确并获授权后，串行执行单例、动态时间代表例两遍、完整模块；检查自有 ID 清理、时区恢复与 git diff。

本轮没有执行 SQL、pytest、API 请求或 Workbook 写入，状态 not-run，不代表验证通过。

## 9. 实施前阻塞

1. 核验当前球队智能推荐基础数据 Workbook 的版本、归属及清理责任；隔离输入快照原缺失，不将历史缺失直接当作当前工作区状态。
2. 获取 r_team_data、r_basic_data、m_team、beitai_football_match/team、nami_football_match/team 的 schema 和关键约束，确认数据库版本、时区及排序字符集。
3. 确认测试 DB/API 环境、数据所有权与清理权限。未确认前不得在真实测试项目或数据库执行写入型测试。
4. 序号13-14需可控服务时钟；现有 SQL 的 `NOW()` 仅支持常规时间窗口，必须改为与服务相同的受控时刻后才能作为这两点的 oracle。不可仅凭请求前读库时间声称精确边界已验证。

