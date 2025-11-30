from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
from typing import List, Dict, Any

from neo4j import GraphDatabase
import requests
import json
from config import Config


from fastapi.staticfiles import StaticFiles

# ======================
# 初始化 FastAPI 和 Neo4j
# ======================
app = FastAPI(
    title="乙烯环氧化催化剂知识图谱",
    description="基于 Neo4j 的科研知识图谱可视化系统"
)

driver = GraphDatabase.driver(
    Config.NEO4J_URI,
    auth=(Config.NEO4J_USER, Config.NEO4J_PASSWORD)
)

# ======================
# 旧的 Cypher 查询函数
# ======================
def run_cypher(query: str, params: Dict[str, Any] = None) -> List[Dict]:
    """执行 Cypher 查询并返回字典列表"""
    with driver.session() as session:
        result = session.run(query, params or {})
        return [record.data() for record in result]

# ======================
# 新的智能问答部分
# ======================
def generate_cypher_query(question: str):
    """使用DeepSeek API生成Cypher查询"""
    DEEPSEEK_API_URL = Config.DEEPSEEK_API_URL
    DEEPSEEK_API_KEY = Config.DEEPSEEK_API_KEY
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""你是一个Neo4j专家，请根据以下规则生成Cypher查询：
    知识图谱结构：
    - 节点标签：Node
    - 关键属性：name
    - 关系：各种催化、影响、促进等关系
    查询生成规则：
    1. 从问题中提取核心实体关键词
    2. 查找与关键词相关的节点和它们之间的关系
    示例：
    问题："银催化剂如何影响反应活性"
    生成："MATCH (n:Node)-[r]-(m:Node) WHERE n.name CONTAINS '银' OR m.name CONTAINS '活性' RETURN n, r, m"
    请为以下问题生成Cypher查询：
    问题：{question}"""

    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一个专业的Cypher查询生成助手，擅长从问题中提取关键实体。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5
    }

    response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data)
    cypher_query = response.json().get("choices")[0]["message"]["content"]
    return cypher_query.strip().replace('```', '')

def get_answer_from_kg(kg_records, question):
    """使用DeepSeek API结合知识图谱数据生成回答"""
    headers = {
        "Authorization": f"Bearer {Config.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""请根据以下知识图谱数据，专业且简洁地回答用户问题：
    [知识图谱数据]:
    {json.dumps(kg_records, indent=2, ensure_ascii=False)}
    [用户问题]:
    {question}
    请回答："""

    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一个材料科学领域的知识图谱分析助手。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5
    }

    response = requests.post(Config.DEEPSEEK_API_URL, headers=headers, json=data)
    answer = response.json().get("choices")[0]["message"]["content"].strip()
    return answer

# ======================
# 路由
# ======================
# 主页
@app.get("/", response_class=HTMLResponse)
async def get_frontend():
    """返回前端页面"""
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return f.read()

# 知识图谱页面
@app.get("/search.html", response_class=HTMLResponse)
async def get_search_page():
    with open("templates/search.html", "r", encoding="utf-8") as f:
        return f.read()

# 智能问答页面
@app.get("/question.html", response_class=HTMLResponse)
async def get_search_page():
    with open("templates/question.html", "r", encoding="utf-8") as f:
        return f.read()

# 挂载静态文件服务
app.mount("/static", StaticFiles(directory="static"), name="static")

# 获取全图数据
@app.get("/api/graph")
async def get_full_graph(limit: int = 300):
    """获取全图数据（限制节点数防卡顿）"""
    query = """
    MATCH (n)-[r]->(m)
    RETURN 
        n.name AS source,
        m.name AS target,
        type(r) AS relation
    LIMIT $limit
    """
    links = run_cypher(query, {"limit": limit})
    
    # 提取唯一节点名
    node_names = set()
    for link in links:
        node_names.add(link["source"])
        node_names.add(link["target"])
    
    nodes = [{"name": name} for name in node_names]
    return {"nodes": nodes, "links": links}

# 搜索包含关键词的子图
@app.get("/api/search")
async def search_subgraph(q: str = Query(..., min_length=1)):
    """搜索包含关键词的子图（模糊匹配）"""
    query = """
    MATCH (n)-[r]->(m)
    WHERE toLower(n.name) CONTAINS toLower($q) OR toLower(m.name) CONTAINS toLower($q)
    RETURN 
        n.name AS source,
        m.name AS target,
        type(r) AS relation
    LIMIT 100
    """
    links = run_cypher(query, {"q": q})
    
    node_names = set()
    for link in links:
        node_names.add(link["source"])
        node_names.add(link["target"])
    
    nodes = [{"name": name} for name in node_names]
    return {"nodes": nodes, "links": links}

# 智能问答接口
@app.get("/api/ask_question")
async def ask_question(q: str):
    try:
        # 第一步：生成Cypher查询
        cypher_query = generate_cypher_query(q)
        
        # 第二步：执行Cypher查询，获取知识图谱数据
        kg_records = run_cypher(cypher_query)
        
        # 第三步：生成回答
        answer = get_answer_from_kg(kg_records, q)
        
        return JSONResponse(content={"answer": answer})
    except Exception as e:
        return JSONResponse(content={"answer": f"Error: {str(e)}"}, status_code=500)

# 生命周期管理
@app.on_event("shutdown")
def close_db_connection():
    driver.close()
