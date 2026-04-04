# Bangumi Skill

OpenClaw Skill for Bangumi (bgm.tv) - 番剧搜索、新番追踪、评分查询。

## 版本选择

本 Skill 提供三个独立版本，按需下载：

### bangumi_explorer - 信息查询版（当前版本 bangumi_explorer-1.0）
- **功能**：搜索番剧、查看详情、当季番表、评分排行、查询声优/Staff
- **特点**：无需登录，开箱即用
- **适用**：只需要查询公开信息的用户
- **下载**：[bangumi_explorer-1.0](https://github.com/MountLynx/bangumi_skill/releases/tag/bangumi_explorer-1.0)

### bangumi_tracker - 本地用户版（开发中）
- **功能**：bangumi_explorer 全部功能 + OAuth 登录 + 收藏管理 + 观看进度标记
- **特点**：需要 Bangumi 账号授权
- **适用**：需要管理个人收藏和进度的用户

### bangumi_tracker_web - MCP Server 版（开发中）
- **功能**：bangumi_tracker 全部功能 + MCP 协议封装
- **特点**：支持多用户，适合服务器部署
- **适用**：多用户环境或远程部署场景

## 安装

1. 下载对应版本的 ZIP 包（如 `bangumi_explorer-1.0.zip`）
2. 解压到 OpenClaw skills 目录：
   - Windows: `%USERPROFILE%\.openclaw-autoclaw\skills\bangumi_explorer\`
   - macOS/Linux: `~/.openclaw-autoclaw/skills/bangumi_explorer/`
3. 重启 OpenClaw Agent

## 使用

安装后，Agent 会自动识别 Bangumi 相关查询。具体命令请参考各版本目录下的 `SKILL.md`。

### bangumi_explorer 示例

```bash
# 搜索番剧
python bangumi.py search "葬送的芙莉莲"

# 查看详情
python bangumi.py info 428477

# 当季新番
python bangumi.py season

# 评分排行
python bangumi.py rank --top 10
```

## 技术说明

- **Python**: 3.9+（推荐，Token 效率高）
- **无 Python**: 可用，但 Token 消耗增加 3-5 倍
- **依赖**: 零第三方依赖（纯标准库）
- **API**: Bangumi API v0
- **缓存**: `~/.bangumi/cache/`（自动过期清理）
- **限速**: 0.5s 请求间隔（尊重 Bangumi API）

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

| 版本 | Tag | 发布日期 | 说明 |
|------|-----|----------|------|
| bangumi_explorer-1.0 | `bangumi_explorer-1.0` | 2026-04-04 | 信息查询版，支持公开 API 查询 |

## 许可证

MIT License
