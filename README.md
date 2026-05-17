# 记账应用 MVP（Vue + FastAPI）

## 线上地址

- 前端：https://ighwayh-star.github.io/note/
- 后端：Railway 部署（需配置 `VITE_API_BASE`）

## 功能

- 用户注册/登录（JWT）
- 手动记账：流水 CRUD（新增/编辑/删除/列表/搜索）
- 基础统计：时间范围内收支汇总、按分类汇总
- AI（只读 v1）：对话式查询/统计（默认 rule 模式，可切换 OpenAI + LangChain）

## 部署架构

- **前端**：GitHub Pages（`.github/workflows/pages.yml`，push main 自动部署）
- **后端**：Railway（FastAPI + PostgreSQL）
- 前端构建时通过 `VITE_API_BASE` 变量指定后端地址，在 GitHub repo Settings → Secrets and variables → Actions → Variables 中设置

## 本地运行

### 1) 启动后端（FastAPI）

```powershell
cd api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

$env:DATABASE_URL = “sqlite:///./app.db”
$env:JWT_SECRET = “dev-secret-change-me”
$env:AI_MODE = “rule”

uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- 健康检查：`http://127.0.0.1:8000/health`
- 接口文档：`http://127.0.0.1:8000/api/docs`

### 2) 启动前端（Vue）

```powershell
npm install
npm run dev
```

打开 `http://127.0.0.1:5173`。

## 测试

### 后端测试

```powershell
cd api
.\.venv\Scripts\Activate.ps1
pytest -q
```

### 前端类型检查

```powershell
npm run check
```

## AI 接入（LangChain）

- 默认 `AI_MODE=rule`：不依赖外部模型，支持基础”汇总/按分类/流水明细”的自然语言查询
- DeepSeek / OpenAI：
  - `pip install -r requirements-ai.txt`
  - 设置环境变量：`AI_MODE=deepseek`、`DEEPSEEK_API_KEY=<your-key>` 等
  - 入口接口：`POST /api/ai/chat`
  - 状态检查：`GET /api/ai/status`
