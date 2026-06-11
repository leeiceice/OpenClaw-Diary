# ARCHITECT.md — 系统架构 🦞

> 核心系统架构规则统一存储。

---

## 时区规则（系统级铁律）

**背景**：服务器在 UTC 时区运行，Lee 在 CST（UTC+8）时区。

**强制规范**：
- `from _timezone import CST` — 所有脚本必须从 `scripts/_timezone.py` 导入 CST 常量
- `datetime.now(CST)` — 业务时间（日志 / 文件名 / 显示）
- `datetime.now(timezone.utc).isoformat()` — 存储时间（跨 Agent / 持久化）
- **禁止** `datetime.now()` — naive datetime 是系统级 bug 根源

**时区语义协议**：
- 内部计算：UTC
- 用户可见：CST（+8）
- 跨 Agent 通信：ISO UTC
- 口头时间：默认 CST（+8），说「UTC」才用 UTC

**CST 常量定义**：`CST = timezone(timedelta(hours=8))`，定义在 `scripts/_timezone.py`

## 三层记忆体系

1. **SESSION-STATE.md** → 短期（当前会话状态）
2. **memory/YYYY-MM-DD.md** → 中期（每日过程记录）
3. **MEMORY.md** → 长期索引（规则与指针）

**优先级**：长期 > 中期 > 当前会话 > 联网搜索

## WAL 协议（2026-06-05 立）

重要决策实时写入 `memory/YYYY-MM-DD.md`（当日文件），不拖延。

## 基础设施

- Gateway 端口：26301
- GitHub 访问（腾讯云）：**必须用 SSH**（git@github.com:xxx），HTTPS 会超时
- SSH URL 格式：`git@github.com:leeiceice/仓库名.git`
- 设置 upstream：`git push --set-upstream origin main`（一次性）

---

_版本：1.0 | 建立：2026-06-11 | by 小龙虾_
