"""诊断检索排名：打印一个问题在全部块里的相似度前 15 名。

用法：
    python diag_rank.py "P1 里哪个地方用了 time.monotonic()？"
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np

import rag
from run_eval import ROOT, load_env


def main() -> None:
    question = sys.argv[1] if len(sys.argv) > 1 else "time.monotonic 用在哪里？"
    env = load_env(ROOT / ".env")
    key = os.environ.get("DASHSCOPE_API_KEY") or env.get("DASHSCOPE_API_KEY")
    if not key:
        sys.exit("缺少 DASHSCOPE_API_KEY")

    client = rag.OpenAI(api_key=key, base_url=rag.EMBED_BASE_URL)
    chunks = []
    for name, text in rag.load_documents(rag.DATA_DIR):
        chunks.extend(rag.split_into_chunks(name, text))

    matrix = rag.embed_texts(client, [rag.embedding_text(c) for c in chunks])
    query_vec = rag.embed_texts(client, [question])[0]

    matrix_unit = matrix / np.linalg.norm(matrix, axis=1, keepdims=True)
    query_unit = query_vec / np.linalg.norm(query_vec)
    scores = matrix_unit @ query_unit
    order = np.argsort(scores)[::-1]

    print("问题：", question)
    for rank, i in enumerate(order[:15], start=1):
        print(f"{rank:>2}. {scores[i]:.4f}  {chunks[i].label()}  {chunks[i].heading}")


if __name__ == "__main__":
    main()
