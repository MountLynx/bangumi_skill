# Bangumi Skill

Agent Skills for Bangumi (bgm.tv) - 番剧搜索、新番追踪、评分查询。

## 注：项目已放弃（mcp版处于未开发状态）

已有更全面的项目 https://github.com/aronnaxlin/bgm-cli

## 快速开始

### 使用 Vercel Skills CLI安装

```bash
# 安装信息查询版（仅查询功能）
npx skills add MountLynx/bangumi_skill --skill bangumi-explorer

# 安装本地用户版（需要 OAuth 授权）
npx skills add MountLynx/bangumi_skill --skill bangumi-tracker

# 安装 MCP Server 版（多用户支持，开发中）
npx skills add MountLynx/bangumi_skill --skill bangumi-tracker-web

# 安装所有技能
npx skills add MountLynx/bangumi_skill --all
```

### 手动安装

1. 下载对应版本的 ZIP 包
2. 解压到对应目录：
   - OpenClaw: `~/.openclaw-autoclaw/skills/`
   - Claude Code: `~/.claude/skills/`
   - Cursor: `~/.cursor/skills/`
   - 其他 Agent: 见 [Vercel Skills 文档](https://skills.sh/docs)
3. 重启 Agent

### 其他

[ClawHub](https://clawhub.ai/)和[SkillHub](https://skillhub.tencent.com/)也已经发布bangumi-explorer和bangumi-tracker。

## 版本选择

本仓库提供三个版本，按需选择：

| 版本 | 状态 | 功能 | 适用场景 |
|------|------|------|----------|
| **bangumi-explorer** | ✅ 可用 | 公开查询：搜索、详情、番表、排行、人物 | 无需登录，开箱即用 |
| **bangumi-tracker** | ✅ 可用 | + OAuth 登录、收藏管理、观看进度 | 本地单用户，需要管理个人收藏 |
| **bangumi (MCP)** | 不可用 | + MCP 协议、多用户支持 | 服务器部署、多用户环境 |

### bangumi-explorer

- **功能**：搜索番剧、查看详情、当季番表、评分排行、查询声优/Staff
- **特点**：无需登录，零配置，开箱即用
- **适用**：只需要查询公开信息的用户

### bangumi-tracker

- **功能**：bangumi-explorer 全部功能 + OAuth 登录 + 收藏管理 + 观看进度标记
- **特点**：需要 Bangumi 账号授权，数据存本地
- **适用**：需要管理个人收藏的本地单用户
- **安全存储**：敏感信息（client_secret、access_token、refresh_token）存储在 Windows 凭据管理器中，非 Windows 系统自动回退到文件存储

### bangumi (MCP 版本)

- **功能**：bangumi-tracker 全部功能 + MCP 协议封装
- **特点**：多用户支持，适合服务器部署
- **适用**：多用户环境、AI Agent 集成
- **状态**：🚧 开发中

## 本地使用示例

### bangumi-explorer

```bash
# 搜索番剧
python bangumi.py search "葬送的芙莉莲"

# 查看详情
python bangumi.py info 428477

# 当季新番
python bangumi.py season

# 评分排行
python bangumi.py rank --top 10

# 查询声优
python bangumi.py person "花泽香菜"
```

### bangumi-tracker

```bash
# 首次配置（需要 Bangumi OAuth 应用凭据）
python bangumi_tracker.py config --client-id <your_client_id> --client-secret <your_client_secret>

# 进行 OAuth 授权（会打开浏览器）
python bangumi_tracker.py auth

# 查看我的收藏
python bangumi_tracker.py collections

# 添加收藏
python bangumi_tracker.py collect 428477 doing
```

#### 获得 Bangumi OAuth 凭据

1. 访问 https://bgm.tv/dev/app/create
2. 填写应用信息：
   - 应用名称：任意
   - 应用主页：任意 URL（或者`http://localhost:17321`）
   - 回调地址：`http://localhost:17321/callback`
3. 创建后获取 `client_id` 和 `client_secret`

## 技术说明

- **Python**: 3.9+
- **依赖**: 零第三方依赖（纯标准库）
- **API**: Bangumi API v0
- **缓存**: 自动过期清理
- **限速**: 0.5s 请求间隔

### 数据存储

| 版本 | 存储位置 |
|------|----------|
| bangumi-explorer | `~/.bangumi/cache/` |
| bangumi-tracker | `~/.bangumi/` + Windows 凭据管理器 |
| bangumi (MCP) | SQLite 数据库 |

**bangumi-tracker 安全存储**：
- Windows：client_secret、token 存储在 Windows 凭据管理器
- 其他系统：自动回退到文件存储
- 如需清除所有存储的信息，可运行 `python bangumi_tracker.py logout`

### 关于 Python 环境，针对bangumi-explorer

**推荐方案**（有 Python）：

- 使用 `bangumi.py`/`bangumi_tracker.py` 脚本执行
- Token 消耗低（~700 tokens/次）
- 响应快，有本地缓存

**降级方案**（无 Python）：

- Agent 直接调用 Bangumi API
- Token 消耗高（~3000-5000 tokens/次）
- 无缓存，响应较慢

Skill 会自动检测 Python 环境并提供相应方案。

## 相关链接

- [Vercel Skills](https://skills.sh)
- [Bangumi API](https://github.com/bangumi/api)
- [OpenClaw](https://openclaw.ai)

## 许可证

MIT License
