import tkinter as tk
from tkinter import scrolledtext
from neo4j import GraphDatabase
import requests
import json

# DeepSeek API 配置（你可以外部读取）
DEEPSEEK_API_KEY = "sk-633697d370c548748933aa1d8a6e1075"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# Neo4j 配置
NEO4J_URI = "neo4j://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "Wx20041112"

# 获取Cypher查询
def get_query(question):
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""你是一个Neo4j专家，请根据以下规则生成Cypher查询：
1. 知识图谱的节点类型为Node，关键属性是name
2. 需要搜索从主节点出发和指向主节点的所有关系
3. 只允许在WHERE子句中使用一个变量

请为以下问题生成Cypher查询（仅返回代码，不要解释）：
问题：{question}"""

    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一个专业的Cypher查询生成助手。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3
    }

    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        cypher_query = response.json()["choices"][0]["message"]["content"].strip()

        # 处理```包裹的代码
        if '```' in cypher_query:
            cypher_query = cypher_query.split('```')[1].strip().replace('cypher\n', '')
        return cypher_query
    except Exception as e:
        return f"生成Cypher查询失败：{str(e)}"


# 执行Cypher查询
def run_cypher_query(query):
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        with driver.session() as session:
            result = session.run(query)
            return [record.data() for record in result]
    except Exception as e:
        return f"查询图谱失败：{str(e)}"
    finally:
        driver.close()

# 基于图谱生成答案
def answer_question(kg_records, question):
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""请根据以下知识图谱数据，专业且简洁地回答用户问题：

【知识图谱数据】:
{json.dumps(kg_records, indent=2, ensure_ascii=False)}

【用户问题】:
{question}

要求：
1. 如果数据与问题相关，直接引用数据回答
2. 保持回答客观，不要编造信息
3. 用中文回答"""

    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一个材料科学领域的知识图谱分析助手。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5
    }

    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=15)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"生成回答失败：{str(e)}"

# GUI 界面逻辑
def on_submit():
    question = input_box.get()
    if not question.strip():
        output_box.insert(tk.END, "请输入问题\n")
        return

    output_box.insert(tk.END, f"\n【问题】：{question}\n")
    output_box.insert(tk.END, "生成Cypher查询中...\n")
    window.update()

    cypher = get_query(question)
    output_box.insert(tk.END, f"【Cypher查询】：{cypher}\n")

    window.update()
    kg_data = run_cypher_query(cypher)
    output_box.insert(tk.END, "已获取图谱数据，生成回答中...\n")
    window.update()

    answer = answer_question(kg_data, question)
    output_box.insert(tk.END, f"【回答】：{answer}\n\n")
    output_box.see(tk.END)

# 创建窗口
window = tk.Tk()
window.title("图谱问答系统（RAG）")
window.geometry("800x600")

# 输入框
tk.Label(window, text="请输入问题：").pack()
input_box = tk.Entry(window, width=100)
input_box.pack()

# 提交按钮
submit_button = tk.Button(window, text="提交问题", command=on_submit)
submit_button.pack()

# 输出框
output_box = scrolledtext.ScrolledText(window, wrap=tk.WORD, width=100, height=30)
output_box.pack()

# 启动窗口
window.mainloop()