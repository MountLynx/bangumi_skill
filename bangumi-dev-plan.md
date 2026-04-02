# Bangumi MCP Skill 开发计划与实现方案

> 编写时间：2026-04-02 · 编写人：Claw酱

---

## 一、项目目标

开发一个 OpenClaw Skill，通过 Bangumi（bgm.tv）公开 API 实现：
- 新番追踪与番表整理
- 番剧搜索与信息查询
- 用户收藏与观看进度管理
- 声优/制作人员查询

分三版迭代，每版独立可用。

---

## 二、Token 优化策略（核心原则）

### 设计理念

SKILL.md 每次触发都会加载到上下文，消耗 token。因此：

| 层级 | 职责 | Token 开销 |
|------|------|-----------|
| **SKILL.md** | 触发判断 + 调用指令模板 | 每次 ~500-900 token（固定开销） |
| **脚本** | API 调用、数据解析、缓存、错误处理、格式化输出 | 0（本地执行，不进上下文） |
| **脚本输出** | 精简的文本结果 | 变动（由脚本输出质量决定） |

### 具体措施

1. **Prompt 极简** — SKILL.md 只写「什么时候用」和「怎么调」，不写 API 细节、数据结构、字段说明
2. **脚本全包** — 所有业务逻辑、数据清洗、错误重试、缓存策略全在脚本内
3. **输出精简** — 脚本直接输出格式化文本，不输出原始 JSON，agent 拿到即用
4. **避免重复加载** — 三版共用一套脚本，SKILL.md 按版本递增，不重复写基础指令

---

## 三、技术架构

### 整体架构

```
┌─────────────────────────────────────────────────────┐
│                    OpenClaw Agent                     │
│                                                       │
│  读取 SKILL.md → 判断触发 → exec 调用脚本 → 读取输出  │
└──────────────────────┬──────────────────────────────┘
                       │ subprocess / exec
                       ▼
┌─────────────────────────────────────────────────────┐
│              bangumi.py（核心脚本）                    │
│                                                       │
│  CLI 解析 → API 调用 → 缓存 → 数据清洗 → 格式化输出   │
└──────────────────────┬──────────────────────────────┘
                       │ HTTPS
                       ▼
┌─────────────────────────────────────────────────────┐
│              Bangumi API (api.bgm.tv/v0/)             │
│                                                       │
│  V1: 无认证（搜索/详情/番表/排行）                     │
│  V2: OAuth（收藏/进度/用户信息）                       │
│  V3: 同 V2 + MCP 协议封装                             │
└─────────────────────────────────────────────────────┘
```

### V3 额外架构

```
┌─────────────────────┐      MCP       ┌─────────────┐
│   MCP Server        │◄──────────────►│  OpenClaw    │
│   (bangumi-mcp)     │                │  Agent       │
│                     │                └─────────────┘
│  - Tool 暴露        │
│  - SQLite 存储      │
│  - Token 自动刷新    │
│  - 请求缓存         │
│  - 速率限制         │
└─────────┬───────────┘
          │ REST
          ▼
┌─────────────────────┐
│   Bangumi API       │
└─────────────────────┘
```

---

## 四、文件结构

```
C:\Users\xingy\.openclaw-autoclaw\skills\bangumi-tracker\
├── SKILL.md                    # Skill 定义
├── bangumi.py                  # 核心脚本（V1+V2）
├── bangumi_mcp_server.py       # MCP Server（V3）
└── references\
    └── api_reference.md        # API 参考文档（不在 SKILL.md 中，agent 不自动加载）
```

### 用户本地数据（V2+）

```
~/.bangumi/
├── config.json     # { "client_id": "", "client_secret": "" }
├── token.json      # { "access_token": "", "refresh_token": "", "expires_at": "" }
└── cache/
    ├── search_*.json    # 搜索缓存（1h）
    ├── subject_*.json   # 条目缓存（24h）
    └── season_*.json    # 番表缓存（6h）
```

### V3 服务器数据

```
~/.bangumi-mcp/
├── config.json     # 服务器配置
├── data.db         # SQLite（用户 token + 缓存）
└── logs/           # 日志
```

---

## 五、Bangumi API 映射

### V1 使用的端点（无需认证）

| 功能 | 方法 | 端点 | 参数 |
|------|------|------|------|
| 搜索番剧 | POST | `/v0/search/subjects` | `keyword`, `type`, `limit`, `offset` |
| 条目详情 | GET | `/v0/subjects/{id}` | - |
| 集数列表 | GET | `/v0/episodes` | `subject_id`, `limit`, `offset` |
| 当季番表 | GET | `/v0/subjects` | `type=2`, `year`, `month`, `sort=date` |
| 评分排行 | GET | `/v0/subjects` | `type`, `sort=rank`, `limit` |
| 人物详情 | GET | `/v0/persons/{id}` | - |
| 人物作品 | GET | `/v0/persons/{id}/subjects` | `type`, `limit` |
| 角色详情 | GET | `/v0/characters/{id}` | - |

### V2 新增端点（需要 OAuth）

| 功能 | 方法 | 端点 | 参数 |
|------|------|------|------|
| 用户收藏 | GET | `/v0/users/{name}/collections` | `type`, `subject_type`, `limit` |
| 修改收藏 | POST | `/v0/users/-/collections/{id}` | `type`（wish/doing/collect/on_hold/dropped） |
| 标记集数 | PUT | `/v0/users/-/collections/{id}/episodes` | `episode_id`, `type` |
| 获取 token | POST | `/v0/oauth/access_token` | `grant_type`, `client_id`, `client_secret`, `code` |
| 刷新 token | POST | `/v0/oauth/access_token` | `grant_type=refresh_token`, `refresh_token` |

### 请求头要求

```
User-Agent: clawbot/1.0 (private)    # 必填，默认 UA 会被 403
Authorization: Bearer <token>        # V2 需要时
Content-Type: application/json       # POST 请求
```

### 速率限制策略

| 操作类型 | 间隔 | 缓存时间 |
|----------|------|----------|
| 搜索 | 0.5s | 1 小时 |
| 条目详情 | 0.5s | 24 小时 |
| 当季番表 | 1s | 6 小时 |
| 收藏操作 | 1s | 不缓存（实时） |

---

## 六、V1 详细设计：信息查询版

### SKILL.md 设计（目标 ~50 行，~500 token）

```
结构：
1. 元信息（name/description/triggers）          ~10 行
2. 触发条件                                      ~5 行
3. 命令列表（6 条，每条 1 行示例）                ~15 行
4. 输出格式说明（1 个示例）                       ~10 行
5. 注意事项                                      ~5 行
6. 版本标记                                      ~5 行
```

**触发词**：`查番`、`bgm`、`bangumi`、`番剧搜索`、`当季新番`、`番表`、`查评分`、`查声优`、`查角色`

### 脚本命令设计

```bash
# 1. 搜索番剧
python bangumi.py search "葬送的芙莉莲" [--type anime|book|game|music|real] [--limit 10]

# 2. 条目详情
python bangumi.py info <subject_id>

# 3. 集数列表
python bangumi.py episodes <subject_id>

# 4. 当季番表
python bangumi.py season [--year 2026] [--month 4]

# 5. 评分排行
python bangumi.py rank [--type anime] [--top 20]

# 6. 人物查询
python bangumi.py person <关键词>
```

### 脚本输出格式规范

#### 搜索结果

```
【搜索结果】"葬送的芙莉莲" — 找到 3 条

1. ⭐ 9.2 | Rank #3
   葬送的芙莉莲 / 葽の吃音 — Fern (ID: 428477)
   TV · 28集 · 2023-10 放送
   标签：奇幻、冒险、魔法、治愈

2. ⭐ 8.5 | Rank #158
   ...
```

#### 条目详情

```
【葬送的芙莉莲】 ⭐ 9.2 | Rank #3
原名：Frieren: Beyond Journey's End / フリーレンの旅
类型：TV · 28集 · 2023-10-06 ~ 2024-03-22
制作：Madhouse / 斋藤圭一郎 / 铃木智寻
评分：9.2（42847人评分）★9>★8>★10>★7>★6
标签：奇幻(1200) 冒险(800) 魔法(600) 治愈(500) ...
收藏：在看 2100 | 看过 38000 | 想看 5200 | 搁置 800 | 抛弃 200

简介：勇者一行击败魔王后，千年精灵魔法使芙莉莲踏上了理解人类的旅途……
```

#### 当季番表

```
【2026年4月新番】共 42 部

📺 TV 动画
10/06（周六）┃ 葬送的芙莉莲 第2期 | ⭐ 9.0 | Madhouse
10/06（周六）┃ XXX | ⭐ 新番 | Studio
10/07（周日）┃ XXX | ⭐ 新番 | Studio

📺 Web 动画
...

📺 剧场版/OVA
...
```

### 脚本内部模块划分

```python
# bangumi.py 结构（约 300 行）

# === 常量 ===
BASE_URL = "https://api.bgm.tv/v0"
HEADERS = {"User-Agent": "clawbot/1.0 (private)"}
TYPE_MAP = {"anime": 2, "book": 1, "game": 4, "music": 3, "real": 6}

# === 网络层 ===
def api_get(path, params=None, use_cache=True) -> dict
def api_post(path, data=None) -> dict

# === 缓存层 ===
def get_cache(key) -> dict | None
def set_cache(key, data, ttl_hours)

# === 格式化层 ===
def format_search(results) -> str
def format_info(subject) -> str
def format_episodes(episodes) -> str
def format_season(subjects) -> str
def format_rank(subjects) -> str
def format_person(person) -> str

# === 命令入口 ===
def cmd_search(args)
def cmd_info(args)
def cmd_episodes(args)
def cmd_season(args)
def cmd_rank(args)
def cmd_person(args)

# === CLI ===
def main()  # argparse + 路由
```

### 依赖

- Python 3.9+
- 仅标准库：`urllib`, `json`, `argparse`, `os`, `time`, `datetime`, `pathlib`
- 不引入第三方依赖，保证零配置即可运行

---

## 七、V2 详细设计：本地用户版

### SKILL.md 新增内容（目标增量 ~20 行，~200 token）

在 V1 基础上新增：
1. OAuth 首次授权流程说明
2. 4 条新命令
3. 错误提示（token 过期/未授权）

### 新增脚本命令

```bash
# 1. OAuth 授权（首次使用）
python bangumi.py auth
# → 自动打开浏览器 → 用户授权 → 回调 localhost → 保存 token

# 2. 查看我的收藏
python bangumi.py collections [--type wish|doing|collect|on_hold|dropped] [--cat anime|book|game]

# 3. 修改收藏状态
python bangumi.py collect <subject_id> <type>
# type: wish(想看) | doing(在看) | collect(看过) | on_hold(搁置) | dropped(抛弃)

# 4. 标记集数观看状态
python bangumi.py progress <subject_id> <episode_id> <type>
# type: watched(看过) | queue(想看) | drop(抛弃)
```

### OAuth 实现方案

```python
# OAuth 流程（约 100 行）

REDIRECT_URI = "http://localhost:17321/callback"
AUTH_URL = "https://bgm.tv/oauth/authorize"
TOKEN_URL = "https://bgm.tv/oauth/access_token"

def cmd_auth():
    """首次 OAuth 授权"""
    # 1. 读取 config.json 中的 client_id
    # 2. 构造授权 URL，自动打开浏览器
    # 3. 启动临时 HTTP Server 监听 /callback
    # 4. 用户授权后，接收 callback 中的 code
    # 5. 用 code + client_id + client_secret 换取 token
    # 6. 保存 token.json 到 ~/.bangumi/
    # 7. 关闭临时 Server
```

### Token 自动刷新

```python
def get_valid_token() -> str:
    """获取有效的 access_token，过期自动刷新"""
    token = load_token()
    if token["expires_at"] - time.time() < 300:  # 提前 5 分钟刷新
        refreshed = refresh_token(token["refresh_token"])
        save_token(refreshed)
        return refreshed["access_token"]
    return token["access_token"]
```

### 用户首次使用流程

```
1. 用户去 bgm.tv/dev/app/create 注册应用
   - 主页地址：随意（个人主页即可）
   - 回调地址：http://localhost:17321/callback
   - 获得 client_id + client_secret

2. 写入配置
   python bangumi.py config --id <client_id> --secret <client_secret>

3. 首次授权
   python bangumi.py auth
   → 自动打开浏览器 → Bangumi 授权 → 回调 localhost → 完成

4. 之后所有命令自动带 token，无需重复授权
```

### 新增脚本模块

```python
# V2 新增（约 200 行）

# === OAuth 层 ===
def cmd_auth()
def cmd_config(args)
def get_valid_token() -> str
def refresh_token(refresh_token) -> dict
def load_token() -> dict
def save_token(data)

# === 用户命令 ===
def cmd_collections(args)
def cmd_collect(args)
def cmd_progress(args)

# === 带认证的请求 ===
def api_get_auth(path, params=None) -> dict
def api_post_auth(path, data=None) -> dict
```

---

## 八、V3 详细设计：服务器 MCP 版

### SKILL.md 新增内容（目标增量 ~20 行，~200 token）

新增：
1. MCP 连接配置说明
2. 与 V1/V2 的差异说明

### MCP Server 工具定义

```python
# bangumi_mcp_server.py 工具列表

tools = [
    {
        "name": "bangumi_search",
        "description": "搜索番剧/书籍/游戏/音乐",
        "parameters": {
            "keyword": "搜索关键词",
            "type": "anime|book|game|music|real（可选）",
            "limit": "返回数量（可选，默认 10）"
        }
    },
    {
        "name": "bangumi_info",
        "description": "获取条目详情",
        "parameters": {
            "subject_id": "条目 ID（整数）"
        }
    },
    {
        "name": "bangumi_episodes",
        "description": "获取集数列表",
        "parameters": {
            "subject_id": "条目 ID",
            "limit": "返回数量（可选）"
        }
    },
    {
        "name": "bangumi_season",
        "description": "获取当季番表",
        "parameters": {
            "year": "年份（可选，默认当年）",
            "month": "月份（可选，默认当季）"
        }
    },
    {
        "name": "bangumi_rank",
        "description": "获取评分排行",
        "parameters": {
            "type": "anime|book|game（可选）",
            "top": "数量（可选，默认 20）"
        }
    },
    {
        "name": "bangumi_person",
        "description": "查询声优/制作人员",
        "parameters": {
            "keyword": "关键词"
        }
    },
    {
        "name": "bangumi_my_collections",
        "description": "查看我的收藏列表",
        "parameters": {
            "status": "wish|doing|collect|on_hold|dropped（可选）",
            "category": "anime|book|game|music|real（可选）"
        }
    },
    {
        "name": "bangumi_update_collection",
        "description": "修改收藏状态",
        "parameters": {
            "subject_id": "条目 ID",
            "status": "wish|doing|collect|on_hold|dropped"
        }
    },
    {
        "name": "bangumi_mark_episode",
        "description": "标记单集观看状态",
        "parameters": {
            "subject_id": "条目 ID",
            "episode_id": "集数 ID",
            "status": "watched|queue|drop"
        }
    }
]
```

### SQLite 数据模型

```sql
-- 用户表
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bgm_username TEXT UNIQUE NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    expires_at INTEGER NOT NULL,
    client_id TEXT NOT NULL,
    client_secret TEXT NOT NULL,
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
);

-- 请求缓存表
CREATE TABLE cache (
    cache_key TEXT PRIMARY KEY,
    response_data TEXT NOT NULL,      -- JSON
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL
);

-- 速率限制表
CREATE TABLE rate_limits (
    endpoint TEXT NOT NULL,
    last_request_at INTEGER NOT NULL
);
```

### MCP Server 模块结构

```python
# bangumi_mcp_server.py（约 400 行）

# === 配置 ===
DEFAULT_PORT = 17321
DB_PATH = "~/.bangumi-mcp/data.db"
CACHE_TTL = {...}  # 各接口缓存时间

# === 数据库层 ===
class BangumiDB:
    def init_db()
    def save_user(username, token_data)
    def get_user(username)
    def update_token(username, token_data)
    def set_cache(key, data, ttl)
    def get_cache(key)

# === Bangumi API 客户端 ===
class BangumiClient:
    def __init__(self, db)
    def search(keyword, type, limit)
    def get_subject(id)
    def get_episodes(subject_id)
    def get_season(year, month)
    def get_rank(type, top)
    def search_person(keyword)
    def get_collections(username, status, category)
    def update_collection(username, subject_id, status)
    def mark_episode(username, subject_id, episode_id, status)
    # 内部
    def _get_valid_token(username)
    def _request(path, params, username)
    def _cache_or_fetch(key, fetcher, ttl)

# === MCP Tool 处理 ===
def handle_bangumi_search(args, db)
def handle_bangumi_info(args, db)
def handle_bangumi_episodes(args, db)
def handle_bangumi_season(args, db)
def handle_bangumi_rank(args, db)
def handle_bangumi_person(args, db)
def handle_bangumi_my_collections(args, db)
def handle_bangumi_update_collection(args, db)
def handle_bangumi_mark_episode(args, db)

# === MCP Server 主循环 ===
class BangumiMCPServer:
    def __init__(self)
    def start()
    def handle_request(request)
    def stop()
```

### V3 部署方式

```json
// OpenClaw 配置中的 MCP Server 注册
{
  "mcp": {
    "servers": {
      "bangumi": {
        "command": "python",
        "args": ["path/to/bangumi_mcp_server.py"],
        "env": {}
      }
    }
  }
}
```

### 多用户 Token 管理

V3 支持两种模式：

**模式 A：本地单用户（默认）**
- 与 V2 行为一致，token 存本地 SQLite
- 适合个人使用

**模式 B：远程多用户**
- MCP Server 部署在服务器上
- 用户通过 Web 页面完成 OAuth 授权
- Web 授权页集成在 MCP Server 中（`/auth` 路由）
- 每个用户独立 token，按 bgm_username 区分

```python
# Web 授权路由
@app.route("/auth")
def auth_page():
    """显示授权引导页"""

@app.route("/auth/callback")
def auth_callback():
    """接收 OAuth 回调，存储 token"""

@app.route("/auth/status")
def auth_status():
    """查询授权状态"""
```

---

## 九、Token 开销总结

### SKILL.md 各版本行数与 Token 预估

| 版本 | 新增行数 | 累计行数 | 预估 Token/次 | 说明 |
|------|---------|---------|--------------|------|
| V1 | ~50 行 | ~50 行 | ~500 | 基础查询 |
| V2 | ~20 行 | ~70 行 | ~700 | +OAuth +收藏 |
| V3 | ~20 行 | ~90 行 | ~900 | +MCP 说明 |

### 脚本行数预估

| 模块 | 行数 | 说明 |
|------|------|------|
| bangumi.py 核心（V1） | ~300 行 | 查询 + 缓存 + 格式化 |
| bangumi.py OAuth（V2） | ~200 行 | +授权 +收藏 |
| bangumi_mcp_server.py（V3） | ~400 行 | MCP 协议 + SQLite |
| 合计 | ~900 行 | |

### Token 开销对比（vs 内联 API 调用）

| 方案 | 每次查询 Token 开销 |
|------|-------------------|
| ❌ SKILL.md 内写 API 细节 | ~2000-3000（上下文中充满 JSON schema） |
| ❌ agent 直接调 web_fetch | ~3000-5000（原始 JSON 全进上下文） |
| ✅ 本方案（脚本 + 精简输出） | ~500（SKILL.md）+ ~200（脚本输出）= **~700** |

**节省约 75-85% token。**

---

## 十、开发路线图

### 阶段 1：V1 信息查询版

```
步骤 1.1  搭建脚本骨架（CLI 解析 + 网络层 + 缓存层）     1h
步骤 1.2  实现 6 个命令（search/info/episodes/season/rank/person）  1.5h
步骤 1.3  输出格式调优（精简、可读、信息密度）           0.5h
步骤 1.4  编写 SKILL.md                                0.5h
步骤 1.5  端到端测试                                   0.5h
```

**V1 交付物**：`bangumi.py` + `SKILL.md`，可搜索/查详情/看番表

### 阶段 2：V2 本地用户版

```
步骤 2.1  实现 OAuth 授权流程（浏览器 + localhost 回调）  1h
步骤 2.2  实现 token 存储/加载/自动刷新                 0.5h
步骤 2.3  实现收藏查询/修改/集数标记                     1h
步骤 2.4  更新 SKILL.md（追加 V2 内容）                 0.5h
步骤 2.5  端到端测试（含 OAuth 全流程）                  0.5h
```

**V2 交付物**：V1 全部 + 收藏管理 + OAuth

### 阶段 3：V3 服务器 MCP 版

```
步骤 3.1  搭建 MCP Server 骨架（协议解析 + 工具注册）     1h
步骤 3.2  移植 API 客户端到 MCP Server                   1h
步骤 3.3  SQLite 集成（用户 + 缓存）                     0.5h
步骤 3.4  Web 授权页（多用户支持）                        1h
步骤 3.5  Token 自动刷新后台任务                          0.5h
步骤 3.6  更新 SKILL.md（追加 V3 内容）                 0.5h
步骤 3.7  端到端测试（MCP 协议 + 多用户）                 1h
```

**V3 交付物**：V2 全部 + MCP Server + 多用户支持

### 总工时

| 阶段 | 工时 | 累计 |
|------|------|------|
| V1 | 4h | 4h |
| V2 | 3.5h | 7.5h |
| V3 | 5.5h | 13h |

---

## 十一、风险与注意事项

| 风险 | 影响 | 应对 |
|------|------|------|
| Bangumi API 变更 | 接口不可用 | 脚本集中管理，一处修改全局生效 |
| 搜索 API 标注"实验性" | schema 可能变动 | 当前稳定运行中，暂不担心 |
| 速率限制未公开 | 可能被限频 | 脚本内建间隔控制 + 缓存 |
| OAuth 回调 localhost | 部分环境不可用 | V3 提供 Web 授权页替代 |
| 缓存文件过多 | 磁盘占用 | 定期清理过期缓存（>7 天） |
| User-Agent 要求 | 默认 UA 被 403 | 脚本硬编码自定义 UA |

---

## 十二、参考资料与 API 文档

### 官方文档

| 资源 | 地址 | 说明 |
|------|------|------|
| API GitHub 仓库 | https://github.com/bangumi/api | OpenAPI 规范、User Agent 建议、Issue 反馈 |
| OpenAPI 规范 (v0.yaml) | https://raw.githubusercontent.com/bangumi/api/master/open-api/v0.yaml | 完整的端点定义、请求/响应 Schema、枚举类型 |
| User Agent 建议 | https://github.com/bangumi/api/blob/master/docs-raw/user%20agent.md | UA 格式要求，非浏览器调用必须自定义 UA |
| 开发者平台 | https://bgm.tv/dev/app/create | 注册第三方应用，获取 client_id / client_secret |
| OAuth 授权入口 | https://bgm.tv/oauth/authorize | OAuth 授权起始页 |
| Token 端点 | https://bgm.tv/oauth/access_token | 用 code 换取 token / 用 refresh_token 刷新 |

### API 基础信息

- **Base URL**: `https://api.bgm.tv`
- **协议**: OpenAPI 3.0.2
- **版本**: v0
- **域名**: `api.bgm.tv` / `bangumi.tv`（两个域名均可）
- **User-Agent**: 必填，格式 `{username}/{app-name}[/version] [(platform)] [(url)]`
  - 示例：`clawbot/bangumi-tracker/1.0 (https://github.com/yourname/bangumi-tracker)`
  - ⚠️ 不要使用 `database`、`Bangumi/1.0` 等通用 UA，会被 403

### API 端点完整清单（按 v0.yaml 整理）

#### 搜索（实验性，POST）

| 端点 | 功能 | 筛选条件 |
|------|------|----------|
| `/v0/search/subjects` | 条目搜索 | type、tag、meta_tags、air_date、rating、rating_count、rank、nsfw |
| `/v0/search/characters` | 角色搜索 | nsfw |
| `/v0/search/persons` | 人物搜索 | career |

搜索 body 结构：
```json
{
  "keyword": "关键词",
  "sort": "match|heat|rank|score",   // 默认 match
  "filter": {
    "type": [1, 2],                   // SubjectType 数组，多值「或」关系
    "meta_tags": ["原创", "-科幻"],    // 多值「且」关系，-前缀排除
    "tag": ["奇幻", "冒险"],          // 多值「且」关系
    "air_date": [">=2025-01-01", "<2025-04-01"],
    "rating": [">=7"],
    "rating_count": [">=100"],
    "rank": ["<=50"],
    "nsfw": false
  }
}
// Query: ?limit=20&offset=0
```

#### 条目（GET，部分支持 OptionalHTTPBearer）

| 端点 | 功能 | 认证 | 缓存 |
|------|------|------|------|
| `/v0/subjects` | 浏览条目 | 可选 | 首页 24h，后续 1h |
| `/v0/subjects/{id}` | 条目详情 | 可选 | 300s |
| `/v0/subjects/{id}/image` | 条目封面 | 可选 | - |
| `/v0/subjects/{id}/persons` | 关联人物 | 可选 | - |
| `/v0/subjects/{id}/characters` | 关联角色 | 可选 | - |
| `/v0/subjects/{id}/subjects` | 关联条目（前传/续作） | 可选 | - |

`/v0/subjects` 查询参数：`type`(必填)、`cat`、`series`、`platform`、`sort`(date|rank)、`year`、`month`、`limit`、`offset`

#### 章节（GET，OptionalHTTPBearer）

| 端点 | 功能 | 参数 |
|------|------|------|
| `/v0/episodes` | 集数列表 | `subject_id`、`type`、`limit`(max 200, default 100)、`offset` |
| `/v0/episodes/{id}` | 单集详情 | - |

#### 角色（GET/POST/DELETE）

| 端点 | 方法 | 功能 | 认证 |
|------|------|------|------|
| `/v0/characters/{id}` | GET | 角色详情（60s 缓存） | 无 |
| `/v0/characters/{id}/image` | GET | 角色图片 | 可选 |
| `/v0/characters/{id}/subjects` | GET | 角色出演作品 | 无 |
| `/v0/characters/{id}/persons` | GET | 角色关联人物 | 无 |
| `/v0/characters/{id}/collect` | POST | 收藏角色 | ✅ Bearer |
| `/v0/characters/{id}/collect` | DELETE | 取消收藏角色 | ✅ Bearer |

#### 人物（GET/POST/DELETE）

| 端点 | 方法 | 功能 | 认证 |
|------|------|------|------|
| `/v0/persons/{id}` | GET | 人物详情（60s 缓存） | 无 |
| `/v0/persons/{id}/image` | GET | 人物图片 | 可选 |
| `/v0/persons/{id}/subjects` | GET | 人物参与作品 | 无 |
| `/v0/persons/{id}/characters` | GET | 人物配音角色 | 无 |
| `/v0/persons/{id}/collect` | POST | 收藏人物 | ✅ Bearer |
| `/v0/persons/{id}/collect` | DELETE | 取消收藏人物 | ✅ Bearer |

#### 用户（GET）

| 端点 | 功能 | 认证 |
|------|------|------|
| `/v0/users/{username}` | 用户信息 | 无 |
| `/v0/users/{username}/avatar` | 用户头像（302 重定向） | 无 |
| `/v0/me` | 当前用户信息 | ✅ Bearer |

#### 收藏（需 Bearer Token，v0.yaml 中有完整定义但上面未截取完整）

| 端点 | 方法 | 功能 |
|------|------|------|
| `/v0/users/{username}/collections` | GET | 查看用户收藏列表 |
| `/v0/users/-/collections/{subject_id}` | POST | 新增收藏 |
| `/v0/users/-/collections/{subject_id}` | PUT | 修改收藏状态 |
| `/v0/users/-/collections/{subject_id}` | DELETE | 删除收藏 |
| `/v0/users/-/collections/{subject_id}/episodes` | PUT | 标记集数观看状态 |

#### 目录

| 端点 | 功能 |
|------|------|
| `/v0/indices` | 浏览目录 |
| `/v0/indices/{id}` | 目录详情 |
| `/v0/indices/{id}/subjects` | 目录内条目 |

### 核心 Schema（数据模型）

#### SubjectType（条目类型）

| 值 | 类型 |
|----|------|
| 1 | 书籍（含轻小说） |
| 2 | 动画 |
| 3 | 音乐 |
| 4 | 游戏 |
| 6 | 三次元 |

#### SubjectCategory（条目分类）

| 值 | 分类 |
|----|------|
| `anime` | 动画 |
| `book` | 书籍 |
| `game` | 游戏 |
| `music` | 音乐 |
| `real` | 三次元 |

#### 收藏状态类型

| 值 | 含义 |
|----|------|
| `wish` | 想看 |
| `collect` | 看过 |
| `doing` | 在看 |
| `on_hold` | 搁置 |
| `dropped` | 抛弃 |

#### 集数类型（EpType）

| 值 | 类型 |
|----|------|
| 0 | 本篇 |
| 1 | SP |
| 2 | OP |
| 3 | ED |
| 4 | 预告/宣传 |
| 5 | MAD |
| 6 | 其他 |

#### Subject 返回字段

```
id, type, name, name_cn, date, platform, summary,
images: {small, grid, large, medium, common},
tags: [{name, count}],
infobox: [{key, value}],
rating: {score, rank, total, count: {1,2,3,...,10}},
collection: {wish, collect, doing, on_hold, dropped},
total_episodes, eps, volumes, meta_tags, series, locked, nsfw
```

#### PersonDetail 返回字段

```
id, name, type, career: [{name}], 
images: {small, grid, large, medium},
summary, infobox: [{key, value}],
locked, verified
```

#### Character 返回字段

```
id, name, type,
images: {small, grid, large, medium},
summary, infobox: [{key, value}],
locked
```

#### Episode 返回字段

```
id, type, sort, name, name_cn, ep, airdate,
comment, duration, desc
```

### OAuth 2.0 授权流程

Bangumi 使用标准 OAuth 2.0 Authorization Code 流程：

```
1. 用户访问授权页
   GET https://bgm.tv/oauth/authorize?client_id={ID}&response_type=code&redirect_uri={URI}

2. 用户点击授权，重定向到回调地址
   {REDIRECT_URI}?code={AUTH_CODE}

3. 用 code 换取 token
   POST https://bgm.tv/oauth/access_token
   Body: {
     grant_type: "authorization_code",
     client_id: "{ID}",
     client_secret: "{SECRET}",
     code: "{AUTH_CODE}",
     redirect_uri: "{URI}"
   }
   Response: { access_token, refresh_token, expires_in, token_type }

4. 刷新 token
   POST https://bgm.tv/oauth/access_token
   Body: {
     grant_type: "refresh_token",
     client_id: "{ID}",
     client_secret: "{SECRET}",
     refresh_token: "{REFRESH_TOKEN}"
   }

5. 请求 API 时
   Header: Authorization: Bearer {ACCESS_TOKEN}
```

### 社区资源

| 资源 | 地址 | 说明 |
|------|------|------|
| 番组开发小组 | https://bgm.tv/group/dev | API 讨论与反馈 |
| BUG 追踪 | https://bgm.tv/group/issues | 提交 API 相关问题 |
| API Issues | https://github.com/bangumi/api/issues | GitHub Issue 追踪 |

---

## 十三、后续扩展方向（不在本次范围内）

- 每周自动生成新番推荐（cron + agent）
- 观看统计与年度总结
- Bangumi 与其他平台（MAL/AniList）的同步
- 通知功能（想看的番更新了新集）
- 基于收藏偏好的推荐算法
