# P2 检索评测集（v0）

目的：每次改切块、embedding、top-k 或 prompt 后，用同一组问题对比效果，避免“感觉变好了”。

评分规则：答对记 1；答错或编造记 0；不可答题必须明确拒答，含糊其辞也算 0。
出处按章节名记录，切块后的真实编号（如 `p1-readme.md#7`）在第一次跑通后补上。

| # | 问题 | 期望答案要点 | 期望出处 |
|---|---|---|---|
| 1 | P1 服务按 IP 限流的阈值是多少？ | 60 秒滑动窗口内最多 20 次，超限返回 429 和 Retry-After | 实现要点 > 7. 按 IP 限流 |
| 2 | P1 的同步端点 60 并发实测耗时多少？ | 3.25 秒 | 实现要点 > 5. 同步 vs 异步 |
| 3 | FastAPI 同步端点使用的线程池默认容量是多少？ | 40 | 实现要点 > 5. 同步 vs 异步 |
| 4 | P1 流式接口的 timeout 是什么含义？ | 两个 chunk 之间最多等 30 秒，不是整个回答的总时长 | 实现要点 > 6. 超时与错误处理 |
| 5 | P1 流式回答正常结束和出错分别发什么？ | 正常发 `data: [DONE]`；出错发 `upstream_error`，且不发 `[DONE]` | 实现要点 > 4 / 6 |
| 6 | P0 的 CLI 怎么退出？ | 输入 `exit` | 功能 / 快速开始 |
| 7 | 这个知识库用的 embedding 模型是什么？ | 明确说材料里没有，不能凭外部知识回答 | 不可答 |
| 8 | P0 项目的数据库密码是多少？ | 明确说材料里没有 | 不可答 |
| 9 | P1 提到 openai SDK 的默认超时是多少秒？ | 600 秒（`openai/_constants.py` 的 `DEFAULT_TIMEOUT`） | 实现要点 > 6. 超时与错误处理 |
| 10 | P1 的 `/slow-sync` 端点在 120 并发下实测耗时多少？ | 4.70 秒 | 实现要点 > 5. 同步 vs 异步 |
| 11 | P1 的限流中间件为什么不能直接 `raise HTTPException`？ | 异常处理器挂在路由层，中间件里抛没人接，会变成 500；要自己返回 `JSONResponse(status_code=429, ...)` | 实现要点 > 7. 按 IP 限流 |
| 12 | P1 里哪个地方用了 `time.monotonic()` 而不是 `time.time()`，为什么？ | 限流滑动窗口的时间戳；避免系统时间被调整时窗口错乱 | 实现要点 > 7. 按 IP 限流 |
| 13 | P1 服务用的 PostgreSQL 版本是多少？ | 明确说材料里没有 | 不可答 |
| 14 | 限流窗口为什么用单调时钟而不是系统时钟？ | 用 `time.monotonic()` 存请求时间戳，避免系统时间被调整时窗口错乱 | 实现要点 > 7. 按 IP 限流 |
| 15 | 120 并发下异步端点两次实测分别是多少秒？ | 1.73 s 和 1.81 s（差值属于测量噪声） | 实现要点 > 5. 同步 vs 异步 |
| 16 | 为什么 120 并发的同步端点耗时是 4.70 秒，而不是 1.5 秒？ | FastAPI 把同步端点放进 anyio 线程池，默认容量 40；120 并发分 3 批，每批 1.5 秒，理论 4.5 秒，实测 4.70 秒 | 实现要点 > 5. 同步 vs 异步 |
| 17 | P1 里哪些接口不限流，为什么？ | `/health`、`/docs`、`/static`；探活要被监控高频调用，`/docs` 加载一次要请求四个资源（页面 + CSS + JS + openapi.json），拦了会打不开文档页 | 实现要点 > 7. 按 IP 限流 |
| 18 | P0 的多轮记忆是怎么实现的？ | 维护 messages 列表保存完整对话历史，每轮追加用户输入和助手完整回复 | P0 实现要点 |
| 19 | P1 用的 Redis 版本是多少？ | 明确说材料里没有 | 不可答 |
| 20 | P1 的 `/slow-sync` 在 60 并发下理论耗时和实测耗时分别是多少？ | 理论 3.0 秒，实测 3.25 秒 | 实现要点 > 5. 同步 vs 异步 |
| 21 | P1 流式接口出错时为什么不发 `[DONE]`？ | 出错发 `upstream_error`，两个信号互斥，客户端据此区分“答完了”和“中途断了”；`[DONE]` 是正常结束哨兵 | 实现要点 > 6. 超时与错误处理 |
| 22 | P1 部署时为什么用 8000 端口而不是 80？ | 国内服务器用 80 端口对公网提供 HTTP 服务需要 ICP 备案，所以演示走 8000 这类非标准端口 | 部署记录 |
| 23 | P1 的 API key 是怎么管理的？ | 通过 `.env` 管理并加入 `.gitignore`，避免敏感信息进版本库；`main.py` 从环境变量 `DEEPSEEK_API_KEY` 读取 | 实现要点 > 3. 密钥不进版本库 |
| 24 | P1 源码里限流用的 `LIMIT` 和 `WINDOW` 常量分别是多少？ | `LIMIT = 20`，`WINDOW = 60` | p1-main.py |
| 25 | P1 源码里每个 IP 的请求时间戳存在什么变量和数据结构里？ | `_hits = defaultdict(deque)`，键是 IP，值是 `deque` | p1-main.py |
| 26 | P1 源码里 `/chat` 端点遇到 `APITimeoutError` 和 `APIConnectionError` 分别返回什么状态码？ | 504 和 502 | p1-main.py |
| 27 | P1 源码里 `/chat/stream/async` 用的是哪个客户端对象？ | `aclient`（`AsyncOpenAI`） | p1-main.py |
| 28 | P1 源码里 `/slow` 和 `/slow-sync` 哪个是同步实现？ | `/slow-sync` 是同步（`def` + `time.sleep(1.5)`），`/slow` 是异步（`async def` + `await asyncio.sleep(1.5)`） | p1-main.py |
| 29 | P0 源码里用什么函数加载 `.env`？ | `load_dotenv()`，来自 `python-dotenv` | p0-chat_cli.py |
| 30 | P0 源码里从流式响应的每个 chunk 里怎么取文本？ | `chunk.choices[0].delta.content` | p0-chat_cli.py |
| 31 | P1 源码里限流超限时返回的 JSON 响应里 `detail` 字段是什么？ | `f"请求过于频繁，请 {wait} 秒后再试"` | p1-main.py |
| 32 | P1 源码里 `GUARDED` 变量限制哪些路径？ | 以 `/chat` 开头的路径 | p1-main.py |
| 33 | P1 源码里 `/chat/stream` 出错时 `yield` 的事件名是什么？ | `event: upstream_error` | p1-main.py |
| 34 | P1 源码里 `bench.py` 用哪个库发 HTTP 请求？ | `urllib`（`urllib.request`） | p1-bench.py |
| 35 | P1 用的消息队列是什么？ | 明确说材料里没有 | 不可答 |
| 36 | P1 源码里有没有用到 Redis？ | 没有；材料里没有 Redis 相关代码 | 不可答 / p1-main.py |
| 37 | P1 源码里有没有定义日志级别常量（如 `LOG_LEVEL`）？ | 没有；材料里没有日志级别常量 | 不可答 / p1-main.py |
| 38 | P0 源码里有没有 try/except 异常处理？ | 没有；`p0-chat_cli.py` 里没有 try/except | p0-chat_cli.py |
| 39 | P1 源码里有没有用到连接池或数据库？ | 没有；材料里没有连接池或数据库相关代码 | 不可答 / p1-main.py |
| 40 | P1 源码里有没有 `WINDOW` 这个常量？ | 有，`WINDOW = 60` | p1-main.py |
| 41 | P1 源码里有没有 `GUARDED` 常量？ | 有，`GUARDED = ("/chat",)` | p1-main.py |

## 用法

1. 先跑 `python rag.py chunk`，确认可答题的答案没有被切碎到无法检索。
2. 跑通 `ask` 后，逐题记录：回答、引用出处、是否正确。
3. 后续每次改动只改一个变量（例如 `MAX_CHARS` 或 `TOP_K`），再跑同一套题对比。
