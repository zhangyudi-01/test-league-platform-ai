# API-003 `listEvents` 问题确认清单

## 引用入口

- [API-003 接口分析](./interface-analysis.md)
- [模块问题确认清单](../../preanalysis/03-clarification-questions.md)
- [模块 Context Pack](../../preanalysis/01-context-pack.md)
- [模块 Data Closures](../../preanalysis/data-closures/README.md)

## 已确认问题与结论

模块级 Q-003（空集合及字段空值）和 Q-004（事件表、展示字段及本轮范围）已在[模块问题确认清单](../../preanalysis/03-clarification-questions.md)回答；本接口沿用原 ID，不重复登记。

| Q-ID | 关联来源 | 状态 | 结论 | 后续使用 |
|---|---|---|---|---|
| Q-001 | 用户于 2026-11-03 确认 | answered | 对缺参、非法运动项目、非正数比赛 ID 等参数异常，调试时以接口返回错误为准，不要求固定的错误码或文案；不将连接失败等请求未到达接口的情况认定为接口报错。 | 按实际协议区分 HTTP 错误和业务错误；具体请求的自动化覆盖应单独记录，不能把探索结果视作自动化通过。 |
| Q-002 | 用户确认；事件表 DDL | answered | 只要数据库事件 `event_id` 非空，响应事件项必须返回对应 `eventId`。当前 DDL 将 `event_id` 定义为非空主键。 | 对正常事件断言字段存在、类型为字符串且值与数据库一致；OpenAPI 未声明必返不改变本接口已确认预期。 |
| Q-003 | 用户确认；事件表 DDL | answered | 数据库存储的空字符串正常原样返回，不转换为 `null`；与字段实际缺失时的模块级空值规则区分。 | 分别覆盖 `event_name`、`reason_desc` 为空字符串，遵守非空约束。 |

## Q-001 调试观察

2026-11-03，开发环境 `dev_newgoal` 对已登录 GET 请求做只读探测：分别缺少 `sportId`、缺少 `matchId`、`sportId=3`、`matchId=0` 和 `matchId=-1`，均观察到 HTTP 200、业务 `code=2`、消息“竞彩比赛事件查询参数错误”。这是当前环境的实现观察，不要求其他环境固定返回这些值。其他非法值、类型绑定失败及这几种情况的自动化回归尚未验证。

## 使用规则

- 模块级问题保留模块 Q-ID，本文件不复制生成新的 API Q-ID。
- 后续若出现只影响 API-003 的新问题，从 `Q-004` 起新增，并同步更新接口分析。
- 若问题会改变模块范围或多个接口的共同契约，应回填模块问题清单，再由本文件引用原模块 Q-ID。
