# Data Closures

## 闭包索引

| DC-ID | 业务数据闭包 | 可点击文件 | 状态 | 关联 RSU | 来源资源 |
|---|---|---|---|---|---|
| DC-001 | 竞彩列表聚合数据闭包 | [DC-001 列表聚合](./DC-001-列表聚合数据闭包.md) | test-point-ready | RSU-001～RSU-010 | SRC-API-BACKEND、SRC-CODE-MONITOR、SRC-CODE-RULES、SRC-CODE-EVENT-REPO、SRC-CODE-REMARK-REPO、SRC-DB13、SRC-DB-SCHEMA |
| DC-002 | 竞彩进程解析数据闭包 | [DC-002 进程解析](./DC-002-进程解析数据闭包.md) | test-point-ready | RSU-004、RSU-011 | SRC-API-BACKEND、SRC-CODE-MONITOR、SRC-HIST-LIVE、SRC-HIST-LIVE-SQL、SRC-DB13 |
| DC-003 | 竞彩事件查询数据闭包 | [DC-003 事件查询](./DC-003-事件查询数据闭包.md) | ready | RSU-012 | SRC-API-BACKEND、SRC-CODE-EVENT、SRC-CODE-EVENT-REPO、SRC-DB13、SRC-DB-SCHEMA |
| DC-004 | 竞彩备注读写数据闭包 | [DC-004 备注读写](./DC-004-备注读写数据闭包.md) | test-point-ready | RSU-013～RSU-016 | SRC-API-BACKEND、SRC-CODE-REMARK、SRC-CODE-REMARK-REPO、SRC-CODE-MONITOR、SRC-DB13、SRC-DB-SCHEMA |

## 状态定义

- ready：足以支撑测试点和可执行用例设计。
- test-point-ready：足以生成测试点，但查询、造数或清理仍有明确缺口。
- blocked：缺口会改变测试点语义，关联 RSU 必须保持 pending-context 或 pending。

## 使用规则

按最小可复用业务数据路径建卡；RSU 在相关上下文中引用 DC-ID；图只用于导航，连接谓词、过滤、数据状态、查询和清理必须写入卡片。
