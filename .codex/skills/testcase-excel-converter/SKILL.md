---
name: testcase-excel-converter
description: "将模块测试用例 Markdown（module-test-cases-history-20261015.md，由测试点收敛阶段产出）转换为团队标准格式的 Excel 工作簿；自动把 <br> 和内联 1.2.3. 编号转成单元格内真实换行，并清理 HTML 标签与 Markdown 反引号。只做格式转换，不生成、不修改用例内容。"
license: MIT
metadata:
  author: project
  version: "2.0"
---

# 测试用例 Markdown 转 Excel（testcase-excel-converter）

当用户要求把 `module-test-cases.md`（或同结构的模块测试用例 Markdown）转换为 Excel、导出正式用例表，或抱怨 Excel 里出现 `<br>`、编号不换行时使用本 skill。

本 skill **只做格式转换**：用例内容（序号、步骤、预期）以输入 Markdown 为准，逐字保留，不做增删改。生成用例本身属于上游 `tp-test-case-generation` 等流程，不属于本 skill。

## 1. 输入格式

输入是测试点收敛阶段产出的 `module-test-cases.md`，结构：

```markdown
# <模块名>需求前置分析 - 模块测试用例

## 生成元数据            ← 可选，两列键值表
## 模块用例追溯索引       ← 可选
## 标准测试用例           ← 必须，12 列标准表
## 模块数据闭包执行计划    ← 可选
## 覆盖矩阵 / SQL资产 ...  ← 其他辅助表
```

识别规则：**每个 `##` 小节中的表变成一个同名 sheet**。包含 `测试项/测试点/执行步骤/预期结果` 四列的表被识别为“标准测试用例表”，套用正式用例样式；其余表按普通辅助表输出（首行表头 + 数据）。

## 2. 输出格式（对齐 tests/sample-testcases.xlsx）

- `首页` sheet：标题 + 各 sheet 名称与行数索引。
- 标准测试用例 sheet：
  - 第 1 行：`时间：xxxx-xx-xx  姓名：xxx`（合并 A1:H1）
  - 第 2 行：`执行开始时间`（合并 A2:G2）
  - 第 3 行：表头（蓝底加粗，冻结 A4，自动筛选）
  - 第 4 行起：数据，全表细边框、顶端对齐、自动换行
- 辅助 sheet：第 1 行表头（同样式），第 2 行起数据，冻结 A2。
- sheet 名超过 31 字符或含 `\/ * ? : [ ]` 时自动清洗截断；重名自动加 `-2` 后缀。

## 3. 单元格清洗规则（核心）

转换时对每个单元格执行：

1. **`<br>`、`<br/>`、`<br />` → 真实换行符**，Excel 内不再出现 `<br>` 字面量。
2. **内联编号拆行**：`1.xxx2.xxx3.xxx`（写在一行没有分隔符的编号）拆成每条一行。
   - 小数保护：`1.5`、`0.5`、`$P=1.5` 不拆（数字后紧跟数字不是编号）。
   - 版本号保护：`迭代2.3`、`版本1.2` 不拆（编号必须位于行首或自然边界 `。；：，` 等之后）。
   - 仅命中 1 处编号不拆（视为正文而非列表），≥2 处才判定为编号列表。
   - 编号限 1–2 位数字（≤99 步）。
3. **去掉 HTML 标签**（如 `<div>`）与 **Markdown 反引号** `` ` ``。
4. `&nbsp;` → 空格；3 个以上连续空行压缩为一个空行；去除首尾空白。

清洗只作用于 `前置条件`、`执行步骤`、`预期结果` 三列的编号拆分；去标签/去反引号作用于所有单元格。

## 4. 使用方法

优先使用 skill 目录变量，保证从任意目录可运行：

```bash
python "${CLAUDE_SKILL_DIR}/scripts/convert_md_to_excel.py" <module-test-cases-history-20261015.md> <output.xlsx> --title "<工作簿标题>"
```

没有 `CLAUDE_SKILL_DIR` 时，从本 skill 目录相对路径运行：

```bash
python .agents/skills/testcase-excel-converter/scripts/convert_md_to_excel.py \
  "<模块目录>/test-cases/module-test-cases.md" \
  "<模块目录>/test-cases/final/<模块名>需求前置分析-测试用例.xlsx" \
  --title "<模块名>需求前置分析"
```

`--title` 缺省取输入文件名；输出目录不存在会自动创建。

## 5. 标准工作流

1. 确认输入路径：`<模块目录>/test-cases/module-test-cases.md`。
2. 确认输出路径：`<模块目录>/test-cases/final/<模块名>需求前置分析-测试用例.xlsx`（与输入同名的 `.xlsx`）。
3. 运行转换脚本，检查控制台输出的各 sheet 行数。
4. 读回验证（见第 6 节），通过后向用户报告。
5. 若目标 xlsx 被占用（Excel 打开中，`PermissionError`），先输出到 `-new.xlsx` 并提示用户关闭原文件后替换。

## 6. 转换后必须验证

用 openpyxl 读回输出文件，检查：

- sheet 齐全：`首页` + 各 `##` 小节 sheet；标准测试用例 sheet 行数 = md 表数据行数 + 3。
- **无 `<br` 字面量残留**（全表扫描）。
- **无 HTML 标签、无反引号残留**。
- 抽查 2–3 行：`前置条件/执行步骤/预期结果` 中 `1.` `2.` `3.` 各占一行（`value` 含 `\n`）。
- 含小数/版本号的单元格（如 `1.5`、`迭代2.3`）未被错误拆行。
- 首行/表头样式：`时间：xxxx-xx-xx  姓名：xxx`、`执行开始时间`、蓝底表头、冻结窗格。

验证脚本骨架：

```python
from openpyxl import load_workbook
wb = load_workbook(out_path)
ws = wb["标准测试用例"]
assert ws.max_row == expected_rows + 3
for row in ws.iter_rows(min_row=4):
    for c in row:
        v = str(c.value or "")
        assert "<br" not in v.lower() and "`" not in v
```

## 7. 已知限制

- 单元格内以 `数据状态：…准备动作：…准备校验：…` 连写的段落（无数字编号）不拆行，保持原文。
- 只有 1 处 `N.` 的文本不拆行（防止把正文当列表）。
- `<br>` 拆行后若原本就有显式编号（`1. xxx<br>2. xxx`），不会重复编号，只保留原文编号。
- 转换不校验用例内容质量；内容问题应在上游生成流程解决。
- 目标文件被 Excel 占用时写入失败，改写 `-new.xlsx`（见第 5 节第 5 步）。

## 8. 支撑文件

- `scripts/convert_md_to_excel.py`：转换脚本（唯一可执行产物）。
- `references/excel-format-spec.md`：输出 Excel 的精确格式规格（行列、样式、列宽），修改输出样式前必读。
- `tests/sample-testcases.md`：覆盖内联编号、`<br>`、小数保护、反引号、辅助表的自检样例。
- `tests/sample-testcases.xlsx`：由自检样例生成的标准输出基准，改脚本后必须重新生成并比对。
