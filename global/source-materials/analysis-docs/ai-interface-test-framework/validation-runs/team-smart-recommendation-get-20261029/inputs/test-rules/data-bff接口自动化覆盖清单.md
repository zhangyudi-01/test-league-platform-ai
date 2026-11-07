# data-bff 前端接口 ↔ 自动化覆盖对照清单

> **统计口径截止：2026-10-01**。本清单为 2026-09-28 基于当时仓库快照与 test3 环境（DB `test3_newgoal`@192.168.22.218，BFF `http://test-newgoal3-192-168-22-218.nip.io:30024/`）的一次性统计结果。
> **后续新增接口不在本清单范围内。** 新增接口若暂不实现接口测试，需**人工维护进 §六 待补登记**，避免遗漏。
>
> 确认依据（三源印证）：
>
> 1. test3 库 `toto_permission` 权限元数据（172 条 method+url 对，is_deleted=0，即前端可调用面的权威来源）；
> 2. 后端仓库 `E:\Vegas2.0\sdd-league-platform` origin/develop 控制器源码；
> 3. jiazics 账号对 test3 的实测探针（code=0 存在 / 1005 无权限 / 404 无路由）。

## 一、口径与范围

| 项                                         | 数值                                                                                                                                                                                                                                                        |
| ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `data/data-bff/` Excel 用例文件          | **99 个** = **80 个被 LIVE 套件实际加载** + **16 个仅被注释停用的 GHOST 套件文字引用**（account 10 + role 6，role 6 个引用路径还指向不存在的 `data/manager-service/`，属历史目录搬迁残留）+ **3 个无任何引用孤儿**（详见 §四.3） |
| Excel`接口路径` 表去重后的前端可调用路径 | **73 条**（2026-10-10 修正 bdSubmitBatch→bd-submit-batch 后仍为 73，去重数不变）                                                                                                                                                                     |
| 确认结果                                   | **✅ 64 条确认存在**（权限表登记 + 后端控制器 + 实测；含 2026-10-10 修正的 bd-submit-batch）；**❌ 9 条未确认**（§三）                                                                                                                         |
| 测试套件                                   | 97 个引用`api_test_data` 的文件：**81 个 LIVE** / **16 个 GHOST**（整文件注释，全部在 account/ 与 role/）                                                                                                                                     |
| **待实现自动化**                     | 以权限面 146 条 URL 为基准、剔除 Excel 已覆盖与 §三 无效路径后，**88 条已上线/已登记但暂无接口测试**的路径 → **§五 待实现清单**（2026-10-10 修正 bd-submit-batch Excel 路径后由 89 降为 88）                                                 |
| 范围未含                                   | data-collection（采集）、data-computation（计算/识别）、openapi（7 文件）属其他服务，未计入；**monitor 大屏已于 2026-10-10 纳入，见 §七**                                                                                                            |
| 执行情况列                                 | 各表末列由人工执行用例后填写，仅两值：**测试通过** / **测试失败**；空白 = 尚未执行（2026-10-10 新增）                                                                                                                                           |

## 二、✅ 64 条确认存在的路径（按模块分组）

### 1. 登录/免认证白名单（5 条）

| 路径                      | 方法 | Excel 来源                   | 套件                            | 状态                    | 执行情况 |
| ------------------------- | ---- | ---------------------------- | ------------------------------- | ----------------------- | -------- |
| `/login`                | POST | 接口测试用例_login           | account/test_login.py           | GHOST（免登录场景本身） |          |
| `/logout`               | POST | 接口测试用例_logout          | account/test_logout.py          | GHOST                   |          |
| `/user/change_password` | POST | 接口测试用例_change_password | account/test_change_password.py | GHOST                   |          |
| `/access/permission`    | GET  | 接口测试用例_权限列表        | role/test_permission_list.py    | GHOST                   |          |
| `/access/role`          | GET  | 接口测试用例_角色列表        | role/test_role_list.py          | GHOST                   |          |

### 2. 草稿管理（原生根路由，17 条）

| 路径                                                              | 方法  | Excel 来源（接口路径表）                            | 套件（testsuites/data-bff/ 下）                                  | 执行情况 |
| ----------------------------------------------------------------- | ----- | --------------------------------------------------- | ---------------------------------------------------------------- | -------- |
| `/batch-matchup-drafts`                                         | POST  | 草稿管理/创建或更新比赛草稿、保存草稿               | draft/test_drafts_post.py                                        |          |
| `/batch-matchup-drafts`                                         | GET   | （根查询）                                          | —（见 §四.2）                                                  |          |
| `/batch-matchup-drafts/s-match`                                 | GET   | 草稿管理/查询比赛信息(添加比赛弹窗)、查询标准化比赛 | draft/test_s_match_get.py                                        | 测试通过 |
| `/batch-matchup-drafts/validate-main-source-match-availability` | POST  | 主数据源比赛可用性校验                              | matchup_validate/test_validate_main_source_match_availability.py | 测试通过 |
| `/batch-matchup-drafts/real-time/add`                           | PATCH | 草稿管理/添加比赛到草稿、草稿列表添加比赛           | draft/test_batch_matchup_drafts_add.py                           |          |
| `/batch-matchup-drafts/real-time/delete`                        | PATCH | 草稿列表删除比赛                                    | draft/test_batch_matchup_drafts_del.py                           |          |
| `/batch-matchup-drafts/real-time/batch-matchup-drafts`          | PATCH | 实时修改草稿其它信息                                | draft/test_batch_matchup_drafts_other.py                         |          |
| `/batch-matchup-drafts/real-time/manual-sort-no`                | PATCH | 手动拖动比赛顺序                                    | draft/test_batch_matchup_drafts_sort.py                          |          |
| `/batch-matchup-drafts/real-time/matchup-no`                    | PATCH | 重置游戏起始场次号                                  | draft/test_batch_matchup_drafts_matchupNo.py                     |          |
| `/batch-matchup-drafts/real-time/sales`                         | PATCH | 调整比赛开售游戏                                    | draft/test_batch_matchup_drafts_games.py                         |          |
| `/batch-matchup-drafts/real-time/batch/add`                     | PATCH | 添加指定批次到当前用户草稿                          | draft/test_batch_matchup_copy.py                                 |          |
| `/batch-matchup-drafts/transfer`                                | POST  | 转移赛程                                            | draft/test_batch_matchup_transfer.py                             |          |
| `/batch-diff/matchup-formal`                                    | POST  | 生成正式版                                          | draft/test_batch_matchup_formal.py                               |          |
| `/upload/s-match/preview`                                       | POST  | 导入胜负比赛预览                                    | draft/test_s_match_upload.py                                     |          |
| `/upload/s-match/save`                                          | POST  | 导入胜负比赛保存                                    | draft/test_s_match_save.py                                       |          |
| `/data-backend/batch-matchup-drafts/all`                        | GET   | 根据批次ID查询所有用户的草稿                        | draft/test_drafts_all_get.py                                     |          |
| `/data-backend/batch-matchup-drafts`                            | GET   | 根据批次ID查询当前登录用户的草稿                    | draft/test_drafts_get.py ⚠️见 §四.2                           |          |

### 3. 奖期 / 批次 / 正式赛程（12 条）

| 路径                                         | 方法                  | Excel 来源                                                        | 套件                                                                                                | 执行情况 |
| -------------------------------------------- | --------------------- | ----------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- | -------- |
| `/data-backend/bd-game-draw`               | POST/PATCH/DELETE/GET | 新建/修改/删除/查询奖期                                           | draw/test_add_draw.py、test_update_draw.py、test_delete_draw.py、test_get_draw_list.py              |          |
| `/data-backend/bd-game-draw/id`            | GET                   | 查询奖期详情                                                      | draw/test_get_draw_details.py                                                                       |          |
| `/data-backend/bd-game-draw/on-sale`       | GET                   | 查询赛果奖期列表                                                  | matchup_result.py/test_result_draw_get.py（注：`matchup_result.py` 实为目录非文件，历史命名如此） |          |
| `/data-backend/bd-batch`                   | POST/PATCH/DELETE/GET | 新建/修改/删除/查询批次                                           | batch/test_add_batch.py、test_update_batch.py、test_delete_batch.py、test_get_batch_list.py         |          |
| `/data-backend/bd-batch/batchNo`           | PATCH                 | 修改批次号                                                        | batch/test_update_batch_no.py                                                                       |          |
| `/data-backend/bd-batch/id`                | GET                   | 查询批次详情                                                      | batch/test_get_batch_details.py                                                                     |          |
| `/data-backend/batch-matchup`              | GET                   | 查询正式版详情                                                    | draft/test_batch_matchup_get.py                                                                     |          |
| `/data-backend/batch-matchup`              | DELETE                | 正式赛程作废                                                      | draft/test_batch_matchup_del.py                                                                     |          |
| `/data-backend/batch-matchup/batch_team`   | GET                   | 查询批次下球队                                                    | submit/test_batch_team_get.py                                                                       |          |
| `/data-backend/batch-matchup/batch_season` | GET                   | 查询批次下赛季                                                    | submit/test_batch_league_get.py                                                                     |          |
| `/data-backend/bd-submit-batch`            | GET                   | 查询批次提交记录（接口测试用例_查询批次提交记录.xlsx，13 条用例） | submit/test_batch_bdSubmitBatch_get.py（Excel 原为过期驼峰 bdSubmitBatch，2026-10-10 已修正）       |          |
| `/data-backend/bd-submit-batch/cancel`     | GET                   | （尚未实现，见 §五.9）                                           | —                                                                                                  |          |

### 4. 主数据 赛事/赛季/球队/比赛（15 条）

| 路径                                          | 方法            | Excel 来源                  | 套件                                                                                                                        | 执行情况 |
| --------------------------------------------- | --------------- | --------------------------- | --------------------------------------------------------------------------------------------------------------------------- | -------- |
| `/data-backend/m-competition`               | POST/PATCH/GET  | 新建/修改赛事、查询赛事列表 | competition/test_competition_add.py、test_competition_update.py、test_competition_get.py                                    |          |
| `/data-backend/m-competition/detail`        | GET             | 查询赛事详情                | competition/test_competition_detail.py                                                                                      |          |
| `/data-backend/m-competition/list`          | GET             | 查询赛事列表不分页          | competition/test_get_competition_list_no_page.py                                                                            |          |
| `/data-backend/m-competition/latest-season` | GET             | 查询赛事最新的赛季信息      | competition/test_competition_latest_season.py                                                                               |          |
| `/data-backend/m-season`                    | POST/GET        | 新建赛季、查询赛季          | season/test_m_season_post.py、test_m_season_get.py                                                                          |          |
| `/data-backend/m-season/team`               | GET             | 查询赛季球队列表            | season/test_get_m_season_team.py                                                                                            |          |
| `/data-backend/m-team`                      | POST/GET        | 新建球队、查询球队          | team/test_m_team_post.py、test_m_team_get.py                                                                                |          |
| `/data-backend/m-team/list`                 | GET             | 查询球队列表                | team/test_m_team_get_list.py                                                                                                |          |
| `/data-backend/m-team/detail`               | GET             | 查询球队详情                | team/test_m_team_get_detail.py                                                                                              |          |
| `/data-backend/m-match`                     | POST/GET        | 新建比赛、查询比赛          | matchup/test_m_matchup_add.py、test_m_matchup_get.py                                                                        |          |
| `/data-backend/r-season-team`               | GET             | 查询赛事的赛季球队列表      | season/test_get_r_season_team.py                                                                                            |          |
| `/data-backend/r-season-team`               | POST            | 赛季关联球队                | season/test_r_season_team.py                                                                                                |          |
| `/data-backend/nami-football-team`          | GET             | 获取纳米数据源球队          | season/test_nami_football_team_get.py                                                                                       |          |
| `/data-backend/m-team-blacklist`            | GET/POST/DELETE | 查询/添加/移除黑名单球队    | team/test_get_m_team_black_list.py、test_m_team_black_list.py、test_delete_m_team_black_list.py                             |          |
| `/data-backend/m-competition-blacklist`     | GET/POST/DELETE | 查询/添加/移除赛事黑名单    | competition/test_get_m_competition_black_list.py、test_m_competition_black_list.py、test_delete_m_competition_black_list.py |          |

### 5. 数据源匹配 relations / realtime / dimension（10 条）

| 路径                                                                          | 方法                  | Excel 来源                  | 套件                                                                                                            | 执行情况 |
| ----------------------------------------------------------------------------- | --------------------- | --------------------------- | --------------------------------------------------------------------------------------------------------------- | -------- |
| `/data-backend/relations/nami/team`                                         | GET                   | 查询纳米球队                | team/test_nami_team_get.py                                                                                      |          |
| `/data-backend/relations/nami/competition`                                  | GET                   | 查询纳米赛事                | competition/test_nami_competition_get.py                                                                        |          |
| `/data-backend/relations/nami/season`                                       | GET                   | 查询纳米赛季                | season/test_nami_season_get.py                                                                                  |          |
| `/data-backend/relations/beitai/competition`                                | GET                   | 查询贝泰赛事                | competition/test_beitai_competition_get.py                                                                      |          |
| `/data-backend/realtime/nami/matchup`                                       | GET                   | 查询纳米十场比赛            | matchup/test_matchup_realtime_nami_get.py                                                                       |          |
| `/data-backend/relations/team/recommendations`                              | GET                   | 球队智能推荐查询            | team/（commit a02d499 新增）                                                                                    |          |
| `/data-backend/dimension/relations/team`                                    | POST                  | 球队维度数据匹配            | team/test_team_pipei_post.py                                                                                    |          |
| `/data-backend/dimension/relations/competition`                             | POST                  | 赛事维度数据匹配            | competition/test_competition_pipei_post.py                                                                      |          |
| `/data-backend/dimension/relations/season`                                  | POST                  | 赛季维度数据匹配            | season/test_season_pipei_post.py                                                                                |          |
| `/data-backend/m-match-remark` 及 `/data-backend/m-match-remark/match-id` | POST/PATCH/DELETE/GET | 添加/修改/删除/查询比赛备注 | draft/test_match_remark_post.py、test_match_remark_patch.py、test_match_remark_del.py、test_match_remark_get.py |          |

### 6. 提交文件 / 账号操作（5 条）

| 路径                                                           | 方法               | Excel 来源                                                         | 套件                         | 执行情况 |
| -------------------------------------------------------------- | ------------------ | ------------------------------------------------------------------ | ---------------------------- | -------- |
| `/data-backend/league_file_submit`                           | POST               | 提交赛事                                                           | submit/test_league_json.py   |          |
| `/data-backend/team_file_submit`                             | POST               | 提交球队                                                           | submit/test_team_json.py     |          |
| `/data-backend/match_file_submit`                            | POST               | 提交比赛                                                           | submit/test_schedule_json.py |          |
| `/data-backend/match_result_file_submit`                     | POST               | 提交赛果                                                           | submit/test_results_json .py |          |
| `/manager_account` POST + `/manager_account_disable` PATCH | 新建账号、停用账号 | account/test_account_add.py、test_account_disable.py（原生根路由） |                              |          |

### 7. 比赛监控（2 条）

| 路径                           | 方法 | Excel 来源       | 套件                                         | 执行情况 |
| ------------------------------ | ---- | ---------------- | -------------------------------------------- | -------- |
| `/data-backend/s-match`      | GET  | 查询比赛监控列表 | match_monitoring/test_get_monitoring_list.py |          |
| `/data-backend/s-match/live` | GET  | 查询比赛进程信息 | match_monitoring/test_get_match_live.py      |          |

## 三、❌ 9 条未确认路径（Excel 有、权限表/后端不存在；不含 §二.3 已修正的 bd-submit-batch）

| #      | Excel 路径                                     | Excel 来源                                 | 绑定套件                                   | 核查结论                                                                                                                                            | 执行情况 |
| ------ | ---------------------------------------------- | ------------------------------------------ | ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| ~~1~~ | ~~`/data-backend/bdSubmitBatch`~~ → 已修正 | （已移入 §二.3 确认区，此处保留编号占位） | —                                         | 2026-10-10 已修正 Excel 接口路径表为`/data-backend/bd-submit-batch`（权限表登记形式，test3 实测 code=0），13 条用例加载正常，转为**已确认** |          |
| 2      | `/data-backend/realtime/tx/matchup`          | 查询同行十场比赛                           | matchup/test_matchup_realtime_tx_get.py    | tx（同行）系接口 2026-03-23 已从 develop 移除（884eed5ae，tx→beitai 改造），权限表 0 条记录（含已删除），实测 1005。**接口已下线**           |          |
| 3      | `/data-backend/relations/tx/competition`     | 查询同行赛事                               | competition/test_tx_competition_get.py     | 同上，已下线                                                                                                                                        |          |
| 4      | `/data-backend/relations/tx/season`          | 查询同行赛季                               | season/test_tx_season_get.py               | 同上，已下线                                                                                                                                        |          |
| 5      | `/data-backend//relations/tx/team`（双斜杠） | 查询同行球队                               | team/test_tx_team_get.py                   | 双重问题：路径拼写错误 + tx 已下线                                                                                                                  |          |
| 6      | `/league/role`                               | 添加/修改/删除角色                         | role/test_role_add.py 等（GHOST）          | `/league` 前缀在权限表/后端代码/基础设施均不存在。正确形式 `/data-backend/role`（POST/PATCH/DELETE）已登记                                      |          |
| 7      | `/league/role/permission`                    | 角色详情                                   | role/test_role_detail.py（GHOST）          | 正确形式`/data-backend/role/**`（GET）已登记                                                                                                      |          |
| 8      | `/league/manager_account`                    | 修改/删除/查询账号列表                     | account/test_account_modify.py 等（GHOST） | 正确形式`/data-backend/manager_account`（PATCH/DELETE）+ `manager_account/**`（GET）已登记                                                      |          |
| 9      | `/league/manager_account/detail`             | 查询账号详情                               | account/test_account_detail.py（GHOST）    | 同上，`/data-backend/manager_account/**` 通配覆盖                                                                                                 |          |
| 10     | `/league/manager_account_enable`             | 启用账号                                   | account/test_account_enable.py（GHOST）    | 正确形式`/data-backend/manager_account_enable`（PATCH）已登记                                                                                     |          |

## 四、注意事项

1. **tx 4 条套件在 test3 上不可跑是双重的**：接口已下线（1005）+ Excel 缺省账号 wjycs 在 test3 不存在。这 4 个 Excel/套件需决策：删除，或迁移到 beitai/nami 对应接口。
2. **`/data-backend/batch-matchup-drafts`（GET）特殊情况**：权限表有 `GET /data-backend/batch-matchup-drafts/**` 通配（能过鉴权），但后端无此路由（ProxyController routeMap 无此字面量），实测 404；**真正的前端路由是根路径 `/batch-matchup-drafts`**（实测 code=0）。绑定套件 test_drafts_get.py 为 LIVE，Excel 路径建议修正。
3. **Excel 可加载性分层（99 = 80 + 16 + 3，2026-10-10 自查修正，原记"96 绑定 / 3 孤儿"不准确）**：
   - **80 个被 LIVE 套件实际加载**（pytest 收集时真正读入）；
   - **16 个运行时不会被加载**，仅存在于整文件注释的 GHOST 套件里：account 10 个（login、logout、change_password、新建/修改/删除/停用/启用账号、查询账号列表、查询账号详情）+ role 6 个（添加/修改/删除角色、角色列表、角色详情、权限列表）。其中 **role 6 个的引用路径写作 `manager-service/接口测试用例_*`，而 `data/manager-service/` 目录并不存在**，文件实际都躺在 `data/data-bff/` 下——即使恢复执行这些套件也会报文件不存在，属历史目录搬迁残留；
   - **3 个无任何引用孤儿**（路径与在用文件重复，不影响统计结论）：`接口测试用例_保存草稿.xlsx`（2026-09-03）、`接口测试用例_查询标准化比赛.xlsx`、`接口测试用例_草稿列表添加比赛.xlsx`（均 2026-03-06）。
4. ~~monitor 大屏 / openapi 套件是否计入"前端调用的接口"~~：monitor 大屏已于 2026-10-10 纳入本清单（§七）；openapi 及 data-collection、data-computation 仍属其他服务未含。

## 五、待实现接口自动化清单（88 条，截止 2026-10-01）

> **统计方法**：以 test3 `toto_permission` 146 条去重 URL 为前端可调用面全量基准，剔除 Excel `接口路径` 表已覆盖的路径（含通配授权命中、`/data-backend` 前缀代理重复登记）后得出。即：**权限表已登记、前端已可调用，但当前无任何 Excel 用例/测试套件覆盖**的接口。
> 实现某个接口的自动化后，将其从本表移入 §二 并在本表划掉或删除。

### 5.1 奖期赛果批次（batch-matchup-draw / bd-batch/draw 系，14 条）

| 路径                                                | 方法                  | 前端功能（权限名）                                                         | 执行情况 |
| --------------------------------------------------- | --------------------- | -------------------------------------------------------------------------- | -------- |
| `/batch-matchup-draw`                             | POST                  | 保存                                                                       |          |
| `/batch-matchup-draw-time`                        | GET                   | 批次详情、计划添加比赛                                                     |          |
| `/batch-matchup-draw/matchup`                     | GET                   | 范围添加比赛                                                               |          |
| `/batch-matchup-draw/matchup/batch-id`            | GET                   | 修改开奖游戏、删除比赛、批次详情、新建赛果批次、范围添加比赛、计划添加比赛 |          |
| `/batch-matchup-draw/real-time/add`               | PATCH                 | 范围添加比赛、计划添加比赛                                                 |          |
| `/batch-matchup-draw/real-time/cancel`            | PATCH                 | 批次详情                                                                   |          |
| `/batch-matchup-draw/real-time/delete`            | PATCH                 | 删除比赛                                                                   |          |
| `/batch-matchup-draw/real-time/draw`              | PATCH                 | 修改开奖游戏                                                               |          |
| `/data-backend/batch-matchup-draw/review-status`  | PATCH                 | 完成审核/取消审核                                                          |          |
| `/data-backend/bd-batch/draw`                     | GET/PATCH/POST/DELETE | 赛果批次 CRUD、批次编辑、调整批次序号、赛果批次管理                        |          |
| `/data-backend/bd-batch/draw/batch-id`            | GET                   | 批次详情、新建赛果批次                                                     |          |
| `/data-backend/bd-batch/draw/batch-order-no`      | PATCH                 | 调整批次序号                                                               |          |
| `/data-backend/batch-matchup/draw_time_plan`      | GET                   | 开奖计划、查看开奖计划                                                     |          |
| `/data-backend/batch-matchup/operation_draw_time` | GET                   | 开奖计划、查看开奖计划                                                     |          |

### 5.2 草稿保存辅助/比对/开售配置（12 条）

| 路径                                                     | 方法  | 前端功能                         | 执行情况 |
| -------------------------------------------------------- | ----- | -------------------------------- | -------- |
| `/batch-diff`                                          | POST  | 开奖时间比对、草稿比对           |          |
| `/batch-diff/cancel`                                   | PATCH | 保存草稿、开奖时间比对、草稿比对 |          |
| `/batch-diff/matchup-formal/previous-matchup-no`       | GET   | 生成正式版                       |          |
| `/batch-diff/user-matchup-drafts`                      | POST  | 保存草稿                         |          |
| `/data-backend/batch-diff/event/wait-check`            | GET   | 草稿                             |          |
| `/batch-matchup-drafts/real-time/cancel`               | PATCH | 草稿保存                         |          |
| `/batch-matchup-drafts/real-time/recreate-sort-no`     | PATCH | 更新赛程顺序                     |          |
| `/batch-matchup-drafts/real-time/sales-260`            | PATCH | 停售下半场、开售下半场           |          |
| `/batch-matchup-drafts/validate-sale-end-time-match`   | POST  | 草稿保存（售卖截止校验）         |          |
| `/data-backend/batch-matchup-drafts/match/sales`       | GET   | 开售配置                         |          |
| `/data-backend/batch-matchup-drafts/verify/consistent` | GET   | 开奖时间比对、开奖时间草稿       |          |
| `/data-backend/bd-game-draw/sale-begin-time`           | GET   | 转移赛程                         |          |

### 5.3 赛果审核确认（event-match-check 系，12 条）

| 路径                                                     | 方法     | 前端功能                           | 执行情况 |
| -------------------------------------------------------- | -------- | ---------------------------------- | -------- |
| `/data-backend/event-match-check`                      | GET/POST | 批量确认、核实、赛果审核、赛果确认 |          |
| `/data-backend/event-match-check/batch`                | POST     | 添加比赛                           |          |
| `/data-backend/event-match-check/check-source-id`      | GET      | 批量确认、核实、赛果审核、赛果确认 |          |
| `/data-backend/event-match-check/event-match`          | GET      | 草稿                               |          |
| `/data-backend/event-match-check/event/confirm`        | POST     | 确认                               |          |
| `/data-backend/event-match-check/match-result/check`   | POST     | 批量确认、赛果确认                 |          |
| `/data-backend/event-match-check/match-result/confirm` | POST     | 批量确认、赛果确认                 |          |
| `/data-backend/event-match-check/match-result/diff`    | POST     | 批量确认、赛果确认                 |          |
| `/data-backend/event`                                  | GET      | 查询                               |          |
| `/data-backend/match-result-rolled-back`               | POST     | 赛果回退                           |          |
| `/data-backend/s-match/result-confirm-record`          | GET      | 查询                               |          |
| `/data-backend/task/cancel`                            | POST     | 取消完成状态                       |          |

### 5.4 文件下载/导出/导入（24 条）

| 路径                                                      | 方法 | 前端功能                           | 执行情况 |
| --------------------------------------------------------- | ---- | ---------------------------------- | -------- |
| `/data-backend/valid_download/valid_league_file`        | POST | 下载赛事文件（校验）               |          |
| `/data-backend/valid_download/valid_match_file`         | POST | 下载比赛文件（校验）               |          |
| `/data-backend/valid_download/valid_match_result_file`  | POST | 下载赛果文件（校验）               |          |
| `/data-backend/valid_download/valid_team_file`          | POST | 下载球队文件（校验）               |          |
| `/download/download_league_file`                        | POST | 下载赛事文件                       |          |
| `/download/download_match_file`                         | POST | 下载比赛文件                       |          |
| `/download/download_match_result_file`                  | POST | 下载赛果文件                       |          |
| `/download/download_team_file`                          | POST | 下载球队文件                       |          |
| `/data-backend/bd-batch/valid`                          | POST | 导出公告表、导出正式赛程（校验）   |          |
| `/data-backend/batch-matchup/count_export_match_result` | GET  | 导出赛果（计数）                   |          |
| `/data-backend/batch-matchup/valid_export_match_result` | GET  | 导出赛果（校验）                   |          |
| `/data-backend/batch-matchup/valid_match`               | GET  | 下载比赛文件、提交比赛文件（校验） |          |
| `/report/change_matchup/6`                              | GET  | 导出变更单                         |          |
| `/report/draft_batch_remark/*`                          | GET  | 导出草稿备注                       |          |
| `/report/event_notice_export`                           | POST | 导出变更公告                       |          |
| `/report/game_draw_remark/*`                            | GET  | 导出备注                           |          |
| `/report/matchup/*`                                     | GET  | 导出正式赛程                       |          |
| `/report/matchup/4`                                     | GET  | 导出正式赛程                       |          |
| `/report/matchup_draft/*`                               | GET  | 导出初版草稿                       |          |
| `/report/matchup_notice/*`                              | GET  | 导出公告表                         |          |
| `/report/matchup_notice/5`                              | GET  | 导出公告表                         |          |
| `/report/matchup_result/7`                              | GET  | 导出赛果                           |          |
| `/upload/m-team/preview`                                | POST | 导入球队（预览）                   |          |
| `/upload/m-team/save`                                   | POST | 导入球队（保存）                   |          |

### 5.5 异常处理/监控（abnormal / monitor / operation，11 条）

| 路径                                           | 方法     | 前端功能                     | 执行情况 |
| ---------------------------------------------- | -------- | ---------------------------- | -------- |
| `/data-backend/abnormal/completed`           | POST     | 变更完成确认                 |          |
| `/data-backend/abnormal/draw_time`           | GET      | 新建处理、详情               |          |
| `/data-backend/abnormal/record`              | POST     | 新建处理                     |          |
| `/data-backend/abnormal/valid_change_inform` | GET      | 导出变更公告                 |          |
| `/data-backend/abnormal/valid_change_notice` | GET      | 导出变更单                   |          |
| `/data-backend/abnormal/voided`              | POST     | 处理作废                     |          |
| `/data-backend/monitor`                      | GET/POST | 查看异常、查询、填写监控记录 |          |
| `/data-backend/monitor/remark`               | POST     | 备注                         |          |
| `/data-backend/monitor/task/schedule`        | POST     | 添加比赛                     |          |
| `/data-backend/operation-record/blacklist`   | GET      | 查询                         |          |
| `/operation/record`                          | GET      | 查询                         |          |

### 5.6 账号/角色（data-backend 正确形式；Excel 侧现为 /league 错误路径 + GHOST 套件，6 条）

| 路径                                     | 方法              | 前端功能             | 执行情况 |
| ---------------------------------------- | ----------------- | -------------------- | -------- |
| `/data-backend/role`                   | POST/PATCH/DELETE | 添加、修改、删除角色 |          |
| `/data-backend/role/**`                | GET               | 查询角色             |          |
| `/data-backend/manager_account`        | PATCH/DELETE      | 修改、删除账号       |          |
| `/data-backend/manager_account/**`     | GET               | 查询账号             |          |
| `/data-backend/manager_account_enable` | PATCH             | 启用账号             |          |
| `/manager_account_password_reset`      | PATCH             | 重置密码             |          |

### 5.7 数据源匹配补齐（beitai 系 + 快速关联，4 条）

| 路径                                      | 方法 | 前端功能                                     | 执行情况 |
| ----------------------------------------- | ---- | -------------------------------------------- | -------- |
| `/data-backend/realtime/beitai/matchup` | GET  | 匹配赛事、匹配赛季、球队匹配（贝泰十场比赛） |          |
| `/data-backend/relations/beitai/season` | GET  | 匹配赛季                                     |          |
| `/data-backend/relations/beitai/team`   | GET  | 查询、球队匹配（贝泰球队）                   |          |
| `/data-backend/r-season-team/draft`     | POST | 快速关联球队                                 |          |

### 5.8 赛程变更（3 条）

| 路径                                                | 方法 | 前端功能     | 执行情况 |
| --------------------------------------------------- | ---- | ------------ | -------- |
| `/data-backend/schedule-change/has-pending`       | GET  | 赛程变更提示 |          |
| `/data-backend/schedule-change/pending-info-list` | GET  | 赛程变更     |          |
| `/data-backend/schedule-change/process`           | POST | 赛程变更     |          |

### 5.9 提交记录（1 条）

| 路径                                     | 方法 | 前端功能 | 执行情况 |
| ---------------------------------------- | ---- | -------- | -------- |
| `/data-backend/bd-submit-batch/cancel` | GET  | 作废     |          |

### 5.10 查询通配补齐（1 条）

| 路径                         | 方法 | 前端功能                                                                                          | 执行情况 |
| ---------------------------- | ---- | ------------------------------------------------------------------------------------------------- | -------- |
| `/data-backend/m-match/**` | GET  | 查询（通配授权；Excel 仅有 /data-backend/m-match 字面路径，若前端存在带子路径的查询形态则未覆盖） |          |

> 注：去重脚本按「`/data-backend/X` 与根路由 `/X` 等价」的代理规则把 `/data-backend/manager_account`（PATCH/DELETE）视作已被 Excel 的 `/manager_account` 覆盖，脚本得 **88 条**；但 Excel 的 `/manager_account` 实际只测 **POST**（新建账号），PATCH/DELETE（修改/删除账号）**确无覆盖**，故本表如实登记为 **88 条**（= 脚本 88 + manager_account PATCH/DELETE 补记 − 2026-10-10 Excel 修正后已覆盖的 bd-submit-batch，各小节行数合计 14+12+12+24+11+6+4+3+1+1 = 88，无重复登记）。

## 六、待补登记（2026-10-01 之后新增、暂不实现接口测试的接口）

> **维护规则**：清单截止 2026-10-01。此后新增的前端接口若**暂不实现接口测试**，须在此表人工登记（路径/方法/来源/计划），待实现测试后移入 §二。

| 登记日期 | 路径     | 方法 | 来源（PRD/需求） | 备注/计划 | 执行情况 |
| -------- | -------- | ---- | ---------------- | --------- | -------- |
| —       | （暂无） | —   | —               | —        |          |

## 七、monitor 大屏接口覆盖（2026-10-10 纳入）

> **口径说明**：monitor 大屏是独立服务（`DATA_MONITOR_URL = https://test-monitor-192-168-22-216.nip.io:31005`，与 data-bff 的 .218:30024 不同主机），Excel 路径带 `/api/` 网关前缀。**该服务的路由不在 data-bff 的 `toto_permission` 权限表内**（权限表 0 条 `monitor/screen` 记录），其可调用面依据为 `data/monitor/` Excel + `testsuites/monitor/` 套件 + `信息入口/赛事监控大屏PRD文档.md`（0815 版，知识库有 PRD 无接口级文档）。

### 7.1 接口清单（8 条，全部 GET，31 条用例）

| 路径                                     | 方法 | Excel 来源                                    | 套件（testsuites/monitor/ 下） | 用例数 | 执行情况 |
| ---------------------------------------- | ---- | --------------------------------------------- | ------------------------------ | ------ | -------- |
| `/api/monitor/screen/current-gamedraw` | GET  | 接口测试用例_当前监控奖期                     | test_get_draw_list.py          | 12     |          |
| `/api/monitor/screen/today-draw-plan`  | GET  | 接口测试用例_查询今日开奖计划                 | test_draw_plan.py              | 5      |          |
| `/api/monitor/screen/alarms`           | GET  | 接口测试用例_查询大屏中央下部报警信息         | test_alarms.py                 | 2      |          |
| `/api/monitor/screen/world-map`        | GET  | 接口测试用例_查询大屏中央世界地图国家比赛分布 | test_world_map.py              | 2      |          |
| `/api/monitor/screen/abnormal-match`   | GET  | 接口测试用例_查询大屏右侧异常比赛列表         | test_abnormal_match.py         | 1      |          |
| `/api/monitor/screen/top-banner`       | GET  | 接口测试用例_查询大屏顶部横幅条目列表         | test_top_banner.py             | 4      |          |
| `/api/monitor/screen/match-progress`   | GET  | 接口测试用例_查询比赛进度                     | test_match_progress.py         | 4      |          |
| `/api//monitor/screen/duty-roster`     | GET  | 接口测试用例_值班排班周视图                   | —（无绑定套件，见 7.2）       | 1      |          |

### 7.2 注意事项

1. **duty-roster 是唯一未绑定套件的 Excel**：`接口测试用例_值班排班周视图.xlsx`（1 条用例）无任何 `api_test_data` 引用，属**待实现**状态；
2. **`/api//monitor/screen/duty-roster` 存在双斜杠**：与其它 7 条的 `/api/monitor/...` 形式不一致，待实现套件时应先核实真实路由（单/双斜杠其一可能 404）；
3. **免登录**：8 个 Excel 的登录列均为空，`DataMonitor` 继承基类 `API`，其 `login/logout` 为空实现（`common/api.py:256`），即 monitor 服务当前**不走登录鉴权**（与 data-bff 的 TOTP 登录不同）；
4. **数据隔离**：`testsuites/monitor/conftest.py` 有函数级 autouse `get_draw` fixture，对 `bd_game_draw` 停售时间做备份/隔离/恢复，并基线清理 `s_event`/`task`/`toto_dict`，符合「自备数据、自己清理」前提；
5. **后端路由源码不在本地已克隆的仓库中**（sdd-league-platform / test-vegas-core 均无 `monitor/screen` 路由），monitor 为独立服务仓库；2026-10-10 实测该服务 8 条路径均返回 **503**（nginx，服务在 test 环境当前未部署/未就绪），接口存在性以 PRD + Excel + 套件三源印证；
6. **PRD 依据**：`D:\knowledge base\信息入口\赛事监控大屏PRD文档.md`（V0.1 2026-08-15）描述了大屏 6 大模块（左侧统计区/顶部横幅/中央世界地图/中央告警区/右侧交接区/比赛进度），与 8 条接口一一对应（值班排班周视图=右侧交接区轮值安排）；**知识库无 monitor 的接口级文档**（无路径/参数定义），Excel 用例的预期以库表反推为据。
