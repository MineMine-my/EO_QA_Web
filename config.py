import os

class Config:
    DEEPSEEK_API_KEY = "sk-633697d370c548748933aa1d8a6e1075"
    DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
    NEO4J_URI = "bolt://localhost:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "3401032005August"
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    OUTPUT_FOLDER = os.path.join(os.getcwd(), 'outputs')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB