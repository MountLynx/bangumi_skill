# Bangumi Skill

OpenClaw/Vercel Skills for Bangumi (bgm.tv) - 番剧搜索、新番追踪、评分查询。

## 快速开始

### 使用 Vercel Skills CLI 安装

```bash
# 安装信息查询版（推荐，无需登录）
npx skills add MountLynx/bangumi_skill --skill bangumi-explorer

# 安装本地用户版（需要 OAuth 授权，开发中）
npx skills add MountLynx/bangumi_skill --skill bangumi-tracker

# 安装 MCP Server 版（多用户支持，开发中）
npx skills add MountLynx/bangumi_skill --skill bangumi-tracker-web

# 安装所有技能
npx skills add MountLynx/bangumi_skill --all
```

### 手动安装

1. 下载对应版本的 ZIP 包（如 `bangumi-explorer-1.0.zip`）
2. 解压到对应目录：
   - OpenClaw: `~/.openclaw-autoclaw/skills/`
   - Claude Code: `~/.claude/skills/`
   - Cursor: `~/.cursor/skills/`
   - 其他 Agent: 见 [Vercel Skills 文档](https://skills.sh/docs)
3. 重启 Agent

## 版本选择

本仓库提供三个独立技能，按需选择：

| 技能 | 状态 | 功能 | 适用场景 |
|------|------|------|----------|
| **bangumi-explorer** | ✅ 可用 | 公开查询：搜索、详情、番表、排行、人物 | 无需登录，开箱即用 |
| **bangumi-tracker** | 🚧 开发中 | + OAuth 登录、收藏管理、观看进度 | 需要管理个人收藏 |
| **bangumi-tracker-web** | 🚧 开发中 | + MCP Server、多用户、Web 授权 | 服务器部署、多用户 |

### bangumi-explorer（推荐）

- **功能**：搜索番剧、查看详情、当季番表、评分排行、查询声优/Staff
- **特点**：无需登录，零配置，开箱即用
- **适用**：只需要查询公开信息的用户

### bangumi-tracker

- **功能**：bangumi-explorer 全部功能 + OAuth 登录 + 收藏管理 + 观看进度标记
- **特点**：需要 Bangumi 账号授权
- **适用**：需要管理个人收藏和进度的用户
- **安全存储**：敏感信息（client_secret、access_token、refresh_token）存储在 Windows 凭据管理器中，非 Windows 系统自动回退到文件存储
- **状态**：🚧 开发中

### bangumi-tracker-web

- **功能**：bangumi-tracker 全部功能 + MCP 协议封装
- **特点**：支持多用户，适合服务器部署
- **适用**：多用户环境或远程部署场景
- **状态**：🚧 开发中

## 使用示例

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

## 技术说明

- **Python**: 3.9+（推荐，Token 效率高）
- **无 Python**: 可用，但 Token 消耗增加 3-5 倍
- **依赖**: 零第三方依赖（纯标准库）
- **API**: Bangumi API v0
- **缓存**: `~/.bangumi/cache/`（自动过期清理）
- **限速**: 0.5s 请求间隔（尊重 Bangumi API）

### bangumi-tracker 信息存储

bangumi-tracker 会安全存储您的敏感信息：

| 信息 | 存储位置 (Windows) | 存储位置 (其他系统) |
|------|-------------------|-------------------|
| client_id | `~/.bangumi/config.json` | `~/.bangumi/config.json` |
| client_secret | Windows 凭据管理器 | `~/.bangumi/config.json` |
| access_token | Windows 凭据管理器 | `~/.bangumi/token.json` |
| refresh_token | Windows 凭据管理器 | `~/.bangumi/token.json` |
| expires_at | `~/.bangumi/token.json` | `~/.bangumi/token.json` |

**安全说明**：
- Windows 用户：client_secret、access_token、refresh_token 会存储在 Windows 凭据管理器中，比普通文件更安全
- 非 Windows 用户：自动回退到文件存储
- 如需清除所有存储的信息，可运行 `python bangumi_tracker.py logout`

### 关于 Python 环境

**推荐方案**（有 Python）：
- 使用 `bangumi.py` 脚本执行查询
- Token 消耗低（~700 tokens/次）
- 响应快，有本地缓存

**降级方案**（无 Python）：
- Agent 直接调用 Bangumi API
- Token 消耗高（~3000-5000 tokens/次）
- 无缓存，响应较慢

Skill 会自动检测 Python 环境并提供相应方案。

## 版本历史

| 技能 | 版本 | 发布日期 | 说明 |
|------|------|----------|------|
| bangumi-explorer | 1.0 | 2026-04-04 | 信息查询版，支持公开 API 查询 |

## 相关链接

- [Vercel Skills](https://skills.sh)
- [Bangumi API](https://github.com/bangumi/api)
- [OpenClaw](https://openclaw.ai)

## 许可证

MIT License
