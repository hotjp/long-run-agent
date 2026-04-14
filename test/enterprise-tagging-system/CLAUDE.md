# 企业标签系统 - Claude Code 项目指南

## 项目概述

**项目**: 企业标签系统
**描述**: 为企业级应用提供统一的标签管理和查询服务
**外部依赖**: auth-center (IAM), api-gateway
**状态**: 规划阶段 (LRA: task_001 进行中)

## 当前任务

**进行中**: task_001 - 需求分析与架构设计
**下一步**: 查看 `lra ready` 获取可认领任务

## 架构决策

### 技术选型

| 组件 | 选型 | 原因 |
|------|------|------|
| 存储 | PostgreSQL | 企业级可靠，支持 JSON |
| 缓存 | Redis | 高并发场景 |
| API | REST + GraphQL | 兼容现有系统 |
| 认证 | auth-center | 企业 SSO |

### 外部服务集成

详见: [.long-run-agent/config.json](.long-run-agent/config.json)

```json
{
  "external_services": {
    "auth-center": {
      "type": "iam_service",
      "endpoint": "http://auth-center.internal:8080"
    }
  }
}
```

## 项目结构

```
enterprise-tagging-system/
├── src/                    # 源代码
│   ├── api/               # REST API
│   ├── graphql/          # GraphQL API
│   ├── storage/           # 数据存储层
│   └── auth/              # auth-center 集成
├── tests/                 # 测试
├── deploy/                # 部署配置
└── .long-run-agent/      # LRA 任务管理
```

## 标签数据模型

> 详细设计见: task_002

```
Tag {
  id: UUID
  name: String
  namespace: String      # 命名空间隔离
  tenant_id: String      # 多租户
  created_by: String
  created_at: Timestamp
  metadata: JSON
}

TagRelation {
  id: UUID
  tag_id: UUID
  resource_type: String  # user, document, asset, etc.
  resource_id: String
}
```

## 任务进度

| 任务 | 状态 | LRA |
|------|------|-----|
| 需求分析与架构设计 | pending | task_001 |
| 标签数据模型设计 | pending | task_002 |
| 标签存储层实现 | pending | task_003 |
| 标签查询API实现 | pending | task_004 |
| 权限与安全模块 | pending | task_005 |
| 多租户支持 | pending | task_006 |
| 前端管理界面 | pending | task_007 |
| 部署与运维 | pending | task_008 |

**查看详情**: `lra status`

## 开发指南

### 快速开始

```bash
# 查看任务
lra list
lra ready          # 可认领的任务

# 开始工作
lra claim task_002
lra show task_002  # 查看任务详情

# 推进状态
lra set <task_id> in_progress
lra checkpoint <task_id> --note "完成设计"
```

### 提交规范

```bash
git commit -m "feat(tags): 实现标签查询 API

- 添加 TagController
- 实现 TagService
- 集成 auth-center 鉴权

Closes: task_004"
```

### Constitution 质量门控

本项目使用 Constitution 验证，详见:

```bash
lra constitution show  # 查看 Constitution 规则
```

**关键规则**:
- P0 任务必须通过所有质量检查
- 提交前运行 `lra check <task_id>`

## 相关文档

- [AGENTS.md](AGENTS.md) - Agent 工作流指南
- [.long-run-agent/config.json](.long-run-agent/config.json) - 外部服务配置
- [docs/](./docs) - 详细设计文档
