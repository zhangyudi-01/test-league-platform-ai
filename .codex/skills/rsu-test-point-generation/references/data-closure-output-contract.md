# Data Closure Output Extension

## 单 RSU 候选

启用数据闭包时，候选表头替换为：

```text
候选 ID | Primary RSU | Source RSUs | 测试项 | 测试点 | 备注 | Question Refs | Context Refs | Data Closure Refs | 推导依据
```

- `Data Closure Refs` 只允许输入包已物化的 `DC-xxx`，多个 ID 使用 `、`，无引用写 `无`。
- 每个 Data Closure Ref 必须同时出现在 Context Refs。
- 不得把 `DC-INDEX` 当作闭包引用；它只是索引。
- 三个业务列遵循基础输出契约：测试点含必要条件和预期，备注可为空；闭包索引不能代替可直接理解的测试点正文。

## 最终测试点

启用数据闭包时，最终表头替换为：

```text
TP-ID | Primary RSU | Source RSUs | 测试项 | 测试点 | 备注 | Question Refs | Context Refs | Data Closure Refs | Source Candidates | 合并或保留依据
```

最终测试点必须完整继承其全部 Source Candidates 的 Data Closure Refs，不能新增、删除或用 `Context Refs` 隐藏闭包依赖。

## 用例就绪性

启用数据闭包时，TP 就绪性表头替换为：

```text
TP-ID | 用例生成状态 | Data Closure Refs | Input Question Refs | 说明
```

每行 Data Closure Refs 必须与最终 TP 完全一致。引用状态为 `test-point-ready` 的闭包时：

- 先按 readiness 五项 CIQ 准入门禁重新判断上游记录的缺口，不得仅凭状态标签判定 `blocked-input`。
- 现有来源、语义参数、常规查询/观察或执行时绑定已足以实例化查询、准备、预期和清理时，可以直接标记 `ready`，不要求创建或回答 CIQ。
- 只有仍缺真实不可替代输入时，TP 才标记 `blocked-input` 并引用待回答的 `data-contract`、`test-data`、`environment` 或 `configuration` CIQ。

`data-contract` 是数据闭包扩展允许的额外 CIQ 类型，用于物理字段、查询入口、造数或清理契约；会改变测试点语义的缺口仍属于 `upstream-gap`，不能降级为该类型。
