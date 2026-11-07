---
name: api-test-implementation
description: 按已审核的极简自动化方案一次性实现 data/init 基础数据 Workbook、四段式 fixture、接口用例 Workbook 与 pytest 脚本，并通过内置审计脚本和双轮串行执行完成闭环验证。
---

# 接口自动化实施（极简预期驱动实现）

## 1. 编码硬门禁（违反任一条立即停止并重构）

1. **函数数量、SQL 复杂度与结构门禁**
   - **查询接口脚本** 顶层函数原则上不超过 **4 个**：`assert_<api>_get(case_dict)`、`assert_<api>_repeat(case_dict, data_bff)`（按需）、`assert_<api>_read_only(case_dict)`（按需）、`test_<api>(...)`。代码总行数目标控制在 **60～110 行**。
   - **严禁编写巨型多 CTE 或多层嵌套 SQL（可读性与易维护性优先）**：单条 SQL 字符串最多不超过 **2 个 CTE**、长度不超过 **35 行**。简单查询（1～2 张表）用 1 条直查短 SQL；复杂业务规则（多源合并、多级关联映射、跨源排除、JSON 数组拆解、中文排序等）必须采用 **“1～3 条平铺短 SQL 拉取字段与关联数据 + Python 列表过滤/组装/排序”**（参考 `test_nami_team_get.py`、`test_m_season_post.py`），避免把 `UNION ALL` 派生表、窗口函数与聚合子查询强行塞进单条大 SQL。
   - **严禁**按测试点或业务规则面拆分多个 `assert_*` 函数。
   - **严禁**编写 `_` 开头的私有微函数、参数转发包装函数或场景路由函数。
   - **严禁**在 `yield` 前对 `expected_data` 或数据库基线记录编写自我验证断言（如 `assert len(expected_data) == ...`）。
   - **严禁**在 `yield` 后手写 `assert actual['code'] == 0`、`assert actual['message'] == 'OK'`、字段集合比对或列表顺序比对（完整响应比对统一由 `data_bff.test()` 中的 `API.verify_response` 完成）。

2. **Generator 与 `yield from` 标准写法**
   - 主处理函数 `assert_<api>_get(case_dict)` 模板：
     ```python
     def assert_<api>_get(case_dict: CaseDict):
         """解析自然键参数，并按分档准则从数据库查询拼装动态预期。"""
         params = case_dict['参数']
         # 1. 自然键解析为真实整数 ID（如 match_no -> match_id）
         ...
         # 2. 成功场景构造动态预期：
         #    - 简单接口：1 条短 SQL 直接查出驼峰字典列表
         #    - 复杂接口：1~3 条短 SQL 查出关联 ID 与主表字段 + Python 过滤/赋值/排序
         if case_dict['预期'].get('code') == 0:
             rows = DB_CONN.get_asdict(SHORT_SQL, [...])
             case_dict['预期']['data'] = rows
         return (yield)
     ```
   - 重复查询函数 `assert_<api>_repeat(case_dict, data_bff)` 模板：
     ```python
     def assert_<api>_repeat(case_dict: CaseDict, data_bff: DataBff):
         """验证相同条件下连续两次查询返回一致。"""
         actual = yield from assert_<api>_get(case_dict)
         response = data_bff.session.get(
             data_bff.base_url + case_dict['路径'], params=case_dict['参数'], timeout=30
         )
         assert response.json() == actual, f'重复查询结果不一致: 实际 {response.json()}, 首次 {actual}'
     ```
   - 只读校验函数 `assert_<api>_read_only(case_dict)` 模板：
     ```python
     def assert_<api>_read_only(case_dict: CaseDict):
         """验证查询接口不修改数据库记录。"""
         sql = 'SELECT ... FROM <table_name> WHERE <pk> BETWEEN %s AND %s ORDER BY <pk>'
         before = DB_CONN.get_asdict(sql, [...])
         yield from assert_<api>_get(case_dict)
         assert DB_CONN.get_asdict(sql, [...]) == before, '查询前后数据库记录被修改'
     ```
   - Pytest 入口函数模板：
     ```python
     @pytest.mark.parametrize(
         'case_dict',
         api_test_data(Path(TEST_DATA_DIR, 'data-bff', '接口测试用例_<接口名>.xlsx')),
     )
     def test_<api>(data_bff: DataBff, <base_data_fixture>, case_dict: CaseDict):
         data_bff.test(case_dict, eval(case_dict['处理数据'] or 'None'))
     ```

3. **模块级初始化 Workbook 与四段式 Fixture 门禁（严禁“一接口一 Excel、一接口一重复 Fixture”）**
   - **同模块共建共用**：先检查当前测试文件所在目录的 `conftest.py` 与 `data/init/`。若同目录已有四段式清理的模块级初始化 Workbook 及 fixture，**必须直接复用该 fixture 并在该 Workbook 中按主键子号段与自然键前缀增量扩充数据**；**严禁**为单个接口另建 `data/init/<接口名>基础数据.xlsx` 或在同一个 `conftest.py` 中复制粘贴多个四段式 fixture。
   - `data/init/<模块名>基础数据.xlsx`：Sheet 名即真实表名，Sheet 顺序即插入顺序；第 1 行为 `字段名|类型`，第 2 行为中文说明，第 3 行起为可直接入库的真实值（SQL `NULL` 写作 `'null'`），第 1 列必须为单列清理主键。
   - `conftest.py` 中的模块级 fixture 必须严格采用 **16 行标准四段式批量入库与清理**（按表调用 `DB_CONN.insert(sheet, rows)` 与 `DB_CONN.delete(sheet, created[sheet])`，底层自动走 `executemany` 与 `WHERE pk IN (...)`），**严禁在 fixture 或造数函数中写 `for row in rows: DB_CONN.insert(...)` 或 `for key in ...: DB_CONN.delete(...)` 逐行循环**，禁止添加表级 `if/elif`、字段映射字典、随机 ID 生成或 `sys.exception()` 包装：
     ```python
     @pytest.fixture(scope='package')
     def <module_base_data_fixture>():
         """初始化本模块共享基础数据，并在测试结束后按表逆序批量清理。"""
         excel = Excel(Path(TEST_DATA_DIR, 'init', '<模块名>基础数据.xlsx'))
         base_data = {sheet: excel.get_asdict(sheet, begin=3)
                      for sheet in excel.file.ws_names}
         created = {}
         try:
             for sheet, rows in base_data.items():
                 key = next(iter(rows[0]))
                 created[sheet] = {key: [row[key] for row in rows]}
                 DB_CONN.insert(sheet, rows)
             yield
         finally:
             for sheet in reversed(created):
                 DB_CONN.delete(sheet, created[sheet])
     ```

4. **Excel 工作簿写入与纯净性门禁**
   - 所有 `.xlsx` 文件必须且只能使用 `xlsxwriter` 写入（先写临时文件再 `os.replace`，构建脚本放在对话 `scratch/` 目录，**严禁**在仓库根目录或业务目录遗留 `_*.py` 临时脚本）。
   - `接口名-参数` Sheet 的第 1 行表头**只允许写接口契约中的真实请求参数列**（如 `['sportId|int', 'matchId']`），**严禁**增加 `'参数说明'` 等额外具名表头列（会导致 `Excel.get_asdict` 将其读入 `case_dict['参数']` 发往后端）。
   - 主 Sheet 的 `预期|json` 列在每一行都必须是非空 JSON（包含明确的 `code`、`message`、`data` 骨架），严禁填空对象 `{}`。

---

## 2. 标准实施与验证流程

一次性完成已审核方案的全部实现（不要分 G1～G6 多次停顿等待确认）：

1. **检查工作区**：执行 `git status --short`，保护用户已有改动；读取沿途 `AGENTS.md` 与 `docs/测试工程/代码编写规则.md`。
2. **生成两份 `.xlsx` 工作簿**：在 `scratch/` 编写 `xlsxwriter` 生成脚本，生成 `data/init/<基础数据>.xlsx` 与 `data/data-bff/接口测试用例_<接口名>.xlsx`。
3. **实现 `conftest.py` 与 `test_<api>.py`**：按第 1 节模板编写四段式 fixture 与精简测试脚本。
4. **执行内置结构审计脚本（必过门禁）**：
   运行本 Skill 自带的审计脚本：
   ```powershell
   python D:\pythonProject\sdd-league-platform\tests\test-league-platform-ai\.codex\skills\api-test-implementation\scripts\audit_test_module.py `
     --test-file <test_xxx.py路径> `
     --case-xlsx <接口测试用例_xxx.xlsx路径> `
     --init-xlsx <基础数据_xxx.xlsx路径>
   ```
   若审计脚本报告任何 `FAIL`，必须先修复再进入下一步。
5. **执行 Excel 三重读取与 `pytest` 双轮串行验证**：
   - `python -m py_compile` 检查语法。
   - 通过 Microsoft Excel COM 实际打开两份 `.xlsx`，再通过 `Excel` (`pylightxl`) 和 `api_test_data()` 读回核对行数与参数字典。
   - 执行 `python -m pytest <test_file> --collect-only`。
   - **连续串行执行两遍** `python -m pytest <test_file> -v`（严禁出现为绕过问题而写的 `SKIPPED`）。
   - **失败归类与“以需求为准”硬门禁**：若执行出现 `FAILED`，必须对照需求、`clarification-questions.md` 已确认结论、独立 SQL Oracle、数据库实际记录与后端源码，将其明确归类为：**测试代码问题 / 前置数据问题 / 测试环境问题 / 后端接口缺陷（Bug）**。
     - 属测试代码或前置数据构造问题（偏离已审核方案）的，修复脚本或数据后重跑；
     - **凡属需求或用户已确认口径下的后端接口缺陷（Bug），必须保留正确的 SQL Oracle、断言与触发该缺陷的 `data/init` 数据，让该用例真实暴露 `FAILED` 并在交付报告中明确列出缺陷详情；严禁为了凑齐 `100% PASSED` 而修改正确预期、改写 SQL 迎合开发实现或篡改 `data/init` 数据掩盖 Bug！**
   - 执行后查询数据库目标表，确认测试主键范围内残留行数为 `0`。
6. **落盘复读与交付报告**：重新读取修改后的磁盘文件，检查 `git status --short` 确认无临时文件残留，按 `代码编写规则.md` 第 10.1 节输出五项规范审核结论。
