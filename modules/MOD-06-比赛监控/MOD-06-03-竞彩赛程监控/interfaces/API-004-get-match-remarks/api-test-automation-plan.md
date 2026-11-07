# 竞彩备注查询接口自动化实施方案

> 接口：`GET /sporttery/match-monitor/remarks`（BFF：`GET /data-backend/sporttery/match-monitor/remarks`）  
> API-ID：`API-004`；SQL 与实施方案已审核；执行结果与未完成项见文末实施进度。  
> 本文同时保留设计依据和逐次执行记录，历史状态以记录日期为准。

## 1. 范围与依据

依据 [接口测试方案](./api-test-plan.md) 的 25 个最终测试点、[接口分析](./interface-analysis.md)、[澄清问题](./clarification-questions.md)、[DC-004](../../preanalysis/data-closures/DC-004-备注读写数据闭包.md) 和 [FC-003](../../preanalysis/context-cards/FC-003-竞彩备注生命周期.md)。用户已审核本实施方案、上游测试方案和 SQL；审核不代替认证、数据隔离及清理等运行门禁。

仅覆盖本查询接口；不测试参数缺失、备注保存和页面交互。用户确认已登录时非法参数与比赛不存在断言业务 `code=2`，不严格限定 HTTP 状态、文案或错误 `data`；未登录与参数非法并存时不限定错误优先级。无备注为 `[]`，记录字段无值为 `null`；不能因本地实现差异自行更改预期。

## 2. 文件与工程基线

| 位置 | 设计用途 |
| --- | --- |
| [api-query-oracle.sql](./api-query-oracle.sql) | 已设计的独立只读 SQL：Q1 比赛存在性、Q2 备注来源、Q3 查询前后备注快照。 |
| `tests/test-league-platform/data/init/竞彩备注查询基础数据.xlsx` | 拟新建共享比赛基础数据 Workbook，与接口用例 Workbook 分开。 |
| `tests/test-league-platform/data/data-bff/接口测试用例_查询竞彩比赛备注.xlsx` | 计划新建的接口用例工作簿；实施前再确认不存在同名权威文件。 |
| `tests/test-league-platform/testsuites/data-bff/sporttery_match_monitoring/test_get_sporttery_match_remarks.py` | 拟新建的单接口 pytest 脚本，按业务处理族准备备注和断言。 |
| `tests/test-league-platform/testsuites/data-bff/sporttery_match_monitoring/conftest.py` | 已存在；拟增量添加显式模块级 fixture `sporttery_remark_base_data`，不修改已有列表和事件初始化函数。 |
| `tests/test-league-platform/common/api.py`、`common/data.py` | 现有客户端和数据读取能力，仅作复用依据；本方案不修改。若需改公共框架须先评估影响并单独审核。 |

以上 `tests/test-league-platform/` 路径相对于 `D:/pythonProject/sdd-league-platform/`。新目录及其 `conftest.py`、列表和事件脚本现已存在；三个拟新建文件实施前重新检查是否已有权威文件。只在该目录已有 `conftest.py` 增量添加本接口 fixture，保留其余函数及用户改动，不覆盖或重建。结构预算：新增一个初始化 Workbook、一个用例 Workbook、一个测试脚本，在现有 `conftest.py` 增加一个 fixture；不新增类、通用清理框架、额外控制列、表/角色映射或子级 `AGENTS.md`。初始化 Workbook 的两个表 Sheet 属于必要的数据表，不是接口用例控制 Sheet。

现有 `api_test_data` 按 `接口路径`、接口名及可选的 `接口名-参数`、`接口名-预期` 读取工作簿；普通测试路径为 `DataBff.test` 和业务 generator。`common/draft.py:get_remarks`、`common/matchup_remark.py` 操作旧备注表，不能作为竞彩备注数据或预期。旧 `match_monitoring/conftest.py` 及旧比赛监控列表初始化函数仅作静态背景，不修改、导入或复用；该同级目录的 conftest 不属于新目录的 pytest fixture 作用域。新目录仍遵循 pytest 的父级 conftest 作用域规则。以上为静态核查，不是实际调用或清理通过的证据。

## 3. 独立 SQL 与判据

- Q1 以请求的 `sportId` 和竞彩官方 `matchId` 在对应项目比赛表中查存在性及 `s_match_id`；已登录且 Q1 无行时，不论 Q2 为空或有孤儿记录，都按用户确认口径断言业务 `code=2`。DDL 快照没有删除标志，不能用该查询证明独立的软删除语义。
- Q2 读取目标项目、官方比赛、`remark_type=1` 的原始记录。仅 Q1 存在时，以运行时登录账号与创建账号确定 `isCurrentUser`，当前用户置顶，其余按更新时间、备注 ID 升序，在测试层映射八个字段并逐项比较；先设计可人工核对的不同时间、同时间和不同项目样本，避免把被测排序当 oracle。账号大小写等价规则未确认，样本使用明确不同的身份字符串，不推导额外规则。
- Q2 为零行且 Q1 存在时，成功响应必须为 `data=[]`。DDL 快照中对应的返回字段源列非空；不违反约束、不把空字符串视作 null，也不伪造响应来证明 null。以后仅在确认存在合法无值来源时补充真实核验。
- 比较创建和修改时间的年月日时分秒，不自行指定时区；实施前复核部署 DDL、精度及序列化。Q3 对同一项目和比赛的所有备注类型取快照，按主键比较记录集合及列值，只证明该范围的备注表无变化，不声称覆盖所有表的副作用。
- Q1～Q3 分别以请求参数或本次自建数据返回的 ID 绑定执行；SQL 不承载账号凭据。身份、HTTP、JSON 类型及认证行为由接口断言验证，不由 SQL 证明。

成功场景统一断言 HTTP 200、`code=0`、`message=OK`、`data` 为数组，并验证各点的完整结果、字段、数量及顺序。已登录的非法参数和比赛不存在场景必须从真实业务响应中断言 `code=2`；其他非零 code、仅有 HTTP 4xx/5xx、成功空列表、连接失败、超时或无法解析响应均不能代替 `code=2`，应记录真实状态并区分断言失败与环境/服务异常，不严格匹配 HTTP 状态、文案或错误 `data`。未登录场景需证明请求确实被拒绝，不能将普通 200 页面、空响应或无法识别的响应直接算通过；仅确认进入 operation 的对应业务错误分支时检查 `code=2`，不预设认证层错误码。

## 4. 数据闭包与清理

沿用 DC-004，不复制新的闭包卡。**选择专用初始化 Workbook 创建共享竞彩比赛基础行，单用例 generator 只创建本场景少量备注；不存在比赛的 ID 单独隔离。** 多个测试点反复需要足球、篮球的官方比赛，并要求跨项目同 ID、同项目不同 ID 和未关联标准比赛；共享基础行可直接表达这组稳定关系。备注的账号归属、类型、内容与时间随用例变化，且真实登录账号不应写入 Workbook，因此不预置备注。基础数据共享不等于依赖其他用例：任一单条用例运行时自身触发 fixture，场景备注在用例结束后清理。

候选方法对比：`common/draw.py:create_bd_batch_matchup` 及 `delete_bd_game_draw_data` 操作北单赛程及相关数据，不能产生或精确清理本接口的竞彩比赛；`common/draft.py:get_remarks`、`common/matchup_remark.py` 使用旧 `m_match_remark`，不是竞彩备注造数和预期来源。静态检查未发现满足当前闭包的现成竞彩业务创建及清理函数。`team/conftest.py:team_smart_recommendation_data` 可参考 `Excel` 按 Sheet 读取、记录插入主键及逆序清理的思路，不可把它的具体表、时区设置或实际运行结果当成本接口已验证能力。相比每条用例重复创建两项目比赛，Workbook 基础行加少量备注增量更清楚；相比复用列表接口拟议的七表 Workbook，本接口不需要列表聚合关联，避免创建无关赛事、球队和标准比赛。上述均为静态设计，实际 DDL/约束和可执行性未验证。

### 4.1 基础 Workbook 与入口

拟用 `data/init/竞彩备注查询基础数据.xlsx` 的两个 Sheet，分别命名为 `sporttery_football_match`、`sporttery_basketball_match`，按该顺序插入、逆序清理；首列 `match_id|int` 为真实主键，首行是字段及类型、第二行为说明、第三行起为可入库数据，不放角色列或映射 Sheet。拟准备足球两行 X、Y 和篮球一行 X：X/Y 是关系示意，X 为跨项目相同的官方 ID，Y 与 X 不同。两项目的 X 在真实 `match_no` 字段使用同一专用定位值，足球 Y 使用另一专用定位值；值应符合 `varchar(10)`、在各自项目表内唯一，实施时选定并检查，不把 X/Y 当作入库 ID。正式 Workbook 使用经授权且预先检查的固定整数 ID，同一 X 在两个项目表的值相等；`s_match_id` 按 `null` 表示 SQL NULL，以支持第 17 点。`business_date` 不作为本接口条件，基线按 SQL NULL 准备，避免固定业务日进入其他列表查询；实际库不允许时先重新评估及审核。其余字段只填实际库必填列和稳定必要值，不推导标准比赛、赛事或球队关联。Workbook 不放备注、账号和动态日期；备注排序时间由 generator 按用例直接写入。

拟在 `sporttery_match_monitoring/conftest.py` 中新增显式模块级 fixture `sporttery_remark_base_data`，不导入其他 `conftest.py`，也不修改旧比赛监控或已有竞彩监控列表、事件初始化函数：通过现有 `Excel` 和 `excel.file.ws_names` 读取每个 Sheet（含项目支持的 `null`、`|int` 类型），通用逐行 `DB_CONN.insert`，记录成功插入的首列主键，`yield` 后按 Sheet 逆序、已记录主键精确删除。fixture 不按表名、测试点或角色分支，不在 Python 重复维护表顺序、主键/字段映射，也不把占位符写入初始化 Workbook。目标 pytest 入口以 fixture 形参触发 setup/teardown，处理函数不接收其返回值；所需比赛 ID 按第 5 节请求中的稳定定位值查库。只选单个参数化用例时也会触发初始化。G3/G4 即使不需比赛也可依赖该显式基础 fixture，但第 20/21 点的缺失 ID 必须与所有基础 ID 不同，不能把基础比赛删除后制造缺失。

所有基础 ID 和其项目下的备注范围在首次写入前核验未占用，并保证运行期不被并发采集或其他测试占用；有冲突即停止，不能 `REPLACE`、覆盖或使用未保护的 `MAX+1`。Workbook 的固定 ID 在独占隔离范围内串行复用，上次有残留时停止并调查。数据基线由 fixture 创建和清理；每条测试使用后只清理 generator 创建的备注，不能删除基础比赛或覆盖其他账号的记录；fixture 最终仅清理自己成功插入的比赛。设计不假设本目录初始化已存在；实际读表、插入、外键约束与单条入口均需实施验证。

**DDL 与逐行对账**：快照中两项目比赛主键均为 `match_id bigint`，`s_match_id int`、`match_no varchar(10)`、`business_date date` 可空，创建和更新时间有默认值。`sporttery_match_remark` 的 `remark_id int` 自增主键，`sport_id int`、`remark_type int`、`match_id bigint`、`remark varchar(300)`、`create_account varchar(100)` 和两个时间非空，`update_account varchar(100)` 可空；其唯一键为 `(sport_id, remark_type, match_id, create_account)`。仅在真实库元数据复核一致后执行写入。

| 基线/场景 | 主键及关联键 | 写入与清理责任 |
| --- | --- | --- |
| 足球 X、Y，篮球 X | 三行各自表的 `match_id` 主键；`sportId + match_no` 为本次专用定位条件，非 DDL 唯一约束；两项目 X 的 `match_id` 相等 | 写入前以只读预检核对各项目定位值无冲突并维持隔离；fixture 通用核验主键后插入，只清理成功插入的各表主键。请求前按定位值查询若不唯一则停止。预检不应把表级业务分支塞进 fixture；无法保证预检到请求期间不被占用则阻塞。 |
| 测试点 1～9、12、14～17、24～25 | 按该行真实 `sportId + matchId` 定位 X 或 Y；generator 按场景增量创建 0～3 条备注，记录其自增 `remark_id`；每条记录的四字段唯一键须在写入前检查 | 初始化 Workbook 不含备注，generator 不修改基线，只插入并按登记的备注主键删除自己的数据；13 为零增量，14 仅有非 1 类型。 |
| 测试点 10～11 | 10 的足球 X、篮球 X 使用相同数值 ID、不同 `sport_id`；11 的足球 X、Y 使用不同 ID；各备注唯一键含各自项目、比赛、类型和创建者 | generator 为两个目标各插入所需备注并逐条登记清理；fixture 清三条基础比赛。不能把另一比赛的备注当作目标比赛备注。 |
| 测试点 18～20、22～23 | 18/23 用非法项目，19 用非正 ID；20 使用目标项目受控保留的不存在正数 ID，22 用合法基线比赛 | 不插入备注；20 的比赛与备注缺失均在请求前查证，无法隔离则阻塞；fixture 只清自己的基础行。 |
| 测试点 21 | 使用不同于基线的受控保留 ID，Q1 零行，按 `(sport_id, 1, match_id, create_account)` 创建一条孤儿备注并核对 Q2 | generator 登记、删除自己的备注主键并释放隔离；外键、触发器或并发使其不安全时阻塞。 |

基线无任何 `sporttery_match_remark` 行，故不存在对同一基线备注重复 `INSERT` 的设计。测试点 13/14 的零类型 1 结果、7～9 的时间及 ID 关系均在请求前独立确认；实际可运行前还需核对账号字段的长度、排序时间精度、唯一键及关联表约束。

### 4.2 场景增量、清理与阻塞

- 各 generator 在由请求定位得到的比赛 ID 上只增添本场景所需的 `sporttery_match_remark`，遵守 `(sport_id, remark_type, match_id, create_account)` 唯一约束；A 为实际登录身份，第 4 点 B 也须可授权登录，其他 B/C/D 可使用独立且明确区分的备注创建者角色。按用户确认，本接口主 Sheet 使用已有的“用户名/密码”列，由 `DataBff.test` 调用现有登录方法；本次不增加凭据脱敏逻辑。
- 备注为自增 `remark_id`：`DB_CONN.insert` 返回受影响行数，当前 `DB_CONN.execute` 会保存 `lastrowid`；实施时确认单行插入成功后立即取得并登记本次 `lastrowid`，不可使用最大 ID 或最新记录。首次写入前建立 `try/finally` 保护；异常或无法确定归属时停止并报告，禁止扩大清理条件。第 7～9 点分别准备不同时序和同秒不同 ID，并在请求前核对关系；第 12、14、25 点准备非 1 类型。第 13 点保持目标范围无备注；第 17 点使用基础未关联比赛，不额外创建标准比赛。
- 第 20 点使用被隔离保留的正数 ID，确认目标项目无比赛且无备注；第 21 点在另一安全保留 ID 下仅创建本次孤儿备注，仍保持比赛不存在。必须能排除并发占用；第 21 点需实际外键、触发器和环境策略允许。无法证明隔离或清理时分别阻断，绝不删除共享比赛制造缺失。
- 标准入口交由 `DataBff.test` 推进 generator；因请求或登录异常时框架的发送与最终断言可能掩盖原异常，且无法保证所有中断路径都关闭挂起 generator，入口仅为这一缺口在 `finally` 中关闭尚未完成的 generator，不手动重复推进或请求。创建记录的保护从第一次写入前开始，按已登记 `remark_id` 清理并报告失败。fixture 的 `try/finally` 覆盖部分初始化失败，按成功主键逆序清理；若场景备注清理失败且继续删除基础比赛会破坏外键关系或数据可追溯性，应保留相关基础行并报告残留，不扩大删除范围。若无法同时保留原始错误并保证清理安全，停止受影响组并先审查最小处理方案。清理后分别核查备注和比赛残留。不可控触发器、审计/同步副作用或无法证明数据归属时阻断，不能删除未经确认的审计数据。
- 现有 `DB_CONN` 静态实现使用自动提交；仍需验证服务连接可见性、目标库隔离及清理提交，不能以回滚假设代替真实残留检查。写库用例串行，禁止并发采集或其他测试污染该范围；不修改共享环境中原有记录，不得整表清理。

## 5. 用例与执行映射

表中 `G1`～`G6` 是业务处理族，分别由接口用例 Workbook 的 `处理数据` 直接选择，不按标题或额外场景键二次分发。每行对应一个 Excel 用例，序号 19 为两条分别传 0、负数的用例；共计划 26 行。Q1/Q2/Q3 为同目录 SQL 标签。X/Y 为 fixture 创建并由请求定位的基础比赛，备注由当前 generator 创建和清理；“fixture 清理基础”指每次独立运行的 fixture teardown，多条用例同次串行运行时为模块级 teardown。下表只是实施追踪，不替代上游测试点原文。

| 测试点 | 处理族及独立准备 | 请求与断言 | 清理 |
| --- | --- | --- | --- |
| 1 | G1 基础足球 X、A 的一条类型 1 备注 | A 查询；Q1/Q2、当前用户标识及完整字段 | generator 清备注；fixture 清基础 |
| 2 | G1 基础篮球 X、B 的一条类型 1 备注 | A 查询；Q1/Q2、非当前用户标识 | generator 清备注；fixture 清基础 |
| 3 | G1 基础比赛及创建者 A、更新者 B，创建及更新时间不同 | Q1/Q2；八字段对应，账号取创建者 | generator 清备注；fixture 清基础 |
| 4 | G2 基础比赛上 A、B 各一条 | 两个独立登录上下文分别查询；Q1/Q2 和各自归属、排序 | generator 清备注；fixture 清基础 |
| 5 | G1 基础比赛上仅 B、C 两条 | A 查询；Q1/Q2，两条均非当前用户，无虚构 A 项 | generator 清备注；fixture 清基础 |
| 6 | G1 基础比赛上仅 A 一条 | Q1/Q2，仅该条，不生成其他用户空项 | generator 清备注；fixture 清基础 |
| 7 | G1 基础比赛上 A/B/C 三条，A 更新最晚、B 早于 C | Q1/Q2；人工预期 A、B、C，并核对完整字段 | generator 清备注；fixture 清基础 |
| 8 | G1 基础比赛上 B/C/D 三条，更新时间依次递增 | Q1/Q2；人工预期 B、C、D | generator 清备注；fixture 清基础 |
| 9 | G1 基础比赛上 B/C 两条，同更新时间、不同备注 ID | Q1/Q2；较小 ID 在前 | generator 清备注；fixture 清基础 |
| 10 | G2 足球和篮球基础比赛 X 各一条不同备注 | A 分别请求两个项目；各自 Q1/Q2，仅返回对应项目记录 | generator 清两项目备注；fixture 清基础 |
| 11 | G1 基础足球 X/Y 各一条不同备注 | 查询 X；Q1/Q2，不含 Y | generator 清两比赛备注；fixture 清基础 |
| 12 | G1 基础比赛有类型 1 和非 1 备注各一条 | Q1/Q2，仅类型 1 | generator 清两类备注；fixture 清基础 |
| 13 | G1 基础比赛，无备注增量 | Q1/Q2；严格 `data=[]` | 无场景备注；fixture 清基础 |
| 14 | G1 基础比赛仅有非 1 类型备注 | Q1/Q2；严格 `data=[]` | generator 清备注；fixture 清基础 |
| 15 | G1 基础比赛上 B/C 内容相同、创建者不同 | Q1/Q2；两条均保留，不按内容去重 | generator 清备注；fixture 清基础 |
| 16 | G1 基础比赛的备注含中文、换行及引号 | Q1/Q2；JSON 解码后内容与原记录完全一致 | generator 清备注；fixture 清基础 |
| 17 | G1 使用 `s_match_id` 为 null 的基础比赛及一条备注 | Q1 验证 `s_match_id` 为空；Q2 及返回官方 ID | generator 清备注；fixture 清基础 |
| 18 | G3 登录 A、传非 1/2 项目及正数 ID | 不查 Q1 作为合法比赛；断言业务 `code=2` | 无场景备注；fixture 清基础 |
| 19 | G3 两条独立行，项目有效，ID 分别为 0、负数 | 分别请求并断言业务 `code=2` | 无场景备注；fixture 清基础 |
| 20 | G3 保留不在基础中的不存在正数 ID，且该键无备注 | Q1/Q2 确认缺失；断言业务 `code=2` | 释放本次保留；fixture 清基础 |
| 21 | G3 保留不在基础中的不存在正数 ID，仅创建本次孤儿备注 | Q1 无行、Q2 有行；断言业务 `code=2`，不接受返回孤儿备注 | generator 清孤儿备注、释放保留；fixture 清基础 |
| 22 | G4 使用基础有效比赛、无有效身份客户端 | 验证确被拒绝；确认进入 operation 时检查 `code=2` | 无场景备注；fixture 清基础 |
| 23 | G4 无有效身份，非 1/2 项目及正数 ID | 检查真实错误，不要求认证和参数校验顺序；确认进入 operation 参数校验分支时断言 `code=2`，不预设认证层 code | 无场景备注；fixture 清基础 |
| 24 | G5 基础比赛上 A/B 各一条，身份和记录不变 | A 连续请求两次；均满足成功条件，完整结果、归属及顺序一致，并对照 Q1/Q2 | generator 清备注；fixture 清基础 |
| 25 | G6 基础比赛含类型 1 及非 1 备注 | 请求前后分别执行 Q3，按 ID 比较所有记录及列；接口成功并对照 Q1/Q2 | generator 清各类备注；fixture 清基础 |

### 5.1 请求参数与处理函数

用例使用独立的 `查询竞彩比赛备注-参数` Sheet，按行对应主 Sheet；参数列为 `sportId|int` 和 `matchId|json`，主 Sheet 保留 `预期|json`。项目 `Excel` 的 `json` 类型通过 `json.loads` 解析。真实请求只含 `sportId`、`matchId`。正常比赛的 `matchId` 定位值为 `{"matchNo":"<本次足球X定位值>"}`；第 11 点另含 `comparisonMatchNo`，只用于准备对照，不发往接口。处理函数按项目参数化查询 `WHERE match_no = %s` 并验证唯一性，请求前替换为实际整数 ID。第 10 点核对另一项目的同号比赛；不存在比赛、非法项目及非正 ID 行在 `matchId` 中直接填整数的 JSON 表示。

处理函数优先接收 `case_dict`；其余参数仅在以下位置使用，不传 fixture 返回值、重复比赛 ID 或凭据：

| Excel 直接选择的处理函数 | 额外实参、来源与最终消费者 |
| --- | --- |
| G1 业务函数，均仅传 `case_dict` | 按单条当前用户备注、单条其他用户备注、同内容、当前用户置顶、时间排序、ID 排序、比赛隔离、类型隔离、无备注、仅其他类型分别准备场景。复用的内部 generator 使用业务函数构造的数据完成写入、Q1/Q2 断言和按插入主键清理；场景数据不放入 Excel 函数参数或额外控制列。 |
| `check_remark_identity(case_dict)`，G2 第 4 点 | 第二身份请求使用函数内部独立客户端的 `test(case_dict, generator)` 完成凭据登录和请求；两条备注归属及双身份是该业务族固定语义。 |
| `check_remark_sport(case_dict, data_bff)`，G2 第 10 点 | `data_bff` 来自 pytest fixture，由本函数实际消费以发送第二次请求；从请求中的定位值解析两个项目的 X，分别造备注并请求。 |
| `check_remark_invalid(case_dict)`、`check_remark_orphan(case_dict)`，G3 | 前者使用真实请求参数覆盖 18～20 点；后者为第 21 点按请求参数创建和清理孤儿备注。统一由 `data_bff.test(case_dict, generator)` 完成登录、首次请求及 generator 生命周期。 |
| `check_remark_unauthenticated(case_dict)`，G4 | 无额外数据参数；用例 `是否登录=否`，由 `data_bff.test` 调用现有 logout 后发起首次请求，再由 generator 验证业务响应确被拒绝。 |
| `check_remark_repeat(case_dict, data_bff)`，G5；`check_remark_read_only(case_dict)`，G6 | 前者实际使用 pytest 的 `data_bff` 发送第二次请求；后者无额外实参，按请求键读取 Q3。两者的备注组合为各自业务族固定语义。 |

G1 的备注组合由各业务函数准备，不按测试标题再分派；相同的单备注和其他用户同内容场景分别复用。第 7～9 点的差异时间在各自业务函数中准备，备注 ID 只取本次插入的 `lastrowid`。第 16 点的中文、换行和引号由业务函数构造，经 SQL 参数和响应 JSON 解码后保持一致。相同 Q1/Q2 数据预期及响应核验通过业务函数 `yield from` 共享。第 4、10、24 点的两次请求共享该用例创建的数据，各自独立验证，不拆成依赖其他用例的行。

## 6. 客户端与验证门禁

源码静态追踪：`DataBff` 继承 `API.test`/`request`；`data_bff` 为 session 级共享对象。`test` 在登录前先 `next(generator)`，随后登录或登出，再调用 `request`；`request` 获取并解析响应，在 `finally` 中向 generator 发送 `actual_result`，之后才检查 HTTP 和预期。HTTP 期望默认 200，传空值亦回退 200；非空 `预期` 时用 `json_tools.diff` 比较完整 JSON，但 HTTP 500 跳过该比较；空 `预期` 时只打印非成功 code，不做业务断言。异常路径可能使用旧 `actual_result` 或由 finally 的断言掩盖原错误；这些是静态结果，不是运行通过的证据。

**断言责任与时序**：G1/G2/G5/G6 首次请求沿用 `data_bff.test(case_dict, generator)`，由框架验证 HTTP 200。由于当前契约只规定时间的年月日时分秒而完整 JSON 的时间格式及额外字段尚未确定，先将 `预期` 设为空字典并由公共成功 generator 在 `yield` 后明确断言 `code=0`、`message=OK`、`data` 数组、独立 Q2 推导的记录数量及八字段、归属与排序；时间仅比较已确认精度。不从实际响应回填预期，也不重复断言框架已检查的首次 HTTP 200。若后续确认完整响应形状及时间序列化可从独立源确定，再评估非空完整预期和框架比较，届时移除重复断言并重新审核。G6 另比较 Q3；G5 第二次请求检验完整结果一致，G2 第二次请求检验对应身份或项目结果；按上游方案每次成功请求均检查 HTTP 200 和业务成功，其中第二次直接请求须自行断言。场景数据、真实请求参数替换和 Q1/Q2 预期均在首次 `yield` 前准备，框架自行推进。

**G3/G4 框架责任**：首次请求均由 `data_bff.test(case_dict, generator)` 执行。当前项目框架对未指定 `HTTP_STATUS_CODE` 的请求要求 HTTP 200；响应随后发送给 generator。G3 断言业务 `code=2`；G4 用例设置 `是否登录=否`，框架先调用 `DataBff.logout()`，再发起请求，generator 断言可解析业务响应为非零 code。无效参数和未登录场景的实测均符合该框架路径，因此不再绕过 `test()`。如果后端以后改为非 200 状态，应根据已确认契约调整用例的 `HTTP_STATUS_CODE`，不能改回手工请求/推进 generator。

**认证路径**：全部用例直接由 `@pytest.mark.parametrize(..., api_test_data(...))` 参数化，入口只调用 `data_bff.test(case_dict, eval(case_dict['处理数据'] or 'None'))`。用户名/密码留在 `case_dict` 供框架登录，未登录用例通过 `是否登录=否` 走框架登出分支；双身份第二次请求也调用独立客户端的 `test(case_dict, generator)`。处理函数不校验账号密码配置一致性，也不预检第二账号的绑定状态；登录校验和账号绑定流程交由 `DataBff.test()` / `DataBff.login()`。双身份场景从另一条 Excel 用例记录读取第二组凭据。

实施前门禁：测试库身份、服务版本、数据库权限、ID 保留机制和副作用可控；账号登录及共享绑定状态须在真实执行中验证；确认未登录访问、非 200 的原始响应可安全取得。第 20/21 点的缺失 ID 隔离或孤儿记录不可安全准备时，各自标记阻塞；不能以跳过或成功空列表代替通过。当前本地 GET 未见比赛存在性校验，20/21 可能与暂定预期不一致，部署未验证；真实失败应保留证据并由用户决定口径。

审核通过后实施顺序：先复核目标路径和规则链，再实现数据准备与异常清理、Workbook 及脚本，随后按以下门禁分别记录：

1. 代码静态检查及 `py_compile`；两份 Workbook 均用 `xlsxwriter` 写入，并经 Microsoft Excel 和 `pylightxl/ExcelReader` 读回；接口用例 Workbook 另外经 `api_test_data` 读回核对 26 行及参数类型，初始化 Workbook 核对两个表的字段、固定整数 ID、SQL NULL 与跨项目/同项目关系。
2. `pytest --collect-only` 检查收集；这不等于数据库或接口通过。
3. 在明确授权的测试环境先串行运行代表性单条用例两遍，确认造数、真实响应、SQL 及清理；再完整串行运行本接口目标测试脚本，并复核残留。
4. 分别记录静态、收集、真实 API/DB、清理结果，将失败归类为测试代码、数据、环境或接口问题。无法构造的 null、孤儿数据或认证分支单列未验证/阻塞；不通过修改正确预期或伪造响应消除失败。

### 实施进度

- 2026-11-03：用户确认实施方案、上游测试方案和 SQL 审核通过；本轮默认实施 G1，其余组仍为 `planned`。
- G1：`blocked`。只读检查当前配置连接 `dev_newgoal`，相关三张表存在，两个授权账号均有有效绑定状态和非空绑定标识；未调用登录，不能据此认定账号可登录或有权限。目标三表未发现触发器；当前根级自动 fixture 会删除的快照表数量为零，不能保证之后仍为零。该检查未执行 oracle、写入或删除数据。
- 现有登录失败时可能将密码和令牌写入异常，`API.request` 在失败分支还可能输出请求参数；目前不能证明失败日志与报告安全。按第 6 节门禁，需先形成并审核最小安全认证方案，且运行前重新检查快照清理范围、实际表结构、数据隔离和清理权限。未创建 Workbook 或测试代码，未运行 pytest、接口或数据库写入；G1 没有测试通过证据。
- 用户随后明确要求不新增独立认证路径并先编写。已在新目录的 `test_get_sporttery_match_remarks.py` 编写无数据库副作用的 `assert_remark_response`，按传入的独立查询行核对成功字段、记录数量、排序、归属及时间；尚未接入业务 generator、fixture、Excel 或 pytest 测试入口。Python 编译通过；离线样本中 2 个有效响应被接受、5 个错误响应被拒绝，只是函数级检查，不是框架、数据库或接口测试。
- 对 `dev_newgoal` 的只读结构检查确认三张目标表所用列和备注唯一键存在，目标表未声明外键；候选比赛主键和比赛编号在检查时无冲突，不能保证并发隔离。G1 仍为 `blocked`：认证失败日志泄密风险尚未消除，数据隔离、异常清理及运行门禁也须在执行前落实；未创建 Workbook，未调用接口、登录或执行数据库写入，其他组仍为 `planned`。
- 同日继续实施 G1：已在新目录新增备注查询脚本并在该目录现有 `conftest.py` 中增量添加 `sporttery_remark_base_data`，没有修改或导入旧 `match_monitoring/conftest.py`。新建两份本接口 Workbook，接口用例当前仅含 G1 的 15 条（序号 1、2、3、5～9、11～17），26 行是后续全部场景完成后的目标，尚未生成其余组。场景数据仅含合成角色，不含真实账号或凭据；真实当前账号取现有 `DataBff.login` 默认身份。
- 当前 G1 状态为 `collected`，不是 `integration-passed`：两个 Python 文件编译成功；初始化 Workbook 通过项目读取验证两个 Sheet、三场比赛及 SQL NULL，用例 Workbook 通过 `api_test_data` 读取并验证 15 条与参数结构；两份 Workbook 经 Microsoft Excel 只读打开；pytest `--collect-only` 收集 15 条。内存替身检查了 15 条正常处理流程、备注部分插入失败清理和基础 fixture 清理；替身结果不是数据库清理证据。
- 依据用户要求不新增独立认证路径，继续沿用已有客户端。现有登录失败异常可能暴露凭据，且根级 session fixture 有快照清理副作用；真实运行前仍须解决日志与报告泄露、核对快照清理范围，并确认固定比赛 ID 在完整运行期的独占隔离及清理权限。未进行真实登录、接口调用、写库、连续重跑或残留核查，不能据此判定接口或清理通过。G2～G6 仍为 `planned`。
- 2026-11-03：用户明确要求执行真实接口与数据库测试。运行前只读复核连接 `dev_newgoal`，三张目标表的专用比赛 ID、定位编号及备注范围均无冲突，三表无触发器，数据库账号对该库有写入/清理权限；默认登录身份已启用且已绑定。通过 `--confcutdir=testsuites/data-bff` 限定 pytest fixture 作用域，使根级快照删除 fixture 不运行；使用 `-o addopts=` 和 `-p no:allure_pytest` 禁用默认 Allure 报告，测试输出仅保存在进程内并展示脱敏结果，以免认证失败内容写入报告或终端。未修改公共认证代码或其他接口的初始化函数。
- G1 真实执行结果：代表用例 `case_dict0` 连续单独运行两次，均为 `1 passed`；每次运行后查询两张比赛表和备注表，本次比赛 ID 均无残留。随后串行运行整个 G1 文件，结果为 `15 passed in 6.39s`；结束后按比赛 ID、定位编号及备注范围复核均为零，默认账号的启用/绑定状态与执行前一致。该结果覆盖本轮测试点 1、2、3、5～9、11～17，状态更新为 `integration-passed`；不代表其余 G2～G6、字段 null 或错误分支已经验证。输出未持久化原始报告；以上为脱敏运行记录。
- 2026-11-04：按用户要求继续实施全部场景，已将用例 Workbook 补齐到 26 行，并在同一新目录脚本中增加 G2～G6 处理族：双身份、跨项目、非法参数、未登录、重复查询和只读快照；未修改旧 `match_monitoring` 目录、公共认证代码或既有列表/事件 fixture。第二身份只从 `SPORTTERY_REMARK_SECOND_USER` / `SPORTTERY_REMARK_SECOND_PASSWORD` 运行环境读取，未写入代码、Workbook、日志或报告；不存在比赛场景只在 `SPORTTERY_REMARK_ISOLATED_IDS` 明确声明目标 ID 时才允许造数/请求。
- 2026-11-04：静态和真实验证：Python 编译通过；用例 Workbook 经 `api_test_data` 读取为 26 条，Excel 只读打开，pytest 收集 26 条。跨项目代表用例连续两次真实通过；无效运动项目、非正 ID、未登录、重复查询和只读性代表用例各连续两次真实通过。完整文件串行执行结果为 `23 passed, 3 skipped`，进程退出码 0；跳过项为测试点 4（缺少第二账号安全运行配置）、测试点 20（不存在比赛 ID 未获得运行期独占隔离）和测试点 21（孤儿备注 ID 未获得运行期独占隔离），跳过不计通过。两次完整运行后核查四个候选比赛 ID、两个定位编号和备注范围均为零残留；数据库仍为 `dev_newgoal`。G2、20、21 保持 `blocked`，其余已执行场景为 `integration-passed`；字段 `null` 仍无合法源数据可验证。未使用 Allure 默认报告和根级快照 fixture，未持久化认证失败内容。
- 2026-11-04：按用户后续要求，参考保存备注工作簿拆出独立参数 Sheet，在主 Sheet 配置授权账号与密码，并将测试脚本拆成普通、业务错误、未登录三个 pytest 入口；普通场景继续使用 `data_bff.test`。账号、密码从用例参数中移出，登录复用现有客户端，不向 pytest/Allure 传递。工作簿中的账号密码是明文，属于用户明确要求，文件共享和提交时需注意。两账号切换代表用例连续两次真实通过；最终全量 `24 passed, 2 skipped`。剩余跳过为 20、21 的不存在比赛 ID 隔离问题，不计通过。参数 Sheet、26 条用例与两组身份经项目读取及 Excel 打开验证；运行采用先前的受限 fixture 和关闭 Allure 方式，目标数据清理以最终核查为准。
- 2026-11-04：按用户要求整改 `处理数据`：备注场景记录不再作为 Excel 表达式参数，改由各稳定业务函数准备并复用内部查询/清理 generator；双身份函数去掉未使用的客户端参数，只有跨项目和重复查询保留用于第二次请求的客户端。参数 Sheet 保持不变，凭据列移至登录列之后。Python 编译通过，Workbook 经项目读取及 Excel 只读打开，26 条用例收集成功；排序和双身份代表场景各连续两次通过，全模块串行 `24 passed, 2 skipped`。测试库 `dev_newgoal`，运行后核查候选比赛 ID、定位编号及对应备注范围无残留。20、21 点仍因未取得不存在比赛 ID 的运行期独占隔离而跳过，不计通过。
- 2026-11-04：按用户确认不考虑凭据脱敏，修复普通测试入口为 `data_bff.test(case_dict, eval(case_dict['处理数据'] or 'None'))`，保留 Workbook 凭据供框架内置登录读取；移除 `login_for_case`、登录 monkey patch、临时替换 `success_response` 和入口手动关闭 generator。原始错误响应场景及第二身份请求直接调用已有 `DataBff.login`，不再通过自定义认证 helper。Python 编译通过，26 条用例收集成功；普通授权账号和双账号切换代表场景各连续两次通过；完整串行执行 `24 passed, 2 skipped`。测试库 `dev_newgoal`，执行后候选比赛 ID、定位编号及备注范围均无残留；跳过项仍为 20、21 点的不存在比赛 ID 隔离场景，不计通过。
- 2026-11-04：按用户指出移除 `check_remark_identity` 中对第二账号 `toto_account` 绑定状态的数据库预检；账号登录与绑定流程交由 `DataBff.test()` / `DataBff.login()`，测试代码不做账号密码配置一致性校验。当前脚本只有一个直接使用 `@pytest.mark.parametrize(..., api_test_data(...))` 的 pytest 入口，不再有 `get_test_cases`。Python 编译通过，pytest 收集 26 条；双账号场景连续两次通过，完整模块串行 `24 passed, 2 skipped`。跳过仍为测试点 20/21 缺少运行期独占 ID 隔离；测试库为 `dev_newgoal`，执行后基础比赛主键、定位值和关联备注均无残留。
