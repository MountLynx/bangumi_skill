# Bangumi Skill Git 管理方案

## 一、仓库结构

采用**单一仓库 + Tag 管理**，所有版本共享同一个 `main` 分支，通过 Tag 区分不同版本的状态。

```
bangumi-skill/
├── README.md                     # 项目说明、版本选择指南、使用教程
├── SKILL.md                      # 随版本变化，对应不同版本的触发词与命令说明
├── bangumi.py                    # 核心脚本，bangumi_explorer 仅查询，bangumi_tracker 含 OAuth 与收藏
├── bangumi_mcp_server.py         # 仅 bangumi_tracker_web 版本存在，其他版本无此文件
├── references/                   # 参考文档（可选，不随版本变化）
│   └── api_reference.md
└── .gitignore
```

**关键点**：  
- 每个 Tag 对应的根目录下文件是该版本的完整内容。  
- 用户下载某个 Tag 的源码包后，解压得到的就是对应版本的独立 Skill 目录，直接放入 OpenClaw 的 `skills` 目录即可使用。

---

## 二、分支策略

采用**线性开发**模式，所有版本开发都在 `main` 分支上依次进行，通过 Tag 标记每个版本的完成点。

```
main:   o---o---o---o---o---o---o---o---o---o
         |           |           |           |
       v1.0        v2.0        v3.0        v3.1 (hotfix)
```

- **不创建长期分支**（如 `v1`、`v2`），保持简单。
- 若需要对旧版本进行修复（如 API 变动），可创建临时分支（如 `hotfix/v1.0`），修复后打新 Tag（如 `v1.0.1`），并合并回 `main`。

---

## 三、版本开发流程

### 阶段 1：bangumi_explorer 开发与发布

```bash
# 1. 初始化仓库
git init bangumi-skill
cd bangumi-skill

# 2. 创建 bangumi_explorer 基础文件（SKILL.md, bangumi.py 等）
#    编写 bangumi_explorer 代码（仅查询功能）
#    提交
git add .
git commit -m "bangumi_explorer: 信息查询版（搜索、详情、番表、排行、人物）"

# 3. 打 Tag v1.0
git tag -a v1.0 -m "bangumi_explorer 正式版：无认证，支持公开查询"

# 4. 推送到远程（GitHub/GitLab）
git remote add origin <repo-url>
git push origin main
git push origin --tags
```

### 阶段 2：bangumi_tracker 开发

在 bangumi_explorer 基础上继续在 `main` 上开发。

```bash
# 继续在 main 上开发 bangumi_tracker 功能（OAuth、收藏管理）
# 修改 SKILL.md 增加 bangumi_tracker 命令说明
# 修改 bangumi.py 增加 OAuth 模块

git add .
git commit -m "bangumi_tracker: 添加 OAuth 授权、收藏管理、进度标记"

# 打 Tag v2.0
git tag -a v2.0 -m "bangumi_tracker 正式版：支持用户登录与收藏管理"

git push origin main
git push origin --tags
```

### 阶段 3：bangumi_tracker_web 开发

```bash
# 继续开发 bangumi_tracker_web，添加 MCP Server 文件
# 新增 bangumi_mcp_server.py
# 修改 SKILL.md 增加 MCP 配置说明
# 更新 bangumi.py（bangumi_tracker_web 中仍保留，供本地模式使用）

git add .
git commit -m "bangumi_tracker_web: 添加 MCP Server 支持，多用户 Token 管理"

git tag -a v3.0 -m "bangumi_tracker_web 正式版：MCP Server 版，支持远程多用户"

git push origin main
git push origin --tags
```

### 阶段 4：后续修复与迭代

#### 修复 bangumi_explorer 的 Bug（如 API 变更）

```bash
# 从 v1.0 创建临时分支
git checkout -b hotfix/v1.0 v1.0

# 修复问题（修改 bangumi.py 等）
git add .
git commit -m "fix: 修复 bangumi_explorer 版本中 API 地址变更导致的 404"

# 打新 Tag v1.0.1
git tag -a v1.0.1 -m "bangumi_explorer 修复版：修正 API 端点"

# 将修复合并回 main（可选，如果 main 中已存在相同问题）
git checkout main
git merge hotfix/v1.0
git push origin main

# 推送新 Tag
git push origin v1.0.1

# 删除临时分支（可选）
git branch -d hotfix/v1.0
```

**注意**：如果 `main` 分支已包含 bangumi_tracker/bangumi_tracker_web 的代码，而修复的代码与后续版本无关，合并时可能需要解决冲突。若冲突复杂，可仅将修复提交 cherry-pick 到 main，或只发布新 Tag 而不合并到 main。

---

## 四、Release 发布

在 GitHub/GitLab 上为每个 Tag 创建 Release，提供源码包下载，方便用户无需 Git 即可获取。

### Release 信息示例

| Tag    | Release 名称                    | 附件                          | 说明                           |
| ------ | ------------------------------- | ----------------------------- | ------------------------------ |
| v1.0   | bangumi_explorer 信息查询版     | bangumi-explorer-v1.0.zip     | 无认证，仅公开查询             |
| v1.0.1 | bangumi_explorer 修复版         | bangumi-explorer-v1.0.1.zip   | 修复 API 问题                  |
| v2.0   | bangumi_tracker 本地用户版      | bangumi-tracker-v2.0.zip      | 支持 OAuth 与收藏管理          |
| v3.0   | bangumi_tracker_web MCP Server 版 | bangumi-tracker-web-v3.0.zip | 支持 MCP 协议，多用户          |

**创建步骤**（以 GitHub 为例）：
1. 进入仓库 → Releases → Draft a new release
2. 选择 Tag（如 `v1.0`）
3. 填写标题和说明（简要描述该版本功能、使用方式、注意事项）
4. 点击“Publish release”，自动生成源码包下载链接

---

## 五、用户使用指南

用户在 README.md 中应看到清晰的版本选择说明：

```markdown
## 版本选择

本 Skill 提供三个独立版本，按需下载：

### bangumi_explorer - 信息查询版
- **功能**：搜索番剧、查看详情、当季番表、评分排行、查询声优/角色
- **无需登录**，开箱即用  
- **下载**：[bangumi-explorer-v1.0.zip](https://github.com/xxx/bangumi-skill/releases/download/v1.0/bangumi-explorer-v1.0.zip)

### bangumi_tracker - 本地用户版
- **功能**：bangumi_explorer 全部功能 + OAuth 登录 + 收藏管理 + 观看进度标记
- **需要**：在 Bangumi 注册应用，获取 client_id/secret，首次运行 `python bangumi.py auth` 授权  
- **下载**：[bangumi-tracker-v2.0.zip](https://github.com/xxx/bangumi-skill/releases/download/v2.0/bangumi-tracker-v2.0.zip)

### bangumi_tracker_web - MCP Server 版
- **功能**：bangumi_tracker 全部功能 + MCP 协议封装，适合多用户环境部署
- **需要**：配置 OpenClaw 的 MCP Server 设置  
- **下载**：[bangumi-tracker-web-v3.0.zip](https://github.com/xxx/bangumi-skill/releases/download/v3.0/bangumi-tracker-web-v3.0.zip)

## 安装方法

1. 下载对应版本的 ZIP 包并解压
2. 将解压后的文件夹放入 OpenClaw 的 `skills` 目录（例如 `~/.openclaw-autoclaw/skills/bangumi-tracker/`）
3. 重启 OpenClaw Agent

## 使用说明

具体命令请参考解压后文件夹中的 `SKILL.md`。
```

---

## 六、版本管理总结

| 版本 | Tag    | 文件内容                                                     | 用户获取方式        |
| ---- | ------ | ------------------------------------------------------------ | ------------------- |
| bangumi_explorer   | v1.0   | SKILL.md (仅查询) + bangumi.py (仅查询)                      | 下载 v1.0 Release   |
| bangumi_tracker   | v2.0   | SKILL.md (查询+收藏) + bangumi.py (含OAuth)                  | 下载 v2.0 Release   |
| bangumi_tracker_web   | v3.0   | SKILL.md (查询+收藏+MCP) + bangumi.py + bangumi_mcp_server.py | 下载 v3.0 Release   |
| 修复 | v1.0.1 | 同 v1.0 但修正 Bug                                           | 下载 v1.0.1 Release |

- 所有版本均从 `main` 分支的历史节点打 Tag 生成。
- 修复旧版本时，从对应 Tag 创建临时分支，修复后打新 Tag 并发布 Release，必要时合并回 `main`。
- 用户无需关心分支，直接通过 Release 下载所需版本即可。

## 七、注意事项

1. **文件存在性**：bangumi_explorer 和 bangumi_tracker 的 Release 中不应包含 `bangumi_mcp_server.py`，而 bangumi_tracker_web 的 Release 必须包含。在打 Tag 前确保文件结构正确。
2. **SKILL.md 版本同步**：每个 Tag 对应的 `SKILL.md` 应只描述该版本的功能，避免包含未实现功能的说明。
3. **README 版本区分**：README.md 本身通常不随 Tag 变化（可以保留在仓库根目录，但每个 Release 的源码包中都会包含当时版本的 README）。如果希望 README 也随版本变化，可以在每个 Tag 中保存不同内容的 README，但这会增加维护复杂度。通常 README 保持通用说明，版本特定信息在 Release 描述中说明。
4. **Git 标签命名规范**：使用语义化版本（SemVer） `v<major>.<minor>.<patch>`，如 `v1.0`、`v2.0.1`。

---

## 七、注意事项

1. **文件存在性**：V1 和 V2 的 Release 中不应包含 `bangumi_mcp_server.py`，而 V3 的 Release 必须包含。在打 Tag 前确保文件结构正确。
2. **SKILL.md 版本同步**：每个 Tag 对应的 `SKILL.md` 应只描述该版本的功能，避免包含未实现功能的说明。
3. **README 版本区分**：README.md 本身通常不随 Tag 变化（可以保留在仓库根目录，但每个 Release 的源码包中都会包含当时版本的 README）。如果希望 README 也随版本变化，可以在每个 Tag 中保存不同内容的 README，但这会增加维护复杂度。通常 README 保持通用说明，版本特定信息在 Release 描述中说明。
4. **Git 标签命名规范**：使用语义化版本（SemVer） `v<major>.<minor>.<patch>`，如 `v1.0`、`v2.0.1`。

---

通过以上方案，你可以轻松实现三个版本独立发布和维护，同时用户能够根据需求选择合适版本，无需接触 Git 操作。