# TP 测试用例生成 Skill 使用手册

## 1. 新流程

本 Skill 不再为每个 TP 建一个生成会话，也不再在写用例时临时造 SQL。流程固定为：

```text
初始化与就绪门禁
  → 模块生成计划
  → 必要查询 SQL 统一生成/EXPLAIN
  → 简单 TP 批量生成、复杂 TP 独立生成
  → 确定性汇总与校验
```

`test-cases/generation-state.json` 是唯一恢复依据。Runner 不读取历史日志决定下一阶段。默认 `module-session` 建立一个模块基础会话；规划、SQL 和每个批次从它独立 fork，批次之间不继承工具历史。不主动依赖自动 compaction。

基础会话完整加载 Skill 及输出、worker、SQL 三份契约。中断续跑时，符合指纹约束的基础会话可跨 Runner 进程复用；复用的只是共同规则上下文，不是上一个批次的会话。

## 2. 开始条件

- 模块前置分析和最终测试点已通过上游校验。
- `test-points/test-case-readiness.md` 的模块及全部 TP 状态均为 `ready`。
- `test-cases/execution-context.md` 无 `pending`。
- 需要 SQL 时有可用数据库连接配置；推荐项目根目录 `database.toml`，兼容 `config.txt`。

## 3. 自动 Runner

```powershell
$SkillDir = "D:\pythonProject\test-supervisor-pc\.codex\skills\tp-test-case-generation"
$ModuleDir = "D:\path\to\module"

python -X utf8 -B "$SkillDir/scripts/run_generation.py" "$ModuleDir"
```

常用参数：

| 参数 | 作用 |
|---|---|
| `--case-output-dir <dir>` | 使用独立输出目录。 |
| `--db-config <file>` | SQL `EXPLAIN` 使用的数据库配置。 |
| `--session-mode module-session\|isolated` | 默认基础会话加独立阶段 fork；或各阶段新会话。 |
| `--max-batch-turns <N>` | 本次最多执行 N 个用例批次。 |
| `--max-tp-turns <N>` | `--max-batch-turns` 的旧兼容别名。 |
| `--reasoning-effort <level>` | 默认 `medium`。 |
| `--max-transient-retries <N>` | 瞬时供应商/网络错误重试次数。 |

Runner 阶段：

1. `prepare_generation_plan.py` 物化整个模块的规划输入。
2. AI 填写 `generation-plan.json`，确定复杂度、SQL需要和批次；校验后写入状态。
3. 有 SQL 时，`prepare_sql_generation.py` 物化 SQL 输入，AI 一次生成所有计划 SELECT，`validate_planned_sql.py` 校验注册表并执行 `EXPLAIN`。
4. `prepare_next_batch.py` 准备唯一下一批。简单/查询展示批次最多 10 个 TP，复杂批次恰好一个 TP。
5. AI 先读取实际 OUTPUT 模板，再填写批内全部 `by-tp/*.md`，`validate_batch_test_cases.py` 全部通过后原子推进批次；这里只核对 SQL 阶段报告和资产指纹，不重复 `EXPLAIN`。格式、编号、变量及已有输入引用填写错误允许在同一 worker turn 内最多 2 轮修正重验，含首次共最多 3 次；缺业务事实、来源漂移或 SQL资产/报告不一致立即阻断。此上限由 worker 契约约束，Runner 未新增强制校验计数器。
6. 全部批次完成后，`prepare_finalization.py` 确定性生成模块用例和覆盖矩阵，`validate_module_test_cases.py` 校验；不再调用 AI 归并。

## 4. 手工执行

数据变量名以大写字母开头，后续可含大写字母、数字及下划线；SQL 参数必须有同名变量，例如 `:REPORT_YEAR=$REPORT_YEAR`。

初始化：

```powershell
python -X utf8 -B "$SkillDir/scripts/init_generation.py" "$ModuleDir"
```

模块计划：

```powershell
python -X utf8 -B "$SkillDir/scripts/prepare_generation_plan.py" "$ModuleDir"
# 使用 apply_patch 填写 test-cases/generation-plan.json，并把 status 改为 validated
python -X utf8 -B "$SkillDir/scripts/validate_generation_plan.py" "$ModuleDir"
```

SQL：

```powershell
python -X utf8 -B "$SkillDir/scripts/prepare_sql_generation.py" "$ModuleDir"
# 若 SQL_COUNT>0，按输入统一填写 sql/*.sql 和 sql-manifest.json
python -X utf8 -B "$SkillDir/scripts/validate_planned_sql.py" "$ModuleDir" --db-config database.toml
```

测试用例批次：

```powershell
python -X utf8 -B "$SkillDir/scripts/prepare_next_batch.py" "$ModuleDir"
# 按 BATCH_INPUT 填写列出的全部 by-tp 文件
python -X utf8 -B "$SkillDir/scripts/validate_batch_test_cases.py" "$ModuleDir" "BATCH-001" --db-config database.toml
```

重复准备和校验批次，直到 `STATUS=all-batches-validated`。最后：

```powershell
python -X utf8 -B "$SkillDir/scripts/prepare_finalization.py" "$ModuleDir"
python -X utf8 -B "$SkillDir/scripts/validate_module_test_cases.py" "$ModuleDir" --db-config database.toml
```

## 5. generation-plan.json

核心结构：

```json
{
  "schema_version": "tp-test-case-generation/plan-v2",
  "module_name": "模块名",
  "source_sha256": "由 planning-input 提供",
  "status": "validated",
  "sql_assets": [
    {
      "sql_id": "SQL-TASK-LIST",
      "statement_type": "SELECT",
      "purpose_type": "page-list-column",
      "functional_module": "任务列表",
      "purpose": "查询任务列表展示字段",
      "rationale": "用于核对页面列表各列与数据库记录",
      "tp_refs": ["TP-030", "TP-031"],
      "data_closure_refs": ["DC-001"]
    }
  ],
  "batches": [
    {
      "batch_id": "BATCH-001",
      "mode": "simple",
      "tp_ids": ["TP-001", "TP-002"],
      "sql_refs": [],
      "rationale": "同一窗口的简单展示规则"
    }
  ]
}
```

复杂度和 SQL 必要性必须分别判断。简单 TP 也可能需要 SQL（例如列表列核对），复杂 TP 也可能完全不需要 SQL（例如并发锁或轮询重试）。需求含原型图时按原型实际功能区组织 SQL，并让字段/别名和结果顺序便于对照；无原型时按需求功能模块组织。每项 SQL 必须填写 `functional_module`，不可按 TP 或底层表机械拆分。

## 6. 用例质量要求

- 对每个 TP 单独判断需要几条用例，不预设 `1 TP = 1 TC`。只有独立业务风险、不可合并前置或操作、独立可判断预期、独立回归价值四项同时成立时才拆分；否则合并可一起执行和判定的验证。多条用例必须在每条追溯说明中给出四项具体依据。
- 简单前置填 `无` 或一句关键条件；多类复杂准备才分类。
- 步骤和预期从 `1.` 连续编号、逐项换行、数量一致并一一对应。
- 不重复入口、相邻 TP 或其他模块已经覆盖的步骤和预期。
- 正文禁止“当前 TP”“来源场景”“场景矩阵”“数据闭包执行计划”“核心操作”等占位话术。
- SQL 只用于页面查询、展示字段、列表、聚合或明确数据库一致性。查询预期简洁写与具体 SQL-ID 查询结果一致。
- 入库/更新预期说明目标记录内容，不生成 DML。
- 固定章节、表头、列数和分隔行不改；必填单元格不留空，不适用填 `无`，三列测试结果填 `未执行`。多项前置、步骤和预期用 `<br>` 分行；变量声明使用非空字段描述加一个 `$变量`，多声明以分号分隔。
- TP、输入哈希及生成结果是文档元数据，`validated` 声明不代表校验已通过；状态只能由校验脚本推进。

## 7. 状态和恢复

状态分三层：

- `planning.status`: `pending | prepared | validated`
- `sql_planning.status`: `pending | prepared | validated`
- `batches[].status`: `pending | prepared | validated`

TP 仍保存 `pending | prepared | validated` 及输入/输出哈希，用于追溯。批次校验先验证全部输出，只有全部通过才一起写为 `validated`。

旧 `tp-test-case-generation/v2` 状态，以及早期虽为 v3 但缺少 `planning/sql_planning/batches` 的状态，只用于识别历史工作区，不能进入旧逐 TP Runner。切换新架构时人工确认影响后执行 `init_generation.py --refresh`；新架构 v3 状态中的未知兼容字段会保留并忽略，不参与调度。

中断后重跑同一命令即可。上游、readiness 或执行上下文变化时，确认后执行：

```powershell
python -X utf8 -B "$SkillDir/scripts/init_generation.py" "$ModuleDir" --refresh
```

旧生成物会进入 `test-cases/history/`。Runner 日志不参与恢复判断。

### 基础会话复用与失败恢复

- `foundation_session` 是 v3 状态中的可选恢复字段（版本、基础会话 ID、SHA-256 指纹、创建时间）。旧状态没有它时正常新建；初始化在来源不变时保留此字段及未知兼容字段，`--refresh` 时清除。
- 指纹绑定来源哈希、模块/输出/工作目录、manifest/preanalysis 路径、Skill 运行规则、适用的本地指令与配置、选定 CLI 身份、model/profile/sandbox/reasoning 及相关 provider 环境值。只保存最终摘要，不保存配置、密钥或环境变量原值。
- 只有记录有效且指纹完全一致才复用；否则新建基础会话。会话 ID 不存在的明确错误可在状态未改变时触发一次重建再 fork；泛化 stream/网络错误不能触发重建。
- 明确余额/额度不足、账户并发窗口已满或模型要求升级 Codex 时立即结束 Runner 自动重试；普通 502/429 等仍按有限次数退避重试。以上不改变 CLI 自身的内部重试机制。
- `isolated` 忽略基础会话记录；全部阶段已完成时不再启动 AI。基础会话不得改模块状态，批次不得污染基础会话记录或兄弟批次。

本次修复不调整默认模型、推理强度、批次规划或并行度。回归测试验证的是调度和恢复行为，不代表已经测得真实 AI 生成耗时下降。

## 8. 输出目录

默认输出为模块的 `test-cases/`，模板使用 `tp-test-cases.md.tmpl` 和 `module-test-cases.md.tmpl`，最终文件固定为 `module-test-cases.md`。带日期的历史归档不作为默认输出；恢复已有独立目录时继续传入原 `--case-output-dir`，不需刷新已验证的计划和 SQL。

| 路径 | 用途 |
|---|---|
| `generation-state.json` | 唯一调度与恢复状态。 |
| `planning-input.md` | 模块级规划输入。 |
| `generation-plan.json` | SQL 需求与批次计划。 |
| `sql-generation-input.md` | 计划 SQL 的统一生成输入。 |
| `sql/` | 已规划 SELECT、manifest 和验证报告。 |
| `inputs/BATCH-xxx-input.md` | 当前批次输入清单。 |
| `inputs/TP-xxx-input.md` | 完整审计输入。 |
| `inputs/TP-xxx-delta.md` | 批次 worker 的 TP 增量。 |
| `by-tp/` | 每个 TP 的已验证用例。 |
| `module-test-cases.md` | 确定性收录后的模块用例。 |
| `coverage-matrix.md` | TP 到最终用例的覆盖。 |
| `runner-logs/` | 事后审计日志，不参与调度。 |
| `history/` | refresh 归档。 |

Excel 不属于本 Skill；模块 Markdown 完成后按需单独使用 `testcase-excel-converter`。
