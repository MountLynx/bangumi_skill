# Bangumi Skill 项目状态文档

> 最后更新：2026-04-03
> 负责人：Claw酱
> 目的：上下文丢失时快速恢复项目状态

---

## 一、项目概览

### 命名规范（口头约定）

| 版本 | 目录名 | 功能定位 |
|------|--------|----------|
| V1 | `bangumi_explorer` | 信息查询版（公开API，无需认证） |
| V2 | `bangumi_tracker` | 本地用户版（OAuth + 收藏管理） |
| V3 | `bangumi_tracker_web` | MCP服务器版（多用户 + 远程部署） |

### 当前进度

- ✅ **bangumi_explorer 已完成** — 功能完整，待测试验证
- ⏳ **bangumi_tracker 未开始** — 待 bangumi_explorer 验证后开发
- ⏳ **bangumi_tracker_web 未开始** — 待 bangumi_tracker 完成后开发

---

## 二、文件结构

```
bangumi_skill/
├── PROJECT_STATUS.md          # ← 本文件（项目状态）
├── bangumi_eval.md            # 可行性评估文档
├── bangumi-dev-plan.md        # 完整开发计划（三版详细设计）
├── git.md                     # Git管理方案（Tag策略、Release流程）
│
├── bangumi_explorer/          # ← V1 完成目录
│   ├── skill.md               # SKILL.md（极简，~50行）
│   ├── bangumi.py             # 核心脚本（~600行，零依赖）
│   └── references/
│       └── .gitkeep           # 参考文档目录（预留）
│
├── bangumi_tracker/           # ← V2 待创建（当前不存在）
│   └── (待开发)
│
└── bangumi_tracker_web/       # ← V3 待创建（当前不存在）
    └── (待开发)
```

---

## 三、bangumi_explorer 详细状态

### 功能清单

| 命令 | 状态 | 说明 |
|------|------|------|
| `search` | ✅ | 搜索条目，支持类型筛选 |
| `info` | ✅ | 条目详情（评分、标签、简介等） |
| `episodes` | ✅ | 集数列表（本篇/SP/OP/ED分组） |
| `season` | ✅ | 当季番表（按平台分组） |
| `rank` | ✅ | 评分排行 |
| `person` | ✅ | 人物搜索/详情 |

### 技术实现

- **语言**：Python 3.9+
- **依赖**：零第三方依赖（纯标准库）
- **API**：Bangumi API v0（`https://api.bgm.tv/v0`）
- **缓存**：`~/.bangumi/cache/`（自动过期清理）
- **限速**：0.5s 请求间隔
- **编码**：Windows 控制台 UTF-8 修复

### 待办

- [ ] 运行测试验证各命令正常
- [ ] 处理边界情况（API异常、空结果等）
- [ ] 准备 bangumi_explorer Release（打 Tag v1.0）

---

## 四、bangumi_tracker 规划

### 新增功能

| 命令 | 说明 |
|------|------|
| `auth` | OAuth 授权流程 |
| `config` | 配置 client_id/secret |
| `collections` | 查看我的收藏 |
| `collect` | 修改收藏状态 |
| `progress` | 标记集数观看状态 |

### 技术要点

- OAuth 2.0 流程（浏览器 + localhost 回调）
- Token 存储/自动刷新
- 认证请求封装

### 开发时机

bangumi_explorer 测试验证通过后开始

---

## 五、bangumi_tracker_web 规划

### 新增内容

- `bangumi_mcp_server.py` — MCP Server 实现
- SQLite 数据库（用户、缓存、速率限制）
- Web 授权页（多用户支持）
- MCP Tool 定义（9个工具）

### 开发时机

bangumi_tracker 完成后开始

---

## 六、快速恢复指南

### 如果上下文丢失，按以下顺序阅读：

1. **本文件**（`PROJECT_STATUS.md`）— 了解当前进度
2. **`bangumi-dev-plan.md`** — 了解详细设计
3. **`bangumi_explorer/skill.md`** — 了解 bangumi_explorer 触发词和命令
4. **`bangumi_explorer/bangumi.py`** — 查看具体实现

### 关键命令测试

```bash
# 进入 bangumi_explorer 目录
cd bangumi_skill/bangumi_explorer

# 测试搜索
python bangumi.py search "葬送的芙莉莲" --limit 3

# 测试详情
python bangumi.py info 428477

# 测试番表
python bangumi.py season

# 测试排行
python bangumi.py rank --top 10
```

---

## 七、相关文档索引

| 文档 | 用途 |
|------|------|
| `bangumi_eval.md` | 可行性评估（API调研、技术选型） |
| `bangumi-dev-plan.md` | 完整开发计划（三版详细设计、Token优化策略） |
| `git.md` | Git管理方案（分支策略、Tag管理、Release流程） |
| `bangumi_explorer/skill.md` | bangumi_explorer SKILL.md（触发词、命令说明） |

---

## 八、注意事项

1. **命名约定**：bangumi_explorer / bangumi_tracker / bangumi_tracker_web 的目录名是口头约定的，文档中未强制要求，但建议保持一致
2. **版本独立**：三个版本是独立发布的，用户按需下载，不是升级关系
3. **缓存位置**：bangumi_explorer 和 bangumi_tracker 共用 `~/.bangumi/`，bangumi_tracker_web 使用 `~/.bangumi-mcp/`
4. **API限制**：Bangumi API 要求自定义 User-Agent，已硬编码在脚本中

---

*文档由 Claw酱 维护，每次重大进度更新时请同步更新此文件。*
