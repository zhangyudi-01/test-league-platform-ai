"""接口自动化实现规范审计脚本。

自动检查：
1. 仓库根目录是否遗留临时脚本（如 _*.py）。
2. test_*.py 行数、顶层函数数量、是否存在私有微函数、是否手写重复响应断言或 expected_data 自我断言。
3. test_*.py 是否编写了超过 2 个 CTE 或超过 40 行的巨型单条 SQL（强制分步短 SQL + Python 组装）。
4. 同目录 conftest.py 是否重复定义了多个 data/init 基础数据 Workbook fixture（强制同模块共建共用）。
5. 接口测试用例 .xlsx 的参数 Sheet 是否混入非契约说明列、预期|json 是否为空、处理数据分布是否收敛。
6. data/init 基础数据 .xlsx 各 Sheet 是否符合首列主键、第3行起数据的规范。
"""
import argparse
import ast
import re
import sys
from collections import Counter
from pathlib import Path


def audit_python_file(test_file: Path, max_functions: int = 5, max_lines: int = 160) -> list[str]:
    errors = []
    source = test_file.read_text(encoding='utf-8')
    lines = source.splitlines()
    if len(lines) > max_lines:
        errors.append(
            f'[Python行数超限] {test_file.name} 共 {len(lines)} 行（上限 {max_lines} 行），请检查是否按测试点拆碎了函数或内联了冗余逻辑'
        )

    tree = ast.parse(source, filename=str(test_file))
    funcs = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    if len(funcs) > max_functions:
        errors.append(
            f'[函数数量过多] {test_file.name} 定义了 {len(funcs)} 个顶层函数 {[f.name for f in funcs]}（上限 {max_functions} 个），严禁按测试点拆分处理函数'
        )

    private_funcs = [f.name for f in funcs if f.name.startswith('_')]
    if private_funcs:
        errors.append(
            f'[禁止私有微函数/路由函数] 发现私有函数 {private_funcs}，请内联或合并至标准业务处理函数'
        )

    for func in funcs:
        if func.name.startswith('test_'):
            continue
        func_src = ast.get_source_segment(source, func) or ''
        for banned in ("actual['code']", 'actual["code"]', "actual['message']", 'actual["message"]'):
            if banned in func_src:
                errors.append(
                    f'[禁止重复响应断言] {func.name} 中出现了 {banned}，完整响应比对必须交由 client.test() 完成'
                )
        if 'pytest.skip(' in func_src:
            errors.append(
                f'[禁止 skip 桩代码] {func.name} 中使用了 pytest.skip()，无法构造的场景应与用户确认后从用例表剔除或调整预期'
            )

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            text = node.value.strip()
            if re.search(r'\bSELECT\b', text, re.IGNORECASE) and re.search(r'\bFROM\b', text, re.IGNORECASE):
                sql_lines = [ln for ln in text.splitlines() if ln.strip()]
                cte_count = (
                    len(re.findall(r'\bAS\s*\(', text, re.IGNORECASE))
                    if re.search(r'^\s*WITH\b', text, re.IGNORECASE)
                    else 0
                )
                if cte_count > 2 or len(sql_lines) > 40:
                    errors.append(
                        f'[禁止巨型多CTE SQL] {test_file.name} 存在 {len(sql_lines)} 行、{cte_count} 个 CTE 的单条 SQL（上限 40 行、最多 2 个 CTE），请拆分为 1~3 条单表/双表短 SQL + Python 列表组装'
                    )

    conftest_path = test_file.parent / 'conftest.py'
    if conftest_path.exists():
        cf_source = conftest_path.read_text(encoding='utf-8')
        cf_tree = ast.parse(cf_source, filename=str(conftest_path))
        init_fixtures = []
        for node in cf_tree.body:
            if isinstance(node, ast.FunctionDef):
                seg = ast.get_source_segment(cf_source, node) or ''
                if 'Excel(' in seg and "'init'" in seg:
                    init_fixtures.append(node.name)
                    if re.search(r'^\s*for\s+\w+\s+in\s+(?:rows|reversed\(created\[)', seg, re.M):
                        errors.append(
                            f'[禁止Fixture逐行INSERT/DELETE] {conftest_path.name} 的 {node.name} 存在逐行数据库操作循环，必须改为按表批量 DB_CONN.insert(sheet, rows) 与 DB_CONN.delete(sheet, created[sheet])'
                        )
        if len(init_fixtures) > 1:
            errors.append(
                f'[禁止同模块重复初始化Fixture/Workbook] {conftest_path} 中定义了 {len(init_fixtures)} 个 data/init 初始化 fixture {init_fixtures}，同模块各接口应共用 1 个模块级基础数据 Workbook 与 1 个 fixture（内部按主键子号段与自然键前缀分区）'
            )

    return errors


def audit_workbooks(repo_root: Path, case_xlsx: Path, init_xlsx: Path | None) -> list[str]:
    errors = []
    sys.path.insert(0, str(repo_root))
    from common.data import Excel, api_test_data  # noqa: E402

    cases = api_test_data(case_xlsx)
    if not cases:
        errors.append(f'[用例为空] {case_xlsx.name} 未读取到任何用例')
        return errors

    handlers = Counter(c.get('处理数据') or '' for c in cases)
    if len(handlers) > 4:
        errors.append(
            f'[处理数据函数发散] 共出现 {len(handlers)} 种处理数据表达式 {dict(handlers)}，请按执行生命周期收敛为 1~3 个函数'
        )

    banned_param_keys = {'参数说明', '测试内容', '描述', '场景', '场景Key', '备注'}
    for idx, c in enumerate(cases, start=1):
        expect = c.get('预期')
        if not isinstance(expect, dict) or 'code' not in expect:
            errors.append(
                f'[预期为空或缺少code] 第 {idx} 条用例 ({c.get("测试内容")}) 的预期为 {expect!r}，必须提供非空响应骨架'
            )
        params = c.get('参数') or {}
        polluted = banned_param_keys.intersection(params.keys())
        if polluted:
            errors.append(
                f'[参数Sheet混入非请求列] 第 {idx} 条用例参数中包含非契约字段 {polluted}，请移除参数Sheet中的说明列表头'
            )

    if init_xlsx and init_xlsx.exists():
        xl_init = Excel(init_xlsx)
        for sheet in xl_init.file.ws_names:
            rows = xl_init.get_asdict(sheet, begin=3)
            if not rows:
                errors.append(f'[初始化Sheet为空] {init_xlsx.name} 的 Sheet {sheet} 没有数据行')

    for temp_py in repo_root.glob('_*.py'):
        errors.append(f'[根目录遗留临时脚本] 发现 {temp_py.name}，必须删除')

    return errors


def main():
    parser = argparse.ArgumentParser(description='Audit API test module compliance.')
    parser.add_argument(
        '--repo-root', default='D:/pythonProject/sdd-league-platform/tests/test-league-platform'
    )
    parser.add_argument('--test-file', required=True)
    parser.add_argument('--case-xlsx', required=True)
    parser.add_argument('--init-xlsx', default='')
    parser.add_argument('--max-functions', type=int, default=5)
    parser.add_argument('--max-lines', type=int, default=160)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    test_file = Path(args.test_file).resolve()
    case_xlsx = Path(args.case_xlsx).resolve()
    init_xlsx = Path(args.init_xlsx).resolve() if args.init_xlsx else None

    all_errors = []
    all_errors.extend(audit_python_file(test_file, args.max_functions, args.max_lines))
    all_errors.extend(audit_workbooks(repo_root, case_xlsx, init_xlsx))

    if all_errors:
        print('=== AUDIT FAILED ===')
        for err in all_errors:
            print(' -', err)
        sys.exit(1)
    print('=== AUDIT PASSED ===')


if __name__ == '__main__':
    main()
