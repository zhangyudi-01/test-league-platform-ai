---
name: tp-test-case-generation
description: Generate concise, executable module test cases from validated test points by planning SQL once, batching simple TPs, isolating complex TPs, and finalizing Markdown deterministically. Use after module test points and case-readiness are ready; do not use for test-point generation or Excel conversion.
---

# 模块测试用例生成

## 目标

以最终测试点为边界，生成测试人员可以直接执行的简洁用例。模块只分析一次，必要查询 SQL 只规划和生成一次；简单 TP 批量生成，复杂 TP 独立生成；最终模块文档由脚本确定性拼接，不再由 AI 二次扩写。

完整命令与恢复方法见 [使用手册](./README.md)。输出格式见 [输出契约](./references/output-contract.md)，批次 worker 见 [执行契约](./references/tp-worker-contract.md)，SQL 规则见 [SQL 资产说明](./references/sql-assets.md)。维护本 Skill 时必须完整读取 [优化记录](./OPTIMIZATION-HISTORY.md)，完成后追加唯一编号。

## 唯一状态与阶段

`test-cases/generation-state.json` 是唯一调度和恢复依据。Runner 不读取历史日志决定进度；日志只用于事后审计。

```text
模块需求、最终 TP、readiness ready
              ↓
模块生成计划：复杂度 × SQL必要性 × 批次
              ↓
必要 SELECT SQL 统一生成并 EXPLAIN
              ↓
简单/查询展示批次（每批最多10个 TP）
复杂批次（1个 TP）
              ↓
确定性生成 module-test-cases.md 与 coverage-matrix.md
```

默认 `module-session` 只建立一个模块基础会话。规划、SQL 和每个测试用例批次分别从基础会话独立 fork；兄弟批次不继承消息、工具调用或输出。不把自动 compaction 当作主要治理手段。

基础会话完整读取本 Skill 及输出、worker、SQL 契约；其 ID 和输入指纹作为可选 `foundation_session` 写入状态。再次运行时，来源、规则、CLI 和运行配置均未变化才复用基础会话，仍从它创建独立 fork，不续接上一个批次。明确报基础会话不存在时最多重建一次；`isolated` 模式及已完成流程不建立基础会话。

## 模块规划

在写任何 SQL 或测试用例前，必须先生成并验证 `generation-plan.json`：

- 每个 TP 必须且只能进入一个批次，保持最终测试点顺序。
- 复杂度与 SQL 必要性是两个独立维度，不能把“复杂 TP”与“需要 SQL”绑定。
- 简单 TP 和同页面查询展示 TP 按功能、共享上下文及 SQL 复用关系分批；通常每批 6～10 个，最多 10 个。
- 并发、锁、轮询、超时、重试、校验短路、多状态组合等复杂 TP 单独成批。
- 对每个 TP 实际评估用例拆分需要，不预设用例数量。仅当独立业务风险、不可合并前置或操作、独立可判断预期、独立回归价值四项同时成立时，才将该 TP 拆成多条用例；否则将可合并的验证收敛在较少用例中。不得仅因正常/边界/非法等数据维度不同而拆分。
- 某 TP 已由其他 TP 验证单一分支时，本 TP 只验证自己独有的组合、顺序或优先级，不重复完整分支流程。

## SQL 使用边界

SQL 在用例批次之前统一规划、生成和校验。用例阶段只能引用已分配的 SQL-ID，不得临时新增 SQL。

应该规划查询 SQL：

- 页面查询条件对应的结果集；
- 页面顶部、详情区域的数据库来源字段；
- 页面列表列值；
- 页面聚合数量、统计值；
- 需求明确要求与数据库直接核对的数据一致性。

不得为了写 SQL 而写 SQL：

- 下拉选项、默认值、输入限制；
- 按钮显示、隐藏、置灰；
- 提示语和校验顺序；
- 第三方接口调用、Mock 返回处理；
- 轮询、超时、重试；
- 并发、锁、重复提交；
- 勾选保留或取消；
- 页面或接口已经可以直接判断的普通状态流转；
- 仅仅因为 TP 引用了 `DC-*`。

入库或更新场景在预期中描述应新增或更新的记录内容。本 Skill 不自动生成 `INSERT`、`UPDATE`、`DELETE`。确需核对页面/API查询结果时使用计划好的共享 `SELECT`。

需求含原型图时，先识别原型中的实际页面功能区，计划中的每条 SQL 标注 `functional_module`，按功能区组织查询；字段/别名及结果顺序应便于与对应区域逐项对照。无原型图时按需求明确的功能模块组织。不得虚构区域或从原型推导新业务口径；归属不明时回到需求澄清。相同功能区数据视图优先共用参数化查询，不按 TP 或底层表机械拆 SQL；执行体相同或仅过滤参数变化时复用，不同业务口径不强行合成万能 SQL。全部计划 SQL 在用例生成前统一通过一次静态检查和 MySQL `EXPLAIN`；批次与最终校验只核对该报告及 SQL/manifest 指纹未变化，不重复连接数据库。

## 用例编写规则

### 内容范围

- 只写当前 TP 的关键前置、具体动作和可判断结果。
- TP 含多个值或状态组合时，在前置或步骤中直接列明可执行的具体条件；不能只写“多个场景”“各场景”再让执行者返回测试点或内部计划查含义。
- 不重复入口 TP 已说明的进入方式，除非进入方式本身就是当前 TP 的被测内容。
- 不提前覆盖相邻 TP 的默认值、单选、筛选、详情、权限、日志或其他模块断言。
- 不写与执行无关的测试过程管理话术、会话独占说明或完整数据构造链。

### 前置条件

- 没有前置条件填 `无`。
- 简单条件可直接写一句，例如 `当前年为 $Y（如 2026）`。
- 只有复杂场景确实包含多类信息时才使用 `任务状态：`、`Mock配置：`、`准备动作：` 等分类；分类名必须反映真实内容，不能固定套用。
- 使用分类时，分类名单独一行并以 `<br>` 与内容分隔；分类内每个完整句子也单独一行。
- 不得为了满足排版凭空制造“场景状态”“场景参数”“准备校验”等分类。

### 步骤与预期

- 步骤和预期都从 `1.` 开始连续编号，每项独占一行并用 `<br>` 分隔。
- 步骤与预期数量一致、一一对应：一个具体动作对应一个可判断结果。
- 简单用例保持简单。例如：`1. 点击彩票年下拉框。` → `1. 下拉框包含 $Y 和 $Y-1。`
- 查询 SQL 步骤引用具体 SQL-ID 和文件名；预期简洁写“页面或接口结果与 `SQL-ID` 查询结果一致”，不重复参数绑定、造数过程或同组取值说明。
- 入库或更新预期说明记录所属表、关键关联、字段值/状态及数量；不要求伪造 DML。

### 禁止占位话术

标准用例的前置、步骤和预期不得出现：

- “当前 TP 包含 N 个来源场景”；
- “按场景矩阵执行”；
- “按数据闭包执行计划准备”；
- “执行当前 TP 的核心操作”；
- “按来源场景分别记录结果”；
- “完成执行计划中的场景条件校验”；
- 其他要求执行者返回 TP、RSU、DC、DP 或内部计划才能理解的描述。

`TP/RSU/DC/DP` 等内部标识只出现在追溯索引，不进入人工执行正文。

### 数据变量与追溯

- `数据变量` 不适用填 `无`；适用时使用“字段描述 + `$变量`”，同一变量在前置或步骤中实际使用。
- Trace 中保留当前 TP 允许的 RSU、问题、Context 和 DC；`DC` 是事实来源，不等于必须选择 DP 或写 SQL。
- 测试结果1、测试结果2、测试结果3尚未执行时统一填 `未执行`。

## 命令工作流

初始化：

```powershell
python -X utf8 -B <skill-dir>\scripts\init_generation.py <module-dir>
```

模块计划：

```powershell
python -X utf8 -B <skill-dir>\scripts\prepare_generation_plan.py <module-dir>
python -X utf8 -B <skill-dir>\scripts\validate_generation_plan.py <module-dir>
```

SQL 阶段：

```powershell
python -X utf8 -B <skill-dir>\scripts\prepare_sql_generation.py <module-dir>
python -X utf8 -B <skill-dir>\scripts\validate_planned_sql.py <module-dir> --db-config <config>
```

逐批生成：

```powershell
python -X utf8 -B <skill-dir>\scripts\prepare_next_batch.py <module-dir>
python -X utf8 -B <skill-dir>\scripts\validate_batch_test_cases.py <module-dir> <BATCH-ID> --db-config <config>
```

确定性汇总：

```powershell
python -X utf8 -B <skill-dir>\scripts\prepare_finalization.py <module-dir>
python -X utf8 -B <skill-dir>\scripts\validate_module_test_cases.py <module-dir> --db-config <config>
```

无人值守执行使用 `scripts/run_generation.py`。它依次完成规划、SQL、批次和确定性汇总。`--max-batch-turns` 限制本次批次数；旧 `--max-tp-turns` 作为兼容别名保留。

## 恢复、漂移与阻断

- 进程中断后重跑相同命令，根据状态 JSON 恢复，不读取历史日志。旧 v2 状态不会进入旧逐 TP 流程；需人工确认后用 `--refresh` 建立 v3 规划状态。
- 上游测试点、readiness 或执行上下文变化时，确认影响后执行 `init_generation.py --refresh`；旧产物进入 `history/`。
- 规划、SQL 或批次处于 `prepared` 时，只完成当前阶段，不越过状态机。
- 用例批次首次校验若仅有格式、编号、变量或已有输入引用填写错误，在同一 worker turn 内修正后重验，最多 2 轮（含首次共最多 3 次）；校验通过才能报告完成。这是 worker 执行约束，不是 Runner 新增的强制计数器。缺事实、来源漂移、SQL资产/报告不一致立即阻断，不能靠改状态绕过。
- 余额/额度不足、账户并发窗口已满、模型要求升级 Codex 等明确错误优先于 stream/429 等泛化提示，Runner 不再为其自动重试或重建基础会话；修复外部条件后重跑。CLI 自身的内部重试不由 Runner 控制。
- 缺少业务事实、表字段、关联谓词、Mock 配置或可判断预期时，回填 `CIQ-*` 并停止；不得按表名或惯例猜测。
- 人工编辑 Markdown、SQL、JSON manifest 必须使用 `apply_patch`。Skill 自带确定性脚本按职责写派生产物不受此限制。
- Excel 转换不属于本 Skill；需要时单独使用 `testcase-excel-converter`。

## 维护闭环

若本次实际修改了功能、默认值、兼容性、状态或用户流程，必须在同一 turn：

1. 完整读取 `OPTIMIZATION-HISTORY.md`；
2. 以最大编号加一追加 `TP-OPT-xxx`，不改写历史；
3. 记录真实问题、落盘方案、验证和相关文件；
4. 同步更新 README；
5. 运行单元测试、Python 编译和 Skill 快速校验。
