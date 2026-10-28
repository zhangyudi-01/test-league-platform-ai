# SQL 资产说明

本参考约束模块级查询 SQL 阶段。SQL 在用例批次之前统一规划、生成并验证；用例阶段只读并引用已分配 SQL-ID。SQL 的业务事实必须来自已物化的模块需求、`DC-*` 和 Context Refs；缺失信息回到 `CIQ-*`。

## 是否需要 SQL

仅为页面查询结果、顶部/详情数据库字段、列表列、聚合数量或需求明确的数据一致性核对规划 `SELECT`。下拉、默认值、按钮、提示、校验顺序、接口调用、轮询、重试、并发、锁、勾选和普通状态流转不因引用 DC 而写 SQL。入库或更新用例用文字描述期望记录，本 Skill 不生成 DML。

需求包含原型图时，先识别原型中的实际页面功能区，并在计划中为每条 SQL 标注 `functional_module`；按功能区组织查询，字段/别名和结果顺序尽量与该区域展示对应，便于逐项比对。无原型图时按需求明确的功能模块组织。不得虚构区域或业务口径；归属无法从需求或可读原型确定时回到需求澄清。相同功能区视图可参数化复用，不按 TP 或底层表机械拆分。

## 目录与注册表

SQL 原文独立存放在当前模块的 `test-cases/sql/`，每个文件使用同名 SQL-ID：

```text
test-cases/sql/
├── sql-manifest.json
├── SQL-TASK-LIST-SELECT.sql
└── validation.json
```

`sql-manifest.json` 是注册表，不是 SQL 原文。最小结构如下：

```json
{
  "schema_version": "tp-test-case-generation/sql-assets-v1",
  "assets": [
    {
      "sql_id": "SQL-TASK-LIST-SELECT",
      "file": "SQL-TASK-LIST-SELECT.sql",
      "statement_type": "SELECT",
      "purpose": "按奖期号查询任务状态",
      "data_closure_refs": ["DC-001"],
      "parameters": {
        "A": {
          "description": "奖期号变量",
          "example": "24011"
        }
      }
    }
  ]
}
```

约束：

- `sql_id` 只能使用 `SQL-*`；`file` 必须严格为 `<sql_id>.sql`。
- 每个 SQL 文件必须登记且每个登记项必须有文件；目录中不允许有未注册的 `.sql` 文件。
- 当前规划流程只允许 `SELECT`，并且必须与文件实际语句一致。旧注册表结构仍可被底层解析，但新模块不得规划 DML。
- `data_closure_refs` 必须列出该 SQL 实际服务的 DC；引用该 SQL 的 TP 必须具备对应 DC 事实。
- 一个 SQL-ID 可以被多个 TP、多个来源用例和多个最终模块用例复用。需要增加过滤条件时维护原 SQL 文件和 manifest，不复制近似 SQL。

SQL 阶段会在 `sql/sql-convergence-report.md` 写出收敛报告。报告把去除注释、SQL 关键字大小写和排版空白后执行体完全相同的资产列为“必须复用/合并”，这类重复会阻断 SQL 阶段，必须在生成用例前收敛 generation plan、manifest 和 SQL 文件。共享查询骨架但 WHERE 或业务表达式不同的资产只列为“建议人工评估参数化”，不会自动合并。字符串/标识符内容保持区分，`CASE`、别名和展示转换差异不单独视为缺陷。

## SQL 写法

每个文件只能有一条 SQL 语句，可以有注释。参数使用大写命名占位符，例如：

```sql
-- :A = 奖期号；用于按奖期号模糊查询
SELECT task_id, draw_no, task_status
FROM task
WHERE draw_no LIKE CONCAT('%', :A, '%');
```

字符串中的 `:A` 不算参数。manifest 声明的参数必须与 SQL 实际使用的参数完全一致；每个参数必须在 SQL 注释中说明用途，并提供可用于 `EXPLAIN` 的 example 值。新规划只允许 `SELECT`，不生成写入、更新或删除语句。

如果同一个查询后来需要“按奖期编号模糊查询”，在既有 SQL 文件的条件位置增加注释和 `LIKE` 条件，并保持 SQL-ID 不变，例如：

```sql
-- :A = 奖期号片段；示例 $A=24011，可匹配 24011、240112
WHERE draw_no LIKE CONCAT('%', :A, '%')
```

用例中的前置条件可以写成：准备奖期号 `$A` 和 `$B`，其中 `$B` 的值包含 `$A`；例如 `$A=24011`、`$B=240112`。正式步骤和预期继续使用 `$A/$B`，不把具体示例值当作固定环境数据。

## 用例引用

数据库用例的 `数据变量` 统一声明虚拟变量。字段描述不限制语言、大小写或命名风格，示例值可写可不写；每条声明只放一个变量：

```text
task_id:$X1（示例：123）；draw_no:$A（示例：24011）；task_status:$B（示例：RUNNING）
```

同一逻辑值在实际使用位置必须保持 `$A` 等同名变量。SQL 参数必须在前置条件或执行步骤的对应 SQL 调用处显式绑定为 `:A=$A`，不含多余空格；查询 SQL 的预期结果不要求再次列出 `$A` 或绑定表达式。

数据库场景只有确实存在多类复杂准备时才分类，例如：

```text
数据状态：<br>
准备前明确记录任务 `$X1` 的奖期号 `$A`、状态 `$B`、关联关系和唯一性要求；示例为奖期号 24011 的任务状态为 RUNNING。<br>
准备方式：<br>
按闭包卡确认的业务流程、Mock 或环境方法准备任务 `$X1`。<br>
查询基准：<br>
执行 `SQL-TASK-LIST-SELECT` / `SQL-TASK-LIST-SELECT.sql`，绑定 `:A=$A`。
```

`SELECT` 必须出现在步骤和预期中。预期必须点名 SQL-ID，但只需简洁写“页面或接口结果与 `SQL-ID` 查询结果一致”；多条查询写“页面或接口结果分别与 `SQL-A`、`SQL-B` 查询结果一致”。不要重复参数绑定、变量值、准备方式或同组取值说明。该表述属于人工功能测试比对；本 Skill 不自动调用接口，也不自动比较接口返回和 SQL 结果。

入库或更新操作在用例预期中描述应落库的表、关联键、字段值/状态和数量，不自动生成 `INSERT`、`UPDATE`、`DELETE`。

## 配置与验证

推荐项目根目录使用专用 `database.toml`，避免把数据库配置和 SFTP/K8s 等其他配置混在 `config.txt` 中：

```toml
[database]
host = "127.0.0.1"
port = 3306
database = "test_db"
user = "tester"
password = "plain-text-for-local-test"
charset = "utf8mb4"
connect_timeout = 10
```

配置发现顺序：显式 `--db-config`，然后从模块目录向上查找 `database.toml`，最后兼容旧 `config.txt` 中的 `服务器地址/端口/数据库/用户名/密码`。`config.txt` 可以保留供其他工具使用，但不再作为推荐数据库配置文件。

SQL 阶段对全部计划 SQL 执行：

1. 静态检查 SQL-ID、文件名、单语句、参数声明/使用、DC 绑定和未注册文件。
2. 连接配置指定的 MySQL，先执行 `SELECT VERSION()`。
3. 对每条 SQL 使用 manifest example 值转换命名参数后执行 `EXPLAIN`。
4. 对连接执行 `rollback()` 和 `close()`。

模块 SQL 阶段写入 `sql/validation.json`。批次和模块最终校验不重复连接数据库，只核对报告中的 registry、SQL 文件 SHA-256 与当前资产一致。报告只记录配置路径和配置文件 SHA-256，不记录密码；SQL manifest、SQL 文件或数据库配置变化后，必须回到 SQL 阶段重新校验。
