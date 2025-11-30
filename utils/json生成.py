import os
import json
import re
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# 替换为你的 DeepSeek API Key
API_KEY = "sk-633697d370c548748933aa1d8a6e1075"

# 文件路径
input_dir = r"D:\作业过渡\dachuang\file---text"
output_dir = r"D:\作业过渡\dachuang\json"
os.makedirs(output_dir, exist_ok=True)


def log_error(filename, message):
    error_file = os.path.join(output_dir, "ethylene_epoxidation_errors.txt")
    with open(error_file, mode="a", encoding="utf-8") as f:
        f.write(f"{filename} Error: {message}\n")


def call_with_messages(filename, content):
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    #提示词
    system_prompt = (
        "你是催化与材料科学领域的专家，专注于乙烯环氧化和银催化剂研究。"
        "从科学文献中提取关键实体和关系来构建知识图谱。\n\n"

        "关键要求：\n"
        "1. 最终输出必须是纯JSON数组"
        "2. 所有节点必须简洁（1–3个词）。反应参数的数值范围可以为5–15字符，例如“200–280°C”。"
        "3. 不要解释，不要markdown，只要纯JSON\n\n"
        "4. 所有关系必须围绕乙烯环氧化的核心性能：选择性（核心）与活性（核心）。"
        "5. 必须能处理推理类问题，将“原因—结果”“机理链条”转换为因果三元组。"
        "6. 必须能处理有关EO反应本身的描述，包括生成路径、副反应、机理、中间体、工艺条件与参数范围。"
        "7. 三元组必须具有连贯性，可以自然连接为知识链，不允许孤立关系。"
        "8. 所有Ag(111)晶面都是优于Ag(100)晶面，且Ag(111）晶面提高选择性，Ag(100）晶面降低选择性，这是事实，请建立这三个三元组关系"
        "9. 不用提取文章中的'晶面-选择性'这个关系"

        """
        "推理类输入需提取因果关系，例如：\n"
        {"start_node": "低温", "relationship": "抑制", "end_node": "完全氧化"}
        {"start_node": "完全氧化", "relationship": "降低", "end_node": "选择性"}
        {"start_node": "低温", "relationship": "提高", "end_node": "选择性"}

        制备催化剂的典型范围也需提取，例如：\n
        {"start_node": "操作温度", "relationship": "范围", "end_node": "250°C"}

        反应参数的典型范围也需提取，例如：
        {"start_node": "反应温度", "relationship": "范围", "end_node": "200–280°C"}
        {"start_node": "O2/C2H4", "relationship": "范围", "end_node": "0.06–0.12"}

        催化剂的典型特征参数也需提取，例如：
        {"start_node": "粒径", "relationship": "范围", "end_node": "50-500 nm"}

        必须包含的基础关系：
        {"start_node": "Ag催化剂", "relationship": "影响", "end_node": "选择性"}
        {"start_node": "Ag催化剂", "relationship": "决定", "end_node": "活性"}
        {"start_node": "Ag", "relationship": "催化", "end_node": "环氧乙烷"}
        """

        "最终输出只允许为纯JSON数组。自动修复三元组字段名，避免模型输出错误字段导致数据被跳过。"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"从以下文本中提取乙烯环氧化和银催化剂相关的知识图谱关系：\n\n{content}"}
    ]

    payload = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": 0.3,  # 降低温度以提高一致性
        "response_format": {"type": "json_object"}  # 要求JSON格式输出
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        content_str = data["choices"][0]["message"]["content"].strip()

        # 直接解析JSON响应
        try:
            parsed_content = json.loads(content_str)

            # 确保是列表格式
            if isinstance(parsed_content, dict):
                # 如果返回的是对象，尝试提取数组
                for key, value in parsed_content.items():
                    if isinstance(value, list):
                        parsed_content = value
                        break
                else:
                    # 如果没有找到数组，创建默认结构
                    parsed_content = [parsed_content]

            # 验证每个元素的格式
            validated_content = []
            for item in parsed_content:
                if (isinstance(item, dict) and
                        "start_node" in item and
                        "relationship" in item and
                        "end_node" in item):
                    # 清理节点名称，确保简洁
                    clean_item = {
                        "start_node": clean_node_name(item["start_node"]),
                        "relationship": clean_relationship(item["relationship"]),
                        "end_node": clean_node_name(item["end_node"])
                    }
                    validated_content.append(clean_item)

            if not validated_content:
                raise ValueError("未提取到有效的关系")

            # 添加必须包含的银催化剂关系
            required_relation = {
                "start_node": "Ag",
                "relationship": "催化",
                "end_node": "环氧乙烷"
            }
            if required_relation not in validated_content:
                validated_content.append(required_relation)

            json_filename = filename.replace(".txt", ".json")
            output_path = os.path.join(output_dir, json_filename)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(validated_content, f, ensure_ascii=False, indent=2)
            print(f"{filename}: 成功提取 {len(validated_content)} 个关系")

        except json.JSONDecodeError as e:
            # 如果直接解析失败，尝试使用正则表达式提取
            json_match = re.search(r'(\[.*?\])', content_str, re.DOTALL)
            if json_match:
                json_text = json_match.group(1).replace('\n', '').replace('\r', '').strip()
                parsed_content = json.loads(json_text)
                # 保存文件...
            else:
                raise ValueError(f"无法解析JSON响应: {e}")

    except (KeyError, json.JSONDecodeError, ValueError) as e:
        print(f"{filename}: 解析响应失败: {e}")
        log_error(filename, f"解析失败: {str(e)}")
    except requests.exceptions.RequestException as e:
        print(f"{filename}: 请求失败: {e}")
        log_error(filename, f"请求失败: {str(e)}")


def clean_node_name(name):
    """清理节点名称，确保简洁"""
    if isinstance(name, str):
        # 移除多余空格和特殊字符
        name = re.sub(r'\s+', ' ', name.strip())
        # 限制长度（最多3个词）
        words = name.split()
        if len(words) > 3:
            name = ' '.join(words[:3])
    return name


def clean_relationship(rel):
    """清理关系名称"""
    if isinstance(rel, str):
        rel = rel.strip()
        # 使用标准化的关系名称
        standard_relations = {
            "促进": "促进", "催化": "催化", "影响": "影响", "增强": "增强",
            "抑制": "抑制", "降低": "降低", "包含": "包含", "负载": "负载",
            "依赖": "依赖", "调节": "调节", "被促进": "被促进", "被增强": "被增强"
        }
        return standard_relations.get(rel, rel)
    return rel


def process_file(filename):
    file_path = os.path.join(input_dir, filename)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()

        if not content:
            print(f"{filename}: 文件内容为空")
            log_error(filename, "内容为空")
            return

        # 如果内容过长，截取前80000字符（避免API限制）
        if len(content) > 80000:
            content = content[:80000] + "...[内容截断]"

        call_with_messages(filename, content)

    except Exception as e:
        print(f"{filename}: 读取或处理异常: {e}")
        log_error(filename, str(e))


def validate_json_files():
    """验证生成的JSON文件格式"""
    json_files = [f for f in os.listdir(output_dir) if f.endswith('.json')]
    valid_count = 0

    for json_file in json_files:
        try:
            with open(os.path.join(output_dir, json_file), 'r', encoding='utf-8') as f:
                data = json.load(f)

            if isinstance(data, list) and len(data) > 0:
                valid_count += 1
            else:
                print(f"警告: {json_file} 格式异常")

        except Exception as e:
            print(f"错误: 验证 {json_file} 失败: {e}")

    print(f"JSON文件验证完成: {valid_count}/{len(json_files)} 个文件有效")


if __name__ == "__main__":
    txt_files = [f for f in os.listdir(input_dir) if f.lower().endswith(".txt")]

    if not txt_files:
        print("未找到 .txt 文件")
    else:
        print(f"找到 {len(txt_files)} 个文本文件，开始处理...")

        max_workers = min(4, len(txt_files))  # 减少线程数避免API限制
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process_file, file) for file in txt_files]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"线程执行异常: {e}")

    # 验证生成的文件
    validate_json_files()
    print("处理完成！")