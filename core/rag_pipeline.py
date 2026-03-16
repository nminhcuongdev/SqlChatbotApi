from pathlib import Path
from typing import Dict, List, Optional

import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import OpenAI
from sqlalchemy import text

from config import settings
from core.db_connection import create_db_engine

EMBEDDING_DIM = 1536


class RAGPipeline:
    def __init__(self):
        self.client: Optional[chromadb.PersistentClient] = None
        self._openai = OpenAI(api_key=settings.OPENAI_API_KEY)

    def initialize(self):
        Path(settings.CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
        print(f"ChromaDB initialized at: {settings.CHROMA_PERSIST_DIR}")

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        cleaned = [t.replace("\n", " ").strip() for t in texts]
        all_embeddings = []
        for i in range(0, len(cleaned), 100):
            resp = self._openai.embeddings.create(
                input=cleaned[i : i + 100],
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

    def _get_collection(self, name: str):
        return self.client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

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
            text_cols = table_cfg.text_columns
            id_col = table_cfg.id_column
            where = table_cfg.where_clause or ""

            rows = self._fetch_rows(table_name, text_cols, id_col, where)

            chunks, ids, metadatas = [], [], []
            for row in rows:
                text_value = row["_text"].strip()
                if not text_value:
                    continue

                parts = splitter.split_text(text_value)
                for i, part in enumerate(parts):
                    chunks.append(part)
                    ids.append(f"{table_name}_{row['_id']}_{i}")
                    metadatas.append(
                        {
                            "source_table": table_name,
                            "source_id": str(row["_id"]),
                            "chunk_index": str(i),
                        }
                    )

            if not chunks:
                continue

            embeddings = self._embed_texts(chunks)

            for i in range(0, len(chunks), 500):
                col.upsert(
                    ids=ids[i : i + 500],
                    embeddings=embeddings[i : i + 500],
                    documents=chunks[i : i + 500],
                    metadatas=metadatas[i : i + 500],
                )
                total_added += len(chunks[i : i + 500])

            print(f"[{table_name}] {len(chunks)} chunks")

        return total_added

    def _fetch_rows(self, table: str, text_cols: List[str], id_col: str, where: str) -> List[Dict]:
        engine = create_db_engine()
        rows = []
        cols_sql = ", ".join(f"[{c}]" for c in [id_col] + text_cols)
        query = f"SELECT {cols_sql} FROM [{table}]"
        if where:
            query += f" WHERE {where}"

        try:
            with engine.connect() as conn:
                result = conn.execute(text(query))
                for row in result.mappings():
                    record = {}
                    for key, value in row.items():
                        if hasattr(value, "item"):
                            value = value.item()
                        record[key] = value

                    text_parts = [
                        f"{column}: {str(record[column]).strip()}"
                        for column in text_cols
                        if record.get(column) and str(record[column]).strip()
                    ]
                    rows.append(
                        {
                            "_id": record.get(id_col, ""),
                            "_text": "\n".join(text_parts),
                        }
                    )
        finally:
            engine.dispose()

        return rows

    def query(self, question: str, collection: str = "warehouse", top_k: int = 5) -> List[Dict]:
        col = self._get_collection(collection)
        count = col.count()
        if count == 0:
            return []

        q_emb = self._embed_query(question)
        results = col.query(
            query_embeddings=[q_emb],
            n_results=min(top_k, count),
            include=["documents", "metadatas", "distances"],
        )

        return [
            {
                "text": text_value,
                "metadata": metadata,
                "score": round(1 - distance, 4),
            }
            for text_value, metadata, distance in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ]

    def delete_collection(self, collection: str):
        self.client.delete_collection(collection)
