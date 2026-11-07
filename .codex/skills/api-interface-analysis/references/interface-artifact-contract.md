# Interface Analysis Artifacts

This contract defines the supporting files owned by one API operation. The endpoint analysis remains the business baseline; supporting files contain only focused material that downstream `api-test-plan` and `api-test-automation-design` need to reuse.

## Directory Layout

Keep the current module-level `preanalysis/` intact. Do not copy its requirement pack, question list, Context Cards, or Data Closures into an API bundle.

```text
<module-root>/
  preanalysis/                       # existing module-level inputs
  interfaces/<API-ID>-<slug>/
    interface-analysis.md            # unique operation analysis
    clarification-questions.md
    context-cards/                   # optional; only when useful
      README.md
      AFC-001-<topic>.md
    data-closures/                   # optional; only when module DCs are insufficient
      README.md
      ADC-001-<data-path>.md
```

The interface analysis links directly to its question file and any relevant module/API FC/DC cards. No new module manifest is required, but update an existing module index or manifest when paths change. When an analyzed operation has authoritative files under the legacy `interface-analysis/endpoints/` or `interface-analysis/artifacts/` layout, or an interface question file named `03-clarification-questions.md`, migrate or rename only that operation's files, preserving content, answers and status. Update links and retain a single authoritative copy; do not migrate unrelated operations or rename the module-level `preanalysis/03-clarification-questions.md`.

## Reuse Before Creation

Before creating an API Data Closure, compare the operation's data path with the module `preanalysis/data-closures/` cards. Reuse a module card when its tables, fields, join predicates, filters, cardinality, result semantics, and preparation/cleanup boundaries are sufficient for this operation. Create an API card only for a distinct path or material operation-specific details missing from the module card; link the reused module card and state the gap this API card fills.

Create an API Context Card only when a stable, non-trivial context spans several sources or rule sections and is likely to be reused by the API test-plan or automation stages. Prefer a module FC when it already owns that context. Do not create a card that merely summarizes the endpoint analysis, repeats a DC, or repeats one short rule.

Create no empty `context-cards/` or `data-closures/` directory. The question file is always present, including when there are no open questions.

## Clarification Questions

`clarification-questions.md` contains only questions whose decision is specific to this operation. If a question concerns module-wide requirement semantics, keep its canonical record in the module `preanalysis/03-clarification-questions.md` and reference that existing Q-ID from the endpoint analysis. Do not duplicate it under a new API Q-ID.

Use IDs `Q-001`, `Q-002`, ... scoped to this file. Preserve IDs when maintaining an existing file. Keep answered questions for traceability; do not turn resolved questions into new rows.

```markdown
# <API-ID> <operation> 问题确认清单

## 引用入口
- 接口分析：[接口分析](./interface-analysis.md)
- 模块问题清单：[模块问题清单](../../preanalysis/03-clarification-questions.md)

## 已确认问题与结论
| Q-ID | 关联来源 | 状态 | 确认结论 | 回填位置 |
|---|---|---|---|---|

## 待确认问题
| Q-ID | 关联来源 | 状态 | 问题与影响 | 需要确认 | 未确认时的处理 |
|---|---|---|---|---|---|

当前无待确认问题。
```

Keep only the applicable no-open-questions sentence: remove it when pending rows exist. Allowed states are `answered`, `pending`, `deferred`, and `out-of-scope`. A pending/deferred question states which conclusion or downstream work it blocks. When answered, update this file, the endpoint analysis, and any dependent API card in the same maintenance pass.

## API Data Closures

An API Data Closure records the smallest database path needed to understand the endpoint's data behavior and prepare later test design. It is not an executable oracle, fixture recipe, sample dataset, or copy of the whole module graph. Concrete SQL, test values, and per-case data ownership are completed in automation design/implementation.

Use IDs `ADC-001`, `ADC-002`, ... within the API bundle. Create one card per independently reusable path, not one per test point. Statuses:

- `ready`: semantic and physical data path is clear enough for test-point and automation design; concrete SQL and case values may still be downstream work.
- `test-point-ready`: business semantics are clear, but physical fields, joins, preparation, or cleanup still have an identified gap for automation design.
- `blocked`: missing/contradictory data semantics can change the expected behavior; link the blocking API Q-ID and do not imply the downstream contract is resolved.

The API Data Closure index uses:

```markdown
# API Data Closures

## 闭包索引
| ADC-ID | 业务数据路径 | 可点击文件 | 状态 | 来源资源 | 下游用途 |
|---|---|---|---|---|---|

## 状态与使用规则
```

Each `ADC-xxx` card follows the module Data Closure shape where applicable, but omits RSU references and module-map registration. Required sections:

```markdown
# ADC-xxx <业务数据路径>

## 引用入口
## 定位
## 关联范围
## 闭包目标
## 输入与输出
## 关系图
## 表角色
## 连接与过滤契约
## 数据状态与准备契约
## 查询与断言契约
## 清理与隔离
## 当前缺口
```

The relationship diagram is navigation only. Record, when applicable, exact table/field roles, complete join predicates, filters, cardinality, null/empty behavior, ordering/aggregation, relevant data profiles, independently derivable expected-result semantics, and safe preparation/cleanup boundaries. Cite the source for each important relation. Never infer a join from names alone. Do not copy the implementation query verbatim and label it an independent oracle.

Every `ADC` card must be linked from its API index and endpoint analysis. The endpoint analysis identifies which behavior groups use it. If it reuses a module `DC`, link that card directly instead of creating a duplicate `ADC`.

## API Context Cards

Use IDs `AFC-001`, `AFC-002`, ... within the API bundle. The index format is:

```markdown
# API Context Cards

## 卡片索引
| AFC-ID | 类型 | 可点击文件 | 复用内容 |
|---|---|---|---|

## 使用规则
```

Each card contains:

```markdown
# AFC-xxx <主题>

## 引用入口
## 定位
## 关联来源
## 已确认上下文
## 当前边界
```

Record only the reusable cross-source context and its evidence. Keep operation behavior and response contracts in the endpoint analysis; keep database relations in the DC. Link a module FC instead when its scope already fits.

## Downstream Consumption

`api-test-plan` reads the endpoint analysis, the question file's pending/deferred items, and only the FC/DC cards linked for the operation. `api-test-automation-design` follows the final test-point Data Closure references to either module DCs or API ADCs. A missing physical preparation/cleanup detail belongs in automation design as a gap; it does not justify inventing semantics in the interface analysis.

When a source or answer changes, update only affected endpoint artifacts and their links. Do not regenerate unrelated API bundles or rewrite the module-level preanalysis.
