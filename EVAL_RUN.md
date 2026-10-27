# EVAL 跑分结果

块数：43

## 1. P1 服务按 IP 限流的阈值是多少？

按 IP 限流阈值为：每个 IP 每分钟最多 20 次（`LIMIT = 20`，`WINDOW = 60` 秒），采用 60 秒滑动窗口，窗口内超过 20 次返回 `429` [p1-main.py#9][p1-readme.md#15]。

补充说明：
- 限流只作用于 `/chat` 开头的业务接口（`GUARDED = ("/chat",)`），`/health`、`/docs`、`/static` 不拦 [p1-main.py#9][p1-readme.md#15]。
- 429 响应会带上 `Retry-After` 头 [p1-readme.md#15]。

冲突检查：未发现材料之间就阈值（20 次 / 60 秒）存在冲突。

检索结果：
- 0.0328  p1-main.py#9  p1-main.py
- 0.0320  p1-readme.md#15  LLM 对话 API 服务 > 实现要点 > 7. 按 IP 限流
- 0.0304  p1-readme.md#22  LLM 对话 API 服务 > 已知局限与下一步

耗时：2.0 秒

## 2. P1 的同步端点 60 并发实测耗时多少？

P1 的同步端点 `/slow-sync` 在 60 并发下实测耗时为 **3.25 s** [p1-readme.md#10]。

材料中未发现与之冲突的数据（同一表格内其他数据分别为 120 并发 4.70 s；异步端点 60 并发 1.77 s、120 并发 1.73/1.81 s），无需指出冲突 [p1-readme.md#10]。

检索结果：
- 0.0325  p1-readme.md#11  LLM 对话 API 服务 > 实现要点 > 5. 同步 vs 异步：实测数据
- 0.0320  p1-readme.md#10  LLM 对话 API 服务 > 实现要点 > 5. 同步 vs 异步：实测数据
- 0.0320  p1-bench.py#0  p1-bench.py

耗时：1.5 秒

## 3. FastAPI 同步端点使用的线程池默认容量是多少？

根据材料，FastAPI 同步端点使用的线程池默认容量是 **40**：`CapacityLimiter(40)` [p1-readme.md#10]。

材料中还说明同步端点被丢进 anyio 线程池执行，因此 60 并发分 2 批（理论 3.0 s、实测 3.25 s），120 并发分 3 批（理论 4.5 s、实测 4.70 s）[p1-readme.md#10]。

检索结果：
- 0.0309  p1-readme.md#10  LLM 对话 API 服务 > 实现要点 > 5. 同步 vs 异步：实测数据
- 0.0308  p1-readme.md#0  LLM 对话 API 服务
- 0.0301  p1-main.py#0  p1-main.py

耗时：1.4 秒

## 4. P1 流式接口的 timeout 是什么含义？

根据材料，P1 流式接口的 `timeout` 含义是：**不是「整个回答最多 30 秒」，而是「两个 chunk 之间最多等 30 秒」，长回答不会被掐断** [p1-readme.md#12]。

材料中明确给出的具体值是 `timeout=30.0` [p1-readme.md#12]，并在代码中体现为流式请求参数 `timeout=30.0` [p1-main.py#7]。

未发现材料之间关于此含义的冲突。

检索结果：
- 0.0320  p1-readme.md#12  LLM 对话 API 服务 > 实现要点 > 6. 超时与错误处理
- 0.0318  p1-main.py#7  p1-main.py
- 0.0313  p1-readme.md#14  LLM 对话 API 服务 > 实现要点 > 6. 超时与错误处理

耗时：1.6 秒

## 5. P1 流式回答正常结束和出错分别发什么？

正常结束发送 `data: [DONE]`（OpenAI 生态约定的哨兵值，非 SSE 协议自带）[p1-readme.md#13]；出错时发送 `event: upstream_error` 事件，例如超时发 `data: 模型服务超时，回答已中断`[p1-main.py#5][p1-readme.md#13]，连接失败发 `data: 无法连接模型服务，回答已中断`[p1-main.py#5][p1-main.py#8]。两个信号互斥：出错时不会发 `[DONE]`，客户端据此区分「答完了」和「中途断了」[p1-readme.md#13]。

响应头方面：流式端点不能靠状态码上报错误，`StreamingResponse` 会先发 `200 OK` 响应头再开始跑生成器，出错时状态码已经发出去了，唯一上报通道是往流里再写一条消息[p1-readme.md#13]；`media_type` 必须是 `text/event-stream`[p1-main.py#8]。

未发现材料间冲突。

检索结果：
- 0.0164  p1-main.py#5  p1-main.py
- 0.0161  p1-readme.md#13  LLM 对话 API 服务 > 实现要点 > 6. 超时与错误处理
- 0.0159  p1-main.py#8  p1-main.py

耗时：2.1 秒

## 6. P0 的 CLI 怎么退出？

根据材料，P0 的 CLI 退出方式：在输入提示 `"\n你: "` 处输入 `exit` 即可退出循环，随后打印 `"\n再见"` 结束程序 [p0-chat_cli.py#0][p0-chat_cli.py#1]。

补充细节：输入为空（strip 后为空）时会 `continue` 跳过，不会退出 [p0-chat_cli.py#0]。

材料中未发现冲突。

检索结果：
- 0.0323  p0-chat_cli.py#0  p0-chat_cli.py
- 0.0318  p0-readme.md#2  LLM 多轮流式对话 CLI > 快速开始
- 0.0164  p0-chat_cli.py#1  p0-chat_cli.py

耗时：1.6 秒

## 7. 这个知识库用的 embedding 模型是什么？

根据现有材料无法回答。我检查了 p1-readme.md#0、p1-readme.md#3、p1-main.py#5，材料只说明服务通过 OpenAI 兼容 SDK 接入 DeepSeek [p1-readme.md#0]，未提及知识库使用的 embedding 模型。

检索结果：
- 0.0164  p1-readme.md#3  LLM 对话 API 服务 > 项目结构
- 0.0161  p1-main.py#5  p1-main.py
- 0.0159  p1-readme.md#0  LLM 对话 API 服务

耗时：1.2 秒

## 8. P0 项目的数据库密码是多少？

根据现有材料无法回答。材料中没有出现任何数据库密码相关信息：`p0-chat_cli.py` 只涉及 `DEEPSEEK_API_KEY` 环境变量 [p0-chat_cli.py#0]；`p0-readme.md` 只说明密钥通过 .env 管理 [p0-readme.md#4]，未提及数据库或其密码。

检索结果：
- 0.0164  p0-chat_cli.py#0  p0-chat_cli.py
- 0.0161  p0-chat_cli.py#1  p0-chat_cli.py
- 0.0159  p0-readme.md#4  LLM 多轮流式对话 CLI > 实现要点

耗时：1.4 秒

## 9. P1 提到 openai SDK 的默认超时是多少秒？

根据材料，openai SDK 的默认超时是 **600 秒**（10 分钟）[p1-readme.md#12]。

检索结果：
- 0.0323  p1-readme.md#12  LLM 对话 API 服务 > 实现要点 > 6. 超时与错误处理
- 0.0315  p1-main.py#0  p1-main.py
- 0.0313  p1-readme.md#13  LLM 对话 API 服务 > 实现要点 > 6. 超时与错误处理

耗时：1.0 秒

## 10. P1 的 `/slow-sync` 端点在 120 并发下实测耗时多少？

P1 的 `/slow-sync` 端点在 120 并发下实测耗时 **4.70 s** [p1-readme.md#10]。

检索结果：
- 0.0325  p1-readme.md#11  LLM 对话 API 服务 > 实现要点 > 5. 同步 vs 异步：实测数据
- 0.0323  p1-main.py#9  p1-main.py
- 0.0318  p1-readme.md#10  LLM 对话 API 服务 > 实现要点 > 5. 同步 vs 异步：实测数据

耗时：1.3 秒

## 11. P1 的限流中间件为什么不能直接 `raise HTTPException`？

根据 p1-readme.md 的说明，中间件里不能直接 `raise HTTPException`，原因是：异常处理器挂在路由那一层，在中间件里抛出去没人接，会变成一个 500；需要自己造响应（例如 `return JSONResponse(status_code=429, ...)`）。[p1-readme.md#15]

材料中没有提到与此冲突的内容。

检索结果：
- 0.0325  p1-readme.md#15  LLM 对话 API 服务 > 实现要点 > 7. 按 IP 限流
- 0.0294  p1-main.py#0  p1-main.py
- 0.0294  p1-main.py#3  p1-main.py

耗时：1.1 秒

## 12. P1 里哪个地方用了 `time.monotonic()` 而不是 `time.time()`，为什么？

材料中最具体的答案：

1. 使用位置：限流中间件 `rate_limit` 里，取当前时间 `now = time.monotonic()` [p1-main.py#9]。
2. 原因：为了避免系统时间被调整时窗口错乱 [p1-readme.md#15]。

材料之间没有冲突。

检索结果：
- 0.0325  p1-main.py#9  p1-main.py
- 0.0296  p1-readme.md#15  LLM 对话 API 服务 > 实现要点 > 7. 按 IP 限流
- 0.0161  p1-main.py#0  p1-main.py

耗时：1.2 秒

## 13. P1 服务用的 PostgreSQL 版本是多少？

根据现有材料无法回答。材料中没有出现 PostgreSQL 或任何数据库版本信息。我检查了提供的材料 [p1-main.py#0]、[p1-main.py#7]、[p1-main.py#9]，均未涉及 PostgreSQL 版本。

检索结果：
- 0.0164  p1-main.py#0  p1-main.py
- 0.0161  p1-main.py#7  p1-main.py
- 0.0159  p1-main.py#9  p1-main.py

耗时：0.8 秒

## 14. 限流窗口为什么用单调时钟而不是系统时钟？

根据材料，限流窗口用 `time.monotonic()` 而不是 `time.time()`，原因是避免系统时间被调整时窗口错乱 [p1-readme.md#15]。

材料中未发现与此结论冲突的内容。

检索结果：
- 0.0164  p1-readme.md#15  LLM 对话 API 服务 > 实现要点 > 7. 按 IP 限流
- 0.0161  p1-readme.md#16  LLM 对话 API 服务 > 实现要点 > 7. 按 IP 限流
- 0.0159  p1-main.py#9  p1-main.py

耗时：1.2 秒

## 15. 120 并发下异步端点两次实测分别是多少秒？

120 并发下异步端点两次实测分别是 **1.73 s** 和 **1.81 s** [p1-readme.md#10]。材料说明这两个值的差值属于测量噪声 [p1-readme.md#10]。

检索结果：
- 0.0328  p1-readme.md#10  LLM 对话 API 服务 > 实现要点 > 5. 同步 vs 异步：实测数据
- 0.0323  p1-readme.md#11  LLM 对话 API 服务 > 实现要点 > 5. 同步 vs 异步：实测数据
- 0.0159  p1-main.py#9  p1-main.py

耗时：1.4 秒

## 16. 为什么 120 并发的同步端点耗时是 4.70 秒，而不是 1.5 秒？

同步端点不是 1.5 秒，是因为 FastAPI 把同步端点丢进 anyio 的线程池执行，而线程池默认容量是 40（`anyio/_backends/_asyncio.py` 里的 `CapacityLimiter(40)`），多出来的请求只能排队分批 [p1-readme.md#10]。120 并发分成 3 批，理论耗时 4.5 s，实测 4.70 s [p1-readme.md#10]。

材料中未发现冲突。

检索结果：
- 0.0325  p1-readme.md#11  LLM 对话 API 服务 > 实现要点 > 5. 同步 vs 异步：实测数据
- 0.0325  p1-readme.md#10  LLM 对话 API 服务 > 实现要点 > 5. 同步 vs 异步：实测数据
- 0.0308  p1-readme.md#14  LLM 对话 API 服务 > 实现要点 > 6. 超时与错误处理

耗时：1.3 秒

## 17. P1 里哪些接口不限流，为什么？

根据材料，不限流的接口是 **`/health`、`/docs`、`/static`**，因为它们不以 `/chat` 开头，而限流中间件只处理 `GUARDED = ("/chat",)` 这些路径前缀 [p1-main.py#9]。原因：`/health` 要供监控高频调用，`/docs` 加载一次要请求四个资源（页面 + CSS + JS + openapi.json），拦它会让人打不开文档页 [p1-readme.md#15]。

检索结果：
- 0.0164  p1-main.py#9  p1-main.py
- 0.0161  p1-main.py#7  p1-main.py
- 0.0159  p1-readme.md#15  LLM 对话 API 服务 > 实现要点 > 7. 按 IP 限流

耗时：1.2 秒

## 18. P0 的多轮记忆是怎么实现的？

P0 的多轮记忆通过维护 messages 列表保存完整对话历史来实现：每轮把用户输入与助手完整回复都追加进去，从而实现跨轮次记忆 [p0-readme.md#4]。

材料中未发现相关冲突。

检索结果：
- 0.0164  p0-readme.md#4  LLM 多轮流式对话 CLI > 实现要点
- 0.0161  p0-readme.md#0  LLM 多轮流式对话 CLI
- 0.0159  p0-readme.md#1  LLM 多轮流式对话 CLI > 功能

耗时：1.0 秒

## 19. P1 用的 Redis 版本是多少？

根据现有材料无法回答。材料中未出现任何 Redis 版本信息；并且从导入与代码看，使用的是进程内 `defaultdict(deque)` 做限流存储，未见 Redis 相关配置 [p1-main.py#9][p1-main.py#0]。

检索结果：
- 0.0164  p1-main.py#9  p1-main.py
- 0.0161  p1-main.py#0  p1-main.py
- 0.0159  p1-main.py#7  p1-main.py

耗时：1.3 秒

## 20. P1 的 `/slow-sync` 在 60 并发下理论耗时和实测耗时分别是多少？

理论耗时 3.0 s，实测耗时 3.25 s [p1-readme.md#10]。

检索结果：
- 0.0325  p1-readme.md#11  LLM 对话 API 服务 > 实现要点 > 5. 同步 vs 异步：实测数据
- 0.0323  p1-main.py#9  p1-main.py
- 0.0315  p1-readme.md#10  LLM 对话 API 服务 > 实现要点 > 5. 同步 vs 异步：实测数据

耗时：1.1 秒

## 21. P1 流式接口出错时为什么不发 `[DONE]`？

出错时不会发 `[DONE]`，因为两个信号互斥，客户端据此区分「答完了」和「中途断了」[p1-readme.md#13]。

另外补充：流式端点生成器抛错时状态码已经发出去了（先发 `200 OK` 响应头），唯一的上报通道是往流里再写一条 `event: upstream_error` 消息[p1-readme.md#13]；代码中 `APITimeoutError` 分支只 yield `event: upstream_error\ndata: 模型服务超时，回答已中断\n\n`，不发 `[DONE]`[p1-main.py#7]。

检索结果：
- 0.0328  p1-readme.md#13  LLM 对话 API 服务 > 实现要点 > 6. 超时与错误处理
- 0.0317  p1-main.py#7  p1-main.py
- 0.0306  p1-main.py#4  p1-main.py

耗时：1.3 秒

## 22. P1 部署时为什么用 8000 端口而不是 80？

根据材料：国内服务器用 80 端口对公网提供 HTTP 服务需要 ICP 备案，所以演示走 8000 这类非标准端口 [p1-readme.md#21]。

检索结果：
- 0.0320  p1-readme.md#21  LLM 对话 API 服务 > 部署记录
- 0.0312  p1-readme.md#17  LLM 对话 API 服务 > 实现要点 > Docker 镜像
- 0.0309  p1-readme.md#11  LLM 对话 API 服务 > 实现要点 > 5. 同步 vs 异步：实测数据

耗时：1.1 秒

## 23. P1 的 API key 是怎么管理的？

P1 的 API key 管理方式如下：

1. **通过 `.env` 管理，`.env` 写入 `.gitignore`**，仓库中不存在明文密钥 [p1-readme.md#7]。
2. **`main.py` 只从环境变量读取**，代码中使用 `os.environ["DEEPSEEK_API_KEY"]` [p1-readme.md#7]。
3. 代码中通过 `load_dotenv()` 加载环境变量 [p1-main.py#1]，并分别在同步客户端 `OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")` 和异步客户端 `AsyncOpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")` 中使用该环境变量 [p1-main.py#1]。

未发现材料之间存在冲突。

检索结果：
- 0.0320  p1-readme.md#7  LLM 对话 API 服务 > 实现要点 > 3. 密钥不进版本库
- 0.0315  p1-main.py#0  p1-main.py
- 0.0313  p1-main.py#1  p1-main.py

耗时：1.6 秒

## 24. P1 源码里限流用的 `LIMIT` 和 `WINDOW` 常量分别是多少？

根据材料，`LIMIT = 20` [p1-main.py#9]，`WINDOW = 60` [p1-main.py#9]（单位：秒，见注释“窗口长度（秒）”）。

材料中另有一处提到“在本地把 `LIMIT` 临时设成 3 跑通，再改回 20 部署上线” [p1-readme.md#16]，这属于本地验证时的临时值，与源码中定义的常量值 20 不构成数值冲突（正式取值仍为 20）。

检索结果：
- 0.0325  p1-main.py#10  p1-main.py
- 0.0325  p1-main.py#9  p1-main.py
- 0.0317  p1-readme.md#16  LLM 对话 API 服务 > 实现要点 > 7. 按 IP 限流

耗时：1.3 秒

## 25. P1 源码里每个 IP 的请求时间戳存在什么变量和数据结构里？

根据材料，每个 IP 的请求时间戳存在 `_hits` 变量里，数据结构是 `defaultdict(deque)`，即每个 IP 对应一个 `deque`（双端队列），存放该 IP 最近几次请求的时间 [p1-main.py#9]。注释明确说明：`_hits = defaultdict(deque)   # {IP: deque([该 IP 最近几次请求的时间])}` [p1-main.py#9]。

材料中未出现冲突。

检索结果：
- 0.0325  p1-main.py#9  p1-main.py
- 0.0304  p1-readme.md#15  LLM 对话 API 服务 > 实现要点 > 7. 按 IP 限流
- 0.0288  p1-main.py#4  p1-main.py

耗时：1.3 秒

## 26. P1 源码里 `/chat` 端点遇到 `APITimeoutError` 和 `APIConnectionError` 分别返回什么状态码？

根据材料回答：

- `/chat` 端点遇到 `APITimeoutError` 时返回 **504**，detail 为“模型服务响应超时”[p1-main.py#3]
- `/chat` 端点遇到 `APIConnectionError` 时返回 **502**，detail 为“无法连接模型服务”[p1-main.py#3]

材料中没有冲突。

检索结果：
- 0.0325  p1-main.py#3  p1-main.py
- 0.0315  p1-readme.md#12  LLM 对话 API 服务 > 实现要点 > 6. 超时与错误处理
- 0.0315  p1-readme.md#13  LLM 对话 API 服务 > 实现要点 > 6. 超时与错误处理

耗时：1.1 秒

## 27. P1 源码里 `/chat/stream/async` 用的是哪个客户端对象？

P1 源码里 `/chat/stream/async` 使用的是异步客户端对象 `aclient`（AsyncOpenAI）[p1-main.py#6]。

检索结果：
- 0.0328  p1-main.py#6  p1-main.py
- 0.0317  p1-main.py#4  p1-main.py
- 0.0311  p1-main.py#9  p1-main.py

耗时：1.1 秒

## 28. P1 源码里 `/slow` 和 `/slow-sync` 哪个是同步实现？

根据材料，`/slow-sync` 是同步实现：它用 `def slow_sync()` 并调用 `time.sleep(1.5)` [p1-main.py#9]。而 `/slow` 是异步实现：`async def slow()` 并 `await asyncio.sleep(1.5)` [p1-main.py#9]。材料中二者不冲突。

检索结果：
- 0.0328  p1-main.py#9  p1-main.py
- 0.0320  p1-readme.md#11  LLM 对话 API 服务 > 实现要点 > 5. 同步 vs 异步：实测数据
- 0.0318  p1-readme.md#10  LLM 对话 API 服务 > 实现要点 > 5. 同步 vs 异步：实测数据

耗时：1.3 秒

## 29. P0 源码里用什么函数加载 `.env`？

根据材料，`p0-chat_cli.py` 源码里用 `load_dotenv()` 加载 `.env` [p0-chat_cli.py#0]。

检索结果：
- 0.0328  p0-chat_cli.py#0  p0-chat_cli.py
- 0.0320  p0-readme.md#2  LLM 多轮流式对话 CLI > 快速开始
- 0.0318  p0-readme.md#3  LLM 多轮流式对话 CLI > 技术栈

耗时：1.3 秒

## 30. P0 源码里从流式响应的每个 chunk 里怎么取文本？

从流式响应的每个 chunk 里取文本的方式是：访问 `chunk.choices[0].delta.content`，并先判空再拼接。[p0-readme.md#4] [p0-chat_cli.py#1]

具体代码中：
- `content = chunk.choices[0].delta.content`
- `if content:` 判空后才 `print` 并累加到 `reply` [p0-chat_cli.py#1]

材料中未发现相关冲突。

检索结果：
- 0.0328  p0-readme.md#4  LLM 多轮流式对话 CLI > 实现要点
- 0.0323  p0-chat_cli.py#1  p0-chat_cli.py
- 0.0159  p0-chat_cli.py#0  p0-chat_cli.py

耗时：1.4 秒

## 31. P1 源码里限流超限时返回的 JSON 响应里 `detail` 字段是什么？

`detail` 字段是 `f"请求过于频繁，请 {wait} 秒后再试"`，其中 `wait = int(WINDOW - (now - q[0])) + 1` [p1-main.py#10]；响应同时带 `status_code=429` 和 `headers={"Retry-After": str(wait)}` [p1-main.py#10]。

材料中另有 README 说明：按客户端 IP 做 60 秒滑动窗口，窗口内超过 20 次返回 `429`，并带 `Retry-After` 头 [p1-readme.md#15]——与源码在状态码和响应头层面一致，但 README 未给出 `detail` 的具体文案，未发现冲突。

检索结果：
- 0.0325  p1-main.py#10  p1-main.py
- 0.0306  p1-readme.md#15  LLM 对话 API 服务 > 实现要点 > 7. 按 IP 限流
- 0.0298  p1-main.py#3  p1-main.py

耗时：1.8 秒

## 32. P1 源码里 `GUARDED` 变量限制哪些路径？

根据材料，`GUARDED` 变量的值为 `("/chat",)`，即限制路径前缀为 `/chat` 的请求 [p1-main.py#9]。

检索结果：
- 0.0328  p1-main.py#9  p1-main.py
- 0.0161  p1-bench.py#0  p1-bench.py
- 0.0159  p1-main.py#0  p1-main.py

耗时：1.3 秒

## 33. P1 源码里 `/chat/stream` 出错时 `yield` 的事件名是什么？

出错时 `yield` 的事件名是 `upstream_error`。[p1-main.py#5] [p1-main.py#8]

检索结果：
- 0.0325  p1-main.py#4  p1-main.py
- 0.0325  p1-main.py#5  p1-main.py
- 0.0315  p1-main.py#8  p1-main.py

耗时：1.2 秒

## 34. P1 源码里 `bench.py` 用哪个库发 HTTP 请求？

根据材料，`bench.py` 使用 `urllib.request` 库发 HTTP 请求，具体调用为 `urllib.request.urlopen(URL).read()` [p1-bench.py#0]。

检索结果：
- 0.0320  p1-readme.md#3  LLM 对话 API 服务 > 项目结构
- 0.0315  p1-bench.py#0  p1-bench.py
- 0.0297  p1-main.py#1  p1-main.py

耗时：1.2 秒

## 35. P1 用的消息队列是什么？

根据现有材料无法回答。

材料中只出现了基于内存的 `defaultdict(deque)` 用于限流计数 [p1-main.py#9]，没有任何关于“消息队列”的定义或配置信息。根据我拿到的材料看不出来 P1 使用了什么消息队列。

检索结果：
- 0.0164  p1-main.py#7  p1-main.py
- 0.0161  p1-main.py#9  p1-main.py
- 0.0159  p1-main.py#5  p1-main.py

耗时：1.3 秒

## 36. P1 源码里有没有用到 Redis？

没有。我检查了材料 [p1-main.py#0] 和 [p1-main.py#9] 中的导入与代码，均未出现 Redis 相关导入或使用；[p1-main.py#0] 的导入项包括 os、time、asyncio、pathlib、dotenv、fastapi、pydantic、openai、collections 等，没有 redis。[p1-main.py#9] 中的限流实现用的是内存结构 `_hits = defaultdict(deque)`，也不是 Redis。[p1-main.py#0][p1-main.py#9]

检索结果：
- 0.0164  p1-main.py#0  p1-main.py
- 0.0161  p1-main.py#7  p1-main.py
- 0.0159  p1-main.py#9  p1-main.py

耗时：1.2 秒

## 37. P1 源码里有没有定义日志级别常量（如 `LOG_LEVEL`）？

没有。我检查了材料中的 p1-main.py（含 #7、#9 片段）和 p1-bench.py（#1），其中未出现 `LOG_LEVEL` 或类似日志级别常量的定义。

检索结果：
- 0.0164  p1-main.py#7  p1-main.py
- 0.0161  p1-main.py#9  p1-main.py
- 0.0159  p1-bench.py#1  p1-bench.py

耗时：1.3 秒

## 38. P0 源码里有没有 try/except 异常处理？

没有。我检查了材料 p0-chat_cli.py 的全部内容（#0 和 #1），源码中没有出现 try/except 异常处理结构。[p0-chat_cli.py#0][p0-chat_cli.py#1]

检索结果：
- 0.0164  p0-chat_cli.py#0  p0-chat_cli.py
- 0.0161  p0-chat_cli.py#1  p0-chat_cli.py
- 0.0159  p0-readme.md#3  LLM 多轮流式对话 CLI > 技术栈

耗时：1.3 秒

## 39. P1 源码里有没有用到连接池或数据库？

没有。我检查了材料中提供的 p1-main.py 片段（#0 的 import 区、#5 的 upstream_error/StreamingResponse 片段），其中没有数据库驱动或连接池相关的导入/定义；p1-bench.py 片段也未涉及。根据现有材料，P1 源码未使用连接池或数据库。[p1-main.py#0][p1-main.py#5][p1-bench.py#0]

注：这只是基于所给片段的判断，片段并非完整源码；若需对整份源码断言，需提供完整文件。

检索结果：
- 0.0164  p1-main.py#0  p1-main.py
- 0.0161  p1-bench.py#0  p1-bench.py
- 0.0159  p1-main.py#5  p1-main.py

耗时：1.7 秒

## 40. P1 源码里有没有 `WINDOW` 这个常量？

有。`WINDOW = 60` 定义在 [p1-main.py#9]，并在限流逻辑中用于判断窗口长度和计算等待时间 [p1-main.py#9][p1-main.py#10]。

检索结果：
- 0.0328  p1-main.py#10  p1-main.py
- 0.0323  p1-main.py#9  p1-main.py
- 0.0159  p1-main.py#0  p1-main.py

耗时：1.3 秒

## 41. P1 源码里有没有 `GUARDED` 常量？

有。`GUARDED = ("/chat",)`，定义在 [p1-main.py#9]，注释说明“只限制这些路径前缀”。

检索结果：
- 0.0328  p1-main.py#9  p1-main.py
- 0.0161  p1-main.py#0  p1-main.py
- 0.0159  p1-main.py#7  p1-main.py

耗时：1.3 秒
