import json
import os
from neo4j import GraphDatabase


class Neo4jImport:
    def __init__(self, uri, user, password):
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self._driver.close()

    def clear_database(self):
        """清空数据库中的所有数据"""
        with self._driver.session() as session:
            query = "MATCH (n) DETACH DELETE n"
            result = session.run(query)
            print("数据库已清空")

    def import_data(self, data, source_file=""):
        with self._driver.session() as session:
            success_count = 0
            error_count = 0

            for i, record in enumerate(data):
                try:
                    if not all(key in record for key in ['start_node', 'relationship', 'end_node']):
                        print(f"记录格式错误，跳过第 {i + 1} 条记录: {record}")
                        error_count += 1
                        continue

                    start_node = str(record['start_node']).strip()
                    relationship = str(record['relationship']).strip()
                    end_node = str(record['end_node']).strip()

                    # 跳过空节点或关系
                    if not start_node or not relationship or not end_node:
                        print(f"空节点或关系，跳过: {record}")
                        error_count += 1
                        continue

                    result = session.execute_write(self._create_relationship, start_node, relationship, end_node,
                                                   source_file)
                    if result:
                        success_count += 1
                    else:
                        error_count += 1

                except Exception as e:
                    print(f"处理记录失败 {i + 1}: {record}, 错误: {e}")
                    error_count += 1

            return success_count, error_count

    @staticmethod
    def _create_relationship(tx, start_node, relationship_type, end_node, source_file):
        try:
            # 清理关系类型，使其符合Neo4j命名规范
            relationship_type = relationship_type.replace("-", "_").replace(" ", "_").replace("/", "_")
            relationship_type = re.sub(r'[^a-zA-Z0-9_]', '_', relationship_type)

            # 如果关系类型以数字开头，添加前缀
            if relationship_type and relationship_type[0].isdigit():
                relationship_type = "REL_" + relationship_type

            query = (
                "MERGE (a:Entity {name: $start_node}) "
                "SET a.source = COALESCE(a.source, []) + $source_file "
                "MERGE (b:Entity {name: $end_node}) "
                "SET b.source = COALESCE(b.source, []) + $source_file "
                f"MERGE (a)-[r:{relationship_type}]->(b) "
                "SET r.source = COALESCE(r.source, []) + $source_file "
                "RETURN a.name, type(r), b.name"
            )

            result = tx.run(query,
                            start_node=start_node,
                            relationship_type=relationship_type,
                            end_node=end_node,
                            source_file=[source_file])
            return result.single() is not None

        except Exception as e:
            print(f"创建关系失败: {start_node} -[{relationship_type}]-> {end_node}, 错误: {e}")
            return False

    def create_constraints(self):
        """创建唯一约束以提高性能"""
        with self._driver.session() as session:
            try:
                # 为Entity节点的name属性创建唯一约束
                session.run("CREATE CONSTRAINT entity_name IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE")
                print("唯一约束创建成功")
            except Exception as e:
                print(f"创建约束失败: {e}")

    def get_statistics(self):
        """获取数据库统计信息"""
        with self._driver.session() as session:
            # 节点统计
            node_query = "MATCH (n) RETURN labels(n)[0] as label, count(n) as count"
            node_stats = session.run(node_query)

            # 关系统计
            rel_query = "MATCH ()-[r]->() RETURN type(r) as type, count(r) as count"
            rel_stats = session.run(rel_query)

            print("\n=== 数据库统计 ===")
            print("节点统计:")
            for record in node_stats:
                print(f"  {record['label']}: {record['count']}")

            print("关系统计:")
            for record in rel_stats:
                print(f"  {record['type']}: {record['count']}")
            print("=================\n")


def validate_json_file(file_path):
    """验证JSON文件格式"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError("JSON根元素不是数组")

        valid_records = []
        for i, record in enumerate(data):
            if not isinstance(record, dict):
                print(f"记录 {i + 1} 不是字典，跳过")
                continue

            if not all(key in record for key in ['start_node', 'relationship', 'end_node']):
                print(f"记录 {i + 1} 缺少必要字段，跳过: {record}")
                continue

            # 验证字段类型
            if not all(isinstance(record[key], str) for key in ['start_node', 'relationship', 'end_node']):
                print(f"记录 {i + 1} 字段类型错误，跳过: {record}")
                continue

            valid_records.append(record)

        return valid_records, len(data) - len(valid_records)

    except Exception as e:
        print(f"文件验证失败: {e}")
        return [], 0


import re

if __name__ == "__main__":
    # 配置项 - 更新为你的路径
    folder_path = r'C:\code\projects\AIPlus_Compitition\utils\json'
    uri = "bolt://localhost:7687"
    user = "neo4j"
    password = "Wx20041112"

    # 错误日志路径
    error_log_path = os.path.join(folder_path, "import_errors.txt")

    # 清空错误日志
    if os.path.exists(error_log_path):
        os.remove(error_log_path)

    # 扫描所有 .json 文件
    file_list = [f for f in os.listdir(folder_path) if f.endswith(".json") and f != "import_errors.txt"]
    print(f"共发现 {len(file_list)} 个 JSON 文件待导入。")

    if not file_list:
        print("未找到JSON文件，程序退出。")
        exit()

    # 初始化Neo4j连接
    neo4j_import = Neo4jImport(uri, user, password)

    try:
        # 清空数据库（可选，根据需要注释掉）
        # print("正在清空数据库...")
        # neo4j_import.clear_database()

        # 创建约束
        print("创建数据库约束...")
        neo4j_import.create_constraints()

        total_success = 0
        total_error = 0
        total_invalid = 0

        # 导入每个文件
        for filename in file_list:
            file_path = os.path.join(folder_path, filename)
            print(f"\n处理文件: {filename}")

            try:
                # 验证JSON文件
                valid_data, invalid_count = validate_json_file(file_path)
                total_invalid += invalid_count

                if not valid_data:
                    print(f"  ⚠️  文件无有效数据，跳过")
                    continue

                print(f"  有效记录: {len(valid_data)}, 无效记录: {invalid_count}")

                # 导入数据
                success_count, error_count = neo4j_import.import_data(valid_data, filename)
                total_success += success_count
                total_error += error_count

                print(f"  ✅ 成功: {success_count}, ❌ 失败: {error_count}")

                # 记录成功信息
                with open(error_log_path, "a", encoding="utf-8") as error_file:
                    if error_count == 0:
                        error_file.write(f"{filename}: 全部导入成功 ({success_count} 条记录)\n")
                    else:
                        error_file.write(
                            f"{filename}: 成功 {success_count}, 失败 {error_count}, 无效 {invalid_count}\n")

            except Exception as e:
                error_msg = f"{filename} 处理失败: {str(e)}"
                print(f"  ❌ {error_msg}")
                with open(error_log_path, "a", encoding="utf-8") as error_file:
                    error_file.write(error_msg + "\n")
                total_error += 1

        # 显示统计信息
        print(f"\n=== 导入完成 ===")
        print(f"总文件数: {len(file_list)}")
        print(f"总成功记录: {total_success}")
        print(f"总失败记录: {total_error}")
        print(f"总无效记录: {total_invalid}")

        # 获取数据库统计
        neo4j_import.get_statistics()

    except Exception as e:
        print(f"程序执行异常: {e}")
    finally:
        neo4j_import.close()
        print("Neo4j连接已关闭")