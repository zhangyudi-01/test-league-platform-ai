# requirement-document-splitter scripts 说明

本目录是 `requirement-document-splitter` skill 的脚本实现区，负责把已经确认好的模块目录与源需求文档进行匹配，并将需求正文拆分到对应模块目录中。

## 目录结构

```text
scripts/
├── document_split_orchestrator.py      # CLI 入口脚本
└── requirement_splitter/               # 具体实现包
    ├── __init__.py
    ├── agents.py
    ├── attachments.py
    ├── cli.py
    ├── config.py
    ├── docx_source.py
    ├── mapper.py
    ├── markdown_source.py
    ├── modules.py
    ├── source_factory.py
    ├── sources.py
    ├── validate.py
    └── writer.py
```

## 执行入口

外部调用时只需要使用：

```powershell
py -3 ".claude\skills\requirement-document-splitter\scripts\document_split_orchestrator.py" inspect --config "<config.json>"
py -3 ".claude\skills\requirement-document-splitter\scripts\document_split_orchestrator.py" plan --config "<config.json>"
py -3 ".claude\skills\requirement-document-splitter\scripts\document_split_orchestrator.py" split --config "<config.json>"
py -3 ".claude\skills\requirement-document-splitter\scripts\document_split_orchestrator.py" validate --manifest "<run_dir>\split-manifest.json"
```

`document_split_orchestrator.py` 只是一个很薄的入口，实际逻辑在 `requirement_splitter/` 包中。

## 文件职责

### `document_split_orchestrator.py`

CLI 入口脚本。

职责：

- 加载 `requirement_splitter.cli.main`。
- 保持外部命令路径稳定。
- 不承载具体业务逻辑。

### `requirement_splitter/cli.py`

命令行编排层。

职责：

- 定义 `inspect`、`plan`、`split`、`validate` 子命令。
- 串联配置读取、源文档解析、模块扫描、映射、写入和校验。
- 输出用户可读的执行结果。

### `requirement_splitter/config.py`

配置读取和规范化。

职责：

- 读取 JSON config。
- 校验必填字段，如 `source`、`modules_root`。
- 支持旧字段 `scope_heading` / `stop_heading`。
- 规范化为新字段 `scope_headings` / `stop_headings`。
- 解析相对路径。
- 设置通用默认值。

注意：不要在这里写死某个项目的需求路径、模块路径或章节标题。

### `requirement_splitter/sources.py`

源文档抽象和通用工具。

职责：

- 定义 `DocumentSource`、`Heading`、`ScopeRange`、`ScopeResolver`。
- 提供标题归一化、hash、JSON 写入、链接/图片 inventory 等通用方法。
- 处理多 `scope_headings` / 多 `stop_headings` 的范围解析。

### `requirement_splitter/markdown_source.py`

Markdown 源文档适配器。

职责：

- 读取 Markdown 原始 bytes。
- 解析 ATX 标题，即 `#` / `##` / `###`。
- 忽略代码块中的伪标题。
- 按原始 bytes 做切片。

这是 Markdown 模式“一字不改”的核心保障。

### `requirement_splitter/docx_source.py`

Word `.docx` 源文档适配器。

职责：

- 使用 Python 标准库读取 OOXML。
- 解析 `word/document.xml`、`word/styles.xml`、`word/_rels/document.xml.rels`、`word/media/*`。
- 根据标题样式识别章节层级，例如 `dingding-heading1`、`Heading1`、`标题 1`。
- 将 docx 稳定转换为 canonical Markdown。
- 提取图片并记录资产信息。
- 将表格转换为 Markdown table。
- 将外部链接转换为 Markdown 链接。

注意：docx 不能像 Markdown 一样做原始字节切片。docx 模式的保证是“canonical Markdown 稳定可校验”，不是“Word 原始字节不变”。

### `requirement_splitter/source_factory.py`

源文档工厂。

职责：

- 根据 `source_format` 或文件后缀选择 `MarkdownSource` 或 `DocxSource`。
- 支持 `auto`、`markdown`、`docx`。

### `requirement_splitter/modules.py`

模块目录扫描。

职责：

- 扫描已经确认好的模块目录。
- 根据 `module_dir_pattern` 解析模块 ID、层级、标题。
- 建立父子模块关系。

本文件不负责创建模块目录。创建目录应由 `module-directory-generator` skill 完成。

### `requirement_splitter/mapper.py`

模块与源文档标题映射。

职责：

- 根据模块标题匹配源文档标题。
- 使用父级路径和层级深度消除歧义。
- 生成 `mapped`、`unmapped`、`ambiguous` 等状态。
- 生成 plan 中的模块映射信息。

### `requirement_splitter/agents.py`

Claude/Codex 复核层。

职责：

- 可选调用本机 Claude Code CLI 或 Codex CLI。
- 支持 `agent_task=review` 或 `agent_task=select`。
- 支持 `agent_scope=problems` 或 `agent_scope=all`。
- 只允许模型返回行号范围 JSON。

重要原则：模型不能生成最终需求正文。

### `requirement_splitter/attachments.py`

本地附件索引。

职责：

- 扫描 `attachments_root`。
- 计算附件 hash。
- 根据模块名称或正文内容推测附件候选关系。

当前只记录候选关系，不主动改写正文链接。

### `requirement_splitter/writer.py`

写入模块需求包。

职责：

- 根据 plan 中的范围写入模块文件。
- Markdown 模式写入原始 Markdown 切片。
- docx 模式写入 canonical Markdown 切片。
- 复制 docx 中被当前模块引用的图片到模块 `assets/`。
- 生成 `split-manifest.json` 和 `coverage.tsv`。

### `requirement_splitter/validate.py`

校验拆分结果。

职责：

- 校验源文档 hash。
- 校验 canonical Markdown hash。
- 校验模块输出是否等于对应源切片。
- 校验图片/链接 inventory。
- 校验 docx 图片资产是否存在且 hash 一致。
- 生成 `validation-report.json`。

## 执行链路

### inspect

```text
config
  -> source_factory
  -> MarkdownSource / DocxSource
  -> ModuleTree
  -> ScopeResolver
  -> DeterministicMapper
  -> 打印标题树、模块树、映射摘要
```

### plan

```text
inspect 链路
  -> 可选 AgentRunner
  -> split-plan.json
  -> coverage.tsv
```

### split

```text
plan 链路
  -> writer.write_split
  -> <module-dir>/00-module-requirement-pack.md
  -> docx assets
  -> split-manifest.json
  -> coverage.tsv
```

### validate

```text
split-manifest.json
  -> 重新加载源文档
  -> 校验输出文件和资产
  -> validation-report.json
```

## 维护原则

1. **不要在脚本中写死项目路径**。
   - 项目差异应通过 config 传入。

2. **不要让模型生成正文**。
   - 模型只能 review/select 行号范围。

3. **Markdown 模式必须保持 byte slice**。
   - 不要对 Markdown 正文做格式化、重排或重新渲染。

4. **docx 模式必须保持转换稳定**。
   - 同一 docx、同一配置，多次转换应得到相同 canonical Markdown hash。

5. **遇到冲突要显式报告**。
   - `unmapped`、`ambiguous`、`agent_conflict` 不应静默通过。

6. **过程产物默认不进 Git**。
   - `runs/`、本地 config、agent 日志通常是运行产物。

## 后续扩展方向

可以考虑扩展：

- 输出每个模块为 `.docx`。
- 表格使用 HTML 输出以更好保留合并单元格。
- 支持更多 Word 标题样式。
- 支持 PDF 或 HTML 源文档。
- 增加 fixture 测试目录。
- 增加 config schema 校验文件。
