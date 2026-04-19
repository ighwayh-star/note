# 上线指南（Railway 后端 + Vercel 前端）

目标：把这个项目上线成“任何人都能访问”的网站。

推荐结构：
- 前端（Vue/Vite）：Vercel 静态托管
- 后端（FastAPI）：Railway Web Service
- 数据库：Railway Postgres
- 域名：`www.xxx.com`（前端） + `api.xxx.com`（后端）

## 1. 后端上线到 Railway

### 1.1 创建项目与服务

1) 打开 Railway，新建 Project  
2) Add Service → Deploy from GitHub → 选择你的仓库 `ighwayh-star/note`  
3) 设置 Root Directory 为 `api`（非常关键，否则会把前端当成根目录）

### 1.2 绑定 Postgres

1) Add → Database → Postgres  
2) Railway 会生成数据库连接字符串（一般会注入到环境变量中）

### 1.3 配置 Build/Start

在 Railway 服务设置中：
- Build Command（示例）：
  - `pip install -r requirements.txt -r requirements-ai.txt`
- Start Command（示例二选一）：
  - `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
  - 或（更推荐生产）：
    - `gunicorn -k uvicorn.workers.UvicornWorker -w 2 -b 0.0.0.0:$PORT app.main:app`

### 1.4 配置环境变量（必填）

在 Railway 的 Variables 中添加：
- `DATABASE_URL`：Postgres 连接（Railway 通常会提供，若变量名不同请手动映射到 DATABASE_URL）
- `JWT_SECRET`：强随机字符串（必须改掉默认 dev-secret）
- `AI_MODE=deepseek`
- `DEEPSEEK_API_KEY=<你的key>`
- `DEEPSEEK_MODEL=deepseek-chat`（或你要用的）
- `DEEPSEEK_BASE_URL=https://api.deepseek.com`
- `CORS_ORIGINS`：
  - 推荐填 JSON：`["https://<你的vercel域名>","https://www.xxx.com"]`
  - 或逗号分隔：`https://<你的vercel域名>,https://www.xxx.com`

说明：项目已支持 JSON/逗号分隔两种写法（见 `api/app/core/config.py`）。

### 1.5 验证后端

Railway 部署成功后，你会得到一个公网域名，比如：
- `https://xxx.up.railway.app`

验证：
- `GET https://xxx.up.railway.app/health` 返回 `{"status":"ok"}`
- `GET https://xxx.up.railway.app/api/docs` 打开 Swagger

## 2. 前端上线到 Vercel

### 2.1 导入仓库

在 Vercel：
1) New Project → Import Git Repository → 选择 `ighwayh-star/note`
2) Framework 选 Vite（自动识别）

### 2.2 设置环境变量

在 Vercel Project → Settings → Environment Variables：
- `VITE_API_BASE=https://<你的railway后端域名>`
  - 例如 `https://xxx.up.railway.app`

说明：前端已从 `import.meta.env.VITE_API_BASE` 读取 API base（见 `src/api/client.ts`）。

### 2.3 构建与部署

Vercel 默认会：
- Install：`npm install`
- Build：`npm run build`
- Output：`dist`

部署成功后会得到访问地址，例如：
- `https://note-yourname.vercel.app`

## 3. 域名与 HTTPS（可选但推荐）

建议：
- 前端：`https://www.xxx.com` → 指向 Vercel
- 后端：`https://api.xxx.com` → CNAME 到 Railway 域名

把这两个域名加入：
- Vercel Domain
- Railway Domain

并更新后端 CORS：
- `CORS_ORIGINS=["https://www.xxx.com"]`

## 4. AI 对外开放的安全建议（强烈建议）

因为 AI 会产生模型调用成本，且可能被刷，建议至少做：
- 对 `/api/ai/chat`、`/api/ai/confirm` 做频率限制（按 user_id / IP）
- 给新注册用户设置每日额度（如 50 次）
- 后台监控调用量（按天统计 tokens/请求数）

如果你希望我把“限流 + 配额 + 管理接口”也补上，我可以直接在代码里实现一个轻量版本（无需额外依赖）。

