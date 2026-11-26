# 玻尔产品周赛·北化分站赛第一期 — 参赛作品集

本仓库包含玻尔「产品周赛·北化分站赛第一期」5 个赛题的 Skill 作品。每个子目录对应一个赛题，可独立查看。

## 作品清单

| 目录 | 赛题 | 说明 |
|---|---|---|
| `paper-to-slides/` | 论文转学术 PPT | 把论文组织成可编辑学术 PPT，保留页级证据映射、讲稿/备注与渲染预览 |
| `pdf-parser/` | 文献文档解析 | 多栏阅读顺序、表格重建、章节结构、公式符号识别，逐元素附 page+bbox 证据 |
| `kg-builder/` | 文献知识图谱构建 | 从两篇论文抽取实体/关系、绑定证据、跨篇对齐，输出可查询图谱 |
| `note-builder/` | 文献总结与结构化笔记 | 按论文自身章节做结构化笔记，逐条锚点回原文 |
| `nanopub/` | Nanopublication | 把结论拆成单条可验证断言 + 证据 + 来源，导出机器可读结构 |

## 每个 Skill 的结构

```
<skill>/
├── SKILL.md          # Skill 主入口（name/description + 完整流程 + 异常处理）
├── scripts/          # 实际运行脚本
├── references/       # 规则与异常处理说明
└── assets/           # JSON schema
```

## 通用约定

- 运行时输入 `/input/case.json` + `task.md`，工作区 `/app/work`，输出 `/app/output/result.json`。
- `result.json` 回填 `task.md` 的 `output_contract` 字段 + `case_id` + `status/sources/uncertainty/change_log`。
- 资源上限：≤50 个 UTF-8 文本文件，单文件 ≤500KB，总量 ≤2MB，无符号链接。
- 所有脚本纯 Python 标准库，无第三方依赖。
