import os
import json
import time
import requests
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask 应用
app = Flask(__name__)

# 读取环境变量
FASTGPT_BASE_URL = os.getenv('FASTGPT_BASE_URL', 'http://127.0.0.1:3000')
DATASET_SEARCH_USING_EXTENSION = os.getenv('DATASET_SEARCH_USING_EXTENSION', 'false').lower() == 'true'
DATASET_SEARCH_EXTENSION_MODEL = os.getenv('DATASET_SEARCH_EXTENSION_MODEL', 'gpt-4-mini')
DATASET_SEARCH_EXTENSION_BG = os.getenv('DATASET_SEARCH_EXTENSION_BG', '')
DATASET_SEARCH_USING_RERANK = os.getenv('DATASET_SEARCH_USING_RERANK', 'false').lower() == 'true'
DATASET_SEARCH_MODE = os.getenv('DATASET_SEARCH_MODE', 'embedding')
FASTGPT_TIMEOUT = int(os.getenv('FASTGPT_TIMEOUT', 30))  # FastGPT API 超时
API_KEY = os.getenv('API_KEY')  # 认证密钥

def validate_api_key(auth_header):
    """验证 API 密钥"""
    if not auth_header or not auth_header.startswith('Bearer '):
        return False
    api_key = auth_header.split(' ')[1]
    return API_KEY and api_key == API_KEY

@app.route('/retrieval', methods=['POST'])
def retrieval():
    start_time = time.time()
    client_ip = request.remote_addr
    logger.info(f'收到检索请求，IP: {client_ip}')

    # 验证 API 认证
    auth_header = request.headers.get('Authorization')
    if not validate_api_key(auth_header):
        logger.warning(f'API 认证失败，IP: {client_ip}')
        return jsonify({'error_code': 1002, 'error_msg': '授权失败'}), 403

    # 解析请求 JSON
    try:
        dify_request = request.get_json(force=True)
        logger.info(f'Dify 请求参数: {json.dumps(dify_request, ensure_ascii=False)}')
    except Exception as e:
        logger.error(f'JSON 解析失败: {str(e)}')
        return jsonify({'error_code': 400, 'error_msg': '请求 JSON 解析失败'}), 400

    # 提取参数
    knowledge_id = dify_request.get('knowledge_id')
    query = dify_request.get('query')
    retrieval_setting = dify_request.get('retrieval_setting', {})

    if not knowledge_id or not query:
        logger.error('缺少必要参数 knowledge_id 或 query')
        return jsonify({'error_code': 400, 'error_msg': '缺少必要参数'}), 400

    # 查询参数
    top_k = retrieval_setting.get('top_k', 5)
    score_threshold = retrieval_setting.get('score_threshold', 0.5)

    # 构建 FastGPT 请求
    fastgpt_request = {
        'datasetId': knowledge_id,
        'text': query,
        'limit': top_k * 500,
        'similarity': score_threshold,
        'searchMode': DATASET_SEARCH_MODE,
        'usingReRank': DATASET_SEARCH_USING_RERANK,
        'datasetSearchUsingExtensionQuery': DATASET_SEARCH_USING_EXTENSION,
        'datasetSearchExtensionModel': DATASET_SEARCH_EXTENSION_MODEL,
        'datasetSearchExtensionBg': DATASET_SEARCH_EXTENSION_BG
    }

    headers = {'Authorization': auth_header, 'Content-Type': 'application/json'}
    fastgpt_url = f"{FASTGPT_BASE_URL}/api/core/dataset/searchTest"
    
    # 发送请求（支持指数退避策略）
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(fastgpt_url, headers=headers, json=fastgpt_request, timeout=FASTGPT_TIMEOUT)
            if response.status_code == 200:
                fastgpt_response = response.json()
                logger.info(f'FastGPT 响应成功，耗时: {time.time() - start_time:.2f}s')
                return jsonify(format_fastgpt_response(fastgpt_response))
            
            elif response.status_code in {401, 403}:
                logger.warning(f'FastGPT API 认证失败，IP: {client_ip}')
                return jsonify({'error_code': 1002, 'error_msg': '授权失败'}), 403

            logger.error(f'FastGPT API 错误: {response.status_code}，内容: {response.text}')
            return jsonify({'error_code': 500, 'error_msg': f'FastGPT API 错误 {response.status_code}'}), 500

        except requests.exceptions.RequestException as e:
            logger.error(f'FastGPT API 请求失败: {str(e)}，第 {attempt+1} 次重试')
            time.sleep(2 ** attempt)  # 指数退避策略

    return jsonify({'error_code': 500, 'error_msg': 'FastGPT API 请求失败'}), 500

def format_fastgpt_response(fastgpt_response):
    """格式化 FastGPT 响应为 Dify 格式"""
    records = []
    data_list = fastgpt_response.get('data', {}).get('list', [])

    for item in data_list:
        if not isinstance(item, dict):
            logger.warning(f'跳过非字典类型数据: {item}')
            continue

        content = f"{item.get('q', '')}\n{item.get('a', '')}".strip()
        score = next((s.get('value', 0) for s in item.get('score', []) if isinstance(s, dict) and s.get('type') == 'embedding'), 0)

        records.append({
            'content': content,
            'score': score,
            'title': item.get('sourceName', 'Unknown'),
            'metadata': {
                'path': f"fastgpt://{item.get('collectionId', '')}",
                'source_id': item.get('sourceId', ''),
                'chunk_index': item.get('chunkIndex', 0)
            }
        })

    return {'records': records}

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
