-- MySQL dump 10.13  Distrib 8.1.0, for Win64 (x86_64)
--
-- Host: 192.168.22.218    Database: test2_newgoal
-- ------------------------------------------------------
-- Server version	8.4.9

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `nami_american_football_stage`
--

DROP TABLE IF EXISTS `nami_american_football_stage`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_american_football_stage` (
  `stage_id` int NOT NULL COMMENT '阶段id',
  `category_id` int DEFAULT NULL COMMENT '分类id',
  `kind` int DEFAULT NULL COMMENT '阶段类型枚举(0-13)',
  `competition_id` int DEFAULT NULL COMMENT '赛事id',
  `season_id` int DEFAULT NULL COMMENT '赛季id',
  `name_zh` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文名称',
  `name_en` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `name_zht` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语名称',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`stage_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米橄榄球阶段列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_sporttery_basketball_match`
--

DROP TABLE IF EXISTS `audit_sporttery_basketball_match`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_sporttery_basketball_match` (
  `match_id` bigint NOT NULL COMMENT '官方比赛 ID，与篮球赛程表一致',
  `s_match_id` int DEFAULT NULL COMMENT '修订时关联的标准化比赛 s_match.match_id',
  `if_change` tinyint DEFAULT NULL COMMENT '修订时预处理维护的主客方向：0顺序一致、1主客反序',
  `rev` int NOT NULL COMMENT 'Envers 修订号，业务关联共享 revinfo.rev',
  `revtype` tinyint DEFAULT NULL COMMENT '操作类型：0新增、1修改、2删除',
  `match_no` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '修订时的场次编号',
  `business_date` date DEFAULT NULL COMMENT '修订时的受注业务日',
  `league_id` bigint DEFAULT NULL COMMENT '修订时的官方联赛 ID',
  `home_team_id` bigint DEFAULT NULL COMMENT '修订时的官方主队 ID',
  `away_team_id` bigint DEFAULT NULL COMMENT '修订时的官方客队 ID',
  `match_time` datetime DEFAULT NULL COMMENT '修订时的完整比赛时间',
  `sell_status` tinyint DEFAULT NULL COMMENT '修订时销售状态：1在售、2停售、3已开奖',
  `part1` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '修订时的第1节比分',
  `part2` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '修订时的第2节比分',
  `part3` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '修订时的第3节比分',
  `part4` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '修订时的第4节比分',
  `part_end` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '修订时的终场比分',
  `home_score` int DEFAULT NULL COMMENT '修订时主队全场得分',
  `away_score` int DEFAULT NULL COMMENT '修订时客队全场得分',
  `remark` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '修订时的官方备注',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`match_id`,`rev`) USING BTREE,
  KEY `idx_sporttery_basketball_match_audit_rev` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='竞彩篮球赛程审计表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_football_competition_table_detail`
--

DROP TABLE IF EXISTS `nami_football_competition_table_detail`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_football_competition_table_detail` (
  `season_id` int NOT NULL COMMENT '赛季id',
  `competition_id` int NOT NULL COMMENT '赛事id',
  `team_id` int NOT NULL COMMENT '球队id',
  `promotions_name_zh` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '升降级中文名',
  `tables_id` int NOT NULL COMMENT '积分榜id',
  `conference` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '分区信息',
  `group` int DEFAULT NULL COMMENT '不为0表示分组赛的第几组，1-A、2-B以此类推',
  `stage_id` int DEFAULT NULL COMMENT '所属阶段id',
  `promotion_id` int DEFAULT NULL COMMENT '升降级id',
  `points` int DEFAULT NULL COMMENT '积分',
  `position` int DEFAULT NULL COMMENT '排名',
  `deduct_points` int DEFAULT NULL COMMENT '扣除积分',
  `note` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '说明',
  `total` int DEFAULT NULL COMMENT '比赛场次',
  `won` int DEFAULT NULL COMMENT '胜的场次',
  `draw` int DEFAULT NULL COMMENT '平的场次',
  `loss` int DEFAULT NULL COMMENT '负的场次',
  `goals` int DEFAULT NULL COMMENT '进球',
  `goals_against` int DEFAULT NULL COMMENT '失球',
  `goal_diff` int DEFAULT NULL COMMENT '净胜球',
  `home_points` int DEFAULT NULL COMMENT '主场积分',
  `home_position` int DEFAULT NULL COMMENT '主场排名',
  `home_total` int DEFAULT NULL COMMENT '主场比赛场次',
  `home_won` int DEFAULT NULL COMMENT '主场胜的场次',
  `home_draw` int DEFAULT NULL COMMENT '主场平的场次',
  `home_loss` int DEFAULT NULL COMMENT '主场负的场次',
  `home_goals` int DEFAULT NULL COMMENT '主场进球',
  `home_goals_against` int DEFAULT NULL COMMENT '主场失球',
  `home_goal_diff` int DEFAULT NULL COMMENT '主场净胜球',
  `away_points` int DEFAULT NULL COMMENT '客场积分',
  `away_position` int DEFAULT NULL COMMENT '客场排名',
  `away_total` int DEFAULT NULL COMMENT '客场比赛场次',
  `away_won` int DEFAULT NULL COMMENT '客场胜的场次',
  `away_draw` int DEFAULT NULL COMMENT '客场平的场次',
  `away_loss` int DEFAULT NULL COMMENT '客场负的场次',
  `away_goals` int DEFAULT NULL COMMENT '客场进球',
  `away_goals_against` int DEFAULT NULL COMMENT '客场失球',
  `away_goal_diff` int DEFAULT NULL COMMENT '客场净胜球',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`season_id`,`team_id`,`tables_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin ROW_FORMAT=DYNAMIC COMMENT=' 纳米足球赛事积分榜';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `toto_account_role`
--

DROP TABLE IF EXISTS `toto_account_role`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `toto_account_role` (
  `account_role_id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '角色账号关系ID 自增',
  `account_id` int unsigned NOT NULL COMMENT '账号 ID',
  `role_id` int NOT NULL COMMENT '角色 ID',
  `system_id` int NOT NULL COMMENT '系统 ID',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账号',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账号',
  PRIMARY KEY (`account_role_id`) USING BTREE,
  UNIQUE KEY `uk_account_role` (`account_id`,`role_id`,`system_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=199 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='角色账号关系';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_task_operation_record`
--

DROP TABLE IF EXISTS `audit_task_operation_record`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_task_operation_record` (
  `operation_record_id` int NOT NULL AUTO_INCREMENT COMMENT '变更记录ID',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `task_id` int NOT NULL COMMENT '任务ID',
  `event_id` varchar(11) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '事件ID',
  `match_id` int NOT NULL COMMENT '比赛id',
  `matchup_unique_no` json DEFAULT NULL COMMENT '北单比赛唯一编号',
  `task_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '任务类型,比赛提前 比赛推迟 比赛中断 比赛取消 比赛腰斩 球队变更 赛果争议',
  `change_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '变更类型,调整停售时间、开奖延后、退票、争议赛果、按实际结果开奖',
  `invalid_status` int DEFAULT NULL COMMENT '有效状态 0 有效 1 无效，当前变更记录是否被中心或运营人员采纳，当不采纳时又导出过变更单后，可以设置为无效',
  `change_status` int DEFAULT NULL COMMENT '变更状态 0待执行 1执行中 2已完成',
  `submit_status` int DEFAULT NULL COMMENT '提交状态 0 未提交 1已提交，提交是否导出过变更单',
  `change_info` json DEFAULT NULL COMMENT '任务变更详情，根据change_type存储不同的结构',
  `operation_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '操作人',
  `operation_time` datetime DEFAULT NULL COMMENT '操作时间',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`operation_record_id`,`rev`) USING BTREE,
  KEY `FK_rev` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_american_football_category`
--

DROP TABLE IF EXISTS `nami_american_football_category`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_american_football_category` (
  `category_id` int NOT NULL COMMENT '分类id',
  `name_zh` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文名称',
  `name_en` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `name_zht` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语名称',
  `country_id` int DEFAULT NULL COMMENT '国家id',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`category_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米橄榄球分类列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_nami_american_football_match`
--

DROP TABLE IF EXISTS `audit_nami_american_football_match`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_nami_american_football_match` (
  `match_id` int NOT NULL COMMENT '比赛id',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `competition_id` int DEFAULT NULL COMMENT '赛事id',
  `season_id` int DEFAULT NULL COMMENT '赛季id',
  `stage_id` int DEFAULT NULL COMMENT '阶段id',
  `venue_id` int DEFAULT NULL COMMENT '场馆id',
  `home_team_id` int DEFAULT NULL COMMENT '主队id',
  `away_team_id` int DEFAULT NULL COMMENT '客队id',
  `match_time` int DEFAULT NULL COMMENT '比赛时间 时间戳精确到毫秒',
  `status_id` int DEFAULT NULL COMMENT '比赛状态，详见字典表nami_american_football_match_status',
  `neutral` int DEFAULT NULL COMMENT '是否中立场，1-是、0-否',
  `coverage_mlive` int DEFAULT NULL COMMENT '是否有动画，1-是、0-否',
  `scores` json DEFAULT NULL COMMENT '比分',
  `weather` json DEFAULT NULL COMMENT '天气',
  `tbd` int DEFAULT NULL COMMENT '比赛时间是否待定 1.是',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`match_id`,`rev`) USING BTREE,
  KEY `FKpfffdf4f03ydfdddeqwum` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_football_country`
--

DROP TABLE IF EXISTS `nami_football_country`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_football_country` (
  `country_id` int NOT NULL COMMENT '国家id',
  `category_id` int DEFAULT NULL COMMENT '分类id',
  `name_zh` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文名称',
  `name_zht` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语名称',
  `name_en` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `logo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '国家logo',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`country_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米足球国家列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `m_season`
--

DROP TABLE IF EXISTS `m_season`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `m_season` (
  `season_id` int NOT NULL AUTO_INCREMENT COMMENT '赛季id 自增',
  `competition_id` int NOT NULL COMMENT '赛事id',
  `year` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '赛季年',
  `sport_id` int NOT NULL COMMENT '运动项目id',
  `name_zh` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '赛季名称',
  `bd_name` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '北单全称',
  `bd_short_name` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '北单简称',
  `name_en` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `nami_id_match_status` tinyint NOT NULL DEFAULT '0' COMMENT '纳米匹配状态 0未匹配 1匹配 默认0',
  `beitai_id_match_status` tinyint NOT NULL DEFAULT '0' COMMENT '贝泰匹配状态 0未匹配 1匹配 默认0',
  `belong` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '隶属',
  `score` int DEFAULT NULL COMMENT '运营综合评分',
  `competition_level` varchar(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛事级别',
  `memo` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛事简介',
  `logo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛事logo',
  `official_web` varchar(300) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '官方网站',
  `media_web_1` varchar(300) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '媒体网站1',
  `media_web_2` varchar(300) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '媒体网站2',
  `media_web_3` varchar(300) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '媒体网站3',
  `media_web_name_1` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '媒体网站名称',
  `media_web_name_2` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '媒体网站名称2',
  `media_web_name_3` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '媒体网站名称3',
  `span` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '时间跨度',
  `time_lag` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '时差',
  `team_cnt` int DEFAULT NULL COMMENT '球队数量',
  `playoff_flag` tinyint DEFAULT NULL COMMENT '附加赛 0无 1有',
  `composition_match_cnt` json DEFAULT NULL COMMENT '比赛构成/比赛数量 字典composition 1常规赛、2冠军组、3保级组、4升降级、5升级、6欧战组、0其他',
  `competition_system` varchar(3000) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛制',
  `submit_status` int DEFAULT NULL COMMENT '提交状态 0未提交 1已提交',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账户',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账户',
  PRIMARY KEY (`season_id`) USING BTREE,
  UNIQUE KEY `uk_season` (`competition_id`,`year`) USING BTREE,
  UNIQUE KEY `uk_season_name` (`name_zh`,`sport_id`) USING BTREE,
  UNIQUE KEY `uk_bd_season` (`bd_name`,`sport_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=439 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='人工录入的赛季';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_ice_hockey_season`
--

DROP TABLE IF EXISTS `nami_ice_hockey_season`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_ice_hockey_season` (
  `season_id` int NOT NULL COMMENT '赛季id',
  `competition_id` int DEFAULT NULL COMMENT '赛事id',
  `year` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛季年份',
  `start_time` int DEFAULT NULL COMMENT '开始时间',
  `end_time` int DEFAULT NULL COMMENT '结束时间',
  `is_current` int DEFAULT NULL COMMENT '是否最新赛季，1-是、0-否',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`season_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米冰球赛季列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_football_season`
--

DROP TABLE IF EXISTS `nami_football_season`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_football_season` (
  `season_id` int NOT NULL COMMENT '赛季id',
  `competition_id` int DEFAULT NULL COMMENT '赛事id',
  `year` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛季年份',
  `start_time` bigint DEFAULT NULL COMMENT '开始时间',
  `end_time` bigint DEFAULT NULL COMMENT '结束时间',
  `is_current` int DEFAULT NULL COMMENT '是否最新赛季，1-是、0-否',
  `has_player_stats` int DEFAULT NULL COMMENT '是否有球员统计，1-是、0-否',
  `has_team_stats` int DEFAULT NULL COMMENT '是否有球队统计，1-是、0-否',
  `has_table` int DEFAULT NULL COMMENT '是否有积分榜，1-是、0-否',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`season_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米足球赛季列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_sporttery_football_match`
--

DROP TABLE IF EXISTS `audit_sporttery_football_match`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_sporttery_football_match` (
  `match_id` bigint NOT NULL COMMENT '官方比赛 ID，与足球赛程表一致',
  `s_match_id` int DEFAULT NULL COMMENT '修订时关联的标准化比赛 s_match.match_id',
  `rev` int NOT NULL COMMENT 'Envers 修订号，业务关联共享 revinfo.rev',
  `revtype` tinyint DEFAULT NULL COMMENT '操作类型：0新增、1修改、2删除',
  `match_no` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '修订时的场次编号',
  `business_date` date DEFAULT NULL COMMENT '修订时的受注业务日',
  `league_id` bigint DEFAULT NULL COMMENT '修订时的官方联赛 ID',
  `home_team_id` bigint DEFAULT NULL COMMENT '修订时的官方主队 ID',
  `away_team_id` bigint DEFAULT NULL COMMENT '修订时的官方客队 ID',
  `match_time` datetime DEFAULT NULL COMMENT '修订时的完整比赛时间',
  `sell_status` tinyint DEFAULT NULL COMMENT '修订时销售状态：1在售、2停售、3已开奖',
  `if_change` tinyint DEFAULT NULL COMMENT '修订时是否主客对调：0否、1是',
  `half_score` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '修订时的半场比分',
  `full_score` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '修订时的全场比分',
  `remark` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '修订时的官方备注',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`match_id`,`rev`) USING BTREE,
  KEY `idx_sporttery_football_match_audit_rev` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='竞彩足球赛程审计表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tx_competition`
--

DROP TABLE IF EXISTS `tx_competition`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tx_competition` (
  `competition_id` int NOT NULL COMMENT '赛事编号',
  `zone_id` int DEFAULT NULL COMMENT '洲编号',
  `zone_name` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '洲名称',
  `country_id` int DEFAULT NULL COMMENT '国家编号',
  `country_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '国家名称',
  `logo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '国家logo地址',
  `competition_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '赛事全称',
  `competition_shortname` varchar(15) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛事简称',
  `name_en` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `color` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛事颜色',
  `competition_type` int DEFAULT NULL COMMENT '赛事类别  1杯赛; 2联赛',
  `current_season` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '当前赛季',
  `startdate` bigint DEFAULT NULL COMMENT '当前赛季开始时间',
  `enddate` bigint DEFAULT NULL COMMENT '当前赛季结束时间',
  `competition_system` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛制内容',
  `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`competition_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='同行足球赛事表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_nami_basketball_stage_newgoal`
--

DROP TABLE IF EXISTS `audit_nami_basketball_stage_newgoal`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_nami_basketball_stage_newgoal` (
  `stage_id` int NOT NULL COMMENT '阶段id 实际存赛季id',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `season_id` int DEFAULT NULL COMMENT '赛季id',
  `name_zh` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文名称(存赛季名称)',
  `name_zht` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语名称',
  `name_en` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `mode` int DEFAULT NULL COMMENT '比赛模式，1-积分赛、2-淘汰赛',
  `group_count` int DEFAULT NULL COMMENT '总组数',
  `round_count` int DEFAULT NULL COMMENT '总轮数',
  `order` int DEFAULT '14' COMMENT '排序，固定14',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`stage_id`,`rev`) USING BTREE,
  KEY `FK_rev` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米篮球阶段列表(赛季数据转为阶段)';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_r_sporttery_basic_data`
--

DROP TABLE IF EXISTS `audit_r_sporttery_basic_data`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_r_sporttery_basic_data` (
  `relation_id` bigint NOT NULL AUTO_INCREMENT COMMENT '关联ID',
  `rev` int NOT NULL COMMENT 'Envers 修订号，业务关联共享 revinfo.rev',
  `revtype` tinyint DEFAULT NULL COMMENT '操作类型：0新增、1修改、2删除',
  `source_type` tinyint NOT NULL COMMENT '数据源 4=竞彩（沿用 r_basic_data 枚举空间：1纳米 2同行）',
  `sport_id` int NOT NULL COMMENT '运动项目ID',
  `sporttery_league_id` bigint NOT NULL COMMENT '竞彩联赛ID（独立ID域，足球/篮球按 sport_id 区分）',
  `manual_competition_id` int NOT NULL COMMENT '标准化赛事ID m_competition.competition_id',
  `version` bigint NOT NULL DEFAULT '0' COMMENT '匹配编辑乐观锁版本',
  `create_account` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `update_account` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`relation_id`,`rev`) USING BTREE,
  KEY `idx_audit_r_sporttery_basic_data` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='竞彩联赛与标准化赛事匹配关系审计表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `beitai_football_standing_snapshot_item`
--

DROP TABLE IF EXISTS `beitai_football_standing_snapshot_item`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `beitai_football_standing_snapshot_item` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `snapshot_id` bigint NOT NULL COMMENT '主表外键（普通索引，不建物理外键约束）',
  `season_id` bigint NOT NULL COMMENT '赛季ID（冗余）',
  `tournament_id` int NOT NULL COMMENT '贝泰赛事ID（冗余）',
  `group_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '分组名，上游为 NULL 时保留 NULL',
  `standing_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL DEFAULT 'TOTAL' COMMENT 'TOTAL/HOME/AWAY',
  `snapshot_time` bigint NOT NULL COMMENT '快照时间（冗余，毫秒）',
  `team_id` bigint NOT NULL COMMENT '球队ID',
  `team_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球队名称，上游为 NULL 时保留 NULL',
  `team_rank` int DEFAULT NULL COMMENT '排名，原 rank 因 MySQL 8 保留字改为 team_rank',
  `points` int DEFAULT NULL COMMENT '积分',
  `played` int DEFAULT NULL COMMENT '比赛场次',
  `win` int DEFAULT NULL COMMENT '胜场',
  `draw` int DEFAULT NULL COMMENT '平场',
  `loss` int DEFAULT NULL COMMENT '负场',
  `goals_for` int DEFAULT NULL COMMENT '进球',
  `goals_against` int DEFAULT NULL COMMENT '失球',
  `goal_diff` int DEFAULT NULL COMMENT '净胜球',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_beitai_item_dim_team` (`snapshot_id`,`standing_type`,`team_id`) USING BTREE,
  KEY `idx_beitai_item_team_type_time` (`team_id`,`standing_type`,`snapshot_time` DESC) USING BTREE,
  KEY `idx_beitai_item_season_type_points` (`season_id`,`standing_type`,`points` DESC) USING BTREE,
  KEY `idx_beitai_item_season_type_rank` (`season_id`,`standing_type`,`team_rank`) USING BTREE,
  KEY `idx_beitai_item_snapshot` (`snapshot_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=118923 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='贝泰足球积分榜快照明细（查询投影）';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tx_match`
--

DROP TABLE IF EXISTS `tx_match`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tx_match` (
  `match_id` int NOT NULL COMMENT '比赛编号',
  `competition_id` int NOT NULL COMMENT '赛事id',
  `home_team_id` int NOT NULL COMMENT '主队编号。',
  `away_team_id` int NOT NULL COMMENT '客队编号。',
  `match_date` bigint NOT NULL COMMENT '比赛时间 时间戳精确到毫秒',
  `season_id` bigint DEFAULT NULL COMMENT '赛季id',
  `stage_id` bigint DEFAULT NULL COMMENT '阶段id',
  `mode` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛制形式',
  `match_group` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '分组',
  `round` tinyint DEFAULT NULL COMMENT '轮次(接口中的Schedule)',
  `period` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '阶段',
  `home_team_rank` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '主队排名',
  `away_team_rank` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '客队排名',
  `neutrality` int DEFAULT NULL COMMENT '是否中立场地。',
  `note` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '备注。',
  `score` json DEFAULT NULL COMMENT '全场比分。',
  `half` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '半场比分。',
  `score_all` json DEFAULT NULL COMMENT '全场比分（含加时）。',
  `score_point` json DEFAULT NULL COMMENT '点球比分。',
  `red_card` json DEFAULT NULL COMMENT '红牌数组',
  `yellow_card` json DEFAULT NULL COMMENT '黄牌数组',
  `valid_game` int DEFAULT NULL COMMENT '比赛状态 1正常 0异常',
  `status` int DEFAULT NULL COMMENT '比赛状态值 0未开始 1上半场 2中场 3下半场 4完场 5中断 6取消 7加时 8加时 9加时 10完场 11点球大战 12全场结束 13延期 14腰斩 15待定  16金球 17未开始',
  `handicap` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '让球',
  `weather` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '天气',
  `stadium` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '比赛场地',
  `match_localtime` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '当地时间',
  `referee` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '裁判',
  `capacity` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球馆容量',
  `spectator` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '现场观众',
  `earlyodds` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '初让球',
  `channel` varchar(300) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '直播频道',
  `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`match_id`) USING BTREE,
  KEY `competition_id` (`competition_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='同行足球比赛表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `m_competition`
--

DROP TABLE IF EXISTS `m_competition`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `m_competition` (
  `competition_id` int NOT NULL AUTO_INCREMENT COMMENT '赛事id 自增',
  `sport_id` int NOT NULL COMMENT '运动项目id',
  `name_zh` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '赛事全称',
  `short_name_zh` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '赛事简称',
  `name_en` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `type` int DEFAULT NULL COMMENT '赛事类型，0-其他、1-联赛、2-杯赛、3-友谊赛',
  `jc_short_name` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '竞彩简称',
  `ctzc_short_name` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '传统足彩简称',
  `collect_match_flag` tinyint DEFAULT NULL COMMENT '是否采集赛事下全部比赛 0不采集  1采集',
  `bd_betting_flag` tinyint DEFAULT NULL COMMENT '北单竞猜赛事 0不竞猜 1竞猜',
  `nami_id_match_status` tinyint NOT NULL DEFAULT '0' COMMENT '纳米匹配状态 0未匹配 1匹配 默认0',
  `beitai_id_match_status` tinyint NOT NULL DEFAULT '0' COMMENT '贝泰匹配状态 0未匹配 1匹配 默认0',
  `default_sort_order` int DEFAULT NULL COMMENT '赛事排序序号 比赛列表按赛事显示默认排序序号,,null使用默认赛事更新时间倒序排',
  `select_sort_order` int DEFAULT NULL COMMENT '赛事筛选排序序号 比赛列表赛事简称赛事选择默认排序,,null使用默认赛事更新时间倒序排',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账户',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账户',
  PRIMARY KEY (`competition_id`) USING BTREE,
  UNIQUE KEY `uk_short_name` (`sport_id`,`short_name_zh`) USING BTREE,
  UNIQUE KEY `uk_name` (`sport_id`,`name_zh`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=219 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='人工录入的赛事';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `beitai_footbal_country`
--

DROP TABLE IF EXISTS `beitai_footbal_country`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `beitai_footbal_country` (
  `code` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '三位国家代码',
  `cn_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '中文名称',
  `en_name` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '英文名称',
  `type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '类型：国家/属地',
  PRIMARY KEY (`code`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='国家地区编码表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sporttery_football_hafu_odds_record`
--

DROP TABLE IF EXISTS `sporttery_football_hafu_odds_record`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sporttery_football_hafu_odds_record` (
  `match_id` int NOT NULL COMMENT 'Sporttery 官方比赛 ID',
  `release_time` datetime NOT NULL COMMENT '官网赔率发布时间（北京时间），由 updateDate 与 updateTime 合成',
  `win_win` decimal(6,2) DEFAULT NULL COMMENT '半场胜全场胜赔率，对应历史接口 hh',
  `win_equal` decimal(6,2) DEFAULT NULL COMMENT '半场胜全场平赔率，对应历史接口 hd',
  `win_lose` decimal(6,2) DEFAULT NULL COMMENT '半场胜全场负赔率，对应历史接口 ha',
  `equal_win` decimal(6,2) DEFAULT NULL COMMENT '半场平全场胜赔率，对应历史接口 dh',
  `equal_equal` decimal(6,2) DEFAULT NULL COMMENT '半场平全场平赔率，对应历史接口 dd',
  `equal_lose` decimal(6,2) DEFAULT NULL COMMENT '半场平全场负赔率，对应历史接口 da',
  `lose_win` decimal(6,2) DEFAULT NULL COMMENT '半场负全场胜赔率，对应历史接口 ah',
  `lose_equal` decimal(6,2) DEFAULT NULL COMMENT '半场负全场平赔率，对应历史接口 ad',
  `lose_lose` decimal(6,2) DEFAULT NULL COMMENT '半场负全场负赔率，对应历史接口 aa',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`match_id`,`release_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='竞彩足球半全场历史赔率表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `duty_schedule_template`
--

DROP TABLE IF EXISTS `duty_schedule_template`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `duty_schedule_template` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `batch_number` tinyint NOT NULL COMMENT '第几批次: 1, 2, 3, 4 (代表第一周到第四周)',
  `day_number` tinyint NOT NULL COMMENT '第几天: 1至7 (代表周一至周日)',
  `shift_type` tinyint NOT NULL COMMENT '班次: 1-白班, 2-夜班',
  `person_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '值班人员名称',
  `sort_order` tinyint NOT NULL DEFAULT '0' COMMENT '人员展示顺序: 1, 2, 3 (保证同一班次内人员上下顺序不变)',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_schedule_slot` (`batch_number`,`day_number`,`shift_type`,`sort_order`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=169 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='4周循环值班排班模板表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_ice_hockey_country`
--

DROP TABLE IF EXISTS `nami_ice_hockey_country`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_ice_hockey_country` (
  `country_id` int NOT NULL COMMENT '国家id',
  `name_zh` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文名称',
  `name_en` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `name_zht` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语名称',
  `logo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '国家logo',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`country_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米冰球国家列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tx_deleted`
--

DROP TABLE IF EXISTS `tx_deleted`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tx_deleted` (
  `deleted_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '删除的数据类型 1:category 分类，2:team 球队，4:competition 赛事，5:stage 阶段，6:season 赛季，7:venue 场馆，8:match 比赛，9:player 运动员',
  `id` int NOT NULL COMMENT '删除的数据id',
  `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`deleted_type`,`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='同行删除数据列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_basketball_stage`
--

DROP TABLE IF EXISTS `nami_basketball_stage`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_basketball_stage` (
  `stage_id` int NOT NULL COMMENT '阶段id',
  `season_id` int DEFAULT NULL COMMENT '赛季id',
  `name_zh` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文名称',
  `name_zht` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语名称',
  `name_en` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `mode` int DEFAULT NULL COMMENT '比赛模式，1-积分赛、2-淘汰赛',
  `group_count` int DEFAULT NULL COMMENT '总组数',
  `round_count` int DEFAULT NULL COMMENT '总轮数',
  `order` int DEFAULT NULL COMMENT '排序，阶段的先后顺序',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`stage_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米篮球获取阶段列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `task`
--

DROP TABLE IF EXISTS `task`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `task` (
  `task_id` int NOT NULL AUTO_INCREMENT COMMENT '任务ID',
  `event_id` varchar(11) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '事件ID',
  `task_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '任务名称，暂存s_event.identity_data.eventName的值，后续可以考虑添加更多标识信息',
  `task_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '任务类型,比赛提前 比赛推迟 比赛中断 比赛取消 比赛腰斩 球队变更 赛果争议',
  `task_role` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '任务执行角色  management赛程管理角色、monitoring赛程监控角色',
  `confirm_result` int DEFAULT NULL COMMENT '任务确认结果 0 未确认 1 已确认  2 已解除',
  `confirm_time` datetime DEFAULT NULL COMMENT '任务确认时间',
  `confirm_account` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '确认账户',
  `task_status` int DEFAULT NULL COMMENT '任务状态 0待执行 1执行中 2已完成 3已取消 4失败',
  `attribution_title` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '异常原因:天气、球员、球迷、裁判、伤病、健康、交通、政治、战争、其它、赛程、比赛设施、未知',
  `attribution_desc` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '异常描述，可存放原因更详细的信息',
  `task_detail` json DEFAULT NULL COMMENT '任务执行步骤详情，不同任务类型taskType具有不同的结构',
  `task_remark` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '任务备注 记录用户对系统、人工填写的异常事件任务',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`task_id`) USING BTREE,
  KEY `ind_event_id` (`event_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=128323 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='任务记录表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sporttery_basketball_hilo_odds`
--

DROP TABLE IF EXISTS `sporttery_basketball_hilo_odds`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sporttery_basketball_hilo_odds` (
  `match_id` int NOT NULL COMMENT 'Sporttery 官方比赛 ID，同时关联 sporttery_basketball_match.match_id',
  `collect_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '本次赔率采集时间',
  `total_score` decimal(6,2) DEFAULT NULL COMMENT '预设总分，对应接口 HILO 的 goalLine 或 goalLineValue',
  `max_odds` decimal(6,2) DEFAULT NULL COMMENT '大分赔率，对应接口 HILO 的 h',
  `min_odds` decimal(6,2) DEFAULT NULL COMMENT '小分赔率，对应接口 HILO 的 l',
  `int_single` int DEFAULT NULL COMMENT '是否允许单关：0 不允许，1 允许；没有返回时为空',
  `match_status` int DEFAULT NULL COMMENT '玩法对应比赛状态：1 开售，2 停售，3 已开奖',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`match_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='竞彩篮球大小分最新赔率表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_bd_batch_matchup`
--

DROP TABLE IF EXISTS `audit_bd_batch_matchup`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_bd_batch_matchup` (
  `batch_matchup_id` int NOT NULL COMMENT '批次比赛id',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `batch_id` int NOT NULL COMMENT '批次id',
  `sort_no` int NOT NULL COMMENT '界面展示排序序号',
  `game_draw_id` int NOT NULL COMMENT '奖期id',
  `match_id` int NOT NULL COMMENT '比赛id',
  `manual_competition_id` int NOT NULL COMMENT '人工录入的赛事',
  `manual_season_id` int NOT NULL COMMENT '人工录入的赛季',
  `matchup_unique_no` varchar(21) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '比赛唯一编号',
  `game1200_matchup_no` int DEFAULT NULL COMMENT '单场场次编号',
  `game1260_matchup_no` int DEFAULT NULL COMMENT '下半场比分场次编号',
  `game1270_matchup_no` int DEFAULT NULL COMMENT '胜负过关场次编号',
  `sport_id` int NOT NULL COMMENT '运动项目id',
  `bd_round` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '轮次',
  `match_time` datetime NOT NULL COMMENT '开赛时间',
  `home_team_id` int NOT NULL COMMENT '主队id',
  `away_team_id` int NOT NULL COMMENT '客队id',
  `team_reverse` int NOT NULL DEFAULT '0' COMMENT '主客队调换 0不调换 1调换 默认0',
  `sale_end_time` datetime DEFAULT NULL COMMENT '停售时间',
  `game1260_sale_end_time` datetime DEFAULT NULL COMMENT '下半场比分停售时间',
  `game1200_handicap` int DEFAULT NULL COMMENT '单场让球 无让球为0',
  `game1270_handicap` decimal(10,1) DEFAULT NULL COMMENT '胜负让球 无让球为0',
  `sale_game_list` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '开售的游戏列表，逗号分割 如200,210,230,240,250,260,270',
  `game1200_draw_time` datetime DEFAULT NULL COMMENT '单场开奖时间',
  `game1270_draw_time` datetime DEFAULT NULL COMMENT '胜负过关开奖时间',
  `game1260_draw_time` datetime DEFAULT NULL COMMENT '下半场比分开奖时间',
  `match_result_status` int DEFAULT NULL COMMENT '赛果确认状态  0未确认 1 已确认',
  `home_score_half` int DEFAULT NULL COMMENT '主队半场比分',
  `away_score_half` int DEFAULT NULL COMMENT '客队半场比分',
  `home_score` int DEFAULT NULL COMMENT '主队全场比分',
  `away_score` int DEFAULT NULL COMMENT '客队全场比分',
  `confirm_time` datetime DEFAULT NULL COMMENT '赛果确认时间',
  `confirm_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛果确认账户',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账号',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账号',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`batch_matchup_id`,`rev`) USING BTREE,
  KEY `FK_rev` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_american_football_venue`
--

DROP TABLE IF EXISTS `nami_american_football_venue`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_american_football_venue` (
  `venue_id` int NOT NULL COMMENT '场馆id',
  `name_zh` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文名称',
  `name_en` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `name_zht` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语名称',
  `capacity` int DEFAULT NULL COMMENT '场馆容量',
  `country_id` int DEFAULT NULL COMMENT '场馆国家归属',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`venue_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米橄榄球场馆列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_ice_hockey_deleted`
--

DROP TABLE IF EXISTS `nami_ice_hockey_deleted`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_ice_hockey_deleted` (
  `deleted_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '删除的数据类型 1:category 分类，2:team 球队，4:competition 赛事，5:stage 阶段，6:season 赛季，7:venue 场馆，8:match 比赛，9:player 运动员',
  `id` int NOT NULL COMMENT '删除的数据id',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`deleted_type`,`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米冰球删除数据列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_basketball_deleted`
--

DROP TABLE IF EXISTS `nami_basketball_deleted`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_basketball_deleted` (
  `deleted_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '删除的数据类型 1:category 分类，2:team 球队，4:competition 赛事，5:stage 阶段，6:season 赛季，7:venue 场馆，8:match 比赛，9:player 运动员',
  `id` int NOT NULL COMMENT '删除的数据id',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`deleted_type`,`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米篮球删除数据列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_football_standing_snapshot`
--

DROP TABLE IF EXISTS `nami_football_standing_snapshot`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_football_standing_snapshot` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `season_id` bigint NOT NULL COMMENT '赛季ID',
  `competition_id` int NOT NULL COMMENT '纳米赛事ID',
  `tables_id` int NOT NULL COMMENT '纳米积分榜子表ID，来源于 tables[].id',
  `stage_id` int DEFAULT NULL COMMENT '纳米阶段ID，来源于 tables[].stage_id',
  `conference` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '分区信息，来源于 tables[].conference',
  `group_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '分组值，来源于 tables[].group',
  `team_count` int NOT NULL DEFAULT '0' COMMENT '球队数量（系统计算，完整性校验用）',
  `team_data` json NOT NULL COMMENT '所有球队数据快照（事实源）',
  `snapshot_hash` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT 'team_data 的 SHA-256 哈希',
  `snapshot_time` bigint NOT NULL COMMENT '快照时间戳（毫秒）',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_nami_football_latest` (`season_id`,`competition_id`,`tables_id`,`stage_id`,`conference`,`group_name`,`snapshot_time` DESC) USING BTREE,
  KEY `idx_nami_football_stage` (`stage_id`) USING BTREE,
  KEY `idx_nami_football_openapi_update` (`competition_id`,`update_time`,`season_id`,`tables_id`,`stage_id`,`conference`,`group_name`) USING BTREE,
  KEY `idx_nami_football_dimension_hash` (`season_id`,`competition_id`,`tables_id`,`stage_id`,`conference`,`group_name`,`snapshot_hash`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=2733 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米足球积分榜变更快照（主表，JSON 事实源）';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `revinfo`
--

DROP TABLE IF EXISTS `revinfo`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `revinfo` (
  `rev` int NOT NULL AUTO_INCREMENT COMMENT '事务id',
  `revtstmp` bigint NOT NULL COMMENT '时间戳',
  PRIMARY KEY (`rev`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=2670161 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='审计表序列生成表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_bd_game_draw`
--

DROP TABLE IF EXISTS `audit_bd_game_draw`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_bd_game_draw` (
  `game_draw_id` int NOT NULL AUTO_INCREMENT COMMENT '奖期ID',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `draw_no` varchar(5) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '奖期编号 ，可为空，不能重复',
  `sale_begin_time` datetime NOT NULL COMMENT '开售时间',
  `sale_end_time` datetime NOT NULL COMMENT '停售时间',
  `draw_time` datetime NOT NULL COMMENT '开奖时间',
  `game1200` tinyint NOT NULL DEFAULT '0' COMMENT '单场竞猜 1为开售，0为不开售 默认0',
  `game1270` tinyint NOT NULL DEFAULT '0' COMMENT '胜负过关 1为开售，0为不开售 默认0',
  `game1260` tinyint NOT NULL DEFAULT '0' COMMENT '下半场比分 1为开售，0为不开售 默认0',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账号',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账号',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`game_draw_id`,`rev`) USING BTREE,
  KEY `FK_rev` (`rev`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=101 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_football_odds`
--

DROP TABLE IF EXISTS `nami_football_odds`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_football_odds` (
  `odds_id` bigint NOT NULL AUTO_INCREMENT COMMENT '赔率id 自增',
  `match_id` int NOT NULL COMMENT '比赛id',
  `company_id` int NOT NULL COMMENT '指数公司id 见字典nami_football_company_id',
  `change_time` int NOT NULL COMMENT '变化时间',
  `home_win` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '主胜',
  `draw` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '亚盘表示盘口',
  `away_win` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '客胜',
  `is_betting_closed` int DEFAULT NULL COMMENT '是否封盘：0-否，1-是',
  `fix_update_time` int DEFAULT NULL COMMENT '更新修复时间',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`odds_id`) USING BTREE,
  KEY `ind_match_id` (`match_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米足球赔率';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sporttery_football_hhad_odds_record`
--

DROP TABLE IF EXISTS `sporttery_football_hhad_odds_record`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sporttery_football_hhad_odds_record` (
  `match_id` int NOT NULL COMMENT 'Sporttery 官方比赛 ID',
  `release_time` datetime NOT NULL COMMENT '官网赔率发布时间（北京时间），由 updateDate 与 updateTime 合成',
  `win_odds` decimal(6,2) DEFAULT NULL COMMENT '让球胜赔，对应历史接口 h',
  `equal_odds` decimal(6,2) DEFAULT NULL COMMENT '让球平赔，对应历史接口 d',
  `lose_odds` decimal(6,2) DEFAULT NULL COMMENT '让球负赔，对应历史接口 a',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`match_id`,`release_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='竞彩足球让球胜平负历史赔率表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `bd_batch`
--

DROP TABLE IF EXISTS `bd_batch`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `bd_batch` (
  `batch_id` int NOT NULL AUTO_INCREMENT COMMENT '批次id 自增 主键',
  `game_draw_id` int NOT NULL COMMENT '奖期ID',
  `batch_order_no` int DEFAULT NULL COMMENT '批次序号',
  `batch_type` int DEFAULT NULL COMMENT '批次类型 0 赛程批次 1开奖批次',
  `sports_id_list` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '运动项目list 逗号分隔',
  `is_final_version` int DEFAULT NULL COMMENT '是否生成正式版 0未生成  1已生成 ',
  `preset_sale_begin_time` datetime DEFAULT NULL COMMENT '预设的批次开售时间',
  `preset_draw_time` datetime DEFAULT NULL COMMENT '预设的批次开奖时间',
  `draw_game_id_list` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '批次开奖的游戏，逗号分隔，如200,210,230,240,250,260,270',
  `batch_sale_status` int DEFAULT NULL COMMENT '是否开售 0未开售 1开售',
  `submit_status` int DEFAULT NULL COMMENT '提交状态 0未提交 1已提交',
  `batch_draw_status` int DEFAULT NULL COMMENT '是否开奖 0未开奖 1已开奖',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账号',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账号',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`batch_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=1360 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='北单批次表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sporttery_football_hafu_odds`
--

DROP TABLE IF EXISTS `sporttery_football_hafu_odds`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sporttery_football_hafu_odds` (
  `match_id` int NOT NULL COMMENT 'Sporttery 官方比赛 ID，同时关联 sporttery_football_match.match_id',
  `collect_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '本次赔率采集时间',
  `win_win` decimal(6,2) DEFAULT NULL COMMENT '半场胜、全场胜赔率，对应接口 hh',
  `win_equal` decimal(6,2) DEFAULT NULL COMMENT '半场胜、全场平赔率，对应接口 hd',
  `win_lose` decimal(6,2) DEFAULT NULL COMMENT '半场胜、全场负赔率，对应接口 ha',
  `equal_win` decimal(6,2) DEFAULT NULL COMMENT '半场平、全场胜赔率，对应接口 dh',
  `equal_equal` decimal(6,2) DEFAULT NULL COMMENT '半场平、全场平赔率，对应接口 dd',
  `equal_lose` decimal(6,2) DEFAULT NULL COMMENT '半场平、全场负赔率，对应接口 da',
  `lose_win` decimal(6,2) DEFAULT NULL COMMENT '半场负、全场胜赔率，对应接口 ah',
  `lose_equal` decimal(6,2) DEFAULT NULL COMMENT '半场负、全场平赔率，对应接口 ad',
  `lose_lose` decimal(6,2) DEFAULT NULL COMMENT '半场负、全场负赔率，对应接口 aa',
  `int_single` int DEFAULT NULL COMMENT '是否允许单关：0 不允许，1 允许；没有返回时为空',
  `match_status` int DEFAULT NULL COMMENT '玩法对应比赛状态：1 开售，2 停售，3 已开奖',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`match_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='竞彩足球半全场最新赔率表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tx_team`
--

DROP TABLE IF EXISTS `tx_team`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tx_team` (
  `team_id` int NOT NULL COMMENT '球队编号(SDT编号)',
  `team_name` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '球队名称',
  `name_en` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `short_name` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球队简称',
  `establish_date` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '成立日期',
  `capacity` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球场容量',
  `website` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '官网',
  `email` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '邮件地址',
  `country` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '国家地区',
  `address` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球队地址',
  `city` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '所在城市',
  `stadium` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球场名称',
  `profile` varchar(4500) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球队简介',
  `best` varchar(3000) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球队之最',
  `glory` varchar(1500) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球队荣誉',
  `player_age_avg` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球员平均年龄',
  `photo` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球队图标',
  `team_price` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球队身价',
  `team_price_currency` int DEFAULT NULL COMMENT '身价单位。1欧元；2美元；3英镑；4人民币',
  `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`team_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='同行球队表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_nami_basketball_match`
--

DROP TABLE IF EXISTS `audit_nami_basketball_match`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_nami_basketball_match` (
  `match_id` int NOT NULL COMMENT '比赛id',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `competition_id` int DEFAULT NULL COMMENT '赛事id',
  `home_team_id` int DEFAULT NULL COMMENT '主队id',
  `away_team_id` int DEFAULT NULL COMMENT '客队id',
  `kind` int DEFAULT NULL COMMENT '类型id，1-常规赛、2-季后赛、3-季前赛、4-全明星、5-杯赛、6-附加赛、0-无',
  `round_stage_id` int DEFAULT NULL COMMENT '存nami_basketball_stage_newgoal.season_id',
  `period_count` int DEFAULT NULL COMMENT '比赛总节数(不包含加时)',
  `status_id` int DEFAULT NULL COMMENT '比赛状态，详见状态码->比赛状态',
  `match_time` bigint DEFAULT NULL COMMENT '比赛时间 时间戳精确到秒',
  `neutral` int DEFAULT NULL COMMENT '是否中立场，1-是、0-否',
  `home_scores` json DEFAULT NULL COMMENT '主队比分字段list',
  `away_scores` json DEFAULT NULL COMMENT '客队比分字段list',
  `over_time_scores` json DEFAULT NULL COMMENT '加时赛比分字段说明',
  `home_position` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '主队排名',
  `away_position` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '客队排名',
  `coverage` json DEFAULT NULL COMMENT '动画、情报、阵容 字段',
  `venue_id` int DEFAULT NULL COMMENT '场馆id',
  `season_id` int DEFAULT NULL COMMENT '赛季id',
  `round` json DEFAULT NULL COMMENT '关联信息',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`match_id`,`rev`) USING BTREE,
  KEY `FK_rev` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米篮球比赛列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sport_radar_prematch_european_odds`
--

DROP TABLE IF EXISTS `sport_radar_prematch_european_odds`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sport_radar_prematch_european_odds` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `sport_event_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '比赛数字ID',
  `market_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '盘口ID',
  `market_name` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '盘口名称',
  `book_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '博彩公司ID',
  `book_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '博彩公司名称',
  `home_odds_american` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '主胜美式赔率',
  `home_odds_decimal` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '主胜小数赔率',
  `draw_odds_american` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '平局美式赔率',
  `draw_odds_decimal` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '平局小数赔率',
  `away_odds_american` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '客胜美式赔率',
  `away_odds_decimal` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '客胜小数赔率',
  `collected_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '赔率采集时间',
  `create_time` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '记录创建时间',
  `update_time` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '记录更新时间',
  `initial_home_odds_american` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT 'Sportradar官方初盘主胜美式赔率',
  `initial_home_odds_decimal` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT 'Sportradar官方初盘主胜小数赔率',
  `initial_draw_odds_american` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT 'Sportradar官方初盘平局美式赔率',
  `initial_draw_odds_decimal` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT 'Sportradar官方初盘平局小数赔率',
  `initial_away_odds_american` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT 'Sportradar官方初盘客胜美式赔率',
  `initial_away_odds_decimal` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT 'Sportradar官方初盘客胜小数赔率',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_sr_euro_event_book` (`sport_event_id`,`market_id`,`book_id`,`collected_at`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=2958005 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Sportradar欧盘胜平负赔率变更快照';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `beitai_football_period`
--

DROP TABLE IF EXISTS `beitai_football_period`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `beitai_football_period` (
  `id` int NOT NULL COMMENT '阶段ID',
  `match_id` bigint NOT NULL COMMENT '比赛ID',
  `number` int DEFAULT NULL COMMENT '阶段编号',
  `home_score` int DEFAULT NULL COMMENT '主队得分',
  `away_score` int DEFAULT NULL COMMENT '客队得分',
  `type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '比赛阶段类型：regular_period/overtime/penalties',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='雷达比赛阶段表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_basketball_category`
--

DROP TABLE IF EXISTS `nami_basketball_category`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_basketball_category` (
  `category_id` int NOT NULL COMMENT '分类id',
  `name_zh` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文名称',
  `name_zht` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语名称',
  `name_en` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`category_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米篮球分类列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `toto_role`
--

DROP TABLE IF EXISTS `toto_role`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `toto_role` (
  `role_id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '角色ID 自增',
  `role_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '角色名称',
  `role_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '角色描述',
  `role_type` tinyint NOT NULL COMMENT '角色分类：0 三员角色、1 普通角色',
  `system_id` int NOT NULL COMMENT '系统 ID',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账号',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账号',
  `is_deleted` tinyint NOT NULL DEFAULT '0' COMMENT '删除状态 0 未删除 1删除 默认0',
  PRIMARY KEY (`role_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=54 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='角色';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_tx_season`
--

DROP TABLE IF EXISTS `audit_tx_season`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_tx_season` (
  `season_id` bigint NOT NULL COMMENT '赛季id',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `competition_id` int NOT NULL COMMENT '赛事id',
  `year` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '赛季年 示例：2024-2025',
  `start_time` datetime DEFAULT NULL COMMENT '开始时间',
  `end_time` datetime DEFAULT NULL COMMENT '结束时间',
  `is_current` int NOT NULL COMMENT '是否当前赛季 0否  1是',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`season_id`,`rev`) USING BTREE,
  KEY `FK_rev` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin ROW_FORMAT=DYNAMIC COMMENT='同行赛季表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_ice_hockey_team`
--

DROP TABLE IF EXISTS `nami_ice_hockey_team`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_ice_hockey_team` (
  `team_id` int NOT NULL COMMENT '球队id',
  `name_zh` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文名称',
  `name_en` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `name_zht` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语名称',
  `short_name_zh` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文简称',
  `short_name_en` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文简称',
  `short_name_zht` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语简称',
  `abbr` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '缩写',
  `suffix` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '后缀',
  `logo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT 'logo',
  `gender` int DEFAULT NULL COMMENT '性别，1-男、2-女、0-未知',
  `national` int DEFAULT NULL COMMENT '是否国家队，0-否、1-是',
  `is_virtual` int DEFAULT NULL COMMENT '是否占位球队 1是0否',
  `uid` int DEFAULT NULL COMMENT '纳米球队合并对应ID',
  `coach_ids` json DEFAULT NULL COMMENT '教练ID数组JSON串',
  `country_id` int DEFAULT NULL COMMENT '纳米国家ID，关联 nami_ice_hockey_country.country_id',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`team_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米冰球球队列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sport_radar_prematch_changelog_record`
--

DROP TABLE IF EXISTS `sport_radar_prematch_changelog_record`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sport_radar_prematch_changelog_record` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `generated_at` datetime DEFAULT NULL COMMENT '雷达响应生成时间，北京时间',
  `fetched_at` datetime NOT NULL COMMENT '本系统抓取时间，北京时间',
  `response_body` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '雷达返回的完整原始JSON',
  `create_time` datetime NOT NULL COMMENT '记录创建时间，北京时间',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_fetched_at` (`fetched_at`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=2733 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Sportradar赛前赔率Changelog临时记录';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `r_basic_data`
--

DROP TABLE IF EXISTS `r_basic_data`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `r_basic_data` (
  `relation_id` int NOT NULL AUTO_INCREMENT COMMENT '匹配id  自增 唯一',
  `source_type` int NOT NULL COMMENT '数据源 1纳米 2同行',
  `sport_id` int NOT NULL COMMENT '运动项目id',
  `manual_competition_id` int NOT NULL COMMENT '人工录入的赛事id',
  `manual_season_id` int DEFAULT NULL COMMENT '人工录入的赛季id',
  `source_competition_id` int NOT NULL COMMENT '匹配的数据源赛事id',
  `source_season_id` bigint DEFAULT NULL COMMENT '匹配的数据源赛季id',
  `nami_competition_id` int DEFAULT NULL COMMENT '纳米赛事id，数据源为同行时匹配',
  `stage_group` json DEFAULT NULL COMMENT '数据源阶段轮次分组信息',
  `relation_status` tinyint NOT NULL COMMENT '0 未匹配 1 赛事匹配  2赛事和赛季匹配  3不进行匹配',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账户',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账户',
  PRIMARY KEY (`relation_id`) USING BTREE,
  UNIQUE KEY `uk_basic_data` (`manual_competition_id`,`manual_season_id`,`source_competition_id`,`source_season_id`,`source_type`,`sport_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=1188 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='赛事赛事阶段匹配表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sporttery_basketball_hdc_odds`
--

DROP TABLE IF EXISTS `sporttery_basketball_hdc_odds`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sporttery_basketball_hdc_odds` (
  `match_id` int NOT NULL COMMENT 'Sporttery 官方比赛 ID，同时关联 sporttery_basketball_match.match_id',
  `collect_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '本次赔率采集时间',
  `host_lose_odds` decimal(6,2) DEFAULT NULL COMMENT '让分主负赔率，对应接口 HDC 的 a',
  `host_win_odds` decimal(6,2) DEFAULT NULL COMMENT '让分主胜赔率，对应接口 HDC 的 h',
  `int_single` int DEFAULT NULL COMMENT '是否允许单关：0 不允许，1 允许；没有返回时为空',
  `match_status` int DEFAULT NULL COMMENT '玩法对应比赛状态：1 开售，2 停售，3 已开奖',
  `handicap` decimal(3,1) DEFAULT NULL COMMENT '让分数，对应接口 HDC 的 goalLine 或 goalLineValue',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`match_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='竞彩篮球让分胜负最新赔率表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_football_competition`
--

DROP TABLE IF EXISTS `nami_football_competition`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_football_competition` (
  `competition_id` int NOT NULL COMMENT '赛事id',
  `category_id` int DEFAULT NULL COMMENT '分类id',
  `country_id` int DEFAULT NULL COMMENT '国家id',
  `name_zh` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文名称',
  `name_zht` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语名称',
  `name_en` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `short_name_zh` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文简称',
  `short_name_zht` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语简称',
  `short_name_en` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文简称',
  `logo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛事logo',
  `type` int DEFAULT NULL COMMENT '赛事类型，0-未知、1-联赛、2-杯赛、3-友谊赛',
  `title_holder` json DEFAULT NULL COMMENT '卫冕冠军',
  `most_titles` json DEFAULT NULL COMMENT '夺冠最多球队列表',
  `newcomers` json DEFAULT NULL COMMENT '晋级淘汰球队低级赛事升级球队球队id列表',
  `divisions` json DEFAULT NULL COMMENT '赛事层级高一级赛事id列表',
  `host` json DEFAULT NULL COMMENT '东道主国家',
  `primary_color` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '主颜色',
  `secondary_color` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '次颜色',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`competition_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米足球赛事列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_football_table_live`
--

DROP TABLE IF EXISTS `nami_football_table_live`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_football_table_live` (
  `season_id` int NOT NULL COMMENT '赛季id',
  `competition_id` int NOT NULL COMMENT '赛事id',
  `team_id` int NOT NULL COMMENT '球队id',
  `updated_at` bigint NOT NULL COMMENT '更新时间',
  `promotions_name_zh` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '升降级中文名',
  `tables_id` int DEFAULT NULL COMMENT '积分榜id',
  `conference` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '分区信息',
  `group` int DEFAULT NULL COMMENT '不为0表示分组赛的第几组，1-A、2-B以此类推',
  `stage_id` int DEFAULT NULL COMMENT '所属阶段id',
  `promotion_id` int DEFAULT NULL COMMENT '升降级id',
  `points` int DEFAULT NULL COMMENT '积分',
  `position` int DEFAULT NULL COMMENT '排名',
  `deduct_points` int DEFAULT NULL COMMENT '扣除积分',
  `note` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '说明',
  `total` int DEFAULT NULL COMMENT '比赛场次',
  `won` int DEFAULT NULL COMMENT '胜的场次',
  `draw` int DEFAULT NULL COMMENT '平的场次',
  `loss` int DEFAULT NULL COMMENT '负的场次',
  `goals` int DEFAULT NULL COMMENT '进球',
  `goals_against` int DEFAULT NULL COMMENT '失球',
  `goal_diff` int DEFAULT NULL COMMENT '净胜球',
  `home_points` int DEFAULT NULL COMMENT '主场积分',
  `home_position` int DEFAULT NULL COMMENT '主场排名',
  `home_total` int DEFAULT NULL COMMENT '主场比赛场次',
  `home_won` int DEFAULT NULL COMMENT '主场胜的场次',
  `home_draw` int DEFAULT NULL COMMENT '主场平的场次',
  `home_loss` int DEFAULT NULL COMMENT '主场负的场次',
  `home_goals` int DEFAULT NULL COMMENT '主场进球',
  `home_goals_against` int DEFAULT NULL COMMENT '主场失球',
  `home_goal_diff` int DEFAULT NULL COMMENT '主场净胜球',
  `away_points` int DEFAULT NULL COMMENT '客场积分',
  `away_position` int DEFAULT NULL COMMENT '客场排名',
  `away_total` int DEFAULT NULL COMMENT '客场比赛场次',
  `away_won` int DEFAULT NULL COMMENT '客场胜的场次',
  `away_draw` int DEFAULT NULL COMMENT '客场平的场次',
  `away_loss` int DEFAULT NULL COMMENT '客场负的场次',
  `away_goals` int DEFAULT NULL COMMENT '客场进球',
  `away_goals_against` int DEFAULT NULL COMMENT '客场失球',
  `away_goal_diff` int DEFAULT NULL COMMENT '客场净胜球',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`season_id`,`team_id`,`updated_at`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin ROW_FORMAT=DYNAMIC COMMENT=' 纳米足球实时积分榜';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tx_season`
--

DROP TABLE IF EXISTS `tx_season`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tx_season` (
  `season_id` bigint NOT NULL COMMENT '赛季id',
  `competition_id` int NOT NULL COMMENT '赛事id',
  `year` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '赛季年 示例：2024-2025',
  `start_time` datetime DEFAULT NULL COMMENT '开始时间',
  `end_time` datetime DEFAULT NULL COMMENT '结束时间',
  `is_current` int NOT NULL COMMENT '是否当前赛季 0否  1是',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`season_id`) USING BTREE,
  UNIQUE KEY `uk_season` (`competition_id`,`year`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='同行赛季表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sporttery_football_team`
--

DROP TABLE IF EXISTS `sporttery_football_team`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sporttery_football_team` (
  `team_id` bigint NOT NULL COMMENT '官方球队ID',
  `team_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球队简称',
  `team_full_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球队全称',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`team_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='竞彩足球球队表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `toto_dict`
--

DROP TABLE IF EXISTS `toto_dict`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `toto_dict` (
  `dict_key` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '字典键。',
  `dict_value` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '字典值。',
  `dict_desc` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '字典描述。',
  PRIMARY KEY (`dict_key`,`dict_value`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='字典表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_nami_football_stage`
--

DROP TABLE IF EXISTS `audit_nami_football_stage`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_nami_football_stage` (
  `stage_id` int NOT NULL COMMENT '阶段id',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `season_id` int DEFAULT NULL COMMENT '赛季id',
  `name_zh` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文名称',
  `name_zht` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语名称',
  `name_en` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `mode` int DEFAULT NULL COMMENT '比赛模式，1-积分赛、2-淘汰赛',
  `group_count` int DEFAULT NULL COMMENT '总组数',
  `round_count` int DEFAULT NULL COMMENT '总轮数',
  `stage_order` int DEFAULT NULL COMMENT '排序，阶段的先后顺序',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`stage_id`,`rev`) USING BTREE,
  KEY `FK_rev` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin ROW_FORMAT=DYNAMIC COMMENT='纳米足球获取阶段列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_basketball_season`
--

DROP TABLE IF EXISTS `nami_basketball_season`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_basketball_season` (
  `season_id` int NOT NULL COMMENT '赛季id',
  `competition_id` int DEFAULT NULL COMMENT '赛事id',
  `year` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛季年份',
  `is_current` int DEFAULT NULL COMMENT '是否最新赛季，1-是、0-否',
  `has_player_stats` int DEFAULT NULL COMMENT '是否有球员统计，1-是、0-否',
  `has_team_stats` int DEFAULT NULL COMMENT '是否有球队统计，1-是、0-否',
  `has_table` int DEFAULT NULL COMMENT '是否有积分榜，1-是、0-否',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`season_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米篮球赛季列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `r_team_data`
--

DROP TABLE IF EXISTS `r_team_data`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `r_team_data` (
  `relation_id` int NOT NULL AUTO_INCREMENT COMMENT '匹配id  自增 唯一',
  `sport_id` int NOT NULL COMMENT '运动项目id',
  `manual_team_id` int NOT NULL COMMENT '人工录入数据的球队id 暂和m_team_id一致',
  `standard_team_id` int NOT NULL COMMENT '标准化球队id',
  `source_type` tinyint NOT NULL COMMENT '数据源 1纳米 2同行 3贝泰',
  `source_team_id` int NOT NULL COMMENT '数据源球队id',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账户',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账户',
  PRIMARY KEY (`relation_id`) USING BTREE,
  UNIQUE KEY `uk_r_team` (`sport_id`,`manual_team_id`,`source_type`,`source_team_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=12045 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='球队数据匹配关系表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_ice_hockey_match`
--

DROP TABLE IF EXISTS `nami_ice_hockey_match`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_ice_hockey_match` (
  `match_id` int NOT NULL COMMENT '比赛id',
  `competition_id` int DEFAULT NULL COMMENT '赛事id',
  `season_id` int DEFAULT NULL COMMENT '赛季id',
  `stage_id` int DEFAULT NULL COMMENT '阶段id',
  `venue_id` int DEFAULT NULL COMMENT '场馆id',
  `home_team_id` int DEFAULT NULL COMMENT '主队id',
  `away_team_id` int DEFAULT NULL COMMENT '客队id',
  `match_time` int DEFAULT NULL COMMENT '比赛时间 时间戳精确到毫秒',
  `status_id` int DEFAULT NULL COMMENT '比赛状态 见字典ice_hockey_match_status',
  `neutral` int DEFAULT NULL COMMENT '是否中立场，1-是、0-否',
  `coverage_mlive` int DEFAULT NULL COMMENT '动画字段 是否有动画，1-是、0-否',
  `scores` json DEFAULT NULL COMMENT '比分数据 ft - 常规比分; p* - 局比分(* - 局数，1、2、3...);ot - 加时赛比分(包含ft) ; ap - 点球比分(包含ft、ot)',
  `tbd` int DEFAULT NULL COMMENT '比赛时间是否待定 1.是',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`match_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米冰球比赛列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tx_stage`
--

DROP TABLE IF EXISTS `tx_stage`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tx_stage` (
  `stage_id` bigint NOT NULL AUTO_INCREMENT COMMENT '阶段id',
  `season_id` bigint DEFAULT NULL COMMENT '赛季id',
  `competition_id` int DEFAULT NULL COMMENT '赛事ID',
  `name_zh` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '阶段名称',
  `stage_order` int DEFAULT NULL COMMENT '排序，阶段的先后顺序',
  `error_detail` json DEFAULT NULL COMMENT '异常信息',
  `first_match_time` datetime DEFAULT NULL COMMENT '阶段中第一场比赛的比赛时间',
  `last_match_time` datetime DEFAULT NULL COMMENT '阶段中最后一场比赛的比赛时间',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`stage_id`) USING BTREE,
  UNIQUE KEY `uk_tx_stage` (`season_id`,`name_zh`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=9006447646976265 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='同行阶段表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_r_basic_data`
--

DROP TABLE IF EXISTS `audit_r_basic_data`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_r_basic_data` (
  `relation_id` int NOT NULL COMMENT '匹配id',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `source_type` int NOT NULL COMMENT '数据源 1纳米 2同行',
  `sport_id` int NOT NULL COMMENT '运动项目id',
  `manual_competition_id` int NOT NULL COMMENT '人工录入的赛事id',
  `manual_season_id` int DEFAULT NULL COMMENT '人工录入的赛季id',
  `source_competition_id` int NOT NULL COMMENT '匹配的数据源赛事id',
  `source_season_id` bigint DEFAULT NULL COMMENT '匹配的数据源赛季id',
  `nami_competition_id` int DEFAULT NULL COMMENT '纳米赛事id，数据源为同行时匹配',
  `stage_group` json DEFAULT NULL COMMENT '数据源阶段轮次分组信息',
  `relation_status` tinyint NOT NULL COMMENT '0 未匹配 1 赛事匹配  2赛事和赛季匹配  3不进行匹配',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账户',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账户',
  PRIMARY KEY (`relation_id`,`rev`) USING BTREE,
  KEY `FK_rev` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `toto_account`
--

DROP TABLE IF EXISTS `toto_account`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `toto_account` (
  `account_id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '账号ID',
  `account` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '用户账号  登录填的用户名 要求唯一',
  `account_user` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '用户的真实姓名,可重复',
  `password` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '密码 符合密码复杂度要求',
  `rdc_id` int NOT NULL COMMENT '所属中心ID',
  `last_password_change_time` datetime DEFAULT NULL COMMENT '最后一次密码修改时间 大于90天强制改密码',
  `account_type` tinyint NOT NULL COMMENT '分类：0 管理用户 、1 普通用户',
  `account_status` tinyint NOT NULL DEFAULT '1' COMMENT '账号状态 0停用 1启用 默认1',
  `account_status_changed_reason` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '账号启停状态account_status变化原因',
  `two_factor_bind_status` tinyint NOT NULL DEFAULT '0' COMMENT '双因子认证设备绑定状态 0未绑定 1已绑定，默认0',
  `token_id` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '令牌ID为随机生成的UUID的字符串',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账号',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账号',
  `is_deleted` tinyint NOT NULL DEFAULT '0' COMMENT '删除状态 0 未删除 1删除 默认0',
  PRIMARY KEY (`account_id`) USING BTREE,
  KEY `uk_account` (`account`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=134 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='账号';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_ice_hockey_venue`
--

DROP TABLE IF EXISTS `nami_ice_hockey_venue`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_ice_hockey_venue` (
  `venue_id` int NOT NULL COMMENT '场馆id',
  `name_zh` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文名称',
  `name_en` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `name_zht` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语名称',
  `capacity` int DEFAULT NULL COMMENT '场馆容量',
  `country_id` int DEFAULT NULL COMMENT '场馆国家归属',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`venue_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米冰球场馆列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sporttery_football_match`
--

DROP TABLE IF EXISTS `sporttery_football_match`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sporttery_football_match` (
  `match_id` bigint NOT NULL COMMENT '官方比赛ID',
  `s_match_id` int DEFAULT NULL COMMENT '关联标准化比赛 s_match.match_id',
  `match_no` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '场次编号，如周二301',
  `business_date` date DEFAULT NULL COMMENT '受注业务日',
  `league_id` bigint DEFAULT NULL COMMENT '联赛ID',
  `home_team_id` bigint DEFAULT NULL COMMENT '主队ID',
  `away_team_id` bigint DEFAULT NULL COMMENT '客队ID',
  `match_time` datetime DEFAULT NULL COMMENT '比赛时间（官方 matchDate + matchTime）',
  `sell_status` tinyint DEFAULT NULL COMMENT '销售状态：1在售/2停售/3已开奖',
  `if_change` tinyint DEFAULT NULL COMMENT '是否主客对调，来源确认后再映射',
  `half_score` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '半场比分',
  `full_score` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '全场比分',
  `remark` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '官方备注',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`match_id`) USING BTREE,
  KEY `idx_league_id` (`league_id`) USING BTREE,
  KEY `idx_business_date` (`business_date`) USING BTREE,
  KEY `idx_sell_status` (`sell_status`) USING BTREE,
  KEY `idx_sptty_fb_smatch` (`s_match_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='竞彩足球赛程表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sporttery_football_ttg_odds_record`
--

DROP TABLE IF EXISTS `sporttery_football_ttg_odds_record`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sporttery_football_ttg_odds_record` (
  `match_id` int NOT NULL COMMENT 'Sporttery 官方比赛 ID',
  `release_time` datetime NOT NULL COMMENT '官网赔率发布时间（北京时间），由 updateDate 与 updateTime 合成',
  `zero` decimal(6,2) DEFAULT NULL COMMENT '0 球赔率，对应历史接口 s0',
  `one` decimal(6,2) DEFAULT NULL COMMENT '1 球赔率，对应历史接口 s1',
  `two` decimal(6,2) DEFAULT NULL COMMENT '2 球赔率，对应历史接口 s2',
  `three` decimal(6,2) DEFAULT NULL COMMENT '3 球赔率，对应历史接口 s3',
  `four` decimal(6,2) DEFAULT NULL COMMENT '4 球赔率，对应历史接口 s4',
  `five` decimal(6,2) DEFAULT NULL COMMENT '5 球赔率，对应历史接口 s5',
  `six` decimal(6,2) DEFAULT NULL COMMENT '6 球赔率，对应历史接口 s6',
  `seven` decimal(6,2) DEFAULT NULL COMMENT '7+ 球赔率，对应历史接口 s7',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`match_id`,`release_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='竞彩足球总进球历史赔率表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `bd_batch_diff_record`
--

DROP TABLE IF EXISTS `bd_batch_diff_record`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `bd_batch_diff_record` (
  `game_draw_id` int NOT NULL COMMENT '奖期id',
  `batch_id` int NOT NULL COMMENT '批次id',
  `diff_status` tinyint NOT NULL COMMENT '0进行中 1比对完成 2比对取消',
  `diff_base_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '比对的基准用户',
  `diff_target_account_list` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '比对用户列表,逗号分隔',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账号',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账号',
  PRIMARY KEY (`game_draw_id`,`batch_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='北单批次对比记录表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sporttery_task`
--

DROP TABLE IF EXISTS `sporttery_task`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sporttery_task` (
  `task_id` int NOT NULL AUTO_INCREMENT COMMENT '任务ID',
  `event_id` varchar(11) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '事件id',
  `task_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '任务名称，暂存sporttery_match_event.event_name（identity_data.eventName）',
  `task_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '任务类型：比赛提前 比赛推迟 比赛中断 比赛取消 比赛腰斩 球队变更',
  `task_role` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '任务执行角色 management赛程管理角色、monitoring赛程监控角色',
  `confirm_result` int DEFAULT NULL COMMENT '任务确认结果 0未确认 1已确认 2已解除',
  `confirm_time` datetime DEFAULT NULL COMMENT '任务确认时间',
  `confirm_account` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '确认账户',
  `task_status` int DEFAULT NULL COMMENT '任务状态 0待执行 1执行中 2已完成 3已取消 4失败',
  `attribution_title` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '异常原因:天气、球员、球迷、裁判、伤病、健康、交通、政治、战争、其它、赛程、比赛设施、未知',
  `attribution_desc` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '异常描述，可存放原因更详细的信息',
  `task_detail` json DEFAULT NULL COMMENT '任务执行步骤详情，不同任务类型taskType具有不同的结构',
  `task_remark` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '任务备注 记录用户对系统、人工填写的异常事件任务',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`task_id`) USING BTREE,
  KEY `ind_event_id` (`event_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='竞彩异常事件任务表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `toto_role_permission`
--

DROP TABLE IF EXISTS `toto_role_permission`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `toto_role_permission` (
  `role_permission_id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '关系 ID 自增',
  `role_id` int NOT NULL COMMENT '角色 ID',
  `permission_id` int NOT NULL COMMENT '权限 ID',
  `system_id` int NOT NULL COMMENT '系统 ID',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账号',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账号',
  PRIMARY KEY (`role_permission_id`) USING BTREE,
  UNIQUE KEY `uk_toto_role_permission` (`role_id`,`permission_id`,`system_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=3715 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='角色权限权限关系表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_m_competition_blacklist`
--

DROP TABLE IF EXISTS `audit_m_competition_blacklist`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_m_competition_blacklist` (
  `competition_blacklist_id` int NOT NULL COMMENT '赛事黑名单ID',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `manual_competition_id` int NOT NULL COMMENT '人工录入的赛事id',
  `reason` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '添加原因',
  `del_reason` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '移除原因',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账号',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账号',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`competition_blacklist_id`,`rev`) USING BTREE,
  KEY `FK_rev` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sporttery_basketball_team`
--

DROP TABLE IF EXISTS `sporttery_basketball_team`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sporttery_basketball_team` (
  `team_id` bigint NOT NULL COMMENT '官方球队ID',
  `team_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球队简称',
  `team_full_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球队全称',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`team_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='竞彩篮球球队表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `s_match`
--

DROP TABLE IF EXISTS `s_match`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `s_match` (
  `match_id` int NOT NULL AUTO_INCREMENT COMMENT '比赛id',
  `sport_id` int DEFAULT NULL COMMENT '运动项目id',
  `season_id` int DEFAULT NULL COMMENT '赛季id',
  `competition_id` int DEFAULT NULL COMMENT '赛事id',
  `matchup_unique_no` json DEFAULT NULL COMMENT '北单比赛唯一编号',
  `beitai_match_id` int DEFAULT NULL COMMENT '贝泰比赛id',
  `nami_match_id` int DEFAULT NULL COMMENT '纳米比赛id',
  `tx_match_id` int DEFAULT NULL COMMENT '同行比赛id',
  `manual_match_id` int DEFAULT NULL COMMENT '人工录入的比赛编号',
  `home_team_id` int DEFAULT NULL COMMENT '主队id',
  `away_team_id` int DEFAULT NULL COMMENT '客队id',
  `match_round` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '轮次',
  `match_stage` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '阶段',
  `match_group` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '分组',
  `status_id` int DEFAULT NULL COMMENT '比赛状态 \r\n1000未开赛(未入稿)\r\n1100比赛中(未入稿)\r\n1200完场(未入稿)\r\n1300推迟(未入稿)\r\n1400中断(未入稿)\r\n1500腰斩(未入稿)\r\n1600取消（未入稿）\r\n1700待定\r\n1001未开赛(已入稿)\r\n1002未开赛(赛程已提交)\r\n1003未开赛(已开售)\r\n1101比赛中(已入稿)\r\n1102比赛中(赛程已提交)\r\n1103比赛中(已开售)\r\n1201完场(已入稿)\r\n1202完场(赛程已提交)\r\n1203完场(已开售)\r\n1205完场(赛果已提交)\r\n1206完场(已开奖)\r\n1301推迟(已入稿)\r\n1302推迟(赛程已提交)\r\n1303推迟(已开售)\r\n1305推迟(赛果已提交)\r\n1306推迟(已开奖)\r\n1401中断(已入稿)\r\n1402中断(赛程已提交)\r\n1403中断(已开售)\r\n1405中断(赛果已提交)\r\n1406中断(已开奖)\r\n1501腰斩(已入稿)\r\n1502腰斩(赛程已提交)\r\n1503腰斩(已开售)\r\n1505腰斩(赛果已提交)\r\n1506腰斩(已开奖)\r\n1601取消(已入稿)\r\n1602取消(赛程已提交)\r\n1603取消(已开售)\r\n1605取消(赛果已提交)\r\n1606取消(已开奖)\r\n',
  `match_time` datetime DEFAULT NULL COMMENT '比赛时间',
  `home_score_half` int DEFAULT NULL COMMENT '主队半场比分',
  `away_score_half` int DEFAULT NULL COMMENT '客队半场比分',
  `home_score` int DEFAULT NULL COMMENT '主队比分',
  `away_score` int DEFAULT NULL COMMENT '客队比分',
  `home_score_all` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '使用源数据json，半场，全场，加时，点球',
  `away_score_all` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '使用源数据json，半场，全场，加时，点球',
  `home_position` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '主队排名',
  `away_position` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '客队排名',
  `venue_id` int DEFAULT NULL COMMENT '场馆id',
  `weather` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '天气',
  `bd_matchup_home_team_id` int DEFAULT NULL COMMENT '北单赛程的比赛的主队id',
  `replace_id` int DEFAULT NULL COMMENT '在旧的比赛记录上关联新比赛ID，如果比赛上有新的比赛ID，则不需要再进行数据更新',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建用户',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新用户',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`match_id`) USING BTREE,
  KEY `ind_tx_match_id` (`tx_match_id`) USING BTREE,
  KEY `ind_manual_match_id` (`manual_match_id`) USING BTREE,
  KEY `ind_nami_match_id` (`nami_match_id`) USING BTREE,
  KEY `ind_status_id` (`status_id`) USING BTREE,
  KEY `ind_update_time` (`update_time`) USING BTREE,
  KEY `ind_match_time` (`match_time`) USING BTREE,
  KEY `ind_replace_id` (`replace_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=116326 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='标准化-比赛';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_nami_basketball_season`
--

DROP TABLE IF EXISTS `audit_nami_basketball_season`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_nami_basketball_season` (
  `season_id` int NOT NULL COMMENT '赛季id',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `competition_id` int DEFAULT NULL COMMENT '赛事id',
  `year` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛季年份',
  `is_current` int DEFAULT NULL COMMENT '是否最新赛季，1-是、0-否',
  `has_player_stats` int DEFAULT NULL COMMENT '是否有球员统计，1-是、0-否',
  `has_team_stats` int DEFAULT NULL COMMENT '是否有球队统计，1-是、0-否',
  `has_table` int DEFAULT NULL COMMENT '是否有积分榜，1-是、0-否',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`season_id`,`rev`) USING BTREE,
  KEY `FK_rev` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米篮球赛季列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `beitai_football_team`
--

DROP TABLE IF EXISTS `beitai_football_team`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `beitai_football_team` (
  `team_id` int NOT NULL,
  `team_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `team_name_en` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `manager_id` int DEFAULT NULL,
  `manager_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `manager_name_en` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `manager_date_of_birth` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `manager_country_code` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `gender` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `country_code` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `season_year` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `season_id` int DEFAULT NULL,
  `tournament_id` int NOT NULL,
  `venue_id` int DEFAULT NULL,
  `away_jerseys` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `home_jerseys` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `third_jerseys` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `goalkeeper_jerseys` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `venue_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `venue_name_en` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `venue_city_name_en` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `venue_country_name_en` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `venue_map_coordinates` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `venue_capacity` int DEFAULT NULL,
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`team_id`,`tournament_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sporttery_match_remark`
--

DROP TABLE IF EXISTS `sporttery_match_remark`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sporttery_match_remark` (
  `remark_id` int NOT NULL AUTO_INCREMENT COMMENT '备注ID',
  `sport_id` int NOT NULL COMMENT '运动项目ID，区分足球/篮球ID域',
  `remark_type` int NOT NULL COMMENT '备注类型 1竞彩比赛监控',
  `match_id` bigint NOT NULL COMMENT '竞彩比赛ID，非s_match ID',
  `remark` varchar(300) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '用户备注',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '创建用户',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新用户',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`remark_id`) USING BTREE,
  UNIQUE KEY `uk_sptty_user_remark` (`sport_id`,`remark_type`,`match_id`,`create_account`) USING BTREE,
  KEY `idx_sptty_remark_list` (`sport_id`,`match_id`,`remark_type`,`update_time`,`remark_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='竞彩比赛用户备注表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_r_season_team`
--

DROP TABLE IF EXISTS `audit_r_season_team`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_r_season_team` (
  `season_team_id` int NOT NULL COMMENT '赛季球队id',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `manual_competition_id` int NOT NULL COMMENT '人工录入的赛事id',
  `manual_season_id` int NOT NULL COMMENT '人工录入的赛季id',
  `manual_team_id` int NOT NULL COMMENT '人工录入的球队id',
  `sport_id` int NOT NULL COMMENT '运动项目id',
  `season_bd_team_name` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '北单全称',
  `season_bd_team_short_name` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '北单简称',
  `naming_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '命名类型',
  `submit_status` int DEFAULT NULL COMMENT '提交状态 0未提交 1已提交',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账号',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账号',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`season_team_id`,`rev`) USING BTREE,
  KEY `FK_rev` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_r_team_data`
--

DROP TABLE IF EXISTS `audit_r_team_data`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_r_team_data` (
  `relation_id` int NOT NULL COMMENT '匹配id',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `sport_id` int NOT NULL COMMENT '运动项目id',
  `manual_team_id` int NOT NULL COMMENT '人工录入数据的球队id 暂和m_team_id一致',
  `standard_team_id` int NOT NULL COMMENT '标准化球队id',
  `source_type` tinyint NOT NULL COMMENT '数据源 1纳米 2同行',
  `source_team_id` int NOT NULL COMMENT '数据源球队id',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账户',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账户',
  PRIMARY KEY (`relation_id`,`rev`) USING BTREE,
  KEY `FK_rev` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='球队数据匹配关系表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `beitai_football_match_deleted`
--

DROP TABLE IF EXISTS `beitai_football_match_deleted`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `beitai_football_match_deleted` (
  `id` int NOT NULL COMMENT '删除记录ID',
  `match_id` bigint DEFAULT NULL COMMENT '比赛ID',
  `tournament_id` int DEFAULT NULL COMMENT '联赛ID',
  `season_id` int DEFAULT NULL COMMENT '赛季ID',
  `season_year` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛季年度描述',
  `del_date` datetime DEFAULT NULL COMMENT '删除时间',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='雷达比赛删除记录表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sporttery_basketball_match`
--

DROP TABLE IF EXISTS `sporttery_basketball_match`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sporttery_basketball_match` (
  `match_id` bigint NOT NULL COMMENT '官方比赛ID',
  `s_match_id` int DEFAULT NULL COMMENT '关联标准化比赛 s_match.match_id',
  `if_change` tinyint DEFAULT NULL COMMENT '主客队方向：0顺序一致、1主客反序；由预处理维护，采集不写入',
  `match_no` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '场次编号，如周二301',
  `business_date` date DEFAULT NULL COMMENT '受注业务日',
  `league_id` bigint DEFAULT NULL COMMENT '联赛ID',
  `home_team_id` bigint DEFAULT NULL COMMENT '主队ID',
  `away_team_id` bigint DEFAULT NULL COMMENT '客队ID',
  `match_time` datetime DEFAULT NULL COMMENT '比赛时间（官方 matchDate + matchTime）',
  `sell_status` tinyint DEFAULT NULL COMMENT '销售状态：1在售/2停售/3已开奖',
  `part1` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '第1节比分',
  `part2` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '第2节比分',
  `part3` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '第3节比分',
  `part4` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '第4节比分',
  `part_end` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '终场比分',
  `home_score` int DEFAULT NULL COMMENT '修订时主队全场得分',
  `away_score` int DEFAULT NULL COMMENT '修订时客队全场得分',
  `remark` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '官方备注',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`match_id`) USING BTREE,
  KEY `idx_league_id` (`league_id`) USING BTREE,
  KEY `idx_business_date` (`business_date`) USING BTREE,
  KEY `idx_sell_status` (`sell_status`) USING BTREE,
  KEY `idx_sptty_bb_smatch` (`s_match_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='竞彩篮球赛程表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_bd_batch_matchup_draw`
--

DROP TABLE IF EXISTS `audit_bd_batch_matchup_draw`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_bd_batch_matchup_draw` (
  `batch_matchup_id` int NOT NULL COMMENT '批次比赛id 同bd_batch_matchup主键',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `batch_id_match_result` int NOT NULL COMMENT '赛果批次id',
  `match_id` int NOT NULL COMMENT '比赛id',
  `game_draw_id` int NOT NULL COMMENT '奖期id',
  `matchup_unique_no` varchar(21) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '比赛唯一编号',
  `draw_game_list` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '开奖的游戏列表，逗号分割 如200,210,230,240,250,260,270',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账号',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账号',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`batch_matchup_id`,`draw_game_list`,`batch_id_match_result`,`rev`) USING BTREE,
  KEY `batch_matchup_id` (`batch_matchup_id`) USING BTREE,
  KEY `batch_id_match_result` (`batch_id_match_result`) USING BTREE,
  KEY `matchup_unique_no` (`matchup_unique_no`) USING BTREE,
  KEY `FK_rev` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='北单批次开奖表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `m_team`
--

DROP TABLE IF EXISTS `m_team`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `m_team` (
  `team_id` int NOT NULL AUTO_INCREMENT COMMENT '球队id 自增',
  `sport_id` int NOT NULL COMMENT '运动项目id',
  `country` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '国家/地区',
  `name_zh` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '球队全称',
  `short_name_zh` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '球队简称',
  `bd_team_name` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '北单全称',
  `bd_team_short_name` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '北单简称',
  `foreign_name` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '官网赛程外文名称',
  `official_web_en_name` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '官网赛程英文名称',
  `name_en` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文全称',
  `nami_id_match_status` tinyint NOT NULL DEFAULT '0' COMMENT '纳米匹配状态 0未匹配 1匹配 默认0',
  `beitai_id_match_status` tinyint NOT NULL DEFAULT '0' COMMENT '贝泰匹配状态 0未匹配 1匹配 默认0',
  `naming_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '命名类型',
  `naming_reason` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '命名原因',
  `jc_name` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '竞彩全称',
  `jc_short_name` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '竞彩简称',
  `ctzc_short_name` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '传统足彩简称',
  `dqd_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '懂球帝名称',
  `logo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球队logo',
  `official_web` varchar(300) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '官方网站',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账户',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账户',
  PRIMARY KEY (`team_id`) USING BTREE,
  UNIQUE KEY `uk_name_zh` (`name_zh`,`sport_id`) USING BTREE,
  UNIQUE KEY `uk_short_name_zh` (`short_name_zh`,`sport_id`) USING BTREE,
  UNIQUE KEY `uk_bd_team_name` (`bd_team_name`,`sport_id`) USING BTREE,
  UNIQUE KEY `uk_bd_team_short_name` (`bd_team_short_name`,`sport_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=7519 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='人工录入的球队';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `r_season_team`
--

DROP TABLE IF EXISTS `r_season_team`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `r_season_team` (
  `season_team_id` int NOT NULL AUTO_INCREMENT COMMENT '赛季球队id 自增',
  `manual_competition_id` int NOT NULL COMMENT '人工录入的赛事id',
  `manual_season_id` int NOT NULL COMMENT '人工录入的赛季id',
  `manual_team_id` int NOT NULL COMMENT '人工录入的球队id',
  `sport_id` int NOT NULL COMMENT '运动项目id',
  `season_bd_team_name` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '北单全称',
  `season_bd_team_short_name` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '北单简称',
  `naming_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '命名类型',
  `submit_status` int DEFAULT NULL COMMENT '提交状态 0未提交 1已提交',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账号',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账号',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`season_team_id`) USING BTREE,
  UNIQUE KEY `uk_season_team` (`manual_season_id`,`manual_team_id`) USING BTREE,
  UNIQUE KEY `uk_season_team1` (`manual_season_id`,`season_bd_team_name`) USING BTREE,
  UNIQUE KEY `uk_season_team2` (`manual_season_id`,`season_bd_team_short_name`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=12338 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='赛季球队表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `s_category`
--

DROP TABLE IF EXISTS `s_category`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `s_category` (
  `category_id` int NOT NULL AUTO_INCREMENT COMMENT '分类id',
  `name_zh` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文名称',
  `name_en` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`category_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='标准化-分类列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `rdc`
--

DROP TABLE IF EXISTS `rdc`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `rdc` (
  `rdc_id` int unsigned NOT NULL COMMENT '中心ID',
  `rdc_name` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '中心名称',
  `rdc_full_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中心全称',
  `old_rdc_id` int NOT NULL COMMENT 'v1系统中心ID',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`rdc_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='彩票中心';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_nami_football_competition`
--

DROP TABLE IF EXISTS `audit_nami_football_competition`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_nami_football_competition` (
  `competition_id` int NOT NULL COMMENT '赛事id',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `category_id` int DEFAULT NULL COMMENT '分类id',
  `country_id` int DEFAULT NULL COMMENT '国家id',
  `name_zh` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文名称',
  `name_zht` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语名称',
  `name_en` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `short_name_zh` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文简称',
  `short_name_zht` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语简称',
  `short_name_en` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文简称',
  `logo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛事logo',
  `type` int DEFAULT NULL COMMENT '赛事类型，0-未知、1-联赛、2-杯赛、3-友谊赛',
  `title_holder` json DEFAULT NULL COMMENT '卫冕冠军',
  `most_titles` json DEFAULT NULL COMMENT '夺冠最多球队列表',
  `newcomers` json DEFAULT NULL COMMENT '晋级淘汰球队低级赛事升级球队球队id列表',
  `divisions` json DEFAULT NULL COMMENT '赛事层级高一级赛事id列表',
  `host` json DEFAULT NULL COMMENT '东道主国家',
  `primary_color` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '主颜色',
  `secondary_color` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '次颜色',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`competition_id`,`rev`) USING BTREE,
  KEY `FK_rev` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米足球赛事列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_nami_football_season`
--

DROP TABLE IF EXISTS `audit_nami_football_season`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_nami_football_season` (
  `season_id` int NOT NULL COMMENT '赛季id',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `competition_id` int DEFAULT NULL COMMENT '赛事id',
  `year` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛季年份',
  `start_time` bigint DEFAULT NULL COMMENT '开始时间',
  `end_time` bigint DEFAULT NULL COMMENT '结束时间',
  `is_current` int DEFAULT NULL COMMENT '是否最新赛季，1-是、0-否',
  `has_player_stats` int DEFAULT NULL COMMENT '是否有球员统计，1-是、0-否',
  `has_team_stats` int DEFAULT NULL COMMENT '是否有球队统计，1-是、0-否',
  `has_table` int DEFAULT NULL COMMENT '是否有积分榜，1-是、0-否',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`season_id`,`rev`) USING BTREE,
  KEY `FK_rev` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米足球赛季列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_nami_ice_hockey_match`
--

DROP TABLE IF EXISTS `audit_nami_ice_hockey_match`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_nami_ice_hockey_match` (
  `match_id` int NOT NULL COMMENT '比赛id',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `competition_id` int DEFAULT NULL COMMENT '赛事id',
  `season_id` int DEFAULT NULL COMMENT '赛季id',
  `stage_id` int DEFAULT NULL COMMENT '阶段id',
  `venue_id` int DEFAULT NULL COMMENT '场馆id',
  `home_team_id` int DEFAULT NULL COMMENT '主队id',
  `away_team_id` int DEFAULT NULL COMMENT '客队id',
  `match_time` int DEFAULT NULL COMMENT '比赛时间 时间戳精确到毫秒',
  `status_id` int DEFAULT NULL COMMENT '比赛状态 见字典ice_hockey_match_status',
  `neutral` int DEFAULT NULL COMMENT '是否中立场，1-是、0-否',
  `coverage_mlive` int DEFAULT NULL COMMENT '动画字段 是否有动画，1-是、0-否',
  `scores` json DEFAULT NULL COMMENT '比分数据 ft - 常规比分; p* - 局比分(* - 局数，1、2、3...);ot - 加时赛比分(包含ft) ; ap - 点球比分(包含ft、ot)',
  `tbd` int DEFAULT NULL COMMENT '比赛时间是否待定 1.是',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`match_id`,`rev`) USING BTREE,
  KEY `FKpff5i3f8x403ydfdddeqwum` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_bd_batch`
--

DROP TABLE IF EXISTS `audit_bd_batch`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_bd_batch` (
  `batch_id` int NOT NULL COMMENT '批次id',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `game_draw_id` int NOT NULL COMMENT '奖期ID',
  `batch_order_no` int DEFAULT NULL COMMENT '批次序号',
  `batch_type` int DEFAULT NULL COMMENT '批次类型 0 赛程批次 1开奖批次',
  `sports_id_list` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '运动项目list 逗号分隔',
  `is_final_version` int DEFAULT NULL COMMENT '是否生成正式版 0未生成  1已生成 ',
  `preset_sale_begin_time` datetime DEFAULT NULL COMMENT '预设的批次开售时间',
  `preset_draw_time` datetime DEFAULT NULL COMMENT '计划开奖时间',
  `draw_game_id_list` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '批次开奖的游戏，逗号分隔，如200,210,230,240,250,260,270',
  `batch_sale_status` int DEFAULT NULL COMMENT '是否开售 0未开售 1开售',
  `submit_status` int DEFAULT NULL COMMENT '提交状态 0未提交 1已提交',
  `batch_draw_status` int DEFAULT NULL COMMENT '是否开奖 0未开奖 1已开奖',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账号',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账号',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`batch_id`,`rev`) USING BTREE,
  KEY `FK_rev` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_toto_role_permission`
--

DROP TABLE IF EXISTS `audit_toto_role_permission`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_toto_role_permission` (
  `role_permission_id` int unsigned NOT NULL,
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账号',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账号',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `permission_id` int DEFAULT NULL,
  `role_id` int DEFAULT NULL,
  `system_id` int DEFAULT NULL,
  PRIMARY KEY (`role_permission_id`,`rev`) USING BTREE,
  KEY `FKi7a25hdbyaq4lixt0sh8bfb7a` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `toto_err`
--

DROP TABLE IF EXISTS `toto_err`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `toto_err` (
  `err_id` int NOT NULL,
  `enum_key` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `enum_value` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `err_desc` varchar(4000) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  PRIMARY KEY (`err_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='错误类型描述';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_football_venue`
--

DROP TABLE IF EXISTS `nami_football_venue`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_football_venue` (
  `venue_id` int NOT NULL COMMENT '场馆id',
  `name_zh` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文名称',
  `name_zht` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语名称',
  `name_en` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `capacity` int DEFAULT NULL COMMENT '球场容量',
  `country_id` int DEFAULT NULL COMMENT '国家id',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`venue_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米足球场馆列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `s_event`
--

DROP TABLE IF EXISTS `s_event`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `s_event` (
  `event_id` varchar(11) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '事件id',
  `event_type` int DEFAULT NULL COMMENT '事件类型 0无异常 1比赛异常 2数据异常 3预警',
  `event_level` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '告警级别 红色、橙色、黄色、无',
  `identity_data` json DEFAULT NULL COMMENT '事件标识数据',
  `source_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '事件来源',
  `source_id` bigint NOT NULL COMMENT '事件来源数据id',
  `reason_title` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '事件原因标题',
  `reason_desc` varchar(5000) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '事件原因详情',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账号',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账号',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`event_id`) USING BTREE,
  KEY `idx_s_event_create_time` (`create_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='事件记录表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_football_team`
--

DROP TABLE IF EXISTS `nami_football_team`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_football_team` (
  `team_id` int NOT NULL COMMENT '球队id',
  `competition_id` int DEFAULT NULL COMMENT '赛事id（球队所属联赛，杯赛不关联）',
  `country_id` int DEFAULT NULL COMMENT '国家id',
  `coach_id` int DEFAULT NULL COMMENT '教练id',
  `name_zh` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文名称',
  `name_zht` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语名称',
  `name_en` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `short_name_zh` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文简称',
  `short_name_zht` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语简称',
  `short_name_en` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文简称',
  `logo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球队logo',
  `national` int DEFAULT NULL COMMENT '是否国家队，1-是、0-否',
  `country_logo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '国家队logo（为国家队时存在）',
  `foundation_time` bigint DEFAULT NULL COMMENT '成立时间',
  `website` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球队官网',
  `venue_id` int DEFAULT NULL COMMENT '场馆id',
  `market_value` bigint DEFAULT NULL COMMENT '市值',
  `market_value_currency` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '市值单位',
  `total_players` int DEFAULT NULL COMMENT '总球员数，-1表示没有该字段数据',
  `foreign_players` int DEFAULT NULL COMMENT '非本土球员数，-1表示没有该字段数据',
  `national_players` int DEFAULT NULL COMMENT '国家队球员数，-1表示没有该字段数据',
  `uid` int DEFAULT NULL COMMENT '球队id(重复球队合并后的对应id)',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`team_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米足球球队列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `m_match_remark`
--

DROP TABLE IF EXISTS `m_match_remark`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `m_match_remark` (
  `remark_id` int NOT NULL AUTO_INCREMENT COMMENT '备注 id 自增',
  `remark_type` int NOT NULL COMMENT '备注类型 1 赛程  2 让球 3 比赛监控',
  `match_id` int NOT NULL COMMENT '比赛id',
  `remark` varchar(300) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '备注',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账号',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账号',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`remark_id`) USING BTREE,
  KEY `uk_match_remark` (`remark_type`,`match_id`,`create_account`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=536 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='比赛备注表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `bjlot_match`
--

DROP TABLE IF EXISTS `bjlot_match`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `bjlot_match` (
  `game_id` int NOT NULL COMMENT '游戏编号gameinfos.id',
  `game_name` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '游戏名称\ngameinfos.name',
  `draw_id` int NOT NULL COMMENT '奖期ID thisDraw.id',
  `draw_no` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '奖期编号 thisDraw.no',
  `sale_begin_time` datetime DEFAULT NULL COMMENT '奖期销售开始时间 schedule.begin',
  `sale_end_time` datetime DEFAULT NULL COMMENT '奖期销售结束时间 schedule.end',
  `draw_time` datetime DEFAULT NULL COMMENT '奖期开奖时间 schedule.draw',
  `matchup_unique_no` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '比赛唯一编号',
  `matchup_no` int NOT NULL COMMENT '场次编号 matches.matchInfo.matchelem.item.no',
  `sport_name` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '运动项目 matches.matchInfo.matchelem.item.gameTypeName',
  `bj_match_status` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛程状态 matches.matchInfo.matchelem.item.matchandstate',
  `league_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛事简称 matches.matchInfo.matchelem.item.leagueName',
  `match_sale_end_time` datetime DEFAULT NULL COMMENT '停售时间 matches.matchInfo.matchelem.item.endTime',
  `home_team_short_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '主队简称 matches.matchInfo.matchelem.item.host',
  `home_team_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '主队全称 matches.matchInfo.matchelem.item.hostFull',
  `handicap` varchar(5) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '让球 matches.matchInfo.matchelem.item.handicap',
  `handicap_danwei` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '让球单位 matches.matchInfo.matchelem.item.rangDanWei',
  `away_team_short_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '客队简称 matches.matchInfo.matchelem.item.guest',
  `away_team_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '客队全称 matches.matchInfo.matchelem.item.guestFull',
  `soccer_half` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '半场比分 matches.matchInfo.matchelem.item.halfsoccer',
  `soccer` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '全场比分 matches.matchInfo.matchelem.item.soccer',
  `sp` json DEFAULT NULL COMMENT 'sp 值matches.matchInfo.matchelem.item.spitem',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`draw_id`,`matchup_no`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='北京体彩网比赛';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `bd_batch_matchup`
--

DROP TABLE IF EXISTS `bd_batch_matchup`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `bd_batch_matchup` (
  `batch_matchup_id` int NOT NULL AUTO_INCREMENT COMMENT '批次比赛id',
  `batch_id` int NOT NULL COMMENT '批次id',
  `sort_no` int NOT NULL COMMENT '界面展示排序序号',
  `game_draw_id` int NOT NULL COMMENT '奖期id',
  `match_id` int NOT NULL COMMENT '比赛id',
  `manual_competition_id` int NOT NULL COMMENT '人工录入的赛事',
  `manual_season_id` int NOT NULL COMMENT '人工录入的赛季',
  `matchup_unique_no` varchar(21) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '比赛唯一编号',
  `game1200_matchup_no` int DEFAULT NULL COMMENT '单场场次编号',
  `game1260_matchup_no` int DEFAULT NULL COMMENT '下半场比分场次编号',
  `game1270_matchup_no` int DEFAULT NULL COMMENT '胜负过关场次编号',
  `sport_id` int NOT NULL COMMENT '运动项目id',
  `bd_round` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '轮次',
  `match_time` datetime NOT NULL COMMENT '开赛时间',
  `home_team_id` int NOT NULL COMMENT '主队id',
  `away_team_id` int NOT NULL COMMENT '客队id',
  `team_reverse` int NOT NULL DEFAULT '0' COMMENT '主客队调换 0不调换 1调换 默认0',
  `sale_end_time` datetime DEFAULT NULL COMMENT '停售时间',
  `game1260_sale_end_time` datetime DEFAULT NULL COMMENT '下半场比分停售时间',
  `game1200_handicap` int DEFAULT NULL COMMENT '单场让球 无让球为0',
  `game1270_handicap` decimal(10,1) DEFAULT NULL COMMENT '胜负让球 无让球为0',
  `sale_game_list` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '开售的游戏列表，逗号分割 如200,210,230,240,250,260,270',
  `game1200_draw_time` datetime DEFAULT NULL COMMENT '单场开奖时间',
  `game1270_draw_time` datetime DEFAULT NULL COMMENT '胜负过关开奖时间',
  `game1260_draw_time` datetime DEFAULT NULL COMMENT '下半场比分开奖时间',
  `match_result_status` int DEFAULT NULL COMMENT '赛果确认状态  0未确认 1 已确认',
  `home_score_half` int DEFAULT NULL COMMENT '主队半场比分',
  `away_score_half` int DEFAULT NULL COMMENT '客队半场比分',
  `home_score` int DEFAULT NULL COMMENT '主队全场比分',
  `away_score` int DEFAULT NULL COMMENT '客队全场比分',
  `confirm_time` datetime DEFAULT NULL COMMENT '赛果确认时间',
  `confirm_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛果确认账户',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账号',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账号',
  PRIMARY KEY (`batch_matchup_id`) USING BTREE,
  KEY `ind_batch_id` (`batch_id`) USING BTREE,
  KEY `ind_game_draw_id` (`game_draw_id`) USING BTREE,
  KEY `ind_match_id` (`match_id`) USING BTREE,
  KEY `ind_matchup_unique_no` (`matchup_unique_no`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=53666 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='北单批次比赛表（正式版本）';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_american_football_season`
--

DROP TABLE IF EXISTS `nami_american_football_season`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_american_football_season` (
  `season_id` int NOT NULL COMMENT '赛季id',
  `competition_id` int DEFAULT NULL COMMENT '赛事id',
  `year` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛季年份',
  `start_time` int DEFAULT NULL COMMENT '开始时间',
  `end_time` int DEFAULT NULL COMMENT '结束时间',
  `is_current` int DEFAULT NULL COMMENT '是否最新赛季，1-是、0-否',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`season_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米橄榄球赛季列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_m_team_blacklist`
--

DROP TABLE IF EXISTS `audit_m_team_blacklist`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_m_team_blacklist` (
  `team_blacklist_id` int NOT NULL COMMENT '球队黑名单ID',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `manual_team_id` int NOT NULL COMMENT '人工录入的球队id',
  `reason` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '添加原因',
  `del_reason` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '移除原因',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账号',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账号',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`team_blacklist_id`,`rev`) USING BTREE,
  KEY `FK_rev` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `beitai_football_event`
--

DROP TABLE IF EXISTS `beitai_football_event`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `beitai_football_event` (
  `event_id` bigint NOT NULL COMMENT '事件ID',
  `match_id` bigint NOT NULL COMMENT '比赛ID',
  `clock` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '比赛时钟',
  `order_id` int DEFAULT NULL COMMENT '事件顺序ID',
  `match_time` int DEFAULT NULL COMMENT '比赛时间（分钟）',
  `stoppage_time` int DEFAULT NULL COMMENT '伤停补时时间',
  `stoppage_time_clock` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '伤停补时时钟',
  `injury_time_announced` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '宣布的伤停时间',
  `period` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '比赛阶段',
  `event_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '事件类型',
  `team` int DEFAULT NULL COMMENT '球队id',
  `player_id1` int DEFAULT NULL COMMENT '球员1ID',
  `player_id2` int DEFAULT NULL COMMENT '球员2ID',
  `player_name1` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球员1姓名',
  `player_name2` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球员2姓名',
  `player_type1` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球员1类型',
  `player_type2` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球员2类型',
  `method` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '方法',
  `status` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '状态',
  `coord_x` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT 'X坐标',
  `coord_y` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT 'Y坐标',
  `text` text CHARACTER SET utf8mb4 COLLATE utf8mb4_bin COMMENT '事件描述文本',
  `home_score` int DEFAULT NULL COMMENT '主队得分',
  `away_score` int DEFAULT NULL COMMENT '客队得分',
  `card_description` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '卡片描述',
  `event_time` datetime DEFAULT NULL COMMENT '事件创建时间',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`event_id`) USING BTREE,
  KEY `ind_match_id` (`match_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='雷达比赛事件表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_tx_stage`
--

DROP TABLE IF EXISTS `audit_tx_stage`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_tx_stage` (
  `stage_id` bigint NOT NULL COMMENT '阶段id',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `season_id` bigint DEFAULT NULL COMMENT '赛季id',
  `competition_id` int DEFAULT NULL COMMENT '赛事ID',
  `name_zh` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '阶段名称',
  `stage_order` int DEFAULT NULL COMMENT '排序，阶段的先后顺序',
  `error_detail` json DEFAULT NULL COMMENT '异常信息',
  `first_match_time` datetime DEFAULT NULL COMMENT '阶段中第一场比赛的比赛时间',
  `last_match_time` datetime DEFAULT NULL COMMENT '阶段中最后一场比赛的比赛时间',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`stage_id`,`rev`) USING BTREE,
  KEY `FK_rev` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin ROW_FORMAT=DYNAMIC COMMENT='同行阶段表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `s_country`
--

DROP TABLE IF EXISTS `s_country`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `s_country` (
  `country_id` int NOT NULL AUTO_INCREMENT COMMENT '国家id',
  `category_id` int DEFAULT NULL COMMENT '分类id',
  `nami_country_id` int DEFAULT NULL COMMENT '纳米国家id',
  `tx_country_id` int DEFAULT NULL COMMENT '同行国家id',
  `name_zh` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文名称',
  `name_en` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `logo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '国家logo',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`country_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='标准化-国家列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `openapi_audit_log`
--

DROP TABLE IF EXISTS `openapi_audit_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `openapi_audit_log` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '物理主键',
  `request_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '请求 ID（链路追踪）',
  `user_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '业务方标识（5 类事件中"签名未通过"事件此处可能为空）',
  `path` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '接口路径',
  `method` varchar(8) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT 'HTTP 方法',
  `client_ip` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '解析后的客户端 IP',
  `remote_addr` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '直连来源 IP',
  `x_forwarded_for` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT '' COMMENT '原始 X-Forwarded-For 头',
  `request_time` datetime(3) NOT NULL COMMENT '请求开始时间（毫秒精度）',
  `response_time` datetime(3) DEFAULT NULL COMMENT '请求结束时间（毫秒精度）',
  `duration_ms` int NOT NULL DEFAULT '0' COMMENT '耗时（毫秒）',
  `http_status` int NOT NULL DEFAULT '0' COMMENT 'HTTP 状态码',
  `biz_code` int NOT NULL DEFAULT '0' COMMENT '业务响应码（v1.5 升级：Integer，对齐 CommonResult 规范；OK=0；详见 §9 v1.5 变更日志）',
  `error_message` varchar(2048) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL DEFAULT '' COMMENT '错误信息（脱敏后）',
  `event_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL DEFAULT 'SERVICE_EXCEPTION' COMMENT '事件类型：SUCCESS / AUTH_FAIL / PERMISSION_FAIL / RATE_LIMIT_FAIL / SERVICE_EXCEPTION（v1.6 升级：加 DDL DEFAULT 兜底，替代实体层 @PrePersist；详见 §4.1 + §9 v1.6 变更日志）',
  `query_digest` varchar(2048) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '脱敏后的 query 摘要（绝不出现密钥/sign/敏感参数）',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `auth_time` bigint DEFAULT NULL COMMENT '鉴权时间戳（v1.10 升级：Unix 秒；来自 X-OpenAPI-Time Header 解析值；鉴权失败时为 NULL）',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_request_time` (`request_time`) USING BTREE,
  KEY `idx_user_time` (`user_code`,`request_time`) USING BTREE,
  KEY `idx_path_time` (`path`,`request_time`) USING BTREE,
  KEY `idx_event_time` (`event_type`,`request_time`) USING BTREE,
  KEY `idx_user_auth_time` (`user_code`,`auth_time`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=19371 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='开放接口审计日志';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `toto_system`
--

DROP TABLE IF EXISTS `toto_system`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `toto_system` (
  `system_id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '系统 ID',
  `system_name` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '系统名称',
  `system_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '系统描述',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`system_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='系统表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_toto_role`
--

DROP TABLE IF EXISTS `audit_toto_role`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_toto_role` (
  `role_id` int unsigned NOT NULL,
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账号',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账号',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `is_deleted` tinyint DEFAULT NULL,
  `role_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `role_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `role_type` tinyint DEFAULT NULL,
  `system_id` int DEFAULT NULL,
  PRIMARY KEY (`role_id`,`rev`) USING BTREE,
  KEY `FKam1oln8wikqbt6p37jnerpg0p` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_ice_hockey_competition`
--

DROP TABLE IF EXISTS `nami_ice_hockey_competition`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_ice_hockey_competition` (
  `competition_id` int NOT NULL COMMENT '赛事id',
  `category_id` int DEFAULT NULL COMMENT '分类id',
  `country_id` int DEFAULT NULL COMMENT '国家id',
  `uid` int DEFAULT NULL COMMENT '纳米赛事合并对应ID',
  `name_zh` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文名称',
  `name_en` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `name_zht` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语名称',
  `short_name_zh` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文简称',
  `short_name_en` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文简称',
  `short_name_zht` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语简称',
  `logo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛事logo',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`competition_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米冰球赛事列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sporttery_football_crs_odds`
--

DROP TABLE IF EXISTS `sporttery_football_crs_odds`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sporttery_football_crs_odds` (
  `match_id` int NOT NULL COMMENT 'Sporttery 官方比赛 ID，同时关联 sporttery_football_match.match_id',
  `collect_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '本次赔率采集时间',
  `1_0` decimal(6,2) DEFAULT NULL COMMENT '比分 1:0 赔率，对应接口 s01s00',
  `2_0` decimal(6,2) DEFAULT NULL COMMENT '比分 2:0 赔率，对应接口 s02s00',
  `2_1` decimal(6,2) DEFAULT NULL COMMENT '比分 2:1 赔率，对应接口 s02s01',
  `3_0` decimal(6,2) DEFAULT NULL COMMENT '比分 3:0 赔率，对应接口 s03s00',
  `3_1` decimal(6,2) DEFAULT NULL COMMENT '比分 3:1 赔率，对应接口 s03s01',
  `3_2` decimal(6,2) DEFAULT NULL COMMENT '比分 3:2 赔率，对应接口 s03s02',
  `4_0` decimal(6,2) DEFAULT NULL COMMENT '比分 4:0 赔率，对应接口 s04s00',
  `4_1` decimal(6,2) DEFAULT NULL COMMENT '比分 4:1 赔率，对应接口 s04s01',
  `4_2` decimal(6,2) DEFAULT NULL COMMENT '比分 4:2 赔率，对应接口 s04s02',
  `5_0` decimal(6,2) DEFAULT NULL COMMENT '比分 5:0 赔率，对应接口 s05s00',
  `5_1` decimal(6,2) DEFAULT NULL COMMENT '比分 5:1 赔率，对应接口 s05s01',
  `5_2` decimal(6,2) DEFAULT NULL COMMENT '比分 5:2 赔率，对应接口 s05s02',
  `win_else` decimal(6,2) DEFAULT NULL COMMENT '胜其他赔率，对应接口 s1sh',
  `0_0` decimal(6,2) DEFAULT NULL COMMENT '比分 0:0 赔率，对应接口 s00s00',
  `1_1` decimal(6,2) DEFAULT NULL COMMENT '比分 1:1 赔率，对应接口 s01s01',
  `2_2` decimal(6,2) DEFAULT NULL COMMENT '比分 2:2 赔率，对应接口 s02s02',
  `3_3` decimal(6,2) DEFAULT NULL COMMENT '比分 3:3 赔率，对应接口 s03s03',
  `equal_else` decimal(6,2) DEFAULT NULL COMMENT '平其他赔率，对应接口 s1sd',
  `0_1` decimal(6,2) DEFAULT NULL COMMENT '比分 0:1 赔率，对应接口 s00s01',
  `0_2` decimal(6,2) DEFAULT NULL COMMENT '比分 0:2 赔率，对应接口 s00s02',
  `1_2` decimal(6,2) DEFAULT NULL COMMENT '比分 1:2 赔率，对应接口 s01s02',
  `0_3` decimal(6,2) DEFAULT NULL COMMENT '比分 0:3 赔率，对应接口 s00s03',
  `1_3` decimal(6,2) DEFAULT NULL COMMENT '比分 1:3 赔率，对应接口 s01s03',
  `2_3` decimal(6,2) DEFAULT NULL COMMENT '比分 2:3 赔率，对应接口 s02s03',
  `0_4` decimal(6,2) DEFAULT NULL COMMENT '比分 0:4 赔率，对应接口 s00s04',
  `1_4` decimal(6,2) DEFAULT NULL COMMENT '比分 1:4 赔率，对应接口 s01s04',
  `2_4` decimal(6,2) DEFAULT NULL COMMENT '比分 2:4 赔率，对应接口 s02s04',
  `0_5` decimal(6,2) DEFAULT NULL COMMENT '比分 0:5 赔率，对应接口 s00s05',
  `1_5` decimal(6,2) DEFAULT NULL COMMENT '比分 1:5 赔率，对应接口 s01s05',
  `2_5` decimal(6,2) DEFAULT NULL COMMENT '比分 2:5 赔率，对应接口 s02s05',
  `lose_else` decimal(6,2) DEFAULT NULL COMMENT '负其他赔率，对应接口 s1sa',
  `int_single` int DEFAULT NULL COMMENT '是否允许单关：0 不允许，1 允许；没有返回时为空',
  `match_status` int DEFAULT NULL COMMENT '玩法对应比赛状态：1 开售，2 停售，3 已开奖',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`match_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='竞彩足球比分最新赔率表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_american_football_team`
--

DROP TABLE IF EXISTS `nami_american_football_team`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_american_football_team` (
  `team_id` int NOT NULL COMMENT '球队id',
  `name_zh` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文名称',
  `name_en` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `name_zht` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语名称',
  `short_name_zh` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文简称',
  `short_name_en` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文简称',
  `short_name_zht` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语简称',
  `abbr` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '缩写',
  `logo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT 'logo',
  `gender` int DEFAULT NULL COMMENT '性别，1-男、2-女、0-未知',
  `national` int DEFAULT NULL COMMENT '是否国家队，0-否、1-是',
  `is_virtual` int DEFAULT NULL COMMENT '是否占位球队 1是0否',
  `uid` int DEFAULT NULL COMMENT '纳米球队合并对应ID',
  `coach_ids` json DEFAULT NULL COMMENT '教练ID数组JSON串',
  `country_id` int DEFAULT NULL COMMENT '纳米国家ID，关联 nami_american_football_country.country_id',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`team_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米冰球球队列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_bd_batch_diff_record`
--

DROP TABLE IF EXISTS `audit_bd_batch_diff_record`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_bd_batch_diff_record` (
  `game_draw_id` int NOT NULL COMMENT '奖期id',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `batch_id` int NOT NULL COMMENT '批次id',
  `diff_status` tinyint NOT NULL COMMENT '0进行中 1比对完成 2比对取消',
  `diff_base_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '比对的基准用户',
  `diff_target_account_list` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '比对用户列表,逗号分隔',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账号',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账号',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`game_draw_id`,`batch_id`,`rev`) USING BTREE,
  KEY `FK_rev` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_tx_match`
--

DROP TABLE IF EXISTS `audit_tx_match`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_tx_match` (
  `match_id` int NOT NULL COMMENT '比赛编号',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `competition_id` int NOT NULL COMMENT '赛事id',
  `home_team_id` int NOT NULL COMMENT '主队编号。',
  `away_team_id` int NOT NULL COMMENT '客队编号。',
  `match_date` bigint NOT NULL COMMENT '比赛时间 时间戳精确到毫秒',
  `season_id` bigint DEFAULT NULL COMMENT '赛季id',
  `stage_id` bigint DEFAULT NULL COMMENT '阶段id',
  `mode` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛制形式',
  `match_group` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '分组',
  `round` tinyint DEFAULT NULL COMMENT '轮次(接口中的Schedule)',
  `period` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '阶段',
  `home_team_rank` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '主队排名',
  `away_team_rank` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '客队排名',
  `neutrality` int DEFAULT NULL COMMENT '是否中立场地。',
  `note` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '备注。',
  `score` json DEFAULT NULL COMMENT '全场比分。',
  `half` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '半场比分。',
  `score_all` json DEFAULT NULL COMMENT '全场比分（含加时）。',
  `score_point` json DEFAULT NULL COMMENT '点球比分。',
  `red_card` json DEFAULT NULL COMMENT '红牌数组',
  `yellow_card` json DEFAULT NULL COMMENT '黄牌数组',
  `valid_game` int DEFAULT NULL COMMENT '比赛状态 1正常 0异常',
  `status` int DEFAULT NULL COMMENT '比赛状态值 0未开始 1上半场 2中场 3下半场 4完场 5中断 6取消 7加时 8加时 9加时 10完场 11点球大战 12全场结束 13延期 14腰斩 15待定  16金球 17未开始',
  `handicap` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '让球',
  `weather` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '天气',
  `stadium` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '比赛场地',
  `match_localtime` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '当地时间',
  `referee` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '裁判',
  `capacity` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球馆容量',
  `spectator` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '现场观众',
  `earlyodds` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '初让球',
  `channel` varchar(300) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '直播频道',
  `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`match_id`,`rev`) USING BTREE,
  KEY `FK_rev` (`rev`) USING BTREE,
  KEY `competition_id` (`competition_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin ROW_FORMAT=DYNAMIC COMMENT='同行足球比赛表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sporttery_match_event`
--

DROP TABLE IF EXISTS `sporttery_match_event`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sporttery_match_event` (
  `event_id` varchar(11) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '事件id',
  `event_type` int NOT NULL COMMENT '事件类型，对齐s_event值域：0无异常 1比赛异常 2数据异常 3预警（竞彩本期均为1）',
  `event_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '事件名称，冗余identity_data.eventName，便于查询',
  `event_level` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '告警级别，对齐s_event值域：红色/橙色/黄色/无',
  `identity_data` json NOT NULL COMMENT '事件标识数据：显示上下文、比较模式与前后值快照',
  `source_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '事件来源，竞彩固定SPORTTERY',
  `source_id` bigint NOT NULL COMMENT '事件来源数据ID，即竞彩比赛ID',
  `reason_title` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '事件原因标题',
  `reason_desc` varchar(2048) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '事件原因详情，超长按契约拒绝或截断非关键说明',
  `event_code` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '竞彩扩展：稳定业务编码，见事件编码表',
  `sport_id` int NOT NULL COMMENT '竞彩扩展：LeagueSport运动项目ID，区分同值source_id的足球/篮球比赛',
  `s_match_id` int DEFAULT NULL COMMENT '竞彩扩展：生成事件时源表s_match_id当时值（关联快照）',
  `notification_data` json DEFAULT NULL COMMENT '通知内容与逐角色投递状态（与identity_data分离，通知调整不改变事件身份）',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建人',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新人',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`event_id`) USING BTREE,
  KEY `idx_sptty_event_match` (`sport_id`,`source_id`,`create_time`,`event_id`) USING BTREE,
  KEY `idx_sptty_event_name` (`event_name`) USING BTREE,
  KEY `idx_sptty_event_date` (`sport_id`,`create_time`,`event_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='竞彩异常事件表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_football_match_live`
--

DROP TABLE IF EXISTS `nami_football_match_live`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_football_match_live` (
  `match_id` int NOT NULL COMMENT '比赛id',
  `status_id` int DEFAULT NULL COMMENT '比赛状态，详见状态码->比赛状态',
  `home_scores` json DEFAULT NULL COMMENT '主队比分字段list',
  `away_scores` json DEFAULT NULL COMMENT '客队比分字段list',
  `kick_off_time` int DEFAULT NULL COMMENT '开球时间',
  `remark` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '备注',
  `stats` json DEFAULT NULL COMMENT '比赛统计',
  `incidents` json DEFAULT NULL COMMENT '比赛事件',
  `tlive` json DEFAULT NULL COMMENT '文字直播',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`match_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin ROW_FORMAT=DYNAMIC COMMENT='纳米足球比赛进程表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_nami_football_team`
--

DROP TABLE IF EXISTS `audit_nami_football_team`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_nami_football_team` (
  `team_id` int NOT NULL COMMENT '球队id',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `competition_id` int DEFAULT NULL COMMENT '赛事id（球队所属联赛，杯赛不关联）',
  `country_id` int DEFAULT NULL COMMENT '国家id',
  `coach_id` int DEFAULT NULL COMMENT '教练id',
  `name_zh` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文名称',
  `name_zht` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语名称',
  `name_en` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `short_name_zh` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文简称',
  `short_name_zht` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语简称',
  `short_name_en` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文简称',
  `logo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球队logo',
  `national` int DEFAULT NULL COMMENT '是否国家队，1-是、0-否',
  `country_logo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '国家队logo（为国家队时存在）',
  `foundation_time` bigint DEFAULT NULL COMMENT '成立时间',
  `website` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球队官网',
  `venue_id` int DEFAULT NULL COMMENT '场馆id',
  `market_value` bigint DEFAULT NULL COMMENT '市值',
  `market_value_currency` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '市值单位',
  `total_players` int DEFAULT NULL COMMENT '总球员数，-1表示没有该字段数据',
  `foreign_players` int DEFAULT NULL COMMENT '非本土球员数，-1表示没有该字段数据',
  `national_players` int DEFAULT NULL COMMENT '国家队球员数，-1表示没有该字段数据',
  `uid` int DEFAULT NULL COMMENT '球队id(重复球队合并后的对应id)',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`team_id`,`rev`) USING BTREE,
  KEY `FK_rev` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米足球球队列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_basketball_match`
--

DROP TABLE IF EXISTS `nami_basketball_match`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_basketball_match` (
  `match_id` int NOT NULL COMMENT '比赛id',
  `competition_id` int DEFAULT NULL COMMENT '赛事id',
  `home_team_id` int DEFAULT NULL COMMENT '主队id',
  `away_team_id` int DEFAULT NULL COMMENT '客队id',
  `kind` int DEFAULT NULL COMMENT '类型id，1-常规赛、2-季后赛、3-季前赛、4-全明星、5-杯赛、6-附加赛、0-无',
  `round_stage_id` int DEFAULT NULL COMMENT '存nami_basketball_stage_newgoal.season_id',
  `period_count` int DEFAULT NULL COMMENT '比赛总节数(不包含加时)',
  `status_id` int DEFAULT NULL COMMENT '比赛状态，详见状态码->比赛状态',
  `match_time` bigint DEFAULT NULL COMMENT '比赛时间 时间戳精确到秒',
  `neutral` int DEFAULT NULL COMMENT '是否中立场，1-是、0-否',
  `home_scores` json DEFAULT NULL COMMENT '主队比分字段list',
  `away_scores` json DEFAULT NULL COMMENT '客队比分字段list',
  `over_time_scores` json DEFAULT NULL COMMENT '加时赛比分字段说明',
  `home_position` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '主队排名',
  `away_position` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '客队排名',
  `coverage` json DEFAULT NULL COMMENT '动画、情报、阵容 字段',
  `venue_id` int DEFAULT NULL COMMENT '场馆id',
  `season_id` int DEFAULT NULL COMMENT '赛季id',
  `round` json DEFAULT NULL COMMENT '关联信息',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`match_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米篮球比赛列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `r_sporttery_basic_data`
--

DROP TABLE IF EXISTS `r_sporttery_basic_data`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `r_sporttery_basic_data` (
  `relation_id` bigint NOT NULL AUTO_INCREMENT COMMENT '关联ID',
  `source_type` tinyint NOT NULL COMMENT '数据源 4=竞彩（沿用 r_basic_data 枚举空间：1纳米 2同行）',
  `sport_id` int NOT NULL COMMENT '运动项目ID',
  `sporttery_league_id` bigint NOT NULL COMMENT '竞彩联赛ID（独立ID域，足球/篮球按 sport_id 区分）',
  `manual_competition_id` int NOT NULL COMMENT '标准化赛事ID m_competition.competition_id',
  `version` bigint NOT NULL DEFAULT '0' COMMENT '匹配编辑乐观锁版本',
  `create_account` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `update_account` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`relation_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=96 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='竞彩联赛与标准化赛事匹配关系表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_sporttery_match_remark`
--

DROP TABLE IF EXISTS `audit_sporttery_match_remark`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_sporttery_match_remark` (
  `remark_id` int NOT NULL AUTO_INCREMENT COMMENT '备注ID',
  `rev` int NOT NULL COMMENT 'Envers 修订号，业务关联共享 revinfo.rev',
  `revtype` tinyint DEFAULT NULL COMMENT '操作类型：0新增、1修改、2删除',
  `sport_id` int NOT NULL COMMENT '运动项目ID，区分足球/篮球ID域',
  `remark_type` int NOT NULL COMMENT '备注类型 1竞彩比赛监控',
  `match_id` bigint NOT NULL COMMENT '竞彩比赛ID，非s_match ID',
  `remark` varchar(300) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '用户备注',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '创建用户',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新用户',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`remark_id`,`rev`) USING BTREE,
  KEY `idx_audit_audit_sporttery_match_remark` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='竞彩比赛用户备注审计表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `bd_batch_matchup_draw_review`
--

DROP TABLE IF EXISTS `bd_batch_matchup_draw_review`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `bd_batch_matchup_draw_review` (
  `review_id` int NOT NULL AUTO_INCREMENT COMMENT '审核记录ID',
  `batch_id` int NOT NULL COMMENT '赛果批次ID，关联 bd_batch.batch_id',
  `account_id` int NOT NULL COMMENT '审核用户ID，关联 toto_account.account_id',
  `review_status` tinyint NOT NULL DEFAULT '0' COMMENT '审核状态：0未审核，1已审核',
  `review_time` datetime DEFAULT NULL COMMENT '完成审核时间',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `create_account` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账号',
  `update_account` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账号',
  PRIMARY KEY (`review_id`) USING BTREE,
  UNIQUE KEY `uk_bd_batch_matchup_draw_review_batch_account` (`batch_id`,`account_id`) USING BTREE,
  KEY `idx_bd_batch_matchup_draw_review_batch_status` (`batch_id`,`review_status`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=883 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='赛果批次审核状态表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_american_football_match`
--

DROP TABLE IF EXISTS `nami_american_football_match`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_american_football_match` (
  `match_id` int NOT NULL COMMENT '比赛id',
  `competition_id` int DEFAULT NULL COMMENT '赛事id',
  `season_id` int DEFAULT NULL COMMENT '赛季id',
  `stage_id` int DEFAULT NULL COMMENT '阶段id',
  `venue_id` int DEFAULT NULL COMMENT '场馆id',
  `home_team_id` int DEFAULT NULL COMMENT '主队id',
  `away_team_id` int DEFAULT NULL COMMENT '客队id',
  `match_time` int DEFAULT NULL COMMENT '比赛时间 时间戳精确到毫秒',
  `status_id` int DEFAULT NULL COMMENT '比赛状态，详见字典表nami_american_football_match_status',
  `neutral` int DEFAULT NULL COMMENT '是否中立场，1-是、0-否',
  `coverage_mlive` int DEFAULT NULL COMMENT '是否有动画，1-是、0-否',
  `scores` json DEFAULT NULL COMMENT '比分',
  `weather` json DEFAULT NULL COMMENT '天气',
  `tbd` int DEFAULT NULL COMMENT '比赛时间是否待定 1.是',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`match_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米橄榄球比赛列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `openapi_user`
--

DROP TABLE IF EXISTS `openapi_user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `openapi_user` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '物理主键',
  `user_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '业务方标识（对外唯一，开放接口 user 参数）',
  `user_name` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL DEFAULT '' COMMENT '业务方名称（人工可读）',
  `enabled` tinyint(1) NOT NULL DEFAULT '1' COMMENT '1=启用，0=停用',
  `secret_hash` char(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '密钥 SHA-256 哈希（hex 小写），绝不存明文',
  `secret_created_at` datetime NOT NULL COMMENT '密钥创建时间',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL DEFAULT '' COMMENT '备注',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_user_code` (`user_code`) USING BTREE,
  KEY `idx_enabled` (`enabled`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='开放接口业务方';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sporttery_football_had_odds_record`
--

DROP TABLE IF EXISTS `sporttery_football_had_odds_record`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sporttery_football_had_odds_record` (
  `match_id` int NOT NULL COMMENT 'Sporttery 官方比赛ID',
  `release_time` datetime NOT NULL COMMENT '官网赔率发布时间（北京时间），由 updateDate 与 updateTime 合成',
  `win_odds` decimal(6,2) DEFAULT NULL COMMENT '胜赔，对应历史接口 h',
  `equal_odds` decimal(6,2) DEFAULT NULL COMMENT '平赔，对应历史接口 d',
  `lose_odds` decimal(6,2) DEFAULT NULL COMMENT '负赔，对应历史接口 a',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`match_id`,`release_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='竞彩足球胜平负历史赔率表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `bd_submit_batch`
--

DROP TABLE IF EXISTS `bd_submit_batch`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `bd_submit_batch` (
  `submit_id` int NOT NULL AUTO_INCREMENT COMMENT '提交到 v2 的批次编号',
  `batch_id` int DEFAULT NULL COMMENT '批次id ，关联批次表bd_batch主键',
  `business_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '业务类型 A1:奖期创建，A2 :导入赛果， A3: 追加比赛  B1:修改奖期创建,B2 :修改导入赛果，B3: 修改追加比赛,\r\nA4:导入赛事,A5:导入球队',
  `submit_title` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '标题',
  `submit_count` int NOT NULL COMMENT '数据量',
  `detail` json NOT NULL COMMENT '导出的json文件内容',
  `submit_type` int DEFAULT NULL COMMENT '提交方式  1线上 2线下',
  `submit_status` int DEFAULT NULL COMMENT '提交状态 0作废  1成功',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账号',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账号',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`submit_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=1330 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='数据文件提交记录表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_task`
--

DROP TABLE IF EXISTS `audit_task`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_task` (
  `task_id` int NOT NULL AUTO_INCREMENT COMMENT '任务ID',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `event_id` varchar(11) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '事件ID',
  `task_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '任务名称，暂存s_event.identity_data.eventName的值，后续可以考虑添加更多标识信息',
  `task_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '任务类型,比赛提前 比赛推迟 比赛中断 比赛取消 比赛腰斩 球队变更 赛果争议',
  `task_role` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '任务执行角色  management赛程管理角色、monitoring赛程监控角色',
  `confirm_result` int DEFAULT NULL COMMENT '任务确认结果 0 未确认 1 已确认  2 已解除',
  `confirm_time` datetime DEFAULT NULL COMMENT '确认时间',
  `confirm_account` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '确认账户',
  `task_status` int DEFAULT NULL COMMENT '任务状态 0待执行 1执行中 2已完成 3已取消 4失败',
  `attribution_desc` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '异常描述，可存放：取消原因等信息',
  `task_detail` json DEFAULT NULL COMMENT '任务执行步骤详情，不同任务类型taskType具有不同的结构',
  `task_remark` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '任务备注 记录用户对系统、人工填写的异常事件任务',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `attribution_title` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '异常原因',
  PRIMARY KEY (`task_id`,`rev`) USING BTREE,
  KEY `FK_rev` (`rev`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=128323 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `openapi_user_path_ratelimit`
--

DROP TABLE IF EXISTS `openapi_user_path_ratelimit`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `openapi_user_path_ratelimit` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '物理主键',
  `user_id` bigint unsigned NOT NULL COMMENT '业务方 ID',
  `path` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '接口路径',
  `strategy` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT 'QPS / FIXED_WINDOW / COOLDOWN',
  `limit_count` int NOT NULL COMMENT '阈值（QPS=每秒次数 / FIXED_WINDOW=窗口内次数 / COOLDOWN=不生效填 1）',
  `window_seconds` int NOT NULL DEFAULT '1' COMMENT 'FIXED_WINDOW 窗口秒数 / COOLDOWN 冷却秒数；QPS 此列无意义',
  `enabled` tinyint(1) NOT NULL DEFAULT '1' COMMENT '1=启用，0=停用',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL DEFAULT '' COMMENT '备注',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_user_path_strategy` (`user_id`,`path`,`strategy`) USING BTREE,
  KEY `idx_path` (`path`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='开放接口 user+path 限流策略';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_event_match_check`
--

DROP TABLE IF EXISTS `audit_event_match_check`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_event_match_check` (
  `check_id` int NOT NULL AUTO_INCREMENT COMMENT '审核ID',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `check_type` int NOT NULL COMMENT '审核资源类型 1 事件 2赛果',
  `check_source_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '事件id或比赛id',
  `check_result` int DEFAULT NULL COMMENT '审核结果 0 一致 1不一致',
  `check_status` int DEFAULT NULL COMMENT '审核状态 0待审核、1审核通过、2审核不通过',
  `check_channel` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '核实渠道: 联赛官网、当地媒体、俱乐部官网、官方社交媒体',
  `check_time` datetime DEFAULT NULL COMMENT '审核时间',
  `change_info` json DEFAULT NULL COMMENT '修改意见  赛果事件存json比分信息',
  `bd_matchup_home_team_id` int DEFAULT NULL COMMENT '北单赛程的比赛的主队id',
  `data_source_type` int DEFAULT NULL COMMENT '赛果审核人所选数据源来源（对齐 RelationDataSourceType：1 纳米 / 3 贝泰）',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账号',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账号',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`check_id`,`rev`) USING BTREE,
  KEY `FK_rev` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='审核表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_tx_competition`
--

DROP TABLE IF EXISTS `audit_tx_competition`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_tx_competition` (
  `competition_id` int NOT NULL COMMENT '赛事编号',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `zone_id` int DEFAULT NULL COMMENT '洲编号',
  `zone_name` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '洲名称',
  `country_id` int DEFAULT NULL COMMENT '国家编号',
  `country_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '国家名称',
  `logo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '国家logo地址',
  `competition_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '赛事全称',
  `competition_shortname` varchar(15) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛事简称',
  `name_en` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `color` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛事颜色',
  `competition_type` int DEFAULT NULL COMMENT '赛事类别  1杯赛; 2联赛',
  `current_season` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '当前赛季',
  `startdate` bigint DEFAULT NULL COMMENT '当前赛季开始时间',
  `enddate` bigint DEFAULT NULL COMMENT '当前赛季结束时间',
  `competition_system` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛制内容',
  `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`competition_id`,`rev`) USING BTREE,
  KEY `FK_rev` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin ROW_FORMAT=DYNAMIC COMMENT='同行足球赛事表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_beitai_football_match`
--

DROP TABLE IF EXISTS `audit_beitai_football_match`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_beitai_football_match` (
  `match_id` int NOT NULL COMMENT '比赛ID',
  `rev` int NOT NULL COMMENT '修订版本号（关联到 REVINFO 表）',
  `revtype` tinyint NOT NULL COMMENT '修订类型：0=新增(ADD), 1=修改(MOD), 2=删除(DEL)',
  `tournament_id` int DEFAULT NULL COMMENT '联赛/锦标赛ID',
  `season_id` int DEFAULT NULL COMMENT '赛季ID',
  `home_competitor_id` int DEFAULT NULL COMMENT '主队球队ID',
  `away_competitor_id` int DEFAULT NULL COMMENT '客队球队ID',
  `venue_id` int DEFAULT NULL COMMENT '球场ID',
  `home_score` int DEFAULT NULL COMMENT '主队比分',
  `away_score` int DEFAULT NULL COMMENT '客队比分',
  `home_half_score` int DEFAULT NULL COMMENT '主队半场比分 从live接口periods字段下获取，值为1时为上半场',
  `away_half_score` int DEFAULT NULL COMMENT '客队半场比分 从live接口periods字段下获取，值为1时为上半场',
  `home_normal_time_score` int DEFAULT NULL COMMENT '主队常规时间得分 从live接口matchinfo字段下获取',
  `away_normal_time_score` int DEFAULT NULL COMMENT '客队常规时间比分 从live接口matchinfo字段下获取',
  `penalties_home_score` int DEFAULT NULL COMMENT '点球大战主队进球',
  `penalties_away_score` int DEFAULT NULL COMMENT '点球大战客队进球',
  `winner_id` int DEFAULT NULL COMMENT '胜利球队ID',
  `status` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '比赛状态【live-进行中、abandoned-中断、cancelled-取消、closed-已关闭、ended-已结束、not_started-未开始、postponed-延期】',
  `live_match_status` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT 'live比赛状态 从live接口中获取',
  `match_status` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '比赛详细状态',
  `effective_match_status` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '有效比赛状态：live没有比赛时值等于status（从matchup赛程获取），存在live时比赛状态从live接口中获取等于live_match_status',
  `match_gtm8_time` datetime DEFAULT NULL,
  `match_local_time` datetime DEFAULT NULL,
  `weather_conditions` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '天气条件【bad-恶劣、good-良好、indoor-室内、medium-一般】',
  `weather_pitch` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '场地条件【bad-差、good-良好、medium-一般】',
  `round_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '轮次名称',
  `round_group` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '分组信息',
  `round_number` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '轮次编号',
  `match_number` int DEFAULT NULL COMMENT '比赛场序号（如世界杯第60场）',
  `phase` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '比赛阶段（如"regular season"-常规赛）',
  `neutral` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '是否中立场地【"true"-是、"false"-否】',
  `replaced_by` int DEFAULT NULL COMMENT '替补赛程ID（比赛延期或重新安排后的新比赛ID）',
  `home_virtual` int DEFAULT NULL COMMENT '主队是否占位球队【0-否、1-是】（赛程未确定时的临时占位）',
  `away_virtual` int DEFAULT NULL COMMENT '客队是否占位球队【0-否、1-是】（赛程未确定时的临时占位）',
  `resumetime` datetime DEFAULT NULL,
  `stage_order` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '阶段顺序',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '原记录更新时间',
  `coverage_scores` varchar(100) COLLATE utf8mb4_bin DEFAULT NULL COMMENT '比分更新方式：live 表示实时比分更新，post 表示赛后比分更新',
  PRIMARY KEY (`match_id`,`rev`) USING BTREE,
  KEY `idx_rev` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='贝泰足球比赛审计表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_toto_account`
--

DROP TABLE IF EXISTS `audit_toto_account`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_toto_account` (
  `account_id` int unsigned NOT NULL,
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账号',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账号',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `account` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `account_status` tinyint DEFAULT NULL,
  `account_status_changed_reason` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `account_type` tinyint DEFAULT NULL,
  `account_user` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `is_deleted` tinyint DEFAULT NULL,
  `last_password_change_time` datetime DEFAULT NULL,
  `password` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `two_factor_bind_status` tinyint DEFAULT NULL,
  `token_id` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `rdc_id` int DEFAULT NULL,
  PRIMARY KEY (`account_id`,`rev`) USING BTREE,
  KEY `FKl7p9ped43bgwanhr21l2vej6f` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_basketball_venue`
--

DROP TABLE IF EXISTS `nami_basketball_venue`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_basketball_venue` (
  `venue_id` int NOT NULL COMMENT '场馆id',
  `name_zh` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文名称',
  `name_zht` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语名称',
  `name_en` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `capacity` int DEFAULT NULL COMMENT '球场容量',
  `city` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '城市',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`venue_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米篮球场馆列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sporttery_basketball_league`
--

DROP TABLE IF EXISTS `sporttery_basketball_league`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sporttery_basketball_league` (
  `league_id` bigint NOT NULL COMMENT '官方联赛ID',
  `league_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '联赛简称',
  `league_full_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '联赛全称',
  `league_color` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '联赛配色',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`league_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='竞彩篮球联赛表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sporttery_basketball_wnm_odds`
--

DROP TABLE IF EXISTS `sporttery_basketball_wnm_odds`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sporttery_basketball_wnm_odds` (
  `match_id` int NOT NULL COMMENT 'Sporttery 官方比赛 ID，同时关联 sporttery_basketball_match.match_id',
  `collect_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '本次赔率采集时间',
  `gw_1_5_odds` decimal(6,2) DEFAULT NULL COMMENT '客胜分差 1-5 赔率，对应接口 WNM 的 l1',
  `gw_6_10_odds` decimal(6,2) DEFAULT NULL COMMENT '客胜分差 6-10 赔率，对应接口 WNM 的 l2',
  `gw_11_15_odds` decimal(6,2) DEFAULT NULL COMMENT '客胜分差 11-15 赔率，对应接口 WNM 的 l3',
  `gw_16_20_odds` decimal(6,2) DEFAULT NULL COMMENT '客胜分差 16-20 赔率，对应接口 WNM 的 l4',
  `gw_21_25_odds` decimal(6,2) DEFAULT NULL COMMENT '客胜分差 21-25 赔率，对应接口 WNM 的 l5',
  `gw_26plus_odds` decimal(6,2) DEFAULT NULL COMMENT '客胜分差 26+ 赔率，对应接口 WNM 的 l6',
  `hw_1_5_odds` decimal(6,2) DEFAULT NULL COMMENT '主胜分差 1-5 赔率，对应接口 WNM 的 w1',
  `hw_6_10_odds` decimal(6,2) DEFAULT NULL COMMENT '主胜分差 6-10 赔率，对应接口 WNM 的 w2',
  `hw_11_15_odds` decimal(6,2) DEFAULT NULL COMMENT '主胜分差 11-15 赔率，对应接口 WNM 的 w3',
  `hw_16_20_odds` decimal(6,2) DEFAULT NULL COMMENT '主胜分差 16-20 赔率，对应接口 WNM 的 w4',
  `hw_21_25_odds` decimal(6,2) DEFAULT NULL COMMENT '主胜分差 21-25 赔率，对应接口 WNM 的 w5',
  `hw_26plus_odds` decimal(6,2) DEFAULT NULL COMMENT '主胜分差 26+ 赔率，对应接口 WNM 的 w6',
  `int_single` int DEFAULT NULL COMMENT '是否允许单关：0 不允许，1 允许；没有返回时为空',
  `match_status` int DEFAULT NULL COMMENT '玩法对应比赛状态：1 开售，2 停售，3 已开奖',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`match_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='竞彩篮球胜分差最新赔率表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_american_football_deleted`
--

DROP TABLE IF EXISTS `nami_american_football_deleted`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_american_football_deleted` (
  `deleted_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '删除的数据类型 1:category 分类，2:team 球队，4:competition 赛事，5:stage 阶段，6:season 赛季，7:venue 场馆，8:match 比赛，9:player 运动员',
  `id` int NOT NULL COMMENT '删除的数据id',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`deleted_type`,`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米橄榄球删除数据列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `bd_game_draw`
--

DROP TABLE IF EXISTS `bd_game_draw`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `bd_game_draw` (
  `game_draw_id` int NOT NULL AUTO_INCREMENT COMMENT '奖期ID 自增',
  `draw_no` varchar(5) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '奖期编号 ，可为空，不能重复',
  `sale_begin_time` datetime NOT NULL COMMENT '开售时间',
  `sale_end_time` datetime NOT NULL COMMENT '停售时间',
  `draw_time` datetime NOT NULL COMMENT '开奖时间',
  `game1200` tinyint NOT NULL DEFAULT '0' COMMENT '单场竞猜 1为开售，0为不开售 默认0',
  `game1270` tinyint NOT NULL DEFAULT '0' COMMENT '胜负过关 1为开售，0为不开售 默认0',
  `game1260` tinyint NOT NULL DEFAULT '0' COMMENT '下半场比分 1为开售，0为不开售 默认0',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账号',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账号',
  PRIMARY KEY (`game_draw_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=101 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='北单奖期表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `event_match_check`
--

DROP TABLE IF EXISTS `event_match_check`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `event_match_check` (
  `check_id` int NOT NULL AUTO_INCREMENT COMMENT '审核ID',
  `check_type` int NOT NULL COMMENT '审核资源类型 1 事件 2赛果',
  `check_source_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '事件id或比赛id',
  `check_result` int DEFAULT NULL COMMENT '审核结果  0 待确认 1 已确认  2 已解除',
  `check_status` int DEFAULT NULL COMMENT '审核状态  0 未核实 1 已核实',
  `check_channel` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '核实渠道: 联赛官网、当地媒体、俱乐部官网、官方社交媒体',
  `check_time` datetime DEFAULT NULL COMMENT '审核时间',
  `change_info` json DEFAULT NULL COMMENT '修改意见  赛果事件存json比分信息',
  `bd_matchup_home_team_id` int DEFAULT NULL COMMENT '北单赛程的比赛的主队id',
  `data_source_type` int DEFAULT NULL COMMENT '赛果审核人所选数据源来源（对齐 RelationDataSourceType：1 纳米 / 3 贝泰）',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账号',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账号',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`check_id`) USING BTREE,
  KEY `idx_check_source_status` (`check_source_id`,`check_status`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=63444 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='审核表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_nami_basketball_stage`
--

DROP TABLE IF EXISTS `audit_nami_basketball_stage`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_nami_basketball_stage` (
  `stage_id` int NOT NULL COMMENT '阶段id',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `season_id` int DEFAULT NULL COMMENT '赛季id',
  `name_zh` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文名称',
  `name_zht` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语名称',
  `name_en` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `mode` int DEFAULT NULL COMMENT '比赛模式，1-积分赛、2-淘汰赛',
  `group_count` int DEFAULT NULL COMMENT '总组数',
  `round_count` int DEFAULT NULL COMMENT '总轮数',
  `order` int DEFAULT NULL COMMENT '排序，阶段的先后顺序',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`stage_id`,`rev`) USING BTREE,
  KEY `FK_rev` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin ROW_FORMAT=DYNAMIC COMMENT='纳米篮球获取阶段列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_american_football_competition`
--

DROP TABLE IF EXISTS `nami_american_football_competition`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_american_football_competition` (
  `competition_id` int NOT NULL COMMENT '赛事id',
  `category_id` int DEFAULT NULL COMMENT '分类id',
  `country_id` int DEFAULT NULL COMMENT '国家id',
  `uid` int DEFAULT NULL COMMENT '纳米赛事合并对应ID',
  `name_zh` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文名称',
  `name_en` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `name_zht` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语名称',
  `short_name_zh` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文简称',
  `short_name_en` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文简称',
  `short_name_zht` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语简称',
  `logo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛事logo',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`competition_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米橄榄球赛事列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sporttery_football_hhad_odds`
--

DROP TABLE IF EXISTS `sporttery_football_hhad_odds`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sporttery_football_hhad_odds` (
  `match_id` int NOT NULL COMMENT 'Sporttery 官方比赛 ID，同时关联 sporttery_football_match.match_id',
  `collect_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '本次赔率采集时间',
  `win_odds` decimal(6,2) DEFAULT NULL COMMENT '让球胜赔，对应接口 HHAD 的 h',
  `equal_odds` decimal(6,2) DEFAULT NULL COMMENT '让球平赔，对应接口 HHAD 的 d',
  `lose_odds` decimal(6,2) DEFAULT NULL COMMENT '让球负赔，对应接口 HHAD 的 a',
  `int_single` int DEFAULT NULL COMMENT '是否允许单关：0 不允许，1 允许；没有返回时为空',
  `match_status` int DEFAULT NULL COMMENT '玩法对应比赛状态：1 开售，2 停售，3 已开奖',
  `handicap` decimal(3,1) DEFAULT NULL COMMENT '让球数，对应接口 HHAD 的 goalLine 或 goalLineValue',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`match_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='竞彩足球让球胜平负最新赔率表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_nami_basketball_competition`
--

DROP TABLE IF EXISTS `audit_nami_basketball_competition`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_nami_basketball_competition` (
  `competition_id` int NOT NULL COMMENT '赛事id',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `category_id` int DEFAULT NULL COMMENT '分类id',
  `country_id` int DEFAULT NULL COMMENT '国家id',
  `name_zh` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文名称',
  `name_zht` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语名称',
  `name_en` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `short_name_zh` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文简称',
  `short_name_zht` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语简称',
  `short_name_en` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文简称',
  `logo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛事logo',
  `type` int DEFAULT NULL COMMENT '赛事类型，0-未知、1-联赛、2-杯赛',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`competition_id`,`rev`) USING BTREE,
  KEY `FK_rev` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米篮球赛事列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `beitai_football_match`
--

DROP TABLE IF EXISTS `beitai_football_match`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `beitai_football_match` (
  `match_id` int NOT NULL COMMENT '比赛ID',
  `tournament_id` int DEFAULT NULL COMMENT '联赛/锦标赛ID',
  `season_id` int DEFAULT NULL COMMENT '赛季ID',
  `home_competitor_id` int DEFAULT NULL COMMENT '主队球队ID',
  `away_competitor_id` int DEFAULT NULL COMMENT '客队球队ID',
  `venue_id` int DEFAULT NULL COMMENT '球场ID',
  `home_score` int DEFAULT NULL COMMENT '主队比分',
  `away_score` int DEFAULT NULL COMMENT '客队比分',
  `home_half_score` int DEFAULT NULL COMMENT '主队半场比分 从live接口periods字段下获取，值为1时为上半场',
  `away_half_score` int DEFAULT NULL COMMENT '客队半场比分 从live接口periods字段下获取，值为1时为上半场',
  `home_normal_time_score` int DEFAULT NULL COMMENT '主队常规时间得分 从live接口matchinfo字段下获取',
  `away_normal_time_score` int DEFAULT NULL COMMENT '客队常规时间比分 从live接口matchinfo字段下获取',
  `penalties_home_score` int DEFAULT NULL COMMENT '点球大战主队进球',
  `penalties_away_score` int DEFAULT NULL COMMENT '点球大战客队进球',
  `winner_id` int DEFAULT NULL COMMENT '胜利球队ID',
  `status` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '比赛状态【live-进行中、abandoned-中断、cancelled-取消、closed-已关闭、ended-已结束、not_started-未开始、postponed-延期】',
  `live_match_status` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT 'live比赛状态 live接口能获取到比赛信息时，该值才有值',
  `match_status` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '比赛详细状态',
  `effective_match_status` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '有效比赛状态：live接口没有比赛信息该值等于status（从matchup赛程获取），live接口有比赛信息时比赛状态从live接口中获取等于live_match_status',
  `match_gtm8_time` datetime DEFAULT NULL COMMENT '北京比赛时间（GMT+8）',
  `match_local_time` datetime DEFAULT NULL COMMENT '比赛当地时间（北美东部时间）',
  `weather_conditions` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '天气条件【bad-恶劣、good-良好、indoor-室内、medium-一般】',
  `weather_pitch` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '场地条件【bad-差、good-良好、medium-一般】',
  `round_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '轮次名称',
  `round_group` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '分组信息',
  `round_number` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '轮次编号',
  `match_number` int DEFAULT NULL COMMENT '比赛场序号（如世界杯第60场）',
  `phase` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '比赛阶段（如"regular season"-常规赛）',
  `neutral` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '是否中立场地【"true"-是、"false"-否】',
  `replaced_by` int DEFAULT NULL COMMENT '替补赛程ID（比赛延期或重新安排后的新比赛ID）',
  `home_virtual` int DEFAULT NULL COMMENT '主队是否占位球队【0-否、1-是】（赛程未确定时的临时占位）',
  `away_virtual` int DEFAULT NULL COMMENT '客队是否占位球队【0-否、1-是】（赛程未确定时的临时占位）',
  `resumetime` datetime DEFAULT NULL COMMENT '延期比赛的恢复时间',
  `stage_order` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '阶段顺序',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `coverage_scores` varchar(100) COLLATE utf8mb4_bin DEFAULT NULL COMMENT '比分更新方式：live 表示实时比分更新，post 表示赛后比分更新',
  PRIMARY KEY (`match_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='贝泰足球比赛表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `m_competition_blacklist`
--

DROP TABLE IF EXISTS `m_competition_blacklist`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `m_competition_blacklist` (
  `competition_blacklist_id` int NOT NULL AUTO_INCREMENT COMMENT '赛事黑名单ID 自增',
  `manual_competition_id` int NOT NULL COMMENT '人工录入的赛事id',
  `reason` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '添加原因',
  `del_reason` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '移除原因',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账号',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账号',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`competition_blacklist_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='赛事黑名单表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `bd_batch_matchup_draw`
--

DROP TABLE IF EXISTS `bd_batch_matchup_draw`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `bd_batch_matchup_draw` (
  `batch_matchup_id` int NOT NULL COMMENT '批次比赛id 同bd_batch_matchup主键',
  `batch_id_match_result` int NOT NULL COMMENT '赛果批次id',
  `match_id` int NOT NULL COMMENT '比赛id',
  `game_draw_id` int NOT NULL COMMENT '奖期id',
  `matchup_unique_no` varchar(21) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '比赛唯一编号',
  `draw_game_list` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '开奖的游戏列表，逗号分割 如200,210,230,240,250,260,270',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账号',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账号',
  PRIMARY KEY (`batch_matchup_id`,`draw_game_list`,`batch_id_match_result`) USING BTREE,
  KEY `batch_matchup_id` (`batch_matchup_id`) USING BTREE,
  KEY `batch_id_match_result` (`batch_id_match_result`) USING BTREE,
  KEY `matchup_unique_no` (`matchup_unique_no`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='北单批次开奖表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `beitai_football_stage`
--

DROP TABLE IF EXISTS `beitai_football_stage`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `beitai_football_stage` (
  `stage_id` int NOT NULL,
  `season_id` int NOT NULL,
  `stage_order` int DEFAULT NULL,
  `phase_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `start_date` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `end_date` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `stage_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `season_year` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`stage_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='贝泰足球阶段表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_basketball_competition_rule`
--

DROP TABLE IF EXISTS `nami_basketball_competition_rule`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_basketball_competition_rule` (
  `competition_rule_id` int NOT NULL COMMENT '赛制id',
  `competition_id` int DEFAULT NULL COMMENT '赛事id',
  `season_ids` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛季id列表,逗号分割',
  `text` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛制说明',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`competition_rule_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米篮球赛事赛制列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_r_sporttery_team_data`
--

DROP TABLE IF EXISTS `audit_r_sporttery_team_data`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_r_sporttery_team_data` (
  `relation_id` bigint NOT NULL AUTO_INCREMENT COMMENT '关联ID',
  `rev` int NOT NULL COMMENT 'Envers 修订号，业务关联共享 revinfo.rev',
  `revtype` tinyint DEFAULT NULL COMMENT '操作类型：0新增、1修改、2删除',
  `source_type` tinyint NOT NULL COMMENT '数据源 4=竞彩',
  `sport_id` int NOT NULL COMMENT '运动项目ID',
  `sporttery_team_id` bigint NOT NULL COMMENT '竞彩球队ID',
  `manual_team_id` int NOT NULL COMMENT '标准化球队ID m_team.team_id',
  `create_account` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `update_account` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`relation_id`,`rev`) USING BTREE,
  KEY `idx_audit_r_sporttery_team_data` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='竞彩球队与标准化球队匹配关系审计表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_football_match_analysis`
--

DROP TABLE IF EXISTS `nami_football_match_analysis`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_football_match_analysis` (
  `match_id` int NOT NULL COMMENT '比赛id',
  `match_info` json DEFAULT NULL COMMENT '当前比赛数据',
  `history_vs` json DEFAULT NULL COMMENT '历史交锋',
  `history_home` json DEFAULT NULL COMMENT '主队近期战绩',
  `history_away` json DEFAULT NULL COMMENT '客队近期战绩',
  `future_vs` json DEFAULT NULL COMMENT '未来交锋赛程',
  `future_home` json DEFAULT NULL COMMENT '主队近期赛程',
  `future_away` json DEFAULT NULL COMMENT '客队近期赛程',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`match_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米足球比赛分析数据';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `beitai_football_tournament`
--

DROP TABLE IF EXISTS `beitai_football_tournament`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `beitai_football_tournament` (
  `tournament_id` int NOT NULL,
  `current_season_year` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `tournament_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `tournament_full_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `current_season_id` int DEFAULT NULL,
  `start_date` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `end_date` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `parent_id` int DEFAULT NULL,
  `category_id` int DEFAULT NULL,
  `category_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `gender` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `tournament_name_en` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `current_season_name_en` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`tournament_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='贝泰足球赛事表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `task_operation_record`
--

DROP TABLE IF EXISTS `task_operation_record`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `task_operation_record` (
  `operation_record_id` int NOT NULL AUTO_INCREMENT COMMENT '变更记录ID',
  `task_id` int NOT NULL COMMENT '任务ID',
  `event_id` varchar(11) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '事件ID',
  `match_id` int NOT NULL COMMENT '比赛id',
  `matchup_unique_no` json DEFAULT NULL COMMENT '北单比赛唯一编号',
  `task_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '任务类型,比赛提前 比赛推迟 比赛中断 比赛取消 比赛腰斩 球队变更 赛果争议',
  `change_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '变更类型,调整停售时间、开奖延后、退票、争议赛果、按实际结果开奖',
  `invalid_status` int DEFAULT NULL COMMENT '有效状态 0 有效 1 无效，当前变更记录是否被中心或运营人员采纳，当不采纳时又导出过变更单后，可以设置为无效',
  `change_status` int DEFAULT NULL COMMENT '变更状态 0待执行 1执行中 2已完成',
  `submit_status` int DEFAULT NULL COMMENT '提交状态 0 未提交 1 已提交，提交是否导出过变更单',
  `change_info` json DEFAULT NULL COMMENT '任务变更详情，根据change_type存储不同的结构',
  `operation_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '操作人',
  `operation_time` datetime DEFAULT NULL COMMENT '操作时间',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`operation_record_id`) USING BTREE,
  KEY `ind_event_id` (`event_id`) USING BTREE,
  KEY `ind_match_id` (`match_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=299 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='任务操作记录表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `m_team_blacklist`
--

DROP TABLE IF EXISTS `m_team_blacklist`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `m_team_blacklist` (
  `team_blacklist_id` int NOT NULL AUTO_INCREMENT COMMENT '球队黑名单ID 自增',
  `manual_team_id` int NOT NULL COMMENT '人工录入的球队id',
  `reason` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '添加原因',
  `del_reason` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '移除原因',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账号',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账号',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`team_blacklist_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=142 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='球队黑名单表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_m_match`
--

DROP TABLE IF EXISTS `audit_m_match`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_m_match` (
  `match_id` int NOT NULL COMMENT '比赛id',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `sport_id` int NOT NULL COMMENT '运动项目id',
  `season_id` int NOT NULL COMMENT '赛季id',
  `competition_id` int NOT NULL COMMENT '赛事id',
  `home_team_id` int NOT NULL COMMENT '主队id',
  `away_team_id` int NOT NULL COMMENT '客队id',
  `match_status` int NOT NULL COMMENT '比赛状态 见字典表同名',
  `match_stage` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '阶段',
  `match_group` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '分组',
  `match_round` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '轮次',
  `match_time` datetime NOT NULL COMMENT '开赛时间',
  `home_score_half` int DEFAULT NULL COMMENT '主队半场比分',
  `away_score_half` int DEFAULT NULL COMMENT '客队半场比分',
  `home_score` int DEFAULT NULL COMMENT '主队比分',
  `away_score` int DEFAULT NULL COMMENT '客队比分',
  `nami_id_match_status` int NOT NULL DEFAULT '0' COMMENT '纳米匹配状态 0未匹配 1匹配 默认0',
  `beitai_id_match_status` int NOT NULL DEFAULT '0' COMMENT '贝泰匹配状态 0未匹配 1匹配 默认0',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账户',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账户',
  PRIMARY KEY (`match_id`,`rev`) USING BTREE,
  KEY `FKpff5i3f8x403yj9d55adeqwum` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `toto_operation_record`
--

DROP TABLE IF EXISTS `toto_operation_record`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `toto_operation_record` (
  `record_id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '记录 ID',
  `operation_module` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '操作模块',
  `operation_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '操作类型',
  `operation_code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '业务操作唯一标识',
  `result` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '操作结果',
  `account_user` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '操作用户',
  `account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '操作账号',
  `rdc_id` int DEFAULT NULL COMMENT '分中心ID',
  `rdc_name` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '分中心名称',
  `operation_time` datetime DEFAULT NULL COMMENT '操作时间',
  `operation_role_id` int DEFAULT NULL COMMENT '操作角色id',
  `operation_role_name` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '操作角色名',
  `operation_key1` varchar(4000) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '日志关键字1',
  `operation_key2` varchar(4000) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '日志关键字2',
  `operation_key3` varchar(4000) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '日志关键字3',
  `ipaddress` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT 'IP地址',
  `error_detail` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '错误信息记录',
  PRIMARY KEY (`record_id`) USING BTREE,
  KEY `ind_toto_operation_record` (`operation_time`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=184756 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='用户操作记录表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_football_competition_rule`
--

DROP TABLE IF EXISTS `nami_football_competition_rule`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_football_competition_rule` (
  `competition_rule_id` int NOT NULL COMMENT '赛制id',
  `competition_id` int DEFAULT NULL COMMENT '赛事id',
  `season_ids` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛季id列表,逗号分割',
  `text` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛制说明',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`competition_rule_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米足球赛事赛制列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_football_europe_odds_company`
--

DROP TABLE IF EXISTS `nami_football_europe_odds_company`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_football_europe_odds_company` (
  `company_id` int NOT NULL COMMENT '公司id',
  `name_zh` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文名称',
  `name_en` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`company_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米足球百欧指数公司列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sport_radar_prematch_asian_handicap_odds`
--

DROP TABLE IF EXISTS `sport_radar_prematch_asian_handicap_odds`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sport_radar_prematch_asian_handicap_odds` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `sport_event_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '比赛数字ID',
  `market_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '盘口ID',
  `market_name` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '盘口名称',
  `handicap_value` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '让球值',
  `book_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '博彩公司ID',
  `book_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '博彩公司名称',
  `home_odds_american` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '主队让球美式赔率',
  `home_odds_decimal` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '主队让球小数赔率',
  `draw_odds_american` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '让球平局美式赔率',
  `draw_odds_decimal` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '让球平局小数赔率',
  `away_odds_american` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '客队让球美式赔率',
  `away_odds_decimal` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '客队让球小数赔率',
  `collected_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '赔率采集时间',
  `create_time` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '记录创建时间',
  `update_time` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '记录更新时间',
  `initial_handicap_value` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT 'Sportradar官方初盘让球值',
  `initial_home_odds_american` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT 'Sportradar官方初盘主队让球美式赔率',
  `initial_home_odds_decimal` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT 'Sportradar官方初盘主队让球小数赔率',
  `initial_draw_odds_american` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT 'Sportradar官方初盘让球平局美式赔率',
  `initial_draw_odds_decimal` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT 'Sportradar官方初盘让球平局小数赔率',
  `initial_away_odds_american` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT 'Sportradar官方初盘客队让球美式赔率',
  `initial_away_odds_decimal` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT 'Sportradar官方初盘客队让球小数赔率',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_sr_asian_event_book_handicap` (`sport_event_id`,`market_id`,`book_id`,`handicap_value`,`collected_at`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=1190804 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Sportradar亚盘让球赔率变更快照';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `openapi_user_path`
--

DROP TABLE IF EXISTS `openapi_user_path`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `openapi_user_path` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '物理主键',
  `user_id` bigint unsigned NOT NULL COMMENT '业务方 ID（关联 t_openapi_user.id）',
  `path` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '接口路径（如 /openapi/v1/football/match/list）',
  `enabled` tinyint(1) NOT NULL DEFAULT '1' COMMENT '1=启用，0=停用',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL DEFAULT '' COMMENT '备注',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_user_path` (`user_id`,`path`) USING BTREE,
  KEY `idx_path` (`path`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='开放接口 user+path 权限';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_m_match_remark`
--

DROP TABLE IF EXISTS `audit_m_match_remark`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_m_match_remark` (
  `remark_id` int NOT NULL COMMENT '备注 id',
  `remark_type` int NOT NULL COMMENT '备注类型 1 赛程  2 让球 3 比赛监控',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `match_id` int NOT NULL COMMENT '比赛id',
  `remark` varchar(300) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '备注',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账号',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账号',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`remark_id`,`rev`) USING BTREE,
  KEY `FK_rev` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='比赛备注表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_m_team`
--

DROP TABLE IF EXISTS `audit_m_team`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_m_team` (
  `team_id` int NOT NULL COMMENT '球队id',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `sport_id` int NOT NULL COMMENT '运动项目id',
  `country` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '国家/地区',
  `name_zh` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '球队全称',
  `short_name_zh` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '球队简称',
  `bd_team_name` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '北单全称',
  `bd_team_short_name` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '北单简称',
  `foreign_name` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '官网赛程外文名称',
  `official_web_en_name` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '官网赛程英文名称',
  `name_en` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文全称',
  `nami_id_match_status` tinyint NOT NULL DEFAULT '0' COMMENT '纳米匹配状态 0未匹配 1匹配 默认0',
  `beitai_id_match_status` tinyint NOT NULL DEFAULT '0' COMMENT '贝泰匹配状态 0未匹配 1匹配 默认0',
  `naming_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '命名类型',
  `naming_reason` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '命名原因',
  `jc_name` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '竞彩全称',
  `jc_short_name` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '竞彩简称',
  `ctzc_short_name` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '传统足彩简称',
  `dqd_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '懂球帝名称',
  `logo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球队logo',
  `official_web` varchar(300) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '官方网站',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账户',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账户',
  PRIMARY KEY (`team_id`,`rev`) USING BTREE,
  KEY `FKpff5i3f8x403yj9d55adeqwum` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_ice_hockey_category`
--

DROP TABLE IF EXISTS `nami_ice_hockey_category`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_ice_hockey_category` (
  `category_id` int NOT NULL COMMENT '分类id',
  `name_zh` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文名称',
  `name_en` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `name_zht` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语名称',
  `country_id` int DEFAULT NULL COMMENT '国家id',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`category_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米冰球分类列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_football_stage`
--

DROP TABLE IF EXISTS `nami_football_stage`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_football_stage` (
  `stage_id` int NOT NULL COMMENT '阶段id',
  `season_id` int DEFAULT NULL COMMENT '赛季id',
  `name_zh` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文名称',
  `name_zht` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语名称',
  `name_en` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `mode` int DEFAULT NULL COMMENT '比赛模式，1-积分赛、2-淘汰赛',
  `group_count` int DEFAULT NULL COMMENT '总组数',
  `round_count` int DEFAULT NULL COMMENT '总轮数',
  `stage_order` int DEFAULT NULL COMMENT '排序，阶段的先后顺序',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`stage_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米足球获取阶段列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `beitai_football_match_live`
--

DROP TABLE IF EXISTS `beitai_football_match_live`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `beitai_football_match_live` (
  `match_id` int NOT NULL COMMENT '比赛ID - 主键',
  `tournament_id` int DEFAULT NULL COMMENT '联赛ID',
  `season_id` int DEFAULT NULL COMMENT '赛季ID',
  `season_year` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛季信息',
  `match_gtm8_time` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '北京比赛时间',
  `match_local_time` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT 'UTC比赛时间',
  `status` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '比赛状态',
  `match_status` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '比赛详细状态，来自 live/info.matchinfo.matchstatus',
  `home_competitor_id` int DEFAULT NULL COMMENT '主队ID',
  `away_competitor_id` int DEFAULT NULL COMMENT '客队ID',
  `home_competitor_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '主队名',
  `away_competitor_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '客队名',
  `home_probability` decimal(10,2) DEFAULT NULL COMMENT '主队胜率',
  `away_probability` decimal(10,2) DEFAULT NULL COMMENT '客队胜率',
  `draw_probability` decimal(10,2) DEFAULT NULL COMMENT '平局概率',
  `home_score` int DEFAULT NULL COMMENT '主队比分',
  `away_score` int DEFAULT NULL COMMENT '客队比分',
  `home_normal_time_score` int DEFAULT NULL COMMENT '主队常规时间得分',
  `away_normal_time_score` int DEFAULT NULL COMMENT '客队常规时间得分',
  `winner_id` int DEFAULT NULL COMMENT '胜利球队ID',
  `venue_id` int DEFAULT NULL COMMENT '场馆ID',
  `venue_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球场名',
  `venue_city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球场所在城市',
  `venue_capacity` int DEFAULT NULL COMMENT '可容纳人数',
  `venue_country_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球场所在国家',
  `venue_map_coordinates` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球场坐标',
  `attendance` int DEFAULT NULL COMMENT '观众人数',
  `weather_pitch` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '天气pitch',
  `weather_conditions` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '天气conditions',
  `neutral` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '是否为中立场地',
  `stage_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '阶段类型(league,cup)',
  `match_clock` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '比赛进行时间（赛中有值）',
  `stoppage_clock` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '实际伤停补时时间（赛中有值）',
  `stoppage_clock_announced` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '官方宣布的伤停补时时间（赛中有值）',
  `referee_id` int DEFAULT NULL COMMENT '裁判ID',
  `referee_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '裁判名',
  `first_assistant_referee_id` int DEFAULT NULL COMMENT '第一助理裁判ID',
  `first_assistant_referee_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '第一助理裁判',
  `second_assistant_referee_id` int DEFAULT NULL COMMENT '第二助理裁判ID',
  `second_assistant_referee_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '第二助理裁判',
  `fourth_official_id` int DEFAULT NULL COMMENT '第四官员ID',
  `fourth_official_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '第四官员',
  `video_assistant_referee_id` int DEFAULT NULL COMMENT '视频助理裁判ID',
  `video_assistant_referee_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '视频助理裁判',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`match_id`) USING BTREE,
  KEY `idx_tournament_id` (`tournament_id`) USING BTREE,
  KEY `idx_season_id` (`season_id`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE,
  KEY `idx_match_gtm8_time` (`match_gtm8_time`) USING BTREE,
  KEY `idx_home_competitor_id` (`home_competitor_id`) USING BTREE,
  KEY `idx_away_competitor_id` (`away_competitor_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='北泰足球直播比赛信息表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_toto_account_role`
--

DROP TABLE IF EXISTS `audit_toto_account_role`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_toto_account_role` (
  `account_role_id` int unsigned NOT NULL,
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账号',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账号',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `account_id` int unsigned DEFAULT NULL,
  `role_id` int DEFAULT NULL,
  `system_id` int DEFAULT NULL,
  PRIMARY KEY (`account_role_id`,`rev`) USING BTREE,
  KEY `fk_1` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `beitai_football_standing_snapshot`
--

DROP TABLE IF EXISTS `beitai_football_standing_snapshot`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `beitai_football_standing_snapshot` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `season_id` bigint NOT NULL COMMENT '赛季ID',
  `tournament_id` int NOT NULL COMMENT '贝泰赛事ID',
  `group_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '分组名，上游为 NULL 时保留 NULL',
  `group_id` int DEFAULT NULL COMMENT '贝泰物理分组ID，来源于上游 groupid；多阶段赛事区分物理分组，单阶段为 NULL',
  `standing_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL DEFAULT 'TOTAL' COMMENT 'TOTAL/HOME/AWAY',
  `team_count` int NOT NULL DEFAULT '0' COMMENT '球队数量（系统计算，完整性校验用）',
  `team_data` json NOT NULL COMMENT '所有球队数据快照（事实源）',
  `snapshot_hash` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT 'team_data 的 SHA-256 哈希',
  `snapshot_time` bigint NOT NULL COMMENT '快照时间戳（毫秒）',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_beitai_football_latest` (`season_id`,`tournament_id`,`standing_type`,`group_id`,`group_name`,`snapshot_time` DESC) USING BTREE,
  KEY `idx_beitai_football_dimension_hash` (`season_id`,`tournament_id`,`standing_type`,`group_id`,`group_name`,`snapshot_hash`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=9190 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='贝泰足球积分榜变更快照（主表，JSON 事实源）';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sporttery_football_crs_odds_record`
--

DROP TABLE IF EXISTS `sporttery_football_crs_odds_record`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sporttery_football_crs_odds_record` (
  `match_id` int NOT NULL COMMENT 'Sporttery 官方比赛 ID',
  `release_time` datetime NOT NULL COMMENT '官网赔率发布时间（北京时间），由 updateDate 与 updateTime 合成',
  `1_0` decimal(6,2) DEFAULT NULL COMMENT '比分 1:0 赔率，对应历史接口 s01s00',
  `2_0` decimal(6,2) DEFAULT NULL COMMENT '比分 2:0 赔率，对应历史接口 s02s00',
  `2_1` decimal(6,2) DEFAULT NULL COMMENT '比分 2:1 赔率，对应历史接口 s02s01',
  `3_0` decimal(6,2) DEFAULT NULL COMMENT '比分 3:0 赔率，对应历史接口 s03s00',
  `3_1` decimal(6,2) DEFAULT NULL COMMENT '比分 3:1 赔率，对应历史接口 s03s01',
  `3_2` decimal(6,2) DEFAULT NULL COMMENT '比分 3:2 赔率，对应历史接口 s03s02',
  `4_0` decimal(6,2) DEFAULT NULL COMMENT '比分 4:0 赔率，对应历史接口 s04s00',
  `4_1` decimal(6,2) DEFAULT NULL COMMENT '比分 4:1 赔率，对应历史接口 s04s01',
  `4_2` decimal(6,2) DEFAULT NULL COMMENT '比分 4:2 赔率，对应历史接口 s04s02',
  `5_0` decimal(6,2) DEFAULT NULL COMMENT '比分 5:0 赔率，对应历史接口 s05s00',
  `5_1` decimal(6,2) DEFAULT NULL COMMENT '比分 5:1 赔率，对应历史接口 s05s01',
  `5_2` decimal(6,2) DEFAULT NULL COMMENT '比分 5:2 赔率，对应历史接口 s05s02',
  `win_else` decimal(6,2) DEFAULT NULL COMMENT '胜其他赔率，对应历史接口 s-1sh',
  `0_0` decimal(6,2) DEFAULT NULL COMMENT '比分 0:0 赔率，对应历史接口 s00s00',
  `1_1` decimal(6,2) DEFAULT NULL COMMENT '比分 1:1 赔率，对应历史接口 s01s01',
  `2_2` decimal(6,2) DEFAULT NULL COMMENT '比分 2:2 赔率，对应历史接口 s02s02',
  `3_3` decimal(6,2) DEFAULT NULL COMMENT '比分 3:3 赔率，对应历史接口 s03s03',
  `equal_else` decimal(6,2) DEFAULT NULL COMMENT '平其他赔率，对应历史接口 s-1sd',
  `0_1` decimal(6,2) DEFAULT NULL COMMENT '比分 0:1 赔率，对应历史接口 s00s01',
  `0_2` decimal(6,2) DEFAULT NULL COMMENT '比分 0:2 赔率，对应历史接口 s00s02',
  `1_2` decimal(6,2) DEFAULT NULL COMMENT '比分 1:2 赔率，对应历史接口 s01s02',
  `0_3` decimal(6,2) DEFAULT NULL COMMENT '比分 0:3 赔率，对应历史接口 s00s03',
  `1_3` decimal(6,2) DEFAULT NULL COMMENT '比分 1:3 赔率，对应历史接口 s01s03',
  `2_3` decimal(6,2) DEFAULT NULL COMMENT '比分 2:3 赔率，对应历史接口 s02s03',
  `0_4` decimal(6,2) DEFAULT NULL COMMENT '比分 0:4 赔率，对应历史接口 s00s04',
  `1_4` decimal(6,2) DEFAULT NULL COMMENT '比分 1:4 赔率，对应历史接口 s01s04',
  `2_4` decimal(6,2) DEFAULT NULL COMMENT '比分 2:4 赔率，对应历史接口 s02s04',
  `0_5` decimal(6,2) DEFAULT NULL COMMENT '比分 0:5 赔率，对应历史接口 s00s05',
  `1_5` decimal(6,2) DEFAULT NULL COMMENT '比分 1:5 赔率，对应历史接口 s01s05',
  `2_5` decimal(6,2) DEFAULT NULL COMMENT '比分 2:5 赔率，对应历史接口 s02s05',
  `lose_else` decimal(6,2) DEFAULT NULL COMMENT '负其他赔率，对应历史接口 s-1sa',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`match_id`,`release_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='竞彩足球比分历史赔率表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sporttery_football_ttg_odds`
--

DROP TABLE IF EXISTS `sporttery_football_ttg_odds`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sporttery_football_ttg_odds` (
  `match_id` int NOT NULL COMMENT 'Sporttery 官方比赛 ID，同时关联 sporttery_football_match.match_id',
  `collect_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '本次赔率采集时间',
  `zero` decimal(6,2) DEFAULT NULL COMMENT '进球数 0 球赔率，对应接口 s0',
  `one` decimal(6,2) DEFAULT NULL COMMENT '进球数 1 球赔率，对应接口 s1',
  `two` decimal(6,2) DEFAULT NULL COMMENT '进球数 2 球赔率，对应接口 s2',
  `three` decimal(6,2) DEFAULT NULL COMMENT '进球数 3 球赔率，对应接口 s3',
  `four` decimal(6,2) DEFAULT NULL COMMENT '进球数 4 球赔率，对应接口 s4',
  `five` decimal(6,2) DEFAULT NULL COMMENT '进球数 5 球赔率，对应接口 s5',
  `six` decimal(6,2) DEFAULT NULL COMMENT '进球数 6 球赔率，对应接口 s6',
  `seven` decimal(6,2) DEFAULT NULL COMMENT '进球数 7+ 球赔率，对应接口 s7',
  `int_single` int DEFAULT NULL COMMENT '是否允许单关：0 不允许，1 允许；没有返回时为空',
  `match_status` int DEFAULT NULL COMMENT '玩法对应比赛状态：1 开售，2 停售，3 已开奖',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`match_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='竞彩足球总进球最新赔率表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_basketball_country`
--

DROP TABLE IF EXISTS `nami_basketball_country`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_basketball_country` (
  `country_id` int NOT NULL COMMENT '国家id',
  `category_id` int DEFAULT NULL COMMENT '分类id',
  `name_zh` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文名称',
  `name_zht` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语名称',
  `name_en` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `logo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '国家logo',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`country_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米篮球国家列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sporttery_basketball_mnl_odds`
--

DROP TABLE IF EXISTS `sporttery_basketball_mnl_odds`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sporttery_basketball_mnl_odds` (
  `match_id` int NOT NULL COMMENT 'Sporttery 官方比赛 ID，同时关联 sporttery_basketball_match.match_id',
  `collect_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '本次赔率采集时间',
  `host_lose_odds` decimal(6,2) DEFAULT NULL COMMENT '主负赔率，对应接口 MNL 的 a',
  `host_win_odds` decimal(6,2) DEFAULT NULL COMMENT '主胜赔率，对应接口 MNL 的 h',
  `int_single` int DEFAULT NULL COMMENT '是否允许单关：0 不允许，1 允许；没有返回时为空',
  `match_status` int DEFAULT NULL COMMENT '玩法对应比赛状态：1 开售，2 停售，3 已开奖',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`match_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='竞彩篮球胜负最新赔率表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `r_sporttery_team_data`
--

DROP TABLE IF EXISTS `r_sporttery_team_data`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `r_sporttery_team_data` (
  `relation_id` bigint NOT NULL AUTO_INCREMENT COMMENT '关联ID',
  `source_type` tinyint NOT NULL COMMENT '数据源 4=竞彩',
  `sport_id` int NOT NULL COMMENT '运动项目ID',
  `sporttery_team_id` bigint NOT NULL COMMENT '竞彩球队ID',
  `manual_team_id` int NOT NULL COMMENT '标准化球队ID m_team.team_id',
  `create_account` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `update_account` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`relation_id`) USING BTREE,
  UNIQUE KEY `uk_std_team` (`sporttery_team_id`,`sport_id`,`manual_team_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='竞彩球队与标准化球队匹配关系';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `toto_permission`
--

DROP TABLE IF EXISTS `toto_permission`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `toto_permission` (
  `permission_id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '权限ID',
  `permission_type` tinyint NOT NULL COMMENT '权限类型  0不可人工分配，1可以人工分配',
  `level1` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '一级权限',
  `level1_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '一级权限名称',
  `level2` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '二级权限',
  `level2_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '二级权限名称',
  `level3` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '三级权限',
  `level3_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '三级权限名称',
  `system_id` int NOT NULL COMMENT '系统 ID',
  `is_deleted` tinyint NOT NULL COMMENT '删除状态 0 未删除 1删除',
  `urls` json DEFAULT NULL COMMENT '权限对应的服务资源',
  PRIMARY KEY (`permission_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=154 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='权限表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_ice_hockey_stage`
--

DROP TABLE IF EXISTS `nami_ice_hockey_stage`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_ice_hockey_stage` (
  `stage_id` int NOT NULL COMMENT '阶段id',
  `category_id` int DEFAULT NULL COMMENT '分类id',
  `kind` int DEFAULT NULL COMMENT '阶段类型枚举(0-13)',
  `competition_id` int DEFAULT NULL COMMENT '赛事id',
  `season_id` int DEFAULT NULL COMMENT '赛季id',
  `name_zh` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文名称',
  `name_en` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `name_zht` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语名称',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`stage_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米冰球阶段列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_football_standing_snapshot_item`
--

DROP TABLE IF EXISTS `nami_football_standing_snapshot_item`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_football_standing_snapshot_item` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `snapshot_id` bigint NOT NULL COMMENT '主表外键（普通索引，不建物理外键约束）',
  `season_id` bigint NOT NULL COMMENT '赛季ID（冗余）',
  `competition_id` int NOT NULL COMMENT '纳米赛事ID（冗余）',
  `tables_id` int NOT NULL COMMENT '纳米积分榜子表ID（冗余自主表）',
  `stage_id` int DEFAULT NULL COMMENT '纳米阶段ID（冗余自主表）',
  `conference` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '分区信息（冗余自主表）',
  `group_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '分组值（冗余自主表，来源于 tables[].group）',
  `snapshot_time` bigint NOT NULL COMMENT '快照时间（冗余，毫秒）',
  `team_id` bigint NOT NULL COMMENT '球队ID',
  `team_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '展示名快照；纳米 API 不返回 teamName 时保留 NULL',
  `position` int DEFAULT NULL COMMENT '总榜排名，对应 API 字段 position',
  `points` int DEFAULT NULL COMMENT '总榜积分，对应 API 字段 points',
  `deduct_points` int DEFAULT NULL COMMENT '扣除积分，对应 API 字段 deduct_points',
  `promotion_id` int DEFAULT NULL COMMENT '升降级ID，对应 API 字段 promotion_id',
  `total` int DEFAULT NULL COMMENT '总比赛场次，对应 API 字段 total',
  `won` int DEFAULT NULL COMMENT '总胜场，对应 API 字段 won',
  `draw` int DEFAULT NULL COMMENT '总平场，对应 API 字段 draw',
  `loss` int DEFAULT NULL COMMENT '总负场，对应 API 字段 loss',
  `goals` int DEFAULT NULL COMMENT '总进球，对应 API 字段 goals',
  `goals_against` int DEFAULT NULL COMMENT '总失球，对应 API 字段 goals_against',
  `goal_diff` int DEFAULT NULL COMMENT '总净胜球，对应 API 字段 goal_diff',
  `home_points` int DEFAULT NULL COMMENT '主场积分，对应 API 字段 home_points',
  `home_position` int DEFAULT NULL COMMENT '主场排名，对应 API 字段 home_position',
  `home_total` int DEFAULT NULL COMMENT '主场比赛场次，对应 API 字段 home_total',
  `home_won` int DEFAULT NULL COMMENT '主场胜场，对应 API 字段 home_won',
  `home_draw` int DEFAULT NULL COMMENT '主场平场，对应 API 字段 home_draw',
  `home_loss` int DEFAULT NULL COMMENT '主场负场，对应 API 字段 home_loss',
  `home_goals` int DEFAULT NULL COMMENT '主场进球，对应 API 字段 home_goals',
  `home_goals_against` int DEFAULT NULL COMMENT '主场失球，对应 API 字段 home_goals_against',
  `home_goal_diff` int DEFAULT NULL COMMENT '主场净胜球，对应 API 字段 home_goal_diff',
  `away_points` int DEFAULT NULL COMMENT '客场积分，对应 API 字段 away_points',
  `away_position` int DEFAULT NULL COMMENT '客场排名，对应 API 字段 away_position',
  `away_total` int DEFAULT NULL COMMENT '客场比赛场次，对应 API 字段 away_total',
  `away_won` int DEFAULT NULL COMMENT '客场胜场，对应 API 字段 away_won',
  `away_draw` int DEFAULT NULL COMMENT '客场平场，对应 API 字段 away_draw',
  `away_loss` int DEFAULT NULL COMMENT '客场负场，对应 API 字段 away_loss',
  `away_goals` int DEFAULT NULL COMMENT '客场进球，对应 API 字段 away_goals',
  `away_goals_against` int DEFAULT NULL COMMENT '客场失球，对应 API 字段 away_goals_against',
  `away_goal_diff` int DEFAULT NULL COMMENT '客场净胜球，对应 API 字段 away_goal_diff',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_nami_item_snapshot_team` (`snapshot_id`,`team_id`) USING BTREE,
  KEY `idx_nami_item_team_time` (`team_id`,`snapshot_time` DESC) USING BTREE,
  KEY `idx_nami_item_season_points` (`season_id`,`competition_id`,`points` DESC) USING BTREE,
  KEY `idx_nami_item_season_position` (`season_id`,`competition_id`,`position`) USING BTREE,
  KEY `idx_nami_item_promotion` (`season_id`,`competition_id`,`promotion_id`) USING BTREE,
  KEY `idx_nami_item_snapshot` (`snapshot_id`) USING BTREE,
  KEY `idx_nami_item_snapshot_position` (`snapshot_id`,`position`) USING BTREE,
  KEY `idx_nami_item_stage_group` (`season_id`,`competition_id`,`stage_id`,`conference`,`group_name`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=39894 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米足球积分榜快照明细（查询投影；单行内联总榜+主客场字段，不使用 standing_type）';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `beitai_football_season`
--

DROP TABLE IF EXISTS `beitai_football_season`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `beitai_football_season` (
  `season_id` int NOT NULL,
  `tournament_id` int DEFAULT NULL,
  `season_year` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `season_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `start_date` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `end_date` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `coverage_basic_player_stats` tinyint(1) DEFAULT NULL COMMENT '基础球员统计覆盖',
  `coverage_goal_scorers` tinyint(1) DEFAULT NULL COMMENT '进球者覆盖',
  `coverage_extended_team_stats` tinyint(1) DEFAULT NULL COMMENT '扩展球队统计覆盖',
  `coverage_deeper_player_stats` tinyint(1) DEFAULT NULL COMMENT '深度球员统计覆盖',
  `coverage_basic_team_stats` tinyint(1) DEFAULT NULL COMMENT '基础球队统计覆盖',
  `coverage_scores` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '比分覆盖',
  `coverage_basic_play_by_play` tinyint(1) DEFAULT NULL COMMENT '基础比赛进程覆盖',
  `coverage_deeper_team_stats` tinyint(1) DEFAULT NULL COMMENT '深度球队统计覆盖',
  `coverage_deeper_play_by_play` tinyint(1) DEFAULT NULL COMMENT '深度比赛进程覆盖',
  `coverage_extended_player_stats` tinyint(1) DEFAULT NULL COMMENT '扩展球员统计覆盖',
  `coverage_lineups` tinyint(1) DEFAULT NULL COMMENT '阵容覆盖',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`season_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_basketball_stage_newgoal`
--

DROP TABLE IF EXISTS `nami_basketball_stage_newgoal`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_basketball_stage_newgoal` (
  `stage_id` int NOT NULL COMMENT '阶段id 实际存赛季id',
  `season_id` int DEFAULT NULL COMMENT '赛季id',
  `name_zh` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文名称(存赛季名称)',
  `name_zht` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语名称',
  `name_en` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `mode` int DEFAULT NULL COMMENT '比赛模式，1-积分赛、2-淘汰赛',
  `group_count` int DEFAULT NULL COMMENT '总组数',
  `round_count` int DEFAULT NULL COMMENT '总轮数',
  `order` int DEFAULT '14' COMMENT '排序，固定14',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`stage_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米篮球阶段列表(赛季数据转为阶段)';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sporttery_football_had_odds`
--

DROP TABLE IF EXISTS `sporttery_football_had_odds`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sporttery_football_had_odds` (
  `match_id` int NOT NULL COMMENT 'Sporttery 官方比赛 ID，同时关联 sporttery_football_match.match_id',
  `collect_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '本次赔率采集时间',
  `win_odds` decimal(6,2) DEFAULT NULL COMMENT '胜赔，对应接口 HAD 的 h',
  `equal_odds` decimal(6,2) DEFAULT NULL COMMENT '平赔，对应接口 HAD 的 d',
  `lose_odds` decimal(6,2) DEFAULT NULL COMMENT '负赔，对应接口 HAD 的 a',
  `int_single` int DEFAULT NULL COMMENT '是否允许单关：0 不允许，1 允许；没有返回时为空',
  `match_status` int DEFAULT NULL COMMENT '玩法对应比赛状态：1 开售，2 停售，3 已开奖',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`match_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='竞彩足球胜平负最新赔率表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_m_competition`
--

DROP TABLE IF EXISTS `audit_m_competition`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_m_competition` (
  `competition_id` int NOT NULL COMMENT '赛事id',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `sport_id` int NOT NULL COMMENT '运动项目id',
  `name_zh` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '赛事全称',
  `short_name_zh` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '赛事简称',
  `name_en` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `type` int DEFAULT NULL COMMENT '赛事类型，0-其他、1-联赛、2-杯赛、3-友谊赛',
  `jc_short_name` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '竞彩简称',
  `ctzc_short_name` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '传统足彩简称',
  `collect_match_flag` tinyint DEFAULT NULL COMMENT '是否采集赛事下全部比赛 0不采集  1采集',
  `bd_betting_flag` tinyint DEFAULT NULL COMMENT '北单竞猜赛事 0不竞猜 1竞猜',
  `nami_id_match_status` tinyint NOT NULL DEFAULT '0' COMMENT '纳米匹配状态 0未匹配 1匹配 默认0',
  `beitai_id_match_status` tinyint NOT NULL DEFAULT '0' COMMENT '贝泰匹配状态 0未匹配 1匹配 默认0',
  `default_sort_order` int DEFAULT NULL COMMENT '赛事排序序号 比赛列表按赛事显示默认排序序号,,null使用默认赛事更新时间倒序排',
  `select_sort_order` int DEFAULT NULL COMMENT '赛事筛选排序序号 比赛列表赛事简称赛事选择默认排序,,null使用默认赛事更新时间倒序排',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账户',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账户',
  PRIMARY KEY (`competition_id`,`rev`) USING BTREE,
  KEY `FKpff5i3f8x403yj9d55adeqwum` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `bd_batch_matchup_diff`
--

DROP TABLE IF EXISTS `bd_batch_matchup_diff`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `bd_batch_matchup_diff` (
  `matchup_diff_id` int NOT NULL AUTO_INCREMENT COMMENT '比赛草稿比对的唯一编号 自增',
  `match_id` int NOT NULL COMMENT '比赛id  diff_type=1或者2 为缺少的比赛id,diff_type=3 为值不一致的id',
  `batch_id` int NOT NULL COMMENT '批次id',
  `game_draw_id` int NOT NULL COMMENT '奖期id',
  `diff_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '比对时间',
  `diff_base_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '比对的基准用户',
  `diff_target_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '比对用户 id',
  `diff_type` tinyint NOT NULL COMMENT '1基准缺少比赛; 2 比对用户缺少比赛; 3值不一致',
  `diff_field` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '比较的字段',
  `diff_base_value` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '比对的基准值',
  `diff_target_value` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '比对的目标值',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账号',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账号',
  PRIMARY KEY (`matchup_diff_id`) USING BTREE,
  KEY `ind_diff_batch_id` (`batch_id`) USING BTREE,
  KEY `ind_diff_game_draw_id` (`game_draw_id`) USING BTREE,
  KEY `ind_diff_match_id` (`match_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=40552 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='北单比赛草稿对比记录表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_bd_batch_matchup_draft`
--

DROP TABLE IF EXISTS `audit_bd_batch_matchup_draft`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_bd_batch_matchup_draft` (
  `matchup_draft_id` int NOT NULL COMMENT '草稿id',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `batch_id` int NOT NULL COMMENT '批次id',
  `sort_no` int NOT NULL COMMENT '草稿界面展示排序序号',
  `game_draw_id` int NOT NULL COMMENT '奖期id',
  `match_id` int NOT NULL COMMENT '比赛id',
  `manual_competition_id` int DEFAULT NULL COMMENT '人工录入的赛事',
  `manual_season_id` int DEFAULT NULL COMMENT '人工录入的赛季',
  `game1200_matchup_no` int DEFAULT NULL COMMENT '单场场次编号',
  `game1260_matchup_no` int DEFAULT NULL COMMENT '下半场比分场次编号',
  `game1270_matchup_no` int DEFAULT NULL COMMENT '胜负过关场次编号',
  `sport_id` int NOT NULL COMMENT '运动项目id',
  `bd_round` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '轮次',
  `match_time` datetime NOT NULL COMMENT '开赛时间',
  `home_team_id` int NOT NULL COMMENT '主队id',
  `away_team_id` int NOT NULL COMMENT '客队id',
  `team_reverse` int NOT NULL DEFAULT '0' COMMENT '主客队调换 0不调换 1调换 默认0',
  `sale_end_time` datetime DEFAULT NULL COMMENT '停售时间',
  `game1260_sale_end_time` datetime DEFAULT NULL COMMENT '下半场比分停售时间',
  `game1200_draw_time` datetime DEFAULT NULL COMMENT ' 单场开奖时间',
  `game1260_draw_time` datetime DEFAULT NULL COMMENT '下半场比分开奖时间',
  `game1270_draw_time` datetime DEFAULT NULL COMMENT '胜负过关开奖时间',
  `game1200_handicap` int DEFAULT '0' COMMENT '单场让球 无让球为0',
  `game1270_handicap` decimal(10,1) DEFAULT '0.0' COMMENT '胜负让球 无让球为0',
  `review_status` tinyint NOT NULL DEFAULT '0' COMMENT '0 未审核1初审2复核 ，默认0',
  `sale_game_list` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL DEFAULT '200,210,230,240,250,260,270' COMMENT '开售的游戏列表，逗号分割 如200,210,230,240,250,260,270',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账号',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账号',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`matchup_draft_id`,`rev`) USING BTREE,
  KEY `FK_rev` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_tx_team`
--

DROP TABLE IF EXISTS `audit_tx_team`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_tx_team` (
  `team_id` int NOT NULL COMMENT '球队编号(SDT编号)',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `team_name` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '球队名称',
  `name_en` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `short_name` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球队简称',
  `establish_date` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '成立日期',
  `capacity` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球场容量',
  `website` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '官网',
  `email` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '邮件地址',
  `country` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '国家地区',
  `address` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球队地址',
  `city` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '所在城市',
  `stadium` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球场名称',
  `profile` varchar(4500) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球队简介',
  `best` varchar(3000) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球队之最',
  `glory` varchar(1500) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球队荣誉',
  `player_age_avg` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球员平均年龄',
  `photo` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球队图标',
  `team_price` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球队身价',
  `team_price_currency` int DEFAULT NULL COMMENT '身价单位。1欧元；2美元；3英镑；4人民币',
  `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`team_id`,`rev`) USING BTREE,
  KEY `FK_rev` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin ROW_FORMAT=DYNAMIC COMMENT='同行球队表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_football_category`
--

DROP TABLE IF EXISTS `nami_football_category`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_football_category` (
  `category_id` int NOT NULL COMMENT '分类id',
  `name_zh` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文名称',
  `name_zht` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语名称',
  `name_en` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`category_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米足球分类列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_nami_football_match`
--

DROP TABLE IF EXISTS `audit_nami_football_match`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_nami_football_match` (
  `match_id` int NOT NULL COMMENT '比赛id',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `season_id` int DEFAULT NULL COMMENT '赛季id',
  `competition_id` int DEFAULT NULL COMMENT '赛事id',
  `home_team_id` int DEFAULT NULL COMMENT '主队id',
  `away_team_id` int DEFAULT NULL COMMENT '客队id',
  `status_id` int DEFAULT NULL COMMENT '比赛状态，详见状态码->比赛状态',
  `match_time` bigint DEFAULT NULL COMMENT '比赛时间 时间戳精确到秒',
  `neutral` int DEFAULT NULL COMMENT '是否中立场，1-是、0-否',
  `note` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '备注',
  `home_scores` json DEFAULT NULL COMMENT '主队比分字段list',
  `away_scores` json DEFAULT NULL COMMENT '客队比分字段list',
  `home_position` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '主队排名',
  `away_position` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '客队排名',
  `coverage` json DEFAULT NULL COMMENT '动画、情报、阵容 字段',
  `venue_id` int DEFAULT NULL COMMENT '场馆id',
  `referee_id` int DEFAULT NULL COMMENT '裁判id',
  `related_id` int DEFAULT NULL COMMENT '双回合中另一回合比赛id',
  `agg_score` json DEFAULT NULL COMMENT '双回合常规时间(包括加时时间)总比分',
  `round_stage_id` int DEFAULT NULL COMMENT '轮次-阶段id',
  `round_group_num` int DEFAULT NULL COMMENT '轮次-第几组，1-A、2-B以此类推',
  `round_round_num` int DEFAULT NULL COMMENT '轮次-第几轮',
  `environment` json DEFAULT NULL COMMENT '比赛环境',
  `tbd` int DEFAULT NULL COMMENT '比赛时间是否待定 1.是',
  `has_ot` int DEFAULT NULL COMMENT '是否有加时 1.是',
  `ended` int DEFAULT NULL COMMENT '结束时间',
  `team_reverse` int DEFAULT NULL COMMENT '是否主客相反 1.是',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`match_id`,`rev`) USING BTREE,
  KEY `FK_rev` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米足球变动比赛列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_football_europe_odds`
--

DROP TABLE IF EXISTS `nami_football_europe_odds`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_football_europe_odds` (
  `odds_id` bigint NOT NULL AUTO_INCREMENT COMMENT '赔率id 自增',
  `match_id` int NOT NULL COMMENT '比赛id',
  `company_id` int NOT NULL COMMENT '博彩公司编号 见nami_football_europe_odds_company',
  `change_time` int NOT NULL COMMENT '变化时间',
  `home_win` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '主胜',
  `draw` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '和局',
  `away_win` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '客胜',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`odds_id`) USING BTREE,
  KEY `ind_match_id` (`match_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米足球百欧赔率';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_bd_batch_matchup_diff`
--

DROP TABLE IF EXISTS `audit_bd_batch_matchup_diff`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_bd_batch_matchup_diff` (
  `matchup_diff_id` int NOT NULL AUTO_INCREMENT COMMENT '比赛草稿编号',
  `match_id` int NOT NULL COMMENT '比赛id  diff_type=1或者2 为缺少的比赛id,diff_type=3 为值不一致的id',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `batch_id` int NOT NULL COMMENT '批次id',
  `game_draw_id` int NOT NULL COMMENT '奖期id',
  `diff_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '比对时间',
  `diff_base_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '比对的基准用户',
  `diff_target_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '比对用户 id',
  `diff_type` tinyint NOT NULL COMMENT '1基准缺少比赛; 2 比对用户缺少比赛; 3值不一致',
  `diff_field` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '比较的字段',
  `diff_base_value` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '比对的基准值',
  `diff_target_value` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '比对的目标值',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账号',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账号',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`matchup_diff_id`,`rev`) USING BTREE,
  KEY `FK_rev` (`rev`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=40552 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_american_football_country`
--

DROP TABLE IF EXISTS `nami_american_football_country`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_american_football_country` (
  `country_id` int NOT NULL COMMENT '国家id',
  `name_zh` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文名称',
  `name_en` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `name_zht` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语名称',
  `logo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '国家logo',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`country_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米橄榄球国家列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_nami_basketball_team`
--

DROP TABLE IF EXISTS `audit_nami_basketball_team`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_nami_basketball_team` (
  `team_id` int NOT NULL COMMENT '球队id',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `competition_id` int DEFAULT NULL COMMENT '赛事id（球队所属联赛，杯赛不关联）',
  `country_id` int DEFAULT NULL COMMENT '国家id',
  `conference_id` int DEFAULT NULL COMMENT '赛区id，1-大西洋赛区、2-中部赛区、3-东南赛区、4-太平洋赛区、5-西北赛区、6-西南赛区、7-A组赛区、8-B组赛区、9-C组赛区、10-D组赛区（1~6:NBA 7~10:CBA）、0-无',
  `coach_id` int DEFAULT NULL COMMENT '教练id',
  `name_zh` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文名称',
  `name_zht` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语名称',
  `name_en` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `short_name_zh` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文简称',
  `short_name_zht` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语简称',
  `short_name_en` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文简称',
  `logo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球队logo',
  `venue_id` int DEFAULT NULL COMMENT '场馆id',
  `uid` int DEFAULT NULL COMMENT '球队id(重复球队合并后的对应id)',
  `is_national` int DEFAULT NULL COMMENT '是否国家队，1-是、0-否',
  `is_virtual` int DEFAULT NULL COMMENT '是否占位球队，1-是、0-否',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`team_id`,`rev`) USING BTREE,
  KEY `FK_rev` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米篮球球队列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sporttery_football_league`
--

DROP TABLE IF EXISTS `sporttery_football_league`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sporttery_football_league` (
  `league_id` bigint NOT NULL COMMENT '官方联赛ID',
  `league_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '联赛简称',
  `league_full_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '联赛全称',
  `league_color` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '联赛配色',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`league_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='竞彩足球联赛表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_m_season`
--

DROP TABLE IF EXISTS `audit_m_season`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_m_season` (
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `season_id` int NOT NULL COMMENT '赛季id',
  `competition_id` int NOT NULL COMMENT '赛事id',
  `year` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '赛季年',
  `sport_id` int NOT NULL COMMENT '运动项目id',
  `name_zh` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '赛季名称',
  `bd_name` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '北单全称',
  `bd_short_name` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '北单简称',
  `name_en` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `nami_id_match_status` tinyint NOT NULL DEFAULT '0' COMMENT '纳米匹配状态 0未匹配 1匹配 默认0',
  `beitai_id_match_status` tinyint NOT NULL DEFAULT '0' COMMENT '贝泰匹配状态 0未匹配 1匹配 默认0',
  `belong` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '隶属',
  `score` int DEFAULT NULL COMMENT '运营综合评分',
  `competition_level` varchar(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛事级别',
  `memo` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛事简介',
  `logo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛事logo',
  `official_web` varchar(300) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '官方网站',
  `media_web_1` varchar(300) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '媒体网站1',
  `media_web_2` varchar(300) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '媒体网站2',
  `media_web_3` varchar(300) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '媒体网站3',
  `media_web_name_1` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '媒体网站名称',
  `media_web_name_2` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '媒体网站名称2',
  `media_web_name_3` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '媒体网站名称3',
  `span` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '时间跨度',
  `time_lag` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '时差',
  `team_cnt` int DEFAULT NULL COMMENT '球队数量',
  `playoff_flag` tinyint DEFAULT NULL COMMENT '附加赛 0无 1有',
  `composition_match_cnt` json DEFAULT NULL COMMENT '比赛构成/比赛数量字典 1常规赛、2冠军组、3保级组、4升降级、5升级、6欧战组、0其他',
  `competition_system` varchar(3000) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛制',
  `submit_status` int DEFAULT NULL COMMENT '提交状态 0未提交 1已提交',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账户',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账户',
  PRIMARY KEY (`season_id`,`rev`) USING BTREE,
  KEY `FKpff5i3f8x4032j9d55adeqwum` (`rev`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_football_match`
--

DROP TABLE IF EXISTS `nami_football_match`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_football_match` (
  `match_id` int NOT NULL COMMENT '比赛id',
  `season_id` int DEFAULT NULL COMMENT '赛季id',
  `competition_id` int DEFAULT NULL COMMENT '赛事id',
  `home_team_id` int DEFAULT NULL COMMENT '主队id',
  `away_team_id` int DEFAULT NULL COMMENT '客队id',
  `status_id` int DEFAULT NULL COMMENT '比赛状态，详见状态码->比赛状态',
  `match_time` bigint DEFAULT NULL COMMENT '比赛时间 时间戳精确到秒',
  `neutral` int DEFAULT NULL COMMENT '是否中立场，1-是、0-否',
  `note` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '备注',
  `home_scores` json DEFAULT NULL COMMENT '主队比分字段list',
  `away_scores` json DEFAULT NULL COMMENT '客队比分字段list',
  `home_position` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '主队排名',
  `away_position` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '客队排名',
  `coverage` json DEFAULT NULL COMMENT '动画、情报、阵容 字段',
  `venue_id` int DEFAULT NULL COMMENT '场馆id',
  `referee_id` int DEFAULT NULL COMMENT '裁判id',
  `related_id` int DEFAULT NULL COMMENT '双回合中另一回合比赛id',
  `agg_score` json DEFAULT NULL COMMENT '双回合常规时间(包括加时时间)总比分',
  `round_stage_id` int DEFAULT NULL COMMENT '轮次-阶段id',
  `round_group_num` int DEFAULT NULL COMMENT '轮次-第几组，1-A、2-B以此类推',
  `round_round_num` int DEFAULT NULL COMMENT '轮次-第几轮',
  `environment` json DEFAULT NULL COMMENT '比赛环境',
  `tbd` int DEFAULT NULL COMMENT '比赛时间是否待定 1.是',
  `has_ot` int DEFAULT NULL COMMENT '是否有加时 1.是',
  `ended` int DEFAULT NULL COMMENT '结束时间',
  `team_reverse` int DEFAULT NULL COMMENT '是否主客相反 1.是',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`match_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米足球变动比赛列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `toto_config`
--

DROP TABLE IF EXISTS `toto_config`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `toto_config` (
  `config_key` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '配置键',
  `config_value` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '配置值',
  `ui_config_flag` tinyint NOT NULL COMMENT '界面配置标志.0 管理端不可修改；1 管理端可修改',
  `config_desc` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '配置描述',
  `rdc_id` int DEFAULT NULL COMMENT '地区ID。空值时全局生效',
  PRIMARY KEY (`config_key`,`config_value`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='配置表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `m_match`
--

DROP TABLE IF EXISTS `m_match`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `m_match` (
  `match_id` int NOT NULL AUTO_INCREMENT COMMENT '比赛id',
  `sport_id` int NOT NULL COMMENT '运动项目id',
  `season_id` int NOT NULL COMMENT '赛季id',
  `competition_id` int NOT NULL COMMENT '赛事id',
  `home_team_id` int NOT NULL COMMENT '主队id',
  `away_team_id` int NOT NULL COMMENT '客队id',
  `match_status` int NOT NULL COMMENT '比赛状态 见字典表同名',
  `match_stage` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '阶段',
  `match_group` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '分组',
  `match_round` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '轮次',
  `match_time` datetime NOT NULL COMMENT '开赛时间',
  `home_score_half` int DEFAULT NULL COMMENT '主队半场比分',
  `away_score_half` int DEFAULT NULL COMMENT '客队半场比分',
  `home_score` int DEFAULT NULL COMMENT '主队比分',
  `away_score` int DEFAULT NULL COMMENT '客队比分',
  `nami_id_match_status` int NOT NULL DEFAULT '0' COMMENT '纳米匹配状态 0未匹配 1匹配 默认0',
  `beitai_id_match_status` int NOT NULL DEFAULT '0' COMMENT '贝泰匹配状态 0未匹配 1匹配 默认0',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账户',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账户',
  PRIMARY KEY (`match_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=1574 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='人工录入的比赛';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `bd_batch_matchup_draft`
--

DROP TABLE IF EXISTS `bd_batch_matchup_draft`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `bd_batch_matchup_draft` (
  `matchup_draft_id` int NOT NULL AUTO_INCREMENT COMMENT '草稿id',
  `batch_id` int NOT NULL COMMENT '批次id',
  `sort_no` int NOT NULL COMMENT '草稿界面展示排序序号',
  `game_draw_id` int NOT NULL COMMENT '奖期id',
  `match_id` int NOT NULL COMMENT '比赛id',
  `manual_competition_id` int DEFAULT NULL COMMENT '人工录入的赛事',
  `manual_season_id` int DEFAULT NULL COMMENT '人工录入的赛季',
  `game1200_matchup_no` int DEFAULT NULL COMMENT '单场场次编号',
  `game1260_matchup_no` int DEFAULT NULL COMMENT '下半场比分场次编号',
  `game1270_matchup_no` int DEFAULT NULL COMMENT '胜负过关场次编号',
  `sport_id` int NOT NULL COMMENT '运动项目id',
  `bd_round` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '轮次',
  `match_time` datetime NOT NULL COMMENT '开赛时间',
  `home_team_id` int NOT NULL COMMENT '主队id',
  `away_team_id` int NOT NULL COMMENT '客队id',
  `team_reverse` int NOT NULL DEFAULT '0' COMMENT '主客队调换 0不调换 1调换 默认0',
  `sale_end_time` datetime DEFAULT NULL COMMENT '停售时间',
  `game1260_sale_end_time` datetime DEFAULT NULL COMMENT '下半场比分停售时间',
  `game1200_draw_time` datetime DEFAULT NULL COMMENT '单场开奖时间',
  `game1260_draw_time` datetime DEFAULT NULL COMMENT '下半场比分开奖时间',
  `game1270_draw_time` datetime DEFAULT NULL COMMENT '胜负过关开奖时间',
  `game1200_handicap` int DEFAULT '0' COMMENT '单场让球 无让球为0',
  `game1270_handicap` decimal(10,1) DEFAULT '0.0' COMMENT '胜负让球 无让球为0',
  `review_status` tinyint NOT NULL DEFAULT '0' COMMENT '0 未审核1初审2复核 ，默认0',
  `sale_game_list` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL DEFAULT '200,210,230,240,250,260,270' COMMENT '开售的游戏列表，逗号分割 如200,210,230,240,250,260,270',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建账号',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新账号',
  PRIMARY KEY (`matchup_draft_id`) USING BTREE,
  KEY `ind_draft_batch_id` (`batch_id`) USING BTREE,
  KEY `ind_draft_game_draw_id` (`game_draw_id`) USING BTREE,
  KEY `ind_draft_match_id` (`match_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=3415287 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='北单比赛草稿表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_football_deleted`
--

DROP TABLE IF EXISTS `nami_football_deleted`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_football_deleted` (
  `deleted_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '删除的数据类型 1:category 分类，2:team 球队，4:competition 赛事，5:stage 阶段，6:season 赛季，7:venue 场馆，8:match 比赛，9:player 运动员',
  `id` int NOT NULL COMMENT '删除的数据id',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`deleted_type`,`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米足球删除数据列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_s_match`
--

DROP TABLE IF EXISTS `audit_s_match`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_s_match` (
  `match_id` int NOT NULL COMMENT '比赛id',
  `rev` int NOT NULL,
  `revtype` tinyint DEFAULT NULL,
  `sport_id` int DEFAULT NULL COMMENT '运动项目id',
  `season_id` int DEFAULT NULL COMMENT '赛季id',
  `competition_id` int DEFAULT NULL COMMENT '赛事id',
  `matchup_unique_no` json DEFAULT NULL COMMENT '北单比赛唯一编号',
  `beitai_match_id` int DEFAULT NULL COMMENT '贝泰比赛id',
  `nami_match_id` int DEFAULT NULL COMMENT '纳米比赛id',
  `tx_match_id` int DEFAULT NULL COMMENT '同行比赛id',
  `manual_match_id` int DEFAULT NULL COMMENT '人工录入的比赛编号',
  `home_team_id` int DEFAULT NULL COMMENT '主队id',
  `away_team_id` int DEFAULT NULL COMMENT '客队id',
  `match_round` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '轮次',
  `match_stage` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '阶段',
  `match_group` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '分组',
  `status_id` int DEFAULT NULL COMMENT '比赛状态 \r\n1000未开赛(未入稿)\r\n1100比赛中(未入稿)\r\n1200完场(未入稿)\r\n1300推迟(未入稿)\r\n1400中断(未入稿)\r\n1500腰斩(未入稿)\r\n1600取消（未入稿）\r\n1700待定\r\n1001未开赛(已入稿)\r\n1002未开赛(赛程已提交)\r\n1003未开赛(已开售)\r\n1101比赛中(已入稿)\r\n1102比赛中(赛程已提交)\r\n1103比赛中(已开售)\r\n1201完场(已入稿)\r\n1202完场(赛程已提交)\r\n1203完场(已开售)\r\n1205完场(赛果已提交)\r\n1206完场(已开奖)\r\n1301推迟(已入稿)\r\n1302推迟(赛程已提交)\r\n1303推迟(已开售)\r\n1305推迟(赛果已提交)\r\n1306推迟(已开奖)\r\n1401中断(已入稿)\r\n1402中断(赛程已提交)\r\n1403中断(已开售)\r\n1405中断(赛果已提交)\r\n1406中断(已开奖)\r\n1501腰斩(已入稿)\r\n1502腰斩(赛程已提交)\r\n1503腰斩(已开售)\r\n1505腰斩(赛果已提交)\r\n1506腰斩(已开奖)\r\n1601取消(已入稿)\r\n1602取消(赛程已提交)\r\n1603取消(已开售)\r\n1605取消(赛果已提交)\r\n1606取消(已开奖)\r\n',
  `match_time` datetime DEFAULT NULL COMMENT '比赛时间',
  `home_score_half` int DEFAULT NULL COMMENT '主队半场比分',
  `away_score_half` int DEFAULT NULL COMMENT '客队半场比分',
  `home_score` int DEFAULT NULL COMMENT '主队比分',
  `away_score` int DEFAULT NULL COMMENT '客队比分',
  `home_score_all` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '使用源数据json，半场，全场，加时，点球',
  `away_score_all` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '使用源数据json，半场，全场，加时，点球',
  `home_position` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '主队排名',
  `away_position` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '客队排名',
  `venue_id` int DEFAULT NULL COMMENT '场馆id',
  `weather` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '天气',
  `bd_matchup_home_team_id` int DEFAULT NULL COMMENT '北单赛程的比赛的主队id',
  `replace_id` int DEFAULT NULL COMMENT '在旧的比赛记录上关联新比赛ID，如果比赛上有新的比赛ID，则不需要再进行数据更新',
  `create_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '创建用户',
  `update_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '更新用户',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`match_id`,`rev`) USING BTREE,
  KEY `ind_tx_match_id` (`tx_match_id`) USING BTREE,
  KEY `ind_manual_match_id` (`manual_match_id`) USING BTREE,
  KEY `ind_nami_match_id` (`nami_match_id`) USING BTREE,
  KEY `ind_status_id` (`status_id`) USING BTREE,
  KEY `ind_update_time` (`update_time`) USING BTREE,
  KEY `ind_match_time` (`match_time`) USING BTREE,
  KEY `FK_rev` (`rev`) USING BTREE,
  KEY `ind_replace_id1` (`replace_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='标准化-比赛';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_basketball_competition`
--

DROP TABLE IF EXISTS `nami_basketball_competition`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_basketball_competition` (
  `competition_id` int NOT NULL COMMENT '赛事id',
  `category_id` int DEFAULT NULL COMMENT '分类id',
  `country_id` int DEFAULT NULL COMMENT '国家id',
  `name_zh` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文名称',
  `name_zht` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语名称',
  `name_en` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `short_name_zh` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文简称',
  `short_name_zht` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语简称',
  `short_name_en` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文简称',
  `logo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '赛事logo',
  `type` int DEFAULT NULL COMMENT '赛事类型，0-未知、1-联赛、2-杯赛',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`competition_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米篮球赛事列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nami_basketball_team`
--

DROP TABLE IF EXISTS `nami_basketball_team`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nami_basketball_team` (
  `team_id` int NOT NULL COMMENT '球队id',
  `competition_id` int DEFAULT NULL COMMENT '赛事id（球队所属联赛，杯赛不关联）',
  `country_id` int DEFAULT NULL COMMENT '国家id',
  `conference_id` int DEFAULT NULL COMMENT '赛区id，1-大西洋赛区、2-中部赛区、3-东南赛区、4-太平洋赛区、5-西北赛区、6-西南赛区、7-A组赛区、8-B组赛区、9-C组赛区、10-D组赛区（1~6:NBA 7~10:CBA）、0-无',
  `coach_id` int DEFAULT NULL COMMENT '教练id',
  `name_zh` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文名称',
  `name_zht` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语名称',
  `name_en` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文名称',
  `short_name_zh` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '中文简称',
  `short_name_zht` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '粤语简称',
  `short_name_en` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '英文简称',
  `logo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '球队logo',
  `venue_id` int DEFAULT NULL COMMENT '场馆id',
  `uid` int DEFAULT NULL COMMENT '球队id(重复球队合并后的对应id)',
  `is_national` int DEFAULT NULL COMMENT '是否国家队，1-是、0-否',
  `is_virtual` int DEFAULT NULL COMMENT '是否占位球队，1-是、0-否',
  `updated_at` bigint DEFAULT NULL COMMENT '纳米更新时间 时间戳精确到秒',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`team_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='纳米篮球球队列表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-10-26 14:19:43
