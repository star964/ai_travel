import os
from pathlib import Path

import pymysql
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from pydantic import BaseModel, Field


# 获取项目所在目录，并读取同一目录下的 .env 文件
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def get_required_env(name: str) -> str:
    """读取必填环境变量，未配置时立即给出明确错误。"""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"缺少环境变量：{name}，请检查 .env 文件")
    return value


# 从 .env 读取 DeepSeek 和 MySQL 配置
DEEPSEEK_API_KEY = get_required_env("DEEPSEEK_API_KEY")

MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = get_required_env("MYSQL_PASSWORD")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "ai_travel")



app = FastAPI(
    title="AI旅游攻略生成系统",
    description="基于 FastAPI、DeepSeek 和 MySQL 的 AI 旅游攻略项目",
    version="1.0.0"
)

FRONTEND_DIR = BASE_DIR / "frontend"


app.mount(
    "/frontend",
    StaticFiles(directory=str(FRONTEND_DIR), html=True),
    name="frontend"
)
# 允许前1端页面访问后端接口
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# 3. 创建 DeepSeek 客户端
# =========================

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

# =========================
# 4. 定义请求数据格式
# =========================

class TravelRequest(BaseModel):
    destination: str = Field(..., min_length=1, max_length=50, description="旅游目的地")
    days: int = Field(..., ge=1, le=30, description="旅游天数")
    budget: str = Field(..., min_length=1, max_length=50, description="旅游预算")
    preference: str = Field(..., min_length=1, max_length=200, description="旅游偏好")

class ChatRequest(BaseModel):
    message: str
    travel_plan: str = ""
    destination: str = ""
    days: int = 1
    budget: str = ""
    preference: str = ""






def get_db_connection():
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )


# =========================
# 6. 测试接口
# =========================

@app.get("/")
def home():
    return {
        "code": 0,
        "message": "AI旅游攻略后端运行成功"
    }

# =========================
# 7. AI旅游攻略接口
# =========================

@app.post("/api/travel")
def generate_travel_plan(request: TravelRequest):
    try:
        prompt = f"""
你是一名专业、实用的旅游规划师。

请根据以下信息，生成一份详细的旅游攻略：

旅游目的地：{request.destination}
旅游天数：{request.days}天
旅游预算：{request.budget}
旅游偏好：{request.preference}

请按照以下结构输出：

一、行程总览
二、每天的详细行程安排
三、推荐景点及推荐理由
四、当地特色美食
五、交通建议
六、住宿建议
七、预算分配建议
八、旅游注意事项

要求：
1. 内容真实、合理、易于执行；
2. 行程安排不要过于紧凑；
3. 语言清晰，适合普通游客阅读；
4. 不要输出与旅游无关的内容。
"""

        # 调用 DeepSeek
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": "你是一名专业旅游规划师。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7
        )

        travel_plan = response.choices[0].message.content

        # 保存到 MySQL
        connection = get_db_connection()

        try:
            with connection.cursor() as cursor:
                sql = """
                    INSERT INTO travel_records
                    (destination, days, budget, preference, travel_plan)
                    VALUES (%s, %s, %s, %s, %s)
                """

                cursor.execute(
                    sql,
                    (
                        request.destination,
                        request.days,
                        request.budget,
                        request.preference,
                        travel_plan
                    )
                )

            connection.commit()

        finally:
            connection.close()

        return {
            "code": 0,
            "message": "旅游攻略生成成功",
            "data": {
                "destination": request.destination,
                "days": request.days,
                "budget": request.budget,
                "preference": request.preference,
                "travel_plan": travel_plan
            }
        }

    except Exception as error:
        return {
            "code": 1,
            "message": "旅游攻略生成失败",
            "error": str(error)
        }


@app.post("/api/chat")
def travel_chat(request: ChatRequest):
    try:
        if not request.message.strip():
            return {
                "code": 1,
                "message": "请输入你的问题"
            }

        system_prompt = """
你是一名专业、可靠、细心的旅行应急助手。

你的任务是帮助用户处理旅行途中发生的突发情况，例如：
1. 景点临时关闭；
2. 天气变化；
3. 航班、高铁或地铁延误；
4. 身体不适；
5. 行程时间不够；
6. 预算超支；
7. 迷路或交通路线变化；
8. 餐厅没有营业；
9. 用户临时改变旅行偏好。

请遵循以下要求：
- 优先保证用户安全；
- 回答要具体、可执行；
- 如果是行程调整，请给出新的时间安排；
- 涉及天气、交通、营业时间等实时信息时，要提醒用户以官方信息为准；
- 如果涉及医疗、危险或法律问题，要建议联系当地官方机构或专业人员；
- 使用中文回答；
- 使用清晰的小标题和列表。
"""

        user_prompt = f"""
用户当前的旅行信息：

目的地：{request.destination}
旅行天数：{request.days}天
预算：{request.budget}
旅行偏好：{request.preference}

当前旅游攻略：
{request.travel_plan}

用户现在遇到的问题：
{request.message}

请根据以上信息，给出具体的解决方案。
如果原来的行程需要调整，请列出调整后的行程安排。
"""

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            temperature=0.7,
            max_tokens=2000
        )

        answer = response.choices[0].message.content

        return {
            "code": 0,
            "message": "回复成功",
            "data": {
                "answer": answer
            }
        }

    except Exception as e:
        return {
            "code": 1,
            "message": "聊天服务调用失败",
            "error": str(e)
        }