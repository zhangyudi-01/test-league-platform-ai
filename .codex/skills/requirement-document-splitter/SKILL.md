---
name: requirement-document-splitter
description: 根据已经确认的模块目录，将 Markdown 或 Word/docx 需求文档按模块确定性拆分；Markdown 保持原文切片，docx 先生成稳定 Markdown 表示再拆分，并支持 Codex/Codex 逐模块复核行号范围。
license: MIT
metadata:
  author: project
  version: "2.0"
---

# 需求正文按模块拆分 Skill

当用户已经有确认好的模块目录，并希望把大需求文档按模块拆分成多个模块需求包时，使用本 skill。

本 skill **不负责生成模块目录**。如果还没有模块目录，请先使用 `module-directory-generator` skill。

## 支持的源文档

- Markdown：`.md` / `.markdown`
- Word：`.docx`

两种模式的保证不同：

| 源文档 | 拆分依据 | 保证 |
|---|---|---|
| Markdown | 原始 Markdown 行 | 输出文件是源文档原始 byte slice，不改字、不改链接、不改换行 |
| Word/docx | 稳定生成的 canonical Markdown | 输出文件等于从 docx 确定性转换出的 Markdown 切片；不是 Word 原始字节切片 |

Word 不是纯文本文件，不能按原始字节“一字不改”切分。对 docx 的正确做法是：先用脚本读取 OOXML，按标题、段落、表格、图片、链接生成稳定 Markdown，再按模块拆分这个 Markdown 表示。

## 适用场景

- 已经存在 `modules/` 目录，需要把源需求正文拆进去。
- 需要保留 Markdown 图片、链接、附件引用。
- 需要支持 Word PRD 中的标题、图片、表格、外部链接。
- 需要分模块调用 Codex/Codex 复核，而不是把整个大需求放进一个对话。
- 需要生成拆分计划、manifest、coverage、validation 报告。

## 不适用场景

- 还没有模块目录，需要先规划目录。
- 想让模型总结、重写、翻译或润色需求。
- 想生成测试点、测试方案、测试用例。
- 要求 docx 输出 100% 还原 Word 版式。当前输出是 Markdown requirement pack + assets。

## 核心原则

1. **已确认目录是拆分依据**：脚本扫描现有模块目录，不在本阶段新设计目录。
2. **模型只做判断**：Codex/Codex 只能选择或复核行号范围，不能生成最终正文。
3. **Markdown 保持原文切片**：Markdown 输出必须来自源文件原始 bytes。
4. **docx 使用 canonical Markdown**：docx 输出必须来自脚本生成的稳定 Markdown 表示。
5. **先 inspect/plan 后 split**：先生成拆分计划并检查，再写入模块目录。
6. **必须 validate**：拆分后必须运行校验。
7. **冲突不自动处理**：unmapped、ambiguous、agent_conflict 必须停下来让用户确认。

## 输入信息

执行前需要确认：

1. `source`：源需求文档路径，支持 `.md/.markdown/.docx`。
2. `source_format`：`auto`、`markdown` 或 `docx`。
3. `modules_root`：已确认模块目录根路径。
4. `attachments_root`：附件目录，没有则为空。
5. `scope_headings`：需要拆分的起始章节标题数组；为空表示全篇。
6. `stop_headings`：拆分停止章节标题数组；没有则为空数组。
7. `run_dir`：本次运行的过程产物输出目录；为空时自动生成在模块目录附近。
8. `output_name`：模块需求包文件名，默认 `00-module-requirement-pack.md`。
9. `write_scope`：通常使用 `direct`。
10. 是否启用模型复核：`agent`、`agent_scope`、`agent_task`。

如果缺少 `modules_root` 或目录为空，不要继续拆分，应提示用户先使用 `module-directory-generator`。

## 配置文件

复制模板：

```text
config/split-config.template.json
```

生成项目本地配置，例如：

```text
02-requirement-split/requirement-split-work/split-config.local.json
```

推荐配置格式：

```json
{
  "schema_version": 2,
  "source": "D:\\project\\需求文档.docx",
  "source_format": "auto",
  "modules_root": "D:\\project\\02-requirement-split\\modules",
  "attachments_root": "",
  "scope_headings": ["产品详细功能说明"],
  "stop_headings": ["非功能性需求", "附录", "术语说明"],
  "run_dir": "D:\\project\\02-requirement-split\\requirement-split-work\\runs\\run-001",
  "output_name": "00-module-requirement-pack.md",
  "write_scope": "direct",
  "module_dir_pattern": "^(?P<prefix>[A-Za-z]+)-(?P<id>\\d+(?:-\\d+)*)-(?P<title>.+)$",
  "docx": {
    "heading_style_map": {
      "dingding-heading1": 1,
      "dingding-heading2": 2,
      "dingding-heading3": 3,
      "dingding-heading4": 4,
      "Heading1": 1,
      "Heading2": 2,
      "Heading3": 3,
      "Heading4": 4,
      "标题 1": 1,
      "标题 2": 2,
      "标题 3": 3,
      "标题 4": 4
    },
    "ignore_toc": true,
    "asset_dir_name": "assets",
    "table_format": "markdown"
  },
  "agent": "none",
  "agent_scope": "problems",
  "agent_task": "review",
  "claude_command": "",
  "codex_command": ""
}
```

旧字段仍兼容：

```json
{
  "scope_heading": "产品详细功能说明",
  "stop_heading": "非功能性需求"
}
```

内部会等价转换为：

```json
{
  "scope_headings": ["产品详细功能说明"],
  "stop_headings": ["非功能性需求"]
}
```

## 多 scope / 多 stop 规则

- `scope_headings` 支持多个起始章节。
- `stop_headings` 支持多个停止章节。
- 每个 scope heading 生成一个拆分范围。
- 范围起点：scope heading 后的第一行。
- 范围终点：该 scope 自然结束，或遇到任意 stop heading，取更早者。
- 多个 scope 范围如果重叠，脚本会报错，避免重复拆分。

示例：

```json
{
  "scope_headings": ["产品详细功能说明", "通用需求"],
  "stop_headings": ["非功能性需求", "附录"]
}
```

含义：只拆 `产品详细功能说明` 和 `通用需求` 范围内的内容，遇到 `非功能性需求` 或 `附录` 任意一个标题就停止当前范围。

## docx 处理说明

脚本使用 Python 标准库读取 `.docx` 内部 OOXML：

```text
word/document.xml
word/styles.xml
word/numbering.xml
word/_rels/document.xml.rels
word/media/*
```

处理能力：

- 根据段落样式识别标题，如 `dingding-heading1` ~ `dingding-heading4`、`Heading1`、`标题 1`。
- 默认忽略 Word 目录/TOC，避免把目录项当作模块标题。
- 段落转换为 Markdown 段落。
- 表格转换为 Markdown table；合并单元格会保留文字，但不保证视觉结构完全一致。
- 外部链接转换为 Markdown 链接。
- 图片从 `word/media` 提取，拆分时复制到模块目录下的 `assets/`。

大型 docx 可以处理，但前提是：模块目录必须和该 docx 的标题结构匹配。不能用另一个项目的模块目录直接套到不同 PRD。

## 执行流程

### 步骤 1：inspect

```powershell
py -3 "${CLAUDE_SKILL_DIR}\scripts\document_split_orchestrator.py" inspect --config "<config.json>"
```

如果 `CLAUDE_SKILL_DIR` 不可用，从项目根目录运行：

```powershell
py -3 ".Codex\skills\requirement-document-splitter\scripts\document_split_orchestrator.py" inspect --config "<config.json>"
```

检查：

- 源文档类型是否正确。
- Markdown/docx 标题树是否正确。
- docx 图片、表格、链接统计是否合理。
- 模块目录树是否正确。
- 映射行号是否合理。
- 是否存在 unmapped / ambiguous。

### 步骤 2：plan

```powershell
py -3 "${CLAUDE_SKILL_DIR}\scripts\document_split_orchestrator.py" plan --config "<config.json>"
```

输出：

- `split-plan.json`
- `coverage.tsv`

### 步骤 3：可选模型复核

每个模块都调用 Codex 复核：

```powershell
py -3 "${CLAUDE_SKILL_DIR}\scripts\document_split_orchestrator.py" plan --config "<config.json>" --agent Codex --agent-scope all --agent-task review --Codex-command "Codex -p"
```

Codex + Codex 双复核：

```powershell
py -3 "${CLAUDE_SKILL_DIR}\scripts\document_split_orchestrator.py" plan --config "<config.json>" --agent both --agent-scope all --agent-task review --Codex-command "Codex -p" --codex-command "codex exec"
```

模型输出只允许是行号范围判断。最终正文仍由脚本复制。

### 步骤 4：split

```powershell
py -3 "${CLAUDE_SKILL_DIR}\scripts\document_split_orchestrator.py" split --config "<config.json>"
```

如需覆盖已有生成文件，才加：

```powershell
--overwrite
```

### 步骤 5：validate

```powershell
py -3 "${CLAUDE_SKILL_DIR}\scripts\document_split_orchestrator.py" validate --manifest "<run_dir>\split-manifest.json"
```

校验通过后，才能告诉用户拆分完成。

## 输出文件

模块目录中生成：

```text
<module-dir>/00-module-requirement-pack.md
<module-dir>/assets/xxx.png    # docx 图片按需生成
```

`run_dir` 中生成：

```text
split-plan.json
split-manifest.json
coverage.tsv
validation-report.json
agent-decisions/   # 仅启用 agent 时可能生成
```

## write_scope 说明

- `leaf`：只写叶子模块。
- `all`：所有映射模块都写，可能产生父子重复内容。
- `direct`：推荐。写叶子模块，以及父模块标题下确实存在独立正文的部分；纯容器父模块不重复写子模块内容。

## 版本管理建议

通常建议提交：

- 确认后的模块需求包。
- 这个 skill 的脚本和说明。

通常不建议提交：

- `runs/` 过程目录。
- 本地绝对路径配置文件。
- agent stdout/stderr 决策日志。

如需保留审计记录，可把关键 manifest/report 复制到正式 review 目录。

## 质量检查清单

完成前确认：

- [ ] 已有模块目录，不是在本 skill 中临时生成的。
- [ ] config 中路径和章节正确。
- [ ] inspect 无异常映射。
- [ ] docx 标题样式被正确识别。
- [ ] docx 目录/TOC 没有被误识别为业务模块。
- [ ] plan 无 unresolved 状态。
- [ ] split 写入文件数量符合预期。
- [ ] validate 通过。
- [ ] Markdown 输出与源文档原文切片一致。
- [ ] docx 输出与 canonical Markdown 切片一致。
- [ ] 图片、附件、链接未被模型改写。

## 与其他 skill 的关系

如果还没有模块目录，先使用：

```text
module-directory-generator
```

模块需求包稳定后，如需生成测试用例，再使用：

```text
testcase-generator
```
