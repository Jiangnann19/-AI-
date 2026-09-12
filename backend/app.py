"""
多模态AI互动式教学智能体 - Flask后端主程序
锐捷网络教育信息化应用场景
"""

import os
import sys
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename
import traceback

# 添加app目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# 导入自定义模块
from app.rags.knowledge_base import get_knowledge_base
from app.parsers.document_parser import get_document_parser
from app.utils.intent_analyzer import get_intent_analyzer
from app.utils.multimodal_fusion import get_multimodal_fusion
from app.utils.image_parser import get_image_parser
from app.generators.ppt_generator import get_ppt_generator
from app.generators.word_generator import get_word_generator
from app.generators.game_generator import get_game_generator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__, 
            template_folder='../frontend/templates',
            static_folder='../frontend/static')
CORS(app)

# 配置
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
OUTPUT_FOLDER = os.path.join(os.path.dirname(__file__), 'outputs')
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'pptx', 'png', 'jpg', 'jpeg', 'mp4', 'avi', 'mov', 'txt'}
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# 确保目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# 全局变量存储生成的文件路径
generated_files = {
    'ppt': None,
    'word': None,
    'game': None
}


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    智能对话API
    处理用户输入，进行意图分析和多轮对话
    """
    try:
        data = request.json
        message = data.get('message', '')
        history = data.get('history', [])
        files = data.get('files', [])
        rag_enabled = data.get('rag_enabled', True)  # 默认开启RAG
        
        logger.info(f"收到对话请求: {message}, RAG启用: {rag_enabled}")
        
        # 处理图片解析结果
        image_context = ""
        if files:
            for file_info in files:
                if isinstance(file_info, dict) and file_info.get('type') == 'image':
                    parsed_text = file_info.get('parsed_text', '')
                    if parsed_text:
                        image_context += f"\n[图片解析: {file_info.get('name', '未知图片')}]\n{parsed_text}\n"
                        logger.info(f"包含图片解析结果: {file_info.get('name')}")
        
        # RAG检索
        rag_context = ""
        used_rag = False
        rag_error = False
        
        if rag_enabled:
            try:
                knowledge_base = get_knowledge_base()
                search_results = knowledge_base.search(message, top_k=5, similarity_threshold=0.015)
                
                if search_results:
                    # 提取检索到的内容
                    rag_context_parts = []
                    for result in search_results:
                        source = result.get('metadata', {}).get('source', '未知文档')
                        content = result.get('content', '')
                        similarity = result.get('similarity', 0)
                        rag_context_parts.append(f"[来源: {source}, 相似度: {similarity:.4f}] {content}")
                    
                    rag_context = "\n\n".join(rag_context_parts)
                    used_rag = True
                    
                    logger.info(f"RAG检索成功: 查询='{message}', 检索到{len(search_results)}个片段")
                    for i, result in enumerate(search_results):
                        logger.info(f"  片段{i+1}: 相似度={result.get('similarity', 0):.4f}, 来源={result.get('metadata', {}).get('source', 'unknown')}")
                else:
                    rag_error = True
                    logger.warning(f"RAG检索未找到匹配内容: 查询='{message}'")
            except Exception as e:
                rag_error = True
                logger.error(f"RAG检索失败: {str(e)}")
        
        # 合并上下文（图片解析 + RAG）
        combined_context = image_context
        if rag_context:
            combined_context += "\n\n" + rag_context
        
        # 获取意图分析器
        intent_analyzer = get_intent_analyzer()
        
        # 分析用户意图（传入合并上下文）
        intent = intent_analyzer.analyze(message, history, rag_context=combined_context)
        
        # 检查信息完整性
        is_complete = intent_analyzer.check_completeness(intent)
        
        # 生成回复
        if is_complete:
            response = intent_analyzer.summarize_intent(intent)
            response += "\n\n信息已完整，您可以点击生成课件按钮开始生成课件。"
        else:
            clarification = intent_analyzer.generate_clarification(intent)
            if clarification:
                response = clarification
            else:
                response = "请提供更多教学需求信息，如教学目标、授课时长、知识点等。"
        
        return jsonify({
            'success': True,
            'response': response,
            'intent': intent,
            'is_complete': is_complete,
            'used_rag': used_rag,
            'rag_error': rag_error
        })
        
    except Exception as e:
        logger.error(f"对话处理错误: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/generate', methods=['POST'])
def generate():
    """
    课件生成API
    融合多模态信息，生成PPT、Word和互动游戏
    """
    global generated_files
    
    try:
        # 获取意图信息
        intent_str = request.form.get('intent', '{}')
        intent = json.loads(intent_str)
        rag_enabled = request.form.get('rag_enabled', 'true').lower() == 'true'  # 默认开启RAG
        
        logger.info(f"收到课件生成请求: {intent.get('course_title', '未命名')}, RAG启用: {rag_enabled}")
        
        # RAG检索（如果启用）
        rag_context = ""
        used_rag = False
        
        if rag_enabled:
            try:
                knowledge_base = get_knowledge_base()
                # 使用课程标题和知识点作为查询词
                query_terms = []
                course_title = intent.get('course_title', '')
                knowledge_points = intent.get('knowledge_points', [])
                
                if course_title:
                    query_terms.append(course_title)
                if knowledge_points:
                    query_terms.extend(knowledge_points)
                
                # 对每个查询词进行检索
                all_search_results = []
                for query in query_terms[:3]:  # 最多检索3个查询词
                    if query:
                        results = knowledge_base.search(query, top_k=5, similarity_threshold=0.015)
                        all_search_results.extend(results)
                
                if all_search_results:
                    # 去重并按相似度排序
                    seen_contents = set()
                    unique_results = []
                    for result in all_search_results:
                        content = result.get('content', '')
                        if content not in seen_contents:
                            seen_contents.add(content)
                            unique_results.append(result)
                    
                    # 按相似度排序
                    unique_results.sort(key=lambda x: x.get('similarity', 0), reverse=True)
                    unique_results = unique_results[:10]  # 最多保留10个结果
                    
                    # 提取检索到的内容
                    rag_context_parts = []
                    for result in unique_results:
                        source = result.get('metadata', {}).get('source', '未知文档')
                        content = result.get('content', '')
                        similarity = result.get('similarity', 0)
                        rag_context_parts.append(f"[来源: {source}, 相似度: {similarity:.4f}] {content}")
                    
                    rag_context = "\n\n".join(rag_context_parts)
                    used_rag = True
                    
                    logger.info(f"课件生成RAG检索成功: 检索到{len(unique_results)}个片段")
                    for i, result in enumerate(unique_results):
                        logger.info(f"  片段{i+1}: 相似度={result.get('similarity', 0):.4f}, 来源={result.get('metadata', {}).get('source', 'unknown')}")
                else:
                    logger.warning(f"课件生成RAG检索未找到匹配内容")
            except Exception as e:
                logger.error(f"课件生成RAG检索失败: {str(e)}")
        
        # 处理上传的文件
        reference_materials = []
        if 'files' in request.files:
            files = request.files.getlist('files')
            document_parser = get_document_parser()
            
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    
                    try:
                        # 解析文件
                        parsed = document_parser.parse(filepath)
                        reference_materials.append(parsed)
                        logger.info(f"成功解析文件: {filename}")
                    except Exception as e:
                        logger.error(f"文件解析失败 {filename}: {str(e)}")
        
        # 将RAG检索到的内容添加到参考资料
        if rag_context:
            reference_materials.append({
                'type': 'rag_knowledge',
                'full_text': rag_context,
                'source': 'knowledge_base'
            })
        
        # 多模态融合
        fusion = get_multimodal_fusion()
        fusion_instruction = fusion.fuse(intent, reference_materials, use_knowledge_base=True)
        
        # 生成PPT
        ppt_generator = get_ppt_generator()
        ppt_path = ppt_generator.generate(fusion_instruction)
        
        # 生成Word
        word_generator = get_word_generator()
        word_path = word_generator.generate(fusion_instruction)
        
        # 生成互动游戏
        game_generator = get_game_generator()
        game_path = game_generator.generate(fusion_instruction)
        
        # 保存生成的文件路径
        generated_files = {
            'ppt': ppt_path,
            'word': word_path,
            'game': game_path
        }
        
        # 生成预览信息
        ppt_structure = fusion_instruction.get('ppt_structure', [])
        word_preview = f"教案标题：{fusion_instruction.get('course_title', '未命名')}\n"
        word_preview += f"教学目标：{fusion_instruction.get('teaching_objective', '')}\n"
        word_preview += f"授课时长：{fusion_instruction.get('duration', '')}\n"
        word_preview += f"受众：{fusion_instruction.get('target_audience', '')}"
        
        logger.info("课件生成成功")
        
        return jsonify({
            'success': True,
            'ppt_path': '/api/download/ppt',
            'word_path': '/api/download/word',
            'game_path': '/api/download/game',
            'ppt_structure': ppt_structure,
            'word_preview': word_preview,
            'fusion_instruction': fusion_instruction,
            'used_rag': used_rag
        })
        
    except Exception as e:
        logger.error(f"课件生成错误: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/iterate', methods=['POST'])
def iterate():
    """
    迭代优化API
    根据用户修改意见更新课件
    """
    global generated_files
    
    try:
        data = request.json
        modification = data.get('modification', '')
        current_intent = data.get('current_intent', {})
        
        logger.info(f"收到迭代优化请求: {modification}")
        
        # 使用意图分析器处理修改指令
        intent_analyzer = get_intent_analyzer()
        updated_intent = intent_analyzer.apply_modification(current_intent, modification)
        
        # 融合更新后的意图
        fusion = get_multimodal_fusion()
        fusion_instruction = fusion.fuse(updated_intent, [], use_knowledge_base=True)
        
        # 重新生成
        ppt_generator = get_ppt_generator()
        ppt_path = ppt_generator.generate(fusion_instruction)
        
        word_generator = get_word_generator()
        word_path = word_generator.generate(fusion_instruction)
        
        game_generator = get_game_generator()
        game_path = game_generator.generate(fusion_instruction)
        
        # 更新文件路径
        generated_files = {
            'ppt': ppt_path,
            'word': word_path,
            'game': game_path
        }
        
        # 生成预览信息
        ppt_structure = fusion_instruction.get('ppt_structure', [])
        word_preview = f"教案标题：{fusion_instruction.get('course_title', '未命名')}\n"
        word_preview += f"教学目标：{fusion_instruction.get('teaching_objective', '')}\n"
        word_preview += f"授课时长：{fusion_instruction.get('duration', '')}\n"
        word_preview += f"受众：{fusion_instruction.get('target_audience', '')}"
        
        logger.info("迭代优化成功")
        
        return jsonify({
            'success': True,
            'ppt_path': '/api/download/ppt',
            'word_path': '/api/download/word',
            'game_path': '/api/download/game',
            'ppt_structure': ppt_structure,
            'word_preview': word_preview,
            'fusion_instruction': fusion_instruction,
            'updated_intent': updated_intent
        })
        
    except Exception as e:
        logger.error(f"迭代优化错误: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/download/ppt', methods=['GET'])
def download_ppt():
    """下载PPT文件"""
    try:
        if generated_files.get('ppt') and os.path.exists(generated_files['ppt']):
            return send_file(generated_files['ppt'], as_attachment=True, download_name='课件.pptx')
        else:
            return jsonify({'success': False, 'error': 'PPT文件不存在'}), 404
    except Exception as e:
        logger.error(f"PPT下载错误: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/download/word', methods=['GET'])
def download_word():
    """下载Word文件"""
    try:
        if generated_files.get('word') and os.path.exists(generated_files['word']):
            return send_file(generated_files['word'], as_attachment=True, download_name='教案.docx')
        else:
            return jsonify({'success': False, 'error': 'Word文件不存在'}), 404
    except Exception as e:
        logger.error(f"Word下载错误: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/download/game', methods=['GET'])
def download_game():
    """下载游戏HTML文件"""
    try:
        if generated_files.get('game') and os.path.exists(generated_files['game']):
            return send_file(generated_files['game'], as_attachment=True, download_name='互动游戏.html')
        else:
            return jsonify({'success': False, 'error': '游戏文件不存在'}), 404
    except Exception as e:
        logger.error(f"游戏下载错误: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/knowledge/upload', methods=['POST'])
def knowledge_upload():
    """
    知识库上传API
    上传教学文档到本地RAG知识库
    """
    try:
        if 'files' not in request.files:
            return jsonify({'success': False, 'error': '没有文件'}), 400
        
        files = request.files.getlist('files')
        knowledge_base = get_knowledge_base()
        document_parser = get_document_parser()
        
        count = 0
        total_chunks_added = 0
        uploaded_files = []
        
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                try:
                    # 解析文件
                    parsed = document_parser.parse(filepath)
                    full_text = parsed.get('full_text', '')
                    
                    if full_text and full_text.strip():
                        # 记录提取的文本长度
                        text_length = len(full_text)
                        logger.info(f"文件 {filename} 提取文本长度: {text_length} 字符")
                        
                        # 分块
                        chunks = knowledge_base.chunk_text(full_text, chunk_size=500, overlap=50)
                        logger.info(f"文件 {filename} 分块数量: {len(chunks)}")
                        
                        # 添加到知识库
                        metadatas = [{'source': filename, 'type': parsed.get('type', 'unknown')} for _ in chunks]
                        added_count = knowledge_base.add_documents(chunks, metadatas=metadatas)
                        total_chunks_added += added_count
                        count += 1
                        
                        uploaded_files.append({
                            'filename': filename,
                            'type': parsed.get('type', 'unknown'),
                            'text_length': text_length,
                            'chunks': len(chunks),
                            'added': added_count
                        })
                        
                        logger.info(f"成功添加到知识库: {filename}, 入库块数: {added_count}")
                    else:
                        logger.warning(f"文件 {filename} 提取文本为空，跳过入库")
                except Exception as e:
                    logger.error(f"知识库添加失败 {filename}: {str(e)}")
                    logger.error(traceback.format_exc())
        
        # 获取更新后的统计信息
        stats = knowledge_base.get_stats()
        
        logger.info(f"知识库上传完成: 成功处理{count}个文件，总入库{total_chunks_added}个文本块")
        
        return jsonify({
            'success': True,
            'count': count,
            'total_chunks': total_chunks_added,
            'uploaded_files': uploaded_files,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"知识库上传错误: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/knowledge/stats', methods=['GET'])
def knowledge_stats():
    """
    知识库统计API
    获取知识库统计信息
    """
    try:
        knowledge_base = get_knowledge_base()
        stats = knowledge_base.get_stats()
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"知识库统计错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/knowledge/search', methods=['POST'])
def knowledge_search():
    """
    知识库搜索API
    语义检索知识库内容
    """
    try:
        data = request.json
        query = data.get('query', '')
        top_k = data.get('top_k', 5)  # 允许前端指定top_k，默认5
        similarity_threshold = data.get('similarity_threshold', 0.015)  # 相似度阈值
        
        if not query:
            return jsonify({'success': False, 'error': '查询内容不能为空'}), 400
        
        logger.info(f"知识库搜索请求: 查询='{query}', top_k={top_k}, 阈值={similarity_threshold}")
        
        knowledge_base = get_knowledge_base()
        results = knowledge_base.search(query, top_k=top_k, similarity_threshold=similarity_threshold)
        
        logger.info(f"知识库搜索返回: {len(results)}个结果")
        
        return jsonify({
            'success': True,
            'results': results,
            'query': query,
            'top_k': top_k,
            'similarity_threshold': similarity_threshold
        })
        
    except Exception as e:
        logger.error(f"知识库搜索错误: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/knowledge/delete', methods=['POST'])
def knowledge_delete():
    """
    知识库删除API
    删除指定文档的所有块
    """
    try:
        data = request.json
        source_name = data.get('source_name', '')
        
        if not source_name:
            return jsonify({'success': False, 'error': '文档名称不能为空'}), 400
        
        logger.info(f"知识库删除请求: 文档={source_name}")
        
        knowledge_base = get_knowledge_base()
        deleted_count = knowledge_base.delete_document(source_name)
        
        logger.info(f"知识库删除完成: 删除了{deleted_count}个块")
        
        return jsonify({
            'success': True,
            'deleted_count': deleted_count,
            'source_name': source_name
        })
        
    except Exception as e:
        logger.error(f"知识库删除错误: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/knowledge/clear', methods=['POST'])
def knowledge_clear():
    """
    知识库清空API
    清空所有文档和文本块
    """
    try:
        logger.info("知识库清空请求")
        
        knowledge_base = get_knowledge_base()
        deleted_count = knowledge_base.clear_all()
        
        logger.info(f"知识库清空完成: 删除了{deleted_count}个块")
        
        return jsonify({
            'success': True,
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        logger.error(f"知识库清空错误: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/parse-image', methods=['POST'])
def parse_image():
    """
    图片解析API
    使用多模态模型识别图片中的文字、报文信息、拓扑结构
    """
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': '未上传图片'}), 400
        
        image_file = request.files['image']
        
        if image_file.filename == '':
            return jsonify({'success': False, 'error': '未选择文件'}), 400
        
        if not allowed_file(image_file.filename):
            return jsonify({'success': False, 'error': '不支持的文件类型'}), 400
        
        # 检查文件大小（限制为10MB）
        image_file.seek(0, os.SEEK_END)
        file_size = image_file.tell()
        image_file.seek(0)
        
        if file_size > 10 * 1024 * 1024:  # 10MB
            return jsonify({'success': False, 'error': '图片过大，请上传小于10MB的图片'}), 400
        
        # 保存上传的图片
        filename = secure_filename(image_file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        image_file.save(filepath)
        
        logger.info(f"收到图片上传请求: {filename}, 大小: {file_size} 字节")
        
        # 调用多模态解析
        from app.utils.image_parser import get_image_parser
        image_parser = get_image_parser()
        
        parsed_text = image_parser.parse_image(filepath)
        
        logger.info(f"图片解析成功: {filename}, 解析文本长度: {len(parsed_text)}")
        
        return jsonify({
            'success': True,
            'parsed_text': parsed_text,
            'filename': filename
        })
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"图片解析错误: {error_msg}")
        traceback.print_exc()
        
        # 提供友好的错误提示
        if 'API密钥' in error_msg or 'api_key' in error_msg.lower():
            return jsonify({'success': False, 'error': 'API密钥错误，请检查DASHSCOPE_API_KEY环境变量'}), 500
        elif '额度' in error_msg or 'quota' in error_msg.lower():
            return jsonify({'success': False, 'error': 'API额度不足，请检查阿里云百炼账户'}), 500
        elif 'dashscope' in error_msg.lower():
            return jsonify({'success': False, 'error': 'DashScope服务错误，请稍后重试'}), 500
        else:
            return jsonify({'success': False, 'error': f'图片解析失败: {error_msg}'}), 500


@app.route('/api/save-to-knowledge-base', methods=['POST'])
def save_to_knowledge_base():
    """
    保存到知识库API
    将图片解析结果保存到知识库
    """
    try:
        data = request.get_json()
        content = data.get('content', '')
        source = data.get('source', '未知来源')
        doc_type = data.get('type', 'text')
        
        if not content:
            return jsonify({'success': False, 'error': '内容不能为空'}), 400
        
        # 获取知识库实例
        kb = get_knowledge_base()
        
        # 添加到知识库
        kb.add_document(content, metadata={
            'source': source,
            'type': doc_type,
            'timestamp': datetime.now().isoformat()
        })
        
        logger.info(f"成功保存到知识库: 来源={source}, 类型={doc_type}, 内容长度={len(content)}")
        
        return jsonify({
            'success': True,
            'message': '成功保存到知识库'
        })
        
    except Exception as e:
        logger.error(f"保存到知识库错误: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })


if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    logger.info(f"启动Flask服务器: {host}:{port}")
    logger.info(f"调试模式: {debug}")
    
    app.run(host=host, port=port, debug=debug)
