# fastgpt-dify-adapter
dify外接fastgpt知识库的工具，功能主要是将Dify请求的RAG检索通过本代码转化为FASTGPT支持的检索请求。做了一层中转和适配。

使用方式参考：https://mp.weixin.qq.com/s/crQrneHZ0sT-c04YanofSw

## 生成随机 API Key

```shell
echo "sk-$(openssl rand -hex 16)"
echo "sk-$(openssl rand -base64 16 | tr -d '/+=')"
echo "sk-$(uuidgen | tr -d '-')"
echo "sk-$(date +%s | md5sum | cut -c1-32)"
echo "sk-$(echo $RANDOM$(date +%s) | sha256sum | cut -c1-32)"
# ADAPTER_API_KEY=sk-u52DLfEleq1Outn1q2Hgg
```
# **📌 `.adapter.env` 配置文件说明**
本文件用于配置 **FastGPT Dify 适配器** 的环境变量，所有运行时参数均可通过 `.adapter.env` 配置，无需修改代码。  
适用于 **Docker 部署** 和 **本地开发**，确保灵活性和可维护性。

## 快速配置

```shell
cp .env.example /path/to/FastGPT/deploy/docker/.adapter.env
```

this `docker-compose.yml` put in `/path/to/FastGPT/deploy/docker/docker-compose.yml` file or your runing docker-compose.yml file

like:

```yaml
  fastgpt-dify-adapter:
    container_name: fastgpt-dify-adapter
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "$PORT:$PORT"
    image: hotwa/fastgpt-dify-adapter:1.0.0
    env_file:
      - .adapter.env
    restart: unless-stopped
```

then restart docker-compose.yml service, then enjoy fastgpt fit dify.

---

## **📖 变量配置说明**
以下是所有可用的环境变量及其作用：

### **🔒 1. API 认证**
| 变量 | 说明 | 默认值 |
|------|------|-------|
| `ADAPTER_API_KEY` | 认证 API 请求的密钥，需匹配请求头中的 `Bearer Token` | **必填** |

📌 **示例：**
```ini
ADAPTER_API_KEY=sk-8f14e45fceea167a5a36dedd4bea2543
```

---

### **🌐 2. 服务器配置**
| 变量 | 说明 | 默认值 |
|------|------|-------|
| `PORT` | Flask 服务器运行端口 | `5500` |
| `GUNICORN_WORKERS` | Gunicorn 进程数（提升并发） | `2` |
| `GUNICORN_TIMEOUT` | Gunicorn 超时时间（秒） | `60` |

📌 **示例：**
```ini
PORT=5500
GUNICORN_WORKERS=4
GUNICORN_TIMEOUT=120
```

---

### **🤖 3. FastGPT 相关配置**
| 变量 | 说明                                                            | 默认值 |
|------|---------------------------------------------------------------|----|
| `FASTGPT_BASE_URL` | FastGPT API 地址                                                | `http://host.docker.internal:3000` |
| `FASTGPT_TIMEOUT` | FastGPT API 请求超时时间（秒）                                         | `30` |
| `DATASET_SEARCH_USING_EXTENSION` | 是否开启问题优化 (`true/false`)                                       | `true` |
| `DATASET_SEARCH_EXTENSION_MODEL` | 问题优化所使用的模型 (`GPT-4, Deepseek-chat, etc.`)                     | `Deepseek-chat` |
| `DATASET_SEARCH_EXTENSION_BG` | 问题优化的背景信息                                                     | （空） |
| `DATASET_SEARCH_USING_RERANK` | 是否使用 ReRank 重新排序 (`true/false`)                               | `true` |
| `DATASET_SEARCH_MODE` | 检索模式配置：embedding（语意检索）、fullTextRecall（全文检索）、mixedRecall（混合检索） | `embedding` |

📌 **示例：**
```ini
FASTGPT_BASE_URL=http://host.docker.internal:3000
FASTGPT_TIMEOUT=30
DATASET_SEARCH_USING_EXTENSION=true
DATASET_SEARCH_EXTENSION_MODEL=Deepseek-chat
DATASET_SEARCH_EXTENSION_BG=
DATASET_SEARCH_USING_RERANK=true
DATASET_SEARCH_MODE=embedding
```

---

### **📜 4. 日志 & 调试**
| 变量 | 说明 | 默认值 |
|------|------|-------|
| `LOG_LEVEL` | 日志级别 (`DEBUG, INFO, WARNING, ERROR, CRITICAL`) | `INFO` |

📌 **示例：**
```ini
LOG_LEVEL=DEBUG
```

---

## **🚀 `.env` 文件完整示例**
```ini
# =========================================
# 🔒 API 认证
# =========================================
API_KEY=sk-8f14e45fceea167a5a36dedd4bea2543

# =========================================
# 🌐 服务器配置
# =========================================
PORT=5500
GUNICORN_WORKERS=4
GUNICORN_TIMEOUT=120

# =========================================
# 🤖 FastGPT 相关配置
# =========================================
FASTGPT_BASE_URL=http://host.docker.internal:3000
FASTGPT_TIMEOUT=30
DATASET_SEARCH_USING_EXTENSION=true
DATASET_SEARCH_EXTENSION_MODEL=Deepseek-chat
DATASET_SEARCH_EXTENSION_BG=
DATASET_SEARCH_USING_RERANK=true
DATASET_SEARCH_MODE=embedding

# =========================================
# 📜 日志 & 调试
# =========================================
LOG_LEVEL=INFO
```

---

## **🔧 使用 `.env` 配置**
### **🔹 1. 在 Docker 中使用**
在 `docker-compose.yml` 中**自动加载 `.env` 文件**：
```yaml
version: '3'

services:
  fastgpt-dify-adapter:
    image: hotwa/fastgpt-dify-adapter:1.0.0
    env_file:
      - .env
    ports:
      - "${PORT}:${PORT}"
    restart: unless-stopped
```

---

### **🔹 2. 在 Python 代码中使用**
确保 `python-dotenv` 已安装：
```bash
pip install python-dotenv
```

然后，在 Flask 代码中加载 `.env`：
```python
from dotenv import load_dotenv
import os

# 加载 .env 文件
load_dotenv()

# 读取环境变量
API_KEY = os.getenv('API_KEY')
PORT = int(os.getenv('PORT', 5000))

print(f"API_KEY: {API_KEY}")
print(f"PORT: {PORT}")
```

---

## **🎯 结论**
✅ **所有配置均可通过 `.env` 进行管理，无需修改代码**  
✅ **适用于 Docker & 本地开发，增强灵活性**  
✅ **支持 API 认证、FastGPT 配置、日志级别、服务器参数**  

🚀 **现在，你可以快速配置和管理 FastGPT Dify 适配器！** 🚀
