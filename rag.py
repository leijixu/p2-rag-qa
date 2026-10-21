"""P2 第一步：手写最小 RAG 链路（numpy，不引入向量库）。

流程：
    读文档 -> 切块 -> 向量化 -> 余弦相似度 top-k -> 拼 prompt -> 调对话模型

用法（PowerShell）：
    python rag.py chunk
    python rag.py ask "P1 服务的限流阈值是多少？"

环境变量（只有 ask 模式需要）：
    DASHSCOPE_API_KEY  阿里云百炼 embedding
    DEEPSEEK_API_KEY   对话模型（沿用 P1 已验证的 DeepSeek）

先只实现 split_into_chunks，跑通 chunk 模式；其余 TODO 留到下一步。
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from openai import OpenAI

EMBED_BASE_URL = "https://maas.qianwenaiapi.com/compatible-mode/v1"
EMBED_MODEL = "text-embedding-v3"
EMBED_BATCH = 10  # 百炼批量上限若低于 10，按报错再调小

CHAT_BASE_URL = "https://api.deepseek.com"
CHAT_MODEL = "deepseek-chat"

DATA_DIR = Path(__file__).resolve().parent / "data"
MAX_CHARS = 600
TOP_K = 3


@dataclass(frozen=True)
class Chunk:
    source: str
    index: int
    heading: str
    text: str

    def label(self) -> str:
        return f"{self.source}#{self.index}"


def load_documents(data_dir: Path) -> list[tuple[str, str]]:
    """读入 data/ 下所有 markdown，返回 [(文件名, 全文)]。"""
    files = sorted(data_dir.glob("*.md"))
    if not files:
        sys.exit(f"{data_dir} 里没有 .md 文件，先放 1~3 篇文档进去")
    return [(p.name, p.read_text(encoding="utf-8")) for p in files]


def split_into_chunks(source: str, text: str, max_chars: int = MAX_CHARS) -> list[Chunk]:
    """把一篇 markdown 切成带来源信息的块。

    需要满足：
    - 先按 markdown 标题切大块；超长的大块再按空行切到 <= max_chars
    - ``` 代码围栏里的 # 不是标题（data/p1-readme.md 里有反例，必须验证）
    - heading 存标题路径，例如 "技术栈 > 实现要点 > 7. 按 IP 限流"
    - text 只存正文，不要重复 heading；index 在整个文件内从 0 连续编号
    - 不产生空块；单个段落超长时允许硬切

    提示：先写一个状态机/循环识别标题行和代码围栏，再做二级切分。
    """
    raise NotImplementedError("TODO 1: 实现切块，然后用 python rag.py chunk 检查")


def embedding_text(chunk: Chunk) -> str:
    """送去 embedding 的文本：标题路径 + 正文。"""
    return f"{chunk.heading}\n{chunk.text}".strip()


def embed_texts(client: OpenAI, texts: list[str]) -> np.ndarray:
    """把一批文本转成 shape=(len(texts), 1024) 的 float32 矩阵。

    需要做：
    - 按 EMBED_BATCH 分批调用 client.embeddings.create(model=EMBED_MODEL, input=batch)
    - 按返回顺序取 resp.data[i].embedding，最后 np.asarray(..., dtype=np.float32)
    - 打印每批的 usage.total_tokens（方便后面估算成本）
    - 如果返回维度不是 1024，直接报错，不要静默继续
    """
    raise NotImplementedError("TODO 2: 实现 embedding 批处理")


def cosine_top_k(
    query_vec: np.ndarray, matrix: np.ndarray, k: int = TOP_K
) -> list[tuple[int, float]]:
    """返回 [(matrix 行号, 相似度), ...]，按相似度降序，最多 k 个。

    需要做：
    - 分别归一化 query_vec 和 matrix 的每一行，注意零向量的情况
    - 相似度用矩阵乘法一次算完，不要写 Python 双重循环
    - 用 np.argsort 取 top-k
    """
    raise NotImplementedError("TODO 3: 实现余弦相似度 top-k")


def build_prompt(question: str, chunks: list[Chunk]) -> str:
    """把 top-k 材料拼成 prompt。约束必须写清楚：

    1. 只根据材料回答，不使用外部知识
    2. 每条结论后面标出处，格式 [文件名#序号]
    3. 材料不足时回答“根据现有材料无法回答”，不要猜
    4. 材料之间冲突时指出冲突，不要擅自选一个
    """
    raise NotImplementedError("TODO 4: 写 prompt 模板")


def generate(client: OpenAI, prompt: str) -> str:
    """调用对话模型，返回纯文本。"""
    raise NotImplementedError("TODO 5: 调用 chat.completions.create")


def cmd_chunk() -> None:
    documents = load_documents(DATA_DIR)
    chunks: list[Chunk] = []
    for name, text in documents:
        chunks.extend(split_into_chunks(name, text))

    for chunk in chunks:
        print(f"{chunk.label():<22} {len(chunk.text):>4} 字  {chunk.heading}")
    print(f"\n共 {len(chunks)} 块，来自 {len(documents)} 篇文档")


def cmd_ask(question: str) -> None:
    dashscope_key = os.environ.get("DASHSCOPE_API_KEY")
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
    if not dashscope_key or not deepseek_key:
        sys.exit("先设置 DASHSCOPE_API_KEY 和 DEEPSEEK_API_KEY")

    embed_client = OpenAI(api_key=dashscope_key, base_url=EMBED_BASE_URL)
    chat_client = OpenAI(api_key=deepseek_key, base_url=CHAT_BASE_URL)

    documents = load_documents(DATA_DIR)
    chunks: list[Chunk] = []
    for name, text in documents:
        chunks.extend(split_into_chunks(name, text))
    if not chunks:
        sys.exit("没有切出任何块")

    matrix = embed_texts(embed_client, [embedding_text(c) for c in chunks])
    query_vec = embed_texts(embed_client, [question])[0]
    hits = cosine_top_k(query_vec, matrix)

    selected = [chunks[i] for i, _ in hits]
    prompt = build_prompt(question, selected)
    reply = generate(chat_client, prompt)

    print(reply)
    print("\n--- 检索结果 ---")
    for i, score in hits:
        print(f"{score:.4f}  {chunks[i].label()}  {chunks[i].heading}")


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit('用法: python rag.py chunk | python rag.py ask "问题"')

    command = sys.argv[1]
    if command == "chunk":
        cmd_chunk()
    elif command == "ask" and len(sys.argv) >= 3:
        cmd_ask(" ".join(sys.argv[2:]))
    else:
        sys.exit('用法: python rag.py chunk | python rag.py ask "问题"')


if __name__ == "__main__":
    main()
