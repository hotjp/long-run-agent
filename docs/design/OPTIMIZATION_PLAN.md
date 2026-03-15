# 多项目并行开发和多会话管理优化方案

## 问题分析

### 当前架构的局限性

1. **单项目限制**
   - 所有工具必须在项目根目录运行
   - 无法同时管理多个项目
   - 缺少项目注册和发现机制

2. **单会话限制**
   - session_state.json 只能记录一个会话
   - 多个 Agent 会话会互相覆盖状态
   - 缺少会话隔离和协调

3. **并发问题**
   - 文件锁只能保护单个文件的并发访问
   - 无法跨项目协调资源
   - 缺少全局会话管理

## 优化方案

### 架构设计

```
~/.lra/                          # 全局 LRA 工作目录
├── registry.json                # 项目注册表
├── sessions/                    # 全局会话目录
│   ├── active/                  # 活跃会话
│   │   ├── session_001.json
│   │   └── session_002.json
│   └── completed/               # 已完成会话
├── locks/                       # 全局锁目录
│   ├── project_A.lock
│   └── project_B.lock
└── logs/                        # 全局日志
    └── lra.log

project-A/                       # 项目目录
└── .long-run-agent/
    ├── feature_list.json
    ├── progress.txt
    ├── config.json
    └── sessions/                 # 项目本地会话引用
        └── active_session_id

project-B/
└── .long-run-agent/
    ├── feature_list.json
    ├── progress.txt
    ├── config.json
    └── sessions/
        └── active_session_id
```

### 核心组件

#### 1. 项目注册表 (Registry)

**功能**:
- 注册新项目（项目路径 + 元数据）
- 列出所有项目
- 查找项目
- 注销项目

**数据结构**:
```json
{
  "projects": {
    "project-A": {
      "path": "/path/to/project-A",
      "name": "任务管理应用",
      "created_at": "2026-02-18T00:00:00",
      "last_active": "2026-02-18T00:30:00",
      "status": "active"
    },
    "project-B": {
      "path": "/path/to/project-B",
      "name": "用户管理系统",
      "created_at": "2026-02-18T01:00:00",
      "last_active": "2026-02-18T01:30:00",
      "status": "active"
    }
  }
}
```

#### 2. 会话管理器 (Session Manager)

**功能**:
- 创建新会话（生成唯一会话 ID）
- 关联会话到项目
- 跟踪会话状态
- 列出活跃会话
- 完成会话

**会话数据结构**:
```json
{
  "session_id": "sess_20260218_001",
  "project_id": "project-A",
  "project_path": "/path/to/project-A",
  "current_feature": "feature_001",
  "started_at": "2026-02-18T00:00:00",
  "ended_at": null,
  "status": "inactive",
  "metadata": {
    "agent_id": "agent_main",
    "model": "glm-4.7"
  }
}
```

#### 3. 资源协调器 (Resource Coordinator)

**功能**:
- 获取项目锁（避免多个会话同时操作同一项目）
- 释放项目锁
- 检查资源可用性
- 跨项目协调

#### 4. 命令行接口改进

**新增命令**:
```bash
# 项目管理
lra project register --name "项目名" --path "/path/to/project"
lra project list
lra project info --project-id "project-A"
lra project unregister --project-id "project-A"

# 会话管理
lra session create --project-id "project-A"
lra session list
lra session info --session-id "sess_001"
lra session complete --session-id "sess_001"

# 多项目管理
lra work --project-id "project-A"  # 设置工作项目
lra task --project-id "project-B"   # 从项目 B 获取任务
```

### 实现细节

#### 项目注册表实现

```python
class ProjectRegistry:
    def __init__(self):
        self.registry_path = os.path.expanduser("~/.lra/registry.json")

    def register(self, project_path, name=None):
        """注册项目"""
        project_id = self._generate_project_id(project_path)

        if not name:
            name = os.path.basename(project_path.rstrip("/"))

        project_data = {
            "project_id": project_id,
            "path": os.path.abspath(project_path),
            "name": name,
            "created_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
            "status": "active"
        }

        with self._lock():
            registry = self._load()
            registry["projects"][project_id] = project_data
            self._save(registry)

        return project_id

    def list_projects(self):
        """列出所有项目"""
        registry = self._load()
        return list(registry["projects"].values())

    def get_project(self, project_id):
        """获取项目信息"""
        registry = self._load()
        return registry["projects"].get(project_id)

    def _load(self):
        """加载注册表"""
        if not os.path.exists(self.registry_path):
            return {"projects": {}}

        with open(self.registry_path, "r") as f:
            return json.load(f)

    def _save(self, data):
        """保存注册表"""
        os.makedirs(os.path.dirname(self.registry_path), exist_ok=True)
        with open(self.registry_path, "w") as f:
            json.dump(data, f, indent=2)
```

#### 会话管理器实现

```python
class SessionManager:
    def __init__(self):
        self.sessions_dir = os.path.expanduser("~/.lra/sessions")
        self.active_dir = os.path.join(self.sessions_dir, "active")
        self.completed_dir = os.path.join(self.sessions_dir, "completed")

    def create_session(self, project_id, agent_id=None):
        """创建新会话"""
        session_id = self._generate_session_id()
        project_registry = ProjectRegistry()
        project = project_registry.get_project(project_id)

        if not project:
            raise ValueError(f"项目 {project_id} 不存在")

        session_data = {
            "session_id": session_id,
            "project_id": project_id,
            "project_path": project["path"],
            "started_at": datetime.now().isoformat(),
            "ended_at": None,
            "status": "in_progress",
            "agent_id": agent_id,
            "current_feature": None
        }

        session_path = os.path.join(self.active_dir, f"{session_id}.json")
        with open(session_path, "w") as f:
            json.dump(session_data, f, indent=2)

        # 更新项目活跃时间
        project_registry.update_last_active(project_id)

        return session_id

    def list_active_sessions(self):
        """列出活跃会话"""
        sessions = []
        for filename in os.listdir(self.active_dir):
            if filename.endswith(".json"):
                session_path = os.path.join(self.active_dir, filename)
                with open(session_path, "r") as f:
                    sessions.append(json.load(f))
        return sessions

    def complete_session(self, session_id):
        """完成会话"""
        session_path = os.path.join(self.active_dir, f"{session_id}.json")

        if not os.path.exists(session_path):
            raise ValueError(f"会话 {session_id} 不存在")

        with open(session_path, "r") as f:
            session_data = json.load(f)

        session_data["ended_at"] = datetime.now().isoformat()
        session_data["status"] = "completed"

        # 移动到已完成目录
        completed_path = os.path.join(self.completed_dir, f"{session_id}.json")
        os.makedirs(self.completed_dir, exist_ok=True)
        with open(completed_path, "w") as f:
            json.dump(session_data, f, indent=2)

        os.remove(session_path)
```

#### 资源协调器实现

```python
class ResourceCoordinator:
    def __init__(self):
        self.locks_dir = os.path.expanduser("~/.lra/locks")

    def acquire_project_lock(self, project_id, session_id, timeout=300):
        """获取项目锁"""
        lock_path = os.path.join(self.locks_dir, f"{project_id}.lock")

        try:
            lock_file = open(lock_path, "w")
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

            # 写入锁信息
            lock_info = {
                "session_id": session_id,
                "acquired_at": datetime.now().isoformat(),
                "timeout": timeout
            }
            json.dump(lock_info, lock_file)

            return lock_file
        except IOError:
            raise ResourceLockError(f"项目 {project_id} 被其他会话锁定")

    def release_project_lock(self, project_id, lock_file):
        """释放项目锁"""
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        lock_file.close()

        lock_path = os.path.join(self.locks_dir, f"{project_id}.lock")
        if os.path.exists(lock_path):
            os.remove(lock_path)
```

### 使用场景

#### 场景 1：多项目并行开发

```bash
# 注册项目 A
lra project register --name "任务管理" --path "/projects/task-manager"

# 注册项目 B
lra project register --name "用户系统" --path "/projects/user-system"

# 列出所有项目
lra project list
# 输出:
# project-A: 任务管理 (/projects/task-manager) - active
# project-B: 用户系统 (/projects/user-system) - active

# Agent 1 开始处理项目 A
lra session create --project-id "project-A" --agent-id "agent_main"
lra task --project-id "project-A"

# Agent 2 开始处理项目 B
lra session create --project-id "project-B" --agent-id "agent_worker_1"
lra task --project-id "project-B"
```

#### 场景 2：多会话协同同一项目

```bash
# Agent 1 获取任务（自动获取锁）
lra work --project-id "project-A"
lra task
# 输出: 下一个任务: feature_001

# Agent 2 尝试获取同一项目的任务
lra task --project-id "project-A"
# 输出: 错误: 项目 project-A 被会话 sess_001 锁定

# Agent 1 完成任务（自动释放锁）
lra complete --feature-id "feature_001" --commit-message "feat: 实现 feature_001"

# 现在 Agent 2 可以获取任务
lra task --project-id "project-A"
# 输出: 下一个任务: feature_002
```

### 迁移计划

#### 阶段 1：基础架构（立即执行）
1. 创建 `~/.lra/` 目录结构
2. 实现 `ProjectRegistry` 类
3. 实现 `SessionManager` 类
4. 实现 `ResourceCoordinator` 类

#### 阶段 2：工具改造（1-2 天）
1. 修改 `feature_manager.py` 支持多项目
2. 修改 `progress_tracker.py` 支持多项目
3. 修改 `session_orchestrator.py` 支持多会话
4. 创建新的命令行接口 `lra`

#### 阶段 3：测试和优化（1 天）
1. 单元测试
2. 集成测试
3. 并发压力测试
4. 性能优化

#### 阶段 4：文档和迁移指南（半天）
1. 更新文档
2. 创建迁移指南
3. 提供示例

### 优势

1. **真正的并行**: 多个项目可以同时开发
2. **会话隔离**: 每个会话有独立的状态
3. **资源安全**: 避免并发冲突
4. **全局视图**: 可以统一管理所有项目和会话
5. **可扩展**: 未来可以支持分布式开发

### 兼容性

- **向后兼容**: 旧的单项目模式仍然支持
- **平滑迁移**: 旧项目可以逐步迁移到新架构
- **可选使用**: 可以选择使用新功能或继续使用旧模式

---

**下一步行动**:
1. 创建 `registry.py` 模块
2. 创建 `session_manager.py` 模块
3. 创建 `resource_coordinator.py` 模块
4. 创建 `lra` 命令行工具
