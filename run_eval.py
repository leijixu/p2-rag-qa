"""跑一遍 EVAL.md 里的所有问题，把结果写到 EVAL_RUN.md。

用法：
    python run_eval.py

需要环境变量（或仓库根目录的 .env 文件）：
    DASHSCOPE_API_KEY
    DEEPSEEK_API_KEY

向量只算一次，所有问题复用同一份矩阵，避免每个问题重复 embed 全部块。
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from rag import (
    CHAT_BASE_URL,
    DATA_DIR,
    EMBED_BASE_URL,
    OpenAI,
    build_prompt,
    embed_texts,
    embedding_text,
    generate,
    hybrid_top_k,
    load_documents,
    split_into_chunks,
)

ROOT = Path(__file__).resolve().parent
EVAL_PATH = ROOT / "EVAL.md"
OUT_PATH = ROOT / "EVAL_RUN.md"


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def load_questions(path: Path) -> list[tuple[str, str]]:
    questions: list[tuple[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 4 or not cells[0].isdigit():
            continue
        questions.append((cells[0], cells[1]))
    return questions


def main() -> None:
    env = load_env(ROOT / ".env")
    dashscope_key = os.environ.get("DASHSCOPE_API_KEY") or env.get("DASHSCOPE_API_KEY")
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY") or env.get("DEEPSEEK_API_KEY")
    if not dashscope_key or not deepseek_key:
        sys.exit(
            "缺少 key：请在 G:\\codex\\rag-qa\\.env 写入 "
            "DASHSCOPE_API_KEY 和 DEEPSEEK_API_KEY"
        )

    embed_client = OpenAI(api_key=dashscope_key, base_url=EMBED_BASE_URL)
    chat_client = OpenAI(api_key=deepseek_key, base_url=CHAT_BASE_URL)

    chunks = []
    for name, text in load_documents(DATA_DIR):
        chunks.extend(split_into_chunks(name, text))

    print(f"共 {len(chunks)} 个块，先算一次向量矩阵……")
    matrix = embed_texts(embed_client, [embedding_text(c) for c in chunks])

    questions = load_questions(EVAL_PATH)
    print(f"共 {len(questions)} 道题")

    lines = ["# EVAL 跑分结果", "", f"块数：{len(chunks)}", ""]
    for number, question in questions:
        started = time.time()
        query_vec = embed_texts(embed_client, [question])[0]
        hits = hybrid_top_k(query_vec, matrix, question, chunks)
        selected = [chunks[i] for i, _ in hits]
        prompt = build_prompt(question, selected)
        reply = generate(chat_client, prompt)
        elapsed = time.time() - started

        print(f"\n== {number}. {question}")
        print(reply.strip())

        lines.append(f"## {number}. {question}")
        lines.append("")
        lines.append(reply.strip())
        lines.append("")
        lines.append("检索结果：")
        for i, score in hits:
            lines.append(f"- {score:.4f}  {chunks[i].label()}  {chunks[i].heading}")
        lines.append("")
        lines.append(f"耗时：{elapsed:.1f} 秒")
        lines.append("")

    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n结果已写入 {OUT_PATH}")


if __name__ == "__main__":
    main()
