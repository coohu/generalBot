# generalBot
### 宝特将军，不是一般的Bot。


### 安装
1. python >= 3.12       https://www.python.org/downloads/
2. mariadb >= 11.7.2    https://mariadb.org/download/
3. 下载代码
```
git clone https://github.com/coohu/generalBot.git
cd generalBot
```
5. 配置开发环境
```
python -m venv pcenv
pcenv\Scripts\Activate.ps1
pip install -r requirements.txt
```
6. 填写数据库账户和名称

./db/db.py
```
c={
    "MARIADB_URL":"mariadb+mariadbconnector://<数据库用户>:<数据库密码>@127.0.0.1:3306/<数据库名>",
}
```
创建名为“rpa”的数据库，名称要与./db/db.py 文件中的<数据库名>一样。
```
mariadb.exe -u root -p -e "CREATE DATABASE rpa;"

```
7. 登录微信，并让微信窗口在桌面，运行程序。
```
python main.py contact
```

其中 contact 是要执行的命令， 有['contact', 'post', 'search', 'chat'] 四种可选。