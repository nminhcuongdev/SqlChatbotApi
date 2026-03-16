# SqlChatbotApi

FastAPI backend for a RAG-powered chatbot that works with Microsoft SQL Server.

This project includes:
- A FastAPI API layer for client requests
- A SQL agent that uses OpenAI to generate and run `SELECT` queries
- A RAG pipeline that ingests data from MSSQL into ChromaDB

## Tech Stack

- Python
- FastAPI
- SQLAlchemy
- `pymssql`
- ChromaDB
- OpenAI
- Docker Compose

## Environment Variables

Create a local `.env` file from [.env.sample](/d:/SqlChatBotAPI/.env.sample) for local development.

Important variables:
- `OPENAI_API_KEY`
- `MSSQL_HOST`
- `MSSQL_PORT`
- `MSSQL_USER`
- `MSSQL_PASSWORD`
- `MSSQL_DATABASE`
- `MSSQL_SQLALCHEMY_DRIVER`
- `MSSQL_WINDOWS_AUTH`
- `CHROMA_PERSIST_DIR`

Docker is configured to use `pymssql` by default, without relying on ODBC Driver 17.

## Run Locally

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.

## Run with Docker

Docker uses a separate environment file: `.env.docker`.

Build the image:

```bash
docker compose build
```

Start the service:

```bash
docker compose up -d
```

If you already have a SQL Server container running on an existing Docker network, make sure [docker-compose.yml](/d:/SqlChatBotAPI/docker-compose.yml) points to the correct external network.

## Main Endpoints

- `GET /health`
- `GET /connection/test`
- `POST /ingest`
- `POST /chat`

## Notes

- The app creates a ChromaDB store in the directory defined by `CHROMA_PERSIST_DIR`
- The SQL agent is intended for read-only database queries
- If the Docker API container does not start, check the container logs and verify SQL Server connectivity
