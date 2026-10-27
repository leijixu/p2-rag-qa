# LLM 多轮流式对话 CLI

一个从零实现的命令行大模型对话助手，支持逐字流式输出与多轮上下文记忆。

## 功能

- 逐字实时输出（流式渲染）
- 多轮对话，模型可记忆前文
- 输入 `exit` 退出

## 快速开始

1. 安装依赖

   ```powershell
   uv sync
   ```

2. 在项目根目录新建 `.env`，写入你的密钥

   ```
   DEEPSEEK_API_KEY=sk-你的key
   ```

3. 运行

   ```powershell
   uv run python src/chat_cli.py
   ```

## 技术栈

Python · openai SDK · python-dotenv · uv · DeepSeek API

## 实现要点

- 流式响应返回的是 `Stream` 对象，需迭代 `chunk.choices[0].delta.content`；
  首尾 chunk 的 content 可能为空字符串或 None，拼接前必须判空
- 维护 messages 列表保存完整对话历史，每轮把用户输入与助手完整回复都追加进去，
  实现跨轮次记忆
- 密钥通过 .env 管理并加入 .gitignore，避免敏感信息进入版本库
