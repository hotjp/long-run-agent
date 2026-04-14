# Query Engine Architecture

## 概述

LRA 任务管理系统架构演进方案：引入 SQLite 作为查询引擎，JSON 作为持久化存储，实现性能与简单性的平衡。

## 背景与动机

### 当前问题

LRA 现有 `task_list.json` 架构存在以下问题：

1. **全量读写瓶颈**
   ```python
   # 每次操作都读写整个 JSON
   data = self._load()      # O(n) 全量加载
   tasks.append(new_task)   # 内存操作
   self._save(data)         # O(n) 全量写回
   ```

2. **无索引**
   - list/filter 操作需要遍历所有任务
   - 随着任务数量增长，性能线性下降

3. **并发冲突**
   - `FileLock` 只能串行化，无法高效并发
   - 多 agent 场景下锁竞争严重

4. **无原子性保障**
   - 崩溃可能损坏 JSON
   - 无事务回滚机制

### 什么时候需要升级

| 信号 | 当前状态 | 阈值 |
|------|---------|------|
| 任务数量 | ~50-200 | >1000 开始考虑 |
| 查询延迟 | <50ms | >200ms 开始感知 |
| 并发 agent | 1-2 | >5 开始冲突 |
| 启动时间 | <1s | >3s 开始抱怨 |

## 架构设计

### 核心理念

```
JSON = 持久化存储（持久化、可视化、git 友好）
SQLite = 查询引擎（索引、查询、统计）
```

两者保持最终一致，JSON 是"真相来源"，SQLite 是"加速索引"。

### 数据流

```
┌─────────────────────────────────────────────────────────────┐
│                         LRA 应用层                          │
│                    task_manager.py / cli.py                  │
└─────────────────────┬───────────────────────────────────────┘
                      │
         ┌────────────┴────────────┐
         │                         │
         ▼                         ▼
┌─────────────────────┐   ┌─────────────────────┐
│      JSON 文件       │   │    SQLite 索引       │
│                     │   │                     │
│  task_list.json     │ ←─┼→  lra_index.db      │
│  tasks/{id}.md      │ 同步│                     │
│                     │   │  (查询加速)           │
└─────────────────────┘   └─────────────────────┘
```

### 三阶段演进

#### Phase 1: 查询引擎引入（轻量级）

**目标**: 零破坏性引入，查询性能从 O(n) → O(1)

**实现**:
- SQLite 仅用于查询，JSON 仍是唯一写入目标
- 启动时全量构建索引（增量更新）
- 写入不经过 SQLite，通过后台任务同步

**Schema 设计**:
```sql
CREATE TABLE tasks (
    id          TEXT PRIMARY KEY,
    priority    TEXT,
    status      TEXT,
    stage       TEXT,        -- Ralph Loop 阶段
    created_at  INTEGER,    -- Unix timestamp
    updated_at  INTEGER,
    parent_id   TEXT,
    raw_json    TEXT         -- 完整 JSON 冗余存储，简化同步
);

CREATE INDEX idx_priority ON tasks(priority);
CREATE INDEX idx_status ON tasks(status);
CREATE INDEX idx_stage ON tasks(stage);
CREATE INDEX idx_created ON tasks(created_at);
CREATE INDEX idx_parent ON tasks(parent_id);
```

**关键 API**:
```python
class QueryEngine:
    def build_index(self, task_list_path: str) -> None:
        """启动时全量构建索引"""

    def incremental_sync(self, task_id: str, task_data: dict) -> None:
        """增量同步单条任务"""

    def query(self, sql: str, *args) -> List[dict]:
        """执行查询"""

    def search(self, priority=None, status=None, stage=None) -> List[dict]:
        """便捷查询入口"""
```

#### Phase 2: 写入路径优化

**目标**: 写入不阻塞，后台异步同步

**实现**:
- 写入仍写 JSON，但立即返回
- SQLite 同步放入队列，后台 worker 处理
- 读取优先查 SQLite，fallback 查 JSON

**同步策略**:
```python
# 写入路径
def create_task(task_data):
    # 1. 立即写入 JSON（持久化）
    save_json(task_data)

    # 2. 放入同步队列（不阻塞）
    sync_queue.put((task_id, task_data))

# 后台 worker
def sync_worker():
    while True:
        task_id, task_data = sync_queue.get()
        try:
            db.upsert_task(task_id, task_data)
        except Exception as e:
            log.error(f"Sync failed: {e}")
            sync_queue.put((task_id, task_data))  # 重试
```

**一致性保证**:
- SQLite 是最终一致，不是强一致
- 读取时如发现 SQLite 与 JSON 不一致，以 JSON 为准
- 可设置 `force_rebuild` 强制全量重建

#### Phase 3: 混合真实源（可选）

**目标**: SQLite 成为查询真实源，JSON 作为备份

**触发条件**:
- SQLite 稳定性验证完成
- 性能收益明确
- 用户显式开启（`lra config set query_engine.mode=sqlite`）

**迁移策略**:
```python
def migrate_to_sqlite_primary():
    # 1. 全量同步 JSON → SQLite
    db.rebuild_from_json(json_path)

    # 2. 切换写入路径
    #    写 SQLite，JSON 成为只读备份

    # 3. 提供回滚机制
    #    lra config set query_engine.mode=json
```

---

## 实现方案

### 文件结构

```
lra/
├── query_engine.py          # 查询引擎核心
├── sync_worker.py           # 后台同步 worker
├── schema.sql               # SQLite schema 定义
└── ...

.long-run-agent/
├── task_list.json          # JSON 持久化
├── tasks/                  # 任务详情
├── lra_index.db            # SQLite 查询索引
└── lra_index.db.lock      # SQLite 锁文件
```

### 核心模块

#### QueryEngine 类

```python
class QueryEngine:
    """SQLite 查询引擎"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.get_index_db_path()
        self.db = sqlite3.connect(self.db_path)
        self._ensure_schema()

    def _ensure_schema(self):
        """确保索引表存在"""
        # ... schema 创建

    def build_index(self, task_list_path: str = None) -> int:
        """
        从 JSON 全量构建索引
        返回构建的记录数
        """
        # ... 全量扫描 JSON，构建索引

    def incremental_sync(self, task_id: str, task_data: dict) -> bool:
        """增量同步单条任务到索引"""
        # ... upsert

    def query(self, sql: str, *args) -> List[dict]:
        """执行查询，返回字典列表"""
        # ... sqlite query wrapper

    def search(self,
               priority: str = None,
               status: str = None,
               stage: str = None,
               parent_id: str = None) -> List[dict]:
        """便捷查询"""
        # ... 构建 WHERE 条件

    def get_stats(self) -> dict:
        """获取统计信息"""
        # ... count by status, priority, etc.

    def close(self):
        """关闭连接"""
        self.db.close()
```

#### SyncWorker 类

```python
import threading
import queue

class SyncWorker:
    """后台同步 worker"""

    def __init__(self, query_engine: QueryEngine):
        self.engine = query_engine
        self.queue = queue.Queue()
        self.running = False
        self.worker_thread = None

    def start(self):
        """启动后台同步"""
        self.running = True
        self.worker_thread = threading.Thread(target=self._run, daemon=True)
        self.worker_thread.start()

    def stop(self):
        """停止后台同步"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)

    def sync_task(self, task_id: str, task_data: dict):
        """提交同步任务"""
        self.queue.put((task_id, task_data))

    def _run(self):
        """Worker 主循环"""
        while self.running:
            try:
                task_id, task_data = self.queue.get(timeout=1)
                self.engine.incremental_sync(task_id, task_data)
            except queue.Empty:
                continue
            except Exception as e:
                log.error(f"Sync error: {e}")
```

---

## 向后兼容

### 模式自动检测

```python
def get_query_engine():
    """
    自动检测并返回合适的查询引擎
    """
    index_db = Config.get_index_db_path()

    if os.path.exists(index_db):
        # 有索引文件，使用 SQLite 引擎
        return SQLiteQueryEngine(index_db)
    else:
        # 无索引，使用传统 JSON 遍历
        return JSONQueryEngine()
```

### 用户可控开关

```python
# config.json
{
    "query_engine": {
        "enabled": true,           # 是否启用
        "mode": "auto",            # auto | sqlite | json
        "sync_interval": 5,         # 同步间隔（秒）
        "rebuild_on_startup": false # 启动时是否强制重建
    }
}
```

---

## 性能预期

### 查询性能对比

| 操作 | JSON O(n) | SQLite O(1) |
|------|-----------|-------------|
| list all | n | n (索引无帮助) |
| filter by priority | n | <n (索引) |
| filter by status | n | <n (索引) |
| get by id | n | 1 (主键) |
| count by status | n | 1 (索引) |

### 启动时间

| 任务数 | 纯 JSON | + 索引构建 |
|--------|---------|------------|
| 100 | 10ms | 50ms |
| 1000 | 100ms | 300ms |
| 10000 | 1s | 2s |

索引构建成本可控，且只需在启动时做一次。

---

## 测试计划

### 单元测试

```python
def test_query_engine_basic():
    engine = QueryEngine(':memory:')
    engine.build_index('tests/fixtures/task_list.json')

    results = engine.search(priority='P0')
    assert len(results) > 0

def test_incremental_sync():
    engine = QueryEngine(':memory:')
    engine.incremental_sync('task-1', {'id': 'task-1', 'priority': 'P0'})

    results = engine.search(priority='P0')
    assert len(results) == 1
```

### 集成测试

```python
def test_json_sqlite_consistency():
    """验证 JSON 和 SQLite 数据一致"""
    # 1. 创建任务
    # 2. 验证 JSON 已更新
    # 3. 等待同步
    # 4. 验证 SQLite 已同步
    # 5. 对比两边数据
```

---

## 迁移路径

### 现有项目

```bash
# 用户无需任何操作，自动检测并使用
lra list  # 自动构建索引（如果需要）
lra list  # 第二次调用享受加速
```

### 禁用查询引擎

```bash
# 如遇问题，可禁用
lra config set query_engine.enabled false

# 或强制使用 JSON 模式
lra config set query_engine.mode json
```

---

## 风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| SQLite 损坏 | JSON 仍是持久化源，可重建索引 |
| 同步延迟 | 读取优先 SQLite，fallback JSON |
| 首次启动慢 | 后台异步构建，不阻塞 CLI |
| 磁盘空间 | SQLite 通常比 JSON 更紧凑（有索引） |

---

## 决策点（待讨论）

1. **Phase 1 实现范围**: 是先实现查询功能，还是同步也做？
2. **索引字段**: 除了 priority/status/stage，还需要索引哪些字段？
3. **同步策略**: 同步失败时的重试次数和退避策略？
4. **数据校验**: 是否需要定期校验 JSON 和 SQLite 一致性？

---

## 进度追踪

- [ ] Phase 1: 查询引擎核心实现
- [ ] Phase 1: 与现有 task_manager 集成
- [ ] Phase 1: CLI 命令支持（`lra list` 走索引）
- [ ] Phase 2: 后台同步 worker
- [ ] Phase 2: 增量同步逻辑
- [ ] Phase 3: 混合真实源（可选）
