# AI Travel 智能旅行规划助手

一个基于 FastAPI、DeepSeek API 和 MySQL 开发的 AI 旅行攻略生成项目。用户可以输入目的地、旅行天数、预算和偏好，系统会自动生成个性化旅行攻略，并将结果保存到 MySQL 数据库。

## 主要功能

- 根据目的地、天数、预算和旅行偏好生成攻略
- 调用 DeepSeek API 生成个性化旅行内容
- 将生成的旅行攻略保存到 MySQL
- 提供旅行应急助手聊天功能
- 提供可视化前端操作页面
- 提供 FastAPI Swagger 接口文档
- 支持 Docker 容器化部署

## 技术栈

- Python
- FastAPI
- Uvicorn
- DeepSeek API
- MySQL
- PyMySQL
- HTML / CSS / JavaScript
- Docker

## 项目结构

```text
ai_travel/
├── frontend/
│   ├── index.html          # 前端页面                 
├── .dockerignore           # Docker 忽略配置
├── .env.example            # 环境变量示例
├── .gitignore              # Git 忽略配置
├── Dockerfile              # Docker 镜像配置
├── main.py                 # FastAPI 后端入口
├── requirements.txt        # Python 依赖
└── README.md               # 项目说明
```

## 本地运行

### 1. 克隆项目

```bash
git clone https://github.com/star964/ai_travel.git
cd ai_travel
```

### 2. 创建并激活虚拟环境

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. 安装依赖

```powershell
pip install -r requirements.txt
```

### 4. 配置环境变量

根据 `.env.example`，在项目根目录创建 `.env` 文件：

```env
DEEPSEEK_API_KEY=your_deepseek_api_key

DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=ai_travel
```

请勿将包含真实 API Key 和数据库密码的 `.env` 上传到 GitHub。

### 5. 准备 MySQL

请确保 MySQL 服务已经启动，并创建项目所需的数据库及数据表。

### 6. 启动项目

```powershell
python -m uvicorn main:app --reload
```

### 7. 访问项目

前端页面：

```text
http://127.0.0.1:8000/frontend/
```

FastAPI 接口文档：

```text
http://127.0.0.1:8000/docs
```

## 主要接口

```text
POST /api/travel
POST /api/chat
```

- `/api/travel`：生成个性化旅行攻略并保存到 MySQL
- `/api/chat`：调用旅行应急助手进行对话

## 安全说明

- `.env` 已加入 `.gitignore`
- 请勿在代码中直接填写 API Key 或数据库密码
- `.env.example` 中只能填写示例值
- 如果密钥意外公开，请立即撤销并重新创建

## 项目仓库

https://github.com/star964/ai_travel
