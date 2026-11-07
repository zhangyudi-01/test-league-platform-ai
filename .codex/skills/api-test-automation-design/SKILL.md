---
name: api-test-automation-design
description: 为已审核的 API 测试方案设计独立 SQL oracle 与极简自动化实施方案。严格遵循“数据区分场景、函数定义执行生命周期、动态预期交由框架比对、静态闭包收敛至初始化 Workbook”原则。只产出设计，不写业务代码或造数。
---

# 接口自动化设计（极简预期驱动架构）

## 1. 核心设计铁律（最高优先级）

在设计任何接口的自动化方案前，必须无条件执行以下五条铁律：

1. **数据区分场景，函数定义执行生命周期（严禁按测试点拆函数）**
   - 不同测试点（如当前用户 vs 其他用户、字段映射、置顶与时间排序、同时间 ID 升序、跨项目/同项目隔离、类型过滤、空结果、特殊字符、未关联标准比赛、非法参数 `code=2`、未登录 `code=1002`）必须通过 **`data/init` 基础数据行 + Excel 请求参数 / 登录账号 / 静态预期** 来区分，**绝不允许为每个测试点或每个业务规则面（Facet）单独设计一个 Python 处理函数**。
   - **查询接口（GET / 只读查询）** 的处理函数默认收敛为 **1～3 个**：
     1. `assert_<api>_get(case_dict)`（覆盖 90% 以上用例）：`yield` 前将参数中的自然键（如比赛编号 `match_no`、球队名称）解析为真实 ID；当 `case_dict['预期'].get('code') == 0` 时，按 **“预期构造分档准则”**（见铁律 4）从数据库查询并拼装 `case_dict['预期']['data']`（及分页 `meta`）；当 `code != 0`（参数错误、未登录等）时保持 Excel 静态错误预期不变；最后执行 `return (yield)` 将控制权交给 `client.test()` 完成请求与全量 JSON 比对。
     2. `assert_<api>_repeat(case_dict, data_bff)`（仅当测试方案包含“重复查询结果一致”时设计）：通过 `actual = yield from assert_<api>_get(case_dict)` 复用首次请求与校验，随后用 `data_bff.session` 发起第二次请求并断言 `response.json() == actual`。
     3. `assert_<api>_read_only(case_dict)`（仅当测试方案包含“查询不修改数据库”时设计）：在 `yield from assert_<api>_get(case_dict)` 前后对目标表拍快照并断言前后一致。
     *(仅当个别测试点必须临时修改数据库状态且放入共享基线会污染其他用例时，才允许增加一个 `try ... yield from assert_<api>_get(case_dict) ... finally` 的写库恢复函数。)*
   - **写接口（POST / PUT / DELETE）** 的处理函数同样按执行生命周期收敛：
     1. `assert_<api>_<action>(case_dict)`：`yield` 前解析自然键并拍下目标表请求前快照；`try: actual = yield` 后根据 `code == 0` 或错误分支核验目标记录持久化、非目标记录零副作用，并回填动态生成的 ID/时间到 `case_dict['预期']['data']`；`finally` 中精确恢复被改动的基线行或删除新增行。
     2. `assert_<api>_repeat(case_dict, data_bff)`：通过 `yield from` 复用主函数并验证幂等性或重复提交行为。

2. **多账号切换、跨运动项目对比一律拆分为标准 Excel 用例行**
   - 账号 A 与账号 B 切换查询同一比赛（如测试点 4），必须在主 Sheet 拆成两条独立用例行（如 `004A`、`004B`），分别在 `用户名`、`密码` 列填写对应账号，共用 `assert_<api>_get(case_dict)`。
   - 同一官方 ID 在足球与篮球下的隔离查询（如测试点 10），必须在参数 Sheet 拆成两条独立用例行（如 `010A` 传 `sportId=1`、`010B` 传 `sportId=2`），共用 `assert_<api>_get(case_dict)`。
   - **严禁**在一个处理函数内部新建第二客户端、二次登录或对不同项目连续发两次请求。

3. **`data/init` 基础数据按【业务模块（子目录）】共建共用，严禁“一接口一 Excel、一接口一重复 Fixture”**
   - **优先复用同模块已有 Workbook 与 Fixture**：当现有 `common/` 业务创建函数无法直接生成所需完整闭包时，先检查目标测试目录 `conftest.py` 与 `data/init/`：
     1. 若同目录（同一业务子模块，如 `season`、`team`、`sporttery_match_monitoring`）已存在采用四段式清理的初始化 Workbook 及 fixture，**必须直接复用并增量扩展该 Workbook**（在已有 Sheet 追加行或按依赖顺序新增 Sheet），**严禁为每个接口单独新建 `data/init/<接口名>基础数据.xlsx` 或在 `conftest.py` 中复制粘贴多个四段式 fixture**。
     2. 仅当同目录尚无四段式初始化 Workbook 时，才新建 **模块级** `data/init/<模块名>基础数据.xlsx` 与 1 个模块共享 fixture（如 `<module>_base_data`）。
   - **同模块多接口数据分区与正交设计**：
     - **只读查询共享公共父表基线**：同模块多个查询接口优先复用公共基础行（如赛事、赛季、球队、主比赛记录），子表/关联表数据同样采用正交组合法直接设计在 `data/init` Workbook 中，**严禁**在 `data/init` 只放空主表而在 Python 用例函数里动态 `INSERT/DELETE` 子表。
     - **专属场景与写接口按【主键子号段 + 自然键前缀】同表分区**：不同接口的特殊边界数据或写接口（POST/PUT/DELETE）目标行，在同一 Sheet 内分配独立负数 ID 子号段与自然键前缀（如 `match_no` 或名称前缀区分），各接口用例仅指定自身号段/前缀的数据，实现同表共存、互不污染、模块级统一清理。

4. **Excel `预期|json` 只存外层骨架，动态预期按复杂度分档构造（严禁巨型多 CTE SQL）**
   - 主 Sheet 的 `预期|json` **只填写外层响应骨架**（**严禁**在 Excel 单元格手填冗长的具体业务记录字段，也**严禁**设为空字典 `{}`）：
     - 成功用例：`{"code": 0, "message": "OK", "data": []}`（对象返回则为 `{}`，带分页则含 `meta` 骨架）
     - 参数/业务错误：`{"code": 2, "message": "<已确认错误文案>", "data": null}`
     - 未登录用例（`是否登录=否`）：`{"code": 1002, "message": "检测到长时间未进行操作，登录失效，请重新登录", "data": null}`
   - **Python 动态填充 `case_dict['预期']['data']` 的两档准则**：
     1. **档位 A（单表/双表直查接口，无复杂跨表算法）**：采用 `test_m_season_get.py` 模式，用 **1 条简单参数化 SQL**（1～2 张表、无复杂嵌套）直接通过字段别名查出驼峰字典列表赋给 `case_dict['预期']['data']`。
     2. **档位 B（复杂业务规则接口：多源合并、多级关联映射、跨源排除过滤、特殊打分/中文排序）**：以**可读性与后期易维护性为第一准则**，采用 `test_nami_team_get.py` / `test_m_season_post.py` 的 **“分步平铺短 SQL 拉取字段 + Python 过滤/组装/排序”** 模式：
        - 用 **1～3 条单表/双表平铺短 SQL**（单条 SQL 最多不超过 2 个 CTE、行数不超过 35 行，避免嵌套 `UNION ALL` 派生表与窗口函数子查询）分别查出候选主表字段与关联/排除数据；
        - 在 Python 中用精简直观的集合/列表推导完成多分支过滤、状态赋值（如 `if_change` 主客对调、JSON 数组拆解、优先级分桶）与排序（如中文排序、多条件优先级），再赋给 `case_dict['预期']['data']`；
        - **严禁**为了把多层业务算法或跨多域聚合强行塞进单条 SQL 而编写包含 3 个以上 CTE 或多层嵌套子查询的巨型 SQL。
   - **严禁**在 `yield` 后手写 `assert actual['code'] == 0`、长度比对或逐项循环比对（统一由 `API.verify_response()` 的 `json_tools.diff` 完成）；**严禁**在 `yield` 前对 `expected_data` 写自我断言。

5. **参数 Sheet 纯净性与标量自然键定位**
   - 接口存在请求参数时，用例 Workbook 必须包含独立的 `接口名-参数` Sheet，且**第一行表头只允许出现真实请求参数列名**（如 `sportId|int`、`matchId`）。**严禁**在参数 Sheet 新增带表头名称的说明列（如 `参数说明`、`测试内容`、`场景Key`），否则 `Excel.get_asdict()` 会将其读入 `case_dict['参数']` 并作为真实查询参数发给接口！
   - 当某个 ID 参数（如 `matchId`、`manualTeamId`）需要指向 `data/init` 中的基础记录时，直接在该参数列填写**标量自然键字符串**（如专用 `match_no` `'RMA004_F01'` 或专用球队名），在非法/边界 ID 用例中直接填写数字（如 `0`、`-1`）。处理函数用 `isinstance(val, str) and not val.lstrip('-').isdigit()` 即可在 8 行内完成解析，**严禁**把简单定位包装成 `{"matchNo": "...", "comparisonMatchNo": "..."}` 等复杂 JSON 结构。

---

## 2. 输入发现与前置核查

1. **定位上游权威依据与闭环承接**：
   - 读取目标 operation 的 `interface-analysis.md`、`clarification-questions.md`（核对已回答 `Q-ID` 的确认结论是否已完整承接）、已审核的 `api-test-plan.md` 及关联的 `DC-*` / `FC-*` / `ADC-*`。
   - **以需求与用户已确认口径为唯一预期基准**：独立 SQL Oracle（`api-query-oracle.sql`）与 `data/init` 基础数据必须严格依据需求、接口契约及 `clarification-questions.md` 已确认结论编写，**严禁照抄开发 Mapper SQL，或为迎合开发代码的冗余限制/错误实现去篡改 SQL Oracle 或弱化测试数据闭包**。
2. **核对源码与数据库表结构（区分“开发缺陷”与“未确认猜测”）**：
   - 读取被测接口的 Controller / Service / Mapper SQL 及相关表 DDL。
   - 若发现后端代码实现与 `api-test-plan.md` 测试点预期不一致，必须先对照 `interface-analysis.md` 与 `clarification-questions.md` 判定性质：
     1. **属于需求明文规定或用户已确认结论（`Q-ID` 已答复）**：判定为**后端实现缺陷（Bug）**。必须在方案中**保留**该测试点的正确 SQL Oracle 与能触发该差异的 `data/init` 数据，并在方案中明确标注“已知后端实现差异，执行时预期 FAIL 以暴露接口缺陷”，**绝不允许为了追求测试通过而将预期或基础数据改成迎合开发代码**。
     2. **属于需求/接口文档未规定、且未经用户确认的猜测分支**（例如无依据假设“子表查询时主表 ID 不存在必返 `code=2`”）：在方案中明确指出源码实际行为并提请用户确认（回填 `clarification-questions.md` 与 `api-test-plan.md` 后决定保留、调整预期或删除无实际业务场景的测试点），**严禁规划基于环境变量或 `pytest.skip` 的桩代码**。
3. **读取测试工程规范、原始标杆实现与同目录已有初始化资产**：
   - 按目标路径逐级读取 `AGENTS.md` 及 `docs/测试工程/代码编写规则.md`。
   - 对照仓库中原始架构标杆实现（如 `testsuites/data-bff/season/test_m_season_get.py`、`testsuites/data-bff/season/test_m_season_post.py`、`testsuites/data-bff/team/test_nami_team_get.py`），禁止参考未经重构的臃肿脚本。
   - 检查目标测试目录的 `conftest.py` 与 `data/init/`，确认是否已存在可复用的模块级初始化 Workbook 与四段式 fixture。

---

## 3. 交付物规范

### 3.1 `api-query-oracle.sql`（仅在需要数据库动态预期或副作用核验时创建）
- 只读、参数化短 SQL（**单条 SQL 最多不超过 2 个 CTE、不超过 35 行**），明确写出：
  - **Q1（自然键转真实 ID 查询）**：如按 `match_no` 或名称查询主键 ID。
  - **Q2（动态预期查询）**：
    - 简单接口（档位 A）：1 条单表/双表直查 SQL 直接通过别名与 `ORDER BY` 产出预期列表；
    - 复杂接口（档位 B）：拆分为 **Q2a（查关联/排除 ID 集合）+ Q2b（查候选主表驼峰字段）** 等分步短 SQL，并附简短注释说明 Python 侧的过滤、状态赋值与排序组装规则。
  - **Q3（数据库快照查询）**：用于只读校验或写接口前后持久化/隔离对比。

### 3.2 `api-test-automation-plan.md`（紧凑、无废话的蓝图）
实施方案必须控制在精简篇幅内，包含以下 5 个标准章节：

1. **范围与文件清单**：
   - 明确 4 类目标文件的复用/增量修改/新建关系：`data/init/<模块名>基础数据.xlsx`（优先复用同模块已有文件并增量扩充）、`conftest.py` 中的模块级四段式 fixture（已有则直接复用，不重复定义）、`data/data-bff/接口测试用例_<接口名>.xlsx`、`testsuites/.../test_<api>.py`。
   - 明确需要向用户确认剔除或调整预期的无真实场景测试点（如有）。
2. **`data/init` 共享基础数据设计（模块共表与正交分区）**：
   - 说明本接口在模块级 Workbook 中复用的已有公共行，以及本次增量追加的主键子号段与自然键前缀（确保与同模块其他接口隔离）。
   - 按 Sheet 顺序列出本次涉及的表名、表头（首行字段与类型、次行中文说明、首列清理主键）及数据行的具体值与设计意图（说明哪几条测试点复用哪一行基础数据）。
   - 明确 `conftest.py` 复用或新增标准 16 行“四段式批量” fixture（通用读取 -> 按表 `DB_CONN.insert(sheet, rows)` 批量插入并登记首列主键列表 -> `yield` -> `finally` 按表逆序 `DB_CONN.delete(sheet, created[sheet])` 批量删除），**严禁逐行循环调用 `DB_CONN.insert` / `DB_CONN.delete`**，无表名分支、无映射字典。
3. **处理函数设计（严格限制函数数量与单条 SQL 复杂度）**：
   - 列出本脚本计划定义的全部函数（查询接口原则上仅 `assert_<api>_get`、`assert_<api>_repeat`、`assert_<api>_read_only` 加上 `test_<api>` 共 4 个函数，总代码量目标控制在 60～110 行以内）。
   - 给出每个函数的职责、参数解析方式、动态预期构造方式（档位 A 单条直查 SQL，或档位 B 分步短 SQL + Python 组装）及 `yield from` 复用关系。
4. **Excel 用例全量映射表**：
   - 一张表列出全部 Excel 用例行：`用例编号/测试内容 | 对应测试点序号 | 是否登录/用户名 | 参数 Sheet 各列值 | 处理数据表达式 | 预期|json 骨架`。
   - 核对确保：`处理数据` 仅出现上述 1～3 个业务函数，且除 `repeat` 传 `(case_dict, data_bff)` 外其余仅传 `(case_dict)`。
5. **验证门禁清单**：
   - `py_compile` 语法检查 -> `xlsxwriter` 生成并经 Excel COM / `pylightxl` / `api_test_data()` 读回 -> `audit_test_module.py` 结构审计 -> `pytest --collect-only` -> 连续两轮串行 `pytest -v` -> 数据库零残留核查。

完成设计后将方案状态标为 `awaiting-review` 并交用户审核，不自动启动实施。
