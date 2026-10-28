---
name: rsu-test-point-generation
description: 在模块需求前置分析通过校验后，由父 Runner 编译自包含输入并用一次零工具语义 Worker 生成必要的 0～N 个可追溯测试点，仅对单 RSU 或跨 RSU 的局部高风险范围定向 fork，再确定性渲染模块测试点并可选审查用例就绪性。适用于跨项目模块测试点生成、恢复和汇总；不用于需求拆分、测试方案或直接生成测试用例。
---

# RSU 测试点生成

本 Skill 把文件、哈希和唯一 JSON 状态作为事实与进度控制面。默认 `module-baseline` 由父 Runner 一次性编译完整业务输入、精简生成规则、风险事实、来源指纹和 JSON Schema，经 stdin 交给零工具 Baseline Worker；Baseline 先建立 FC/Q/DC 覆盖账本并在生成前划分简单 RSU 与复杂 Scope，只为简单 RSU 生成候选。复杂 RSU 必须保持零候选并进入独立 Fork，由 Fork 首次深度生成该范围的测试点。Worker 只返回 JSON，不加载 Skill、不读仓库、不运行脚本、不写 Markdown。旧 `foundation-fork` 仅保留为显式兼容路径，isolated 保留为手动逐 RSU 模式。

## 使用与维护入口

- 操作方法、参数、状态、恢复和排障：阅读 [使用手册](./README.md)。
- Runner 拓扑与停止规则：阅读 [Runner 说明](./references/runner.md)。
- 功能或兼容行为发生变化时，在 [优化记录](./OPTIMIZATION-HISTORY.md) 追加记录，不覆盖历史。
- 本文件与 `references/` 是执行契约；README 只提供操作说明。

## 必读契约

根据当前阶段读取：

1. planning：读取 [规划规则](./references/planning-rules.md) 和 [输入契约](./references/input-contract.md)。
2. batch Worker：读取 [生成规则](./references/generation-rules.md)、[输入契约](./references/input-contract.md) 和 [输出契约](./references/output-contract.md)。
3. module assembly：读取 [模块测试点汇总规则](./references/finalization-rules.md) 和 [输出契约](./references/output-contract.md)。
4. readiness：读取 [用例就绪性规则](./references/case-readiness-rules.md) 和 [输出契约](./references/output-contract.md)。
5. 启用 Data Closure 时，同时使用对应 `data-closure-*.md` 契约。

默认基线阶段由外层 Skill/父 Runner读取并校验上述契约，再把所有 RSU 实际物化依赖的去重并集编译到 `baseline-worker-packet.md`。子 Worker 不再读取 `SKILL.md`、`baseline-input.md` 或任何路径；其私有 `worker-results/baseline.json` 只保存 Baseline 阶段逐 RSU 处置、简单候选语义和 fork 路由，复杂 Fork 结果另存且不得覆盖该文件。父 Runner 将合并语义结果保存在 `worker-results/merged.json`，兼容用的 `baseline-result.json`、候选 Markdown、最终测试点和覆盖矩阵均由父 Runner确定性生成。恢复 Baseline 时除指纹和哈希外，必须重新通过 Baseline-only 授权校验；失败则重新生成，不得复用复杂 Fork 合并结果。

## 核心不变量

- `<module-dir>` 是模块工作区根目录。优先使用显式 `--manifest`；否则只接受唯一可解析的 `preanalysis-manifest.json`，不得按目录名猜测。
- `module-requirement-preanalysis` 的 manifest、RSU map、问题清单、Context/Data Closure Card 和来源文件是需求事实。RSU 的简单/复杂分类是本次生成的运行计划，不得写回前置分析产物。
- `inputs/<RSU-ID>-input.md` 始终保留为该 RSU 的完整权威输入并绑定 SHA-256。Foundation 或 fork 记忆只能减少重复阅读，不能替代文件事实、当前动态依赖或哈希校验。
- 完整生成来源支持的测试点，不设目标数量；不为凑数机械拆分，也不为减少数量强制合并。每个 RSU 可以合法生成 `0～N` 个候选，零候选必须给出可审计理由，不能用来跳过未知、阻塞或难以理解的规则。
- 一个测试点针对一个明确、可独立验证的功能行为、业务规则、状态控制、操作分支、状态迁移、异常处理或边界约束。不同操作或不同业务结果可分别形成测试点。
- 测试点以需求原文描述的行为为边界。Question 答复只解释或限定原文行为，不能单独新增验收对象或测试点；其中仅用于数据源、公式、SQL/计算路径或测试数据判定的口径，留给对应 TP 的测试设计或 SQL 资产。只有用户明确声明新增需求/验收行为时才扩展范围。Context/Data Closure 只能澄清和追溯，不得把实现细节改写成业务措辞扩张验收范围；来源冲突回到前置分析处理。
- 你是高级测试工程师。一个测试点必须能够独立触发、独立执行、独立判定，并且能够独立定位缺陷。状态值、错误码、字段、等价类、边界值以及页面/API/数据库/日志观察层，均须结合需求语义判断：若形成不同操作、不同控件/对象、不同状态迁移、不同业务结果或不同异常/恢复路径，或者可以独立执行和定位缺陷，就拆分；只有属于同一操作、同一对象、同一生命周期阶段和同一预期结果下的等价输入或共同证据时才合并。
- 业务列统一为 `测试项 | 测试点 | 备注`：测试项是简洁功能/规则分类；测试点直接表达必要条件、操作或系统事件及明确预期，不能只是短标题；备注可为空，仅放补充说明，不隐藏关键条件或判据。来源与范围写入追溯列。具体写法见生成规则。
- 当前 RSU 的 `父级条件（原文）` 和 `原文内容` 必须分别审查。父级只作条件时带入相关候选；父级含独立可观察行为但没有对应原文 RSU 时，按上游映射缺口停止。
- 不生成测试方案、测试用例、详细执行步骤或 Excel。

## 模块级基线 / 定向 Fork 验收拓扑

默认流程：

```text
确定性上游校验与输入准备
        │
        ▼
一次自包含、零工具 baseline Worker
        │
        ├── 简单 RSU ─────────────────────> Baseline 内批量首次生成
        ├── FC/Q/DC 覆盖账本 ─────────────> 父 Runner 校验逐项处置
        ├── 单 RSU 复杂生命周期 ──────────> 独立 Fork 首次生成
        └── 直接耦合的跨 RSU 复杂 Scope ─> 独立 Fork 首次生成
        │
        ▼
父 Runner 稳定编号、渲染 Markdown、确定性校验与原子发布
        │
        └── 可选后置 readiness（不阻塞测试点完成）
```

运行时不得因为 RSU 数量直接判定 simple/complex，也不得为了增加数量而制造测试点。复杂度必须在候选生成前根据完整模块关系、结构化风险事实和实际 FC/Q/DC 依赖确定；候选结果不得反过来决定是否 Fork。一个 RSU 内的异步+超时/重试、外部提交+并发/幂等、权限/审计或锁与状态迁移可以独立触发；跨 RSU 只有在业务对象、直接生命周期依赖或专属 FC/Q/DC 明确连接时才组成同一 Scope。共享固定来源或通用卡片本身不得把全模块连成一个 Scope。

Baseline 和 Complex Worker 均以高级测试工程师身份工作：先识别当前范围的独立测试承诺，再生成候选并进行原子性自审。复选框可选性、全选范围、操作按钮可用性和操作后的状态重算，若能独立触发、执行、判定或定位缺陷，必须分别生成候选；不得因为它们属于同一页面、同一对象或同一 RSU 就合并。

## Foundation/Fork 兼容拓扑

从独立普通终端运行（默认即为 `module-baseline`）：

```powershell
python -B <skill-dir>/scripts/run_generation.py <module-dir> --manifest <preanalysis-manifest.json>
```

默认基线模式可使用 `--dry-run` 只准备输入和状态；`--run-readiness` 在测试点发布后显式运行就绪性审查。

`foundation-fork` + `module-session` 的顺序为：

1. 初始化并校验上游、状态和逐 RSU 权威输入。
2. 生成 planning 输入；建立只加载固定需求、稳定索引和契约的模块 Foundation。
3. planning 从 Foundation 独立 fork，生成并验证 `generation-plan.json`。
4. 普通且上下文兼容的 RSU 按目标 4～6、最多 10 个组批；复杂 RSU 单独成批。
5. 父 Runner 在模块并发与全局 slot 的共同限制下调度批次，默认模块内最多 3 个 Worker。
6. 每个批次从同一 Foundation 独立 fork，只补读批次 manifest、逐 RSU delta 和本批动态依赖。兄弟批次不继承彼此消息、工具调用或候选输出。
7. Worker 只写批次私有 staging 和 result；父 Runner 校验授权范围、格式、来源与哈希后，按稳定 RSU 顺序串行、原子提交共享状态和正式候选。
8. 全部计划内 RSU validated 后，finalization 与 readiness 分别从 Foundation 独立 fork，并按此顺序串行执行。

`foundation-fork` 下的 `module-session` 必须支持 `codex exec fork`；能力缺失时在候选写入前失败，提示升级 CLI 或显式使用 `--session-mode isolated`。不得静默退回跨 RSU `resume`。`isolated` 是手动/兼容模式：每个 RSU 及后续阶段都新建会话并完整读取输入，按 RSU 顺序一次处理一个 RSU。

旧的 `legacy-resume` 是本次重构前按 RSU 顺序复用同一 `codex exec resume` 会话的实现，已从 CLI 架构选项中移除，不再作为默认或备用拓扑。

`foundation-fork` 下，`--context-refresh-interval` 仅为旧调用兼容而保留，Runner 接受、提示已弃用并忽略。独立 fork 已阻断兄弟历史；本流程不优先依赖自动 compaction，也不在同一长会话中周期重锚。

## Planning 与批次规则

- Planner 基于语义宽度、状态/时序风险和动态依赖判断 `simple` 或 `complex`，父 Runner 负责重算上下文签名并校验计划。
- 计划必须覆盖全部且仅覆盖 manifest 中的 RSU；拒绝遗漏、未知、重复、乱序、不兼容依赖、普通批次超过 10 个或复杂批次包含多个成员。
- 普通批次目标为 4～6 个，但不足目标是合法的；不得为凑数合并上下文不兼容 RSU。
- Worker 无法可靠处理某 RSU 时返回结构化 `replan-required`，不得通过枚举大量候选掩盖上下文不足。
- Worker 提交前只删除明确重复的候选，不做基于“同一风险”“同一生命周期”或观察层的广义业务合并；跨批候选由父 Runner 在模块汇总阶段按精确重复规则处理。

## 状态、恢复与权限

`generation-state.json` 是唯一共享进度源，记录 Foundation、planning、批次、逐 RSU、finalization、readiness、Worker packet/schema/policy/risk/source 指纹、私有结果哈希和最近错误。父 Runner 独占共享状态提交，使用临时文件、刷新和原子替换；默认语义 Worker 不得调用工具或写任何文件，兼容批次 Worker 也不得写共享状态、最终文件或其他批次输出。

父 Runner 在真正启动批次 Worker 前，原子地把该批次及其活动 RSU 标记为 `running` 并记录 owner PID/run ID。`batch-results/<BATCH-ID>/result.json` 的批次状态可为 `draft`、`partial`、`complete`、`replan-required`，逐 RSU 状态可为 `draft`、`complete`、`failed`、`replan-required`；其中 `failed` 必须保留具体原因并回到可重试状态，不阻止同批已完成成员先提交。

- `pending` / `prepared`：等待计划或执行。
- `running`：仅在受管阶段实际运行期间有效；重启发现无活跃进程时恢复为可重试状态。
- `validated`：来源、输入、输出、格式和授权范围已验证。
- `failed`：阶段失败，可按 Runner 的有限重试或人工修复规则处置。
- `replan-required`：只重新规划受影响的未完成工作，保留来源未变的 validated 结果。
- `blocked` / `stale`：存在未闭合依赖或来源变化；必须先修复上游或显式 refresh，不能伪造完成。

旧状态由脚本备份并受控迁移；旧会话 ID 不复用。`reopen_rsu.py` 只失效目标 RSU、所属批次及下游 finalization/readiness，保留不相关且哈希一致的结果。不要手工把状态改为 validated。

Runner 重启时只依据 JSON 状态、私有语义结果、计划和文件哈希恢复，不扫描历史日志。默认基线只有 packet、业务输入、policy、schema、risk 和 source 指纹全部一致时才复用；任一变化都使私有结果失效，但旧正式文件在新结果完成全部校验前保持不变。兼容批次路径仍按旧 owner、私有 result 和哈希恢复。

## 模块测试点汇总与 readiness

- module assembly 只基于已验证候选做精确重复去重和稳定 `TP-ID` 编号，不从原文补造候选，也不按目标数量增删测试点。默认一个候选对应一个最终测试点；仅测试项、完整测试点和备注忽略排版空白后均完全相同的候选允许自动合并。旧三列仅兼容读取，不用于新生成。
- 并行完成顺序不能影响最终编号；顺序由 RSU map 和候选局部顺序决定。
- 若候选本身混入多个可独立验证的需求行为，停止模块汇总并重新打开对应 RSU，而不是在父 Runner 中绕过局部追溯直接改写语义。
- readiness 只审查生成可执行测试用例还缺的测试数据、环境、配置和可观察性输入。默认开发与测试并行；可在执行时绑定的参数、常规 Network/日志/文件/数据观察方式不得形成低价值 CIQ。`test-point-ready` Data Closure 只触发重新审查，不自动等于 `blocked-input` 或必须存在 CIQ。
- 测试点生成完成不依赖 readiness；只有用户准备进入测试用例生成时，才要求 readiness 整体结果为 `ready`。

## 可靠性与边界

planning、batch、finalization 和 readiness 均受心跳、watchdog、重复工具动作检测、瞬时错误有限重试、确定性校验修复、模块锁、全局 slot 和结构化 telemetry 保护。暂不增加单 RSU 熔断或会话级熔断。

已经在本 Skill 的 AI Worker 内执行时不得递归启动 Runner。需要连续执行时由外层普通终端启动；Worker 只完成分配阶段并停止，也不得自动回答 `Q-ID` 或 `CIQ-ID`。
