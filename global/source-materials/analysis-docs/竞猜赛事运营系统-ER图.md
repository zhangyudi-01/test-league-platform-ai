# 竞猜赛事运营系统 · ER 图（基于 test2_newgoal 真实表结构 · 第 13 轮冲刺同步版）

> 依据：`database-docs/北单运营系统-test2_newgoal-202610261418.sql` DDL（187 张表，较 2026-09-17 新增 34 张、修改 4 张）+ `第十三轮冲刺竞彩抓取数据库设计和变更.md` + `竞彩数据采集模块设计文档-第五段是数据库设计.md` + 实库 `test2_newgoal`（279 张表，2026-10-26 连库核验）+ `api-docs/league-core-api` 八份 OpenAPI 规范交叉验证。
> 说明：全库无物理外键，图中连线均为**逻辑外键**（应用层维护的引用关系）；仅绘制业务有效表（排除 ~51 张 `audit_*` 审计表与 ~48 张 `*_bak`/`z_*`/`zbk1_*`/`zz_*` 备份临时表）。
> 查看方式：任何支持 mermaid 的 Markdown 渲染器（IDEA/VSCode/GitLab/GitHub）。

---

## 图 0 · 总览：四层分域、微服务与核心数据流（含第 13 轮中国竞彩域）

```mermaid
flowchart LR
    subgraph SVC["微服务层(OpenAPI 8规范 + 第13轮增量)"]
        direction LR
        BFF["data-bff<br/>158(+12)路径=代理+26自营<br/>(草稿/开奖real-time会话<br/>report/upload/download/otp)"]
        BACK["data-backend<br/>162(+12)路径/198(+12)操作"]
        COLL["data-collection<br/>109+7竞彩接口"]
        COMP["data-computation<br/>14接口(标准化/检测/事件/竞彩关联)"]
        NOTI["notification<br/>SSE 4接口"]
        OPEN["openapi v1<br/>9接口(HMAC+限流)"]
        V1["league-backend/bff<br/>V1老系统(账号/角色)"]
    end
    subgraph L1["采集层 · 数据源镜像(只增不改)"]
        direction TB
        NAMI["nami_* 纳米四运动 ~35表"]
        BEITAI["beitai_* 贝泰足球 ~12表<br/>+sport_radar_prematch_* 赔率3表"]
        TX["tx_* 同行足球 ~7表"]
        BJLOT["bjlot_match 体彩官网"]
        SPTTY["★sporttery_* 中国竞彩 20表<br/>(足球13表 + 篮球7表)"]
    end
    subgraph L2["标准层 · 多源收敛"]
        SMATCH[("s_match 标准化比赛")]
        SEVENT[("s_event 事件")]
    end
    subgraph L3["运营层 · 北单与竞彩监控业务"]
        direction TB
        BD["bd_* 奖期/批次/草稿/正式版/开奖 ~9表"]
        M["m_* 人工主数据 ~8表"]
        R["r_* 匹配关系 5表<br/>(含★r_sporttery_basic/team_data)"]
        TASK["task / task_operation_record / event_match_check"]
        SP_OP["★sporttery_match_event / sporttery_task<br/>/ sporttery_match_remark 3表"]
    end
    L4["支撑层: toto_* 权限(149+1)/字典/配置 + openapi_* + revinfo/audit_*(+5表)"]

    COLL --> L1
    L1 -- "r_basic_data / r_team_data / ★r_sporttery_* 多源ID映射" --> L3
    L1 -- "预处理·字段级集成(足球:贝泰主+纳米辅)" --> SMATCH
    L3 -- "匹配后集成 / ★s_match_id反写sporttery_*_match" --> SMATCH
    SMATCH --> SEVENT --> TASK
    SPTTY --> SP_OP
    SMATCH -- "草稿选比赛/正式版回写" --> BD
    BFF --> BACK --> L3
    FRONT["前端"] --> BFF
    FRONT --> NOTI
    EXT["外部业务方"] --> OPEN
    SCHED["调度器"] --> COLL & COMP
    L3 -.-> L4
```

---

## 图 1 · 主数据域：赛事-赛季-球队与四源匹配（m_* + r_* + ★r_sporttery_* + 黑名单）

```mermaid
erDiagram
    m_competition ||--o{ m_season : "competition_id"
    m_season ||--o{ r_season_team : "manual_season_id"
    m_team ||--o{ r_season_team : "manual_team_id"
    m_competition ||--o{ r_season_team : "manual_competition_id"
    m_competition ||--o{ r_basic_data : "manual_competition_id"
    m_season ||--o{ r_basic_data : "manual_season_id"
    m_team ||--o{ r_team_data : "manual_team_id"
    m_competition ||--o{ r_sporttery_basic_data : "manual_competition_id (★第13轮单选匹配)"
    m_team ||--o{ r_sporttery_team_data : "manual_team_id (★第13轮单选/多选匹配)"
    m_competition ||--o{ m_competition_blacklist : "manual_competition_id"
    m_team ||--o{ m_team_blacklist : "manual_team_id"
    m_season ||--o{ m_match : "season_id"
    m_competition ||--o{ m_match : "competition_id"
    m_team ||--o{ m_match : "home_team_id / away_team_id"
    m_match ||--o{ m_match_remark : "match_id"

    m_competition {
        int competition_id PK "赛事id 自增"
        int sport_id "运动项目(字典league_sport_id)"
        varchar name_zh "赛事全称 uk(sport)"
        varchar short_name_zh "赛事简称 uk(sport)"
        int type "0其他/1联赛/2杯赛/3友谊赛"
        varchar jc_short_name "竞彩简称"
        varchar ctzc_short_name "传统足彩简称"
        tinyint collect_match_flag "是否采集全部比赛"
        tinyint bd_betting_flag "北单竞猜赛事"
        tinyint nami_id_match_status "纳米匹配状态"
        tinyint beitai_id_match_status "贝泰匹配状态"
        int default_sort_order "列表默认排序(null回退更新时间倒序)"
        int select_sort_order "筛选排序"
    }
    m_season {
        int season_id PK
        int competition_id FK
        varchar year "赛季年 uk(competition)"
        varchar name_zh "赛季名称 uk(sport)"
        varchar bd_name "北单全称 uk(sport)"
        varchar bd_short_name "北单简称"
        tinyint nami_id_match_status
        tinyint beitai_id_match_status
        int score "运营综合评分"
        varchar competition_level "赛事级别S/A/B/C/D(字典league_level)"
        varchar official_web "官方网站(官媒外链)"
        varchar media_web_1 "媒体网站1-3(官媒外链)"
        json composition_match_cnt "比赛构成/数量"
        tinyint playoff_flag "附加赛"
        int submit_status "0未提交/1已提交(赛事文件)"
    }
    m_team {
        int team_id PK
        int sport_id
        varchar name_zh "球队全称 uk(sport)"
        varchar short_name_zh "球队简称 uk(sport)"
        varchar bd_team_name "北单全称 uk(sport)"
        varchar bd_team_short_name "北单简称 uk(sport)"
        varchar foreign_name "官网赛程外文名称(★PBL-637支持关联球队回填)"
        varchar name_en "英文全称"
        tinyint nami_id_match_status
        tinyint beitai_id_match_status
        varchar naming_type "命名类型"
        varchar naming_reason "命名原因"
        varchar official_web "官方网站(官媒外链)"
    }
    r_basic_data {
        int relation_id PK
        int source_type "1纳米/2同行/3贝泰"
        int manual_competition_id FK
        int manual_season_id FK "可空=仅赛事级匹配"
        int source_competition_id "数据源赛事id"
        bigint source_season_id "数据源赛季id"
        int nami_competition_id "同行源时桥接纳米赛事"
        json stage_group "数据源阶段轮次分组"
        tinyint relation_status "0未匹配/1赛事匹配/2赛事和赛季匹配/3不匹配"
    }
    r_team_data {
        int relation_id PK
        int manual_team_id FK
        int standard_team_id "标准化球队id"
        tinyint source_type "1纳米/2同行/3贝泰"
        int source_team_id "数据源球队id"
    }
    r_sporttery_basic_data {
        int relation_id PK "★第13轮新增: 竞彩赛事匹配表(实库95条)"
        int source_type "固定4=中国竞彩"
        int sport_id "1足球/2篮球"
        int manual_competition_id FK "人工赛事id(可空)"
        int sporttery_competition_id "竞彩赛事league_id"
        tinyint relation_status "0未匹配/1赛事匹配"
        bigint version "乐观锁版本号"
    }
    r_sporttery_team_data {
        int relation_id PK "★第13轮新增: 竞彩球队匹配表"
        int manual_team_id FK "uk_std_team(sporttery_team_id,sport_id,manual_team_id)"
        int sport_id "1足球/2篮球"
        tinyint source_type "固定4=中国竞彩"
        int sporttery_team_id "竞彩球队team_id"
    }
    r_season_team {
        int season_team_id PK
        int manual_competition_id FK
        int manual_season_id FK
        int manual_team_id FK
        varchar season_bd_team_name "本赛季北单全称 uk(season)"
        varchar season_bd_team_short_name "本赛季北单简称 uk(season)"
        varchar naming_type
        int submit_status "0未提交/1已提交(球队文件)"
    }
    m_competition_blacklist {
        int competition_blacklist_id PK
        int manual_competition_id FK
        varchar reason "添加原因"
        varchar del_reason "移除原因"
    }
    m_team_blacklist {
        int team_blacklist_id PK
        int manual_team_id FK
        varchar reason
        varchar del_reason
    }
    m_match {
        int match_id PK "人工比赛id"
        int sport_id
        int season_id FK
        int competition_id FK
        int home_team_id FK
        int away_team_id FK
        int match_status "比赛状态(字典match_status)"
        varchar match_stage "阶段"
        varchar match_group "分组"
        varchar match_round "轮次"
        datetime match_time "开赛时间"
        int home_score_half
        int away_score_half
        int home_score
        int away_score
        int nami_id_match_status
        int beitai_id_match_status
    }
    m_match_remark {
        int remark_id PK
        int remark_type "1赛程/2让球/3比赛监控"
        int match_id FK
        varchar remark "备注(300) uk(type+match+account)"
    }
```

## 图 2 · 标准层：s_match 四源收敛 + 事件

```mermaid
erDiagram
    m_match ||..o| s_match : "manual_match_id 自动同步"
    s_match ||--o{ s_event : "match(经identity_data)"
    s_event ||--o{ task : "event_id"
    s_event ||--o{ event_match_check : "check_type=1 check_source_id=event_id"

    s_match {
        int match_id PK "标准化比赛id(全系统身份收敛点)"
        int sport_id
        int season_id "标准化赛季id"
        int competition_id
        json matchup_unique_no "北单比赛唯一编号(list,一赛多号)"
        int beitai_match_id "贝泰比赛id idx"
        int nami_match_id "纳米比赛id idx"
        int tx_match_id "同行比赛id idx"
        int manual_match_id "人工比赛id idx"
        int home_team_id
        int away_team_id
        varchar match_round "轮次"
        varchar match_stage "阶段"
        varchar match_group "分组"
        int status_id "复合状态(字典s_match_status 40项) idx"
        datetime match_time "比赛时间 idx"
        int home_score_half "半场比分(开奖用int)"
        int away_score_half
        int home_score "全场比分(开奖用)"
        int away_score
        varchar home_score_all "源数据json(半场/全场/加时/点球)"
        varchar away_score_all
        varchar home_position "主队排名"
        varchar away_position
        int venue_id
        varchar weather
        int bd_matchup_home_team_id "北单赛程主队(正式版回写)"
        int replace_id "置换链:旧比赛关联新比赛id idx"
    }
    s_event {
        varchar event_id PK "幂等ID(由identity_data生成)"
        int event_type "0无异常/1比赛异常/2数据异常/3预警"
        varchar event_level "红/橙/黄/无"
        json identity_data "事件标识(key升序序列化)"
        varchar source_type "来源 表名.字段名"
        bigint source_id
        varchar reason_title
        varchar reason_desc "详情(5000)"
    }
```

## 图 3 · 北单赛程域：奖期→批次→草稿→比对→正式版→赛果批次→提交

```mermaid
erDiagram
    bd_game_draw ||--o{ bd_batch : "game_draw_id"
    bd_batch ||--o{ bd_batch_matchup_draft : "batch_id (按create_account分用户)"
    bd_batch ||--o{ bd_batch_matchup : "batch_id"
    bd_batch ||--o{ bd_batch_diff_record : "game_draw_id+batch_id 联合PK(操作锁)"
    bd_batch ||--o{ bd_batch_matchup_diff : "batch_id"
    bd_batch_matchup ||--o{ bd_batch_matchup_draw : "batch_matchup_id"
    bd_batch ||--o{ bd_batch_matchup_draw : "batch_id(开奖批次batch_type=1)"
    bd_batch ||--o{ bd_batch_matchup_draw_review : "batch_id"
    bd_batch ||--o{ bd_submit_batch : "batch_id"
    s_match ||--o{ bd_batch_matchup_draft : "match_id(读取)"
    s_match ||--o{ bd_batch_matchup : "match_id(生成正式版/异常变更回写)"
    toto_account ||--o{ bd_batch_matchup_draw_review : "account_id"

    bd_game_draw {
        int game_draw_id PK "奖期id 自增"
        varchar draw_no "奖期编号(5位,年+月)"
        datetime sale_begin_time "开售时间"
        datetime sale_end_time "停售时间"
        datetime draw_time "开奖时间"
        tinyint game1200 "单场竞猜开售"
        tinyint game1260 "下半场比分开售"
        tinyint game1270 "胜负过关开售"
    }
    bd_batch {
        int batch_id PK
        int game_draw_id FK
        int batch_order_no "批次序号(可拖拽调整)"
        int batch_type "0赛程批次/1开奖批次"
        varchar sports_id_list "运动项目csv(赛程态)"
        int is_final_version "是否生成正式版(赛程态)"
        datetime preset_sale_begin_time "计划开售时间(赛程态)"
        varchar draw_game_id_list "开奖游戏csv(开奖态)"
        datetime preset_draw_time "计划开奖时间(开奖态)"
        int batch_sale_status "开售状态(官网采集回写)"
        int submit_status "文件提交状态"
        int batch_draw_status "开奖状态(官网采集回写)"
    }
    bd_batch_matchup_draft {
        int matchup_draft_id PK
        int batch_id FK "idx"
        int sort_no "展示排序"
        int game_draw_id FK "idx"
        int match_id FK "idx"
        int manual_competition_id
        int manual_season_id
        int game1200_matchup_no "单场场次编号"
        int game1260_matchup_no "下半场场次编号"
        int game1270_matchup_no "胜负场次编号"
        varchar bd_round "轮次(可编辑)"
        datetime match_time "开赛时间(可编辑)"
        int home_team_id
        int away_team_id
        int team_reverse "主客调换"
        datetime sale_end_time "停售时间"
        datetime game1260_sale_end_time "下半场停售时间"
        int game1200_handicap "单场让球"
        decimal game1270_handicap "胜负让球"
        datetime game1200_draw_time "单场开奖时间"
        datetime game1260_draw_time "下半场开奖时间"
        datetime game1270_draw_time "胜负开奖时间"
        tinyint review_status "0未审核/1初审/2复核 ★草稿独有"
        varchar sale_game_list "开售游戏csv"
        varchar create_account "★用户隔离键(无独立user列)"
    }
    bd_batch_matchup {
        int batch_matchup_id PK
        int batch_id FK "idx"
        int sort_no
        int game_draw_id FK "idx"
        int match_id FK "idx"
        varchar matchup_unique_no "18位比赛编号 idx ★正式版独有"
        int game1200_matchup_no
        int game1260_matchup_no
        int game1270_matchup_no
        varchar bd_round
        datetime match_time
        int home_team_id
        int away_team_id
        int team_reverse
        datetime sale_end_time
        datetime game1260_sale_end_time
        int game1200_handicap
        decimal game1270_handicap
        varchar sale_game_list
        datetime game1200_draw_time
        datetime game1270_draw_time
        datetime game1260_draw_time
        int match_result_status "赛果确认状态 ★正式版独有"
        int home_score_half "★以下赛果四字段正式版独有"
        int away_score_half
        int home_score
        int away_score
        datetime confirm_time "赛果确认时间"
        varchar confirm_account "赛果确认账户"
    }
    bd_batch_diff_record {
        int game_draw_id PK "联合PK=操作锁"
        int batch_id PK
        tinyint diff_status "0进行中/1完成/2取消"
        varchar diff_base_account "基准用户(主草稿)"
        varchar diff_target_account_list "比对用户csv"
    }
    bd_batch_matchup_diff {
        int matchup_diff_id PK
        int match_id "diff_type=1/2缺比赛id,3不一致id idx"
        int batch_id FK "idx"
        int game_draw_id FK "idx"
        datetime diff_time
        varchar diff_base_account
        varchar diff_target_account
        tinyint diff_type "1基准缺少/2比对方缺少/3值不一致"
        varchar diff_field "比较字段"
        varchar diff_base_value
        varchar diff_target_value
    }
    bd_batch_matchup_draw {
        int batch_matchup_id PK "联合PK 同正式版主键"
        varchar draw_game_list PK "开奖游戏csv"
        int batch_id_match_result PK "赛果批次id idx"
        int match_id
        int game_draw_id
        varchar matchup_unique_no "idx"
    }
    bd_batch_matchup_draw_review {
        int review_id PK
        int batch_id FK "uk(batch,account)"
        int account_id FK "toto_account"
        tinyint review_status "0未审核/1已审核(≥3人可提交)"
        datetime review_time
    }
    bd_submit_batch {
        int submit_id PK "提交到v2的批次号"
        int batch_id FK
        varchar business_type "A1-A5/B1-B3"
        varchar submit_title
        int submit_count "数据量"
        json detail "完整json文件内容快照"
        int submit_type "1线上sftp/2线下下载"
        int submit_status "0作废/1成功"
    }
```

## 图 4 · 事件-任务-变更域

```mermaid
erDiagram
    s_event ||--o{ task : "event_id idx"
    task ||--o{ task_operation_record : "task_id"
    s_event ||--o{ task_operation_record : "event_id"
    s_match ||--o{ task_operation_record : "match_id"
    s_event ||--o{ event_match_check : "check_type=1"
    s_match ||--o{ event_match_check : "check_type=2 (check_source_id=match_id)"

    task {
        int task_id PK
        varchar event_id FK "idx"
        varchar task_name "暂存identity_data.eventName"
        varchar task_type "字典task_type: 提前/推迟/延期/中断/取消/腰斩/球队变更/赛果争议"
        varchar task_role "management赛程/monitoring监控"
        int confirm_result "0未确认/1已确认/2已解除"
        datetime confirm_time
        varchar confirm_account
        int task_status "0待执行/1执行中/2完成/3取消/4失败"
        varchar attribution_title "异常原因一级(字典两级11大类)"
        varchar attribution_desc "异常原因详述"
        json task_detail "执行步骤(按taskType异构)"
        varchar task_remark "备注"
    }
    task_operation_record {
        int operation_record_id PK "变更管理实体表"
        int task_id FK "idx"
        varchar event_id FK "idx"
        int match_id FK "idx"
        json matchup_unique_no "涉及的全部比赛编号"
        varchar task_type "同task"
        varchar change_type "字典change_type: 调整停售/开奖延后/退票/争议赛果/按实际结果开奖(+记录在案)"
        int invalid_status "0有效/1无效(不采纳且导出过变更单)"
        int change_status "0待执行/1执行中/2已完成"
        int submit_status "是否导出过变更单"
        json change_info "按change_type异构(时间/比分/四文本)"
        varchar operation_account
        datetime operation_time
    }
    event_match_check {
        int check_id PK
        int check_type "1事件核实 / 2赛果审核 ★一表两用"
        varchar check_source_id "事件id或比赛id idx(check_source+status)"
        int check_result "0待确认/1已确认/2已解除"
        int check_status "0未核实/1已核实"
        varchar check_channel "核实渠道(字典source_name)"
        datetime check_time
        json change_info "赛果审核存json比分"
        int bd_matchup_home_team_id "审核时的北单主队"
        int data_source_type "★第12/13轮新增: 赛果审核人所选数据源(1纳米/3贝泰)"
    }
```

## 图 5 · 权限支撑域

```mermaid
erDiagram
    toto_system ||--o{ toto_role : "system_id"
    toto_system ||--o{ toto_permission : "system_id"
    toto_role ||--o{ toto_role_permission : "role_id"
    toto_permission ||--o{ toto_role_permission : "permission_id"
    toto_account ||--o{ toto_account_role : "account_id"
    toto_role ||--o{ toto_account_role : "role_id"
    rdc ||--o{ toto_account : "rdc_id"

    toto_account {
        int account_id PK
        varchar account UK "登录名唯一"
        varchar account_user "真实姓名"
        varchar password "符合复杂度"
        int rdc_id FK "所属中心"
        datetime last_password_change_time ">90天强制改密"
        tinyint account_type "0管理/1普通"
        tinyint account_status "0停用/1启用"
        varchar account_status_changed_reason
        tinyint two_factor_bind_status "双因子绑定"
        varchar token_id "令牌UUID"
        tinyint is_deleted
    }
    toto_role {
        int role_id PK
        varchar role_name
        varchar role_desc
        tinyint role_type "0三员角色(1/2/3固定)/1普通"
        int system_id FK
        tinyint is_deleted
    }
    toto_permission {
        int permission_id PK
        tinyint permission_type "0不可人工分配/1可分配"
        varchar level1 "一级权限"
        varchar level2 "二级权限"
        varchar level3 "三级权限(功能点)"
        json urls "权限对应服务资源URL+method(实库149条+#147待入库)"
        tinyint is_deleted
    }
    toto_role_permission {
        int role_permission_id PK
        int role_id FK "uk(role,permission,system)"
        int permission_id FK
        int system_id FK
    }
    toto_account_role {
        int account_role_id PK
        int account_id FK
        int role_id FK
        int system_id FK
    }
    toto_operation_record {
        int record_id PK "17万+ 操作留痕"
        varchar operation_module
        varchar operation_type
        varchar operation_code "业务操作唯一标识"
        varchar result
        varchar account
        int operation_role_id
        datetime operation_time "idx"
        varchar operation_key1 "业务关键字1-3"
        varchar ipaddress
        varchar error_detail
    }
    toto_dict {
        varchar dict_key PK "联合PK"
        int dict_value PK
        varchar dict_desc "481条: 状态机/异常原因/事件类型/赔率公司等"
    }
    toto_config {
        varchar config_key PK "联合PK"
        varchar config_value PK
        tinyint ui_config_flag "管理端可否修改"
        int rdc_id "分中心级配置(空=全局)"
    }
```

## 图 6 · 采集层：纳米/同行/贝泰/SportRadar/体彩官网表族（以足球为例）

```mermaid
erDiagram
    nami_football_category ||--o{ nami_football_competition : "category_id"
    nami_football_category ||--o{ nami_football_country : "category_id"
    nami_football_competition ||--o{ nami_football_season : "competition_id"
    nami_football_competition ||--o{ nami_football_competition_rule : "competition_id"
    nami_football_competition ||--o{ nami_football_competition_table_detail : "competition_id"
    nami_football_season ||--o{ nami_football_stage : "season_id"
    nami_football_season ||--o{ nami_football_match : "season_id"
    nami_football_season ||--o{ nami_football_competition_table_detail : "season_id"
    nami_football_team ||--o{ nami_football_match : "home_team_id/away_team_id"
    nami_football_venue ||--o{ nami_football_match : "venue_id"
    nami_football_match ||--o| nami_football_match_live : "match_id"
    nami_football_match ||--o{ nami_football_europe_odds : "match_id"
    nami_football_match ||--o{ nami_football_odds : "match_id"
    nami_football_match ||--o| nami_football_match_analysis : "match_id"
    nami_football_europe_odds_company ||--o{ nami_football_europe_odds : "company_id"
    nami_football_team ||--o{ nami_football_table_live : "team_id"

    tx_competition ||--o{ tx_season : "competition_id"
    tx_season ||--o{ tx_stage : "season_id"
    tx_competition ||--o{ tx_match : "competition_id"
    tx_team ||--o{ tx_match : "home_team_id/away_team_id"

    beitai_football_tournament ||--o{ beitai_football_season : "tournament_id"
    beitai_football_season ||--o{ beitai_football_stage : "season_id"
    beitai_football_tournament ||--o{ beitai_football_team : "tournament_id"
    beitai_football_match ||--o| beitai_football_match_live : "match_id"
    beitai_football_match ||--o{ beitai_football_event : "match_id"
    beitai_football_match ||--o{ beitai_football_period : "match_id"
    beitai_football_match ||--o{ sport_radar_prematch_european_odds : "sport_event_id"
    beitai_football_match ||--o{ sport_radar_prematch_asian_handicap_odds : "sport_event_id"
    beitai_football_standing_snapshot ||--o{ beitai_football_standing_snapshot_item : "snapshot_id"

    beitai_football_match {
        int match_id PK
        int tournament_id
        int season_id
        varchar status "live/abandoned/cancelled/closed/ended/not_started/postponed"
        varchar live_match_status "live接口状态"
        varchar effective_match_status "有效状态(live优先)"
        int replaced_by "替补赛程ID(延期重排新比赛)"
        int home_virtual "主队占位"
        int away_virtual "客队占位"
        datetime resumetime "延期恢复时间"
        varchar coverage_scores "★第13轮新增: 比分更新方式(live实时/post赛后)"
    }
    sport_radar_prematch_european_odds {
        bigint id PK "★第13轮实库21.5万行: SportRadar赛前欧赔"
        int sport_event_id "关联比赛ID"
        int bookmaker_id "博彩公司ID"
        decimal home_win_odds
        decimal draw_odds
        decimal away_win_odds
    }
    sport_radar_prematch_asian_handicap_odds {
        bigint id PK "★第13轮实库110.6万行: SportRadar赛前亚盘"
        int sport_event_id "关联比赛ID"
        int bookmaker_id "博彩公司ID"
        varchar line "盘口线"
        decimal home_odds
        decimal away_odds
    }
    beitai_football_standing_snapshot {
        bigint id PK "事实+投影双表设计"
        bigint season_id
        int tournament_id
        json team_data "全部球队数据(事实源)"
        varchar snapshot_hash "SHA-256完整性校验"
    }
    beitai_football_standing_snapshot_item {
        bigint id PK "查询投影"
        bigint snapshot_id FK
        varchar standing_type "TOTAL/HOME/AWAY"
        bigint team_id
        int team_rank
        int points
    }
    nami_football_match {
        int match_id PK
        int season_id
        int competition_id
        int home_team_id
        int away_team_id
        int status_id "字典nami_football_match_status 0-13"
        bigint match_time "时间戳(秒)"
        json home_scores "比分list"
        json away_scores
        int round_stage_id "轮次-阶段id"
        int round_group_num "第几组"
        int round_round_num "第几轮"
        int team_reverse "主客相反"
        int tbd "时间待定"
        int related_id "双回合另一场"
        json agg_score "双回合总比分"
        bigint updated_at "纳米更新时间(秒)"
    }
    nami_football_deleted {
        varchar deleted_type PK "联合PK 通告表"
        int id PK "1分类/2球队/4赛事/5阶段/6赛季/7场馆/8比赛/9球员"
    }
    tx_match {
        int match_id PK
        int competition_id
        bigint match_date "时间戳(毫秒)"
        bigint season_id
        bigint stage_id
        int status "字典tx_match_status 0-17"
        json score "常规比分"
        varchar half "半场"
        json score_all "含加时"
        json score_point "点球"
        int valid_game "1正常/0异常"
    }
    bjlot_match {
        int draw_id PK "联合PK 体彩官网回读"
        int matchup_no PK "场次编号"
        varchar draw_no "奖期编号"
        varchar matchup_unique_no "比赛唯一编号"
        varchar bj_match_status "赛程状态"
        json sp "sp值"
    }
```

---

## 图 6B · 第 13 轮新增：中国竞彩（Sporttery）全链路分域 ER 图（采集 20 表 + 匹配 2 表 + 监控事件/任务/备注 3 表）

```mermaid
erDiagram
    sporttery_football_league ||--o{ sporttery_football_match : "league_id"
    sporttery_football_team ||--o{ sporttery_football_match : "home_team_id / away_team_id"
    sporttery_football_match ||--o| sporttery_football_had_odds : "match_id(最新胜平负)"
    sporttery_football_match ||--o| sporttery_football_hhad_odds : "match_id(最新让球胜平负)"
    sporttery_football_match ||--o| sporttery_football_crs_odds : "match_id(最新比分)"
    sporttery_football_match ||--o| sporttery_football_ttg_odds : "match_id(最新总进球)"
    sporttery_football_match ||--o| sporttery_football_hafu_odds : "match_id(最新半全场)"
    sporttery_football_match ||--o{ sporttery_football_had_odds_record : "match_id+release_time(历史)"
    sporttery_football_match ||--o{ sporttery_football_hhad_odds_record : "match_id+release_time(历史)"
    sporttery_football_match ||--o{ sporttery_football_crs_odds_record : "match_id+release_time(历史)"
    sporttery_football_match ||--o{ sporttery_football_ttg_odds_record : "match_id+release_time(历史)"
    sporttery_football_match ||--o{ sporttery_football_hafu_odds_record : "match_id+release_time(历史)"

    sporttery_basketball_league ||--o{ sporttery_basketball_match : "league_id"
    sporttery_basketball_team ||--o{ sporttery_basketball_match : "home_team_id / away_team_id"
    sporttery_basketball_match ||--o| sporttery_basketball_mnl_odds : "match_id(最新胜负)"
    sporttery_basketball_match ||--o| sporttery_basketball_hdc_odds : "match_id(最新让分胜负)"
    sporttery_basketball_match ||--o| sporttery_basketball_hilo_odds : "match_id(最新大小分)"
    sporttery_basketball_match ||--o| sporttery_basketball_wnm_odds : "match_id(最新胜分差)"

    m_competition ||--o{ r_sporttery_basic_data : "manual_competition_id(单选)"
    sporttery_football_league ||--o| r_sporttery_basic_data : "sporttery_competition_id(sport_id=1)"
    sporttery_basketball_league ||--o| r_sporttery_basic_data : "sporttery_competition_id(sport_id=2)"

    m_team ||--o{ r_sporttery_team_data : "manual_team_id(单选/多选)"
    sporttery_football_team ||--o{ r_sporttery_team_data : "sporttery_team_id(sport_id=1)"
    sporttery_basketball_team ||--o{ r_sporttery_team_data : "sporttery_team_id(sport_id=2)"

    s_match ||--o{ sporttery_football_match : "s_match_id(关联标准比赛)"
    s_match ||--o{ sporttery_basketball_match : "s_match_id(关联标准比赛)"
    sporttery_football_match ||--o{ sporttery_match_event : "source_id(sport_id=1)"
    sporttery_basketball_match ||--o{ sporttery_match_event : "source_id(sport_id=2)"
    sporttery_match_event ||--o{ sporttery_task : "event_id"
    sporttery_football_match ||--o{ sporttery_match_remark : "match_id(sport_id=1)"
    sporttery_basketball_match ||--o{ sporttery_match_remark : "match_id(sport_id=2)"

    sporttery_football_league {
        int league_id PK "实库77条"
        varchar league_name "赛事全称"
        varchar league_name_abbr "赛事简称"
        varchar league_back_color "底色"
    }
    sporttery_football_team {
        int team_id PK "实库1124条"
        varchar team_name "球队全称"
        varchar team_name_abbr "球队简称"
        varchar team_All_en_name "英文全称"
    }
    sporttery_football_match {
        bigint match_id PK "实库20617条: 竞彩足球比赛ID"
        bigint s_match_id FK "我方标准比赛ID(idx_s_match_id)"
        varchar match_num_str "周几+编号(如周一001)"
        int match_num "场次号(如1001)"
        varchar match_date "比赛日"
        datetime match_start_time "开赛时间(idx)"
        int league_id FK
        int home_team_id FK
        int away_team_id FK
        int sell_status "0待开售/1在售/2停售/3已开奖"
        varchar match_status "竞彩赛事状态"
        int home_half_score
        int away_half_score
        int home_score
        int away_score
        varchar had_combination_desc "胜平负彩果"
        varchar hhad_combination_desc "让球胜平负彩果"
        int if_change "是否队伍变动:0否/1是"
    }
    sporttery_basketball_match {
        bigint match_id PK "实库10727条: 竞彩篮球比赛ID"
        bigint s_match_id FK "我方标准比赛ID(idx_s_match_id)"
        varchar match_num_str "周几+编号"
        int match_num "场次号"
        datetime match_start_time "开赛时间(idx)"
        int league_id FK
        int home_team_id FK
        int away_team_id FK
        int sell_status "0待开售/1在售/2停售/3已开奖"
        varchar part_end "全场比分(注意格式=客队:主队)"
        int away_score "★第13轮新增: 客队全场比分(part_end左值)"
        int home_score "★第13轮新增: 主队全场比分(part_end右值)"
        int if_change "是否队伍变动:0否/1是"
    }
    sporttery_match_event {
        varchar event_id PK "幂等ID(11位)"
        int event_type "0无异常/1比赛异常/2数据异常/3预警"
        varchar event_level "红/橙/黄/无"
        json identity_data "事件唯一标识JSON"
        varchar source_type "固定SPORTTERY"
        bigint source_id "竞彩match_id"
        int sport_id "1足球/2篮球"
        bigint s_match_id "关联标准比赛ID"
        int event_code "事件编码"
        varchar reason_title "原因概述"
        varchar reason_desc "原因详述(5000)"
        json notification_data "通知展示数据"
    }
    sporttery_task {
        int task_id PK
        varchar event_id FK "idx_st_event_id"
        varchar task_name
        varchar task_type "提前/推迟/中断/取消/腰斩/球队变更"
        varchar task_role "monitoring监控等"
        int confirm_result "0未确认/1已确认/2已解除"
        int task_status "0待执行/1执行中/2完成/3取消/4失败"
    }
    sporttery_match_remark {
        int remark_id PK
        int sport_id "uk_sptty_user_remark(sport_id,remark_type,match_id,create_account)"
        int remark_type "3比赛监控"
        int match_id FK "竞彩比赛ID"
        varchar remark "备注(300)"
        varchar create_account
    }
```

---

## 图 7 · 核心生命周期时序（补充：数据如何流经各表与服务）

```mermaid
sequenceDiagram
    autonumber
    participant SRC as 数据源(纳米/贝泰/同行)
    participant COLL as data-collection
    participant COMP as data-computation
    participant SM as s_match
    participant EV as s_event
    participant MQ as RabbitMQ
    participant TK as task
    participant BFF as data-bff(会话)
    participant OP as 运营人员
    participant DRAFT as bd_batch_matchup_draft
    participant FORMAL as bd_batch_matchup
    participant SFTP as 北单系统(sftp)
    participant BJ as bjlot_match

    SRC->>COLL: API拉取(init全量/update增量)
    COLL->>COMP: 写入原始表(带updated_at)
    COMP->>SM: 标准化(足球为贝泰主、纳米为辅、批量查询、分桶处理)
    COMP->>EV: 预处理比赛更新事件(type=0)
    SM->>EV: 17规则数据识别(状态/时间/比分/删除/球队变更)
    EV->>MQ: binlog经CDC进入事件队列
    MQ->>TK: 生成任务(按赛程状态路由角色)
    MQ-->>OP: SSE通知
    OP->>BFF: real-time会话编辑(添加/让球/排序、未入库)
    OP->>DRAFT: POST固化保存(draftProcessNodes流程节点)
    OP->>DRAFT: 草稿比对(分布式锁、bd_batch_diff_record)
    OP->>FORMAL: 生成正式版(18位编号)
    FORMAL-->>SM: 回写开赛时间与bd_matchup_home_team_id
    OP->>SFTP: 提交赛事/球队/比赛文件(A4/A5/A1或A3、记录bd_submit_batch)
    BJ-->>FORMAL: 官网采集开售状态(batch_sale_status)
    OP->>EV: 完场后赛果审核(event_match_check type=2、两人审核、batch批量)
    OP->>FORMAL: 赛果确认(check、diff、confirm三步)
    OP->>SFTP: 提交赛果文件(A2)
    BJ-->>SM: 开奖采集、状态置为xx06终态
```
