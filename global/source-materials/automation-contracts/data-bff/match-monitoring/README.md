# Match Monitoring Automation Contracts

本目录保存 `test-league-platform` 中既有比赛监控自动化实现所依赖的、可供 AI 测试分析复用的历史资料。

## 来源

- 原始目录：`tests/test-league-platform/testsuites/data-bff/match_monitoring/test_dependent_file/比赛列表逻辑讲解/`
- 资料性质：旧版“比赛赛程监控”测试与业务说明的参考资料
- 当前用途：为 `MOD-06-03-竞彩赛程监控` 提供可追溯的历史列表、比赛进程、事件和数据准备参考
- 重要边界：本目录中的 `/s-match` 与 `/s-match/live` 契约不是当前竞彩赛程监控主契约

当前竞彩赛程监控的主契约应优先读取：

- `global/source-materials/api-docs/league-api-definition/league-core-api/data-backend-openapi.json`
- `global/project-context.md`
- `modules/MOD-06-比赛监控/MOD-06-03-竞彩赛程监控/` 下对应模块的需求包

当前接口包括 `/sporttery/match-monitor`、`/sporttery/match-monitor/live`、`/sporttery/match-monitor/events` 和 `/sporttery/match-monitor/remarks`。本目录只提供历史实现参考，不覆盖当前接口定义。

## 目录说明

### `legacy-match-list/`

保存旧比赛列表的需求、`/s-match` OpenAPI、查询结果数据准备分析，以及列表事件/预警相关的辅助说明。

### `legacy-match-live/`

保存旧比赛进程查询的需求、SQL、`/s-match/live` OpenAPI 和实际返回示例。

## 使用规则

1. 旧资料只能作为复用逻辑、字段来源、数据准备和动态预期的参考。
2. 新模块的接口路径、参数、响应结构和错误码以当前 `api-docs` 仓库为准。
3. 数据库结构优先使用 `global/source-materials/database-docs/` 中的当前资料；本目录不保存整库旧 SQL 快照。
4. 既有 pytest、fixture、common 和 Excel 仍归 `test-league-platform` 管理，本目录不保存可执行测试代码副本。
5. 需要在前置分析中引用本目录资料时，在对应 `preanalysis` 的资源表、Context Card 或 Data Closure 中登记具体文件和用途。

