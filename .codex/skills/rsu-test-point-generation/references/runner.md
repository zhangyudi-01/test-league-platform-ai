# 自动连续执行 Runner

`scripts/run_generation.py` 是面向普通终端或 CI 的父编排器。它以文件、SHA-256 和唯一 `generation-state.json` 为进度事实，不解析模型自述来猜测完成状态。

## 会话拓扑

Runner 的会话模式在所选 pipeline 架构内生效：

- `foundation-fork` + `module-session`：先创建一个模块 Foundation；planning、每个 RSU 批次、finalization、readiness 均通过 `codex exec fork <FOUNDATION_THREAD_ID>` 从该 Foundation 独立派生。所有兄弟 fork 使用同一父会话，但互不继承彼此的消息、工具调用和输出。
- `isolated`：每个 RSU 使用新的 `codex exec` 并读取该 RSU 完整输入，按 RSU 顺序一次执行一个；finalization/readiness 也各自独立。适合 CLI 不支持 fork、手动执行或排查会话问题。

`module-baseline` 是默认 pipeline architecture；`foundation-fork` 保留为独立兼容路径。默认主链中旧的路径式自主 baseline 和直接写 Markdown 的 semantic-fork 已移除，不会作为隐式回退。旧 `legacy-resume` 曾通过同一长会话的 `codex exec resume` 顺序处理 RSU，现已移除，不再接受该参数。

默认 `module-baseline` 的 baseline 不是通用仓库 Agent：父 Runner先把精简规则、完整业务输入、风险事实、来源指纹和精确 JSON Schema 编译为一个自包含 packet，并把全文通过 `codex exec` stdin 发送。子 Worker 必须零工具调用，只返回 schema-constrained 语义 JSON；Markdown、编号、状态和校验全部留在父进程。只有被风险路由选中的局部范围才从干净的 baseline thread fork，并收到自己的自包含 scope packet。

## Worker 与父 Runner 的交接契约

父 Runner 是确定性编排、权限校验和结果提交方；Worker 是受限的语义分析方。两者不是连续共享工作区的两个 Agent，而是通过 packet、Schema、局部 key 和哈希交接：

1. 父 Runner 完成 manifest/前置分析校验，建立每个 RSU 的权威 `InputBundle`，计算允许的 RSU、Q、Context、Data Closure 范围。
2. 父 Runner 把完整业务事实、精简生成规则、风险事实、来源指纹和输出 Schema 编译为 stdin packet；Worker 不重新寻找文件、不加载 Skill、不运行脚本。
3. Worker 以高级测试工程师身份，先识别独立测试承诺，再完成 simple/complex 路由、候选生成、来源追溯和原子性自审。每个候选必须能够独立触发、独立执行、独立判定并独立定位缺陷；Worker 只返回结构化 JSON。
4. 父 Runner 收到 JSON 后校验 Schema、packet/hash、引用授权、Scope 边界、FC/Q/DC 处置、RSU 覆盖和候选/Disposition 双向一致性；这些校验确认“结果合法”，不代替 Worker 理解业务语义。
5. 校验通过后，父 Runner 才分配稳定 Candidate/TP ID、渲染 Markdown、生成覆盖矩阵并原子提交。默认最终化不重新拆候选；若发现一个候选包含多个可独立验证行为，应停止汇总并重新打开对应 RSU。

因此，前置分析完成并不等于 Worker 自动继承了“测试点已识别”的中间结果：前置分析提供需求事实和 RSU 边界，Worker 在 packet 内重新完成语义识别。过去的缺口是 Worker 直接从事实生成候选，原子性只存在于自然语言要求中，没有被要求在生成前后显式自审；本版本已把角色、原子定义、拆分/合并条件和典型复合反例加入各语义 Worker 规则。

`foundation-fork` 禁止跨 RSU 或跨阶段使用 `codex exec resume`。启动时必须探测 `codex exec fork`；能力缺失时在候选写入前失败，并提示升级 CLI 或显式使用 `--session-mode isolated`。

Foundation 只加载 Skill、固定需求来源、稳定索引和契约。它不加载某个批次候选、Worker 工具历史或后续阶段输出。会话记忆用于避免重复注入固定正文；路径、哈希和物化输入始终是事实源。

## 执行流程

默认 `module-baseline`：

1. 校验 manifest 与前置分析，初始化或迁移 JSON 状态，并物化逐 RSU 权威输入。
2. 从所有 RSU `InputBundle` 聚合固定/动态材料的去重并集；未被物化的证据或登记来源只写路径、用途和 SHA-256，不展开正文。
3. 生成 `baseline-worker-packet.md` 与版本化 output schema；packet 超过 `--worker-packet-budget-bytes` 时写入明确的 `context-pressure` 状态并停止，不回退到让模型分段读文件。
4. 启动一次零工具模块语义 Worker。Worker 先返回逐 RSU simple/complex disposition、FC/Q/DC 覆盖账本和复杂 Scope 路由，并只为简单 RSU 返回候选语义；不写共享或正式文件，非零工具调用直接判为契约违规。
5. 父 Runner 校验 schema、来源引用、范围和哈希，并用结构化复杂度信号检查明显需要 Fork 的范围没有被误留在 Baseline。该检查只保护 simple/complex 路由，不规定测试点数量、拆分方式或合并方式。定向 fork 同样只接收 stdin packet、只返回局部候选语义；范围外变化被拒绝。
6. 父 Runner分配稳定 Candidate/TP ID，渲染 `by-rsu/`、`module-test-points.md` 和 `coverage-matrix.md`，运行现有确定性校验；全部通过后才发布。readiness 按需独立运行，不阻塞测试点完成。

兼容 `foundation-fork`：校验并物化输入后创建 Foundation，再 fork planning、批次 Worker、finalization 和 readiness。普通且上下文兼容的 RSU 目标每批 4～6 个、最多 10 个；复杂 RSU 单独成批。父 Runner 负责有界并发、写边界、结果校验、原子提交、局部重排和 JSON 恢复，整个过程不读取历史日志判断进度。

并行完成顺序不影响最终编号；finalization 按 RSU map 和局部候选顺序确定 `TP-ID`。

## 运行

```powershell
python -B .codex/skills/rsu-test-point-generation/scripts/run_generation.py `
  <module-dir> `
  --manifest <preanalysis-manifest.json> `
  --pipeline-architecture module-baseline
```

常用参数：

- `--pipeline-architecture module-baseline`：默认模块级基线；Baseline 先理解完整模块并路由 simple/complex，只有需要补充局部上下文或集中推理的复杂 Scope 创建定向 fork。复杂度路由不参与测试点数量控制或语义合并。
- `--pipeline-architecture foundation-fork`：旧 Foundation/planning/batch/finalization/readiness 兼容路径。
- `--session-mode module-session|isolated`：默认 `module-session`；`isolated` 为一次一个 RSU 的手动/兼容模式。
- `--module-concurrency N`：模块内批次 Worker 上限，默认 3。
- `--global-concurrency N`：共享 slot 下所有 Runner 的 Codex turn 上限，默认 3；`0` 关闭全局协调。
- `--dry-run`：只准备模块基线输入、路由和指标状态，不调用 Codex，不修改正式测试点。
- `--run-readiness`：测试点完成后显式运行 readiness；readiness 不再阻塞测试点完成。
- `--worker-packet-budget-bytes N`：自包含 Worker packet 的 UTF-8 字节上限，默认 1,000,000；超限显式停止，不静默改为路径读取。
- `--max-rsu-turns N`：按 RSU 数量限制本次安全预算，不是每 RSU 单独开 turn 的承诺。
- `--max-transient-retries N`、`--retry-base-delay-seconds`、`--retry-max-delay-seconds`：供应商或网络瞬时错误的有限指数退避。
- `--stage-timeout-seconds`、`--stall-timeout-seconds`、`--heartbeat-interval-seconds`、`--repeated-action-limit`、`--max-watchdog-retries`：阶段看门狗与恢复参数。
- `--max-validation-repairs N`：确定性格式或引用错误的有限修复回合。
- `--session-reset-after`、`--session-recovery`：Foundation/会话连续瞬时失败后的恢复策略，不是单 RSU 或会话级业务熔断。
- `--context-refresh-interval N`：旧命令兼容参数。接受、输出一次弃用提示并忽略；独立 fork 不执行同会话周期重锚。
- `--workdir`、`--output-dir`、`--preanalysis-dir`、`--logs-dir`、`--model`、`--profile`、`--codex-bin`：显式路径或 Codex 配置覆盖。

完整参数以 `run_generation.py --help` 为准。

## 状态与恢复

`generation-state.json` schema 为数字版本 `4`，并带有 `scheduler_schema = rsu-test-point-generation/state-v2`。共享状态只允许父 Runner通过临时文件、刷新和原子替换提交。

- `pending` / `prepared`：等待规划或执行。
- `running`：受管进程正在运行；重启后若没有活跃进程，恢复为可重试状态。
- `validated`：输入、输出、来源、哈希和授权范围都已验证。
- `failed`：阶段失败，可按有限重试或人工修复处理。
- `replan-required`：只重新规划受影响且未完成的工作。
- `blocked` / `stale`：上游缺口或来源变化，必须修复或显式 refresh。

批次私有 `batch-results/<BATCH-ID>/result.json` 使用独立状态契约：

- 聚合状态：`draft`、`partial`、`complete`、`replan-required`。
- 逐 RSU 状态：`draft`、`complete`、`failed`、`replan-required`。
- `draft` 聚合只有在至少一个成员已有终态时才可作为中断恢复现场；全员仍为 `draft` 不代表进度。
- `failed` 必须包含具体原因，父 Runner 记录原因后把该成员恢复为 `prepared` 重试；它不使同批合法的 `complete` 成员回滚。
- `replan-required` 必须包含具体的复杂时序、冲突依赖或语义宽度理由，只失效受影响的未完成工作。

重启时，父 Runner 先检查 `running` 批次的 owner：活跃 owner 仍存在则拒绝抢占；owner 已不存在则恢复为 `prepared`。随后优先验证已有合法完整/部分 result，提交完成成员并仅为剩余成员重新物化 batch manifest/result。损坏、越界或与活动成员不一致的 result 隔离到 `history/batch-results/`。整个恢复判断只读取状态、计划、私有结果和哈希，不扫描历史日志。

旧 schema 1～3 状态会先备份再受控迁移；旧的 resume 会话 ID 永不复用。哈希一致且可独立校验的完成结果可保留，无法安全判定时停止并要求 refresh。

`reopen_rsu.py` 只失效目标 RSU、所属批次与下游 finalization/readiness；不相关且哈希一致的 validated 结果保持完成。

## 输入策略

默认 `module-baseline`：

- `baseline-input.md` 是父 Runner 生成的业务事实中间件，不是子 Worker 要读取的路径。
- `baseline-worker-packet.md` 把完整业务事实、精简 policy、结构化风险事实、来源指纹和精确 output schema 合并为一次 stdin payload。
- `worker-results/baseline.json` 只保存 Baseline Worker 的生成前 simple/complex 路由、简单候选和 FC/Q/DC 覆盖账本；其状态哈希永远只指向这份 Baseline-only 结果。复杂 Fork 的结果单独保存在 `fork-results/`，最终合并语义结果保存在 `worker-results/merged.json`，不得覆盖 Baseline 文件；`baseline-result.json` 仅为父 Runner 确定性生成的旧格式兼容清单。
- `fork-inputs/COMPLEX-xxx-worker-packet.md` 显式包含授权 RSU 与专属 FC/Q/DC 正文；对应 Fork 从零生成复杂 Scope，不复核既有候选，也不修改 Markdown。
- 恢复只比较 packet/business/policy/schema/risk/source 指纹与私有结果哈希，并用 Baseline 的逐 RSU 授权再次验证复用结果；旧 Runner 曾写入合并 Fork 候选的 Baseline 文件会被判为不可复用并重新生成。恢复不读取 JSONL 或历史命令日志。

兼容 `foundation-fork`：

- `inputs/<RSU-ID>-input.md` 是逐 RSU 完整权威输入，始终生成并绑定 SHA-256。
- `session-inputs/<RSU-ID>-delta.md` 是批次 fork 的补充输入：保留当前 RSU、支持 RSU、Q、动态 FC/DC、证据和允许引用集合，省略 Foundation 已加载的固定正文。
- `batches/<BATCH-ID>-input.md` 列明批次成员、模式、动态依赖、完整输入、delta、授权输出和哈希。
- `finalization-session-input.md` 与 `case-readiness-session-input.md` 用于 Foundation fork；完整输入仍分别保留为 `finalization-input.md` 与 `case-readiness-input.md`。
- Foundation 身份、固定来源指纹或锚点冲突时，停止使用轻量输入并回退该阶段完整输入；仍不一致则停止。

不优先依赖自动 compaction。TP/RSU 兄弟阶段的工具历史本来就不应成为后续业务依据，因此从会话拓扑上隔离，而不是先积累无用历史再等待不确定时机压缩。

## Worker 权限与停止规则

默认 Baseline 与 complex-generation Worker 必须零工具调用。它们不获得需要读取的仓库路径，不加载本 Skill，不运行准备/校验/Runner 脚本，也不写任何文件；父 Runner从 CLI 的 final response 文件读取 JSON。任何工具调用、schema 违规、过期 hash、复杂 RSU 在 Baseline 提前生成候选、FC/Q/DC 账本缺项或越权引用都不会发布正式产物。

Worker 只能写提示授权的批次私有目录和 `batch-results/<BATCH-ID>/result.json`。禁止写：

- `generation-state.json`
- `generation-plan.json`
- `module-test-points.md`
- `coverage-matrix.md`
- 其他批次目录或正式 `by-rsu` 结果

各 AI 阶段不得自行运行会提交共享状态的准备/校验脚本。若阶段误写 `generation-state.json`，父 Runner 先恢复调用前字节并记录 `unauthorized_state_write_rolled_back`，随后只依据授权输出运行自己的校验和状态提交；模型写入不能成为完成依据。

以下情况停止并等待处理：上游校验失败、pending Q、必需来源缺失、基线或 fork 能力不满足、计划非法、越权写入、哈希漂移、无法安全迁移。readiness 非 `ready` 只阻塞后续测试用例生成，不撤销已完成的测试点。

已经在 Skill 的 AI Worker 内时不得递归启动 Runner。Runner 从普通终端或 CI 启动。

## 日志与 telemetry

Runner 日志默认写入 `<output-dir>/runner-logs/<run-id>/`，仅用于诊断，不作为决定下一个 RSU/批次的进度来源。恢复只读取状态、计划、批次私有结果和产物哈希，不扫描历史日志推断进度。

结构化 telemetry 按 foundation、planning、batch、finalization、readiness 记录阶段身份、父子会话、批次/RSU 数、耗时、工具调用、input/cached/output token、重试、replan 与验证结果。

当前明确不增加单 RSU 熔断或会话级熔断。
