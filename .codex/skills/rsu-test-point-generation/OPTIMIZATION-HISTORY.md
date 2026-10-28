# RSU 测试点生成 Skill 优化记录

本文记录 `rsu-test-point-generation` 的功能演进、运行中发现的缺陷、修复方案、最终能力和验证结果。它用于回答“为什么这样设计、某个行为何时改变、问题实际修在哪里”，不替代 [SKILL.md](./SKILL.md) 的执行约束或 [README.md](./README.md) 的使用说明。

## 维护规则

- 功能新增、缺陷修复、默认值变化、兼容性变化或重要使用约束都要追加记录。
- 不覆盖或删除旧行；后续若调整同一问题，应新增一行并在“关联”中引用旧编号。
- “类型”区分 `需求`、`缺陷`、`安全性`、`兼容性`、`文档` 和 `关联上游修复`。
- “归属”明确实际修改位于当前 Skill、上游 Skill、模块产物还是仅为使用方式，避免把运行现场问题错误归因给 runner。
- 验证应写实际执行过的测试或产物检查；没有自动验证时明确写“人工确认”，不填模糊的“已验证”。
- 日期采用仓库所在时区的自然日；本文首次建立时，已回填本次会话中完成或确认的优化。

## RSU-OPT-051

| Date | Type | Symptom / Cause | Fix / Decision | Verification / Impact |
|---|---|---|---|---|
| 2026-10-15 | Defect / Baseline recovery and Fork result isolation | The complex Fork merge path could persist merged semantics, including Fork candidates, back into `worker-results/baseline.json` while the state hash pointed to that file. On recovery, validating the merged result with Baseline-only authorization rejected valid Context references owned by a complex Scope; relaxing validation would allow contaminated Baseline reuse. | Keep Baseline-only Worker output in `worker-results/baseline.json` and persist merged output separately in `worker-results/merged.json`; record independent paths and hashes. Revalidate Baseline-only authorization before reuse so results written by older runners are rejected and regenerated. Synchronize README, Runner contract, and regression coverage. | Pending the targeted/full tests, compilation, CLI, and quick validation in this run. |

## RSU-OPT-049

| 日期 | 类型 | 现象/原因 | 修复与决策 | 验证/影响 |
|---|---|---|---|---|
| 2026-10-15 | 缺陷 / 需求来源边界 | MOD-04 旧测试点把 Data Closure 中的销量表、字段与金额计算路径写成独立验收点。生成策略要求覆盖输入包支持的内容，却没有明确限定业务承诺必须由需求原文或用户确认规则授权，且结构校验不能发现这种语义越界。 | 在 Baseline 与复杂 Fork 共用的 Worker policy、生成规则、Skill 核心不变量和 README 中明确：需求/已确认规则定义验收范围；Context/Data Closure 只能澄清、限定和追溯；Data Closure 的 schema、关联、SQL/计算实现和造数方法不得单独生成测试点；候选须能追溯到直接支持业务行为的权威条款，且以业务语言表述。策略随 packet 编译并参与指纹，旧结果因此失效。增加 Baseline/Fork packet 回归断言。 | Skill 全量测试 171 项通过；`compileall`、Runner `--help` 通过；MOD-04 `--dry-run` 前置分析 errors=0/warnings=0，确认策略变更使 8 个旧 RSU 全部 stale，并由 Runner 回收无效 PID 的旧模块锁。 |

## RSU-OPT-050

| 日期 | 类型 | 现象/原因 | 修复与决策 | 验证/影响 |
|---|---|---|---|---|
| 2026-10-15 | 缺陷 / Readiness 门禁边界 | MOD-04 readiness 将实际隔离环境、账号、匹配样本和数据修改授权尚未确认，误判为 11 个数据库 TP 无法生成用例。通用规则虽允许执行时绑定，却另要求预先确认访问条件可用；Data Closure 扩展也未区分“方案能否设计”与“执行资源是否已交付”。 | 统一规则：环境、凭据/权限、具体样本和运行实例若不改变用例设计，写入前置条件或执行时绑定，不因未开通/未验证而阻断。数据库 TP 仍须具备语义数据画像、查询/断言口径及安全准备与清理恢复方案；缺失这些设计契约或无法安全判定时才创建 CIQ。生产造数和未授权修改明确禁止。同步 Data Closure 扩展、输出契约及 README。 | 验证记录将在本修复完成后补充；Skill 规则一致性回归、全量单测、编译、CLI 与 MOD-04 readiness Runner 结果以本次实际执行结果更新。 | 

## RSU-OPT-027

| 日期 | 类型 | 现象/原因 | 修复与决策 | 验证/影响 |
|---|---|---|---|---|
| 2026-09-14 | 兼容性 / 架构 | `legacy-resume` 是重构前按 RSU 顺序复用同一长会话的旧拓扑；它会累积历史上下文、工具输出和会话 token，且与 foundation/fork 的隔离目标冲突。 | 移除 `legacy-resume` CLI 选项；`foundation-fork` 成为默认且唯一流水线架构。保留 `--session-mode isolated` 作为手动/兼容路径：每个 RSU 使用全新会话、完整输入并按顺序执行。 | CLI 默认解析、旧参数拒绝、foundation/isolated 路由测试通过；真实对比数据记录于 OpenSpec `acceptance-report.md`：旧拓扑约 29.7 分钟，foundation/fork 约 34.3 分钟，但 RSU 阶段由约 19.1 分钟降至约 11.2 分钟。 |

## RSU-OPT-028

| 日期 | 类型 | 现象/原因 | 修复与决策 | 验证/影响 |
|---|---|---|---|---|
| 2026-09-15 | 缺陷 / 当前 Skill Runner | 真实基准恢复运行暴露两个问题：`module-baseline` 的快速恢复会用本次 0 调用指标覆盖首次生成指标；`foundation-fork` 在接纳已有私有 Batch 结果前无条件建立新 Foundation，导致恢复时重复付费调用，且无法复用已验证的 Foundation 会话。 | Adaptive 指标保留首次生成数据，恢复调用单独追加到 `resume_history`/`last_resume`；兼容拓扑先验证并提交合法私有 Batch 结果，仅在仍需 Planning、Batch、Finalization 或 Readiness AI 时建立 Foundation。若状态中的 Foundation 已 validated，且来源指纹、输入路径和输入哈希均一致，则恢复保存的 thread ID 并从它继续 fork。 | `test_adaptive_runner.py` 10 项测试通过；`test_v2_scheduler.py` 与 `test_foundation_fork_runner.py` 合计 9 项测试通过；修改脚本编译通过。恢复判断继续只依赖 JSON 状态、私有结果与哈希，不读取历史日志推断进度。 |

## RSU-OPT-029

| 日期 | 类型 | 现象/原因 | 修复与决策 | 验证/影响 |
|---|---|---|---|---|
| 2026-09-16 | 缺陷 / 自适应路由与父提交 | 两组真实对比发现：小而复杂的文件核查虽然覆盖 9/9 RSU，但 baseline 将 IN15、IN17 轮询、状态映射、超时、重试和并发生命周期一对一保留为 13 个 TP，且因未自报 `needs-fork` 以 0 fork 完成；大而简单的任务列表则不需要额外收敛。兼容拓扑 Readiness 还出现 AI 误跑校验器并写共享状态，导致有效输出被父 Runner 拒绝。自适应指标原先也只累计 baseline turn，未包含实际 fork 成本。 | 增加基于稳定风险事实与候选归并状态的门禁：至少两个 RSU/候选共同构成外部提交或异步轮询，并同时存在超时、重试、状态迁移或并发/幂等，且相关候选仍全部 `retained` 时，创建一次 `semantic-fork-v1` 有界收敛；已有 `merged` 证据、普通筛选/展示/静态状态矩阵不触发。该 fork 只能修改最终测试点、覆盖矩阵和私有结果，候选及范围外测试意图受父 Runner 校验。所有 AI 阶段明确禁止运行准备/校验脚本；误写共享状态时父 Runner 回滚后自行校验。Adaptive telemetry 累计 baseline 与所有实际 fork 的工具调用和 token。 | 真实私有产物只读路由回放：文件核查新拓扑触发 1 个 scope，文件核查旧拓扑和任务列表新旧拓扑均为 0；131 项 Skill 测试通过。正式模块产物哈希未因基准或修复改变。 |

## RSU-OPT-030

| 日期 | 类型 | 现象/原因 | 修复与决策 | 验证/影响 |
|---|---|---|---|---|
| 2026-09-16 | 架构、性能与质量 / 当前 Skill Runner | `module-baseline` 虽只有一个 AI turn，但父提示仍让通用 Agent 重新加载 Skill、分段读取 `baseline-input.md`、检查 Runner/validator 实现、运行准备/校验脚本并直接编写多份 Markdown。真实基准因此产生 58～63 次工具调用；现有风险门禁还要求至少两个候选和两个 RSU，漏掉单 RSU 内的异步恢复或并发边界。 | 把默认子会话改为自包含零工具语义 Worker：父 Runner编译完整业务输入、精简 policy、风险事实、当前来源指纹和精确 JSON Schema，通过 stdin 一次发送并用 `--output-schema` 约束响应；子 Worker 只返回语义 JSON，任何工具调用均拒绝发布。Candidate/TP 编号、Markdown、状态和确定性校验全部回到父进程。风险路由改为相连 scope，可识别单 RSU 与跨 RSU 生命周期；定向 fork 同样使用自包含 packet 和结构化 patch。恢复指纹覆盖 packet/business/policy/schema/risk/source，超预算显式记录 context-pressure，不回退路径读取。 | 142 项 Skill 测试、全部 Python 脚本编译、Runner `--help`、Skill quick validation 和 OpenSpec strict validation 均通过。非付费真实模块 dry-run 生成的文件核查 packet 为 81,883 bytes/9 RSU，任务列表 packet 为 97,014 bytes/12 RSU；旧真实候选路由重放中，文件核查形成 1 个相连高风险 scope，覆盖 8 个 RSU，任务列表形成 0 个 scope。未执行新的付费模型性能基准，不宣称具体墙钟或 token 改善。 |

## RSU-OPT-031

| 日期 | 类型 | 现象/原因 | 修复与决策 | 验证/影响 |
|---|---|---|---|---|
| 2026-09-17 | 兼容性 / 当前 Skill Runner | 使用本地默认 `gpt-5.6-luna` 验证 `module-baseline` 时，CC Switch/Responses 适配链路拒绝动态输出 Schema：根属性和状态字段仅使用 `const`/`enum`，未显式声明 `type`；上游严格校验返回 `Invalid schema ... properties.schema ... must have a type key`，baseline 尚未进入业务生成。 | 在 `adaptive_worker.py` 生成的 baseline/review Schema 中，为所有 `const`/`enum` 属性补充 `type: string`；增加回归测试，递归保证对象属性 Schema 均显式声明类型。保留 JSON Schema 语义和 Runner 模型继承逻辑，不改用 Chat Completions。 | `test_adaptive_worker.py` 11 项通过；待使用修复后的 Schema 重新执行一次最小 `module-baseline` 和文件核查模块验证，以确认代理链路继续通过后续结构化输出校验。 |

## 优化与修复历史

| 编号 | 日期 | 类型 / 归属 | 问题或需求 | 修复或实现方案 | 实现能力 / 结果 | 验证 | 相关文件 |
|---|---|---|---|---|---|---|---|
| RSU-OPT-030 | 2026-09-16 | 架构、性能与质量 / 当前 Skill Runner | 默认 baseline 子会话仍是会读文件、查脚本、跑校验并写 Markdown 的通用 Agent，工具调用和耗时偏高，且双候选/双 RSU 门禁漏掉单 RSU 高风险生命周期。 | 改为父 Runner 编译 stdin 自包含 packet + JSON Schema、子 Worker 零工具返回语义 JSON、父进程渲染校验；新增相连的单/跨 RSU 风险 scope 与结构化 fork patch。默认主链中旧的路径式自主 baseline 与 Markdown semantic-fork 实现已移除，兼容能力只由独立 `foundation-fork` 拓扑提供。 | 普通模块只需一次语义生成；复杂范围仍获得独立复核；恢复依赖完整指纹和私有结果而非日志；超预算显式停止。 | 142 项 Skill 测试通过；全部 Python 脚本编译通过；Runner `--help`、Skill quick validation、OpenSpec strict validation 通过。非付费真实模块 packet dry-run：文件核查 81,883 bytes/9 RSU，任务列表 97,014 bytes/12 RSU；路由重放：文件核查 13 个候选/13 个最终意图形成 1 个 scope，覆盖 RSU-001～RSU-007、RSU-009，任务列表 15 个候选/15 个最终意图形成 0 个 scope。未运行新的付费模型基准，因此不宣称墙钟或 token 改善。 | [adaptive_worker.py](./scripts/adaptive_worker.py)、[adaptive_runner.py](./scripts/adaptive_runner.py)、[run_generation.py](./scripts/run_generation.py)、[test_adaptive_worker.py](./tests/test_adaptive_worker.py)、[runner.md](./references/runner.md)、[input-contract.md](./references/input-contract.md)、[output-contract.md](./references/output-contract.md) |
| RSU-OPT-001 | 2026-09-02 | 需求 / 当前 Skill | 逐 RSU 生成仅靠对话约定容易跳号、漏依赖或在一个 turn 中连续处理多个 RSU；局部候选也缺少稳定的最终收敛过程。 | 建立脚本控制的三阶段流水线：初始化与逐 RSU 输入物化/候选校验、全模块收敛、测试用例输入就绪性审查；用 `generation-state.json`、固定模板和 SHA-256 作为控制面。 | 实现严格按 map 顺序、每 turn 一个 RSU、`0～N` 候选、输入防漂移、最终 `TP-ID`、覆盖矩阵和 readiness 交接。 | 全量 Skill 单元测试；Skill 结构快速校验。 | [SKILL.md](./SKILL.md)、[input-contract.md](./references/input-contract.md)、[generation-rules.md](./references/generation-rules.md)、[output-contract.md](./references/output-contract.md)、[finalization-rules.md](./references/finalization-rules.md)、[case-readiness-rules.md](./references/case-readiness-rules.md)、`scripts/*.py` |
| RSU-OPT-002 | 2026-09-02 | 需求 / 当前 Skill Runner | 人工模式每生成完一个 RSU 都要再次输入“继续下一个”，大量 RSU 或多模块时需要持续值守。 | 新增外层 `run_generation.py`。每个阶段单独启动一个 Codex turn，结束后重新读取状态；只有预期 RSU 恰好变为 `validated` 才继续，全部 RSU 后再分别运行收敛和 readiness。 | 可以从 PowerShell 自动连续执行剩余 RSU，直到模块成功或出现需人工处理的终止条件；不依赖解析 AI 自述判断完成。 | Runner 单元测试覆盖参数、状态推进、阶段顺序、停止条件和日志；本会话实际用于多模块批跑。 | [run_generation.py](./scripts/run_generation.py)、[test_run_generation.py](./tests/test_run_generation.py)、[runner.md](./references/runner.md) |
| RSU-OPT-003 | 2026-09-02 | 安全性 / 当前 Skill Runner | 多个终端可能误启动同一模块，造成状态、输入和候选文件并发写入；同时需要允许不同模块并行。 | 在每个模块的输出目录使用 `.generation-runner.lock` 互斥；session、状态和日志均按模块隔离，不设置全项目级锁。 | 不同模块可在多个 PowerShell 窗口并行；同一模块的第二个 runner 会拒绝启动。某模块 blocked/错误不要求停止其他模块进程。 | Runner 锁相关单元测试；本会话按独立模块进程进行批量运行。 | [run_generation.py](./scripts/run_generation.py)、[test_run_generation.py](./tests/test_run_generation.py)、[runner.md](./references/runner.md) |
| RSU-OPT-004 | 2026-09-03 | 缺陷 / 当前 Skill 与上游契约 | 实际生成时发现可观察的父级行为可能只出现在 RSU map 的 `父级条件（原文）`，下游若把它只当普通前置条件，会漏掉创建、跳转、状态变化、提示或展示行为。 | 强化父级来源覆盖：准备阶段同时审查父级条件和原文；高置信可观察父级行为必须完整进入当前或支持 RSU 的 `原文内容`；候选“推导依据”必须分别记录非空父级条件和原文内容；否则阻塞并回到上游修 map。 | 下游不再静默丢失父级业务行为，也不能靠候选临时补造上游未映射的需求。 | 新增 `test_parent_source_coverage.py`；当前 Skill 全量单元测试通过。 | [SKILL.md](./SKILL.md)、[input-contract.md](./references/input-contract.md)、[generation-rules.md](./references/generation-rules.md)、[output-contract.md](./references/output-contract.md)、[common.py](./scripts/common.py)、[test_parent_source_coverage.py](./tests/test_parent_source_coverage.py) |
| RSU-OPT-005 | 2026-09-03 | 兼容性 / 当前 Skill Runner | Windows 控制台默认编码可能不是 UTF-8。供应商返回中文错误时，runner 自己可能先触发 `UnicodeEncodeError`，掩盖真正的 Codex/供应商错误并破坏诊断与重试。 | runner 启动时将 stdout/stderr 重新配置为 UTF-8，并让 Codex 子进程及日志链路按 UTF-8 处理，无法编码的字符使用可恢复策略。 | 中文供应商错误可以稳定写入终端和日志，错误分类与后续重试不再被控制台编码异常打断。 | Runner 单元测试覆盖编码配置；Windows 环境运行日志检查。 | [run_generation.py](./scripts/run_generation.py)、[test_run_generation.py](./tests/test_run_generation.py) |
| RSU-OPT-006 | 2026-09-03 | 缺陷 / 当前 Skill Runner | Codex CLI 内部的供应商连接重试耗尽后直接非零退出，runner 原来没有第二层重试，导致可恢复的模块过早停止。 | 增加 runner 级错误分类和有界指数退避；识别 HTTP 408/425/429/部分 5xx、连接/代理故障与流中断。每次重试前重新读状态并检查是否已完成、RSU 顺序和进度是否仍可安全恢复；quota、余额不足和账单硬限制优先判为不可重试。 | 默认额外重试 3 次，等待约 5/10/20 秒且单次不超过 60 秒；可配置关闭或调整。完成状态不会因进程非零而重复生成。 | Runner 单元测试覆盖瞬时/非瞬时分类、重试上限、退避、非零但阶段已完成、状态不安全时拒绝重试；全量 runner 测试通过。 | [run_generation.py](./scripts/run_generation.py)、[test_run_generation.py](./tests/test_run_generation.py)、[runner.md](./references/runner.md) |
| RSU-OPT-007 | 2026-09-03 | 关联上游修复 / `module-requirement-preanalysis` 与 02 模块产物 | `MOD-02-03-02-生成计奖审核任务` 的上游 map 原先只有 7 个 RSU，父句中的弹窗、确认校验和创建/跳转等可观察行为没有被完整承载，触发下游父级行为保护。根因位于前置分析产物及其校验覆盖，不是 runner 调度错误。 | 修正上游语义拆分与校验：区分独立契约、复合契约、父级可观察行为、结构容器和视觉占位；将漏掉的行为补入映射，02 模块由 7 个 RSU 补为 9 个，并重新同步相关 Q/FC/DC、manifest 和测试点状态。 | 02 模块 RSU-001～RSU-009 能完整承载弹窗、校验、创建成功、待核查状态、详情跳转与展示契约；下游可在不补造需求的前提下继续。 | 上游 `test_parent_behavior_validation.py`；上游 Skill 校验；02 模块 preanalysis 校验并重新物化至 RSU-009。 | [上游 SKILL.md](../module-requirement-preanalysis/SKILL.md)、[上游语义拆分协议](../module-requirement-preanalysis/references/rsu-semantic-partitioning.md)、[上游校验器](../module-requirement-preanalysis/scripts/validate_preanalysis.py)、[上游测试](../module-requirement-preanalysis/tests/test_parent_behavior_validation.py)、`../../../modules/MOD-02-03-计奖审核（增）/MOD-02-03-02-生成计奖审核任务/02-sentence-test-point-map.md` |
| RSU-OPT-008 | 2026-09-03 | 关联上游缺陷修复 / `module-requirement-preanalysis` | Markdown 行尾内联原型图片会把 `image.png` 等 alt 文本混入需求原文归一化，造成 RSU 原文匹配误报；图片占位本身也可能被误当作文字业务契约。 | 在上游 `normalize_source_text` 中先去除 Markdown 图片标记，将图片归为 `visual-placeholder`；补充“内联图片不影响父句原文匹配”的回归测试和拆分规则。 | “校验通过后进入详情页。![image.png](...)”可按文字父句正确匹配，图片保留为视觉来源/问题上下文但不单独生成伪 RSU。 | `test_source_match_ignores_inline_prototype_image` 通过；上游 Skill 校验通过。 | [上游校验器](../module-requirement-preanalysis/scripts/validate_preanalysis.py)、[上游测试](../module-requirement-preanalysis/tests/test_parent_behavior_validation.py)、[上游工作流](../module-requirement-preanalysis/references/workflow.md) |
| RSU-OPT-009 | 2026-09-03 | 需求 / 当前 Skill Runner | 原 runner 每个 RSU 都开启新对话，会重复阅读相同公共上下文，增加时间与算力；用户的手工使用习惯是在同一会话中连续生成整个模块。 | 新增可配置会话策略，并将 `module-session` 设为默认。首阶段捕获 JSONL `thread.started` 的 session ID，后续阶段使用 `codex exec resume`；保留 `isolated` 模式兼容强隔离场景。 | 同一模块的 RSU、全模块收敛和 readiness 可以共享一个会话记忆；不同模块仍使用独立会话。`--session-mode isolated` 可随时恢复旧式逐阶段新会话。 | Runner 单元测试覆盖 session ID 捕获、resume 命令、ID 漂移拒绝、默认/显式模式；全量 runner 测试通过。 | [run_generation.py](./scripts/run_generation.py)、[test_run_generation.py](./tests/test_run_generation.py)、[runner.md](./references/runner.md)、[SKILL.md](./SKILL.md) |
| RSU-OPT-010 | 2026-09-03 | 需求 / 当前 Skill Runner | 单一模块 RSU 很多时，共享会话可能因上下文增长、摘要或压缩而遗忘早期细节；但 Codex CLI 没有稳定的“遗忘事件”可供 runner 精确检测。 | 采用确定性刷新与模型侧自检组合：首项、`stale` 恢复点和每 N 个已验证 RSU 后完整重读当前输入；默认 N=5，可设 0 关闭周期刷新；发现无法准确回忆、上下文压缩迹象或文件/哈希冲突时补读相关资源，仍不确定则完整重读。 | 在保留会话复用收益的同时降低长会话遗漏风险；每个 RSU 的完整输入仍落盘并校验，记忆不会成为新的事实源。 | Runner 单元测试覆盖默认值、刷新周期、stale 和模式差异；prompt 行为检查；全量 runner 测试通过。 | [run_generation.py](./scripts/run_generation.py)、[test_run_generation.py](./tests/test_run_generation.py)、[runner.md](./references/runner.md)、[SKILL.md](./SKILL.md) |
| RSU-OPT-011 | 2026-09-03 | 文档 / 当前 Skill | 模型/profile 是否继承 Desktop、怎样并行多个模块、能否由上层对话驱动 PowerShell、如何恢复和调整两种会话模式等信息只存在于聊天记录，后续会遗忘。 | 新增完整使用手册，明确 CLI 配置来源、PowerShell 示例、全部参数、并行边界、锁、上下文刷新、重试、状态、输出、退出码、恢复方式和递归运行限制；从 `SKILL.md` 增加稳定入口。 | 新用户不依赖历史会话即可配置和运行；当前代码的 `--help` 仍是参数默认值的最终依据。 | 文档相对链接检查；Skill 快速校验；runner `--help` 与参数表逐项核对。 | [README.md](./README.md)、[SKILL.md](./SKILL.md)、[runner.md](./references/runner.md)、[run_generation.py](./scripts/run_generation.py) |
| RSU-OPT-012 | 2026-09-03 | 文档 / 当前 Skill | 多轮优化没有统一、可持续追加的变更记录，无法追溯需求、问题归属、修复方式、最终能力和验证结果。 | 新增本文，使用固定表格回填本次会话的 runner、追溯、Windows、重试、上游 map、图片归一化、会话模式与上下文刷新改动，并规定以后只追加不覆盖。 | 后续可在一个位置查阅“问题/需求 → 实现 → 能力 → 验证 → 文件”的完整链路。 | 人工逐项对照本次会话、脚本、规则、测试和文件时间；文档链接检查。 | [OPTIMIZATION-HISTORY.md](./OPTIMIZATION-HISTORY.md) |
| RSU-OPT-013 | 2026-09-03 | 缺陷与性能 / 当前 Skill、关联上游契约 | FC/DC 卡中的“关联 RSU”和来源证据被递归解释成运行时全文依赖，导致一个 RSU 继承其他 RSU 的全部上下文并反复嵌入整份 PRD/数据库设计。任务列表示例每个输入约 1.516 MB、1.55 万行；isolated 批跑前 5 个 turn 累计约 315 万 input tokens（约 284 万 cached）。该问题不只由 isolated 引起，module-session 也会生成相同大文件并在首项/刷新点重读。 | 将依赖分为三类：固定与当前 RSU 显式动态资源继续完整物化；FC/DC 卡完整物化其聚焦语义；卡内来源证据只记录路径、用途和正文 SHA-256，不展开正文，也不允许直接作为候选 Context Refs。保留卡片关联 RSU 的映射行供跨 RSU 组合，但不再继承这些 RSU 的动态依赖。证据变化仍使输入过期；确需来源原文时必须由上游显式绑定聚焦资源。 | 既保留 isolated 的完整测试点语义、可审计性和变更检测，又消除传递依赖爆炸。任务列表现有 RSU-001～006 的新输入估算由约 1.516 MB 降至约 69～84 KB，减少 94.5%～95.4%；module-session 与 isolated 都受益。旧输入不原地改写；因输入契约/哈希变化，模块下次初始化会把旧 validated/prepared 结果标为 stale 并受控重生成。 | 新增 4 项依赖范围回归测试，覆盖证据不展开、证据哈希触发变化、支持 RSU 不继承依赖、显式资源仍全文物化；当前 Skill 26 项测试通过；真实任务列表 12 个 RSU 只读构包测量。 | [common.py](./scripts/common.py)、[输入契约](./references/input-contract.md)、[生成规则](./references/generation-rules.md)、[输入模板](./assets/templates/rsu-input-data-closure.md.tmpl)、[回归测试](./tests/test_input_dependency_scope.py)、[上游输入契约](../module-requirement-preanalysis/SKILL.md) |
| RSU-OPT-014 | 2026-09-03 | 缺陷 / 当前 Skill | 逐 RSU 模式强化了追溯、上下文和完整断言，却没有同等明确地定义测试点粒度与字段职责，导致模型把前端显隐、后端拒绝、数据库原子性、日志和范围说明保守地合成超长候选；作废模块最终测试点平均 53.3 字，RSU-004 候选平均 79.4 字，并出现可独立失败的结论过度合并。 | 将 `测试点` 明确定义为标题就绪的单一测试意图，详细断言放入 `可观察结果`，追溯/范围说明放入依据列；增加“可分别通过或失败、准备/动作/观察入口不同、无法用一个短标题概括即拆点”的生成自审和收敛门禁；标题建议不超过 40 个非空白字符、硬上限 60，禁止分号、多句及高置信范围说明，并由候选/最终校验器共同检查。 | 恢复模型按测试专业知识先拆意图再写标题的能力，防止句子级生成退化为“一条 RSU 对应一个大段候选”；不新增泛化备注列，保留现有可观察结果和追溯结构。旧产物不原地改写，重新初始化后按新输入契约受控重生成。 | 新增标题质量单元测试；全量 Skill 测试与快速校验；作废任务 RSU-001 隔离试生成对比。 | [SKILL.md](./SKILL.md)、[generation-rules.md](./references/generation-rules.md)、[output-contract.md](./references/output-contract.md)、[finalization-rules.md](./references/finalization-rules.md)、[common.py](./scripts/common.py)、[标题质量测试](./tests/test_test_point_title_quality.py) |
| RSU-OPT-015 | 2026-09-03 | 需求 / 当前 Skill | 最终 `module-test-points.md` 的 `Context Refs` 只有资源 ID，机器可通过上游 map 解析，但人工阅读时缺少类似“引用入口”的路径索引；若手工复制整张上游表又会形成双重事实源和路径漂移。 | 在收敛模板中增加受控的“上下文资源入口”区；最终 TP 与覆盖矩阵全部验证通过后，校验器取最终 `Context Refs` 并集，按上游 map 顺序自动生成 `资源 ID / 可点击文件 / 定位用途`，仅包含实际使用资源。上游 map 继续作为唯一权威来源，自动区不复制正文且禁止手工维护；旧版合法最终文件可在再次校验时自动插入受控区，无需重做收敛。 | 最终测试点文档可独立提供资源路径入口，下游仍按规范化 ID 解析，不增加模型填写负担，不把资源目录复制成第二份配置；重新校验时可确定性重建索引。 | 新增资源索引单元测试，覆盖实际引用过滤、map 顺序、相对可点击路径、单元格转义、幂等替换、空结果、旧文件迁移和残缺标记保护；全量 Skill 测试与快速校验。 | [SKILL.md](./SKILL.md)、[输出契约](./references/output-contract.md)、[收敛规则](./references/finalization-rules.md)、[common.py](./scripts/common.py)、[prepare_finalization.py](./scripts/prepare_finalization.py)、[validate_module_test_points.py](./scripts/validate_module_test_points.py)、[资源索引测试](./tests/test_context_resource_index.py) |
| RSU-OPT-016 | 2026-09-03 | 缺陷 / 当前 Skill 状态恢复 | 全模块收敛规则要求在发现复合候选时回退对应 RSU，但原有脚本没有合法入口；直接修改 `generation-state.json` 会绕过状态契约，删除整个输出目录又会无谓重跑其他 RSU。 | 新增 `reopen_rsu.py`：在上游校验、runner 锁检查和生成状态锁保护下，只允许把指定的 `validated` RSU 改为 `stale`；保留后续合法 RSU，失效收敛/readiness，记录原因及回退前完整状态，旧候选交由下一次准备脚本归档。 | 收敛阶段可确定性地只返工问题 RSU，再由 runner 从该点继续正式生成、校验、收敛和 readiness；无需手改状态或重跑整个模块。 | 新增纯状态转换与 runner 锁回归测试；全量 Skill 单元测试；Skill 快速校验；02 模块 RSU-008 真实恢复验证。 | [reopen_rsu.py](./scripts/reopen_rsu.py)、[test_reopen_rsu.py](./tests/test_reopen_rsu.py)、[SKILL.md](./SKILL.md)、[runner.md](./references/runner.md)、[README.md](./README.md) |
| RSU-OPT-017 | 2026-09-04 | 缺陷 / 当前 Skill Runner | 审计发现 runner 在阶段无输出、工具循环、长时间供应商故障、共享 session 损坏、多模块并发和确定性校验失败时会等待过久、重复返工或过早停止；旧日志也无法准确区分模型耗时、退避、排队和恢复耗时。 | 增加阶段总超时、无 JSONL 事件看门狗、心跳和重复动作检测；将 runner 级瞬时错误重试提升为默认 6 次、15 秒起步且单次最多 300 秒；`module-session` 连续失败达到阈值后支持 `fresh-session`/`isolated`/`stop`；增加跨进程全局 slot 并发上限（默认 3）、死亡 slot 回收、确定性校验有限自动修复（默认 2 回合）；后台读取 JSONL、terminate/kill 兜底并关闭 stdout；写入结构化 `runner-events.jsonl`。 | 供应商瞬时中断可在安全边界内自动恢复；静默/卡死/工具循环不会无限等待；损坏 session 可换新；多模块并行时不会无限冲击同一账户；格式、引用、哈希和覆盖等机械错误可有限修复；阶段耗时可审计。`blocked-input`、`upstream-gap`、待确认、额度硬限制和未知业务错误仍立即交人工处理。 | 新增并通过 watchdog、重复动作、slot 等待/回收、session 恢复、校验修复、CLI help 和停止边界测试；runner 测试通过，Skill 全量测试 56 项通过。 | [run_generation.py](./scripts/run_generation.py)、[test_run_generation.py](./tests/test_run_generation.py)、[README.md](./README.md)、[runner.md](./references/runner.md)、[SKILL.md](./SKILL.md) |
| RSU-OPT-018 | 2026-09-04 | 缺陷 / 当前 Skill | 涉及数据库、落库、事务、SQL、字段或表的测试点若遗漏 Data Closure，后续用例阶段无法稳定准备数据；但仅凭模糊字段名又可能误猜错误的闭包卡。 | 在公共规则中识别明确的数据持久化/架构断言；若测试点中的唯一字段或表标识只匹配一个已物化 DC 卡，则确定性推导并校验其引用；多卡歧义不猜测，仍要求显式绑定。 | 明确数据断言必须有可追溯、已物化的 Data Closure；普通 UI 文案不被误判；模糊标识不会被自动补引用。 | 新增 `test_data_closure.py` 3 项测试通过，并纳入全量 56 项测试。 | [common.py](./scripts/common.py)、[validate_rsu_test_points.py](./scripts/validate_rsu_test_points.py)、[test_data_closure.py](./tests/test_data_closure.py) |
| RSU-OPT-019 | 2026-09-04 | 文档 / 当前 Skill | runner 新增了多个可靠性参数和日志事件，但旧使用手册、Runner 说明仍记录 3 次重试、5/10/20 秒退避和 60 秒上限，容易造成实际运行与文档不一致。 | 同步 `SKILL.md`、`README.md` 和 `references/runner.md`：补齐默认值、看门狗、心跳、会话恢复、全局并发、校验修复、遥测字段、停止边界和排障方法；保留上游 02 map 归因及历史递归输入展开修复说明。 | 文档成为当前行为的可持续入口；使用者可从参数表和日志文件定位恢复、并发及耗时问题，不依赖本次聊天记忆。 | `run_generation.py --help` 与文档逐项核对；Skill 快速校验（`PYTHONUTF8=1`）通过；全量回归测试和编译通过。 | [SKILL.md](./SKILL.md)、[README.md](./README.md)、[runner.md](./references/runner.md)、[OPTIMIZATION-HISTORY.md](./OPTIMIZATION-HISTORY.md) |
| RSU-OPT-020 | 2026-09-04 | 缺陷 / 当前 Skill Runner | 为说明默认全局 slot 路径而在 argparse help 中写入 `%TEMP%`，`argparse` 将 `%T` 误当格式占位符，导致 `run_generation.py --help` 抛出 `ValueError`，实际参数无法查看。 | 将帮助文本中的 `%TEMP%` 转义为 `%%TEMP%%`；运行时解析仍使用系统临时目录和 workdir hash，行为不变。 | Windows 下 `--help` 正常显示所有参数和默认值，文档与真实默认 slot 路径一致。 | 实际执行 `python .../run_generation.py --help` 并检查新增参数输出；编译通过。 | [run_generation.py](./scripts/run_generation.py)、[runner.md](./references/runner.md)、[README.md](./README.md) |
| RSU-OPT-021 | 2026-09-05 | 缺陷 / 当前 Skill Runner | 审计确认 Windows 看门狗终止后只清理 Codex wrapper 可能遗留的子进程；供应商返回 JSON/字段形式的 `retry_after` 也可能未被解析；死亡锁和 slot 在旧 runner 与新 owner 交接时存在误删风险；结构化日志缺少明确的 watchdog 终止事件。 | Windows 终止路径先记录入口进程是否仍在运行：看门狗触发且入口仍存活时才使用 `taskkill /T /F` 清理整个 Codex 子进程树，避免对已退出且可能被复用的 PID 盲目执行；扩展 `Retry-After` 解析支持引号、冒号/等号及 `retry_after_seconds`；模块锁和全局 slot 写入 owner token，释放时要求 PID 与 token 同时匹配；新增 `watchdog_terminated` telemetry 事件，并同步 Runner/README 使用说明。随后补充统一的 pipeline 终态 telemetry：成功、需人工处理、runner 错误和用户中断分别记录 `pipeline_completed`、`pipeline_attention`、`pipeline_failed`、`pipeline_interrupted`，且每个 run 只写一个终态事件。 | 长会话被看门狗打断时会尽力回收仍属于入口进程树的派生 Codex/provider 进程，且不会对已退出入口的旧 PID 盲杀；长退避提示可被正确尊重且受最大等待上限保护；旧 runner 不会删除新 runner 的锁或 slot；耗时审计可直接按事件统计 watchdog 终止，并能区分成功、人工介入、错误和中断。操作系统树外的进程仍不保证可回收。 | 新增并通过 Windows taskkill 模拟、watchdog telemetry、Retry-After 多种格式、锁 owner 交接和四种 pipeline 终态回归测试；本轮针对该修复的 runner 测试 **34 项**通过；Skill 全量测试、编译和快速校验通过。 | [run_generation.py](./scripts/run_generation.py)、[test_run_generation.py](./tests/test_run_generation.py)、[runner.md](./references/runner.md)、[README.md](./README.md) |
| RSU-OPT-022 | 2026-09-05 | 缺陷 / 当前 Skill Runner | 现场实际可能返回中文“供应商连接失败”“网络连接异常”“请求超时”“流式中断”等瞬时错误，原分类器只覆盖英文，导致没有进入 runner 级重试；未预期异常、初始化前失败和 telemetry 写入异常的诊断边界也不够完整，可能出现有错误但没有结构化终态，或日志故障反向掩盖主流程错误。 | 扩展瞬时/非瞬时错误分类，加入常见中文供应商与网络文案，并把“额度不足”归入不可重试；`RunTelemetry.emit()` 将日志写入降级为诊断旁路，写失败只输出 `TELEMETRY_WRITE_FAILED`；`run_pipeline()` 和 `main()` 为普通异常统一记录 `pipeline_failed` 并返回固定错误码；初始化、状态、输出目录或锁创建前通过 `startup-failures/<run>/runner-events.jsonl` 写入 `startup: true` 的启动 telemetry；同步修正文档中的 Windows `taskkill` 安全边界和日志路径说明。 | 中文供应商故障可触发有界退避重试；额度硬限制不会被误重试；任何阶段的未预期错误都有统一终态；初始化失败也能通过 JSONL 定位；telemetry 不再成为主流程的单点故障。 | runner 测试 **66 项**通过；`module-requirement-preanalysis` 测试 **6 项**通过；`tp-test-case-generation` 测试 **44 项**通过；相关脚本编译通过；Skill Creator 快速校验通过。 | [run_generation.py](./scripts/run_generation.py)、[test_run_generation.py](./tests/test_run_generation.py)、[SKILL.md](./SKILL.md)、[README.md](./README.md)、[runner.md](./references/runner.md) |
| RSU-OPT-023 | 2026-09-05 | 缺陷 / 当前 Skill Runner | 终止 Codex wrapper 时若只记录“调用前曾经存活”，优雅终止后仍可能对已退出且已被系统复用的 PID 执行 Windows `taskkill`；这会把安全的进程树清理变成误杀风险。 | `terminate_process_tree()` 在优雅等待后再次检查 `process.poll()`，只有入口进程仍存活时才执行 `taskkill /PID <pid> /T /F`；入口已退出则跳过强制树杀，同时保留跨平台的最终等待/kill 兜底。新增“优雅退出不 taskkill”和“仍存活才 taskkill”两类回归测试，并同步文档与上一条记录的边界描述。 | 看门狗仍可尽力清理活跃入口及其子树，但不会盲目操作已退出入口的旧 PID；树外脱离进程仍明确不保证回收。 | runner 测试 **67 项**通过；相关脚本编译通过；Skill Creator 快速校验通过。 | [run_generation.py](./scripts/run_generation.py)、[test_run_generation.py](./tests/test_run_generation.py)、[runner.md](./references/runner.md)、[README.md](./README.md) |
| RSU-OPT-024 | 2026-09-07 | 缺陷与性能 / 当前 Skill Runner | `module-session` 虽复用了 Codex 会话 ID，但旧策略把每个 `stale` RSU 都当作完整上下文刷新点；当固定来源或映射改动使整批 RSU 过期时，每轮仍重复读取相同的全局、模块、Context 与生成契约，实际接近全量模式并造成明显延迟。 | 为每个 RSU 确定性生成 `session-inputs/<RSU-ID>-delta.md`；首轮、runner 重启、会话恢复与默认每 5 个 RSU 的周期点完整重锚，其他轮次只读取当前/支持 RSU、Q、动态 FC/DC、证据和允许引用集合。新增固定来源指纹，固定资源/契约/manifest 角色变化时停止复用；`stale` 本身不再强制全量读取。模型发现摘要/压缩、无法准确回忆或锚点冲突时仍须主动补读完整输入。 | 共享会话现在真正执行文件级增量读取，同时保留每个 RSU 的完整 `INPUT_FILE`、业务哈希、防漂移与独立复现能力；动态变更不会漏读，固定来源变化和新会话不会错误复用旧上下文。 | 新增增量包正文范围、动态/证据变化、固定来源指纹和 stale 刷新策略回归测试；全量 Skill 单元测试与真实模块构包测量见本次运行记录；脚本编译和 Skill Creator 快速校验。 | [common.py](./scripts/common.py)、[prepare_next_rsu.py](./scripts/prepare_next_rsu.py)、[run_generation.py](./scripts/run_generation.py)、[test_input_dependency_scope.py](./tests/test_input_dependency_scope.py)、[test_run_generation.py](./tests/test_run_generation.py)、[input-contract.md](./references/input-contract.md)、[runner.md](./references/runner.md)、[README.md](./README.md)、[SKILL.md](./SKILL.md) |
| RSU-OPT-025 | 2026-09-10 | 架构、性能与质量 / 当前 Skill Runner | 顺序 `resume` 让后续 RSU 继承兄弟消息、工具调用和候选输出，周期重锚不能阻止会话历史增长；每 RSU 单独执行又不能利用共同固定上下文。旧“任一状态、错误码或观察差异即可拆点”的规则还会诱导候选膨胀。 | 将默认 `module-session` 升级为“模块 Foundation + planning/batch/finalization/readiness 独立 fork”，引入一次性复杂度与上下文签名规划、普通 RSU 4～6 个目标且最多 10 个组批、复杂 RSU 单批、有界并发和父 Runner 独占提交；状态升级为 schema 4 / state-v2，旧状态备份迁移且旧 session ID 不复用；保留 `--context-refresh-interval` 仅作弃用兼容。Worker 只写私有 staging/result，父 Runner 在启动前原子写 `running`，重启优先接纳合法完整/部分结果、仅重跑剩余成员并隔离非法结果。候选改为合法 `0～N`，只有独立风险、不可合并主要触发、独立可判结果、独立回归价值四项全部满足才拆点，多观察层和状态/错误码默认合并或下沉到用例场景。 | 兄弟批次历史从拓扑上隔离，固定来源由 Foundation 复用，动态事实仍通过文件与哈希锚定；并发可降低模块墙钟时间，但不承诺 cached token 归零。恢复不读取历史日志，也不优先依赖触发时机不可控的自动 compaction。finalization/readiness 使用独立轻量 fork；当前按用户决定暂不增加单 RSU 熔断和会话级熔断。 | 会话适配、计划、上下文签名、状态迁移、原子写入、并发权限、越权检测、部分提交/中断恢复、replan/reopen、候选质量与最终阶段回归测试；最终全量数量和真实模块性能对比以本次变更验收记录为准。 | [SKILL.md](./SKILL.md)、[README.md](./README.md)、[run_generation.py](./scripts/run_generation.py)、[common.py](./scripts/common.py)、[prepare_next_batch.py](./scripts/prepare_next_batch.py)、[validate_batch_candidates.py](./scripts/validate_batch_candidates.py)、[runner.md](./references/runner.md)、[generation-rules.md](./references/generation-rules.md)、[finalization-rules.md](./references/finalization-rules.md)、[test_foundation_fork_runner.py](./tests/test_foundation_fork_runner.py)、[test_generation_plan.py](./tests/test_generation_plan.py)、[test_batch_workflow.py](./tests/test_batch_workflow.py)、[test_candidate_quality.py](./tests/test_candidate_quality.py) |
| RSU-OPT-026 | 2026-09-11 | 缺陷与验证 / 当前 Skill Runner | v2 完整调度路径的 telemetry 使用了未初始化的 `recovered_batches`，原有测试偏重组件和 legacy 兼容路径，未真正走完并发 v2 pipeline；来源失效传播和局部 replan 也缺少直接状态转换证据；实现还提前把未完成真实模块验收的新拓扑设成了 CLI 默认。 | 在模块锁内、读取调度快照前恢复陈旧 running 批次并初始化 `recovered_batches`；新增 v2 已完成短路、并发乱序完成但稳定提交、模板渲染后 JSON 解析、固定来源变化失效 foundation/planning/batches、局部 replan 隔离受影响 RSU 且保留其他 validated 结果的回归测试；增加 `--pipeline-architecture` 上线门禁，验收前 CLI 默认保持 `legacy-resume`，新架构必须显式选择 `foundation-fork`。 | v2 调度可完整经过 batch、finalization 和 readiness；恢复顺序在锁内确定；来源变化及 replan 的状态传播可直接审计。正式模块产物未被修改，未验收架构不会被默认用于正式执行。 | 107 项单元测试按测试文件分组全部通过；全部 Python 脚本编译通过；`run_generation.py --help`、本机 Codex CLI 0.153.4 的 `codex exec fork --help` 与 `openspec validate refactor-rsu-test-point-runner --strict` 通过。真实模块副本的新旧性能和候选质量对比仍待验收，不在此记录中宣称完成。 | [run_generation.py](./scripts/run_generation.py)、[test_v2_scheduler.py](./tests/test_v2_scheduler.py)、[test_input_dependency_scope.py](./tests/test_input_dependency_scope.py)、[test_replan_generation.py](./tests/test_replan_generation.py)、[OpenSpec tasks](../../../openspec/changes/refactor-rsu-test-point-runner/tasks.md) |
| RSU-OPT-027 | 2026-09-11 | 缺陷与效率 / 当前 Skill readiness | 真实模块验收中 readiness 把每个 `test-point-ready` Data Closure 机械判为必须存在 CIQ，并把 pending 回填列锁死为中文“未提供”；三个等价占位错误因校验器逐条 fail-fast 连续消耗两次模型修复后仍失败。该行为既违背“执行时可绑定不阻断”，又把语义正确的中英文占位当作格式错误。 | 删除 `test-point-ready => 必须 pending/answered CIQ` 的确定性硬编码，只保留 `blocked` 闭包硬门禁；统一要求按五项 CIQ 准入和反向自审判断真实缺口；pending 接受语义明确的中英文未回答占位且大小写不敏感，answered 仍要求实质答案；在 v2 readiness 提示中明确发版后字段核对、样本 ID、SQL 参数和可执行时绑定信息不自动阻断。 | Readiness 不再因上游状态标签或单一中文格式制造低价值问题，也不会为多个等价占位逐项浪费模型修复回合；真正缺少不可替代账号、访问能力或数据准备方法时仍可生成 CIQ。 | 新增 pending 等价占位与实质答案分类测试；全量测试、真实模块续跑和最终验收结果见本次 OpenSpec 验收记录。 | [validate_case_readiness.py](./scripts/validate_case_readiness.py)、[case-readiness-rules.md](./references/case-readiness-rules.md)、[data-closure-readiness-rules.md](./references/data-closure-readiness-rules.md)、[data-closure-output-contract.md](./references/data-closure-output-contract.md)、[run_generation.py](./scripts/run_generation.py)、[test_case_readiness_validation.py](./tests/test_case_readiness_validation.py) |

## 本次会话回填范围

## RSU-OPT-032

| 日期 | 类型 | 现象/原因 | 修复与决策 | 验证/影响 |
|---|---|---|---|---|
| 2026-09-17 | 缺陷 / Responses 兼容与输出契约 | 使用本地 `gpt-5.6-luna` 的 `module-baseline` Worker 能正常完成 Responses 请求，但首个候选只返回 `CTX`/局部卡片，遗漏输出契约要求的全部固定资源引用（通常为 `SRC-GLOBAL`、`SRC-MOD`、`CTX`），被父 Runner 的确定性校验拒绝。原因是 Worker packet 的生成策略只笼统要求引用上下文，没有把固定引用的硬性规则写成显式指令。 | 在 `adaptive_worker.py` 的 Worker 策略中明确：每个候选的 `context_refs` 必须包含 packet `Required Context Refs` 的全部精确 ID，再追加实际使用的局部资源；`data_closure_refs` 必须同时出现在 `context_refs`，不得使用别名或省略固定来源。保留父 Runner 校验，不对模型结果静默补引用。 | Responses Schema 兼容错误已消失；补强后重新运行验证。该修复不改变候选数量或业务语义，只降低因格式契约遗漏导致的无效重跑。 |

## RSU-OPT-033

| 日期 | 类型 | 现象/原因 | 修复与决策 | 验证/影响 |
|---|---|---|---|---|
| 2026-09-17 | 缺陷 / 基线跨 RSU 归属 | `module-baseline` Worker 正确把 IN17 轮询与结果映射、查询超时与重试等连续行为合并为跨 RSU 候选，但父校验器要求 `candidate_keys` 只能出现在 `primary_rsu` 行，与“一个候选可覆盖多个 RSU”的基线规则冲突。 | 保留单一 `primary_rsu` 作为稳定归属；允许候选在其 `source_rsus` 声明的其他 RSU 行中列出，仍拒绝列入未声明的 RSU。新增跨 RSU 归属回归测试。 | Skill 全量测试 144 项通过，避免把合理的跨 RSU 合并误判为 Runner 失败；不放宽未知 RSU、Primary/Source 校验。 |

## RSU-OPT-034

| 日期 | 类型 | 现象/原因 | 修复与决策 | 验证/影响 |
|---|---|---|---|---|
| 2026-09-17 | 兼容 / Codex CLI 选择 | Runner 默认以 `codex` 解析 PATH，实际命中了旧 npm 全局 CLI（0.153.4），而桌面本地配置对应的 CLI 为版本化安装（0.154.0-alpha.6.2）。在 `gpt-5.6-luna` baseline 验证中旧 CLI 出现 `stream disconnected before completion: Upstream request failed`，无法区分模型/协议兼容性。 | `resolve_codex_binary("codex")` 先采用有效的 `CODEX_CLI_PATH`；未导出该变量时自动探测 `%LOCALAPPDATA%/OpenAI/Codex/bin/*/codex.exe` 的最新版本；均不存在时才回退 PATH。显式传入其他二进制路径仍保持原行为，Runner 不硬编码模型或 API 路径。 | 新增 CLI 选择回归测试；后续验证可确认实际使用的 CLI 版本，避免旧全局二进制掩盖本地模型配置。 |

## RSU-OPT-035

| 日期 | 类型 | 现象/原因 | 修复与决策 | 验证/影响 |
|---|---|---|---|---|
| 2026-09-17 | 缺陷 / 语义追溯契约 | `gpt-5.6-luna` baseline 与 review 能生成业务候选，但 `derivation` 只写“RSU-xxx规定……”，未显式记录 `原文内容：`（及适用时的 `父级条件：`），被父 Runner 的输出契约拒绝。模型提示只强调上下文引用，未重复该硬性追溯标签要求。 | 在 baseline/review Worker 共同提示中加入强制追溯规则：每个候选 `derivation` 和零候选理由必须具体包含 `原文内容：`；当前 RSU 有父级条件时同时包含 `父级条件：`，不得只写 RSU 编号或泛化表述。保留父校验，不静默改写模型结果。 | 新增 Worker 提示回归测试；下一次重跑应直接满足输出契约，避免在已完成 baseline/review 后才因格式追溯失败。 |

## RSU-OPT-036

| 日期 | 类型 | 现象/原因 | 修复与决策 | 验证/影响 |
|---|---|---|---|---|
| 2026-09-17 | 缺陷 / 基线 RSU 双向归属 | `gpt-5.6-luna` 文件核查基线把 `CAND-FILE-AUTH-LOG` 列入 RSU-003，但候选 `source_rsus` 未声明 RSU-003，触发父 Runner 的 fail-closed 校验。候选归属与 RSU disposition 需要显式双向约束，不能依赖模型自行推断。 | 在 baseline/review Worker 策略中加入双向归属硬约束：RSU 只能列出其属于候选 `source_rsus` 的 key；跨 RSU 候选必须在 `source_rsus` 和所有对应 disposition 中完整列出；不得为补齐映射而虚构 RSU。保留确定性父校验，不静默修正候选。 | 后续以全新输出目录重跑文件核查模块；目标是不再出现 `outside source_rsus`，同时保留对未知 RSU 和遗漏覆盖的拒绝。 |

## RSU-OPT-037

| 日期 | 类型 | 现象/原因 | 修复与决策 | 验证/影响 |
|---|---|---|---|---|
| 2026-09-17 | 缺陷 / 默认拓扑语义 | `module-baseline` 被错误实现为先生成全模块候选、再从候选图检测复杂范围，Fork 只做后置 review；复杂 RSU 因而可能不进入 Fork，权限、日志、并发等动态资源也可能静默遗漏。 | 恢复生成前 simple/complex 路由：Baseline 只生成简单 RSU；复杂 RSU 必须零候选并进入唯一 `complex_scopes`；Fork 改为从零首次生成并显式接收 Scope 专属 FC/Q/DC 正文。新增 `context_dispositions` 覆盖账本，逐项强制处置所有非固定 FC/Q/DC。保留自包含零工具 Worker、JSON 状态和父 Runner 确定性渲染，不恢复旧多阶段 Foundation 流水线。 | Schema/packet 升级到 v3/v2 以禁止复用旧 semantic-review 结果；父校验拒绝复杂 RSU 提前生成候选、Scope 重叠/遗漏、动态资源未处置及越权引用。完整单元测试、编译、CLI 与 Skill 快速校验必须通过。 |

## RSU-OPT-038

| 日期 | 类型 | 现象/原因 | 修复与决策 | 验证/影响 |
|---|---|---|---|---|
| 2026-09-17 | 缺陷 / Baseline 覆盖账本与有限修复 | 文件核查 Baseline 已正确完成简单/复杂路由，但模型从多个索引自行重建 `context_dispositions` 全集时漏掉部分 Context、Question 和 Data Closure 身份；adaptive 主链虽暴露 `--max-validation-repairs`，却在首次父校验失败时直接退出。 | 父 Runner 在自包含 packet 中确定性写入必须逐项处置的精确身份账本；模型只需为该集合逐项给出处置。Baseline 仍不合格时，从其线程定向 fork 一个零工具、只允许修复输出契约的有限回合，保留原路由和业务语义；修复次数、turn 与 token 纳入 metrics。 | 新增账本物化和修复提示回归测试；adaptive 相关 37 项测试通过。全新隔离目录实跑用于验证复杂 RSU 仍由 Fork 首次生成，旧失败运行不计入性能基准。 |

## RSU-OPT-039

| 日期 | 类型 | 现象/原因 | 修复与决策 | 验证/影响 |
|---|---|---|---|---|
| 2026-09-18 | 缺陷 / 复杂 Scope 输入、分阶段授权与稳定收敛顺序 | 文件核查实跑发现四类关联问题：复杂 Fork packet 把仅作来源证据的接口、主库和公证库全文再次展开，导致 packet 达到 1,279,118 bytes；Fork 生成后，父发布阶段又按 Primary RSU 的单 RSU InputBundle 校验跨 RSU候选，误拒绝 Scope 已明确授权的 Q/Context/DC 引用；反向地，Baseline 语义 JSON 曾按模块全量资源宽授权，导致 provenance-only 数据库附件引用直到发布阶段才失败，错过已有的有限 validation repair；复杂结果原先直接追加到简单候选尾部，使较早 Primary RSU 的复杂候选排在较晚 Primary RSU 的简单候选之后，破坏最终校验器使用的稳定 TP 顺序。另修正零候选 Markdown 状态从错误的 `zero-test-points` 为契约要求的 `zero-candidate`。 | 复杂 packet 只展开 Scope 各 RSU 的真实 InputBundle 物化依赖，证据型大附件仅保留路径、用途与 SHA-256；Baseline 语义校验、复杂语义校验及发布校验统一使用候选所属的精确 RSU/Q/Context/DC 授权集合：简单候选取 Primary RSU InputBundle，复杂候选取当前 Scope，固定三类 Context 始终保留，禁止放宽到模块全量资源。这样越权引用在语义阶段立即进入有限修复，不再拖到发布阶段。复杂结果合并后，候选按 Primary RSU 在 RSU map 中的顺序及其候选文档物理出现顺序稳定归一化；最终意图按其最早 Source Candidate 的同一物理顺序归一化，不依赖 Fork 完成顺序，也不再错误地以最早来源 RSU 排序。 | 文件核查复杂 packet 从 1,279,118 bytes 降至 82,356 bytes；新增 Scope 内跨 RSU 引用允许、Scope 外 Q/Context 拒绝、provenance-only 资源在语义阶段拒绝、发布覆盖、零候选状态及复杂合并稳定顺序回归。Skill 全量 159 项测试通过，相关脚本编译通过；r1～r8 为缺陷发现轮次，不作为性能基准，后续全新轮次作为有效性能基准。 |

## RSU-OPT-040

| 日期 | 类型 | 现象/原因 | 修复与决策 | 验证/影响 |
|---|---|---|---|---|
| 2026-09-18 | 缺陷 / 复杂 Scope Data Closure 双重引用授权 | 文件核查 r9 的复杂 Worker 正确把 `DC-001` 同时写入候选 `data_closure_refs` 与 `context_refs`，但 Scope 路由只在专用 `data_closure_refs` 字段保存 DC；复杂语义校验和发布授权构造仅把 Scope 普通 `context_refs` 合入允许 Context，因而把契约要求的合法 DC Context 引用误判为 `invalid or incomplete context references`。 | 复杂语义校验的有效 Context 改为固定 Context、Scope 普通 Context 和 Scope Data Closure 的并集；复杂 Scope 发布授权同样把 Data Closure 合入 `allowed_context_ids`，同时继续保留独立的 `allowed_data_closure_ids`，不放宽其他资源。 | 新增“DC 仅位于 Scope 专用字段、候选按契约双重引用”的语义与授权回归；Skill 全量 160 项测试通过，相关脚本编译通过。r9 为缺陷发现轮次，不作为性能基准。 |

## RSU-OPT-041

| 日期 | 类型 | 现象/原因 | 修复与决策 | 验证/影响 |
|---|---|---|---|---|
| 2026-09-18 | 缺陷 / 复杂 Scope 依赖授权由语义模型漏报或宽报 | 文件核查 r10 的复杂 Scope 包含明确依赖 `Q-102` 的 `RSU-004`，但 Baseline 路由结果漏报 `Q-102`，导致复杂候选引用该已回答问题时被误判为 unknown question；同时 Baseline 可能把仅用于来源追溯的 `SRC-API-BLACKBOX`、`SRC-DB-MAIN`、`SRC-DB-NOTARY` 宽报为 Scope Context。根因是复杂度与 Scope 成员划分、精确依赖授权被错误地同时交给语义模型。 | Baseline 仍负责基于完整模块语义决定哪些 RSU 构成复杂 Scope；父 Runner 随后针对 Scope 内每个 RSU 调用权威 `InputBundle`，确定性重建 Q、Context 与 Data Closure 授权并按模块顺序稳定合并。模型给出的依赖列表不再作为权限事实，因此会自动补齐 RSU 已声明的 `Q-102`，并剔除未被 InputBundle 物化的 provenance-only 资源。 | 新增“模型漏报问题且宽报证据资源”回归，验证 Q 补齐、FC/DC 保留、证据资源剔除；Skill 全量 161 项测试通过，相关脚本编译通过。r10 为缺陷发现轮次，不作为性能基准。 |

## RSU-OPT-042

| 日期 | 类型 | 现象/原因 | 修复与决策 | 验证/影响 |
|---|---|---|---|---|
| 2026-09-18 | 缺陷 / 次级来源 RSU 的确定性零候选文档缺少追溯标签 | 文件核查 r11 中，某候选以一个 RSU 为主归属并同时覆盖其他 RSU；父 Runner 为次级来源 RSU 正确渲染空候选表和 `zero-candidate`，却直接复用了语义 disposition 的普通说明。该说明不承担候选文档契约，因此未必包含 `原文内容：` / `父级条件：`，最终被候选文档校验拦截。 | 当 RSU 无主归属候选、但 disposition 已关联候选时，父 Runner 根据稳定候选 ID 确定性生成零候选说明：明确原文规则已被哪些关联候选完整覆盖；父级非“无”时明确其已作为适用限定审查。真正无任何关联候选时仍使用 Worker 的零候选理由并维持严格契约校验。 | 新增跨 RSU 次级来源渲染回归，验证 `zero-candidate`、原文/父级标签和关联候选 ID；Skill 全量 161 项测试通过，相关脚本编译通过。r11 为缺陷发现轮次，不作为性能基准。 |

## RSU-OPT-043

| 日期 | 类型 | 现象/原因 | 修复与决策 | 验证/影响 |
|---|---|---|---|---|
| 2026-09-18 | 缺陷 / 确定性 Scope 授权与 Baseline 覆盖账本未同步 | 文件核查 r12 已按权威 InputBundle 从复杂 Scope 中剔除 provenance-only 的 `SRC-API-BLACKBOX`、`SRC-DB-MAIN`、`SRC-DB-NOTARY`，但 Baseline 原始 `context_dispositions` 仍把这些资源标成 `needs-fork`。复杂结果合并后，Scope 已被消费，覆盖账本却留下无法路由的承诺，触发“not routed to a complex scope”。 | 在复杂 Fork 调度前，以全部确定性重建后的 Scope 授权并集归一化覆盖账本：仍被物化的 FC/Q/DC 保持 `needs-fork`；不在授权并集中的模型宽报项保留账本身份但转为 `excluded`，明确其仅作来源追溯或未被复杂语义物化。复杂拓扑仍由 Baseline 决定，不改变 RSU 成员划分。 | 新增“合法 FC 保持路由、provenance-only 资源转为 excluded”回归；Skill 全量 162 项测试通过，相关脚本编译通过。r12 为缺陷发现轮次，不作为性能基准。 |

本表已覆盖本次会话中讨论、实现或确认的事项：

- 自动发送后续 turn、连续处理 RSU 的 runner。
- runner 使用的模型/profile 配置来源。
- 不同模块多窗口并行与同模块互斥锁。
- 可由上层 Codex 对话驱动独立 PowerShell runner 的使用方式。
- 多模块批跑时单模块停止、其他模块继续的隔离原则。
- 父级可观察行为追溯缺口及下游保护。
- Windows 中文供应商错误的 UTF-8 兼容。
- 供应商/网络瞬时错误的 runner 级重试。
- 02 模块上游 map 从 7 个 RSU 补为 9 个 RSU。
- `module-requirement-preanalysis` 对内联图片视觉占位的归一化修复。
- `module-session` 默认会话复用与可选 `isolated` 模式。
- 长会话的周期上下文刷新和不确定性触发补读。
- FC/DC 传递依赖导致整份附件在每个 RSU 输入中重复展开的性能缺陷，以及直接语义输入/追溯证据分离。
- 测试点标题职责、合理拆点、全模块防过度合并和标题质量校验。
- 最终测试点根据实际 `Context Refs` 自动生成轻量、可点击的资源入口，同时保持上游 map 为唯一权威来源。
- 明确数据库/落库/事务/SQL/字段/表断言的 Data Closure 要求，并对唯一标识执行确定性闭包推导、对歧义标识拒绝猜测。
- 阶段级总超时、无输出看门狗、心跳、重复工具动作检测、供应商长退避、共享 session 自动恢复、跨进程全局并发 slot、确定性校验有限修复和结构化耗时遥测。
- 本轮 Windows 快速校验需通过 `PYTHONUTF8=1` 运行外部 `skill-creator` 校验脚本；这属于外部脚本编码兼容，不是 Skill 运行时缺陷。
- 使用手册与长期优化记录入口。

其中 RSU-OPT-007 和 RSU-OPT-008 是为解决本 Skill 执行时暴露的问题而完成的上游修复，但实际代码归属于 `module-requirement-preanalysis` 或具体模块产物，因此特意标为“关联上游修复”。

# 2026-09-18：阻止复杂生命周期按“完整闭环”过度合并

- 文件核查模块的新拓扑实跑暴露出语义收敛过度：正常 IN15 提交与并发幂等、IN17 调度配置与返回映射、页面刷新与开始计奖门禁被 final intent 合并，权限与操作日志甚至在候选阶段即被打包。
- 生成 policy、候选规则和 finalization 规则现明确区分四组独立风险轴：权限/日志、正常处理/并发幂等、轮询配置/结果映射、刷新连续性/下游门禁。共享对象、状态或生命周期不能替代四项门槛判断。
- 新增 packet 回归测试，保证零工具 Baseline 与复杂 Fork 均实际收到该防过度合并契约。

## RSU-OPT-044

| 日期 | 类型 | 现象/原因 | 修复与决策 | 验证/影响 |
|---|---|---|---|---|
| 2026-09-18 | 纠偏 / 测试点语义与最终化 | 前述“四组风险轴”、标题长度/标点、状态与错误码默认下沉、观察层默认合并以及广义语义收敛，把测试分析能力替换成了机械拆合公式。文件核查实跑因此把多个独立需求行为塞进少量候选的 `可观察结果`，最终数量虽少但已不像可执行的测试点。 | 撤销 RSU-OPT-014 中的机械标题限制和 RSU-OPT-025/本页上一节中的四门槛、默认下沉与生命周期归组规则。Baseline 与 Complex Worker 只负责生成来源支持的独立可验证候选，不设目标数量；状态、错误码、字段、边界和 UI/API/数据库/日志观察层既不是自动拆分理由，也不是自动合并理由。Worker Schema 升级为 `semantic-baseline-v4` / `complex-generation-v4`，不再输出或决定 `final_intents`。父 Runner 默认一候选一 TP，只在标题与可观察结果忽略排版空白后均完全相同时确定性合并。 | 保留 Baseline + Complex Fork 拓扑、复杂范围路由、来源/授权/哈希/状态/追溯和 FC/Q/DC 覆盖校验；删除标题质量硬校验、四门槛校验和广义语义压缩。全量 159 项单元测试通过，脚本与测试编译通过，CLI `--help` 通过；外部 `quick_validate.py` 在 Windows 下以 `PYTHONUTF8=1` 运行后通过。本轮不执行付费真实 Runner。 |

## RSU-OPT-045

| 日期 | 类型 | 现象/原因 | 修复与决策 | 验证/影响 |
|---|---|---|---|---|
| 2026-09-18 | 契约措辞 / 模块测试点汇总 | 旧的“全模块收敛”术语和 Worker 提示中的 `final intents` 容易让后续模型误以为还存在广义业务压缩，和“父 Runner 仅精确去重、默认一候选一 TP”的新契约冲突。 | 将面向 Worker/Runner 的阶段描述统一为“模块测试点汇总与发布”；明确可观察结果不能隐藏多个独立验证目标，但该判断由 Worker 基于语义完成，不由父 Runner 机械拦截；明确 `final_intents` 仅是父 Runner 为兼容旧产物确定性维护的映射。文件名、状态字段和兼容读取保持不变。 | 结构、来源、授权、哈希、覆盖、双向归属和精确重复校验保持不变；不新增数量限制或业务收敛规则。 |

## RSU-OPT-046

| 日期 | 类型 | 现象/原因 | 修复与决策 | 验证/影响 |
|---|---|---|---|---|
| 2026-09-18 | 清理 / 复杂度路由边界 | `adaptive_validation.py` 仍残留未接入当前 `module-baseline` 主链的 `semantic-fork` 后处理死代码（候选生成后的语义审查/合并），名称和测试容易误导维护者把复杂度路由与生成后语义收敛混为一谈。 | 删除 `SEMANTIC_FORK_SCHEMA`、`detect_fragmented_semantic_scope` 和 `validate_semantic_fork_manifest` 及其旧测试；将生成前风险事实识别重命名为 `complexity_risk_signals`。该信号只用于 Baseline 的 simple/complex 路由，不参与测试点拆分、合并或数量控制。保留复杂 RSU 必须由定向 Fork 首次生成、父 Runner 只做结构/来源/授权/哈希/精确重复校验的生命周期。 | 全量 159 项 Skill 测试通过；脚本与测试编译通过；CLI `--help` 通过；本轮不执行付费真实 Runner。 |

## RSU-OPT-047

| 日期 | 类型 | 现象/原因 | 修复与决策 | 验证/影响 |
|---|---|---|---|---|
| 2026-09-22 | 纠偏 / 高级测试工程师语义与候选原子性 | 文件核查实跑中，Worker 将复选框可选性、全选范围、批量按钮可用性和部分成功后的状态重算合并为一个候选。原规则虽要求独立行为，但没有明确“独立触发、执行、判定、缺陷定位”的原子标准和生成前后自审，且部分模板仍保留“状态/字段/观察层不是拆合理由”的旧措辞。 | 保留状态、来源、授权、哈希、恢复、零工具和父 Runner 提交框架；删除旧的笼统拆合限制，要求 Worker 以高级测试工程师身份先识别独立测试承诺。不同操作、对象、状态迁移、业务结果、异常/恢复路径或缺陷归属必须拆分；同一操作下的等价输入或共同证据才合并。新增独立触发/执行/判定/缺陷定位标准、原子性自审要求、典型复合候选反例，并补充父 Runner 与 Worker 的交接契约说明。 | 受影响的 Worker/候选质量/标题测试 37 项通过；全量 Skill 测试 159 项通过。工程框架未改变；本轮未重新执行付费真实 Runner。 |

## RSU-OPT-048

| 日期 | 类型 | 现象/原因 | 修复与决策 | 验证/影响 |
|---|---|---|---|---|
| 2026-10-13 | 业务表达 / 测试项与完整测试点 | 旧的“测试维度、测试点、可观察结果”把分类、长标题和断言分散在三列，容易重复描述，不能像成品测试方案一样直接理解验证内容。仅修改表头不能修复零工具 Worker 的实际生成行为。 | 新业务列统一为“测试项、测试点、备注”：测试项是简洁功能/规则分类；测试点自身包含必要条件、动作或事件及具体预期；备注可空且仅补充，不承载关键判据。规则嵌入编译后的 Worker policy 和兼容批次提示，同步 Schema、模板、校验器与汇总。Worker Schema 升级 v5、packet 升级 v3，通过指纹校验阻断旧语义结果复用；Markdown 仍兼容读取旧三列，不机械改名或改写既有正式产物。保留独立验证承诺、0～N、来源覆盖与授权、稳定编号和精确重复去重，仅在测试项、完整测试点及备注排版归一后完全相同时合并。同步测试方案转换的新旧投影规则，验证后续用例读取完整测试点。 | 新增 12 项业务列回归；RSU 全量 171 项、下游 TP 全量 75 项测试通过；编译、Runner --help、两个 Skill 的 quick_validate 均通过。假 Worker 调度测试隔离 Codex 版本探测，不启动真实 CLI。没有执行付费 AI Runner，没有重新生成或覆盖既有模块测试点。 |

