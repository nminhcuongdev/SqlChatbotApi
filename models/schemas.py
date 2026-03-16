from pydantic import BaseModel, Field
from typing import List, Optional


# ── /connection/test ──────────────────────────────────────────────────────────
class ConnectionTestResponse(BaseModel):
    success: bool
    message: str
    tables: List[str] = []


# ── /ingest ───────────────────────────────────────────────────────────────────
class IngestTableConfig(BaseModel):
    table_name: str
    text_columns: List[str] = Field(..., description="Các cột chứa text cần embed")
    id_column: str = Field(default="id")
    where_clause: Optional[str] = None


class IngestRequest(BaseModel):
    tables: List[IngestTableConfig] = Field(..., description="Danh sách bảng cần nạp vào RAG")
    collection_name: str = Field(default="warehouse", description="Tên collection ChromaDB")

    class Config:
        json_schema_extra = {
            "example": {
                "collection_name": "warehouse",
                "tables": [
                    {"table_name": "Products", "text_columns": ["ProductName", "Description"], "id_column": "ProductId"},
                    {"table_name": "Locations", "text_columns": ["LocationName", "Zone"], "id_column": "LocationId"},
                    {"table_name": "DeliveryOrders", "text_columns": ["OrderCode", "Note"], "id_column": "OrderId", "where_clause": "IsActive = 1"},
                ]
            }
        }


class IngestResponse(BaseModel):
    success: bool
    message: str
    chunks_added: int


# ── /chat ─────────────────────────────────────────────────────────────────────
class ConversationMessage(BaseModel):
    role: str = Field(..., description="'user' hoặc 'assistant'")
    content: str


class ChatRequest(BaseModel):
    question: str = Field(..., description="Câu hỏi của người dùng")
    conversation_history: List[ConversationMessage] = Field(
        default=[], description="Lịch sử hội thoại để bot nhớ ngữ cảnh"
    )
    use_rag: bool = Field(default=True, description="Có dùng RAG vector search không")
    collection_name: str = Field(default="warehouse")
    top_k: int = Field(default=5, ge=1, le=20)

    class Config:
        json_schema_extra = {
            "example": {
                "question": "Hiện kho còn bao nhiêu sản phẩm A?",
                "conversation_history": [
                    {"role": "user", "content": "Sản phẩm A là gì?"},
                    {"role": "assistant", "content": "Sản phẩm A là hàng điện tử..."},
                ],
                "use_rag": True,
                "collection_name": "warehouse",
                "top_k": 5,
            }
        }


class ChatResponse(BaseModel):
    answer: str
    sources: List[str] = []
