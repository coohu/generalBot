google_search_api="AIzaSyB0yvUT2D5rgTEIc84xJMhZjqnW8C4srUY"
url = "https://relay.shengsuanyun.com/v1"
key = "8N9ievEPeJP2UAb-iJs2cKTb1eHGKq0zBO8WKd3U_wz3U6fD01izh-LDDSV0JYmofbkbImyEuOViIcGA_mW7NytQ"
model ={
    'embed':['text-embedding-v3'],
    'chat':['shengsuanyun/DeepSeek-R1','qwen-turbo'],
    'img':['Ali:qwen-vl-plus-latest'],
    'audio':['Ali:qwen-audio-turbo-latest']
}
secret_key = "HGKq0zBO8WKd3U_wz3U6fD01izh-65ed2fc5-6bd2-4673-97df-30831d9583f8"
dbURL = "mariadb+mariadbconnector://root:v@127.0.0.1:3306/xhs"
pgVector = "postgresql://postgres:v@localhost:5432/test"

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 300000
CACHE_TIMEOUT_SECONDS = 1800 
CACHE_CLEANUP_INTERVAL_SECONDS = 600
# docker run -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=v -e POSTGRES_DB=test -e POSTGRESQL_EXTRA_CONF="listen_addresses='*'" -v pgvector_data:/var/lib/postgresql/data  -p 5432:5432 pgvector/pgvector:0.8.0-pg17
# psql -h localhost -U postgres -d test







