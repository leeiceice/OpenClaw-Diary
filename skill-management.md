# Skill 管理经验

## 安装规则
- 任何 Skill 安装前必须 `skill-vetter` 安全审查，高危/极高危直接拒绝
- 经过 skill-vetter 审查后 → 报告结果 → 等 Lee 确认 → 才执行安装
- 切勿跳过审查直接执行（已多次漏过）
- **技能进化产物**（MemOS skillEvolution 自动生成）同等待遇：生成后、安装前必须过 skill-vetter 审查，报告结果，等 Lee 确认

## 高危特征（记忆）
- `curl` + `eval` 同时存在 → 极高危
- `credentials` / `SecretId` / `SecretKey` 硬编码 → 高危
- 外部数据发送（无明确用途说明）→ 高危
- `run.sh` 未审查 → 存疑，须细审

## 已卸载危险/闲置 Skill
- `tencent-cos-skill`（高危）
- `tencentcloud-lighthouse-skill`（闲置）
- `tencent-docs`（闲置）
- `memory-hygiene`（闲置）
- `tencent-meeting-skill`（高危）
- `scrapling`（存疑+未审查）

## 判断框架
安装前先问自己：
1. 这个 Skill 用途清晰吗？
2. 有没有 curl/eval/credentials？
3. 数据发向哪里？
4. Lee 明确要求了吗？
→ 任一为"否" → 审查后再说

---

## ⚠️ 踩坑记录（从 memory/ 日志提炼）

### Skill 安装漏过审查（2026-04-25）
- **问题**：Lee 多次强调安装前必须安全审查，我漏过直接执行
- **教训**：bundled skill 也要审查，不能因"官方捆绑"心存侥幸
- **规则**：skill-vetter 审查 → 报告结果 → 等 Lee 确认 → 才执行安装

### scrapling 存疑未审（2026-04-23）
- **问题**：检测到 ⚠️ SUSPICIOUS + run.sh 未审查，仍在考虑安装
- **教训**：有任何一个存疑点就不安装，除非全部审查通过
- **状态**：已卸载

### baoyu-url-to-markdown 安装（2026-04-20）
- **问题**：CLI 是 Bun 原生格式，无法直接用 Node.js 执行
- **教训**：安装 Skill 前先验证执行环境兼容性
- **解决**：需要写 npx 包装器，或确认 Node.js 环境

---

## 技能进化质量门禁（2026-05-02 新增）

### 问题
技能进化系统产出了大量重复/无效技能，造成 skills/ 目录膨胀，干扰正常 skill 调用。

### 门禁规则（Generator 调用前必须通过）

**自动拒绝（任一匹配 → 拒绝生成）**：

| 规则 | 匹配模式 | 说明 |
|------|---------|------|
| 一次性任务 | `已修复|已完成|done|临时|调试|补丁` | 修完就用一次，没有复用价值 |
| 重复技能 | 与现有 skill 功能重叠 | 生成前必须扫描 `skills/` 确认无重复 |
| 单次bug | `bug修复|特定错误代码|一次性问题` | 只解决当前这次的问题 |
| 版本锁定 | `版本号|当前版本|特定版本专用` | 版本更新后立即失效 |
| 过度具体 | 路径/变量/ID 直接写死 | 无法迁移到其他场景 |
| 低价值闲聊 | `感想|讨论|分享|你认为` | 没有可执行的操作步骤 |

**生成前检查（必做）**：
```bash
# 扫描现有 skills/ 确认无重复
ls /root/.openclaw/workspace/skills/ | grep -i "<技能关键词>"
# 检查 skills-store 是否有相似候选
find /root/.openclaw/workspace/skills-store/ -name "*.md" | xargs grep -l "<关键词>"
```

**如果命中重复**：调用方应该先读取已有 skill，将其更新/扩展，而不是生成新 skill。

### Lee 确认后执行

门禁已建立（写入 skill-management.md），**方案B：在我这边加强制审查**。

**执行方式**：
1. MemOS 技能进化系统生成新 skill → 保存到 `skills/` 或 `skills-store/`
2. 我在 routine 检查中扫描新生成的 skill
3. 对照门禁规则判断：
   - **通过** → 标记为「可安装」，等 Lee 确认
   - **拒绝** → 报告给 Lee，说明拒绝原因（命中哪条规则）
4. Lee 确认后才执行安装

**无需修改 MemOS 插件代码**，门禁审查在我这一层执行，不影响插件现有逻辑。
