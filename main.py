import logging
import os
from pathlib import Path
from typing import Any

import pymysql
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from pydantic import BaseModel, Field


# =========================
# 基础配置
# =========================

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger(__name__)


def get_required_env(name: str) -> str:
    """读取必填环境变量。"""
    value = os.getenv(name)

    if not value:
        raise RuntimeError(
            f"缺少环境变量：{name}，请检查项目根目录下的 .env 文件"
        )

    return value


DEEPSEEK_API_KEY = get_required_env("DEEPSEEK_API_KEY")

MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = get_required_env("MYSQL_PASSWORD")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "ai_travel")


# =========================
# FastAPI 应用
# =========================

app = FastAPI(
    title="AI Travel 智能旅行规划助手",
    description="基于 FastAPI、DeepSeek 和 MySQL 的 AI 旅游攻略项目",
    version="1.0.0"
)

FRONTEND_DIR = BASE_DIR / "frontend"

if FRONTEND_DIR.exists():
    app.mount(
        "/frontend",
        StaticFiles(directory=str(FRONTEND_DIR), html=True),
        name="frontend"
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# DeepSeek 客户端
# =========================

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)


# =========================
# 请求数据模型
# =========================

class TravelRequest(BaseModel):
    destination: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="旅游目的地"
    )
    days: int = Field(
        ...,
        ge=1,
        le=30,
        description="旅游天数"
    )
    budget: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="旅游预算"
    )
    preference: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="旅游偏好"
    )


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="用户问题"
    )
    travel_plan: str = Field(
        default="",
        max_length=30000,
        description="当前旅游攻略"
    )
    destination: str = Field(
        default="",
        max_length=50,
        description="旅游目的地"
    )
    days: int = Field(
        default=1,
        ge=1,
        le=30,
        description="旅行天数"
    )
    budget: str = Field(
        default="",
        max_length=50,
        description="旅行预算"
    )
    preference: str = Field(
        default="",
        max_length=200,
        description="旅行偏好"
    )


# =========================
# 数据库工具
# =========================

def get_db_connection():
    """创建 MySQL 数据库连接。"""
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )


def normalize_text(value: str) -> str:
    """清理用户输入两端的空白字符。"""
    return value.strip()


# =========================
# 基础接口
# =========================

@app.get("/")
def home():
    return {
        "code": 0,
        "message": "AI旅游攻略后端运行成功"
    }


@app.get("/api/health")
def health_check():
    """检查应用和数据库是否正常。"""
    connection = None

    try:
        connection = get_db_connection()

        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        return {
            "code": 0,
            "message": "服务正常",
            "data": {
                "database": "connected"
            }
        }

    except Exception:
        logger.exception("健康检查失败")

        return {
            "code": 1,
            "message": "数据库连接失败",
            "data": {
                "database": "disconnected"
            }
        }

    finally:
        if connection:
            connection.close()


# =========================
# 生成旅游攻略
# =========================

@app.post("/api/travel")
def generate_travel_plan(request: TravelRequest):
    destination = normalize_text(request.destination)
    budget = normalize_text(request.budget)
    preference = normalize_text(request.preference)

    try:
        prompt = f"""
你是一名专业、实用的旅游规划师。

请根据以下信息，生成一份详细、清晰、可执行的旅游攻略：

旅游目的地：{destination}
旅游天数：{request.days}天
旅游预算：{budget}
旅游偏好：{preference}

请按照以下结构输出：

# 一、行程总览

# 二、每天的详细行程安排

# 三、推荐景点及推荐理由

# 四、当地特色美食

# 五、交通建议

# 六、住宿建议

# 七、预算分配建议

# 八、旅游注意事项

要求：
1. 内容真实、合理、易于执行；
2. 行程安排不要过于紧凑；
3. 语言清晰，适合普通游客阅读；
4. 尽量给出时间段和顺序建议；
5. 涉及价格、营业时间和交通时，提醒用户以官方最新信息为准；
6. 不要输出与旅游无关的内容。
"""

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

        travel_plan = response.choices[0].message.content or ""

        if not travel_plan.strip():
            raise RuntimeError("DeepSeek 返回了空攻略")

        connection = None

        try:
            connection = get_db_connection()

            with connection.cursor() as cursor:
                sql = """
                    INSERT INTO travel_records
                    (destination, days, budget, preference, travel_plan)
                    VALUES (%s, %s, %s, %s, %s)
                """

                cursor.execute(
                    sql,
                    (
                        destination,
                        request.days,
                        budget,
                        preference,
                        travel_plan
                    )
                )

                record_id = cursor.lastrowid

            connection.commit()

        except Exception:
            if connection:
                connection.rollback()

            raise

        finally:
            if connection:
                connection.close()

        return {
            "code": 0,
            "message": "旅游攻略生成成功",
            "data": {
                "id": record_id,
                "destination": destination,
                "days": request.days,
                "budget": budget,
                "preference": preference,
                "travel_plan": travel_plan
            }
        }

    except Exception:
        logger.exception("旅游攻略生成失败")

        return {
            "code": 1,
            "message": "旅游攻略生成失败，请检查 DeepSeek 配置或数据库连接"
        }


# =========================
# 历史攻略接口
# =========================

@app.get("/api/travel-records")
def get_travel_records(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="返回记录数量"
    )
):
    """按创建时间倒序查询历史攻略列表。"""
    connection = None

    try:
        connection = get_db_connection()

        with connection.cursor() as cursor:
            sql = """
                SELECT
                    id,
                    destination,
                    days,
                    budget,
                    preference,
                    created_at
                FROM travel_records
                ORDER BY created_at DESC, id DESC
                LIMIT %s
            """

            cursor.execute(sql, (limit,))
            records = cursor.fetchall()

        return {
            "code": 0,
            "message": "历史攻略获取成功",
            "data": records
        }

    except Exception:
        logger.exception("获取历史攻略失败")

        return {
            "code": 1,
            "message": "历史攻略获取失败，请稍后重试"
        }

    finally:
        if connection:
            connection.close()


@app.get("/api/travel-records/{record_id}")
def get_travel_record(record_id: int):
    """查询单条历史攻略详情。"""
    connection = None

    try:
        connection = get_db_connection()

        with connection.cursor() as cursor:
            sql = """
                SELECT
                    id,
                    destination,
                    days,
                    budget,
                    preference,
                    travel_plan,
                    created_at
                FROM travel_records
                WHERE id = %s
            """

            cursor.execute(sql, (record_id,))
            record = cursor.fetchone()

        if not record:
            raise HTTPException(
                status_code=404,
                detail="没有找到对应的旅游攻略"
            )

        return {
            "code": 0,
            "message": "攻略详情获取成功",
            "data": record
        }

    except HTTPException:
        raise

    except Exception:
        logger.exception("获取攻略详情失败")

        return {
            "code": 1,
            "message": "攻略详情获取失败，请稍后重试"
        }

    finally:
        if connection:
            connection.close()


@app.delete("/api/travel-records/{record_id}")
def delete_travel_record(record_id: int):
    """删除单条历史攻略。"""
    connection = None

    try:
        connection = get_db_connection()

        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM travel_records WHERE id = %s",
                (record_id,)
            )

            deleted_count = cursor.rowcount

        if deleted_count == 0:
            connection.rollback()

            raise HTTPException(
                status_code=404,
                detail="没有找到对应的旅游攻略"
            )

        connection.commit()

        return {
            "code": 0,
            "message": "攻略删除成功",
            "data": {
                "id": record_id
            }
        }

    except HTTPException:
        raise

    except Exception:
        if connection:
            connection.rollback()

        logger.exception("删除攻略失败")

        return {
            "code": 1,
            "message": "攻略删除失败，请稍后重试"
        }

    finally:
        if connection:
            connection.close()


# =========================
# 旅行应急助手聊天
# =========================

@app.post("/api/chat")
def travel_chat(request: ChatRequest):
    message = normalize_text(request.message)

    if not message:
        return {
            "code": 1,
            "message": "请输入你的问题"
        }

    try:
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
{message}

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

        answer = response.choices[0].message.content or ""

        if not answer.strip():
            raise RuntimeError("DeepSeek 返回了空回复")

        return {
            "code": 0,
            "message": "回复成功",
            "data": {
                "answer": answer
            }
        }

    except Exception:
        logger.exception("聊天服务调用失败")

        return {
            "code": 1,
            "message": "聊天服务调用失败，请稍后重试"
        }
