# 小红书助手
### 小红书运维助手


#### 安装
1. python >= 3.12       https://www.python.org/downloads/
2. docker
3. 配置开发环境
```
cp env.py.example env.py
python -m venv pcenv
pcenv\Scripts\Activate.ps1
pip install -r requirements.txt

docker volume create pgvector_data

docker run -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=v -e POSTGRES_DB=test -e POSTGRESQL_EXTRA_CONF="listen_addresses='*'" -v pgvector_data:/var/lib/postgresql/data  -p 5432:5432 pgvector/pgvector:0.8.0-pg17

```
#### 运行
修改env.py文件，添加必要的 api_Key
```
python main.py
```

#### 有用的资源
https://github.com/microsoft/graphrag

https://github.com/run-llama/llama_index

https://github.com/tomasonjo/diffbot-kg-chatbot

https://github.com/mem0ai/mem0

https://milvus.io/zh

https://neo4j.com/docs/

https://tcnqigfvmci2.feishu.cn/wiki/GhiQwgakIizyyOkjAxGcWeyonkd

https://github.com/JoeanAmier/XHS-Downloader

https://github.com/SciPhi-AI/R2R

#### 联网搜索资源

