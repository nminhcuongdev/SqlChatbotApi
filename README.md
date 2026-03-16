# SqlChatbotApi

FastAPI backend cho chatbot RAG làm việc với Microsoft SQL Server.

Project này gồm 3 phần chính:
- FastAPI API để nhận request từ client
- SQL agent dùng OpenAI để sinh và chạy truy vấn `SELECT`
- RAG pipeline để ingest dữ liệu từ MSSQL vào ChromaDB

## Tech Stack

- Python
- FastAPI
- SQLAlchemy
- `pymssql`
- ChromaDB
- OpenAI
- Docker Compose

## Environment

Tạo file `.env` từ [.env.sample](/d:/SqlChatBotAPI/.env.sample) khi chạy local.

Các biến quan trọng:
- `OPENAI_API_KEY`
- `MSSQL_HOST`
- `MSSQL_PORT`
- `MSSQL_USER`
- `MSSQL_PASSWORD`
- `MSSQL_DATABASE`
- `MSSQL_SQLALCHEMY_DRIVER`
- `MSSQL_WINDOWS_AUTH`
- `CHROMA_PERSIST_DIR`

Mặc định Docker đang dùng `pymssql`, không dùng ODBC Driver 17.

## Run Local

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

API chạy tại `http://localhost:8000`.

## Run Docker

Project hiện dùng file env riêng cho Docker là `.env.docker`.

Build image:

```bash
docker compose build
```

Start service:

```bash
docker compose up -d
```

Nếu bạn đã có container MSSQL chạy ở network khác, cần chắc rằng network trong [docker-compose.yml](/d:/SqlChatBotAPI/docker-compose.yml) trỏ đúng network external đang chứa SQL Server.

## Main Endpoints

- `GET /health`
- `GET /connection/test`
- `POST /ingest`
- `POST /chat`

## Notes

- App khởi động sẽ tạo ChromaDB tại thư mục được khai báo trong `CHROMA_PERSIST_DIR`
- SQL agent chỉ nên dùng cho truy vấn đọc dữ liệu
- Nếu Docker API không lên được, kiểm tra lại log container và khả năng kết nối tới SQL Server container
