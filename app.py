import os
import json
import time
import requests
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

app = Flask(__name__)

# 从环境变量获取FastGPT基础URL和问题优化配置
FASTGPT_BASE_URL = os.getenv('FASTGPT_BASE_URL', 'http://127.0.0.1:3000')
DATASET_SEARCH_USING_EXTENSION = os.getenv('DATASET_SEARCH_USING_EXTENSION', 'false').lower() == 'true'
DATASET_SEARCH_EXTENSION_MODEL = os.getenv('DATASET_SEARCH_EXTENSION_MODEL', 'gpt-4-mini')
DATASET_SEARCH_EXTENSION_BG = os.getenv('DATASET_SEARCH_EXTENSION_BG', '')
DATASET_SEARCH_USING_RERANK = os.getenv('DATASET_SEARCH_USING_RERANK', 'false').lower() == 'true'

@app.route('/retrieval', methods=['POST'])
def retrieval():
    logger.info('收到检索请求')
    # 验证Authorization头
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        logger.error('无效的Authorization头格式')
        return jsonify({
            'error_code': 1001,
            'error_msg': '无效的 Authorization 头格式。预期格式为 \'Bearer \'。'
        }), 403
    
    # 获取API密钥
    api_key = auth_header.split(' ')[1]
    # 这里可以添加API密钥验证逻辑
    # 简单示例：检查是否与环境变量中的API_KEY匹配
    expected_api_key = os.getenv('API_KEY')
    if expected_api_key and api_key != expected_api_key:
        logger.error(f'API密钥验证失败: {api_key}')
        return jsonify({
            'error_code': 1002,
            'error_msg': '授权失败'
        }), 403
    
    # 检查Content-Type请求头
    content_type = request.headers.get('Content-Type', '')
    logger.info(f'请求Content-Type: {content_type}')
    
    # 如果没有Content-Type，认为是验证请求
    if not content_type:
        logger.info('收到验证请求')
        # 构建一个简单的FastGPT API请求来验证连接
        headers = {
            'Authorization': auth_header,
            'Content-Type': 'application/json'
        }
        
        try:
            # 调用FastGPT API进行验证
            response = requests.get(
                f'{FASTGPT_BASE_URL}/api/core/dataset/list',
                headers=headers,
                timeout=(5, 30)
            )
            
            # 检查响应状态码和响应内容
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    logger.info('json数据: {json.dumps(response_data, ensure_ascii=False)}')
                    if response_data.get('code') != 200:
                        logger.error('FastGPT API密钥验证失败')
                        return jsonify({
                            'error_code': 1002,
                            'error_msg': '授权失败'
                        }), 403
                    logger.info('API验证成功')
                    return jsonify({'message': 'API验证成功'}), 200
                except Exception as e:
                    error_msg = f'FastGPT响应解析失败: {str(e)}'
                    logger.error(error_msg)
                    return jsonify({
                        'error_code': 500,
                        'error_msg': error_msg
                    }), 500
            elif response.status_code == 401 or response.status_code == 403:
                logger.error('API密钥验证失败')
                return jsonify({
                    'error_code': 1002,
                    'error_msg': '授权失败'
                }), 403
            else:
                error_msg = f'API验证失败: 状态码={response.status_code}'
                logger.error(error_msg)
                return jsonify({
                    'error_code': 500,
                    'error_msg': error_msg
                }), 500
                
        except requests.exceptions.RequestException as e:
            error_msg = f'API连接失败: {str(e)}'
            logger.error(error_msg)
            return jsonify({
                'error_code': 500,
                'error_msg': error_msg
            }), 500
    
    # 检查Content-Type是否为application/json
    if not content_type.startswith('application/json'):
        error_msg = f'不支持的Content-Type: {content_type}，需要application/json'
        logger.error(error_msg)
        return jsonify({
            'error_code': 400,
            'error_msg': error_msg
        }), 400

    # 解析Dify请求
    try:
        try:
            dify_request = request.json
        except Exception as e:
            error_msg = f'JSON解析失败: {str(e)}'
            logger.error(error_msg)
            return jsonify({
                'error_code': 400,
                'error_msg': error_msg
            }), 400

        logger.info(f'Dify请求参数: {json.dumps(dify_request, ensure_ascii=False)}')
        
        knowledge_id = dify_request.get('knowledge_id')
        query = dify_request.get('query')
        retrieval_setting = dify_request.get('retrieval_setting', {})
        
        # 验证必要参数
        if not knowledge_id:
            logger.error('缺少knowledge_id参数')
            return jsonify({
                'error_code': 2001,
                'error_msg': '知识库不存在'
            }), 400
        
        if not query:
            logger.error('缺少query参数')
            return jsonify({
                'error_code': 400,
                'error_msg': '查询不能为空'
            }), 400
        
        # 获取检索设置
        top_k = retrieval_setting.get('top_k', 5)
        score_threshold = retrieval_setting.get('score_threshold', 0.5)
        
        # 构建FastGPT搜索测试请求
        fastgpt_request = {
            'datasetId': knowledge_id,  # 使用knowledge_id作为datasetId
            'text': query,
            'limit': top_k * 500,
            'similarity': score_threshold,
            'searchMode': 'embedding',
            'usingReRank': DATASET_SEARCH_USING_RERANK,
            'datasetSearchUsingExtensionQuery': DATASET_SEARCH_USING_EXTENSION,
            'datasetSearchExtensionModel': DATASET_SEARCH_EXTENSION_MODEL,
            'datasetSearchExtensionBg': DATASET_SEARCH_EXTENSION_BG
        }
        logger.info(f'FastGPT请求参数: {json.dumps(fastgpt_request, ensure_ascii=False)}')
        
        # 调用FastGPT API，使用请求头中的token作为FastGPT的API密钥
        headers = {
            'Authorization': auth_header,  # 直接使用请求头中的Authorization
            'Content-Type': 'application/json'
        }
        
        logger.info(f'开始调用FastGPT API: {FASTGPT_BASE_URL}/api/core/dataset/searchTest')
        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                response = requests.post(
                    f'{FASTGPT_BASE_URL}/api/core/dataset/searchTest',
                    headers=headers,
                    json=fastgpt_request,
                    timeout=(5, 30)  # 连接超时5秒，读取超时30秒
                )
                break
            except requests.exceptions.RequestException as e:
                retry_count += 1
                if retry_count == max_retries:
                    error_msg = f'FastGPT API连接失败: {str(e)}'
                    logger.error(error_msg)
                    return jsonify({
                        'error_code': 500,
                        'error_msg': error_msg
                    }), 500
                logger.warning(f'FastGPT API请求失败，正在进行第{retry_count}次重试')
                time.sleep(1)  # 重试前等待1秒
        
        # 检查FastGPT响应
        if response.status_code != 200:
            try:
                error_response = response.json()
                if error_response.get('code') == 514:
                    logger.error('FastGPT API密钥验证失败')
                    return jsonify({
                        'error_code': 1002,
                        'error_msg': '授权失败'
                    }), 403
            except:
                pass
            
            error_msg = f'FastGPT API错误: 状态码={response.status_code}, 响应内容={response.text}'
            logger.error(error_msg)
            return jsonify({
                'error_code': 500,
                'error_msg': error_msg
            }), 500
        
        fastgpt_response = response.json()
        logger.info(f'FastGPT响应数据: {json.dumps(fastgpt_response, ensure_ascii=False)}')
        
        # 转换FastGPT响应为Dify格式
        records = []
        data_list = fastgpt_response.get('data', {}).get('list', [])
        logger.info(f'FastGPT返回数据项数量: {len(data_list)}')
        # logger.info(f'FastGPT返回数据类型: {[type(item).__name__ for item in data_list]}')
        
        for item in data_list:
            # 确保item是字典类型
            if not isinstance(item, dict):
                logger.warning(f'跳过非字典类型数据: {item}')
                continue
                
            # FastGPT返回的数据结构可能需要根据实际情况调整
            # 合并问题和答案作为完整内容
            q = item.get('q', '')
            a = item.get('a', '')
            content = f"{q}\n{a}" if q and a else q or a
            
            # 获取相似度分数
            score = 0
            scores = item.get('score', [])
            if scores and isinstance(scores, list):
                for score_item in scores:
                    if isinstance(score_item, dict) and score_item.get('type') == 'embedding':
                        score = score_item.get('value', 0)
                        break
            
            record = {
                'content': content,
                'score': score,
                'title': item.get('sourceName', 'Unknown'),  # 使用sourceName作为标题
                'metadata': {
                    'path': f"fastgpt://{item.get('collectionId', '')}",
                    'source_id': item.get('sourceId', ''),
                    'chunk_index': item.get('chunkIndex', 0)
                }
            }
            records.append(record)
        
        # 返回Dify格式的响应
        response_data = {'records': records}
        # logger.info(f'返回Dify响应: {json.dumps(response_data, ensure_ascii=False)}')
        logger.info('返回Dify成功')
        return jsonify(response_data)
        
    except Exception as e:
        import traceback
        error_msg = f'服务器内部错误: {str(e)}\n{traceback.format_exc()}'
        logger.error(error_msg)
        return jsonify({
            'error_code': 500,
            'error_msg': error_msg
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)