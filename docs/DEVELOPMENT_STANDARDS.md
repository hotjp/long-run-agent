# 开发标准

## 技术规范

### 1. 领域模型设计
- ✅ 必须进行领域模型设计
- ✅ 使用 UML 类图或文档说明
- ✅ 清晰定义实体对象和关系
- ✅ 设计合理的聚合根和值对象

### 2. 后端接口规范
- ✅ 必须提供 Swagger/OpenAPI 文档
- ✅ 接口使用 RESTful 风格
- ✅ 统一的响应格式
- ✅ 完善的接口注释和参数说明

### 3. 前端框架要求
- ✅ 必须使用现代前端框架（React/Vue/Angular）
- ✅ 遵循框架的最佳实践
- ✅ 组件化开发

### 4. 组件库使用
- ✅ 优先使用成熟的组件库（Ant Design/Element UI/Material-UI）
- ✅ 自定义组件必须有复用价值
- ✅ 组件库组件无法满足需求时才自定义

### 5. 前后端分离
- ✅ 严格前后端分离
- ✅ 正确处理跨域问题（CORS 配置）
- ✅ 使用 JWT 或 Session 认证

### 6. 前端工程化
- ✅ 统一的环境变量管理（env 文件）
- ✅ 后端接口地址配置（BASE_URL）
- ✅ 接口请求统一封装（axios/fetch wrapper）
- ✅ 统一的错误处理和提示（Toast/Modal）
- ✅ 公共函数抽取（utils、helpers）
- ✅ 公共变量抽取（constants、config）

### 7. 错误处理
- ✅ 统一的错误码定义
- ✅ 统一的错误提示（用户友好的消息）
- ✅ 错误日志记录
- ✅ 网络错误重试机制

### 8. 代码质量
- ✅ 使用 ESLint/Prettier 代码规范
- ✅ 使用 TypeScript（推荐）
- ✅ 合理的代码注释
- ✅ 清晰的目录结构

### 9. 测试
- ✅ 使用 Playwright 进行端到端测试
- ✅ 编写单元测试
- ✅ 测试覆盖率 > 70%

### 10. 问题解决
- ✅ 遇到资料不全时可联网搜索解决方案
- ✅ 记录搜索到的解决方案
- ✅ 验证解决方案的可行性

### 11. 文档编写
- ✅ 必须编写项目文档（README.md）
- ✅ 必须编写安装部署文档（INSTALL.md、DEPLOYMENT.md）
- ✅ 必须编写架构设计文档（ARCHITECTURE.md）
- ✅ 必须编写用户使用文档（USER_GUIDE.md）
- ✅ 必须编写开发指南（DEVELOPMENT_GUIDE.md）
- ✅ 必须编写变更日志（CHANGELOG.md）
- ✅ 文档必须清晰、准确、及时更新

---

## 项目结构模板

### 后端结构
```
backend/
├── src/
│   ├── domain/           # 领域模型
│   │   ├── entities/    # 实体
│   │   ├── value-objects/# 值对象
│   │   └── repositories/# 仓储接口
│   ├── application/      # 应用层
│   │   ├── services/    # 应用服务
│   │   └── dto/         # 数据传输对象
│   ├── infrastructure/   # 基础设施
│   │   ├── database/    # 数据库配置
│   │   ├── repositories/# 仓储实现
│   │   └── external/    # 外部服务
│   ├── interfaces/       # 接口层
│   │   ├── controllers/ # 控制器
│   │   ├── routes/      # 路由
│   │   └── middleware/ # 中间件
│   └── shared/          # 共享代码
│       ├── errors/       # 错误定义
│       ├── utils/        # 工具函数
│       └── constants/    # 常量
├── docs/                # 文档（Swagger 生成的）
├── tests/               # 测试
│   ├── unit/            # 单元测试
│   └── e2e/             # 端到端测试（Playwright）
└── package.json
```

### 前端结构
```
frontend/
├── src/
│   ├── api/              # API 封装
│   │   ├── client.ts     # Axios 实例
│   │   ├── modules/      # 各模块 API
│   │   └── types.ts      # API 类型
│   ├── assets/           # 静态资源
│   ├── components/       # 公共组件
│   │   ├── common/       # 通用组件
│   │   └── business/     # 业务组件
│   ├── config/           # 配置
│   │   └── env.ts        # 环境变量
│   ├── hooks/            # 自定义 Hooks
│   ├── layouts/          # 布局
│   ├── pages/            # 页面
│   ├── router/           # 路由
│   ├── stores/           # 状态管理
│   ├── styles/           # 样式
│   ├── types/            # 类型定义
│   └── utils/            # 工具函数
│       ├── request.ts    # 请求封装
│       └── error.ts      # 错误处理
├── public/
├── tests/               # 测试
│   ├── e2e/             # 端到端测试（Playwright）
│   └── specs/           # 测试用例
├── .env.development      # 开发环境变量
├── .env.production       # 生产环境变量
└── package.json
```

---

## 实现检查清单

每个功能开发前必须确认：

### 后端
- [ ] 领域模型已设计
- [ ] Swagger 文档已更新
- [ ] 接口遵循 RESTful 规范
- [ ] 跨域已正确配置
- [ ] 错误处理已实现
- [ ] 单元测试已编写
- [ ] Playwright 端到端测试已编写

### 前端
- [ ] 页面使用组件库组件
- [ ] 环境变量已配置（BASE_URL）
- [ ] API 请求使用统一封装
- [ ] 错误处理使用统一提示
- [ ] 公共函数已抽取
- [ ] 组件已复用
- [ ] 响应式适配已完成
- [ ] Playwright 端到端测试已编写

---

## Playwright 测试示例

### 后端 API 测试

```typescript
// tests/e2e/api/auth.spec.ts
import { test, expect } from '@playwright/test';

test.describe('用户认证 API', () => {
  test('用户注册', async ({ request }) => {
    const response = await request.post('/api/auth/register', {
      data: {
        username: 'testuser',
        password: 'password123',
        email: 'test@example.com',
      },
    });

    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data).toHaveProperty('token');
  });

  test('用户登录', async ({ request }) => {
    const response = await request.post('/api/auth/login', {
      data: {
        username: 'testuser',
        password: 'password123',
      },
    });

    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data).toHaveProperty('token');
  });
});
```

### 前端页面测试

```typescript
// tests/e2e/pages/login.spec.ts
import { test, expect } from '@playwright/test';

test.describe('登录页面', () => {
  test('显示登录表单', async ({ page }) => {
    await page.goto('http://localhost:3000/login');

    await expect(page.locator('input[name="username"]')).toBeVisible();
    await expect(page.locator('input[name="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('成功登录', async ({ page }) => {
    await page.goto('http://localhost:3000/login');

    await page.fill('input[name="username"]', 'testuser');
    await page.fill('input[name="password"]', 'password123');
    await page.click('button[type="submit"]');

    // 等待跳转到首页
    await page.waitForURL('http://localhost:3000/dashboard');

    // 验证登录成功
    await expect(page).toHaveURL(/dashboard/);
  });

  test('登录失败显示错误', async ({ page }) => {
    await page.goto('http://localhost:3000/login');

    await page.fill('input[name="username"]', 'wronguser');
    await page.fill('input[name="password"]', 'wrongpass');
    await page.click('button[type="submit"]');

    // 验证错误提示
    const errorMessage = page.locator('.error-message');
    await expect(errorMessage).toBeVisible();
    await expect(errorMessage).toContainText('用户名或密码错误');
  });
});
```

---

## 联网搜索

当遇到技术问题时，会自动联网搜索解决方案。

### 搜索工具
- ✅ **Tavily Search**（AI 增强搜索，推荐使用）
- ✅ Web Fetch（抓取文档）

### Tavily Search 使用

```bash
# 基础搜索
python scripts/tavily_search.py "搜索内容"

# 返回更多结果
python scripts/tavily_search.py "搜索内容" --max-results 15

# 输出 JSON 格式
python scripts/tavily_search.py "搜索内容" --json

# Python 代码中调用
import sys
sys.path.insert(0, '/root/.openclaw/workspace/skills/tavily-search/scripts')
from tavily_search import tavily_search, format_result

# 搜索
result = tavily_search("搜索内容", max_results=5)
print(format_result(result))
```

### 搜索策略
1. 使用 Tavily Search 进行 AI 增强搜索
2. 搜索官方文档
3. 搜索 Stack Overflow
4. 搜索 GitHub Issues
5. 搜索技术博客

### 验证步骤
1. 阅读 Tavily 返回的 AI 答案摘要
2. 查看搜索结果列表
3. 筛选最佳方案
4. 记录解决方案
5. 实施验证
6. 记录结果

---

## 项目文档模板

### README.md（项目简介）

```markdown
# 项目名称

简短的项目描述（1-2 句话）

## 功能特性

- 功能 1
- 功能 2
- 功能 3

## 技术栈

- 前端: [框架]
- 后端: [框架]
- 数据库: [数据库]

## 快速开始

### 安装

```bash
npm install
```

### 开发

```bash
npm run dev
```

### 构建

```bash
npm run build
```

## 文档

- [架构设计](./ARCHITECTURE.md)
- [用户指南](./USER_GUIDE.md)
- [开发指南](./DEVELOPMENT_GUIDE.md)
- [部署文档](./DEPLOYMENT.md)

## 许可证

MIT
```

### ARCHITECTURE.md（架构设计）

```markdown
# 架构设计

## 系统架构

### 整体架构图

```
[前端] ←→ [API 网关] ←→ [后端服务] ←→ [数据库]
```

### 技术架构

- 前端: [框架]
- 后端: [框架]
- 数据库: [数据库]

## 领域模型

### 实体关系图

```
用户 1--N 任务
任务 1--N 评论
```

### 核心实体

#### User（用户）
- id: string
- username: string
- email: string
- ...

#### Task（任务）
- id: string
- title: string
- description: string
- status: TaskStatus
- ...

## 模块设计

### 前端模块

- api/ - API 封装
- components/ - 组件
- pages/ - 页面
- stores/ - 状态管理
- ...

### 后端模块

- domain/ - 领域层
- application/ - 应用层
- infrastructure/ - 基础设施层
- interfaces/ - 接口层

## API 设计

### RESTful 规范

- 使用名词复数
- 使用 HTTP 方法（GET/POST/PUT/DELETE）
- 统一的响应格式

### API 列表

#### 用户认证

- POST /api/auth/register - 用户注册
- POST /api/auth/login - 用户登录
- POST /api/auth/logout - 用户登出

#### 任务管理

- GET /api/tasks - 获取任务列表
- POST /api/tasks - 创建任务
- PUT /api/tasks/:id - 更新任务
- DELETE /api/tasks/:id - 删除任务

## 安全设计

- JWT 认证
- CORS 配置
- 输入验证
- SQL 注入防护

## 性能优化

- 前端: 代码分割、懒加载
- 后端: 缓存、数据库索引
- 数据库: 查询优化
```

### USER_GUIDE.md（用户指南）

```markdown
# 用户指南

## 功能说明

### 用户注册和登录

1. 打开应用
2. 点击"注册"按钮
3. 填写用户名、邮箱、密码
4. 点击"提交"
5. 注册成功后自动登录

### 创建任务

1. 登录后进入首页
2. 点击"新建任务"按钮
3. 填写任务标题和描述
4. 选择任务优先级
5. 点击"保存"

### 编辑任务

1. 在任务列表中找到要编辑的任务
2. 点击任务卡片
3. 修改任务信息
4. 点击"保存"

### 删除任务

1. 在任务列表中找到要删除的任务
2. 点击任务卡片上的删除图标
3. 确认删除

## 常见问题

### Q: 忘记密码怎么办？

A: 点击登录页面的"忘记密码"链接，通过邮箱重置密码。

### Q: 如何导出任务数据？

A: 在任务列表页面，点击"导出"按钮，选择导出格式。

## 快捷键

- `Ctrl + N` - 新建任务
- `Ctrl + F` - 搜索任务
- `Ctrl + E` - 编辑任务
```

### DEVELOPMENT_GUIDE.md（开发指南）

```markdown
# 开发指南

## 环境要求

- Node.js >= 16
- npm >= 8
- [其他依赖]

## 安装步骤

```bash
# 克隆项目
git clone [仓库地址]
cd [项目目录]

# 安装依赖
npm install

# 配置环境变量
cp .env.example .env.local
# 编辑 .env.local

# 初始化数据库
npm run db:migrate

# 启动开发服务器
npm run dev
```

## 项目结构

```
项目目录/
├── frontend/          # 前端项目
│   ├── src/
│   ├── package.json
│   └── ...
├── backend/           # 后端项目
│   ├── src/
│   ├── package.json
│   └── ...
├── docs/              # 文档
└── README.md
```

## 开发命令

```bash
# 启动前端开发服务器
npm run dev:frontend

# 启动后端开发服务器
npm run dev:backend

# 启动所有服务
npm run dev

# 运行测试
npm test

# 运行端到端测试
npm run test:e2e

# 代码检查
npm run lint

# 代码格式化
npm run format

# 构建
npm run build

# 运行生产环境
npm run start
```

## 代码规范

### 前端

- 使用 TypeScript
- 组件使用 PascalCase
- 文件使用 kebab-case
- 使用 ESLint 和 Prettier

### 后端

- 遵循领域驱动设计（DDD）
- 使用 TypeScript
- 使用 Swagger 文档

## Git 工作流

```bash
# 创建功能分支
git checkout -b feature/功能名

# 提交代码
git add .
git commit -m "feat: 实现功能"

# 推送到远程
git push origin feature/功能名

# 创建 Pull Request
```

---

## Git 提交规范

### 1. 提交信息格式

**格式：** `type(scope): subject`

**类型（type）：**
- `feat`: 新功能
- `fix`: 修复 Bug
- `docs`: 文档变更
- `style`: 代码格式（不影响功能）
- `refactor`: 重构（既不是新功能也不是修复）
- `test`: 添加测试
- `chore`: `构建过程或辅助工具的变动`
- `perf`: 性能优化
- `ci`: CI 配置文件变更

**作用域（scope）：**
- `backend-go`: Go 后端模块
- `backend-python`: Python 后端模块
- `frontend`: 前端模块
- `architecture`: 架构设计
- `database`: 数据库设计
- `deployment`: 部署配置

**主题（subject）：**
- 简短描述（不超过 50 字符）
- 使用中文（项目使用中文）
- 不以句号结尾
- 使用祈使句

### 2. 提交信息正文规范

**必须包含以下内容：**

1. **Feature ID**（从 feature_list.json 获取）
2. **功能名称**（与 feature_list.json 一致）
3. **完成步骤**（对照 feature 列表中的 steps）
4. **测试结果**（单元测试、E2E 测试）
5. **新增/修改文件**（主要变更）

**示例模板：**

```
feat(scope): 功能名称（Feature ID）

功能名称：
- [x] 步骤1（完成打钩）
- [x] 步骤2
- [ ] 步骤3（未完成）

测试：
- 单元测试：x/x 通过
- E2E 测试：y/y 通过

变更：
- 新增：文件列表
- 修改：文件列表

关联：feature_xxx
```

### 3. 完整示例

#### 示例 1：后端功能实现

```
feat(backend-python): 实现数据清洗与去重服务（Feature 013）

功能：
- [x] 实现HTML清洗（移除标签、提取纯文本、保留段落格式）
- [x] 实现文本规范化（移除噪音、全角转半角、分句）
- [x] 实现SimHash去重（64位指纹计算、汉明距离判断）
- [x] 实现相似度计算（Jaccard、余弦相似度）
- [x] 编写测试（33个单元测试）
- [x] 性能测试（大文本、批量去重）

测试结果：
- 单元测试：33/33 通过
- 性能测试：通过（1000条文本去重 < 5秒）

变更文件：
- 新增：backend/python/data_cleaner.py
- 新增：backend/python/tests/test_data_cleaner.py

依赖：
- jieba：中文分词
- beautifulsoup4：HTML 解析

关联：feature_013
```

#### 示例 2：架构设计

```
feat(architecture): 完成数据库设计（Feature 033）

设计内容：
- [x] 设计article表（舆情文章）
- [x] 设计article_llm表（AI分析）
- [x] 设计event表（舆情事件）
- [x] 设计task表（监测任务）
- [x] 设计索引（复合索引、唯一索引）
- [x] 编写SQL文档（SCHEMA.sql）
- [x] 数据模型验证（17张表）

表结构：
- 租户相关：tenant, role, permission, role_permission, user（5张）
- 任务相关：task（1张）
- 文章相关：article, article_llm（2张）
- 事件相关：event（1张）
- 预警相关：alert_rule, alert（2张）
- 工单相关：ticket, ticket_log（2张）
- 报告相关：report（1张）
- 配置相关：system_config, tenant_config（2张）
- 统计相关：task_statistics, tenant_statistics（2张）

变更文件：
- 新增：backend/database/SCHEMA.sql
- 新增：backend/database/README.md

技术规格：
- MySQL 8.0+
- utf8mb4 字符集（支持 emoji）
- InnoDB 引擎（事务支持）
- 17 张核心表

关联：feature_033
```

#### 示例 3：Bug 修复

```
fix(backend-python): 修复 SimHash 距离计算类型错误（Feature 013）

问题描述：
is_duplicate() 方法接收字符串参数，但 distance() 需要整数
导致 TypeError: unsupported operand type(s) for ^: 'str' and 'str'

修复内容：
- [x] 添加 int() 类型转换
- [x] 修复 is_duplicate() 方法
- [x] 更新单元测试
- [x] 验证修复结果

测试结果：
- 单元测试：33/33 通过（之前 3 个测试失败）
- 修复前：2 个错误，1 个失败
- 修复后：全部通过

变更文件：
- 修改：backend/python/data_cleaner.py
- 修改：backend/python/tests/test_data_cleaner.py

关联：feature_013
```

### 4. 验收规范（Review Checklist）

**Reviewer 可以对照 feature 列表验收：**

```bash
# 1. 查看提交信息
git log -1 --pretty=full

# 2. 查看变更文件
git show --name-only HEAD

# 3. 对比 feature 列表
python3 feature_manager.py get --feature-id feature_xxx

# 4. 运行测试
npm test
# 或
pytest

# 5. 检查代码规范
npm run lint
# 或
flake8 .
```

**验收清单：**

- [ ] 提交信息格式正确（type(scope): subject）
- [ ] 提交信息包含 Feature ID
- [ ] 提交信息包含功能名称（与 feature 列表一致）
- [ ] 提交信息包含完成步骤（对照 feature 列表的 steps）
- [ ] 提交信息包含测试结果
- [ ] 提交信息包含变更文件
- [ ] 所有步骤标记 [x]（完成）
- [ ] 测试全部通过
- [ ] 代码通过 Lint 检查
- [ ] 代码符合项目规范

### 5. 提交前检查（Pre-commit Hook）

**建议在提交前自动检查：**

```bash
# .git/hooks/pre-commit
#!/bin/bash

# 1. 运行测试
npm test
if [ $? -ne 0 ]; then
  echo "❌ 测试失败，禁止提交"
  exit 1
fi

# 2. 运行 Lint
npm run lint
if [ $? -ne 0 ]; then
  echo "❌ Lint 失败，请先修复"
  exit 1
fi

# 3. 检查提交信息格式
# 提取提交信息格式化检查
# ...

echo "✅ 预检查通过"
```

### 6. Commit Message vs Feature List 对照表

| Feature ID | Feature 名称 | 步骤（steps） | 提交信息验证 |
|-----------|-------------|----------------|--------------|
| feature_013 | 数据清洗与去重 | 1. 实现HTML清洗<br>2. 实现文本规范化<br>3. 实现SimHash去重<br>4. 实现相似度计算<br>5. 编写测试<br>6. 性能测试 | ✅ 包含所有步骤<br>✅ 测试结果：33/33 通过<br>✅ 包含文件列表 |
| feature_033 | 数据库设计 | 1. 设计article表<br>2. 设计article_llm表<br>3. 设计event表<br>4. 设计task表<br>5. 设计索引<br>6. 编写SQL文档<br>7. 数据模型验证 | ✅ 包含所有步骤<br>✅ 表结构说明清晰<br>✅ 包含技术规格 |

**Reviewer 验收步骤：**

1. 查看 Git 提交信息
2. 对比 feature_list.json 中的步骤
3. 验证所有步骤是否完成（[x] 标记）
4. 验证测试结果是否通过
5. 验证变更文件是否合理
6. 运行测试验证
7. 代码 Review

### 7. 常见错误和纠正

**错误示例：**

```
# ❌ 错误 1：没有 Feature ID
feat(backend-python): 数据清洗与去重

# ✅ 正确：
feat(backend-python): 实现数据清洗与去重服务（Feature 013）
功能：
- [x] 实现HTML清洗
...
关联：feature_013
```

```
# ❌ 错误 2：没有步骤完成情况
feat(backend-python): 实现数据清洗与去重服务（Feature 013）
完成了HTML清洗、文本规范化等功能

# ✅ 正确：
feat(backend-python): 实现数据清洗与去重服务（Feature 013）
功能：
- [x] 实现HTML清洗
- [x] 实现文本规范化
- [ ] 实现SimHash去重
```

```
# ❌ 错误 3：没有测试结果
feat(backend-python): 实现数据清洗与去重服务（Feature 013）
功能：...

# ✅ 正确：
feat(backend-python): 实现数据清洗与去重服务（Feature 013）
功能：...
测试：
- 单元测试：33/33 通过
- 性能测试：通过
```

## 调试指南

### 前端调试

1. 打开浏览器开发者工具
2. 在代码中设置断点
3. 使用 React DevTools 查看组件状态

### 后端调试

1. 使用 debugger 语句
2. 使用 console.log 输出日志
3. 查看 API 文档测试接口

## 常见问题

### Q: 端口被占用

A: 修改 .env 文件中的端口配置

### Q: 数据库连接失败

A: 检查数据库是否启动，检查连接配置
```

### DEPLOYMENT.md（部署文档）

```markdown
# 部署文档

## 环境变量配置

### 前端环境变量

```env
# API 地址
VITE_API_BASE_URL=https://api.example.com

# 其他配置
VITE_APP_TITLE=项目名称
```

### 后端环境变量

```env
# 数据库配置
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname

# JWT 密钥
JWT_SECRET=your-secret-key

# 端口
PORT=3000

# 其他配置
NODE_ENV=production
```

## 构建步骤

### 前端构建

```bash
cd frontend
npm run build
```

### 后端构建

```bash
cd backend
npm run build
```

## 部署方式

### Docker 部署

```dockerfile
# docker-compose.yml
version: '3'
services:
  frontend:
    build: ./frontend
    ports:
      - "80:80"
    environment:
      - VITE_API_BASE_URL=https://api.example.com

  backend:
    build: ./backend
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgresql://...
      - JWT_SECRET=...

  database:
    image: postgres:14

    environment:
      - POSTGRES_DB=dbname
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
```

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 云平台部署（Vercel、Railway 等）

#### Vercel（前端）

1. 连接 GitHub 仓库
2. 配置环境变量
3. 自动部署

#### Railway（后端）

1. 连接 GitHub 仓库
2. 配置数据库
3. 自动部署

## 健康检查

### 前端健康检查

```bash
curl https://example.com/health
# 返回: {"status": "ok"}
```

### 后端健康检查

```bash
curl https://api.example.com/health
# 返回: {"status": "ok", "version": "1.0.0"}
```

## 监控和日志

### 应用监控

- 使用 Sentry 错误监控
- 使用 Google Analytics 用户分析

### 日志管理

- 日志级别: DEBUG、INFO、WARN、ERROR
- 日志格式: JSON
- 日志轮转: 按日期和大小

## 备份策略

### 数据库备份

```bash
# 每天自动备份
pg_dump dbname > backup-$(date +%Y%m%d).sql
```

### 文件备份

- 使用云存储（AWS S3、阿里云 OSS）
- 定期备份重要文件
```

### CHANGELOG.md（变更日志）

```markdown
# 变更日志

本文档记录项目的所有重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [未发布]

## [1.0.0] - 2024-02-18

### 新增

- 用户注册和登录功能
- 任务创建、编辑、删除功能
- 任务列表显示和筛选
- 用户权限管理
- API 文档（Swagger）

### 变更

- 重构用户认证模块
- 优化任务查询性能

### 修复

- 修复任务删除时的权限问题
- 修复前端状态同步问题

### 安全

- 添加输入验证
- 强化 JWT 认证
- 配置 CORS 白名单

## [0.9.0] - 2024-02-10

### 新增

- 初始版本
- 基础任务管理功能

---

[未发布]: https://github.com/user/project/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/user/project/releases/tag/v1.0.0
[0.9.0]: https://github.com/user/project/releases/tag/v0.9.0
```

---

## 验收标准

项目交付时必须满足：

1. ✅ 领域模型文档完整
2. ✅ Swagger 文档可访问
3. ✅ 前端页面正常显示
4. ✅ 组件库组件使用率 > 80
5. ✅ 跨域问题已解决
6. ✅ 环境变量配置正确
7. ✅ API 统一封装
8. ✅ 错误提示统一友好
9. ✅ 代码通过 ESLint 检查
10. ✅ 测试覆盖率 > 70%
11. ✅ Playwright 端到端测试全部通过

### 文档完整性

12. ✅ README.md - 项目简介和快速开始
13. ✅ ARCHITECTURE.md - 架构设计和领域模型
14. ✅ USER_GUIDE.md - 用户使用指南
15. ✅ DEVELOPMENT_GUIDE.md - 开发指南
16. ✅ DEPLOYMENT.md - 部署文档
17. ✅ CHANGELOG.md - 变更日志
18. ✅ 所有文档清晰、准确、及时更新

### 交付产物清单

项目交付时必须包含以下文件和目录：

```
项目根目录/
├── README.md                          # ✅ 必需
├── ARCHITECTURE.md                    # ✅ 必需
├── USER_GUIDE.md                      # ✅ 必需
├── DEVELOPMENT_GUIDE.md                # ✅ 必需
├── DEPLOYMENT.md                      # ✅ 必需
├── CHANGELOG.md                       # ✅ 必需
├── LICENSE                            # 可选
├── .gitignore                         # ✅ 必需
├── frontend/                          # 前端项目
│   ├── src/
│   ├── tests/                         # ✅ 必需（包含 Playwright 测试）
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts / webpack.config.js
│   ├── .env.development               # ✅ 必需
│   ├── .env.production                # ✅ 必需
│   └── README.md
├── backend/                           # 后端项目
│   ├── src/
│   ├── tests/                         # ✅ 必需（包含单元测试和 E2E 测试）
│   ├── package.json
│   ├── tsconfig.json
│   └── README.md
├── docs/                              # 额外文档（可选）
│   ├── api/                           # API 文档（Swagger 自动生成）
│   ├── diagrams/                      # 架构图
│   └── ...
└── docker-compose.yml                 # 可选（Docker 部署）
```

### 文档质量检查

每个文档必须满足：

- ✅ 格式清晰（使用 Markdown）
- ✅ 内容准确（与实际代码一致）
- ✅ 及时更新（代码变更后同步更新）
- ✅ 示例完整（代码示例可运行）
- ✅ 图表清晰（架构图、流程图）
- ✅ 中英文对照（可选）
