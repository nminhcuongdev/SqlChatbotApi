"""
SQL Agent Manager — đọc cấu hình từ settings (.env).
Không nhận openai_api_key hay db_uri từ request.
"""

from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_openai import ChatOpenAI
from config import settings
from core.db_connection import DB_URI


CUSTOM_PREFIX = """
You are an expert assistant for querying a Microsoft SQL Server database.

GOAL
- Answer the user's question by generating SQL Server SELECT queries and using the database tool to fetch results.
- If conversation history is provided, use it to understand context and follow-up questions.

DATABASE OVERVIEW
- Stocks Table: List of items currently in stock
- StockIns Table: History of products, goods received into the warehouse
- StockOuts Table: History of products, goods out of the warehouse
- Products Table: Detailed product master information for reference
- Locations Table: Master information of warehouse locations for reference
- Users Table: System user information
- DeliveryOrders Table: Information about delivery orders prepared for warehouse receiving

STRICT RULES (SECURITY)
- READ-ONLY: You must use SELECT statements only.
- NEVER use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, MERGE, EXEC, TRUNCATE.
- Do not call any procedure.
- Do not guess table/column names. Use only what you discover from the database schema/tools.

PERFORMANCE RULES
- Always limit row counts with TOP (50) unless the user explicitly asks for more.
- Prefer filtering by date range or identifiers when possible.
- Avoid SELECT * unless user explicitly requests all columns.

MULTI-TURN CONVERSATION
- If the question contains "LỊCH SỬ HỘI THOẠI:", use it to understand context.
- Pronouns like "nó", "cái đó", "sản phẩm đó" refer to entities mentioned in history.

IF AMBIGUOUS
- Ask ONE short clarification question before running a query.

FINAL ANSWER FORMAT
- Provide a short explanation in Vietnamese.
- Include the SQL you used in a SQL code block.
- If RAG context is provided (starts with "THÔNG TIN NGỮ CẢNH"), use it for business logic.
"""


class SQLAgentManager:
    """
    Singleton SQL Agent — khởi tạo 1 lần khi server start,
    tái sử dụng cho mọi request.
    """

    def __init__(self):
        self._agent = None

    def get_agent(self):
        if self._agent is None:
            self._agent = self._create_agent()
        return self._agent

    def _create_agent(self):
        # ✅ llm và toolkit khởi tạo cùng scope — không có biến tự do
        llm = ChatOpenAI(
            model=settings.OPENAI_CHAT_MODEL,
            temperature=0,
            api_key=settings.OPENAI_API_KEY,
        )
        db = SQLDatabase.from_uri(DB_URI)
        toolkit = SQLDatabaseToolkit(db=db, llm=llm)
        return create_sql_agent(
            llm=llm,
            toolkit=toolkit,
            verbose=True,
            agent_type="zero-shot-react-description",
            agent_kwargs={"prefix": CUSTOM_PREFIX},
        )

    def invalidate(self):
        """Force tạo lại agent (dùng khi cần reload config)."""
        self._agent = None
