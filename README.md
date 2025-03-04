## poe-to-gpt
一个转换器，可以将 POE 提供的 API 令牌转换为 OpenAI 的 API 格式，从而使依赖于 OpenAI API 的其他应用程序可以使用 POE 的 API。

这是一个工具，将 Poe官方网站提供的 API 密钥转换为兼容的 OpenAI API 密钥。它使 Poe API 密钥可以与依赖于 OpenAI API 密钥的工具一起使用。开发此工具的主要原因是为中国大陆用户提供便利和稳定性，因为他们发现订阅和充值 OpenAI API 不太方便。

### 特点
- 支持 LinuxDO OAuth 登录认证
- 支持多用户管理和权限控制
- 支持自定义 API 访问令牌
- 支持用户状态管理（启用/禁用）
- 管理员面板用于用户管理
- 连接池优化的数据库处理
- Docker 支持

### 先决条件
- PostgreSQL 数据库
- LinuxDO OAuth 应用程序凭据
- POE 订阅者 API 密钥

### 安装

1. 克隆仓库：
```
git clone https://github.com/formzs/poe-to-gpt.git
cd poe-to-gpt/
```

2. 从 requirements.txt 安装依赖项：
```
pip install -r requirements.txt
```

3. 在项目的根目录中创建配置文件。指令已写在注释中：
```
cp config.example.toml config.toml
vim config.toml
```

4. 启动项目：
```
# 默认运行在端口 3700
python app.py
```

#### Docker （推荐）
```
cp config.example.toml config.toml
vim config.toml
# 构建并启动容器，默认运行在端口 3700
docker-compose up -d
```

### 配置反向代理真实 IP
如果您在 Docker 容器中运行此服务并通过反向代理（如 Nginx）访问，默认情况下日志会显示 Docker 网桥 IP（172.17.0.1）而不是实际客户端 IP。

要在日志中显示真实客户端 IP，请确保您的反向代理正确转发以下头信息：
- X-Forwarded-For
- X-Real-IP

这些头信息在默认配置中已启用。服务配置为信任来自本地主机（127.0.0.1）和 Docker 桥接网络（172.17.0.1）的请求头。

### 使用

请查看 [OpenAI 文档](https://platform.openai.com/docs/api-reference/chat/create) 以获取有关如何使用 ChatGPT API 的更多详细信息。

只需在您的代码中将 `https://api.openai.com` 替换为 `http://localhost:3700` 即可开始使用。
> 注意：请务必输入自定义 API 密钥（对应字段为 `config.toml` 中的 `accessTokens` ）

支持的路由：
- /chat/completions
- /v1/chat/completions

## 支持的模型参数（对应poe上机器人名称）。
> 传参可忽略大小写

Assistant

GPT-3.5-Turbo

GPT-3.5-Turbo-16k


GPT-3.5-Turbo-lnstruct


GPT-4o


GPT-4o-128k


GPT-4o-Mini


GPT-4o-Mini-128k


ChatGPT-4o-Latest


ChatGPT-4o-Latest-128k


GPT-4o-Aug-128k


o1


o1-mini


o1-preview


Claude-3.5-Sonnet


Claude-3.5-Sonnet-200k


Claude-3.5-Haiku


Claude-3.5-Haiku-200k


Claude-3.5-Sonnet-June


Claude-3.5-Sonnet-June-200k


Claude-3-opus


Claude-3-opus-200k


Claude-3-Sonnet


Claude-3-Sonnet-200k


Claude-3-Haiku


Claude-3-Haiku-200k


Gemini-2.0-Flash


Gemini-1.5-Pro


Gemini-1.5-Pro-Search


Gemini-1.5-Pro-128k


Gemini-1.5-Pro-2M


Gemini-1.5-Flash


Gemini-1.5-Flash-Search


Gemini-1.5-Flash-128k


Gemini-1.5-Flash-1M


Grok-beta


Qwen-QwQ-32b-preview


Qwen-2.5-Coder-32B-T


Qwen-2.5-72B-T


Llama-3.1-405B


Llama-3.1-405B-T


Llama-3.1-405B-FP16


Llama-3.1-405B-FW-128k


Llama-3.1-70B


Llama-3.1-70B-FP16


Llama-3.1-70B-T-128k


Llama-3.1-70B-FW-128k


Llama-3.1-8B


Llama-3.1-8B-FP16


Llama-3.1-8B-T-128k


DALL-E-3


StableDiffusionXL


StableDiffusion3.5-T


StableDiffusion3.5-L


StableDiffusion3


SD3-Turbo


FLUX-pro


FLUX-pro-1.1


FLUX-pro-1.1-T


FLUX-pro-1.1-ultra


FLUX-schnell


FLUX-dev


Luma-Photon


Luma-Photon-Flash


Playground-v3


Ideogram-v2


Imagen3


Imagen3-Fast


## 鸣谢
- https://github.com/juzeon/poe-openai-proxy
- https://developer.poe.com/server-bots/accessing-other-bots-on-poe
