"""
探测 embedding 接口：模型名对不对、向量维度是多少。

用法（PowerShell）：
    $env:DASHSCOPE_API_KEY = "sk-你的key"
    & "G:\code\p1-llm-api\.venv\Scripts\python.exe" "G:\codex\rag-qa\probe_embedding.py"
    & "G:\code\p1-llm-api\.venv\Scripts\python.exe" "G:\codex\rag-qa\probe_embedding.py" 换个模型名

base_url 和最可能的模型名在下面，按实际情况改。
"""
import os
import sys

from openai import OpenAI

BASE_URL = "https://maas.qianwenaiapi.com/compatible-mode/v1"
DEFAULT_MODEL = "text-embedding-v3"

key = os.environ.get("DASHSCOPE_API_KEY")
if not key:
    sys.exit("没找到环境变量 DASHSCOPE_API_KEY：先在 PowerShell 里 $env:DASHSCOPE_API_KEY = \"sk-...\"")

model = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MODEL
client = OpenAI(api_key=key, base_url=BASE_URL)

try:
    resp = client.embeddings.create(model=model, input="这是一次探测")
except Exception as exc:
    print("调用失败：", type(exc).__name__)
    print(exc)
    sys.exit(1)

vec = resp.data[0].embedding
print("base_url :", BASE_URL)
print("模型     :", model)
print("维度     :", len(vec))
print("前 5 个值:", [round(x, 4) for x in vec[:5]])
try:
    print("usage    :", resp.usage)
except Exception:
    pass