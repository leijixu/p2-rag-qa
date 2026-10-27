"""P2 第一步：手写最小 RAG 链路（numpy，不引入向量库）。

流程：
    读文档 -> 切块 -> 向量化 -> 余弦相似度 top-k -> 拼 prompt -> 调对话模型

用法（PowerShell）：
    python rag.py parse
    python rag.py chunk
    python rag.py ask "P1 服务的限流阈值是多少？"

环境变量（只有 ask 模式需要）：
    DASHSCOPE_API_KEY  阿里云百炼 embedding
    DEEPSEEK_API_KEY   对话模型（沿用 P1 已验证的 DeepSeek）

先只实现 split_into_chunks，跑通 chunk 模式；其余 TODO 留到下一步。
"""

from __future__ import annotations

import os
import re
import sys
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from openai import OpenAI

EMBED_BASE_URL = "https://maas.qianwenaiapi.com/compatible-mode/v1"
EMBED_MODEL = "text-embedding-v3"
EMBED_BATCH = 10  # 百炼批量上限若低于 10，按报错再调小

CHAT_BASE_URL = "https://api.deepseek.com"
CHAT_MODEL = "deepseek-chat"

ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = ROOT_DIR / "data"
SAMPLES_DIR = ROOT_DIR / "samples"


def _pick_data_dir() -> Path:
    """data/ 里有文件就用 data/，否则退回仓库自带的 samples/。"""
    if DEFAULT_DATA_DIR.is_dir() and any(DEFAULT_DATA_DIR.glob("*")):
        return DEFAULT_DATA_DIR
    return SAMPLES_DIR


DATA_DIR = _pick_data_dir()
MAX_CHARS = 600
TOP_K = 3
SUPPORTED_SUFFIXES = {".md", ".py"}

TOKEN_RE = re.compile(r"[a-z_][a-z0-9_\.]*|\d+")
STOPWORDS = {"p0", "p1", "p2", "readme", "md"}


def tokenize(text: str) -> list[str]:
    """把文本切成小写 token：英文标识符、带点的标识符、数字。中文暂时不切。"""
    return [token for token in TOKEN_RE.findall(text.lower()) if token not in STOPWORDS]


def source_filter(question: str) -> str | None:
    """问题里明确提到 p0/p1/p2 时，只在这些来源里检索。

    项目名不当内容词（已进 STOPWORDS），但当来源过滤器：
    “P0 源码里……” 就只看 p0-* 文件，避免和 P1 的同名函数混淆。
    """
    lowered = question.lower()
    hits = [prefix for prefix in ("p0", "p1", "p2") if re.search(rf"\b{prefix}\b", lowered)]
    return hits[0] if len(hits) == 1 else None


def keyword_scores(
    question: str, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75
) -> list[float]:
    """BM25 关键词分数，返回每个块一个分数。

    BM25 解决两个问题：
    - 罕见词权重更高（IDF）：time.monotonic 只在 1 个块里出现，权重大
    - 词频饱和（TF saturation）：p1 出现 5 次，不会简单地把分数拉成 5 倍
    """
    query_tokens = list(dict.fromkeys(tokenize(question)))
    if not query_tokens or not chunks:
        return [0.0] * len(chunks)

    total = len(chunks)
    lower_texts = [chunk.text.lower() for chunk in chunks]
    lengths = [len(chunk.text) for chunk in chunks]
    avg_len = sum(lengths) / total

    doc_freq = {
        token: sum(1 for lower in lower_texts if token in lower)
        for token in query_tokens
    }
    idf = {
        token: math.log((total - doc_freq[token] + 0.5) / (doc_freq[token] + 0.5) + 1)
        for token in query_tokens
    }

    scores: list[float] = []
    for lower, dl in zip(lower_texts, lengths):
        score = 0.0
        for token in query_tokens:
            tf = lower.count(token)
            if tf:
                score += idf[token] * (tf * (k1 + 1)) / (
                    tf + k1 * (1 - b + b * dl / avg_len)
                )
        scores.append(score)
    return scores


@dataclass(frozen=True)
class Chunk:
    source: str
    index: int
    heading: str
    text: str

    def label(self) -> str:
        return f"{self.source}#{self.index}"


@dataclass(frozen=True)
class Section:
    heading: str
    lines: list[str]


def load_documents(data_dir: Path) -> list[tuple[str, str]]:
    """读入 data/ 下所有 markdown / Python 文件，返回 [(文件名, 全文)]。"""
    files = sorted(
        path
        for path in data_dir.iterdir()
        if path.is_file() and path.suffix in SUPPORTED_SUFFIXES
    )
    if not files:
        sys.exit(f"{data_dir} 里没有 {SUPPORTED_SUFFIXES} 文件，先放几篇文档进去")
    return [(p.name, p.read_text(encoding="utf-8")) for p in files]


def load_env_file() -> None:
    """把仓库根目录 .env 里的键值读进 os.environ，已存在的不覆盖。"""
    path = Path(__file__).resolve().parent / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def parse_sections(text: str) -> list[Section]:
    """第一小步：把 markdown 拆成 [(标题路径, 正文行)]。

    只处理三件事：
    1. 用 in_fence 跟踪 ``` 代码围栏，围栏里的 # 不是标题
    2. 用 heading_stack 维护层级，例如 [1, 2, 3] -> "A > B > C"
    3. 遇到新标题时，把上一节放进 sections

    边界：
    - 第一个标题前的内容，heading 用 "(文档开头)"
    - 标题行本身不要放进正文
    - 空正文的 section 也返回，交给 pack_section 决定是否跳过
    """
    in_fence = False
    stack: list[tuple[int,str]] = []
    sections: list[Section] = []
    current_heading = "(文档开头)"
    current_lines: list[str] = []

    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            current_lines.append(line)
            continue

        if not in_fence and line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            title = line[level:].strip()

            if 0 < level <= 6 and line[level:level+1] == " " and title:
                if current_heading != "(文档开头)" or any(line.strip() for line in current_lines):
                    sections.append(Section(current_heading, current_lines.copy()))

                while stack and stack[-1][0] >= level:
                    stack.pop()

                stack.append((level, title))
                current_heading = " > ".join(t for _, t in stack)

                current_lines = []
                continue

        current_lines.append(line)
    if current_heading != "(文档开头)" or any(line.strip() for line in current_lines):
        sections.append(Section(current_heading, current_lines.copy()))
    return sections


def split_long_block(block: str, max_chars: int) -> list[str]:
    """单个 block 超过 max_chars 时，先按行、再按字符硬切。"""
    pieces: list[str] = []
    current = ""

    for line in block.splitlines():
        if len(line) > max_chars:
            if current:
                pieces.append(current)
                current = ""
            for start in range(0, len(line), max_chars):
                pieces.append(line[start : start + max_chars])
            continue

        if not current:
            current = line
        elif len(current) + 1 + len(line) <= max_chars:
            current += "\n" + line
        else:
            pieces.append(current)
            current = line

    if current:
        pieces.append(current)
    return pieces


def pack_section(lines: list[str], max_chars: int) -> list[str]:
    """把一节正文行打包成若干不超过 max_chars 的字符串。

    分两步：
    1. 按空行把正文切成 block；代码围栏里的空行不算分隔符
    2. 贪心合并 block；单个 block 超长时先按行、再按字符硬切

    注意：正文行保留原始缩进，不要对每一行都 strip。
    """
    blocks: list[str] = []
    current: list[str] = []
    in_fence = False

    # 第一遍：按"空行"和"代码围栏"把正文切成若干 block
    # - 普通正文：空行 = block 分隔符
    # - 代码围栏：整个 fenced block 作为一个整体，围栏里的空行不算分隔符
    for line in lines:
        is_fence = line.lstrip().startswith("```")

        # 遇到 ``` 且当前不在围栏里 → 围栏开始
        # 先把正在收集的正文段落收进 blocks，避免正文和代码混在一起
        if is_fence and not in_fence:
            if current:
                blocks.append("\n".join(current))
                current = []
            in_fence = True
            current.append(line)
            continue

        # 遇到 ``` 且当前已在围栏里 → 围栏结束
        # 把从"围栏开始"到"围栏结束"整段（包括两个 ```）作为一个完整 block
        if is_fence and in_fence:
            current.append(line)
            blocks.append("\n".join(current))
            current = []
            in_fence = False
            continue

        # 围栏内：所有行（包括空行）都是代码的一部分，原样追加
        if in_fence:
            current.append(line)
        # 围栏外的空行：标记上一段正文结束，收进 blocks
        elif not line.strip():
            if current:
                blocks.append("\n".join(current))
                current = []
        # 围栏外的非空行：继续累积当前正文段落
        else:
            current.append(line)

    # 循环结束后可能还有一段没来得及收（文件末尾没有空行/围栏来触发 flush）
    if current:
        blocks.append("\n".join(current))

    pieces: list[str] = []
    current_piece = ""
    for block in blocks:
        if len(block) > max_chars:
            if current_piece:
                pieces.append(current_piece)
                current_piece = ""
            pieces.extend(split_long_block(block, max_chars))
            continue

        if not current_piece:
            current_piece = block
        elif len(current_piece) + 2 + len(block) <= max_chars:
            current_piece += "\n\n" + block
        else:
            pieces.append(current_piece)
            current_piece = block

    if current_piece:
        pieces.append(current_piece)
    return pieces


def sections_for(source: str, text: str) -> list[Section]:
    """markdown 走 parse_sections；Python 文件整篇当一个 section。"""
    if source.endswith(".md"):
        return parse_sections(text)
    return [Section(heading=source, lines=text.splitlines())]


def split_into_chunks(source: str, text: str, max_chars: int = MAX_CHARS) -> list[Chunk]:
    """把 parse_sections 和 pack_section 拼成最终的 Chunk 列表。

    这段胶水已经写好，不需要你改。你只写上面两个函数。
    """
    chunks: list[Chunk] = []
    for section in sections_for(source, text):
        for piece in pack_section(section.lines, max_chars):
            piece = piece.strip("\n")
            if not piece.strip():
                continue
            chunks.append(
                Chunk(
                    source=source,
                    index=len(chunks),
                    heading=section.heading,
                    text=piece,
                )
            )
    return chunks


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
    vectors = []
    for start in range(0,len(texts),EMBED_BATCH):
        batch = texts[start:start+EMBED_BATCH]

        resp = client.embeddings.create(model=EMBED_MODEL, input=batch)

        for item in resp.data:
            vectors.append(item.embedding)

        print("本批 tokens:", resp.usage.total_tokens)

    matrix = np.asarray(vectors, dtype=np.float32)

    if matrix.shape[1] != 1024:
        raise ValueError(f"embedding 维度不是 1024，而是 {matrix.shape[1]}")
    return matrix


def cosine_top_k(
    query_vec: np.ndarray, matrix: np.ndarray, k: int = TOP_K
) -> list[tuple[int, float]]:
    """返回 [(matrix 行号, 相似度), ...]，按相似度降序，最多 k 个。

    需要做：
    - 分别归一化 query_vec 和 matrix 的每一行，注意零向量的情况
    - 相似度用矩阵乘法一次算完，不要写 Python 双重循环
    - 用 np.argsort 取 top-k
    """
    query_unit = query_vec / np.linalg.norm(query_vec)
    matrix_unit = matrix / np.linalg.norm(matrix, axis=1, keepdims=True)

    scores = matrix_unit @ query_unit
    order = np.argsort(scores)[::-1][:k]

    result = []
    for i in order:
        result.append((int(i),float(scores[i])))
    return result


def hybrid_top_k(
    query_vec: np.ndarray,
    matrix: np.ndarray,
    question: str,
    chunks: list[Chunk],
    k: int = TOP_K,
    rrf_k: int = 60,
) -> list[tuple[int, float]]:
    """向量检索 + BM25 关键词检索，用 RRF 按名次融合。

    只看名次，不看原始分数，所以不需要把两种分数归一化。
    一个块在两种检索里都靠前，融合分数就高。
    """
    query_unit = query_vec / np.linalg.norm(query_vec)
    matrix_unit = matrix / np.linalg.norm(matrix, axis=1, keepdims=True)
    vector_scores = matrix_unit @ query_unit
    keyword = np.asarray(keyword_scores(question, chunks), dtype=np.float32)

    total = len(chunks)
    prefix = source_filter(question)
    if prefix:
        allowed = np.array(
            [i for i, chunk in enumerate(chunks) if chunk.source.startswith(prefix + "-")],
            dtype=np.int64,
        )
        if allowed.size:
            mask = np.zeros(total, dtype=bool)
            mask[allowed] = True
            vector_scores = np.where(mask, vector_scores, -np.inf)
            keyword = np.where(mask, keyword, 0.0)

    vector_order = np.argsort(vector_scores)[::-1]
    vector_rank = np.empty(total, dtype=np.int32)
    vector_rank[vector_order] = np.arange(1, total + 1)

    # 关键词分数为 0 的块不参与关键词排名。
    # 否则全 0 时 argsort 反转会按索引倒序发名次，把无关块抬上来。
    keyword_rank = np.full(total, 10**6, dtype=np.int64)
    matched = np.flatnonzero(keyword > 0)
    if matched.size:
        keyword_order = matched[np.argsort(keyword[matched])[::-1]]
        keyword_rank[keyword_order] = np.arange(1, matched.size + 1)

    fused = 1.0 / (rrf_k + vector_rank) + 1.0 / (rrf_k + keyword_rank)
    order = np.argsort(fused)[::-1][:k]
    return [(int(i), float(fused[i])) for i in order]


def build_prompt(question: str, chunks: list[Chunk]) -> str:
    """把 top-k 材料拼成 prompt。约束必须写清楚：

    1. 只根据材料回答，不使用外部知识
    2. 每条结论后面标出处，格式 [文件名#序号]
    3. 材料不足时回答“根据现有材料无法回答”，不要猜
    4. 材料之间冲突时指出冲突，不要擅自选一个
    5. 问“有没有 X”时，材料里没有 X 就明确说“没有”，不要回答“无法回答”
    6. 断言“材料里没有 X”前，先确认上下文覆盖了可能定义 X 的材料
    """
    materials = []
    for chunk in chunks:
        materials.append(f"[{chunk.label()}] {chunk.heading}\n{chunk.text}")

    material_text = "\n\n".join(materials)

    return f"""
    1. 只根据材料回答，不使用外部知识
    2. 每条结论后面标出处，格式 [文件名#序号]
    3. 材料不足时回答“根据现有材料无法回答”，不要猜
    4. 材料之间冲突时指出冲突，不要擅自选一个
    5.先给出材料中最具体的答案，再单独指出冲突
    6.数字和响应头尽量答全
    7. 如果问题问“有没有/是否包含 X”：只要材料覆盖了相关文件且材料里没有 X，就明确回答“没有”，并说明你检查了哪些材料；不要把这种情况回答成“无法回答”。
    8. 如果你要断言“材料里没有 X”，先确认上下文确实包含可能定义 X 的材料；否则说“根据我拿到的材料看不出来”。
    材料:
    {material_text}
    问题: {question}
    """


def generate(client: OpenAI, prompt: str) -> str:
    """调用对话模型，返回纯文本。"""
    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role":"user","content":prompt}],
        timeout=30.0
    )
    return resp.choices[0].message.content


def cmd_parse() -> None:
    for name, text in load_documents(DATA_DIR):
        sections = sections_for(name, text)
        print(f"== {name}: {len(sections)} 节 ==")
        for section in sections:
            body_chars = len("\n".join(section.lines).strip())
            print(f"{body_chars:>5} 字  {section.heading}")


def cmd_chunk() -> None:
    documents = load_documents(DATA_DIR)
    chunks: list[Chunk] = []
    for name, text in documents:
        chunks.extend(split_into_chunks(name, text))

    for chunk in chunks:
        print(f"{chunk.label():<22} {len(chunk.text):>4} 字  {chunk.heading}")
    print(f"\n共 {len(chunks)} 块，来自 {len(documents)} 篇文档")


def cmd_embed() -> None:
    """单独测试 embed_texts，不依赖切块和对话模型。"""
    dashscope_key = os.environ.get("DASHSCOPE_API_KEY")
    if not dashscope_key:
        sys.exit("先设置 DASHSCOPE_API_KEY")

    client = OpenAI(api_key=dashscope_key, base_url=EMBED_BASE_URL)
    texts = sys.argv[2:] or ["这是第一句话", "这是第二句话", "这是第三句话"]
    matrix = embed_texts(client, texts)
    print("形状:", matrix.shape)
    print("第一条前 5 个值:", [round(float(x), 4) for x in matrix[0][:5]])


def cmd_similar() -> None:
    """测试余弦相似度：把第一句当查询，看哪句最像。"""
    dashscope_key = os.environ.get("DASHSCOPE_API_KEY")
    if not dashscope_key:
        sys.exit("先设置 DASHSCOPE_API_KEY")

    client = OpenAI(api_key=dashscope_key, base_url=EMBED_BASE_URL)
    texts = sys.argv[2:] or [
        "今天天气很好",
        "今天阳光明媚",
        "数据库的密码是 123456",
        "Python 的列表可以 append",
    ]
    matrix = embed_texts(client, texts)
    hits = cosine_top_k(matrix[0], matrix, k=len(texts))
    for i, score in hits:
        print(f"{score:.4f}  {texts[i]}")


def cmd_keyword(question: str) -> None:
    """只看关键词分数，检查精确词能不能被召回。"""
    chunks: list[Chunk] = []
    for name, text in load_documents(DATA_DIR):
        chunks.extend(split_into_chunks(name, text))

    scores = keyword_scores(question, chunks)
    scored = sorted(enumerate(scores), key=lambda pair: pair[1], reverse=True)

    print("查询 token:", tokenize(question))
    for i, score in scored[:10]:
        print(f"{score:.4f}  {chunks[i].label()}  {chunks[i].heading}")


def cmd_hybrid(question: str) -> None:
    """只看混合检索排名，检查精确词问题的召回。"""
    dashscope_key = os.environ.get("DASHSCOPE_API_KEY")
    if not dashscope_key:
        sys.exit("先设置 DASHSCOPE_API_KEY")

    client = OpenAI(api_key=dashscope_key, base_url=EMBED_BASE_URL)
    chunks: list[Chunk] = []
    for name, text in load_documents(DATA_DIR):
        chunks.extend(split_into_chunks(name, text))

    matrix = embed_texts(client, [embedding_text(c) for c in chunks])
    query_vec = embed_texts(client, [question])[0]
    hits = hybrid_top_k(query_vec, matrix, question, chunks, k=10)

    print("查询 token:", tokenize(question))
    for i, score in hits:
        print(f"{score:.4f}  {chunks[i].label()}  {chunks[i].heading}")


def cmd_prompt(question: str) -> None:
    """只跑检索 + 拼 prompt，不调用对话模型。"""
    dashscope_key = os.environ.get("DASHSCOPE_API_KEY")
    if not dashscope_key:
        sys.exit("先设置 DASHSCOPE_API_KEY")

    client = OpenAI(api_key=dashscope_key, base_url=EMBED_BASE_URL)
    documents = load_documents(DATA_DIR)
    chunks: list[Chunk] = []
    for name, text in documents:
        chunks.extend(split_into_chunks(name, text))

    matrix = embed_texts(client, [embedding_text(c) for c in chunks])
    query_vec = embed_texts(client, [question])[0]
    hits = hybrid_top_k(query_vec, matrix, question, chunks)
    selected = [chunks[i] for i, _ in hits]

    print(build_prompt(question, selected))
    print("\n--- 检索结果 ---")
    for i, score in hits:
        print(f"{score:.4f}  {chunks[i].label()}  {chunks[i].heading}")


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
    hits = hybrid_top_k(query_vec, matrix, question, chunks)

    selected = [chunks[i] for i, _ in hits]
    prompt = build_prompt(question, selected)
    reply = generate(chat_client, prompt)

    print(reply)
    print("\n--- 检索结果 ---")
    for i, score in hits:
        print(f"{score:.4f}  {chunks[i].label()}  {chunks[i].heading}")


def main() -> None:
    load_env_file()
    if len(sys.argv) < 2:
        sys.exit('用法: python rag.py parse | chunk | embed | similar | keyword "问题" | hybrid "问题" | prompt "问题" | ask "问题"')

    command = sys.argv[1]
    if command == "parse":
        cmd_parse()
    elif command == "chunk":
        cmd_chunk()
    elif command == "embed":
        cmd_embed()
    elif command == "similar":
        cmd_similar()
    elif command == "keyword" and len(sys.argv) >= 3:
        cmd_keyword(" ".join(sys.argv[2:]))
    elif command == "hybrid" and len(sys.argv) >= 3:
        cmd_hybrid(" ".join(sys.argv[2:]))
    elif command == "prompt" and len(sys.argv) >= 3:
        cmd_prompt(" ".join(sys.argv[2:]))
    elif command == "ask" and len(sys.argv) >= 3:
        cmd_ask(" ".join(sys.argv[2:]))
    else:
        sys.exit('用法: python rag.py parse | chunk | embed | similar | keyword "问题" | hybrid "问题" | prompt "问题" | ask "问题"')


if __name__ == "__main__":
    main()
