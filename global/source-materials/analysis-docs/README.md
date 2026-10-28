# 分析产出文档（analysis-docs）

本目录存放基于需求/数据/接口/实库四方信息源生成的分析产出物，与源材料（`current-requirement`、`database-docs`、`api-docs`）分离存放。

## 文档清单

| 文档 | 内容 | 信息源 |
| --- | --- | --- |
| `竞猜赛事运营系统整体架构与业务逻辑深度分析报告-完整版.md` | 最终完整版（含第 13 轮冲刺竞彩全链路）：项目概述/模块划分/业务流程/数据模型/微服务架构/风险 | PRD(至13轮) + 数据模型设计 + 数据库设计文档 + 第13轮竞彩数据库变更 + SQL DDL(20261026) + 8 份 OpenAPI + test2_newgoal 实库核验 |
| `竞猜赛事运营系统-ER图.md` | 基于真实表结构的 mermaid ER 图（9 张：总览/主数据/标准层/赛程域/事件任务变更/权限/采集层/竞彩域(13轮)/生命周期时序） | SQL DDL(20261026) + 第13轮竞彩表设计 + 实库核验 + OpenAPI |
| `竞猜赛事运营系统-表模块接口追溯矩阵.md` | 表 ↔ 模块 ↔ 接口 ↔ 权限点四方追溯矩阵（含第 13 轮竞彩与告警修改新增接口、反向索引与三方差异说明） | 实库 toto_permission.urls(149+1条) + 第13轮权限SQL + OpenAPI + PRD 操作日志 |

## 信息源位置

- 需求：`../current-requirement/`（第 13 轮冲刺 PRD + PBL 研发需求 CSV + 附件）
- 数据库：`../database-docs/`（两份基础设计 md + 第 13 轮竞彩采集与数据库变更设计 md + 最新 SQL dump `北单运营系统-test2_newgoal-202610261418.sql` + 连接配置 `database.toml`）
- 接口：`../api-docs/league-core-api/`（8 份 OpenAPI 3 规范：data-backend/data-bff/data-collection/data-computation/league-backend-service/league-bff-service/notification/openapi）

## 核验环境

- 库：test2_newgoal @ 192.168.22.218:3306（配置见 `../database-docs/database.toml`）
  - 2026-09-17 首轮核验：246 表（DDL 导出 153 表）/ 字典 481 条 / 权限 143 条 / 角色 7 个；
  - 2026-10-26 第 13 轮冲刺核验：实库 **279 表**（最新 DDL `北单运营系统-test2_newgoal-202610261418.sql` 导出 **187 表**，净增 **34 张表** + **4 张表字段扩展**）/ 字典 481 条 / 实库权限 **149 条**（含 13 轮新增 `#148~#153`，另有 `#147` 告警修改权限定义于变更 SQL）/ 角色 7 个。
