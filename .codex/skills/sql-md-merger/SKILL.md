---
name: sql-md-merger
description: "把模块 test-cases-history-20261015/sql/ 下的全部查询 SQL 资产合并为一份 Markdown 汇总文档：每条 SQL 一个中文标题小节，注明来源 .sql 文件与 SQL-ID 等元数据，SQL 正文放入 ```sql``` 代码块逐字保留；文首生成索引表。只做合并与格式转换，不改写 SQL。"
license: MIT
metadata:
  author: project
  version: "1.0"
---

# 测试用例 SQL 合并转 Markdown（sql-md-merger）

当用户要求把某个模块 `test-cases/sql/` 下的 SQL 汇总成一个 `.md` 文档（例如“把所有查询 SQL 放到一个 md 里，每个 SQL 用中文标题，写清来源文件，再用 ```sql``` 代码块放 SQL”）时使用本 skill。

本 skill **只做合并与格式转换**：SQL 正文逐字取自 `.sql` 文件，不改写、不重排、不重新格式化。SQL 资产的生成与维护属于上游 `tp-test-case-generation`，不属于本 skill。

## 1. 输入格式

输入是一个模块的 `test-cases/sql/` 目录（tp-test-case-generation 产出）：

```
sql-manifest.json        ← 必需：SQL 资产登记（sql-assets-v1，含 sql_id/file/statement_type/purpose/data_closure_refs/parameters）
SQL-<ID>.sql             ← SQL 文件，每文件一条语句
validation.json          ← EXPLAIN 验证证据，本 skill 忽略
```

manifest 的 `assets[].purpose` 是中文用途描述，是标题的主要来源。

## 2. 输出格式

默认输出 `<模块>/test-cases/模块测试用例SQL汇总.md`（可用 `-o` 指定其他路径），结构：

```markdown
# <模块名> 测试用例 SQL 汇总

> 共收录 N 条查询 SQL，来源于 `sql/sql-manifest.json`；SQL 正文逐字取自对应 .sql 文件，未做任何改写。

## 索引

| 序号 | SQL 标题 | SQL-ID | 来源文件 | 类型 | 用途 |
| --- | --- | --- | --- | --- | --- |
| 1 | … | `SQL-XXX` | `SQL-XXX.sql` | SELECT | … |

## 1. <中文标题>

- 来源文件：`SQL-XXX.sql`
- SQL-ID：`SQL-XXX`
- 语句类型：SELECT
- 数据闭包：DC-001
- 参数：`:YEAR`（彩票年，示例 2026）；`:PAGE`（页面页大小，示例 100）
- 用途：<manifest purpose 原文>

```sql
<.sql 文件正文逐字嵌入>
```
```

## 3. 中文标题推导规则（核心）

每条 SQL 的标题按以下优先级取值：

1. manifest 中的 `title_cn` 字段（可选的人工覆盖入口，上游不生成但允许补写）；
2. SQL 文件内首个 `-- title: <中文>` 注释行（同样允许人工补写）；
3. **manifest 的 `purpose` 字段**，截到第一个句读（。；;，,）为止，最长 60 字符——这是默认来源，因为 tp-test-case-generation 的 purpose 就是中文用途描述；
4. 兜底：SQL-ID 本身。

标题必须可读且唯一性由序号保证；同一 purpose 截断后重复时允许重名（索引仍可按 SQL-ID 区分）。

## 4. 硬性规则

1. **SQL 正文逐字保留**：不重排、不重缩进、不去注释、不改参数写法；代码块语言标记固定为 `sql`。
2. **只收录 SELECT**：INSERT/UPDATE/DELETE 默认跳过并在文档说明行中列明跳过了哪些（用 `--include-all` 可全量收录）。
3. **禁止覆盖已存在的输出文件**：目标 `.md` 已存在时脚本直接报错退出，必须用 `-o` 另起别名或显式 `--force`。这与 testcase-excel-converter 的不覆盖约定一致。
4. 来源文件名、SQL-ID、类型、闭包、参数、用途均取自 manifest；`.sql` 文件缺失时报错停止，不做静默跳过。
5. 索引表中的用途文本对 `|` 做转义，避免破坏表格。

## 5. 使用方法

```powershell
python -X utf8 -B <skill-dir>\scripts\merge_sql_to_md.py <模块目录>\test-cases\sql
```

参数：

- `-o <path>`：输出路径（默认 `test-cases\模块测试用例SQL汇总.md`）；
- `--module-name <名称>`：标题中的模块名（默认从目录名 `MOD-xx-xx-<中文名>` 推导中文名）；
- `--include-all`：包含非 SELECT 语句；
- `--force`：允许覆盖已存在的输出（默认禁止）。

## 6. 标准工作流

1. 确认输入：`<模块>/test-cases/sql/sql-manifest.json` 存在。
2. 确认输出不存在（存在则换别名，禁止覆盖）。
3. 运行脚本，检查控制台输出的条目数与逐条标题。
4. **读回验证**（必须）：
   - 文档内 ```sql 代码块数量 = 收录条目数；
   - 抽查 2–3 条：代码块内容与源 `.sql` 文件逐字节一致；
   - 每个小节都有“来源文件”行且指向真实存在的 `.sql`；
   - 标题均为中文（无 title_cn/-- title:/purpose 时才会出现 SQL-ID 兜底，需人工确认）；
   - manifest 中的 SELECT 资产无一遗漏。
5. 向用户报告：模块名、输出文件、收录/跳过条数、索引摘要。

## 7. 已知限制

- 标题自动推导依赖 manifest `purpose` 的中文质量；purpose 缺失或为英文时落到 SQL-ID 兜底，此时应人工在 manifest 补 `title_cn` 或在 .sql 头部补 `-- title:` 后重跑。
- 不解析 SQL 语法，不做 EXPLAIN，不连数据库——那属于上游 skill 的职责。
- `validation.json` 被忽略；如需把验证状态写进汇总，需扩展 manifest 读取（当前有意不做）。

## 8. 支撑文件

- `scripts/merge_sql_to_md.py`：转换脚本（唯一可执行产物）。
- `tests/`：自检样例（小型 manifest + sql 文件 + 期望输出），改脚本后必须重新运行比对。
