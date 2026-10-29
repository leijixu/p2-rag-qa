"""P2 RAG Web 演示：FastAPI 后端 + 静态页面。

启动：
    uvicorn app:app --host 0.0.0.0 --port 8000

启动时加载一次文档块和向量矩阵，之后每次提问只 embed query。
"""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import rag
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
LIMIT = 10
WINDOW = 60
MAX_QUESTION_CHARS = 500
GUARDED_PREFIX = "/ask"

_hits: dict[str, deque[float]] = defaultdict(deque)


class AskRequest(BaseModel):
    question: str


class RagIndex:
    def __init__(self) -> None:
        rag.load_env_file()
        dashscope_key = os.environ.get("DASHSCOPE_API_KEY")
        deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
        if not dashscope_key or not deepseek_key:
            raise RuntimeError("缺少 DASHSCOPE_API_KEY / DEEPSEEK_API_KEY，请先配置 .env")

        self.embed_client = rag.OpenAI(api_key=dashscope_key, base_url=rag.EMBED_BASE_URL)
        self.chat_client = rag.OpenAI(api_key=deepseek_key, base_url=rag.CHAT_BASE_URL)

        self.chunks = []
        for name, text in rag.load_documents(rag.DATA_DIR):
            self.chunks.extend(rag.split_into_chunks(name, text))
        if not self.chunks:
            raise RuntimeError("没有切出任何块")

        self.matrix = rag.embed_documents(self.embed_client, self.chunks)


index: RagIndex | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global index
    index = RagIndex()
    yield
    index = None


app = FastAPI(title="P2 RAG Demo", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.middleware("http")
async def limit_and_log(request: Request, call_next):
    started = time.perf_counter()
    ip = request.client.host if request.client else "unknown"

    if request.url.path.startswith(GUARDED_PREFIX):
        now = time.monotonic()
        hits = _hits[ip]
        while hits and now - hits[0] > WINDOW:
            hits.popleft()
        if len(hits) >= LIMIT:
            wait = int(WINDOW - (now - hits[0])) + 1
            response = JSONResponse(
                status_code=429,
                content={"detail": f"请求过于频繁，请 {wait} 秒后再试"},
                headers={"Retry-After": str(wait)},
            )
            print(f"{ip} {request.method} {request.url.path} 429 {time.perf_counter() - started:.2f}s", flush=True)
            return response
        hits.append(now)

    response = await call_next(request)
    print(
        f"{ip} {request.method} {request.url.path} {response.status_code} "
        f"{time.perf_counter() - started:.2f}s",
        flush=True,
    )
    return response


@app.get("/")
def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "chunks": len(index.chunks) if index else 0}


@app.post("/ask")
def ask(req: AskRequest) -> dict[str, Any]:
    if index is None:
        raise HTTPException(status_code=503, detail="索引还没准备好")

    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")
    if len(question) > MAX_QUESTION_CHARS:
        raise HTTPException(
            status_code=400,
            detail=f"问题太长，最多 {MAX_QUESTION_CHARS} 字",
        )

    try:
        query_vec = rag.embed_texts(index.embed_client, [question])[0]
        hits = rag.hybrid_top_k(query_vec, index.matrix, question, index.chunks)
        selected = [index.chunks[i] for i, _ in hits]
        prompt = rag.build_prompt(question, selected)
        answer = rag.generate(index.chat_client, prompt)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"RAG 调用失败: {exc}") from exc

    citations = [
        {
            "label": index.chunks[i].label(),
            "heading": index.chunks[i].heading,
            "score": round(float(score), 4),
        }
        for i, score in hits
    ]
    return {"answer": answer, "citations": citations}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="127.0.0.1", port=8000)
