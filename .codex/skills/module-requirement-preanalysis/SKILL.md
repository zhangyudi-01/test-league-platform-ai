---
name: module-requirement-preanalysis
description: 对已拆到模块级的需求执行测试点生成前分析：在模块根目录的 preanalysis 子目录中探索需求全文和模块背景，按语义完整契约建立 RSU 原文映射，维护普通澄清问题与可复用 Context Card；数据库相关模块再按最小业务数据路径建立可选 DC 数据闭包，并生成 preanalysis/v1 manifest 供后续逐 RSU 测试点 Skill 定位固定上下文和动态依赖。适用于新建、补全或审核模块前置分析产物；要求保持需求原文、固定 Markdown 结构并通过 manifest、链接、ID、来源匹配和拆分决策追溯强校验。不用于 AI 改写原子需求、复杂度评分、直接生成测试点/方案/用例或按标点、换行机械断句。
---

# 模块需求前置分析

## 使用者文档

- 首次使用、能力边界、目录布局、聊天框用法、脚手架与校验命令、RSU 判断、既有产物维护和排障：阅读 [使用手册](./README.md)。
- 历次需求、缺陷、修复方案、实现结果、验证和关联文件：阅读 [优化记录](./OPTIMIZATION-HISTORY.md)。每次功能、行为、默认值、输出契约或兼容性发生变化时，只追加新记录，不覆盖历史。
- 本文件及 `references/` 是 AI 执行约束的权威来源；使用手册面向操作人员，不得用手册摘要放宽下述来源保真、语义拆分或完成门禁。

## 目标

把模块需求整理为可重复、可追溯、可校验的测试点生成前输入。保留需求来源文字，先形成模块逻辑基线，再建立 `RSU-ID` 原文需求单元映射；不要增加一层 AI 改写的原子需求。

本阶段只回答五件事：

1. 本模块在需求全文中做什么，与哪些上下文有关。
2. 来源资料中有哪些原文需求单元，是否完整覆盖。
3. 哪些理解、范围、链路或资料仍需人工确认。
4. 后续处理某个 `RSU-ID` 时必须读取哪些固定输入和动态依赖。
5. 若行为依赖数据库，哪些最小数据路径、连接/过滤、数据状态和准备/清理契约必须随 RSU 进入后续阶段。

## 必读资源

开始前执行以下动作：

1. 递归枚举目标模块目录，读取所有默认产物、需求包和 Context Card。
2. 读取项目全局上下文、需求全文、模块来源区间、资料注册表及模块实际引用的附件。
3. 读取用户在探索前或探索中提供的业务说明；这些说明是形成模块逻辑的重要输入，不能只留在聊天记录。
4. 尊重用户明确排除的文件。排除文件不参与推导、不维护、不写入默认流程。
5. 读取 [产物职责](./references/artifact-map.md)、[执行工作流](./references/workflow.md)、[固定输出契约](./references/output-contract.md)、[RSU 语义拆分协议](./references/rsu-semantic-partitioning.md) 和 [数据闭包契约](./references/data-closure-contract.md)。

若缺少模块需求原文，不要凭空创建需求；先定位来源或记录阻塞问题。

### 全文读取与提问门禁

- 通读需求全文，截断须补读；搜索、模块切片和旧摘要不能替代全文。按 [工作流](./references/workflow.md) 在 Context Pack 简记实际读取范围与缺口。
- 提问前先核对适用的全文通用规则；已有答案的自行回填并注明来源，剩余缺口才向用户确认，不套用邻模块专属规则。

## 固定产物

新建产物固定使用以下规范结构。`preanalysis` 是前置分析目录的规范名称，并且必须是模块根目录的直接子目录；这样 `rsu-test-point-generation` 可以从模块根目录自动发现唯一 manifest，同时测试点、方案和用例可作为同级阶段目录独立维护：

```text
<module-root>/
  00-module-requirement-pack.md        # 由上游拆分写入时保留在模块根，被 manifest 原地引用
  preanalysis/
    preanalysis-manifest.json
    README.md
    00-module-requirement-pack.md      # 仅当模块根没有需求包时才创建于此
    01-context-pack.md
    02-sentence-test-point-map.md
    03-clarification-questions.md
    context-cards/
      README.md
      FC-001-<主题>.md               # 仅在确有可复用复杂上下文时创建
    data-closures/                    # 仅数据库相关模块创建
      README.md
      DC-001-<业务数据路径>.md        # 按最小可复用数据路径创建，不按 TP 复制
  test-points/                       # 后续阶段产物，不由本 Skill 生成
  test-plans/                        # 可选后续阶段，不由本 Skill 生成
  test-cases/                        # 可选后续阶段，不由本 Skill 生成
```

禁止为新模块把上述文件平铺到 `<module-root>`。既有平铺项目可继续由 manifest/旧格式兼容读取，但维护时要标明其为 legacy flat layout；除非用户明确要求迁移，不要擅自移动既有产物、重写全部相对链接或使下游状态失效。新建产物统一使用 `preanalysis/`；若模块根目录已存在平铺 manifest 或核心前置产物，脚手架必须拒绝再创建第二套目录。

`02-sentence-test-point-map.md` 是历史兼容文件名，文件内容统一使用 `RSU-ID`，职责是“原文需求单元映射”，不是句子测试点或测试点种子。不要擅自重命名现有文件。

`preanalysis-manifest.json` 是生产端与后续测试点生成端的唯一机器接口。新建时位于 `<module-root>/preanalysis/preanalysis-manifest.json`，其中 `module_root` 为 `..`、默认 `output.test_points_dir` 为 `../test-points`；路径必须相对 manifest，schema 固定为 `preanalysis/v1`。下游从模块根目录及其直接子目录查找唯一 manifest，不依赖目录名猜测。

模块需求包 `00-module-requirement-pack.md` 保持单一事实源，禁止在模块根和 `preanalysis/` 各存一份。模块根已有 `00-module-requirement-pack.md`（例如由 `requirement-document-splitter` 拆分写入）时，manifest `module_requirement` 角色指向 `../00-module-requirement-pack.md` 原地引用，脚手架不得再复制副本；没有模块根需求包时才在 `preanalysis/` 内创建。产物内的需求包链接由脚手架按 manifest 路由生成，不手写死相对路径。

需要初始化新目录时，先解析当前 `SKILL.md` 所在目录为 `<skill-dir>`，再运行：

```bash
python <skill-dir>/scripts/scaffold_preanalysis.py <module-root> --module-name "<模块名>" --global-context <project-context.md> --requirement-source <模块需求原文文件>
```

数据库相关的新模块在上述命令后追加：

```bash
--with-data-closures --data-source <schema/SQL/代码/数据库设计文件> --data-source-id SRC-DB-SCHEMA
```

该参数只创建 `DC-INDEX` 和首张闭包卡骨架，不推测表、字段或外键。无数据库依赖的模块不要使用此参数。

脚手架会自动创建 `<module-root>/preanalysis/`，只固定结构，不会编造模块需求，也不会覆盖已存在的 `00-module-requirement-pack.md`；必须读取真实资料后替换全部占位内容。模块根已有需求包时，脚手架原地引用该文件并在 manifest 中登记 `../00-module-requirement-pack.md`，不再向 `preanalysis/` 复制；若两处已存在内容不同的副本，脚手架报错并要求先收敛为一份。不要把 `<module-root>/preanalysis` 作为位置参数再次传入，也不要假设脚本位于仓库根目录的 `scripts/`。

只需要在规范目录中重新计算 manifest 的模块根目录或默认输出路径时，对同一个 `<module-root>` 调用并追加 `--refresh-manifest`；不要为刷新 manifest 使用会覆盖分析骨架的 `--force`。原来的 `<preanalysis-dir> --module-root <module-root>` 调用仅作为脚本兼容入口，不能用于新建平铺产物。

## 执行流程

1. **盘点并完整读取来源**：登记当前需求、需求全文、全局上下文、附件、历史 PRD、接口、数据库、配置、环境和原型；标明权威级别与允许用途，核对全文读取覆盖并记录证据。
2. **探索模块逻辑**：先结合需求全文与人工讲解理解模块背景、目标、能力、主链路、分支、外部系统、验收层级和明确边界。
3. **建立 Context Pack**：把已确认理解写入 `01-context-pack.md`。该文件是模块逻辑与上下文基线，不只是资料路由表。
4. **先消疑再记录问题**：先用需求全文及适用共享规则核对疑问，再把仍存在的理解缺口、资料冲突、范围疑问和不可读原型统一写入 `03-clarification-questions.md` 的普通 `Q-ID`；不增加签字、拍板或独立 scope-decision 流程。
5. **先做语义拆分审查，再建立 RSU 映射**：先对来源结构逐段分类为视觉占位符、结构容器、字段碎片、独立契约、复合契约或未决范围，再按 [RSU 语义拆分协议](./references/rsu-semantic-partitioning.md) 建立 RSU。原文必须可回查；RSU 必须是能独立表达完整业务契约的来源单元，不按 Markdown 行、换行、标点或最小编号项机械拆分。
6. **建立上下文索引**：为每个 RSU 填写来源 ID、语义定位、必要 `Q-ID` 和 `FC-ID`。链接统一放在文件顶部资源表，行内只写稳定 ID。
7. **创建 Context Card**：仅为跨 RSU 的功能链路、既有契约、外部依赖或验证位置创建可复用卡片；从 `assets/templates/context-cards/FC-card.md.tmpl` 复制固定骨架并替换占位符，不要每个 RSU 建一张卡。创建后必须同时登记到 map 资源入口和 `context-cards/README.md`。
8. **建立数据闭包**：仅当 RSU 的行为、预期或后续造数/查询依赖数据库时，按最小可复用业务数据路径建立 `DC-ID`。必须记录表角色、完整连接谓词、过滤、基数、数据 Profile、查询口径和清理边界；图不能替代这些表格。将适用的 `DC-ID` 写入 RSU 的“相关上下文”。
9. **回填确认**：人工回答后同步更新问题清单、Context Pack、相关 Context Card/Data Closure Card 和 map 状态。答案不能只留在聊天中，也不能伪装成需求原文。
10. **维护机器契约**：确认 manifest 中模块根目录、六类逻辑产物、三类固定资源角色和测试点输出目录与实际一致。可选 DC 通过资源索引发现，不需要按项目修改 manifest schema 或 Skill 代码。
11. **执行强校验**：运行校验脚本；有错误时继续修复，不得把“生成完成”作为通过标准。

## 不可违反的规则

### 来源保真

- 保持 `原文内容` 与来源可见文字一致，只允许去掉 Markdown 链接目标、统一空白，或将仅用于适用范围的最小父级条件移到专用列。
- 不把人工说明、验证方法、实现推测或测试范围结论写成 RSU 原文。
- 历史 PRD 只有在人工确认“既有逻辑继续沿用且本次不修改”后，相关原文条款才能进入 RSU。
- 附件或历史资料的范围必须裁剪到最小可定位章节/规则，不能因字段级内容排除就把整个文件标为 `indexed-only` 或 `scope-excluded`。进入当前层级的文件类型、数量、命名、目录、覆盖等条款建立 RSU；真正排除的字段/章节再单独保留追溯。
- 无法可靠读取原型或附件时，创建普通待确认问题，不凭经验补写 UI、接口、数据库或外部系统规则。

### RSU 语义完整性

- `RSU` 是完整业务契约，不是句子、换行、字段名、枚举项或测试项；不要在 RSU 表中增加 `测试项`、测试意图、预期结果或验证步骤列。
- 必须在 map 中维护 `原文结构与拆分决策` 表，先记录来源范围的语义角色和 `one-rsu`/`not-rsu`/`pending` 决策，再生成 RSU 表。
- 拆分决策表与来源覆盖表必须使用相同的 `SRC-ID > 语义范围`；`one-rsu` 对应 `mapped`，`not-rsu` 对应 `not-rsu`，`pending` 对应 `pending` 或 `pending-context` 并关联未关闭的 `Q-ID`。
- `原型`、图片标题和不可执行的视觉占位符通常是 `visual-placeholder`，不生成仅包含“原型”的 RSU；不可读的视觉细节用普通 `Q-ID` 和来源覆盖状态记录。
- `查询条件包括：`、`包含以下信息：`、`任务列表的行内操作：` 等只组织后续内容的文字是 `structural-container`，不单独生成 RSU。
- 独立控件规则可以分别成为 RSU；结果列表的父规则与仅列举字段的子项必须合并为一个 `composite-contract` RSU。不要把“任务 ID；”“彩票年；”等字段碎片单独生成 RSU。
- `父级条件（原文）` 只填写来源中的实际父级文字；`业务规则 1`、`业务规则 2.1` 等编号属于 `来源定位`，不能冒充父级条件。
- `父级条件（原文）` 只能承载让当前 `原文内容` 可理解的适用条件、触发、状态或范围，不能成为业务行为的隐藏存放区。创建/生成、修改/删除、写入/发送、状态变化、页面进入/跳转、弹窗/提示、展示等可独立观察行为，必须完整出现在至少一个 RSU 的 `原文内容` 中。
- 父句同时包含条件和可观察行为时，优先把完整父句建立为独立 RSU，再为能够独立验证的子项建立 RSU；若父句与子项共同构成一个不可分割契约，则把父句和完整必要子项按来源顺序合并进同一 RSU 的 `原文内容`。不得只把父句放在一个或多个子 RSU 的 `父级条件（原文）` 中。
- 子 RSU 只需继承父句中的最小原文条件片段，例如 `校验通过后`；不得为了保留层级结构复制整段含行为父句。建立映射后必须执行“父级隐藏行为”反查：每段含可观察行为的父级文字都能定位到承载其完整原文的 RSU。
- 先保证每个 RSU 具备对象、适用条件/触发、行为/约束/结果和必要子项，再保证来源覆盖；不能为了 RSU 数量、排版或后续批处理方便拆开不可独立理解的文字。

### 模块逻辑基线

- 将人工在探索前讲解的完整业务链路视为核心上下文，核对来源后写入 Context Pack。
- 明确区分当前新增能力、沿用的既有系统能力、验证证据和本次不重测范围。
- 问题清单保存确认依据，Context Card 展开局部主题；两者都不能替代 Context Pack 中的模块主逻辑。

### 后续逐 RSU 输入

后续每次从一个 `RSU-ID` 生成 0～N 个测试点时，固定读取：

1. manifest `global_context` 角色对应的项目全局上下文全文（默认 `SRC-GLOBAL`）。
2. manifest `module_requirement` 角色对应的当前模块需求全文（默认 `SRC-MOD`）。
3. manifest `module_context` 角色对应的模块背景、能力、已确认详细逻辑和理解边界（默认 `CTX`）。
4. 当前 `RSU-ID` 的完整映射行。

再解析并读取当前 RSU 显式声明的 Q、FC、DC、附件、PRD、API、数据库、配置、环境及跨 RSU 依赖。FC/DC 必须把测试点阶段需要的聚焦语义写入卡片；卡内“引用入口”“依据”和“关联 RSU”只建立来源追溯，不等于要求下游递归复制整份来源或继承被关联 RSU 的全部动态依赖。卡片引用的证据资源由下游记录路径、用途和正文哈希；只有当前 RSU 的“相关上下文”直接列出某资源 ID 时才加载其正文。确需长来源细节时，使用聚焦资源和语义定位，不能默认投喂整份 PRD 或数据库设计。

### 数据闭包边界

- 数据闭包是一等但可选的上下文类型。无数据库依赖时不创建 `DC-INDEX`、空图或虚构表。
- 一张闭包卡覆盖一条最小可复用业务数据路径，可被多个 RSU/TP 共享；不要做模块整库巨图，也不要每个 TP 复制一张图。
- `ready` 表示足以支撑测试点和可执行用例设计；`test-point-ready` 表示测试点语义已闭合、用例 SQL/造数仍缺输入；`blocked` 表示缺口会改变测试点语义。
- `blocked` 闭包关联的 RSU 必须是 `pending-context` 或 `pending`，并关联至少一个待确认 `Q-ID`。
- 连接必须写完整 Join Predicate 和附加过滤，包含来源类型、运动类型、删除状态、租户/中心、时间、状态等实际影响结果的条件；不得依据表名猜测。
- 具体环境 SQL 和样本参数在用例阶段实例化，但表角色、连接、过滤、数据状态、预期推导、准备和清理结构应在闭包卡中闭合。
- FC/DC 卡必须自包含测试点阶段所需的业务语义；引用的 schema、SQL、API、代码或人工确认是卡片结论的证据链，不是逐 RSU 的递归全文依赖。若卡片无法在不重新阅读某来源正文的情况下支持测试点，应将聚焦来源资源显式绑定到相应 RSU，或先补全卡片再交付下游。

### 索引与排版

- 新建产物使用规范文件名；已有项目的路径差异写入 manifest。章节顺序、表头、ID 前缀和状态值仍固定，以 `references/output-contract.md` 为准。
- 在每个主产物顶部维护资源入口或快速索引；使用可点击的相对路径。
- 不创建同文件 `RSU-ID`、`Q-ID`、`FC-ID` 深层锚点，不在每行重复长路径。
- 长文档使用“资源 ID + 章节/规则/字段名”定位，不依赖阅读器不一致的标题锚点。
- 所有本地 Markdown 链接必须实际存在；所有 map 引用的 Q、FC、DC、SRC 必须可解析。
- 来源覆盖表首列固定写成 `SRC-ID > 章节/规则/字段范围`；禁止只写“附件”“业务规则”或文件名。每个结构化来源的在范围条款必须逐项标记，不能用一条整文件状态替代章节级盘点。
- map 的 `原文结构与拆分决策` 必须逐项覆盖进入范围的来源范围，记录语义角色、处理决定、对应 RSU 和理由；不生成 RSU 的范围必须明确写成 `not-rsu`，不能静默消失。

### 阶段边界

- 不生成 AI 改写的原子需求或 ATP/STP 种子。
- 不生成复杂度评分、复杂度处理清单或 `test-point-batch-*`；除非复杂度未来真实改变模型、输入、审核或执行路径，并由用户重新确认。
- 不生成正式测试点、测试方案、测试用例、执行步骤或 Excel。
- 全部 RSU 后续生成完测试点后，仍需另做全模块去重、覆盖、引用完整性和跨单元组合检查；当前阶段只写明该契约。

## 强校验

完成或维护产物后必须运行：

```bash
python <skill-dir>/scripts/validate_preanalysis.py <module-root>/preanalysis --require-canonical-layout
```

仅审核尚未迁移的既有平铺/自定义目录时省略 `--require-canonical-layout`；校验器会给出布局兼容警告。新建产物不得忽略规范布局错误。

校验至少覆盖：

- manifest schema、相对路径、模块边界、逻辑角色、输出目录和配置产物是否一致。
- 新建产物是否位于 `<module-root>/preanalysis/`，manifest 是否可由下游从模块根目录的直接子目录自动发现。
- 模块需求包是否单一事实源：manifest `module_requirement` 可指向模块根（如 `../00-module-requirement-pack.md`），但模块根与 `preanalysis/` 不得同时存在 `00-module-requirement-pack.md` 副本。
- 必需逻辑产物、单一一级标题、固定章节顺序、固定表头、重复结构和空表格单元格。
- 模板占位符是否清理。
- 所有本地 Markdown 链接是否可打开，且没有阅读器不稳定的本地 `#fragment`。
- Context Pack 和 map 中 manifest 三类固定资源角色、`RSU-INDEX`、`Q-INDEX` 是否都有可点击入口并指向正确文件。
- `RSU-ID`、`Q-ID`、`FC-ID`、`SRC-*` 是否唯一且引用闭合；Context Card 是否有真实文件并同时登记在 map 和卡片索引，索引中不得残留孤立 `FC-ID`。
- 启用数据闭包时，`DC-INDEX`、`DC-ID`、卡片文件、关联 RSU、来源资源、卡片状态和 map/Context Pack 索引是否一致；固定章节、表头、Mermaid 图及 Table/Edge/Profile ID 是否有效。
- `blocked` 闭包是否阻止关联 RSU，`ready` 闭包是否仍残留未知或待确认的数据契约。
- RSU 原文能否在对应可读文本来源中归一化匹配。
- 拆分决策表中的角色、处理决定和 RSU 引用是否闭合，并与来源覆盖表逐范围、逐状态、逐引用一致；结构容器、视觉占位符和字段碎片不得被错误登记为独立 RSU，复合契约不得遗漏其父级或子项。
- `父级条件（原文）` 是否只保存条件/触发/状态/范围；其中若含可独立观察行为，其完整原文是否也出现在某个 RSU 的 `原文内容` 中。校验器将高置信度的父级隐藏行为视为错误，必须调整拆分后才能交给下游。
- 来源覆盖行是否都带有已登记的 `SRC-ID` 和语义定位，是否把同一资料的纳入部分与排除部分分开处置。
- Context Pack、README 和 map 是否都声明四项固定输入。
- 是否误建 ATP、复杂度表、批次目录或正式测试点产物。

脚本返回非零即为失败。不得忽略错误；确实无法自动验证的来源必须在问题清单和覆盖表中明确标记，不能静默跳过。
