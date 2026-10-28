# 自动连续 Runner

`scripts/run_generation.py` 是单模块外层编排器。它以 `generation-state.json` 为唯一恢复依据，不读取历史日志判断阶段、下一个批次或完成状态。

## 阶段

```text
init_generation
  → planning fork
  → optional SQL fork
  → BATCH-001 fork
  → BATCH-002 fork
  → ...
  → deterministic finalization
```

- 规划阶段一次读取模块最终测试点、需求动态资源、readiness 和执行上下文，输出 SQL 需求及批次计划。
- SQL 阶段一次生成计划中的全部 SELECT，并在用例前执行唯一一次静态校验和 MySQL `EXPLAIN`；后续阶段只验证报告与资产指纹。
- 简单和查询展示批次最多 10 个 TP；复杂批次一个 TP。批次先验证全部输出，再原子更新状态。
- 最终阶段由脚本逐条收录已验证来源用例，不调用 AI 改写或归并正文。

## 会话模式

- `module-session`（默认）：完整 Skill 在模块基础会话加载一次；规划、SQL 和每个批次分别从基础会话独立 fork。兄弟批次不继承消息、工具调用或输出。
- `isolated`：每个阶段启动新会话并读取所需自包含输入。

基础会话必须完整读取 Skill 及输出、worker、SQL 契约。它只承载稳定规则，不读取兄弟批次产物或审计日志，也不得修改模块状态。基础会话的可选恢复记录不改变独立 fork 边界。

Runner 不调用 compact，也不把自动 compaction 当作成本治理方案。TP-001 的工具历史不应进入后续批次；批次边界通过独立 fork 直接阻断无关历史。

## 参数

| 参数 | 默认值 | 说明 |
|---|---|---|
| `--case-output-dir` | `<module>/test-cases` | 隔离输出目录。 |
| `--db-config` | 自动发现 | SQL EXPLAIN 配置。 |
| `--session-mode` | `module-session` | 基础会话加独立阶段 fork，或 isolated。 |
| `--max-batch-turns` | 未完成批次数 | 本次批次上限。 |
| `--max-tp-turns` | 兼容别名 | 等同 `--max-batch-turns`。 |
| `--reasoning-effort` | `medium` | Runner 独立推理强度。 |
| `--max-transient-retries` | `3` | 瞬时网络/供应商错误重试。 |
| `--retry-base-delay-seconds` | `5` | 指数退避基数，单次最多 60 秒。 |
| `--session-rotation-interval` | 兼容参数 | 新架构忽略。 |

`module-session` 要求 CLI 支持 `codex exec fork`。Windows 默认候选不支持时会继续探测 Desktop CLI；显式不兼容路径直接停止。`isolated` 不要求 fork。

## 锁、日志和恢复

- Runner 在 `<case-output-dir>/.generation-runner.lock` 持有模块锁；同一输出目录不可并发运行。
- 每个阶段保存 JSONL、stderr 和最后消息供审计，但恢复绝不读取历史日志。
- 当前调用非零时只使用本次流式事件和本次 stderr 判断是否为瞬时错误。
- 重启后从状态 JSON 读取 planning、sql_planning、batches 和 TP 状态。可选 `foundation_session` 保存版本、基础会话 ID、创建时间和指纹；只有来源哈希、模块/输出/工作目录、Skill 运行规则、适用本地指令/配置、选定 CLI 身份和 model/profile/sandbox/reasoning/provider 配置均匹配才复用，否则重建。只保存指纹摘要，不保存密钥或配置原值。
- 来源不变的初始化保留可选恢复/兼容字段；显式 refresh 清除。旧状态没有该记录也可正常新建，不需要额外迁移。
- 仅复用记录对应的 session/thread/rollout 明确不存在、失败调用未改状态且不含明确供应商硬错误时，允许本进程最多重建一次基础会话再 fork；普通网络错误不能触发重建。`isolated` 不使用该记录；已完成流程不启动 AI。
- 余额/额度不足、账户并发窗口已满、模型要求升级 Codex 等硬错误优先于 stream/429 泛化提示，不进入 Runner 自动重试；普通瞬时错误仍有限退避。Runner 无法取消 CLI 自己在进程内部进行的重试。
- 用例 worker 先读实际模板并保留固定表格契约。首次校验仅有当前输出格式、编号、变量或已有输入引用填写错误时，允许同一 worker turn 内最多 2 轮修正后复验（合计最多 3 次），通过才报告完成；缺事实、来源漂移、SQL资产/报告不一致立即阻断。此上限是 worker 提示/执行契约，不是 Runner 强制计数器。
- 上游来源漂移时停止，必须人工确认后运行 `init_generation.py --refresh`。
- 旧 v2 状态以及缺少模块规划/批次字段的早期 v3 状态不得回落到旧逐 TP 调度；初始化会要求显式 `--refresh` 后进入新 v3 状态机。

本轮未增加单批次时长/工具调用熔断，也未增加会话级 token/时长熔断。
