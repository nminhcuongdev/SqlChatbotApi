"""
RAG SQL Server — FastAPI backend
Tất cả cấu hình (MSSQL + OpenAI) đọc từ .env.
Kotlin chỉ cần gửi câu hỏi, không cần truyền credentials.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from models.schemas import (
    ChatRequest, ChatResponse,
    IngestRequest, IngestResponse,
    ConnectionTestResponse,
)
from core.db_connection import test_connection
from core.sql_agent import SQLAgentManager
from core.rag_pipeline import RAGPipeline

agent_manager = SQLAgentManager()
rag_pipeline = RAGPipeline()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("RAG SQL Server khởi động...")
    rag_pipeline.initialize()
    agent_manager.get_agent()
    print("Sẵn sàng nhận request")
    yield
    print("Server tắt")


app = FastAPI(
    title="RAG SQL Server API",
    description="Chatbot RAG kết nối MSSQL",
    version="2.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Kiểm tra server còn sống — Kotlin ping trước khi dùng."""
    return {"status": "ok", "version": "2.1.0"}


@app.get("/connection/test", response_model=ConnectionTestResponse)
async def test_db_connection():
    """
    Test kết nối MSSQL từ .env — không cần body.
    Trả về danh sách bảng nếu thành công.
    """
    try:
        tables = test_connection()
        return ConnectionTestResponse(success=True, message="Kết nối thành công", tables=tables)
    except Exception as e:
        return ConnectionTestResponse(success=False, message=str(e), tables=[])


@app.post("/ingest", response_model=IngestResponse)
async def ingest(req: IngestRequest):
    """
    Nạp dữ liệu từ MSSQL vào ChromaDB.
    Body chỉ cần khai báo bảng nào, cột nào cần embed.
    """
    try:
        added = await rag_pipeline.ingest_from_mssql(
            tables=req.tables,
            collection=req.collection_name,
        )
        return IngestResponse(
            success=True,
            message=f"Đã nạp {added} chunks vào collection '{req.collection_name}'",
            chunks_added=added,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Endpoint chính — Kotlin gửi câu hỏi, nhận câu trả lời.

    Flow:
      1. RAG  : tìm chunks liên quan từ ChromaDB (ngữ cảnh nghiệp vụ)
      2. History : ghép lịch sử hội thoại vào prompt
      3. SQL Agent : sinh SQL → chạy → GPT tổng hợp câu trả lời
    """
    try:
        agent = agent_manager.get_agent()

        # ── 1. RAG context ────────────────────────────────────────────────────
        rag_context = ""
        if req.use_rag and req.collection_name:
            rag_docs = rag_pipeline.query(
                question=req.question,
                collection=req.collection_name,
                top_k=req.top_k,
            )
            if rag_docs:
                parts = [f"- {d['text']}" for d in rag_docs]
                rag_context = "THÔNG TIN NGỮ CẢNH TỪ CƠ SỞ DỮ LIỆU:\n" + "\n".join(parts) + "\n\n"

        # ── 2. Conversation history ───────────────────────────────────────────
        history_text = ""
        if req.conversation_history:
            lines = [
                f"{'Người dùng' if m.role == 'user' else 'Trợ lý'}: {m.content}"
                for m in req.conversation_history[-10:]   # tối đa 10 lượt
            ]
            history_text = "LỊCH SỬ HỘI THOẠI:\n" + "\n".join(lines) + "\n\n"

        # ── 3. Gọi SQL Agent ──────────────────────────────────────────────────
        full_prompt = f"{history_text}{rag_context}CÂU HỎI HIỆN TẠI: {req.question}"
        answer = agent.run(full_prompt)

        return ChatResponse(
            answer=answer,
            sources=rag_context.splitlines() if rag_context else [],
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

