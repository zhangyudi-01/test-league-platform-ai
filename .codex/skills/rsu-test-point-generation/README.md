# RSU 测试点生成 Skill 使用手册

本手册说明 `rsu-test-point-generation` 的运行、恢复和排障。AI 执行契约以 [SKILL.md](./SKILL.md) 与 `references/` 为准；历史变更见 [OPTIMIZATION-HISTORY.md](./OPTIMIZATION-HISTORY.md)。

## 1. 目标与边界

输入是已通过 `module-requirement-preanalysis` 校验的模块产物。默认 Runner 先完成一次模块级基线生成，再按需处理局部 fork：

1. 父 Runner准备完整业务输入并编译自包含 Worker packet。
2. 一次零工具 Baseline Worker 先建立 FC/Q/DC 覆盖账本并做生成前 simple/complex 路由，只为简单 RSU 返回必要候选。
3. 对 needs-fork/blocked 的单 RSU 或直接耦合跨 RSU 复杂 Scope 启动结构化 Fork，由 Fork 首次生成该范围候选。
4. 父 Runner确定性校验、编号、渲染并原子发布 Markdown。
5. 可选地审查测试用例生成所需的数据、环境、配置和可观察性输入。

本 Skill 不拆需求、不修改 RSU map、不生成测试方案/测试用例/Excel，也不自动回答 Q/CIQ。

## 2. 核心能力

| 能力 | 说明 |
|---|---|
| Manifest 定位 | 优先使用 `preanalysis/v1` manifest 的资源角色和输出路径，不按中文目录名猜测。 |
| 权威输入 | 每个 RSU 都保留完整 `inputs/<RSU-ID>-input.md` 与 SHA-256。 |
| 动态规划 | Planner 根据语义宽度、状态/时序风险和动态依赖划分普通/复杂 RSU；分类不写回前置分析。 |
| 批次执行 | 普通且上下文兼容的 RSU 目标每批 4～6 个、最多 10 个；复杂 RSU 单独成批。 |
| 模块基线/fork | 默认一次自包含、零工具语义基线先分流；简单 RSU 在基线生成，复杂 Scope 从干净基线定向 Fork 首次生成。旧 foundation-fork 保留兼容。 |
| 历史隔离 | 兄弟 fork 不继承彼此提示、工具调用和输出；默认不跨 RSU `resume`，也不等待自动 compaction。 |
| 有界并发 | 模块内默认最多 3 个 batch Worker，并继续服从全局 slot；非 `workspace-write` 自动串行。 |
| 父提交 | 默认 Worker 不写文件；父 Runner解析语义 JSON 后稳定编号、渲染和提交。兼容批次 Worker 仍只写私有 staging/result。 |
| 可恢复状态 | schema 4 / state-v2 额外记录 Worker packet/business/policy/schema/risk/source 指纹、私有结果和 thread ID；恢复不扫描日志。 |
| 必要候选 | 每个 RSU 合法产生 `0～N` 个候选；候选数不是目标，零候选必须有可审计理由。 |
| 独立行为生成 | Worker 以高级测试工程师身份先识别独立测试承诺；每个候选必须能独立触发、执行、判定并定位缺陷；不设目标数量。 |
| 需求来源边界 | 测试点以需求原文行为为边界；Question 答复只解释/限定原文，不单独新增 TP。数据源、公式、SQL/计算路径等确认口径用于对应 TP 的测试设计或 SQL，除非用户明确声明新增验收行为。 |
| 语义判断 | 状态、错误码、字段、等价类、边界和页面/API/数据库/日志观察层按需求语义拆合；不同操作、对象、状态迁移、结果或缺陷归属拆分，同一操作下的等价输入或共同证据才合并。 |
| 确定性最终化 | 全部计划 RSU validated 后，父 Runner 默认一候选一 TP，只合并测试项、完整测试点和备注均完全重复的候选；并发完成顺序不影响最终编号。 |
| Readiness 门禁 | 只有整体结果为 `ready` 才允许进入测试用例生成。 |
| 可靠性 | 保留模块锁、全局 slot、心跳、watchdog、瞬时错误有限重试、机械校验修复和结构化 telemetry。 |

当前明确不增加单 RSU 熔断或会话级熔断。

## 3. 默认自包含基线流程

```text
校验上游与初始化状态
        │
        ▼
父 Runner 编译完整 stdin packet + JSON Schema
        │
        ▼
零工具 Baseline Worker ──> 路由 + simple semantic JSON + FC/Q/DC 账本
        │
        ├── 简单范围 ─────────> Baseline 内首次生成
        └── 复杂范围 ─────────> bounded complex-generation Fork 首次生成
        │
        ▼
父 Runner 编号、渲染、校验、原子发布
```

子 Worker 不读取 Skill、仓库文件、Runner 脚本或历史日志，也不写 Markdown/状态。定向 Fork 继承干净 Baseline 公共上下文，同时收到包含授权 RSU 与专属 FC/Q/DC 正文的局部 packet；任何工具调用或范围外引用都会被父 Runner拒绝。Fork 不复核或改写 Baseline 候选，而是从零生成复杂 Scope。默认主链中旧的路径式自主 baseline 和直接写 Markdown 的 semantic-fork 实现已经移除；`foundation-fork` 的 planning/batch 流程仅作为独立、显式兼容架构保留。

### Worker 与父 Runner 的衔接

父 Runner 是确定性编排与提交方，不负责替代 Worker 做需求语义判断。它先校验上游产物、构造权威 InputBundle、编译自包含 packet 和 JSON Schema，再通过 stdin 把它们交给 Worker。Worker 是语义分析方：以高级测试工程师身份识别独立测试承诺，完成 simple/complex 路由、候选生成、来源追溯和原子性自审，只返回结构化 JSON。

Worker 返回后，父 Runner 负责校验 Schema、packet/hash、RSU/Q/Context/Data Closure 授权、复杂 Scope 边界、FC/Q/DC 处置和候选覆盖；通过后才把 Worker 的局部 key 映射为稳定 Candidate ID、渲染 `by-rsu/` 和模块汇总。默认最终化只做精确重复去重和稳定 TP 编号，不替 Worker 把复合候选重新拆开；发现候选包含多个独立行为时，应拒绝汇总并重新打开对应 RSU。

## 4. 运行方式

在普通 PowerShell 终端或 CI 中运行：

```powershell
python -B .codex/skills/rsu-test-point-generation/scripts/run_generation.py `
  "modules/<模块目录>" `
  --manifest "modules/<模块目录>/preanalysis/preanalysis-manifest.json"
```

不要在已经作为本 Skill Worker 执行的 AI turn 内递归启动 Runner。

`module-baseline` 现为 CLI 默认架构；`foundation-fork` 是兼容路径。旧的 `legacy-resume` 仍不可选。

### 会话模式

默认模式：

```powershell
--session-mode module-session
```

无需指定 `--pipeline-architecture`。只有 Baseline 在生成前路由出 complex scope 时才要求 Codex CLI 支持 `codex exec fork`；不会静默退回旧的跨 RSU `resume` 或模型分段读文件。

隔离模式：

```powershell
--session-mode isolated
```

每个 RSU 创建新会话并读取该 RSU 的完整输入，按 RSU 顺序一次执行一个；finalization 和 readiness 也各自使用新会话。适合不支持 fork、手动逐 RSU 执行或排查隔离问题。

在 `foundation-fork` 架构下，旧参数 `--context-refresh-interval` 仍可传入，但只会显示一次弃用提示并被忽略。独立 fork 已阻断兄弟历史，不再做同一长会话的每 N 个 RSU 重锚。

## 5. 关键参数

| 参数 | 默认 | 用途 |
|---|---:|---|
| `--pipeline-architecture` | module-baseline | 默认模块级基线；`foundation-fork` 仅兼容使用。 |
| `--dry-run` | false | 仅准备输入、路由和状态，不调用 Codex、不改正式测试点。 |
| `--run-readiness` | false | 在测试点完成后可选运行 readiness，readiness 不阻塞测试点完成。 |
| `--worker-packet-budget-bytes` | 1000000 | 自包含 Worker packet 的 UTF-8 字节上限；超限记录 context-pressure 并停止。 |
| `--module-concurrency` | 3 | 当前模块并行 batch Worker 上限。 |
| `--global-concurrency` | 3 | 共享 slot 下所有 Runner 的 Codex turn 上限；0 关闭。 |
| `--max-rsu-turns` | 未完成 RSU 数 | 本次 RSU 安全预算。 |
| `--max-transient-retries` | 6 | 供应商/网络瞬时错误的 Runner 级重试。 |
| `--stage-timeout-seconds` | 3600 | 单阶段总墙钟超时；0 关闭。 |
| `--stall-timeout-seconds` | 900 | 无 JSONL 事件超时；0 关闭。 |
| `--heartbeat-interval-seconds` | 60 | 等待阶段输出的进度心跳。 |
| `--repeated-action-limit` | 6 | 连续相同工具动作终止阈值；0 关闭。 |
| `--max-watchdog-retries` | 1 | watchdog 终止后的恢复次数。 |
| `--max-validation-repairs` | 2 | 确定性校验错误修复回合。 |
| `--session-reset-after` | 2 | 连续瞬时会话失败后的恢复阈值。 |
| `--session-recovery` | fresh-session | 可选 fresh-session / isolated / stop。 |

另有 `--manifest`、`--preanalysis-dir`、`--output-dir`、`--workdir`、`--logs-dir`、`--codex-bin`、`--model`、`--profile`、`--global-lock-dir` 等路径和执行配置。以 `run_generation.py --help` 为准。

## 6. 输入文件为什么仍然存在

默认 Worker 不自己读取这些文件；它们由父 Runner确定性汇集、审计与恢复：

- `baseline-input.md`：父 Runner 的业务事实中间件；正文只包含所有 RSU 实际物化依赖的去重并集。
- `baseline-worker-packet.md`：完整 stdin payload，包含 policy、业务事实、风险事实、来源指纹和 output schema。
- `worker-results/baseline.json`：schema-constrained 私有语义结果；Worker 不直接生成 Markdown。
- `inputs/<RSU-ID>-input.md`：该 RSU 的完整权威输入，可独立审计和重跑。
- `session-inputs/<RSU-ID>-delta.md`：batch fork 使用的当前 RSU/支持 RSU/Q/动态 FC/DC/证据与哈希，省略 Foundation 已加载的固定正文。
- `batches/<BATCH-ID>-input.md`：批次成员、上下文签名、输入、动态依赖与授权输出清单。
- `finalization-session-input.md`、`case-readiness-session-input.md`：后续 Foundation fork 的轻量输入；对应完整输入仍保留。

会话记忆不是事实源。packet/business/policy/schema/risk/source 任一指纹变化时，baseline 私有结果失效；旧正式文件在新结果完整通过校验前保持不变。

## 7. 输出目录

```text
test-points/
  generation-state.json
  baseline-input.md
  baseline-worker-packet.md
  baseline-result.json
  worker-schemas/
  worker-results/
    baseline.json
    merged.json
  generation-plan.json
  planning-input.md
  inputs/
  session-inputs/
  batches/
  batch-results/
  fork-inputs/
  fork-results/
  by-rsu/
  history/
  finalization-input.md
  finalization-session-input.md
  module-test-points.md
  coverage-matrix.md
  case-readiness-input.md
  case-readiness-session-input.md
  test-case-readiness.md
  runner-logs/
```

`runner-logs/` 只用于诊断，不作为进度控制面。Runner 恢复不扫描历史日志来推断“执行到哪个 RSU”，只读取状态、计划、产物与哈希。

## 8. 状态与恢复

状态 schema 为数字版本 `4`，调度标识为 `rsu-test-point-generation/state-v2`。

- `pending` / `prepared`：等待计划或执行。
- `running`：受管阶段正在执行；重启发现没有活跃进程时恢复为可重试。
- `validated`：来源、输入、输出、格式和权限均已验证。
- `failed`：阶段失败。
- `replan-required`：只重排受影响的未完成成员。
- `blocked` / `stale`：上游缺口或来源变化，必须修复或 refresh。

批次私有 `result.json` 的聚合状态为 `draft`、`partial`、`complete` 或 `replan-required`；逐 RSU 状态为 `draft`、`complete`、`failed` 或 `replan-required`。父 Runner 启动 Worker 前会原子写入批次/RSU `running` 和 owner 信息。`failed` 表示该成员本轮未完成：具体原因写入状态后回到 `prepared` 重试，不会撤销或阻止同批其他合法 `complete` 成员先提交。

重启恢复顺序是：恢复无活跃 owner 的陈旧 `running` → 校验已有私有 result → 提交可独立验证的完成成员 → 只为剩余成员重建 batch manifest/result。已完成成员不会再次调用 AI；损坏、成员越界、顺序错误或其他非法结果会移入 `history/batch-results/` 后再重新准备。恢复判断不读取历史日志。

旧 schema 1～3 状态会被备份；旧 resume session ID 不复用。来源未变且可重新验证的完成结果可保留。损坏状态、未知 schema 或无法安全判断的迁移会停止，不会覆盖原文件。

重新打开一个 RSU：

```powershell
python -B .codex/skills/rsu-test-point-generation/scripts/reopen_rsu.py `
  "modules/<模块目录>" RSU-001 `
  --manifest "<manifest>"
```

它只失效目标 RSU、所属批次和下游 finalization/readiness；无关 validated 结果保持完成。

## 9. 候选质量规则

每个候选应表达一个明确、可独立验证的功能行为、业务规则、状态控制、操作分支、状态迁移、异常处理或边界约束。业务列为 `测试项 | 测试点 | 备注`：测试项简洁分类，测试点直接说明必要条件、操作或系统事件及明确预期，备注可为空且只作补充。不同操作或不同业务结果可以分别形成测试点；不能在一条描述中塞入多个独立行为。旧三列仅兼容读取，不能通过机械改名完成语义迁移。

不设置候选数量目标。普通和复杂 RSU 都可以合法产生 `0～N` 个必要候选：高级测试工程师依据独立触发、独立执行、独立判定和独立缺陷定位判断粒度，不为了写多而机械拆分，也不为了数量少而强制合并。状态、错误码、字段、等价类、边界值以及页面/API/数据库/日志观察层，若对应不同操作、对象、状态迁移、结果或缺陷归属就拆分；同一操作下的等价输入或共同证据才合并。

Worker 只删除测试项、完整测试点和备注均完全重复的明显重复项，不做“同一风险”“同一生命周期”或观察层的广义业务合并。

## 10. 并发与权限

父 Runner是唯一共享状态写入者。Worker 只允许写：

- `batches/<BATCH-ID>/` 下自己的 staging 文件；
- `batch-results/<BATCH-ID>/result.json`。

Worker 修改 `generation-state.json`、最终文件、正式 `by-rsu/` 或兄弟批次目录会被视为越权并隔离。父 Runner按 RSU map 稳定顺序接纳完成结果，所以并发乱序不会改变正式顺序和最终 `TP-ID`。

AI 阶段不运行准备或校验脚本。若它误写共享状态，父 Runner 会回滚到调用前状态并自行校验授权输出，避免模型或校验器旁路父提交。

## 11. Finalization 与 readiness

finalization 只处理已验证候选，不从原文补造候选、不按目标数量增删测试点。默认一候选一 TP，仅当测试项、完整测试点和备注均完全重复时确定性合并，并继承全部 Source RSUs、Question Refs、Context Refs 和 Data Closure Refs。

readiness 只判断是否足以设计可执行用例，不检查执行环境是否已经部署或账号是否已发放。实际环境地址、账号/权限、具体样本和实例若不改变设计，写为用例前置条件或执行时绑定；对于数据库用例，必须已有足够明确的语义数据画像、查询/断言口径和安全准备/清理恢复方案。只有这些设计输入本身不可替代地缺失时才返回 `blocked-input`；发现上游覆盖缺口则返回 `upstream-gap`。不得因缺少实际环境访问而要求用户先确认可用，也不得把生产造数或未授权修改列为默认步骤。

## 12. 排障

- `requires codex exec fork`：升级 CLI，或显式使用 `--session-mode isolated`。
- `blocked`：处理 pending Q 或缺失来源后重新运行。
- `stale`：来源/输入哈希变化，重新准备；不要手工把状态改为 validated。
- `replan-required`：Runner 会保留 validated 成员并重排受影响批次；检查具体理由。
- `outside its authorization`：Worker 修改了共享或兄弟文件，隔离输出后重试。
- `readiness ... blocked-input/upstream-gap`：按 `test-case-readiness.md` 修复输入或回退上游。
- 卡死/重复工具动作：查看当前 run 的 JSONL、stderr 与 telemetry，调整 watchdog 只用于诊断；日志不参与恢复决策。

不优先依赖自动 compaction：兄弟 RSU 的工具历史本来就不应成为业务依据，当前拓扑从一开始就不让后续 fork 继承这些历史。compaction 触发时机不可由 Runner在 TP/RSU 边界确定性控制，也不能替代来源哈希和状态恢复。
