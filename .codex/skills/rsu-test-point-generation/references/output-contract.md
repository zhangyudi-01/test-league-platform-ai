# Output Contract

## 目录结构

```text
<resolved-test-points-dir>/
  README.md
  generation-state.json
  generation-plan.json
  planning-input.md
  inputs/RSU-001-input.md
  session-inputs/RSU-001-delta.md
  batches/BATCH-001-input.md
  batches/BATCH-001/RSU-001.md
  batch-results/BATCH-001/result.json
  by-rsu/RSU-001.md
  history/
  finalization-input.md
  finalization-session-input.md
  module-test-points.md
  coverage-matrix.md
  case-readiness-input.md
  case-readiness-session-input.md
  test-case-readiness.md
```

计划在 Foundation planning fork 后创建并校验。批次 Worker 只写自己的 staging 与 result；父 Runner 校验后才原子提交 `by-rsu/` 和共享状态。模块最终测试点文件只在全部计划内 RSU 校验通过后创建；用例就绪性文件只在最终测试点通过校验后创建。默认根目录由 manifest `output.test_points_dir` 决定；旧项目默认使用 `<module-dir>/test-points`，显式 `--output-dir` 优先级最高。

`batch-results/<BATCH-ID>/result.json` 是 Worker 的私有交接文件，不是共享进度源。其聚合状态可为 `draft`、`partial`、`complete`、`replan-required`，逐 RSU 状态可为 `draft`、`complete`、`failed`、`replan-required`。父 Runner 可从合法完整或部分文件中按稳定 RSU 顺序提交 `complete` 成员；`draft` / `failed` 成员重新准备，`replan-required` 成员进入局部重规划。只有父 Runner 完成验证后，正式 `by-rsu/` 与 `generation-state.json` 才能变化。

`generation-state.json` 必须记录并校验 `module_dir`、`preanalysis_dir`、`manifest_path`、manifest 哈希和 `output_dir`，避免同一状态被错误复用于另一套输入或输出。

## 单 RSU 候选

固定章节为“生成元数据”“候选测试点”“零候选说明”。元数据表头为 `字段 | 值`，必须包含 `RSU-ID`、`输入 SHA-256`、`生成结果`；结果只能是 `candidates` 或 `zero-candidate`。

候选固定表头：

```text
候选 ID | Primary RSU | Source RSUs | 测试项 | 测试点 | 备注 | Question Refs | Context Refs | 推导依据
```

- 候选 ID 从 `CAND-<RSU-ID>-001` 连续编号。
- `Primary RSU` 必须是当前 RSU。
- `Source RSUs` 必须包含当前 RSU，只能引用输入包已物化的 RSU。
- `Question Refs` 使用 `Q-xxx`，无引用写 `无`。
- `Context Refs` 至少包含 manifest 三类固定资源角色映射出的 ID 和当前来源资源；旧项目默认是 `SRC-GLOBAL`、`SRC-MOD`、`CTX`。
- `测试点` 应由高级测试工程师直接说明一个可独立验证的功能行为、业务规则、状态控制、操作分支、状态迁移、异常处理或边界约束。一个测试点必须能够独立触发、独立执行、独立判定，并且能够独立定位缺陷。中英文、大小写、标点和文字长度不作为机械拒绝条件；拆分以需求语义、独立判定和缺陷归属为准。
- `测试项` 是简洁的功能或规则分类，例如“彩票年选项”“重置”“作废入口”；不要机械拼接旧测试维度与长标题。
- `测试点` 本身必须包含必要条件、操作或系统事件以及明确预期，不再是等待另一列补充判据的短标题。共同证明同一意图的观察项可以放在其中；若包含可独立执行、判定和定位缺陷的多个目标，Worker 应拆分候选并进行原子性自审，父 Runner 不按文字模式拆分。
- `备注` 是可为空的补充说明，例如适用限制或迭代调整；不可把必要条件、规格、边界或预期从测试点搬到备注。其他必填列仍不得为空。
- 每行“推导依据”必须包含 `原文内容：...`；当前 RSU 的父级条件非 `无` 时，还必须包含 `父级条件：...`。两部分分别说明本候选覆盖的原文规则以及父级对它的限定作用，不能只写规则编号或笼统的“依据需求”。
- `zero-candidate` 的“零候选说明”同样必须包含 `原文内容` 审查结论；父级条件非 `无` 时还必须包含 `父级条件` 审查结论，并说明为何没有形成候选或由何处完整吸收。
- 单元格中的竖线必须转义为 `\|`，避免破坏 Markdown 表格。
- 不得残留 `待填写`、`TODO`、`TBD` 或模板占位符。

## 最终测试点

`module-test-points.md` 的最终表头：

```text
TP-ID | Primary RSU | Source RSUs | 测试项 | 测试点 | 备注 | Question Refs | Context Refs | Source Candidates | 合并或保留依据
```

`module-test-points.md` 的元数据必须包含当前“最终输入 SHA-256”和“生成结果”。生成结果只能是 `test-points` 或 `zero-test-points`，并与最终表是否为空一致。

元数据后必须保留脚本创建的“上下文资源入口”自动生成区。最终校验器从最终表全部 `Context Refs` 取并集，按 RSU map“引用入口”的资源顺序生成以下轻量索引：

```text
资源 ID | 可点击文件 | 定位用途
```

- 只列最终 TP 实际引用的资源，不复制资源正文，也不列仅由已排除候选使用的资源。
- 文件链接相对于 `module-test-points.md` 生成，表中显示实际路径并可直接点击。
- RSU map 的“引用入口”仍是资源 ID、路径和定位用途的唯一权威来源；本表是自动派生的人工阅读入口，不是第二份配置。
- AI 不得手工填写、删改自动生成标记或复制上游整张资源表。最终 TP 与覆盖矩阵全部通过校验后由脚本写入；`zero-test-points` 时写明没有引用资源。
- 升级前生成且没有自动标记区的合法最终文件，在下一次成功校验时自动插入本节；已有同名非受控章节或残缺标记视为结构冲突，必须重新准备模块汇总。

`TP-ID` 从 `TP-001` 连续编号，并按最早 Source Candidate 的出现顺序稳定排序。每个最终测试点至少引用一个候选，并保留全部来源 RSU、问题和上下文依赖。

最终表直接继承候选的测试项、完整测试点和备注。父 Runner 不做广义语义改写或数量压缩；仅对这三列忽略排版空白后均完全相同的候选执行确定性合并。读取历史文件兼容旧三列，但新生成只使用新三列；同一文件不得混用新旧候选表或最终表。

## 覆盖矩阵

RSU 覆盖表头：

```text
RSU-ID | 候选数 | Final TP Refs | 处理结果 | 说明
```

处理结果为 `covered`、`zero-candidate` 或 `excluded`：只要有最终 TP 引用该 RSU 就写 `covered`（即使该 RSU 自身候选数为 0）；无候选且无最终引用写 `zero-candidate`；有候选但全部被合理排除写 `excluded`。

候选归并表头：

```text
Candidate ID | Source RSU | 处理结果 | Final TP Refs | 说明
```

处理结果为 `retained`、`merged` 或 `excluded`。每个候选必须且只能出现一次；`merged` 只用于测试项、完整测试点和备注均完全重复的候选，`excluded` 只用于明确范围排除或非法候选，二者都必须有具体说明。

## 校验边界

脚本校验顺序、哈希、表头、ID、引用集合、候选处置、RSU 覆盖、双列追溯标签和授权范围；输入准备还会阻止仅存在于父级条件列的高置信度可观察行为。测试点是否准确表达独立需求行为，以及追溯说明是否真实覆盖语义，由生成 Worker 基于完整上下文判断；父 Runner 只做确定性结构校验和精确重复去重。

## 用例生成就绪性

`test-case-readiness.md` 固定包含一张元数据表和以下三张表：

```text
输入主题 | 已确认结论 | 来源 | 关联 TP
TP-ID | 用例生成状态 | Input Question Refs | 说明
CIQ-ID | 类型 | 关联 TP | 待补充问题 | 已有依据 | 回填答案/资料 | 状态
```

- 审查结果只能是 `ready`、`blocked-input` 或 `upstream-gap`。
- 每个最终 TP 必须按原顺序出现一次；TP 状态只能是 `ready`、`blocked-input` 或 `upstream-gap`。
- `CIQ-ID` 从 `CIQ-001` 连续编号，类型只能是 `test-data`、`environment`、`configuration`、`observability` 或 `upstream-requirement`，状态只能是 `pending` 或 `answered`。
- `blocked-input` TP 必须引用至少一个待回答的非上游 CIQ；`upstream-gap` TP 必须引用待回答的 `upstream-requirement` CIQ；`ready` TP 不得依赖待回答 CIQ。
- CIQ 只承载用例执行输入，不能代替需求澄清或掩盖测试点遗漏。整体结果不是 `ready` 时，后续测试用例生成必须停止。
- 具体执行环境、凭据、权限开通状态和实际样本若不改变用例设计，属于用例前置条件/执行时绑定，不得仅因其尚未提供或未验证可用而创建 pending CIQ；只有准备/断言/安全恢复方案本身无法确定时才阻断。
# 模块级语义 Worker 结果

默认 Baseline Worker 只返回私有 `worker-results/baseline.json`，schema 为 `rsu-test-point-generation/semantic-baseline-v5`。它包含：

- 与 packet hash 绑定且按 map 顺序完整出现的 `rsus` disposition；
- 使用 Worker 局部 key 的候选语义及其 RSU/Q/Context/Data Closure 引用；
- 生成前确定且范围明确的 `complex_scopes`；
- 对全部非固定 FC/Q/DC 的唯一 `context_dispositions` 覆盖账本。

候选业务字段为 `test_item`、`test_point`、`remarks`；前两项为非空字符串，备注允许空字符串。旧 `dimension`、`title`、`observable_results` 不属于新 Worker Schema。

该文件不得包含 Markdown、正式 Candidate/TP ID、路径写入指令或共享状态。父 Runner校验局部 key、引用和 hash 后分配稳定编号，并生成兼容 `baseline-result.json`：

```json
{
  "schema": "rsu-test-point-generation/baseline-v1",
  "input_sha256": "<baseline-input.md SHA-256>",
  "rsus": [
    {"rsu_id": "RSU-001", "status": "generated", "candidate_ids": [], "reason": ""}
  ]
}
```

`rsus` 必须严格按 RSU map 顺序逐个出现。`generated`、`zero-test-points`、`needs-fork`、`blocked` 是唯一允许的 baseline 状态；后三者必须有具体可审计原因。兼容文件、候选、最终测试点和覆盖矩阵全部由父 Runner渲染，Worker 不得直接写入。

有界复杂 Fork 使用 `complex-generation-v5` 私有结果，对授权 Scope 首次生成完整 disposition 和候选语义：

```json
{
  "schema": "rsu-test-point-generation/complex-generation-v5",
  "packet_sha256": "<fork packet SHA-256>",
  "scope_id": "COMPLEX-001",
  "status": "resolved",
  "rsus": [],
  "candidates": [],
  "reason": "<具体生成结论>"
}
```

RSU 顺序必须与父 Runner 授权范围完全一致；候选只能引用授权 RSU 和当前来源。Fork 可以从零创建候选 key，但不能引用范围外 RSU。父 Runner 拒绝任何越界引用，并由候选确定性建立最终意图：默认一候选一 TP，只合并测试项、完整测试点和备注均完全重复的候选；子 Fork 不修改最终文件或共享状态。
