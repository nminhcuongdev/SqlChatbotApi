"""
RAG Pipeline — ChromaDB 1.4.x + OpenAI Embeddings.
ChromaDB 1.4.x đã có sẵn trong môi trường, API có thay đổi so với 0.x.
"""

from typing import List, Dict, Optional
from urllib.parse import unquote_plus, urlparse, parse_qs
from pathlib import Path

import chromadb
from openai import OpenAI
import pyodbc

from config import settings
from core.db_connection import DB_URI

EMBEDDING_DIM = 1536   # text-embedding-3-small


class RAGPipeline:

    def __init__(self):
        self.client: Optional[chromadb.PersistentClient] = None
        self._openai = OpenAI(api_key=settings.OPENAI_API_KEY)

    def initialize(self):
        Path(settings.CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)
        # ChromaDB 1.4.x: PersistentClient nhận path trực tiếp
        self.client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
        print(f"📦 ChromaDB 1.4 khởi tạo tại: {settings.CHROMA_PERSIST_DIR}")

    # ── Embedding ─────────────────────────────────────────────────────────────

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        cleaned = [t.replace("\n", " ").strip() for t in texts]
        all_embeddings = []
        for i in range(0, len(cleaned), 100):
            resp = self._openai.embeddings.create(
                input=cleaned[i: i + 100],
                model=settings.OPENAI_EMBEDDING_MODEL,
            )
            all_embeddings.extend([item.embedding for item in resp.data])
        return all_embeddings

    def _embed_query(self, query: str) -> List[float]:
        resp = self._openai.embeddings.create(
            input=[query.replace("\n", " ").strip()],
            model=settings.OPENAI_EMBEDDING_MODEL,
        )
        return resp.data[0].embedding

    # ── Collection ────────────────────────────────────────────────────────────

    def _get_collection(self, name: str):
        # ChromaDB 1.4.x: get_or_create_collection vẫn dùng được
        return self.client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

    # ── Ingest ────────────────────────────────────────────────────────────────

    async def ingest_from_mssql(
        self,
        tables: List,
        collection: str = "warehouse",
    ) -> int:
        col = self._get_collection(collection)

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        total_added = 0

        for table_cfg in tables:
            table_name = table_cfg.table_name
            text_cols  = table_cfg.text_columns
            id_col     = table_cfg.id_column
            where      = table_cfg.where_clause or ""

            rows = self._fetch_rows(table_name, text_cols, id_col, where)

            chunks, ids, metadatas = [], [], []
            for row in rows:
                text = row["_text"].strip()
                if not text:
                    continue
                parts = splitter.split_text(text)
                for i, part in enumerate(parts):
                    chunks.append(part)
                    ids.append(f"{table_name}_{row['_id']}_{i}")
                    metadatas.append({
                        "source_table": table_name,
                        "source_id":    str(row["_id"]),
                        "chunk_index":  str(i),
                    })

            if not chunks:
                continue

            embeddings = self._embed_texts(chunks)

            # Upsert batch 500
            for i in range(0, len(chunks), 500):
                col.upsert(
                    ids=ids[i: i + 500],
                    embeddings=embeddings[i: i + 500],
                    documents=chunks[i: i + 500],
                    metadatas=metadatas[i: i + 500],
                )
                total_added += len(chunks[i: i + 500])

            print(f"  ✅ [{table_name}] {len(chunks)} chunks")

        return total_added

    def _fetch_rows(self, table: str, text_cols: List[str], id_col: str, where: str) -> List[Dict]:
        conn_str = self._uri_to_odbc(DB_URI)
        rows = []
        conn = pyodbc.connect(conn_str)
        try:
            cursor = conn.cursor()
            cols_sql = ", ".join(f"[{c}]" for c in [id_col] + text_cols)
            query = f"SELECT {cols_sql} FROM [{table}]"
            if where:
                query += f" WHERE {where}"
            cursor.execute(query)
            col_names = [d[0] for d in cursor.description]
            for row in cursor.fetchall():
                record = dict(zip(col_names, row))
                text_parts = [
                    f"{c}: {str(record[c]).strip()}"
                    for c in text_cols
                    if record.get(c) and str(record[c]).strip()
                ]
                rows.append({"_id": record.get(id_col, ""), "_text": "\n".join(text_parts)})
        finally:
            conn.close()
        return rows

    @staticmethod
    def _uri_to_odbc(uri: str) -> str:
        parsed = urlparse(uri)
        qs       = parse_qs(parsed.query)
        driver   = qs.get("driver", ["ODBC Driver 17 for SQL Server"])[0].replace("+", " ")
        server   = parsed.hostname or "localhost"
        if parsed.port:
            server = f"{server},{parsed.port}"
        database = parsed.path.lstrip("/")
        if qs.get("trusted_connection"):
            return (
                f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};"
                "Trusted_Connection=yes;TrustServerCertificate=yes;"
            )
        user     = unquote_plus(parsed.username or "")
        password = unquote_plus(parsed.password or "")
        return (
            f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};"
            f"UID={user};PWD={password};TrustServerCertificate=yes;"
        )

    # ── Query ─────────────────────────────────────────────────────────────────

    def query(self, question: str, collection: str = "warehouse", top_k: int = 5) -> List[Dict]:
        col   = self._get_collection(collection)
        count = col.count()
        if count == 0:
            return []

        q_emb   = self._embed_query(question)
        results = col.query(
            query_embeddings=[q_emb],
            n_results=min(top_k, count),
            include=["documents", "metadatas", "distances"],
        )

        return [
            {
                "text":     text,
                "metadata": meta,
                "score":    round(1 - dist, 4),
            }
            for text, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ]

    def delete_collection(self, collection: str):
        self.client.delete_collection(collection)