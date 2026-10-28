# 竞猜赛事运营系统（赛事服务大平台）项目全局上下文

> **文档用途**：供参与本项目需求拆分、迭代深度分析、测试点提炼、测试用例编写及 SQL 数据核验的 AI Agent 使用。本文档沉淀了「竞猜赛事运营系统（北单运营平台 / 赛事服务大平台）」的全局业务背景、四层数据模型、微服务接口契约、**第 13 轮冲刺最新增量需求**以及**本项目严格的 AI 测试工程规范**，方便新开会话时快速建立完整、准确的上下文。
>
> **形成与更新时间**：2026-10-26（基于全量架构分析报告 V1.0 + 第 12 轮冲刺沉淀 + **第 13 轮冲刺 PRD/PBL/竞彩数据库设计**生成）
>
> **当前迭代主题（第 13 轮冲刺）**：
> 1. **中国竞彩（Sporttery）全链路接入**：竞彩足球/篮球赛事、球队、赛程、赛果、最新赔率（9 表）、足球历史赔率（5 表）采集与审计（S619/S620/S621）；**竞彩赛事管理**（PBL-632）、**竞彩球队管理**（PBL-633）、**竞彩赛程监控与备注**（PBL-634）。
> 2. **既有模块优化与扩展**：草稿快速关联球队跳转匹配纳米数据源（PBL-618）、匹配球队智能推荐算法优化（PBL-635）、新建赛季流程调整（PBL-636）、关联球队后名称回填规则优化（PBL-637）、告警异常详情修改（PBL-638）、13 轮操作日志与系统权限扩展（PBL-639），以及草稿添加/保存数据源比赛校验（PBL-599/600）。

---

## 1. AI 测试工程规范与资料权威原则（必读红线）

### 1.1 多方信息源与权威优先级

当不同文档之间出现细节差异时，严格按以下优先级裁决，并将冲突点暴露到「待确认问题」清单：

1. **当前生效需求（最高权威）**：
   - 模块级：`modules/<模块目录>/00-module-requirement-pack.md`（从当前 PRD 确定性切片出的模块需求包）。
   - 全局级：`global/source-materials/current-requirement/竞猜赛事运营系统需求PRD文档-13轮冲刺.md` 与 `赛事运营系统第十三轮冲刺-PBL研发需求.csv`。
2. **需求附件与测试方案（业务判定与测试口径基线）**：
   - **需求附件**：
     - `global/source-materials/current-requirement/attachments/赛事服务大平台数据模型设计.md`（多源比赛状态定义、字段级融合规则、开奖用比分下标映射）。
     - `global/source-materials/current-requirement/attachments/根据赛事特点确定的比赛赛果.md`（各运动项目赛果特殊判定背景）。
   - **历次冲刺测试方案库（高价值测试用例依据）**：
     - `global/source-materials/test-plan/赛事运营系统第十三轮冲刺测试方案.md`（极其重要：涵盖第 13 轮底层数据中心 STORY #619~#622、#626~#631 的功能与接口测试用例集，含 P0/P1/P2 测试项、容错、边界、重复幂等与审计快照断言，是竞彩采集预处理与异常通知测试点设计的核心依据）。
     - `global/source-materials/test-plan/赛事运营系统第十二轮冲刺测试方案.md`（主数据源删除/置换校验测试）。
     - `global/source-materials/test-plan/赛事运营系统第十一轮冲刺测试方案.md`（提交球队筛选优化测试）。
     - `global/source-materials/test-plan/赛事运营系统第十轮冲刺测试方案.md`（比赛进行时间显示修复测试）。
3. **接口与数据库最新契约（底层数据结构与服务定义）**：
   - OpenAPI 规范：`global/source-materials/api-docs/league-core-api/*.json`（8 份微服务 OpenAPI 3.0/3.1 规范）。
   - 实库与全量 DDL：
     - `global/source-materials/database-docs/北单运营系统-test2_newgoal-202610261418.sql`（最新 187 张表 DDL，较 0917 增 34 张、改 4 张）；
     - `global/source-materials/database-docs/北单运营系统-test2_newgoal-202609171050.sql`（153 张表历史基线 DDL）；
     - 测试库连接配置：`global/source-materials/database-docs/database.toml`（192.168.22.218:3306/test2_newgoal 实库验证）。
   - 第 13 轮库表设计：`global/source-materials/database-docs/第十三轮冲刺竞彩抓取数据库设计和变更.md`、`竞彩数据采集模块设计文档-第五段是数据库设计.md`。
4. **全局分析底座与表模块接口追溯矩阵（全域架构指南）**：
   - `global/source-materials/analysis-docs/README.md`
   - `global/source-materials/analysis-docs/竞猜赛事运营系统整体架构与业务逻辑深度分析报告-完整版.md`
   - `global/source-materials/analysis-docs/竞猜赛事运营系统-ER图.md`（9 张分域 Mermaid ER 图，含第 13 轮中国竞彩全链路 ER 图）
   - `global/source-materials/analysis-docs/竞猜赛事运营系统-表模块接口追溯矩阵.md`（表 ↔ 模块 ↔ 接口 ↔ 权限点四方追溯矩阵，已同步实库 149 项权限与第 13 轮增量）
5. **历史需求与旧数据库设计文档（仅供演进与历史对比参考）**：
   - `global/source-materials/history-requirements/竞猜赛事运营系统需求PRD文档-12轮冲刺.md`
   - `global/source-materials/database-docs/赛事数据管理系统数据库设计.md`、`数据采集系统数据库设计.md`（注：早期 md 设计文档部分字段如 `tx_id_match_status` 在实库已演进为 `beitai_id_match_status`，一律以 SQL DDL + 实库为准）。

### 1.2 三大测试工程必读红线

在编写任何分析报告、测试点或测试用例前，必须严格遵守 `global/source-materials/` 下的三份必读规范：

1. **《必读-测试点编写规范.md》——断言四大合法依据与推断隔离**：
   - 测试点/用例中的每一条断言，依据只能是以下四类之一，且必须可追溯：
     - **① 需求原文**（首选，标注文档与章节/条目）；
     - **② 需求方/开发确认**（用户沟通明确给出的结论，标注「已确认」与来源）；
     - **③ 接口/数据契约**（OpenAPI 规范、开发枚举/DDL 定义）；
     - **④ 实库既有数据形态**（仅用于落库格式、存量数据兼容类断言，须标注核验日期）。
   - **严禁把类推、反推、备注推导的内容直接写成测试点断言**（例如把 A 运动的规则类推到 B 运动，或用实库样本反推业务规则）。
   - **推断内容的唯一合法出口是「待确认问题」清单**：必须在 `01-迭代深度分析报告.md` 的「遗留待确认问题」章节与 `test-points/01-迭代测试点.md` 末尾同步列出，且编号互通。需求自身标注「待确认」的规则，按需求当前文字写测试点并在备注标注「需求标注待确认」，同时列入待确认清单。
2. **《必读-需求包标记符号说明.md》——变更符号优先级**：
   - 生效优先级：**`⭐（需求变更，二次调整） > ✅（本次迭代更新） > ~~删除线~~（旧版废弃，不生效）`**。
   - **同级替换**：`⭐` 与 `✅` 出现在同一规则项时，`⭐` 是最新口径，直接替换 `✅`（被作废的旧结论在分析报告和测试点中用删除线保留并注明原因，不静默删除）。
   - **子级例外**：`⭐` 出现在 `✅` 规则的子级时，视为对父规则的**穷尽例外条款**——不在例外中的状态/场景严格按父规则执行。
3. **《必读-需求文档版本管理规则.md》——替换与归档两步走**：
   - `current-requirement/` 下只保留最新生效需求，旧版移入 `history-requirements/<文档名>-V<版本号>.md`。模块需求包 `00-module-requirement-pack.md` 作为迭代工作件直接在原文件更新。

### 1.3 模块化五步产出流水线与内置 Skills

- **内置 Skills（`.codex/skills/`）**：
  1. `module-directory-generator`：仅根据源 PRD 指定章节结构生成 `modules/MOD-xx-xx-<源文档模块名>/` 目录树（源文档是唯一命名依据，不乱加词、不建占位文件，先输出计划经用户确认后再创建）。
  2. `requirement-document-splitter`：根据已确认的 `modules/` 目录树，调用 `document_split_orchestrator.py`（`inspect -> plan -> split -> validate`）将源文档按原始行切片生成各模块下的 `00-module-requirement-pack.md`。
- **单模块标准产出顺序**（参考标杆 `modules/MOD-06-比赛监控/MOD-06-01-比赛赛程监控/MOD-06-01-03-赛果审核/`）：
  ```text
  1. 00-module-requirement-pack.md          ← 模块需求包（输入）
  2. 01-迭代深度分析报告.md                 ← 需求拆解 + ✅/⭐变更影响面 + 实库核验 + 遗留待确认问题
  3. test-points/01-迭代测试点.md           ← 四类合法依据断言 + 待确认问题引用 + 已确认结论回填
  4. test-points/gen_test_cases.py & *.xlsx ← 按 global/source-materials/template/功能测试用例-模板.xlsx 生成十列标准 Excel（归档至 test-cases/）
  5. <模块名>查询.sql                       ← 配套数据造数、映射核验与落库断言 SQL
  ```

### 1.4 全局资料目录结构全景（`global/` 权威索引）

```text
global/
├── project-context.md                                    # [本项目] 全局业务背景与测试工程上下文规范（本文档）
└── source-materials/                                     # 原始输入资料与全局分析底座根目录
    ├── 必读-测试点编写规范.md                              # 必读规范一：断言四大合法依据与推断隔离
    ├── 必读-需求包标记符号说明.md                            # 必读规范二：⭐ > ✅ > ~~删除线~~ 变更优先级
    ├── 必读-需求文档版本管理规则.md                           # 必读规范三：替换与历史归档规则
    ├── 项目全局上下文生成提示词.txt                         # 全局上下文初始化提示词
    ├── current-requirement/                              # 当前生效需求目录（第 13 轮冲刺）
    │   ├── 竞猜赛事运营系统需求PRD文档-13轮冲刺.md           # 第 13 轮 PRD 需求原文（最高权威）
    │   ├── 赛事运营系统第十三轮冲刺-PBL研发需求.csv           # 第 13 轮研发 PBL 清单与 Story 映射
    │   └── attachments/                                  # 需求附件目录
    │       ├── 赛事服务大平台数据模型设计.md                 # 状态映射、比分下标与字段级融合规则
    │       └── 根据赛事特点确定的比赛赛果.md                 # 各运动赛果特殊判定规则
    ├── history-requirements/                             # 历史需求归档目录
    │   └── 竞猜赛事运营系统需求PRD文档-12轮冲刺.md           # 第 12 轮历史 PRD
    ├── test-plan/                                        # 历次冲刺测试方案库（高价值测试用例依据）
    │   ├── 赛事运营系统第十三轮冲刺测试方案.md                # 第 13 轮底层数据中心测试方案（STORY #619~#622、#626~#631）
    │   ├── 赛事运营系统第十二轮冲刺测试方案.md                # 第 12 轮主数据源删除/置换校验测试方案
    │   ├── 赛事运营系统第十一轮冲刺测试方案.md                # 第 11 轮提交球队筛选优化测试方案
    │   └── 赛事运营系统第十轮冲刺测试方案.md                 # 第 10 轮比赛进行时间显示修复测试方案
    ├── test-cases/                                       # 测试用例沉淀目录（分层治理）
    │   ├── functional-test-cases/                        # 功能测试用例目录（按模块沉淀 Excel/Markdown）
    │   └── script-test-cases/                            # 自动化脚本、接口与造数断言用例目录
    ├── template/                                         # 标准用例与交付物模板
    │   └── 功能测试用例-模板.xlsx                           # 十列标准功能测试用例 Excel 模板
    ├── analysis-docs/                                    # 系统级深度分析底座（已同步第 13 轮与 2026-10-26 实库）
    │   ├── README.md                                     # 分析文档导读与表数/权限基线
    │   ├── 竞猜赛事运营系统整体架构与业务逻辑深度分析报告-完整版.md # 全域深度分析报告（微服务/流水线/状态机）
    │   ├── 竞猜赛事运营系统-ER图.md                       # 9 张分域 Mermaid ER 图（含第 13 轮中国竞彩域）
    │   └── 竞猜赛事运营系统-表模块接口追溯矩阵.md             # 表 ↔ 模块 ↔ 接口 ↔ 权限点四方追溯矩阵
    ├── api-docs/                                         # 微服务 OpenAPI 规范与契约
    │   └── league-core-api/                              # 8 份微服务 OpenAPI 3.0/3.1 JSON 规范
    └── database-docs/                                    # 数据库设计文档、配置与 SQL Dump
        ├── database.toml                                 # 测试库 MySQL 连接配置（192.168.22.218:3306/test2_newgoal）
        ├── 北单运营系统-test2_newgoal-202610261418.sql     # 2026-10-26 最新 DDL（187 表，+34 新表 / 4 改动表）
        ├── 北单运营系统-test2_newgoal-202609171050.sql     # 2026-09-17 基线 DDL（153 表）
        ├── 第十三轮冲刺竞彩抓取数据库设计和变更.md             # 第 13 轮竞彩抓取 DDL、增量字段与存量迁移脚本
        ├── 竞彩数据采集模块设计文档-第五段是数据库设计.md       # 竞彩 7 个采集接口与 20 张表详细设计
        ├── 数据采集系统数据库设计.md                         # 早期数据采集设计
        └── 赛事数据管理系统数据库设计.md                     # 早期数据中心设计

---

## 2. 项目背景与整体业务运转逻辑

### 2.1 系统定位

本系统是**体育彩票「北京单场」（北单）竞猜游戏的中后台运营平台**，同时也是「赛事服务大平台」的核心中枢，处于**「上游多方赛事数据源」**与**「下游体彩中心北单游戏系统 / 对外数据消费方」**之间：

```text
┌────────────────────────┐   ┌──────────────────────────────────────┐   ┌────────────────────┐
│ 上游外部数据源          │   │           赛事服务大平台              │   │ 下游系统与外部消费方 │
│ • 贝泰/SportRadar(主源) │   │  数据采集(data-collection)           │   │ • 北单游戏系统(V2)  │
│ • 纳米数据(四运动辅/单源)│──▶│    ↓ 预处理与标准化(data-computation) │──▶│   (SFTP 8类加密文件)│
│ • 同行数据(足球)        │   │  数据中心(s_match / s_event)         │   │ • 外部业务方        │
│ • 中国竞彩网(13轮新增)  │   │    ↓ 运营编排与风控(data-bff/backend) │   │   (openapi v1 网关) │
│ • 运营人工录入(m_*)     │   │  【竞猜赛事运营系统(前端+管理后台)】   │   └────────────────────┘
└────────────────────────┘   └──────────────────────────────────────┘
```

- **对北单游戏系统的文件级交互（SFTP）**：不直接走 RPC 修改体彩中心库，而是将运营确认后的数据打包为 **8 类 V2 标准文件**（`A1` 创建奖期赛程、`A2` 导入赛果、`A3` 追加比赛、`A4` 导入赛事、`A5` 导入球队，以及修改类的 `B1` 修改赛程、`B2` 修改赛果、`B3` 预设开奖时间），按 `JSON -> 加密签名 -> ZIP -> 上传 SFTP 按日期目录`（或线下下载）流转，并在本地 `bd_submit_batch.detail` 保存完整 JSON 快照。
- **对北单官网状态的回读闭环**：通过抓取北单官网（`bjlot.com` 七玩法 XML 落表 `bjlot_match`）自动回写批次与比赛的「已开售」「已开奖」状态。
- **对外数据开放服务（`openapi v1`）**：提供 `/v1/bdlottery/match/list` 及 `/v1/football/*` 共 9 个只读接口（HMAC-SHA256 签名鉴权 + `X-OpenAPI-Time` 防重放 + QPS/FIXED_WINDOW/COOLDOWN 限流）。

### 2.2 核心业务域与基础概念

1. **运动项目（15 项，字典 `league_sport_id`）**：
   - 12 个单项运动：足球(`1`)、篮球(`2`)、网球(`6`)、橄榄球(`13`)、冰球(`14`)、排球、羽毛球、乒乓球、沙滩排球、曲棍球、手球、水球；
   - 3 个团体运动：乒乓球团体、羽毛球团体、网球团体。
   - **数据源覆盖关系**：
     - **足球(`1`)**：贝泰（主数据源 `source_type=3`）+ 纳米（辅数据源 `source_type=1`）+ 同行（`source_type=2`）+ **竞彩（第 13 轮新增 `source_type=4`）**；
     - **篮球(`2`)**：纳米（单源计算）+ **竞彩（第 13 轮新增 `source_type=4`）**；
     - **冰球(`14`)、橄榄球(`13`)**：纳米（单源计算）；
     - **其他无源运动（如网球等）**：依赖人工录入（`m_match` 自动同步至 `s_match`）。
2. **三大北单竞猜游戏（`game_type` / `game_id`）**：
   - **`1200` 足球单场**（仅足球）：下辖 5 个子玩法——`200` 胜平负、`210` 上下盘单双、`230` 总进球、`240` 半全场胜平负（界面简称「半全场」）、`250` 单场比分。任开 1 个子玩法即拥有「单场场次编号」（`game1200_matchup_no`）。
   - **`1260` 下半场比分**（仅足球）：子玩法 `260`，拥有独立场次编号（`game1260_matchup_no`）与独立下半场停售时间（`game1260_sale_end_time`）。
   - **`1270` 胜负过关**（全运动项目）：子玩法 `270`，拥有胜负场次编号（`game1270_matchup_no`），提交时最大场次编号须 ≥ 3。
3. **标准化比赛复合状态机（`s_match.status_id`，字典 `s_match_status` 共 40 项）**：
   - 采用 4 位数字编码 `xxyy`（前两位 `xx` = 比赛状态，后两位 `yy` = 北单赛程状态）：
     - `xx` 段：`10` 未开赛、`11` 比赛中、`12` 完场、`13` 推迟、`14` 中断、`15` 腰斩、`16` 取消、`17` 待定（`1700`）；
     - `yy` 段：`00` 未入稿、`01` 已入稿、`02` 赛程已提交、`03` 已开售、`05` 赛果已提交、`06` 已开奖。
   - **通用状态映射口诀（PRD 通用需求）**：
     - **比赛状态（8 态）**：按前两位 `10xx~16xx` 及 `1700` 映射；
     - **入稿状态**：`xx00` 及 `1700` 为「未入稿」，其余均为「已入稿」；
     - **开售状态**：`xx03`、`xx05`、`xx06` 为「已开售」，其余为「未开售」；
     - **开奖状态**：`1206`、`1306`、`1406`、`1506`、`1606` 五个状态码为「已开奖」，其余为「未开奖」。
4. **多人交叉复核风控防线**：
   - **赛程草稿**：个人草稿独立编辑（按 `create_account` 隔离）→ 比赛需完成「已审核→已复核」才允许参与「草稿比对」生成正式版；
   - **赛果确认**：单场比赛需 **≥ 2 人**完成「赛果审核」（`event_match_check` `check_type=2`）且状态、比分一致，方可进行「赛果确认」（注：确认比对时不比较审核所选的数据源标签）；
   - **赛果文件提交**：开奖批次需 **≥ 3 人**点击「完成审核」（`bd_batch_matchup_draw_review`），且批次内比赛赛果全部已确认、无未完成人工异常变更，才可提交 `A2/B2` 赛果文件。

### 2.3 四大核心业务流转链路

#### 链路一：北单赛程编排与发布生命周期
```text
新建奖期(bd_game_draw: 5位奖期号, 开售/停售/开奖时间, 勾选开售游戏)
  ─▶ 新建赛程批次(bd_batch, batch_type=0)
  ─▶ 个人草稿会话式实时编辑(data-bff real-time/* 维护会话, 6个滑签节点 draftProcessNodes 0~5)
       ├─ 添加比赛(过滤非北单赛事/replace_id非空/主源已删/他奖期正式版禁选)
       ├─ 快速关联赛季球队(r_season_team + 13轮新增【匹配纳米数据源】一键跳转)
       ├─ 让球配置(单场|5|整数, 胜负|99.5|以.5结尾, 联动SportRadar欧赔亚盘)
       ├─ 赛程变更旁路处理(schedule-change: 更新至草稿/不更新/删除)
       ├─ 审核与复核
       └─ 草稿保存(先独立只读校验: 停售时间不一致弹窗 + 主数据源删除/置换弹窗 -> 16项完整校验 -> POST固化入库)
  ─▶ 草稿比对(bd_batch_diff_record 联合PK操作锁 + 逐字段差异 bd_batch_matchup_diff)
  ─▶ 生成正式版(bd_batch_matchup: 生成18位唯一编号 matchup_unique_no, 覆盖全员草稿, 唯一回写 s_match 开赛时间/主队/已入稿状态)
  ─▶ 开奖时间草稿与比对(校验草稿与正式版一致 verify/consistent)
  ─▶ 提交/下载文件(赛事A4 / 球队A5 / 比赛A1或A3 -> SFTP + bd_submit_batch 快照 -> s_match 状态推进至 xx02 赛程已提交)
  ─▶ 官网采集(bjlot_match)回写开售状态 -> s_match 推进至 xx03 已开售(开售后草稿侧全部锁定)
```

#### 链路二：比赛监控、赛果审核与开奖管理链路
```text
比赛开售/进行中/完场
  ─▶ 比赛赛程监控列表(按开售后异常事件行标色: 提前红/推迟黄/取消中断腰斩橙/球队变更绿; 足球比赛中融合贝泰live时钟)
  ─▶ 填写监控记录(POST /monitor: 无变动/新增异常/新增预警 -> 人工生成 s_event + task)
  ─▶ 赛果审核(event_match_check, check_type=2):
       ├─ 足球展示【贝泰数据】【纳米数据】双标签(默认贝泰, nami_match_id为空时纳米置灰; 切换标签重置表单)
       ├─ 非足球不展示数据源标签(直接读标准化 s_match)
       ├─ 贝泰标签/非足球读 s_match 状态与开奖比分; 纳米标签读 nami_football_match 状态与 home/away_scores[0]全场/[1]半场(未开赛status=1不显示比分)
       └─ 提交写入 data_source_type(1纳米/3贝泰/非足球NULL) 及 change_info JSON(statusId + 四比分, 非完场固定 -1:-1)
  ─▶ 赛果确认/批量确认(check -> diff -> confirm: ≥2人审核结果一致, 回写 bd_batch_matchup 与 s_match)
  ─▶ 开奖管理-赛果批次(bd_batch batch_type=1 -> 范围/计划添加比赛 -> ≥3人完成批次审核)
  ─▶ 提交/下载赛果文件(A2/B2 -> s_match 推进至 xx05 赛果已提交 -> 官网开奖采集推进至 xx06 已开奖)
```

#### 链路三：异常事件识别、告警核实确认与变更管理闭环
```text
事件三通道(data-computation 17条自动检测规则 / 人工填写监控记录 / 赛程状态识别)
  ─▶ 生成幂等事件 s_event(event_type: 0无异常 / 1比赛异常 / 2数据异常 / 3预警)
  ─▶ 事件处理器分发任务 task + SSE 实时通知(notification)
  ─▶ 告警管理:
       ├─ 告警核实(event_match_check check_type=1: 确有变动/无变动)
       ├─ 异常确认(event/confirm: 需至少1人已核实; 选择"确认为比赛异常"+级联原因 或 "解除告警"; 确认后按异常类型联动更新 s_match 并推送至变更管理)
       └─ 13轮新增【修改】(PBL-638: 已确认/已解除状态下可修改异常详情 attribution_desc)
  ─▶ 变更管理(task_operation_record):
       ├─ 6种处理操作: 记录在案 / 调整停售时间 / 开奖延后 / 退票(-1:-1) / 争议赛果 / 按实际结果开奖
       ├─ 状态流转: 新建处理 -> (部分操作需人工完成确认 completed / 支持取消完成 task/cancel) / 支持处理作废 voided
       └─ 导出变更单(report/change_matchup/6)与变更公告(report/event_notice_export)
```

---

## 3. 当前迭代需求基线（第 13 轮冲刺全量拆解）

第 13 轮冲刺共包含 **9 个研发需求（PBL-618、632~639）**、**2 个草稿校验补充项（PBL-599/600）** 以及底层的 **中国竞彩数据采集与存储模块（S619/S620/S621）**。

### 3.1 底层基建：中国竞彩（Sporttery）数据采集与事件任务（S619 / S620 / S621）

- **上游数据源（`webapi.sporttery.cn` 7 个接口）与 `data-collection` 7 个 POST 调度接口**：
  1. `POST /sporttery/football/schedule`（足球受注赛程 `getMatchListV1.qry?clientCode=3001`）→ 幂等落库 `sporttery_football_team`、`sporttery_football_league`、`sporttery_football_match`；
  2. `POST /sporttery/football/odds`（足球混合过关赔率 `getMatchCalculatorV1.qry?channel=c`）→ 按 `HAD/HHAD/CRS/TTG/HAFU` 写入足球 5 张最新赔率表；
  3. `POST /sporttery/football/odds/record`（足球历史赔率 `getFixedBonusV1.qry?clientCode=3001&matchId={id}`）→ 写入足球 5 张 `*_odds_record` 历史表（主键 `match_id + release_time`），并回写已有最新赔率表；
  4. `POST /sporttery/football/result`（足球赛果 `getUniformMatchResultV1.qry`）→ 分页去重，仅回写已有足球赛程的 `home_half_score`/`away_half_score`、`home_score`/`away_score`；
  5. `POST /sporttery/basketball/schedule`（篮球受注赛程 `basketball/getMatchListV1.qry?clientCode=3001`）→ 幂等落库 `sporttery_basketball_team`、`sporttery_basketball_league`、`sporttery_basketball_match`；
  6. `POST /sporttery/basketball/odds`（篮球混合过关赔率 `basketball/getMatchCalculatorV1.qry?channel=c`）→ 按 `MNL/HDC/HILO/WNM` 写入篮球 4 张最新赔率表；
  7. `POST /sporttery/basketball/result`（篮球赛果 `getUniformBasketballMatchResultV1.qry`）→ **注意主客顺序**：接口 `finalScore` 按**「客队比分-主队比分」**返回，存入 `part_end` 为**「客队:主队」**（冒号分隔），同时拆分左值→`away_score`、右值→`home_score` 整型列（注：2026-10-26 实库核验显示存量 10,668 条已开奖记录的 `home_score`/`away_score` 拆分迁移 SQL 尚未执行，当前为 `NULL`）。
- **每轮调度采集顺序**：`赛程 -> 最新赔率 -> 足球历史赔率 -> 赛果 -> 状态推进`（历史赔率必须在赛果将状态推进为 `3-已开奖` 之前执行，以免候选比赛被过滤）。
- **字段缺失与保护规则**：
  - 关键 ID（`matchId`/`leagueId`/`homeTeamId`/`awayTeamId`）任一缺失：跳过该场写入与状态推进，记 `WARN` 日志，不阻断同批其他比赛；
  - 可空字段缺失：新记录存 `NULL`，**已有记录遇到上游 `NULL`/空串时保留库内旧值不被覆盖**；
  - 本地预处理维护字段（`s_match_id`、`if_change`）：**采集服务在任何情况下均不读取、不写入、不清空、不覆盖**（新增保持 `NULL`，刷新保留原值）；
  - 赛程新增/修改及赛果回写均在事务内通过 JPA 写入 Envers 审计表 `audit_sporttery_football_match` / `audit_sporttery_basketball_match`。

### 3.2 新增模块一：竞彩赛事管理（PBL-632，基础信息管理 -> 竞彩赛事管理）

- **（1）赛事列表**：
  - **查询条件**：
    - 运动项目：下拉单选（全部、足球、篮球，默认全部）；
    - 匹配状态：下拉单选（全部、未匹配、已匹配，默认全部）；
    - 赛事名称：输入框，默认空，匹配赛事简称、赛事全称，支持模糊查询、忽略英文大小写。
  - **查询结果**：未删除的竞彩赛事列表（来源 `sporttery_football_league` / `sporttery_basketball_league` 结合 `r_sporttery_basic_data`），按**更新时间倒序**排列，支持分页。
  - **交互**：【重置】恢复默认条件但不刷新列表；点击行内【匹配】跳转「竞彩赛事匹配」页。
- **（2）匹配赛事**：
  - **顶部信息**：显示当前竞彩赛事的运动项目、赛事全称、赛事简称、匹配状态（已匹配/未匹配），以及**当前时间前后各 5 场**该赛事的竞彩赛程信息（按开赛时间正序排列）。
  - **匹配区查询**：赛事名称输入框，**默认带入当前竞彩赛事的赛事简称**，从标准化赛事（`m_competition`）的赛事简称、赛事全称、英文名称中模糊查询（忽略大小写），**必填，不少于 2 个字符宽度**。
  - **匹配区结果**：已匹配的标准化赛事列表 ∪ 符合查询条件且未删除的当前运动项目下标准化赛事列表，按**匹配状态（已匹配靠前）+ 简称正序**排列，不分页；展示标准化赛事的赛事 ID、赛事简称、赛事全称、英文名称。
  - **联动预览**：点击查询结果中任一标准化赛事行，高亮该行，并在右侧展示**标准化比赛（`s_match`）中该赛事当前时间前后各 5 场比赛信息**（按开赛时间正序）。
  - **勾选与提交**：
    - 支持**多选**勾选标准化赛事；**已匹配的赛事不可取消勾选**；未勾选新项时【匹配】按钮不可点；
    - 点击【匹配】弹窗确认：`是否确认与以下赛事进行匹配：{赛事简称}、{赛事简称}？`；
    - 确认后校验：**所选的标准化赛事未与当前竞彩赛事匹配**，否则提示 `{赛事简称}已匹配`；
    - 校验通过后写入 `r_sporttery_basic_data`（`source_type=4`，含乐观锁 `version`）及审计表 `audit_r_sporttery_basic_data`，刷新并停留在当前页面；点击【返回】回到原列表查询结果。

### 3.3 新增模块二：竞彩球队管理（PBL-633，基础信息管理 -> 竞彩球队管理）

- **（1）球队列表**：
  - **查询条件**：运动项目（全部、足球、篮球，默认全部）、匹配状态（全部、未匹配、已匹配，默认全部）、球队名称（模糊匹配球队简称、球队全称，忽略英文大小写，默认空）。
  - **查询结果**：符合条件且未删除的竞彩球队列表（`sporttery_football_team` / `sporttery_basketball_team`），按**更新时间倒序**排列，支持分页。点击【匹配】进入「竞彩球队匹配」页。
- **（2）匹配球队**（注意与竞彩赛事匹配的差异点）：
  - **顶部信息**：显示当前竞彩球队的运动项目、球队全称、球队简称、匹配状态，以及**当前时间前后各 5 场**该球队的竞彩赛程（按开赛时间正序）。
  - **匹配区查询**：球队名称输入框，**默认带入当前竞彩球队的球队简称**，从标准化球队（`m_team`）的球队简称、球队全称、英文全称中模糊查询（忽略大小写），**必填，不少于 2 个字符宽度**。
  - **匹配区结果**：已匹配的标准化球队 ∪ 符合条件且未删除的同运动项目标准化球队，按**匹配情况（已匹配、可匹配）+ 简称正序**排列，不分页；点击任一行高亮并展示标准化比赛（`s_match`）中该球队当前时间前后各 5 场比赛（按开赛时间正序）。
  - **勾选与提交（★单选约束）**：
    - 不同于赛事匹配的多选，竞彩球队匹配**只可单选**；已匹配的球队不可取消勾选；
    - 点击【匹配】提示：`是否确认与以下球队进行匹配：{球队简称}？`；
    - **双向唯一校验**：
      1. 当前竞彩球队未与其他标准化球队匹配，否则提示 `{当前球队简称}已与其他球队匹配`；
      2. 所选标准化球队未与当前竞彩球队匹配，否则提示 `{当前球队简称}已匹配`（注：具体提示占位符以 PRD 原文与接口返回为准）；
    - 校验通过落库 `r_sporttery_team_data`（`source_type=4`，唯一键 `uk_std_team(sporttery_team_id, sport_id, manual_team_id)`）及 `audit_r_sporttery_team_data`，刷新并停留在当前页面。

### 3.4 新增模块三：竞彩赛程监控（PBL-634，比赛监控 -> 竞彩赛程监控）

- **（1）比赛列表**：
  - **查询条件**：
    - 运动项目：足球、篮球，**支持多选，默认全选**；
    - 业务日：开始日期～结束日期，**默认为 `当前日期` 至 `当前日期 + 6`**；
    - 自动刷新：下拉选择 `关、5s、10s、30s、1m、5m`，**默认为 `关`**（触发刷新时仅更新列表数据，保留查询条件、表头筛选结果及滚动条位置）。
  - **列表展示（按编号正序排列，不分页）**：
    1. 业务日（`business_date`）；
    2. 编号（`match_no`，如「周三 001」）；
    3. 运动项目；
    4. 赛事简称（竞彩赛程所属赛事对应的竞彩简称 `league_name`）；
    5. 开赛时间（`match_time`）；
    6. 主队全称、客队全称（显示竞彩全称 `team_full_name`，主客顺序与竞彩赛程一致）；
    7. 主队排名、客队排名（取关联标准化比赛 `s_match` 中的排名，无则不显示，顺序与主客队一致）；
    8. **比赛状态**：根据关联标准化比赛（`s_match`）的状态映射显示（详见通用需求 8 态）；足球项目为「比赛中」时，融合贝泰直播数据（`live`）的 `match_clock`、`stoppage_clock` 和 `match_status`；**若未关联标准化比赛（`s_match_id` 为空），显示「未匹配」**；
    9. **半场、全场比分**：**已开奖时**显示竞彩赛程自身的比分（`half_score`/`full_score` 或篮球 `part_end`）；**未开奖时**显示系统采集的开奖用比分（`s_match`）；无比分时显示 `-`；比分顺序与主客队一致；
    10. **事件**：显示对应赛程的竞彩事件条数（`sporttery_match_event`），超链接样式，**条数为 0 时置灰**；点击弹窗显示事件记录（事件时间、标题、异常详情，按事件时间倒序排列）；
    11. **备注**：显示对应赛程的备注条数（`sporttery_match_remark`），超链接样式；点击弹出备注框；
    12. **开奖状态**：显示竞彩赛程开奖状态，包含 `未开奖`（`sell_status in (1,2)`）、`已开奖`（`sell_status = 3`）。
  - **异常事件行背景标色规则（按事件更新时间 `update_time` 最大的竞彩事件填充）**：
    - `比赛提前` → **红色**；
    - `比赛推迟` → **黄色**；
    - `比赛取消`、`比赛中断`、`比赛腰斩` → **橙色**；
    - `球队变更` → **绿色**。
  - **列表表头筛选**：
    - `赛事简称`：弹出当前赛程列表涉及的所有赛事简称筛选框；
    - `比赛状态`：未开赛、比赛中、完场、推迟、中断、腰斩、取消，默认全选，支持反选；
    - `事件`：无事件、有事件，默认全选；
    - `备注`：无备注、有备注，默认全选；
    - `开奖状态`：未开奖、已开奖，默认全选。
  - **比赛进程弹窗**：点击「比赛状态」弹出对应比赛进程信息（规则同北单「比赛赛程监控」）。
- **（2）备注弹窗**：
  - 标题显示赛程编号；
  - **当前用户的账号及备注信息置顶显示**（无备注时显示空，可编辑，最多 **300 字符**）；
  - **其他用户的账号及备注信息**按备注修改时间**正序**排列（无备注时不显示，只读）；
  - 点击【保存】写入 `sporttery_match_remark`（`remark_type=1`，唯一键 `sport_id + remark_type + match_id + create_account`）及审计表 `audit_sporttery_match_remark`，关闭弹窗并刷新页面；点击【取消】关闭不更新。

### 3.5 既有模块优化与扩展（PBL-618 / 635 / 636 / 637 / 638 / 639 / 599 / 600）

| PBL 编号 | 所属模块 | 迭代变更规则要点（`✅` 标记） |
| --- | --- | --- |
| **PBL-618** | 北单赛程管理 -> 草稿管理 -> 快速关联球队 | 点击未关联标识弹出「快速关联球队」弹窗时，新增 **【匹配纳米数据源】** 按钮：<br>1. 判断当前球队是否已匹配纳米数据源（`m_team.nami_id_match_status` / `r_team_data`），**未匹配时显示按钮，已匹配时隐藏**；<br>2. 点击打开浏览器**新标签页**进入「球队管理 - 匹配球队」页面，定位到当前球队；<br>3. 匹配球队页**默认选中「纳米数据」标签页**，且「球队名称」筛选框**默认填入当前选中球队的球队简称**；<br>4. 不影响原弹窗正常关联赛季球队流程。 |
| **PBL-635** | 基础信息管理 -> 球队管理 -> 匹配球队 | **智能推荐算法优化**：当球队 A 数据源已匹配、B 数据源未匹配且处于【B 数据】标签页点击【智能推荐】时，第 1 步取数由旧版「获取 A 数据源中该球队最新的 10 场比赛」改为 **「获取 A 数据源中已匹配的赛季下该球队当前时间前后各 5 场比赛」**，再按相同开赛时间、同一赛季、相同主客角色统计 B 数据源球队出现频次最高者（按简称正序排列）。 |
| **PBL-636** | 基础信息管理 -> 赛事管理 -> 新建赛季 | **新建赛季匹配后停留在当前页**：创建赛季成功进入该赛季的匹配页面后，按钮文案由【匹配并继续】改为 **【匹配】**；确认匹配校验通过后，由旧版「跳转至当前赛季的关联球队页面」改为 **「刷新并停留在当前页面」**。 |
| **PBL-637** | 基础信息管理 -> 赛事管理 -> 关联球队 | **关联球队后名称回填规则优化**：在赛季下点击【关联】确认并完成当前赛季下（本赛季）北单全称/北单简称非空且唯一校验后，新增回填判断：<br>若数据中心球队（`m_team`）的 **北单全称** 或 **北单简称** 为空，且（本赛季）北单全称在当前运动项目下（不含当前球队）的 `球队全称`、`北单全称` 均唯一，同时（本赛季）北单简称在当前运动项目下（不含当前球队）的 `球队简称`、`北单简称` 均唯一，则**用（本赛季）北单全称同时更新 `m_team` 的 `球队全称` 和 `北单全称`，用（本赛季）北单简称同时更新 `m_team` 的 `球队简称` 和 `北单简称`**。 |
| **PBL-638** | 异常管理 -> 告警管理 | **异常详情修改**：<br>1. 告警列表在确认状态为 **「已确认」「已解除」** 时，操作列除【备注】外新增 **【修改】** 按钮可用；<br>2. 点击【修改】弹出「修改详情」弹窗，展示信息同「告警详情」；<br>3. **「异常详情」**（`task.attribution_desc`）可编辑，支持汉字、字母、数字和字符，长度 **≤ 300 个字符数**；<br>4. 点击【保存】调用 `POST /data-backend/monitor/attribution-desc` 更新异常详情，关闭弹窗并刷新页面；点击【取消】关闭不更新。 |
| **PBL-639** | 操作日志 & 系统权限 | **第 13 轮权限与操作日志扩展**：<br>1. **新增 7 个权限点（`toto_permission` ID 147~153）**：<br>   • `异常管理 - 告警管理 - 修改`（ID 147，`POST /data-backend/monitor/attribution-desc`）<br>   • `基础信息管理 - 竞彩赛事管理 - 查询 / 匹配`（ID 148 / 149）<br>   • `基础信息管理 - 竞彩球队管理 - 查询 / 匹配`（ID 150 / 151）<br>   • `比赛监控 - 竞彩赛程监控 - 查询 / 备注`（ID 152 / 153）<br>   （未开启任何权限的模块/菜单整项隐藏）<br>2. **新增 4 类操作日志（`toto_operation_record`）**：<br>   • `基础信息管理` - `竞彩赛事匹配`（竞彩赛事匹配页的【匹配】按钮）<br>   • `基础信息管理` - `竞彩球队匹配`（竞彩球队匹配页的【匹配】按钮）<br>   • `比赛监控` - `竞彩赛程备注`（竞彩赛程监控页备注弹窗的【保存】按钮）<br>   • `异常管理` - `修改详情`（告警管理页修改详情弹窗的【保存】按钮） |
| **PBL-599 / 600** | 北单赛程管理 -> 草稿管理 & 添加比赛弹窗 | • **草稿保存前置双弹窗校验（PBL-599）**：在 16 项完整校验前依次执行：① 停售时间与下半场停售时间不一致确认弹窗（可继续保存）；② 主数据源比赛已删除或置换确认弹窗（可继续保存）；<br>• **添加比赛弹窗过滤（PBL-600）**：不显示非北单赛事、`replace_id` 非空、主数据源已删除或置换的比赛；在其他奖期正式版已添加的比赛置灰禁选；移除了旧版「球队未关联赛季置灰」「赛季无北单简称/全称置灰」的限制。 |

---

## 4. 四层数据模型与核心表关系

测试库 `test2_newgoal`（MySQL 8.0，`utf8mb4_bin` 区分大小写排序规则）全库无物理外键，全部通过应用层逻辑外键关联。核心表按四层分域：

### 4.1 四层表结构全景

| 分层 | 表前缀 / 集合 | 核心职责与第 13 轮新增表（★） |
| --- | --- | --- |
| **1. 采集层** | `beitai_*`<br>`nami_*`<br>`tx_*`<br>`bjlot_match`<br>★ `sporttery_*` | 外部数据源镜像（采集服务只增/幂等更新，不改业务预处理字段）：<br>• **贝泰**：`beitai_football_match`（13轮新增 `coverage_scores` 标识 `live/post`）、`beitai_football_match_live`、`beitai_football_event` 等 ~11 表；<br>• **纳米**：`nami_football_match`、`nami_basketball_match`、`nami_ice_hockey_match`、`nami_american_football_match` 等 ~35 表；<br>• **北单官网**：`bjlot_match`（七玩法 XML 抓取）；<br>• ★ **中国竞彩（13轮新增 20 表）**：<br>  - 档案与赛程：`sporttery_football_team`、`sporttery_football_league`、`sporttery_football_match`、`sporttery_basketball_team`、`sporttery_basketball_league`、`sporttery_basketball_match`；<br>  - 足球最新赔率（5表，PK=`match_id`）：`sporttery_football_{had,hhad,crs,ttg,hafu}_odds`；<br>  - 篮球最新赔率（4表，PK=`match_id`）：`sporttery_basketball_{mnl,hdc,hilo,wnm}_odds`；<br>  - 足球历史赔率（5表，PK=`match_id, release_time`）：`sporttery_football_{had,hhad,crs,ttg,hafu}_odds_record`。 |
| **2. 标准层** | `s_match`<br>`s_event` | 多源数据收敛与标准化核心：<br>• `s_match`：全系统比赛唯一身份收敛点（含 `beitai_match_id`、`nami_match_id`、`tx_match_id`、`manual_match_id`、`replace_id`、`status_id` 40 项复合状态、开奖用半全场比分 `home/away_score_half` & `home/away_score`）；<br>• `s_event`：北单标准层幂等事件表（`event_id` 由 `identity_data` 哈希生成）。 |
| **3. 运营与关系层** | `m_*`、`r_*`<br>`bd_*`<br>`task*`<br>`event_match_check`<br>★ `sporttery_match_*`<br>★ `sporttery_task` | • **人工主数据（`m_*`）**：`m_competition`、`m_season`、`m_team`、`m_match`、`m_match_remark`、`m_competition_blacklist`、`m_team_blacklist`；<br>• **多源匹配关系（`r_*`）**：<br>  - 既有：`r_basic_data`（赛事/赛季匹配，`source_type` 1纳米/2同行/3贝泰）、`r_team_data`（球队匹配）、`r_season_team`（赛季关联球队，三唯一键）；<br>  - ★ **13轮新增**：`r_sporttery_basic_data`（竞彩联赛匹配标准化赛事，`source_type=4`，含乐观锁 `version`）、`r_sporttery_team_data`（竞彩球队匹配标准化球队，`source_type=4`，唯一键 `uk_std_team`）；<br>• **北单赛程与开奖（`bd_*`）**：`bd_game_draw`（奖期）→ `bd_batch`（0赛程批次/1开奖批次）→ `bd_batch_matchup_draft`（个人草稿）→ `bd_batch_diff_record` / `bd_batch_matchup_diff`（比对锁与差异）→ `bd_batch_matchup`（正式赛程）→ `bd_batch_matchup_draw` / `bd_batch_matchup_draw_review`（赛果批次与≥3人审核）→ `bd_submit_batch`（SFTP 文件提交快照）；<br>• **北单监控/异常/变更**：`task`、`task_operation_record`、`event_match_check`（`check_type=1` 告警核实 / `check_type=2` 赛果审核，含 12 轮新增 `data_source_type` 列）；<br>• ★ **竞彩监控/异常/备注（13轮新增 3 表）**：`sporttery_match_event`（竞彩异常事件，`source_type='SPORTTERY'`）、`sporttery_task`（竞彩异常任务）、`sporttery_match_remark`（竞彩监控备注，`remark_type=1`）。 |
| **4. 支撑与审计层** | `toto_*`<br>`openapi_*`<br>`revinfo` / `audit_*` | • **权限与日志**：`toto_account`、`toto_role`、`toto_permission`（`urls` JSON 绑定接口路径+Method）、`toto_operation_record`（操作日志）、`toto_dict`（481+ 字典项）、`toto_config`；<br>• **Envers 实体审计（`audit_*`）**：全域覆盖（`revtype`: 0新增/1修改/2删除），★ **13轮新增 5 张竞彩审计表**：`audit_sporttery_football_match`、`audit_sporttery_basketball_match`、`audit_r_sporttery_basic_data`、`audit_r_sporttery_team_data`、`audit_sporttery_match_remark`。 |

### 4.2 竞彩数据域与标准层关联关系图（第 13 轮重点）

```text
sporttery_football_league / sporttery_basketball_league (官方 league_id)
       │ (sporttery_league_id + sport_id)
       ▼
r_sporttery_basic_data (source_type=4, version) ──▶ m_competition (manual_competition_id)

sporttery_football_team / sporttery_basketball_team (官方 team_id)
       │ (sporttery_team_id + sport_id, uk_std_team)
       ▼
r_sporttery_team_data (source_type=4) ────────────▶ m_team (manual_team_id)

sporttery_football_match / sporttery_basketball_match (官方 match_id)
       ├── s_match_id (由预处理写入, 采集不碰) ───▶ s_match (读取标准比赛状态、主客排名、未开奖时的开奖比分、贝泰直播时钟)
       ├── (sport_id + source_id=match_id) ──────▶ sporttery_match_event ──▶ sporttery_task
       └── (sport_id + match_id, remark_type=1) ─▶ sporttery_match_remark (uk: sport_id+remark_type+match_id+create_account)
```

---

## 5. 微服务架构与接口契约全景

### 5.1 八大微服务分工

| 服务名 | OpenAPI 规范文件 | 核心职责 |
| --- | --- | --- |
| **data-bff** | `data-bff-openapi.json` | 前端直接调用的聚合层：**132 个透传代理接口**（`/data-backend/*`）+ **26 个自营接口**（草稿/赛果批次 `real-time/*` 会话态编辑、报表导出 `/report/*`、Excel 两段式导入 `/upload/*`、文件下载 `/download/*`、双因子 `/otp/*`、操作日志查询 `/operation/record`）。 |
| **data-backend** | `data-backend-openapi.json` | 运营域核心后端（162+ 路径）：奖期、批次、草稿固化、正式赛程、监控、审核、异常、变更、开奖、基础数据 CRUD 与多源匹配、黑名单、SportRadar 赔率查询、`/lock` 分布式锁。 |
| **data-collection** | `data-collection-openapi.json` | 外部数据源采集服务：纳米四运动（init/update）、贝泰、同行、SportRadar 早盘赔率、北单官网 XML，以及**第 13 轮新增的 6 个中国竞彩调度采集接口**。 |
| **data-computation** | `data-computation-openapi.json` | 预处理与异常识别：各运动比赛标准化计算（足球贝泰主+纳米辅，其余纳米单源）、球队标准化、北单/竞彩比赛预处理、17+ 条异常检测规则与事件处理分发。 |
| **league-backend / bff** | `league-*-service-openapi.json` | V1 老系统（北单 2.0）：目前仍在承担账号管理（`manager_account`）、角色权限等底层服务，由 `data-bff` 代理编织。 |
| **notification** | `notification-openapi.json` | 消息通知服务：基于 SSE（`/api/notifications/{accountId}`）+ RabbitMQ + Redis 向前端实时推送告警与变更通知。 |
| **openapi** | `openapi-openapi.json` | 对外开放 API 网关（`/v1/*`）：HMAC-SHA256 鉴权 + 多策略限流。 |

### 5.2 统一响应与错误码契约

跨服务接口统一返回结构 `{"code": 0, "message": "...", "data": ...}`（或 `errorCode`）：
- `code = 0`：成功；
- `code = 2`：业务校验失败（前端直接展示返回的业务提示文案，如唯一性冲突、状态不允许操作等）；
- `code = 31`（或 `3x`）：服务内部异常（统一提示「服务异常」）；
- HTTP `400`：参数类型或格式不合法。

### 5.3 第 13 轮冲刺新增核心接口速查

1. **业务端接口（`data-bff` -> `data-backend`，源自 `toto_permission` 147~153）**：
   - **告警异常详情修改（PBL-638，权限 147）**：
     - `POST /data-backend/monitor/attribution-desc`
   - **竞彩赛事管理（PBL-632，权限 148 查询 / 149 匹配）**：
     - `GET /data-backend/sporttery/competition`（竞彩赛事列表）
     - `GET /data-backend/relations/sporttery/competition/candidates`（待匹配标准化赛事候选查询）
     - `GET /data-backend/relations/sporttery/competition/source-matches`（当前竞彩赛事前后 5 场竞彩赛程）
     - `GET /data-backend/relations/sporttery/competition/match-preview`（选中标准化赛事前后 5 场标准化比赛预览）
     - `POST /data-backend/relations/sporttery/competition`（提交竞彩赛事匹配）
   - **竞彩球队管理（PBL-633，权限 150 查询 / 151 匹配）**：
     - `GET /data-backend/sporttery/team`（竞彩球队列表）
     - `GET /data-backend/relations/sporttery/team/source-matches`（当前竞彩球队前后 5 场竞彩赛程）
     - `GET /data-backend/relations/sporttery/team/manual-teams`（待匹配标准化球队候选查询）
     - `GET /data-backend/relations/sporttery/team/match-preview`（选中标准化球队前后 5 场标准化比赛预览）
     - `POST /data-backend/relations/sporttery/team`（提交竞彩球队匹配）
   - **竞彩赛程监控（PBL-634，权限 152 查询 / 153 备注）**：
     - `GET /data-backend/sporttery/match-monitor`（竞彩赛程监控列表）
     - `GET /data-backend/sporttery/match-monitor/events`（比赛竞彩事件弹窗列表）
     - `GET /data-backend/sporttery/match-monitor/remarks`（查询比赛备注列表）
     - `POST /data-backend/sporttery/match-monitor/remark`（保存当前用户比赛备注）
2. **采集调度端接口（`data-collection` 内部供调度器调用）**：
   - 足球/篮球受注赛程采集、最新赔率采集、足球历史赔率采集、赛果采集与状态推进共 6 个独立无参调度入口（异常统一返回 `code=31, message="服务异常", data=null`）。

---

## 6. 测试环境连接与四层核验指南

### 6.1 测试数据库配置

- 连接配置文件：`global/source-materials/database-docs/database.toml`
- MySQL 地址：`192.168.22.218:3306`
- 数据库名：`test2_newgoal`（字符集 `utf8mb4`，排序规则 `utf8mb4_bin`）

### 6.2 标准四层核验顺序（UI + API + DB + Audit/Log）

在设计测试点、编写测试用例及执行实库验证时，应覆盖以下四层闭环：

1. **UI 表现与交互层**：
   - 默认筛选条件、排序方向（如更新时间倒序 vs 编号正序 vs 开赛时间正序）、分页/不分页策略；
   - 【重置】按钮通用规则：**仅将查询条件恢复为默认值，不触发列表刷新**；
   - 自动刷新与返回保留规则：自动刷新或从弹窗返回列表时，**保留原有查询条件、表头筛选状态及滚动条位置**；
   - 字符宽度与长度校验：区分「字符数」（如备注 ≤ 300 字符、赛事简称 ≤ 10 字符）与「字符宽度」（如北单全称 ≤ 20 字符宽度、北单简称 ≤ 16 字符宽度、足球赛季北单简称 ≤ 12 字符宽度、匹配搜索框 ≥ 2 字符宽度，通常 1 汉字 = 2 字符宽度、1 英文/数字 = 1 字符宽度，具体边界需覆盖全角/半角混合场景）；
   - 按钮防抖：涉及修改数据的按钮均设 **3s 防抖**。
2. **API 契约与权限拦截层**：
   - 校验正常提交、必填缺失、格式/范围越界、唯一性冲突时的 HTTP 状态码与业务 `code=2` 提示文案是否严格对齐 PRD；
   - 校验未授权角色访问菜单（应隐藏）及直接调用后端接口（应被权限拦截拒绝）。
3. **业务主表与关系表落库层（DB）**：
   - 核对主表（`m_*` / `r_*` / `r_sporttery_*` / `sporttery_*` / `bd_*` / `task*` / `event_match_check`）字段值、唯一键约束、乐观锁 `version` 递增、空值保留策略及多账号数据隔离（`create_account`）。
4. **操作日志与 Envers 审计层（Audit & Log）**：
   - 查 `toto_operation_record`：确认非查询类写操作已记录正确的「操作模块、操作类型、操作结果（成功/失败）、操作用户/账号、操作角色快照、操作时间」；
   - 查对应 `audit_*` 表与 `revinfo`：确认新增（`revtype=0`）、修改（`revtype=1`）、删除（`revtype=2`）均生成完整修订快照。

### 6.3 测试资产分层沉淀与归档规范

为保障 AI 协作与持续迭代中的用例与数据资产规范可追溯，本项目对测试资产实行分层治理：
1. **测试方案（Test Plan）**：
   - 存放于 `global/source-materials/test-plan/`，按冲刺沉淀（如 `赛事运营系统第十三轮冲刺测试方案.md`），作为用例覆盖率和测试项拆解的高优先级输入依据。
2. **测试用例（Test Cases）**：
   - **功能测试用例**：统一沉淀至 `global/source-materials/test-cases/functional-test-cases/`（或对应模块目录下的 `test-cases/` 目录），必须严格基于 `global/source-materials/template/功能测试用例-模板.xlsx` 生成或维护标准 10 列 Excel（用例编号、用例名称、前置条件、操作步骤、预期结果、测试数据、优先级、所属模块、执行结果、备注）。
   - **脚本自动化与造数用例**：统一沉淀至 `global/source-materials/test-cases/script-test-cases/`，维护自动化断言脚本、API 批量校验脚本以及 SQL 数据准备与落库断言脚本（如 `<模块名>查询.sql`）。

---

## 7. 已知架构风险与测试重点关注事项

1. **全库无物理外键 + 跨源 ID 域隔离**：
   - 竞彩足球与竞彩篮球的官方 `league_id`、`team_id`、`match_id` 各自独立，存在同值可能，因此所有关联表（`r_sporttery_basic_data`、`r_sporttery_team_data`、`sporttery_match_event`、`sporttery_match_remark`）**必须同时携带 `sport_id`（足球=1，篮球=2）进行区分**。测试时需重点构造或验证「足球与篮球存在相同 ID」或「跨运动项目筛选/匹配」的隔离性。
2. **竞彩篮球比分主客顺序翻转**：
   - 中国竞彩官网篮球接口返回的赛果比分是「客队在前、主队在后」，而本系统内部展示与存储统一要求「主客顺序与竞彩赛程一致（主队在前、客队在后）」。测试竞彩篮球赛果采集与「竞彩赛程监控」比分展示时，必须核对主客得分是否已正确翻转对齐。
3. **竞彩赛程监控「已开奖 vs 未开奖」双轨比分来源**：
   - 竞彩赛程监控列表中，**未开奖**（`sell_status in (1,2)`）显示标准化比赛 `s_match` 的开奖用比分；**已开奖**（`sell_status = 3`）切换为显示竞彩赛程表自身的比分（`half_score`/`full_score` 或篮球 `part_end`）。这一切换点是极高价值的测试点。
4. **文档滞后与四类依据纪律**：
   - 历史数据库设计 Markdown 与实库存在多处演进差异，遇到文档未明文规定或实库存在例外的场景，严格遵循《必读-测试点编写规范.md》，通过「待确认问题」清单向用户暴露并确认，绝不自行脑补断言。
