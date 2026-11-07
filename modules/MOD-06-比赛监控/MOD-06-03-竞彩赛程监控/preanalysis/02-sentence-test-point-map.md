# MOD-06-03 竞彩赛程监控原文需求单元映射

## 定位

本文件保存需求原文到语义完整原文单元的无损映射，不是正式测试点、测试方案或测试用例。原文内容保持当前模块需求包中的文字；前端行为仍保留为功能 RSU，接口字段另在相关 RSU 中体现。

## 引用入口

| 资源 ID | 可点击文件 | 定位用途 |
|---|---|---|
| SRC-MOD | [当前模块需求](./00-module-requirement-pack.md) | 比赛列表与备注全部原文 |
| SRC-UPSTREAM-LIST | [比赛列表上游需求包](../MOD-06-03-01-比赛列表/00-module-requirement-pack.md) | 比赛列表原始输入 |
| SRC-UPSTREAM-REMARK | [备注上游需求包](../MOD-06-03-02-备注/00-module-requirement-pack.md) | 备注原始输入 |
| SRC-GLOBAL | [项目全局上下文](../../../../global/project-context.md) | 权威优先级和术语 |
| SRC-PRD13 | [第十三轮 PRD](../../../../global/source-materials/current-requirement/竞猜赛事运营系统需求PRD文档-13轮冲刺.md) | PBL-634 原始需求 |
| SRC-API-BACKEND | [data-backend OpenAPI](../../../../global/source-materials/api-docs/league-api-definition/league-core-api/data-backend-openapi.json) | 当前接口契约 |
| SRC-CODE-MONITOR | [当前监控服务](../../../../../../apps/league-platform/data-backend/src/main/java/com/league/backend/service/sporttery/SportteryMatchMonitorService.java) | 实现证据 |
| SRC-CODE-RULES | [状态/比分/颜色规则](../../../../../../apps/league-platform/data-backend/src/main/java/com/league/backend/service/sporttery/SportteryMatchMonitorRules.java) | 派生规则 |
| SRC-CODE-CONTROLLER | [监控 Controller](../../../../../../apps/league-platform/data-backend/src/main/java/com/league/backend/controller/sporttery/SportteryMatchMonitorController.java) | 参数验证入口 |
| SRC-CODE-EVENT | [竞彩事件实体](../../../../../../apps/league-platform/coredb-entity/src/main/java/com/league/coredb/entity/SportteryMatchEventEntity.java) | 事件字段 |
| SRC-CODE-REMARK | [竞彩备注实体](../../../../../../apps/league-platform/coredb-entity/src/main/java/com/league/coredb/entity/SportteryMatchRemarkEntity.java) | 备注唯一键 |
| SRC-CODE-EVENT-REPO | [事件 Repository](../../../../../../apps/league-platform/coredb-repo/src/main/java/com/league/coredb/repository/SportteryMatchEventRepository.java) | 事件过滤、排序的本地实现观察 |
| SRC-CODE-REMARK-REPO | [备注 Repository](../../../../../../apps/league-platform/coredb-repo/src/main/java/com/league/coredb/repository/SportteryMatchRemarkRepository.java) | 备注查询和当前用户定位 |
| SRC-HIST-LIVE | [旧进程需求](../../../../global/source-materials/automation-contracts/data-bff/match-monitoring/legacy-match-live/比赛进程信息需求.md) | 历史进程参考 |
| SRC-HIST-LIVE-SQL | [旧进程 SQL](../../../../global/source-materials/automation-contracts/data-bff/match-monitoring/legacy-match-live/比赛进程信息查询接口.sql) | 历史来源参考 |
| SRC-DB13 | [数据库设计](../../../../global/source-materials/database-docs/第十三轮冲刺竞彩抓取数据库设计和变更.md) | 当前表设计 |
| SRC-DB-SCHEMA | [最新 DDL](../../../../global/source-materials/database-docs/北单运营系统-test2_newgoal-202610261418.sql) | 字段、键和索引 |
| CTX | [Context Pack](./01-context-pack.md) | 模块逻辑基线 |
| Q-INDEX | [问题清单](./03-clarification-questions.md) | 问题和回填 |
| FC-INDEX | [Context Cards](./context-cards/README.md) | 可复用上下文 |
| FC-001 | [列表聚合卡](./context-cards/FC-001-竞彩监控列表聚合链路.md) | 列表聚合链路 |
| FC-002 | [进程解析卡](./context-cards/FC-002-竞彩进程解析链路.md) | 进程解析链路 |
| FC-003 | [备注生命周期卡](./context-cards/FC-003-竞彩备注生命周期.md) | 备注生命周期 |
| DC-INDEX | [Data Closures](./data-closures/README.md) | 数据闭包 |
| DC-001 | [列表聚合](./data-closures/DC-001-列表聚合数据闭包.md) | 列表数据路径 |
| DC-002 | [进程解析](./data-closures/DC-002-进程解析数据闭包.md) | 进程数据路径 |
| DC-003 | [事件查询](./data-closures/DC-003-事件查询数据闭包.md) | 事件数据路径 |
| DC-004 | [备注读写](./data-closures/DC-004-备注读写数据闭包.md) | 备注读写路径 |

## 当前模块原文单元

### 原文结构与拆分决策

| 来源范围 | 语义角色 | 拆分处理 | 对应 RSU | 判定理由 |
|---|---|---|---|---|
| SRC-MOD > 比赛列表 > 业务规则 1 | composite-contract | one-rsu | RSU-001 | 运动项目、业务日和自动刷新选项共同定义列表查询条件。 |
| SRC-MOD > 比赛列表 > 业务规则 2.1～2.6 | composite-contract | one-rsu | RSU-002 | 身份、名称、时间和竞彩源字段共同定义列表基础行。 |
| SRC-MOD > 比赛列表 > 业务规则 2.7 | independent-contract | one-rsu | RSU-003 | 排名来源、缺失展示和主客方向是独立字段契约。 |
| SRC-MOD > 比赛列表 > 业务规则 2.8 | composite-contract | one-rsu | RSU-004 | 标准化状态和足球 live 补充共同定义比赛状态展示。 |
| SRC-MOD > 比赛列表 > 业务规则 2.9 | composite-contract | one-rsu | RSU-005 | 开奖/未开奖比分来源、空比分和主客方向共同定义比分展示。 |
| SRC-MOD > 比赛列表 > 业务规则 2.10～2.11 | composite-contract | one-rsu | RSU-006 | 事件和备注计数共同定义列表行聚合。 |
| SRC-MOD > 比赛列表 > 业务规则 2.12 | independent-contract | one-rsu | RSU-007 | 开奖状态是独立字段和筛选依据。 |
| SRC-MOD > 比赛列表 > 业务规则 3 | composite-contract | one-rsu | RSU-008 | 事件类型、解除状态、更新时间和颜色共同构成契约。 |
| SRC-MOD > 比赛列表 > 业务规则 4 | independent-contract | one-rsu | RSU-009 | 自动刷新和查询状态保留是独立功能行为。 |
| SRC-MOD > 比赛列表 > 业务规则 5 | composite-contract | one-rsu | RSU-010 | 五类列筛选共同定义列表筛选行为。 |
| SRC-MOD > 比赛列表 > 业务规则 6 | independent-contract | one-rsu | RSU-011 | 点击比赛状态进入对应比赛进程链路。 |
| SRC-MOD > 比赛列表 > 业务规则 7 | composite-contract | one-rsu | RSU-012 | 点击事件后的字段、排序和详情展示共同构成事件弹窗契约。 |
| SRC-MOD > 比赛列表 > 业务规则 8 | independent-contract | one-rsu | RSU-013 | 点击备注进入备注弹窗链路。 |
| SRC-MOD > 备注 > 业务规则 1 | composite-contract | one-rsu | RSU-014 | 标题、当前用户、其他用户构成完整备注展示契约。 |
| SRC-MOD > 备注 > 业务规则 2 | independent-contract | one-rsu | RSU-015 | 置顶与其余排序是独立顺序契约。 |
| SRC-MOD > 备注 > 业务规则 3～5 | composite-contract | one-rsu | RSU-016 | 输入限制、保存更新、取消不更新共同构成编辑生命周期。 |
| SRC-MOD > 两个原型图片 | visual-placeholder | not-rsu | 无 | 原型是功能测试定位资料，不单独生成 RSU。 |
| SRC-MOD > 章节标题/PBL索引 | structural-container | not-rsu | 无 | 章节和元数据不是可观察业务行为。 |

### RSU 映射

| RSU-ID | 父级条件（原文） | 原文内容 | 来源 | 来源定位 | 相关上下文 | 相关问题 | 状态 |
|---|---|---|---|---|---|---|---|
| RSU-001 | 无 | 1. 查询条件包括： 1. 运动项目，包含：足球、篮球；支持多选，默认全选； 2. 业务日，可选择开始日期和结束日期，默认为当前日期至当前日期+6； 3. 自动刷新，通过下拉框选择，包含：关、5s、10s、30s、1m、5m，默认为关。 | SRC-MOD | 比赛列表 > 业务规则 1 | FC-001、DC-001 | 无 | captured |
| RSU-002 | 无 | 2. 查询结果为符合条件的竞彩赛程列表，按编号正序排列，不分页，具体信息包括： 1. 业务日； 2. 编号，即竞彩赛程编号，如“周三 001”； 3. 运动项目； 4. 赛事简称，竞彩赛程信息中比赛所属赛事对应的竞彩简称； 5. 开赛时间，竞彩赛程中的开赛时间； 6. 主队全称、客队全称，竞彩赛程中的球队，名称显示竞彩全称，主客队顺序与竞彩赛程一致； | SRC-MOD | 比赛列表 > 业务规则 2.1～2.6 | FC-001、DC-001 | 无 | captured |
| RSU-003 | 无 | 7. 主队排名、客队排名，标准比赛信息中的排名，无则不显示；排名顺序与主客队一致； | SRC-MOD | 比赛列表 > 业务规则 2.7 | FC-001、DC-001 | 无 | captured |
| RSU-004 | 无 | 8. 比赛状态，根据标准化比赛信息中的比赛状态进行显示，映射关系详见“通用需求”；足球项目，比赛状态为“比赛中”，获取贝泰直播数据（live）中的 match\_clock、stoppage\_clock 和 match\_status 值，具体规则同“**比赛赛程监控**”章节。（无则显示未匹配） | SRC-MOD | 比赛列表 > 业务规则 2.8 | FC-001、FC-002、DC-001、DC-002 | Q-003 | captured |
| RSU-005 | 无 | 9. 半场、全场比分，已开奖时显示竞彩赛程的比分，未开奖时显示系统采集的开奖用的比分，无比分时显示“-”；比分顺序与主客队一致； | SRC-MOD | 比赛列表 > 业务规则 2.9 | FC-001、DC-001 | 无 | captured |
| RSU-006 | 无 | 10. 事件，显示对应赛程的竞彩事件条数，为超链接样式，条数为 0 时置灰； 11. 备注，显示对应赛程的备注条数，为超链接样式； | SRC-MOD | 比赛列表 > 业务规则 2.10～2.11 | FC-001、DC-001 | 无 | captured |
| RSU-007 | 无 | 12. 开奖状态，显示竞彩赛程开奖状态，包含：未开奖、已开奖。 | SRC-MOD | 比赛列表 > 业务规则 2.12 | FC-001、DC-001 | 无 | captured |
| RSU-008 | 无 | 3. 当赛程存在以下情况时，将赛程的背景填充为对应颜色： 1. 存在异常类型为“比赛提前”的竞彩事件时，填充为红色； 2. 存在异常类型为“比赛推迟”的竞彩事件时，填充为黄色； 3. 存在异常类型为“比赛取消”、“比赛中断”、“比赛腰斩”的竞彩事件时，填充为橙色； 4. 存在异常类型为“球队变更”的竞彩事件时，填充为绿色； 5. 按事件更新时间最大的事件进行填充。 | SRC-MOD | 比赛列表 > 业务规则 3 | FC-001、DC-001 | 无 | captured |
| RSU-009 | 无 | 4. 比赛列表根据设置的自动刷新时长自动更新，只更新列表内的数据，保留之前的查询、筛选结果，及滚动条位置； | SRC-MOD | 比赛列表 > 业务规则 4 | FC-001、DC-001 | 无 | captured |
| RSU-010 | 无 | 5. 点击列表标题的对应项可进行比赛筛选，具体包括： 1. “赛事简称”，弹出赛事筛选框，包含当前赛程列表中涉及的所有赛事简称，具体规则参考**比赛信息管理**； 2. “比赛状态”，包含：未开赛、比赛中、完场、推迟、中断、腰斩、取消，默认全选，支持反选； 3. “事件”，包含：无事件、有事件，默认全选； 4. “备注”，包含：无备注、有备注，默认全选； 5. “开奖状态”，包含：未开奖、已开奖，默认全选。 | SRC-MOD | 比赛列表 > 业务规则 5 | FC-001、DC-001 | 无 | captured |
| RSU-011 | 无 | 6. 点击列表中的比赛状态，弹出对应比赛的进程信息，具体规则同“**比赛赛程监控**”章节； | SRC-MOD | 比赛列表 > 业务规则 6 | FC-002、DC-002 | Q-003 | captured |
| RSU-012 | 无 | 7. 点击列表中的事件，弹窗显示对应比赛的事件记录，包含：事件时间、标题、异常详情，按事件时间倒序排列； | SRC-MOD | 比赛列表 > 业务规则 7 | DC-003 | Q-003、Q-004 | captured |
| RSU-013 | 无 | 8. 点击列表中的备注，弹出备注框，详见后续章节。✅ | SRC-MOD | 比赛列表 > 业务规则 8 | FC-003、DC-004 | Q-002 | captured |
| RSU-014 | 无 | 1. 点击列表中的备注，弹出备注框，包含以下信息：标题：赛程编号当前用户的账号及备注信息，无备注时显示空；其他用户的账号及备注信息，无备注时不显示。 | SRC-MOD | 备注 > 业务规则 1 | FC-003、DC-004 | Q-002 | captured |
| RSU-015 | 无 | 2. 当前用户的备注置顶显示，其他用户的备注按备注修改时间正序排列。 | SRC-MOD | 备注 > 业务规则 2 | FC-003、DC-004 | Q-002 | captured |
| RSU-016 | 无 | 3. 可编辑当前用户的备注信息，最多可输入300 字符； 4. 点击【保存】，更新当前用户备注信息，关闭弹窗并刷新页面； 5. 点击【取消】，关闭弹窗，不更新数据。✅ | SRC-MOD | 备注 > 业务规则 3～5 | FC-003、DC-004 | Q-002 | captured |

## 原文来源覆盖检查

| 原文来源范围 | 处理结果 | 对应 RSU/问题 | 说明 |
|---|---|---|---|
| SRC-MOD > 比赛列表 > 业务规则 1 | mapped | RSU-001 | 已按对应 RSU 保留完整原文和语义范围。 |
| SRC-MOD > 比赛列表 > 业务规则 2.1～2.6 | mapped | RSU-002 | 已按对应 RSU 保留完整原文和语义范围。 |
| SRC-MOD > 比赛列表 > 业务规则 2.7 | mapped | RSU-003 | 已按对应 RSU 保留完整原文和语义范围。 |
| SRC-MOD > 比赛列表 > 业务规则 2.8 | mapped | RSU-004 | 已按对应 RSU 保留完整原文和语义范围。 |
| SRC-MOD > 比赛列表 > 业务规则 2.9 | mapped | RSU-005 | 已按对应 RSU 保留完整原文和语义范围。 |
| SRC-MOD > 比赛列表 > 业务规则 2.10～2.11 | mapped | RSU-006 | 已按对应 RSU 保留完整原文和语义范围。 |
| SRC-MOD > 比赛列表 > 业务规则 2.12 | mapped | RSU-007 | 已按对应 RSU 保留完整原文和语义范围。 |
| SRC-MOD > 比赛列表 > 业务规则 3 | mapped | RSU-008 | 已按对应 RSU 保留完整原文和语义范围。 |
| SRC-MOD > 比赛列表 > 业务规则 4 | mapped | RSU-009 | 已按对应 RSU 保留完整原文和语义范围。 |
| SRC-MOD > 比赛列表 > 业务规则 5 | mapped | RSU-010 | 已按对应 RSU 保留完整原文和语义范围。 |
| SRC-MOD > 比赛列表 > 业务规则 6 | mapped | RSU-011 | 已按对应 RSU 保留完整原文和语义范围。 |
| SRC-MOD > 比赛列表 > 业务规则 7 | mapped | RSU-012 | 已按对应 RSU 保留完整原文和语义范围。 |
| SRC-MOD > 比赛列表 > 业务规则 8 | mapped | RSU-013 | 已按对应 RSU 保留完整原文和语义范围。 |
| SRC-MOD > 备注 > 业务规则 1 | mapped | RSU-014 | 已按对应 RSU 保留完整原文和语义范围。 |
| SRC-MOD > 备注 > 业务规则 2 | mapped | RSU-015 | 已按对应 RSU 保留完整原文和语义范围。 |
| SRC-MOD > 备注 > 业务规则 3～5 | mapped | RSU-016 | 已按对应 RSU 保留完整原文和语义范围。 |
| SRC-MOD > 两个原型图片 | not-rsu | 无 | 作为功能测试定位资料。 |
| SRC-MOD > 章节标题/PBL索引 | not-rsu | 无 | 结构和元数据不构成独立行为。 |

## 后续使用规则

每次固定读取：

1. SRC-GLOBAL 项目全局上下文全文。
2. SRC-MOD 当前模块需求全文。
3. CTX 中的模块背景、能力、详细逻辑和边界。
4. 当前 RSU-ID 的完整映射行。

再读取当前 RSU 显式声明的 Q、FC、DC、OpenAPI、代码、数据库和历史契约；FC/DC 卡内来源只作为追溯证据，不自动递归展开整份原文。
