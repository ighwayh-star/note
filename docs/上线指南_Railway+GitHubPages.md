# 上线指南（Railway 后端 + GitHub Pages 前端）

目标：把这个项目上线成"任何人都能访问"的网站。

推荐结构：
- 前端（Vue/Vite）：GitHub Pages 静态托管
- 后端（FastAPI）：Railway Web Service
- 数据库：Railway Postgres

## 1. 后端上线到 Railway

### 1.1 创建项目与服务

1) 打开 Railway，新建 Project  
2) Add Service → Deploy from GitHub → 选择你的仓库 `ighwayh-star/note`  
3) 设置 Root Directory 为 `api`

### 1.2 绑定 Postgres

1) Add → Database → Postgres  
2) Railway 自动注入数据库连接字符串

### 1.3 配置 Build/Start

在 Railway 服务设置中：
- Build Command：`pip install -r requirements.txt -r requirements-ai.txt`
- Start Command：`uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### 1.4 配置环境变量（必填）

在 Railway 的 Variables 中添加：
- `DATABASE_URL`：Postgres 连接（Railway 自动提供）
- `JWT_SECRET`：强随机字符串
- `AI_MODE=deepseek`
- `DEEPSEEK_API_KEY=<你的key>`
- `DEEPSEEK_MODEL=deepseek-chat`
- `DEEPSEEK_BASE_URL=https://api.deepseek.com`
- `CORS_ORIGINS`：`["https://ighwayh-star.github.io"]`

### 1.5 验证后端

Railway 部署成功后会得到公网域名，例如 `https://xxx.up.railway.app`。

验证：
- `GET https://xxx.up.railway.app/health` 返回 `{"status":"ok"}`
- `GET https://xxx.up.railway.app/api/docs` 打开 Swagger

## 2. 前端上线到 GitHub Pages

### 2.1 启用 GitHub Pages

1) 进入 GitHub repo → Settings → Pages  
2) Source 选择 **GitHub Actions**

### 2.2 配置 API 地址

在 GitHub repo → Settings → Secrets and variables → Actions → Variables：
- 添加 `VITE_API_BASE` = `https://<你的railway后端域名>`

### 2.3 触发部署

Push 到 `main` 分支即自动触发构建部署（`.github/workflows/pages.yml`）。

也可以在 Actions → "Deploy to GitHub Pages" → Run workflow 手动触发。

部署成功后访问：`https://ighwayh-star.github.io/note/`

## 3. AI 对外开放的安全建议

因为 AI 会产生模型调用成本，建议：
- 对 `/api/ai/chat`、`/api/ai/confirm` 做频率限制
- 给新注册用户设置每日额度
- 后台监控调用量
