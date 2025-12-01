# 乙烯环氧化催化剂智能问答系统

## 目录
- [乙烯环氧化催化剂智能问答系统](#乙烯环氧化催化剂智能问答系统)
  - [目录](#目录)
  - [环境配置](#环境配置)
    - [Python依赖](#python依赖)
    - [Neo4j配置](#neo4j配置)
      - [本地配置Neo4j数据库](#本地配置neo4j数据库)
      - [云端数据库](#云端数据库)
  - [启动步骤](#启动步骤)

## 环境配置

### Python依赖
**1. 创建虚拟环境**
方法一：python原生环境创建虚拟环境
```pwl
# 1. 进入项目目录
cd project-folder # 这里的project-folder替换成项目路径

# 2. 创建虚拟环境（名字叫 ai_env）
python -m venv venv # 第二个venv是环境名称，可以自定义

# 3. 激活虚拟环境（根据情况选择一句执行）
# Windows:
venv\Scripts\activate
# macOS/Linux:
# source venv/bin/activate

# 4. 安装依赖
pip install -r requirements.txt
```
方法二：anaconda环境配置
略

### Neo4j配置
#### 本地配置Neo4j数据库
我们是用Neo4j数据库存储图的数据，如果希望在本地配置Neo4j数据库，请按照下面步骤下载Neo4j库：
1. 打开网址`https://neo4j.com/download-center/#desktop`
2. 找到 “Neo4j Desktop” 区块
3. 点击对应系统的版本（Windows / macOS）
4. 下载完成后，会得到一个安装文件
5. 双击运行
6. 打开desktop，点击create instance创建实例
7. 设置数据库账号密码并记住（这个之后代码会用到）
8. 进入虚拟环境
   ```pwl
   cd project-folder # 进入自己的项目目录
   venv\Scripts\activate # 激活虚拟环境 # 这一步要根据自己的配置来，和python依赖中创建虚拟环境的激活步骤一致
   ```
9. 修改config.py中的内容，账号密码改为第7步设置的，NEO4J_URI的值改为`"bolt://localhost:7687"`。
10. 运行json_to_neo4j.py将数据存入数据库
    ```pwl
    python -m utils.json_to_neo4j
    ```
11. 在浏览器网址栏输入`http://localhost:7474`可以进入本地数据库，在网页上看到本地的数据情况。


#### 云端数据库
使用云端数据库无需下载Neo4j，直接是用默认的Neo4j配置即可，当然，也可以自己配置云端数据库：
1. 打开`https://neo4j.com/product/auradb/`
创建账号之后可以创建instance，用创建后的密码替换掉config中的NEO4J_PASSWORD变量。
2. 点击connect -> 点击Query -> 点击左上角带有绿色点点的Instance开头的下拉菜单，点击Connection details，复制URI，替换掉config中的NEO4J_URI变量。
3. 运行json_to_neo4j.py将数据存入数据库
    ```pwl
    python -m utils.json_to_neo4j
    ```
4. 之后可以再次进入网址，点击connect，点击Query，可以查看云端数据库的情况。

## 启动步骤
首先启动后端
```pwl
# 1. 进入工作目录
cd project-folder
# 2. 激活虚拟环境
venv\Scripts\activate
# 3. 运行后端
uvicorn main:app --reload --port 5000 # 这个端口号如果已占用请改用空闲端口号
```
然后打开网址：`http://127.0.0.1:5000`，就可以进入我们的项目网页啦
