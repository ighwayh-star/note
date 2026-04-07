# 记账应用 MVP（Vue + FastAPI）

## 功能

- 用户注册/登录（JWT）
- 手动记账：流水 CRUD（新增/编辑/删除/列表/搜索）
- 基础统计：时间范围内收支汇总、按分类汇总
- AI（只读 v1）：对话式查询/统计（默认 rule 模式，可切换 OpenAI + LangChain）

## 本地运行

### 1) 启动后端（FastAPI）

在项目根目录打开终端：

```powershell
cd api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt

如果依赖下载很慢，可尝试加镜像：`pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt`

$env:DATABASE_URL = "sqlite:///./app.db"
$env:JWT_SECRET = "dev-secret-change-me"
$env:AI_MODE = "rule"

uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- 健康检查：`http://127.0.0.1:8000/health`
- 接口文档：`http://127.0.0.1:8000/api/docs`

### 2) 启动前端（Vue）

另开一个终端，在项目根目录：

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

- 默认 `AI_MODE=rule`：不依赖外部模型，支持基础“汇总/按分类/流水明细”的自然语言查询（建议消息里带明确日期范围：`YYYY-MM-DD 到 YYYY-MM-DD`）
- 使用 OpenAI（LangChain 工具调用）：
  - `cd api`
  - `pip install -r requirements-ai.txt`
  - 设置环境变量：
    - `$env:AI_MODE = "openai"`
    - `$env:OPENAI_API_KEY = "<your-key>"`
    - `$env:OPENAI_MODEL = "gpt-4o-mini"`
  - 入口接口：`POST /api/ai/chat`，Body：`{"message":"..."}`
  - 状态检查：`GET /api/ai/status`（可查看是否已正确识别 key 与依赖）
