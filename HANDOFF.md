# P2 · RAG 知识库问答 — 交接说明

## 我是谁 / 目标

- 李嘉轩，浙江万里学院 计算机科学与技术，2027 届（2027.06 毕业）
- 目标：2027 春招拿到 Agent 应用开发 / 大模型应用开发实习
- 每天可投入 5 小时以上，偶有中断
- 学习方式：**先讲概念再动手；代码给骨架让我自己填，不要直接给完整实现；一次只推进一小块；每步都有可验证的验收标准；中文回答**

## 已完成，不用重做

**P0 · 多轮流式对话 CLI** — github.com/leijixu/p0-llm-basics

**P1 · FastAPI 对话服务** — github.com/leijixu/p1-llm-api

- `/health`、`/chat`、`/chat/stream`（SSE）、`/chat/stream/async`
- 30s 超时；上游异常映射为 502 / 504；流式异常用 `upstream_error` 事件上报；正常结束发 `data: [DONE]`
- 中间件按 IP 限流：60 秒滑动窗口、20 次/分钟、超限 429 + `Retry-After`
- 部署：腾讯云轻量 `43.142.41.234:8000`，systemd 常驻 + 开机自启；Dockerfile 已验证通过

进度以这两个文件为准：

- `C:\Users\李嘉轩\Documents\ChatGPT\agent学习\ROADMAP.md`
- `C:\Users\李嘉轩\Documents\ChatGPT\agent学习\PROGRESS.md`

## P2 目标

可演示的知识库问答，带引用溯源。最终要能公网访问，并写进简历。

## 选型状态

### 已确定：embedding（10/21 实测通过）

| 项 | 值 |
| --- | --- |
| 平台 | 阿里云百炼（千问） |
| base_url | `https://maas.qianwenaiapi.com/compatible-mode/v1` |
| 模型 | `text-embedding-v3` |
| 向量维度 | **1024** |
| 协议 | OpenAI 兼容，用 `openai` SDK 的 `client.embeddings.create()` 直接调 |

验证方式：仓库里的 `probe_embedding.py` 跑一次即可（key 从环境变量 `DASHSCOPE_API_KEY` 读）。
实测返回 1024 维向量、usage 正常，说明模型名和地址都对。

> 注意：这个 base_url 的域名不是 `aliyuncs.com`，是用户从控制台拿到的地址；无法联网核实域名归属，
> 但接口行为符合 OpenAI 兼容规范，可以正常使用。简历上写"接入阿里云百炼 embedding 接口"是合理的。

### 待定 1：要不要用框架

主流方案：LangChain、LlamaIndex（库），RAGFlow、Dify（低代码产品）。

建议：**先手写最小链路，再用 LlamaIndex 复刻一遍做对照**。理由：面试问的是"检索到底怎么工作"，
只答得出框架名会被追到哑口。手写版大约 60~80 行，值得。

（这些框架的当前状态没有联网核实，真正选型时以官网为准。）

### 待定 2：语料用什么

建议先用自己的项目 README + 几篇技术文档，来源可解释。
文档放 `data/`，已加入 .gitignore。
## 第一步（等决策 1 定了再做）

用 numpy 手写，不引入向量库：

1. 读入 1~3 篇 markdown
2. 按标题 / 段落切块，每块记录来源文件名和序号
3. 调 embedding 接口拿向量
4. 查询时算余弦相似度，取 top-3
5. 把 top-3 拼进 prompt，要求模型只基于给定材料回答，并标出处

验收标准：问一个只存在于文档里的细节，能答对并给出处；问文档里没有的东西，模型要明确说不知道。

## 三个先别踩的坑

- **RAG 的效果大头在切块和 rerank，不在向量库选型。** 先别一上来就上 Qdrant / Chroma。
- **向量检索不等于语义一定对。** 专有名词、缩写、数字仍是弱项，所以后面要做混合检索（关键词 + 向量）。
- **先写评测集。** 没有评测集，你无法判断一次改动是变好还是变坏。