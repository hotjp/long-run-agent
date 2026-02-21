# LRA - Long-Running Agent 工具

多项目并行开发和多会话管理系统。

## 🚀 快速开始

### 1. 初始化项目

```bash
cd /path/to/your/project
python3 /root/.openclaw/workspace/tools/long-run-agent/feature_manager.py init \
  --project-name "我的应用" \
  --spec "项目描述"

# 添加功能清单
python3 /root/.openclaw/workspace/tools/long-run-agent/feature_manager.py add \
  --category "functional" \
  --description "用户可以登录" \
  --priority 1
```

### 2. 注册项目

```bash
# 注册到 LRA
python3 /root/.openclaw/workspace/tools/long-run-agent/lra project register \
  --path /path/to/your/project \
  --name "我的应用"
```

### 3. 创建会话并开始工作

```bash
# 创建会话
python3 /root/.openclaw/workspace/tools/long-run-agent/lra session create \
  --project-id project_id \
  --agent-id agent_main

# 获取下一个任务
python3 /root/.openclaw/workspace/tools/long-run-agent/lra task next \
  --project-id project_id

# 完成任务
python3 /root/.openclaw/workspace/tools/long-run-agent/lra task complete \
  --feature-id feature_001 \
  --commit-message "feat: 实现用户登录" \
  --project-id project_id
```

## 📚 命令参考

### 项目管理

```bash
# 注册项目
lra project register --path /path/to/project --name "项目名"

# 列出所有项目
lra project list

# 查看项目详情
lra project info --project-id project_id

# 注销项目
lra project unregister --project-id project_id
```

### 会话管理

```bash
# 创建新会话
lra session create --project-id project_id --agent-id agent_id

# 列出活跃会话
lra session list --status active

# 列出已完成会话
lra session list --status completed

# 查看会话详情
lra session info --session-id session_id

# 完成会话
lra session complete --session-id session_id --notes "完成说明"
```

### 任务管理

```bash
# 获取下一个任务
lra task next --project-id project_id

# 完成任务
lra task complete \
  --feature-id feature_001 \
  --notes "实现说明" \
  --commit-message "feat: 实现功能" \
  --project-id project_id
```

### 工具命令

```bash
# 设置工作项目（之后可以省略 --project-id）
lra work --project-id project_id

# 查看统计信息
lra stats

# 强制释放项目锁（谨慎使用）
lra force-release-lock --project-id project_id
```

## 🔧 多项目并行开发

### 场景：同时开发多个项目

```bash
# 注册项目 A
lra project register --path /projects/task-manager --name "任务管理"

# 注册项目 B
lra project register --path /projects/user-system --name "用户系统"

# Agent 1 处理项目 A
lra session create --project-id task-manager_id --agent-id agent_main
lra task next --project-id task-manager_id

# Agent 2 处理项目 B
lra session create --project-id user-system_id --agent-id agent_worker
lra task next --project-id user-system_id
```

### 场景：多会话协同同一项目

```bash
# Agent 1 获取任务（自动获取锁）
lra task next --project-id project_id

# Agent 2 尝试获取同一项目的任务
lra task next --project-id project_id
# 输出: 项目被会话 sess_xxxx 锁定

# Agent 1 完成任务（自动释放锁）
lra task complete --feature-id feature_001 --project-id project_id

# 现在 Agent 2 可以获取任务
lra task next --project-id project_id
```

## 📁 目录结构与其他模块交互说明

### LRA 全局目录结构

```
~/.lra/                          # LRA 工作目录
├── registry.json                # 项目注册表
├── sessions/                    # 全局会话目录
│   ├── active/                  # 活跃会话
│   │   └── sess_*.json
│   └── completed/               # 已完成会话
│       └── sess_*.json
├── locks/                       # 全局锁目录
│   └── project_id.lock
└── registry.lock                # 注册表锁
```

### 项目目录结构

```
project-root/
├── .long-run-agent/           # 项目元数据目录
│   ├── feature_list.json      # 功能清单
│   ├── progress.txt            # 进度日志
│   ├── config.json            # 项目配置
│   └── sessions/              # 项目会话引用（预留）
├── init.sh                     # 初始化脚本（可选）
└── ...                        # 项目文件
```

### 模块交互关系

```
                    ┌──────────────┐
                    │  lra (CLI)   │
                    └──────┬───────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
    ┌─────▼─────┐   ┌─────▼─────┐   ┌─────▼─────┐
    │ Registry  │   │ Session   │   │ Resource  │
    │ Manager   │   │ Manager   │   │Coordinator│
    └─────┬─────┘   └─────┬─────┘   └─────┬─────┘
          │                │                │
          └────────────────┴────────────────┘
                           │
                  ┌────────▼────────┐
                  │   Config.py     │
                  │   (共享配置)    │
                  └─────────────────┘
                           │
                  ┌────────▼────────┐
                  │ feature_manager  │
                  │ progress_tracker │
                  │ session_...     │
                  └─────────────────┘
```

### 核心交互流程

#### 1. 项目注册流程

```python
# lra project register
→ Registry.register()
  └─> 读取 .long-run-agent/config.json
  └─> 生成 project_id (路径哈希)
  └─> 写入 ~/.lra/registry.json (带锁)
```

#### 2. 会话创建流程

```python
# lra session create
→ Registry.get_project(project_id)
  └─> 验证项目存在
→ SessionManager.create_session()
(在 ~/.lra/sessions/active/ 创建 sess_xxx.json)
→ ResourceCoordinator.acquire_project_lock()
  └─> 创建 ~/.lra/locks/project_id.lock
→ Registry.update_last_active()
```

#### 3. 获取任务流程

```python
# lra task next
→ ResourceCoordinator.check_project_lock()
  └─> 检查项目是否被锁定
→ Registry.get_project(project_id)
  └─> 获取项目路径
→ os.chdir(project_path)  # 切换到项目目录
→ feature_manager.get_next_feature()
  └─> 读取 .long-run-agent/feature_list.json
  └─> 返回未完成的功能
→ SessionManager.update_session()
  └─> 更新会话的 current_feature
```

#### 4. 完成任务流程

```python
# lra task complete
→ feature_manager.update_feature_status()
  └─> 更新 .long-run-agent/feature_list.json
→ progress_tracker.log()
  └─> 写入 .long-run-agent/progress.txt
→ GitHelper.commit()
  └─> 执行 git commit
→ feature_manager.get_feature_stats()
  └─> 返回进度统计
→ feature_manager.get_next_feature()
  └─> 返回下一个任务
```

#### 5. 完成会话流程

```python
# lra session complete
→ SessionManager.complete_session()
  └─> 移动到 ~/.lra/sessions/completed/
→ ResourceCoordinator.force_release_project_lock()
  └─> 删除 ~/.lra/locks/project_id.lock
```

## 🔒 并发安全机制

### 文件锁策略

1. **注册表锁**: `registry.lock` - 保护 registry.json
2. **项目锁**: `project_id.lock` - 保护单个项目的并发访问

### 锁获取流程

```python
# 尝试获取项目锁
lock = ResourceCoordinator.acquire_project_lock(project_id, session_id)

if lock:
    # 成功获取，可以操作项目
    with lock:
        # 执行操作
        pass
    # 自动释放锁
else:
    # 项目被其他会话锁定
    print("项目被锁定，请等待")
```

### 锁冲突处理

```
Agent 1                      Agent 2
   │                            │
   ├─> 获取锁 project_A         │
   │  (成功)                    │
   ├─> 操作项目                 │
   │                            ├─> 获取锁 project_A
   │                            │  (失败，被 Agent 1 锁定)
   │                            │  返回错误
   │                            (等待或放弃)
   ├─> 释放锁 project_A         │
   │                            ├─> 获取锁 project_A
   │                            │  (成功)
   │                            ├─> 操作项目
```

## 📊 状态跟踪

### 项目状态

```json
{
  "project_id": "demo-project_0756a8d5",
  "name": "演示项目",
  "path": "/root/demo-project",
  "created_at": "2026-02-18T00:00:00",
  "last_active": "2026-02-18T01:00:00",
  "status": "active"
}
```

### 会话状态

```json
{
  "session_id": "sess_20260218_001",
  "project_id": "demo-project_0756a8d5",
  "project_path": "/root/demo-project",
  "project_name": "演示项目",
  "started_at": "2026-02-18T00:00:00",
  "ended_at": null,
  "status": "in_progress",
  "agent_id": "agent_main",
  "current_feature": "feature_001",
  "metadata": {}
}
```

### 功能状态

```json
{
  "id": "feature_001",
  "category": "functional",
  "description": "用户可以登录",
  "steps": [...],
  "priority": 1,
  "passes": false,
  "created_at": "2026-02-18T00:00:00",
  "completed_at": null
}
```

## 🐛 故障排除

### 问题：项目被锁定

```bash
# 查看锁状态
lra project info --project-id project_id

# 强制释放锁（谨慎使用）
lra force-release-lock --project-id project_id
```

### 问题：会话卡住

```bash
# 检查会话状态
lra session info --session-id session_id

# 手动完成会话
lra session complete --session-id session_id
```

### 问题：找不到项目

```bash
# 列出所有项目
lra project list

# 重新注册项目
lra project register --path /path/to/project
```

## 🎯 最佳实践

1. **每次会话只处理一个功能**: 遵循增量开发原则
2. **完成任务后立即 Git 提交**: 保持代码整洁
3. **记录详细的进度**: 在 notes 中说明实现细节
4. **定期检查状态**: 使用 `lra stats` 查看全局状态
5. **善用工作项目**: 使用 `lra work` 设置后可省略 --project-id

## 🔗 与 OpenClaw 集成

可以在 OpenClaw 会话中自动执行 LRA 命令：

```python
# 会话开始时自动检查状态
exec('python3 /root/.openclaw/workspace/tools/long-run-agent/lra stats')

# 获取下一个任务
exec('python3 /root/.openclaw/workspace/tools/long-run-agent/lra task next --project-id project_id')

# 完成任务
exec('python3 /root/.openclaw/workspace/tools/long-run-agent/lra task complete --feature-id feature_001 --commit-message "feat: 实现" --project-id project_id')
```

## 📈 性能考虑

- **文件锁开销**: 使用 fcntl，开销很小
- **JSON 读取**: 每次操作都读取文件，适合中小型项目
- **内存使用**: 每个会话独立，内存占用小
- **并发限制**: 文件锁可能成为瓶颈，考虑使用分布式锁（Redis）

## 🚧 未来改进

- [ ] 分布式锁支持（Redis）
- [ ] WebSocket 实时状态同步
- [ ] Web UI 管理界面
- [ ] 任务优先级动态调整
- [ ] 会话恢复和重试机制
- [ ] 性能监控和统计
