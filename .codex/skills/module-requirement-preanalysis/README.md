# 模块需求前置分析 Skill 使用手册

本文面向使用和维护 `module-requirement-preanalysis` 的人员，集中说明它已经实现的能力、前置条件、目录布局、运行方式、RSU 判断方法、校验命令和常见排障。AI 执行时的权威约束仍以 [SKILL.md](./SKILL.md) 及 `references/` 下的契约为准；历史改动见 [OPTIMIZATION-HISTORY.md](./OPTIMIZATION-HISTORY.md)。

> 本文件是 Skill 自身的使用手册。Skill 生成到业务模块 `preanalysis/README.md` 的文件是该模块前置分析产物的导航页，两者不是同一个 README。

## 1. 它解决什么问题

该 Skill 接收已经拆到模块级的需求及相关项目资料，在生成测试点前完成以下工作：

1. 结合需求全文、模块原文、全局上下文、附件和人工讲解，建立模块逻辑基线。
2. 按语义完整业务契约建立原文保真的 `RSU-ID` 映射，而不是按 Markdown 行或标点机械断句。
3. 记录澄清问题、可复用 Context Card，以及数据库相关模块的最小业务数据闭包。
4. 生成 `preanalysis/v1` manifest，把固定产物、资源角色和后续测试点目录连接起来。
5. 通过格式、链接、ID、来源匹配、拆分决策、覆盖和数据闭包校验后，才交给 `rsu-test-point-generation`。

它的核心目标是防止来源遗漏、原文被 AI 改写、结构容器被误当需求、完整契约被拆碎、父级行为被隐藏，以及后续测试点阶段读错目录或缺少上下文。

该 Skill 不负责：

- 从整份需求文档规划模块目录；这属于 `module-directory-generator`。
- 把整份 Markdown/Word 需求确定性切到各模块；这属于 `requirement-document-splitter`。
- 生成测试点、测试方案、正式测试用例、执行步骤或 Excel。
- 将原文改写成新的“原子需求”或 ATP/STP 种子。
- 自动回答尚无依据的业务问题，或替用户决定有歧义的范围。
- 在未获得明确授权时迁移已有平铺目录、批量重写相对链接或清除下游状态。

## 2. 已实现能力

| 能力 | 说明 |
|---|---|
| 规范阶段目录 | 新建产物固定进入 `<module-root>/preanalysis/`，与同级 `test-points/`、方案和用例分离。 |
| Manifest 路由 | 生成 `preanalysis/v1` manifest，以逻辑产物角色和固定资源角色连接上下游，不让下游猜目录名。 |
| 模块逻辑基线 | 先形成模块背景、目标、能力、主链路、分支和边界，再拆 RSU。 |
| 全文读取防漏 | 通读全文并补齐截断，在 Context Pack 简记实际范围与缺口，不新增阅读日志。 |
| 两遍 RSU 语义拆分 | 第一遍分类来源结构并记录拆分决策，第二遍执行语义闭合，不按行、编号或标点机械切分。 |
| 来源角色分类 | 区分 `visual-placeholder`、`structural-container`、`field-fragment`、`independent-contract`、`composite-contract` 和 `unresolved`。 |
| 父级行为保护 | `父级条件（原文）` 只保存最小条件；创建、状态变化、跳转、提示、展示等行为必须进入某个 RSU 的 `原文内容`。 |
| 原文保真与图片归一化 | 校验 RSU 与父级文字能够在来源中归一化匹配；行尾 Markdown 原型图不会把 `image.png` 等 alt 文本混入业务原文。 |
| 拆分与覆盖对账 | `原文结构与拆分决策` 和 `原文来源覆盖检查` 按同一 `SRC-ID > 语义范围` 对账。 |
| 澄清问题闭环 | 提问前先核对全文及适用共享规则，能从需求解答的自行回填并注明来源；只对剩余缺口使用普通 `Q-ID`，不冒充人工确认。 |
| Context Card | 为跨 RSU 链路、既有契约或观察位置建立可复用 `FC-ID`，避免每个 RSU 重复上下文。 |
| Data Closure | 数据库相关模块可按最小业务数据路径建立 `DC-ID`，记录表角色、连接、过滤、数据状态、查询和清理契约。 |
| 可重复脚手架 | `scaffold_preanalysis.py` 创建固定骨架、manifest 和可选 DC 骨架，不编造需求内容。 |
| 强校验 | `validate_preanalysis.py` 校验布局、manifest、章节、表头、链接、ID、来源、拆分、覆盖、FC/DC 和阶段边界。 |
| Legacy 兼容 | 既有平铺或自定义布局可继续维护并得到兼容警告；不会在未授权时自动迁移。 |
| 下游输出隔离 | legacy 平铺目录中存在 `test-points/` 时，可排除该生成目录的 Markdown 链接检查，避免物化文件的相对链接被误判为上游断链。 |

全文读取与提问前消疑由执行层落实，自动校验不能证明已读懂全文；详见 [工作流](./references/workflow.md)。

## 3. 开始前需要什么

至少准备：

1. 已确定的模块工作区根目录。
2. 当前模块需求原文，通常是 `00-module-requirement-pack.md` 的来源。
3. 项目全局上下文和当前需求全文。
4. 模块实际引用的原型、附件、接口、数据库、配置、环境或历史 PRD。
5. 用户已经说明的业务链路、沿用关系、验证层级和排除范围。

数据库相关模块还应尽量准备 schema、建表 SQL、关键查询、实体/Mapper、数据字典或经确认的数据库设计。资料不完整时可以建立 `Q-ID` 和相应阻塞状态，但不能依据表名猜外键或过滤条件。

来源权威关系通常为：当前模块需求原文 → 人工对本次范围和实际链路的明确确认 → 当前需求全文/全局规则 → 已确认继续沿用的历史 PRD → 当前需求引用的附件、接口、数据库和环境资料。

## 4. 目录布局与三个容易混淆的文件

新建模块的规范布局：

```text
<module-root>/
  00-module-requirement-pack.md      # 上游拆分写入时保留在模块根，被 manifest 原地引用
  preanalysis/
    preanalysis-manifest.json
    README.md
    00-module-requirement-pack.md    # 仅当模块根没有需求包时才创建
    01-context-pack.md
    02-sentence-test-point-map.md
    03-clarification-questions.md
    context-cards/
      README.md
      FC-001-<主题>.md
    data-closures/                 # 仅数据库相关模块
      README.md
      DC-001-<业务数据路径>.md
  test-points/                     # 后续 Skill 输出
  test-plans/                      # 可选后续阶段
  test-cases/                      # 可选后续阶段
```

需求包保持单一事实源：模块根已有 `00-module-requirement-pack.md`（通常是 `requirement-document-splitter` 的输出）时，manifest `module_requirement` 指向 `../00-module-requirement-pack.md` 原地引用，`preanalysis/` 内不保留副本；只有模块根没有需求包时才在 `preanalysis/` 内创建。重新运行脚手架会自动删除与模块根完全相同的旧副本；两处内容不同时脚手架报错，需要先人工收敛。

三个文件名称相近，但职责不同：

| 文件 | 面向对象 | 唯一职责 | 是否作为下游语义输入 |
|---|---|---|---|
| Skill 根目录的本 `README.md` | Skill 使用者 | 说明如何使用和维护 Skill | 否 |
| 模块 `preanalysis/README.md` | 当前模块维护者 | 当前目录导航、文件职责、分析流程和固定输入入口 | 仅作导航契约，不承载模块业务细节 |
| 模块 `preanalysis/01-context-pack.md` | AI 与测试分析人员 | 模块背景、能力、主链路、已确认逻辑和边界 | 是，manifest 的 `module_context` 固定角色 |

因此，模块 `README.md` 和 `01-context-pack.md` 不应合并。前者回答“文件在哪里、按什么流程使用”，后者回答“模块实际做什么、上下文和边界是什么”。删除任意一个都会破坏现有输出契约或下游固定输入。

## 5. 完整工作流

```text
模块原文 + 需求全文 + 全局上下文 + 相关资料 + 人工讲解
    ↓
盘点来源、权威级别和当前范围
    ↓
建立 Context Pack 模块逻辑基线
    ↓
记录并回填 Q-ID
    ↓
第一遍：来源结构分类与拆分决策
    ↓
第二遍：RSU 语义闭合与父级行为反查
    ↓
建立 FC / 可选 DC 及稳定资源索引
    ↓
拆分决策与来源覆盖逐项对账
    ↓
维护 preanalysis/v1 manifest
    ↓
强校验通过
    ↓
交给 rsu-test-point-generation
```

不要从“逐行遍历需求并立即创建 RSU”开始。模块逻辑和来源结构必须先于 RSU 表建立。

## 6. 使用方式一：在 Codex 对话中执行

新模块可以这样发起：

```text
请使用 @module-requirement-preanalysis，分析模块目录
modules/<模块目录>，读取当前模块需求、需求全文、项目上下文和引用资料，
在模块根目录的 preanalysis 子目录生成规范前置分析产物并完成强校验。
```

维护或审核已有产物时：

```text
请使用 @module-requirement-preanalysis 审核
modules/<模块目录> 的现有前置分析产物。
保留已经完成的澄清结论和稳定 ID，重点检查 RSU 是否按完整语义拆分、
父级行为是否进入原文内容、拆分决策与来源覆盖是否一致，修复后重新校验。
```

如果某个问题已经由用户回答，应明确要求把答案回填到问题清单、Context Pack、相关 FC/DC 和 RSU 状态，而不是只留在聊天记录。

遇到需要人工确认的范围、来源冲突或不可读资料时，Skill 应创建或维护 `Q-ID` 并停止相关 RSU 的下游交接；不能自行补写答案。

## 7. 使用方式二：脚手架初始化

从项目根目录运行：

```powershell
$SkillDir = ".codex/skills/module-requirement-preanalysis"
$ModuleRoot = "modules/<模块目录>"

python -X utf8 -B "$SkillDir/scripts/scaffold_preanalysis.py" `
  "$ModuleRoot" `
  --module-name "<模块名>" `
  --global-context "global/project-context.md" `
  --requirement-source "path/to/module-requirement.md"
```

脚手架只创建结构并复制明确提供的需求来源，不会完成语义分析。生成后仍必须读取真实资料，替换全部占位内容并执行强校验。

数据库相关模块：

```powershell
python -X utf8 -B "$SkillDir/scripts/scaffold_preanalysis.py" `
  "$ModuleRoot" `
  --module-name "<模块名>" `
  --global-context "global/project-context.md" `
  --requirement-source "path/to/module-requirement.md" `
  --with-data-closures `
  --data-source "global/source-materials/database-docs/schema.md" `
  --data-source-id "SRC-DB-SCHEMA" `
  --data-closure-title "<业务数据路径>"
```

`--with-data-closures` 必须配合真实 `--data-source`；它只创建 DC 索引和首张卡片骨架，不推测表、字段、连接或过滤。无数据库依赖时不要创建空 DC 目录。

仅重新计算规范 manifest 路由时：

```powershell
python -X utf8 -B "$SkillDir/scripts/scaffold_preanalysis.py" `
  "$ModuleRoot" --refresh-manifest
```

不要为了刷新 manifest 使用 `--force`。`--force` 会覆盖已生成的分析骨架，虽然不会覆盖模块需求包，但仍可能破坏人工维护的 Context Pack、map 或问题清单。

## 8. 脚手架参数

| 参数 | 默认值 | 用途 |
|---|---:|---|
| `target_dir` | 必填 | 新用法中表示模块工作区根目录，产物写入其 `preanalysis/` 子目录。 |
| `--module-root <path>` | 无 | 旧 CLI 兼容入口：把 `target_dir` 当作前置分析目录；新模块不要使用。 |
| `--test-points-dir <path>` | `<module-root>/test-points` | 写入 manifest 的后续测试点输出目录。 |
| `--module-name <name>` | 模块目录名 | Markdown 标题使用的模块名称。 |
| `--global-context <path>` | 无 | 项目全局上下文文件。 |
| `--requirement-source <path>` | 无 | 当需求包不存在时，将明确来源原样复制为 manifest 指向的 `00-module-requirement-pack.md`；模块根已有需求包时忽略复制、原地引用。 |
| `--force` | 关闭 | 覆盖分析骨架；不覆盖模块需求包。只在明确知道会覆盖什么时使用。 |
| `--refresh-manifest` | 关闭 | 只重写规范 manifest 路由值，不要求 `--force`。 |
| `--with-data-closures` | 关闭 | 创建可选 DC 索引和首张闭包卡骨架。 |
| `--data-closure-title <name>` | 默认标题 | 首张 DC 卡的业务数据路径标题。 |
| `--data-source-id <SRC-ID>` | `SRC-DB-SCHEMA` | 首张 DC 卡引用的数据来源资源 ID。 |
| `--data-source <path>` | 无 | schema、SQL、代码或数据库设计来源；启用 DC 时必填。 |

查看当前代码的权威参数：

```powershell
python -X utf8 -B .codex/skills/module-requirement-preanalysis/scripts/scaffold_preanalysis.py --help
```

## 9. 如何判断一个来源范围是不是 RSU

RSU 是完整、原文保真的业务契约，不是句子、字段、测试项或 Markdown 行。先分类，再决定是否建立 RSU：

| 来源示例 | 语义角色 | 正确处理 |
|---|---|---|
| `原型`、图片标题、图片占位 | `visual-placeholder` | `not-rsu`；不可读且可能影响行为时创建问题。 |
| `查询条件包括：` | `structural-container` | 不单独建立 RSU；只作为必要的父级上下文。 |
| `彩票年：下拉选择框……默认为全部` | `independent-contract` | 可独立建立一个 RSU。 |
| `任务 ID；彩票年；创建时间。` | `field-fragment` | 不逐字段建 RSU；并入定义结果列表的复合契约。 |
| 查询结果、排序、分页及完整字段列表 | `composite-contract` | 父规则与完整子项合并成一个 RSU。 |
| 不同状态分别提供不同操作 | 多个 `independent-contract` | 容器不建 RSU，各完整状态行为分别建立 RSU。 |
| 父句描述生成任务、状态变化并进入详情页 | `independent-contract` 或复合契约父句 | 完整父句必须进入 `原文内容`；不能只放在 `父级条件（原文）`。 |

两个重要结论：

- RSU 表不增加“测试项”列。一个完整 RSU 后续可以派生多个测试点，测试意图属于下游阶段。
- `父级条件（原文）` 只保存类似“校验通过后”“任务状态为待核查时”的最小条件。父级中的创建、更新、跳转、提示或展示行为必须由某个 RSU 的 `原文内容` 承载。

详细协议见 [RSU 语义拆分协议](./references/rsu-semantic-partitioning.md)。

## 10. 各前置分析产物的职责

| 文件或目录 | 主要职责 |
|---|---|
| `preanalysis-manifest.json` | 保存模块根目录、六类产物路径、三类固定资源角色和测试点输出目录。 |
| `00-module-requirement-pack.md` | 保存当前模块需求原文，不保存 AI 总结；单一事实源位于 manifest `module_requirement` 指向的路径（模块根或 `preanalysis/`）。 |
| `01-context-pack.md` | 保存模块背景、能力、主链路、已确认逻辑、边界和输入规则。 |
| `02-sentence-test-point-map.md` | 保存来源结构决策、RSU 原文映射、资源索引和来源覆盖。 |
| `03-clarification-questions.md` | 保存已确认/待确认问题、人工结论及回填结果。 |
| `context-cards/` | 保存跨 RSU 可复用的链路、契约和观察位置。 |
| `data-closures/` | 可选；保存最小业务数据路径、表关系、状态、查询和清理契约。 |
| 模块 `preanalysis/README.md` | 保存当前模块前置分析目录的导航和执行入口。 |

完整边界见 [产物职责](./references/artifact-map.md) 和 [固定输出契约](./references/output-contract.md)。

## 11. 更新已有前置分析产物

维护已有模块时，先递归读取当前目录，不能从模板覆盖人工答案。建议按以下顺序同步：

1. 保留已确认 `Q-ID`、答案和回填结果；已有引用需要时允许编号空档，不为“连续好看”强制重排。
2. 更新 Context Pack 中受影响的模块逻辑和边界。
3. 先更新“原文结构与拆分决策”，再更新 RSU 表。
4. 同步“原文来源覆盖检查”的范围、状态和 RSU/Q 引用。
5. 更新受影响的 FC/DC 卡及其索引，确保 map、Context Pack、卡片索引三方一致。
6. 复核 manifest 路径和资源角色；仅路由变化时使用 `--refresh-manifest`。
7. 运行校验；若 RSU、Q、FC、DC 或输入文件改变，后续测试点状态可能变为 `stale`，应由下游重新物化。

已有平铺产物属于兼容布局。除非用户明确要求迁移，不要擅自移动到 `preanalysis/`；迁移会影响相对链接、manifest 路径和既有测试点哈希。

## 12. 强校验

规范目录使用：

```powershell
$SkillDir = ".codex/skills/module-requirement-preanalysis"
$ModuleRoot = "modules/<模块目录>"

python -X utf8 -B "$SkillDir/scripts/validate_preanalysis.py" `
  "$ModuleRoot/preanalysis" --require-canonical-layout
```

既有平铺目录使用：

```powershell
python -X utf8 -B "$SkillDir/scripts/validate_preanalysis.py" "$ModuleRoot"
```

如果 legacy 平铺模块已经在根目录下生成了 `test-points/`，物化输入中的相对链接是以原文件位置为基准，不能从 `test-points/inputs/` 直接解析。手工审核上游时应排除该下游生成目录：

```powershell
python -X utf8 -B "$SkillDir/scripts/validate_preanalysis.py" `
  "$ModuleRoot" --exclude-root test-points
```

规范布局的 `test-points/` 是 `preanalysis/` 的同级目录，本来就不在扫描范围内，无需排除。下游 Skill 会在 legacy 输出目录确实位于前置分析根目录中时自动传入该排除参数。

校验器参数：

| 参数 | 用途 |
|---|---|
| `preanalysis_dir` | 包含前置分析产物和 manifest 的目录。 |
| `--manifest <path>` | 显式指定 `preanalysis/v1` manifest；默认读取前置分析目录内的 manifest。 |
| `--exclude <filename>` | 从 Markdown 链接检查排除指定文件名，可重复。 |
| `--exclude-root <dir>` | 从 Markdown 链接检查排除前置分析目录内的指定目录树，可重复；不能越界或排除整个前置分析目录。 |
| `--require-canonical-layout` | 要求目录严格为 `<module-root>/preanalysis/`，新建产物必须使用。 |

校验至少覆盖：

- manifest schema、相对路径、模块边界、逻辑角色和输出目录。
- 规范目录或 legacy 布局警告。
- 必需文件、章节顺序、固定表头、空单元格和模板占位符。
- 本地 Markdown 链接和稳定资源入口。
- RSU、Q、FC、DC、SRC 的唯一性与引用闭合。
- RSU 原文和父级文字的来源匹配。
- 结构角色、拆分决定、RSU 引用和来源覆盖逐项一致。
- 结构容器、视觉占位和字段碎片没有误建成独立 RSU。
- 可观察父级行为没有只藏在父级条件列。
- DC 的表角色、Join Predicate、过滤、状态、Profile、查询和清理契约。
- 本阶段没有生成测试点、测试方案或测试用例。

脚本返回非零即为失败。警告需要报告和理解；错误必须修复，不能因为文件已经生成就宣称完成。

## 13. 下游交接

校验通过后，`rsu-test-point-generation` 优先读取 manifest，并固定物化：

1. `global_context` 角色对应的项目全局上下文全文。
2. `module_requirement` 角色对应的当前模块需求全文。
3. `module_context` 角色对应的 Context Pack 全文。
4. 当前 `RSU-ID` 的完整映射行。

随后解析当前 RSU 显式声明的 Q、FC、DC、附件、API、数据库、配置、环境及必要支持 RSU。固定资源、直接动态资源和 FC/DC 卡加载实际正文；卡片中的来源资源只保留路径、用途和正文哈希，不递归复制整份附件，也不继承其他 RSU 的所有依赖。若测试点语义确需某个来源原文，必须把聚焦资源 ID 直接写入当前 RSU 的“相关上下文”。

如果上游仍存在 `pending`、`pending-context`、未回答问题、失效链接、来源不匹配或父级隐藏行为，下游必须阻塞。不要在测试点候选中临时补造缺失的上游需求。

## 14. 常见问题

### 模块 `README.md` 和 `01-context-pack.md` 是否重复？

不重复。README 是目录导航与执行入口，Context Pack 是模块业务逻辑和边界的权威语义输入。保持两者各自职责，避免在 README 复制大段业务内容。

### 为什么 map 仍叫 `02-sentence-test-point-map.md`？

这是历史兼容文件名。文件内容现在统一使用 `RSU-ID`，表示原文需求单元，不表示按句子拆分，也不是测试点文件。不要只为名称好看重命名并破坏现有链接和 manifest。

### 一行或一个编号是否等于一个 RSU？

不是。编号和换行只是边界线索。一个编号可能只是结构容器；父规则和多个字段子项可能共同形成一个复合 RSU；同一编号范围也可能含多个独立契约，需要先细分来源范围。

### 为什么 `原型` 不能单独成为 RSU？

单独的“原型”或图片标题没有可执行文字行为，属于 `visual-placeholder`。图片中不可读但可能影响验证的内容应进入问题和覆盖状态，不应创建内容仅为“原型”的伪 RSU。

### 为什么父级条件会触发错误？

父级条件只允许保存最小上下文。若它同时描述生成、状态变化、跳转、提示或展示，而没有任何 RSU 的 `原文内容` 完整承载该行为，下游可能漏测，因此校验器会阻止交接。

### 行尾原型图片为什么不参与原文匹配？

Markdown 图片 alt 文本常是 `image.png`，它是视觉占位而不是需求正文。归一化会忽略图片标记，但图片仍可作为来源入口或问题上下文保留。

### 没有数据库依赖也必须创建 Data Closure 吗？

不需要。DC 是一等但可选的上下文类型。纯前端或不依赖数据库状态的模块不创建空 DC 索引、空图或虚构表关系。

### 为什么 legacy 模块校验时出现大量 `test-points/inputs` 断链？

这是生成文件搬运原文后相对链接基准改变造成的扫描噪声，不代表原始前置分析链接都失效。使用 `--exclude-root test-points`，或通过下游新版调用自动排除；不要因此删除原始链接。

## 15. 安全与维护约定

- 新模块统一使用 `preanalysis/`；legacy 迁移必须获得用户明确授权。
- 不使用 `--force` 覆盖已有人工分析，除非已经确认准确目标和影响。
- 不把聊天答案、测试断言或实现猜测写进 RSU 原文。
- 不为减少 RSU 数量合并不同来源契约，也不为追求“原子”拆碎完整契约。
- 不用整文件 `scope-excluded` 掩盖已进入当前层级的附件条款。
- 不在 DC 中记录环境密码或凭命名猜连接。
- 参数默认值以脚本 `--help` 为准；格式契约以 `SKILL.md` 与 `references/` 为准。
- 每次新增能力、缺陷修复、默认值、输出契约或兼容性变化，都应在 [OPTIMIZATION-HISTORY.md](./OPTIMIZATION-HISTORY.md) 追加记录，不覆盖既有历史。
