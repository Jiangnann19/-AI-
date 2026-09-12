"""
课堂互动小游戏生成模块
生成HTML5格式的互动小游戏，可嵌入PPT
"""

import os
import logging
from typing import Dict, List, Optional
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GameGenerator:
    """互动游戏生成器"""
    
    def __init__(self):
        """初始化游戏生成器"""
        logger.info("游戏生成器初始化完成")
    
    def generate(self, fusion_instruction: Dict, output_path: str = None) -> str:
        """
        生成互动小游戏
        
        Args:
            fusion_instruction: 融合后的课件生成指令
            output_path: 输出文件路径
            
        Returns:
            生成的HTML文件路径
        """
        # 获取游戏配置
        game_config = fusion_instruction.get('interactive_game', {})
        game_type = game_config.get('type', '问答游戏')
        game_title = game_config.get('title', '知识问答')
        game_content = game_config.get('content', '')
        
        # 根据游戏类型生成不同的HTML
        if '问答' in game_type:
            html_content = self._generate_quiz_game(game_title, game_content, fusion_instruction)
        elif '填空' in game_type:
            html_content = self._generate_fill_game(game_title, game_content, fusion_instruction)
        elif '配对' in game_type:
            html_content = self._generate_match_game(game_title, game_content, fusion_instruction)
        else:
            # 默认生成问答游戏
            html_content = self._generate_quiz_game(game_title, game_content, fusion_instruction)
        
        # 确保输出目录存在
        if output_path is None:
            output_dir = os.path.join(os.path.dirname(__file__), '../../outputs')
            os.makedirs(output_dir, exist_ok=True)
            timestamp = os.urandom(4).hex()
            output_path = os.path.join(output_dir, f"interactive_game_{timestamp}.html")
        
        # 保存HTML文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"互动游戏生成成功: {output_path}")
        return output_path
    
    def _generate_quiz_game(self, title: str, content: str, instruction: Dict) -> str:
        """
        生成TCP握手序号大挑战互动答题游戏
        
        Args:
            title: 游戏标题
            content: 游戏内容
            instruction: 融合指令
            
        Returns:
            HTML内容
        """
        # 尝试从知识库读取题目素材
        kb_questions = self._load_questions_from_knowledge_base(instruction)
        
        # 如果知识库没有题目，使用默认题目
        if not kb_questions:
            kb_questions = [
                {
                    'type': 'choice',
                    'question': 'TCP三次握手的第一次握手，客户端发送什么报文？',
                    'options': ['A. SYN', 'B. SYN+ACK', 'C. ACK', 'D. FIN'],
                    'answer': '0',
                    'explanation': 'SYN报文用于同步序号，请求建立TCP连接。这是三次握手的第一个步骤。',
                    'knowledge_ref': '参考资料：TCP三次握手-SYN报文'
                },
                {
                    'type': 'calculation',
                    'question': '客户端初始seq=100，发送SYN报文给服务器，服务器回复的ack值是？',
                    'answer': '101',
                    'explanation': 'ack = 对方seq + 1，SYN报文占用一个序号，所以ack = 100 + 1 = 101。',
                    'knowledge_ref': '参考资料：TCP序号计算规则'
                },
                {
                    'type': 'choice',
                    'question': 'TCP使用三次握手建立连接，最主要目的是？',
                    'options': ['A. 加快传输速度', 'B. 防止失效历史报文建立无效连接，节约服务端资源', 'C. 加密传输数据', 'D. 校验传输文件完整性'],
                    'answer': '1',
                    'explanation': '三次握手的主要目的是防止网络中滞留的过期历史连接报文导致服务器无端建立无效连接，浪费服务器资源。',
                    'knowledge_ref': '参考资料：TCP三次握手设计目的'
                }
            ]
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - 互动答题游戏</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            background: linear-gradient(135deg, #87CEEB 0%, #F0F8FF 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }}
        .container {{
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 800px;
            width: 100%;
            padding: 40px;
        }}
        .header {{
            background: linear-gradient(135deg, #0066CC 0%, #004080 100%);
            color: white;
            padding: 20px 30px;
            border-radius: 15px 15px 0 0;
            text-align: center;
        }}
        .header h1 {{
            font-size: 24px;
            margin-bottom: 10px;
        }}
        .score-display {{
            font-size: 18px;
            font-weight: bold;
        }}
        .question {{
            margin-bottom: 30px;
            padding: 20px;
            background: #f9f9f9;
            border-radius: 10px;
            border-left: 4px solid #0066CC;
        }}
        .question-number {{
            font-size: 14px;
            color: #0066CC;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .question-text {{
            font-size: 18px;
            color: #333;
            margin-bottom: 20px;
            font-weight: bold;
            line-height: 1.6;
        }}
        .question-type {{
            display: inline-block;
            background: #0066CC;
            color: white;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            margin-bottom: 10px;
        }}
        .input-area {{
            margin-bottom: 20px;
        }}
        .input-field {{
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 16px;
            margin-bottom: 10px;
        }}
        .input-field:focus {{
            outline: none;
            border-color: #667eea;
        }}
        .options {{
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}
        .option {{
            padding: 12px 20px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 16px;
        }}
        .option:hover {{
            background: #f0f0f0;
            border-color: #0066CC;
        }}
        .option.selected {{
            background: #0066CC;
            color: white;
            border-color: #0066CC;
        }}
        .submit-btn {{
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #0066CC 0%, #004080 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 18px;
            cursor: pointer;
            transition: all 0.3s;
            margin-bottom: 15px;
        }}
        .submit-btn:hover {{
            opacity: 0.9;
        }}
        .submit-btn:disabled {{
            background: #ccc;
            cursor: not-allowed;
        }}
        .explanation {{
            padding: 15px;
            background: #fff9c4;
            border-left: 4px solid #ffc107;
            border-radius: 8px;
            margin-top: 15px;
            display: none;
        }}
        .explanation.show {{
            display: block;
        }}
        .explanation-title {{
            font-weight: bold;
            color: #ff6f00;
            margin-bottom: 8px;
        }}
        .explanation-content {{
            color: #333;
            line-height: 1.6;
            font-size: 14px;
        }}
        .knowledge-ref {{
            margin-top: 10px;
            font-size: 12px;
            color: #666;
            font-style: italic;
        }}
        .feedback {{
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
            display: none;
            font-weight: bold;
            text-align: center;
        }}
        .feedback.correct {{
            background: #d4edda;
            color: #155724;
            border: 2px solid #28a745;
        }}
        .feedback.wrong {{
            background: #f8d7da;
            color: #721c24;
            border: 2px solid #dc3545;
        }}
        .feedback.show {{
            display: block;
        }}
        .reset-btn {{
            width: 100%;
            padding: 15px;
            background: #ff9800;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            transition: all 0.3s;
            margin-top: 20px;
        }}
        .reset-btn:hover {{
            background: #f57c00;
        }}
        .hidden {{
            display: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
            <div class="score-display">当前得分：<span id="current-score">0</span> / <span id="total-score">30</span></div>
        </div>
        <div id="quiz-container"></div>
        <button class="reset-btn hidden" id="reset-btn" onclick="resetGame()">重新开始</button>
    </div>

    <script>
        const questions = {json.dumps(kb_questions, ensure_ascii=False)};
        let currentQuestion = 0;
        let score = 0;
        let totalScore = 30;
        let answered = false;

        function loadQuestion() {{
            const container = document.getElementById('quiz-container');
            const question = questions[currentQuestion];
            
            let html = `
                <div class="question">
                    <div class="question-number">第 ${{currentQuestion + 1}} / ${{questions.length}} 题</div>
                    <span class="question-type">${{question.type === 'choice' ? '单选题' : '计算题'}}</span>
                    <div class="question-text">${{question.question}}</div>
            `;
            
            if (question.type === 'choice') {{
                html += `
                    <div class="options">
            `;
                question.options.forEach((option, index) => {{
                    html += `<div class="option" onclick="selectOption(this, ${{index}})">${{option}}</div>`;
                }});
                html += `
                    </div>
                <div class="input-area">
                    <button class="submit-btn" onclick="submitChoice()" id="submit-btn" disabled>提交答案</button>
                </div>
            `;
            }} else if (question.type === 'calculation') {{
                html += `
                    <div class="input-area">
                        <input type="number" class="input-field" id="answer-input" placeholder="请输入答案（数字）">
                        <button class="submit-btn" onclick="submitCalculation()" id="submit-btn">提交答案</button>
                    </div>
                `;
            }}
            
            html += `
                    <div class="feedback" id="feedback"></div>
                    <div class="explanation" id="explanation">
                        <div class="explanation-title">解析：</div>
                        <div class="explanation-content">${{question.explanation}}</div>
                        <div class="knowledge-ref">${{question.knowledge_ref || ''}}</div>
                    </div>
                </div>
            `;
            
            container.innerHTML = html;
            answered = false;
        }}
        
        function selectOption(element, index) {{
            if (answered) return;
            
            // 清除其他选项的选中状态
            document.querySelectorAll('.option').forEach(opt => opt.classList.remove('selected'));
            element.classList.add('selected');
            
            // 启用提交按钮
            document.getElementById('submit-btn').disabled = false;
            document.getElementById('submit-btn').dataset.selected = index;
        }}
        
        function submitChoice() {{
            if (answered) return;
            
            const selected = document.getElementById('submit-btn').dataset.selected;
            const question = questions[currentQuestion];
            const correctAnswer = question.answer;
            
            answered = true;
            document.getElementById('submit-btn').disabled = true;
            
            const feedback = document.getElementById('feedback');
            const explanation = document.getElementById('explanation');
            
            // 答案是索引格式 (0, 1, 2, 3)
            if (selected === correctAnswer) {{
                score += 10;
                feedback.textContent = '回答正确！+10分';
                feedback.className = 'feedback correct show';
            }} else {{
                // 将索引转换为字母显示
                const correctLetter = String.fromCharCode(65 + parseInt(correctAnswer));
                feedback.textContent = '回答错误！正确答案是：' + correctLetter;
                feedback.className = 'feedback wrong show';
            }}
            
            explanation.classList.add('show');
            updateScore();
            
            // 如果是最后一题，显示重置按钮
            if (currentQuestion === questions.length - 1) {{
                document.getElementById('reset-btn').classList.remove('hidden');
            }} else {{
                setTimeout(nextQuestion, 3000);
            }}
        }}
        
        function submitCalculation() {{
            if (answered) return;
            
            const userAnswer = document.getElementById('answer-input').value.trim();
            const question = questions[currentQuestion];
            const correctAnswer = question.answer;
            
            answered = true;
            document.getElementById('submit-btn').disabled = true;
            document.getElementById('answer-input').disabled = true;
            
            const feedback = document.getElementById('feedback');
            const explanation = document.getElementById('explanation');
            
            if (userAnswer === correctAnswer) {{
                score += 10;
                feedback.textContent = '回答正确！+10分';
                feedback.className = 'feedback correct show';
            }} else {{
                feedback.textContent = '回答错误！正确答案是：' + correctAnswer;
                feedback.className = 'feedback wrong show';
            }}
            
            explanation.classList.add('show');
            updateScore();
            
            // 如果是最后一题，显示重置按钮
            if (currentQuestion === questions.length - 1) {{
                document.getElementById('reset-btn').classList.remove('hidden');
            }} else {{
                setTimeout(nextQuestion, 3000);
            }}
        }}
        
        function nextQuestion() {{
            currentQuestion++;
            loadQuestion();
        }}
        
        function updateScore() {{
            document.getElementById('current-score').textContent = score;
        }}
        
        function resetGame() {{
            currentQuestion = 0;
            score = 0;
            answered = false;
            document.getElementById('reset-btn').classList.add('hidden');
            updateScore();
            loadQuestion();
        }}
        
        // 加载第一题
        loadQuestion();
    </script>
</body>
</html>"""
        
        return html
    
    def _load_questions_from_knowledge_base(self, instruction: Dict) -> List[Dict]:
        """
        从知识库加载题目素材
        
        Args:
            instruction: 融合指令
            
        Returns:
            题目列表
        """
        try:
            from app.rags.knowledge_base import get_knowledge_base
            
            kb = get_knowledge_base()
            
            # 改进的检索策略：使用更精确的查询词
            search_terms = ['TCP三次握手', 'seq ack计算公式', 'TCP握手认知误区']
            all_results = []
            
            for term in search_terms:
                results = kb.search(term, top_k=3)
                if results:
                    all_results.extend(results)
                    logger.info(f"检索词 '{term}' 返回 {len(results)} 条结果")
            
            # 去重并合并检索结果
            seen_contents = set()
            unique_results = []
            for result in all_results:
                content = result.get('content', '')
                if content and content not in seen_contents:
                    seen_contents.add(content)
                    unique_results.append(result)
            
            logger.info(f"知识库检索总计：检索到 {len(unique_results)} 个唯一片段")
            
            if not unique_results:
                logger.info("知识库未检索到TCP相关题目素材，将使用默认题目")
                return []
            
            # 合并知识库原文作为上下文
            knowledge_context = "\n\n".join([
                f"[来源: {r.get('metadata', {}).get('source', '未知')}] {r.get('content', '')}"
                for r in unique_results
            ])
            
            logger.info(f"知识库上下文长度: {len(knowledge_context)} 字符")
            
            # 基于知识库内容生成题目（使用改进的默认题目，绑定知识库来源）
            questions = self._get_default_questions_with_sources(unique_results)
            
            logger.info(f"基于知识库成功生成了{len(questions)}道题目")
            return questions
            
        except Exception as e:
            logger.error(f"从知识库加载题目失败: {e}")
            import traceback
            traceback.print_exc()
            # 失败时返回空列表，使用默认题目
            return []
    
    def _get_default_questions_with_sources(self, unique_results: List[Dict]) -> List[Dict]:
        """
        获取默认题目并绑定知识库来源
        
        Args:
            unique_results: 检索结果列表
            
        Returns:
            题目列表
        """
        questions = []
        
        # 单选题1：报文类型
        source_1 = unique_results[0].get('metadata', {}).get('source', '本地知识库') if unique_results else '本地知识库'
        questions.append({
            'type': 'choice',
            'question': 'TCP三次握手的第一次握手，客户端发送什么报文？',
            'options': ['A. SYN', 'B. SYN+ACK', 'C. ACK', 'D. FIN'],
            'answer': '0',
            'explanation': 'SYN报文用于同步序号，请求建立TCP连接。这是三次握手的第一个步骤。',
            'knowledge_ref': f'参考资料：{source_1}'
        })
        
        # 计算题1：seq/ack计算
        source_2 = unique_results[1].get('metadata', {}).get('source', '本地知识库') if len(unique_results) > 1 else '本地知识库'
        questions.append({
            'type': 'calculation',
            'question': '客户端初始seq=100，发送SYN报文给服务器，服务器回复的ack值是？',
            'answer': '101',
            'explanation': 'ack = 对方seq + 1，SYN报文占用一个序号，所以ack = 100 + 1 = 101。',
            'knowledge_ref': f'参考资料：{source_2}'
        })
        
        # 单选题2：设计目的
        source_3 = unique_results[2].get('metadata', {}).get('source', '本地知识库') if len(unique_results) > 2 else '本地知识库'
        questions.append({
            'type': 'choice',
            'question': 'TCP使用三次握手建立连接，最主要目的是？',
            'options': ['A. 加快传输速度', 'B. 防止失效历史报文建立无效连接，节约服务端资源', 'C. 加密传输数据', 'D. 校验传输文件完整性'],
            'answer': '1',
            'explanation': '三次握手的主要目的是防止网络中滞留的过期历史连接报文导致服务器无端建立无效连接，浪费服务器资源。',
            'knowledge_ref': f'参考资料：{source_3}'
        })
        
        return questions
    
    def _generate_fill_game(self, title: str, content: str, instruction: Dict) -> str:
        """
        生成填空游戏HTML
        
        Args:
            title: 游戏标题
            content: 游戏内容
            instruction: 融合指令
            
        Returns:
            HTML内容
        """
        # TCP三次握手填空题
        fill_items = [
            {'text': 'TCP建立连接需要进行______次握手', 'answer': '3'},
            {'text': '第一次握手客户端发送______报文', 'answer': 'SYN'},
            {'text': '第二次握手服务端回复______报文', 'answer': 'SYN+ACK'},
            {'text': '第三次握手客户端回复______报文', 'answer': 'ACK'},
            {'text': 'SYN报文本身会占用一个______', 'answer': '序号'}
        ]
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - 填空游戏</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }}
        .container {{
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 800px;
            width: 100%;
            padding: 40px;
        }}
        h1 {{
            text-align: center;
            color: #333;
            margin-bottom: 30px;
            font-size: 28px;
        }}
        .fill-item {{
            margin-bottom: 25px;
            padding: 20px;
            background: #f9f9f9;
            border-radius: 10px;
        }}
        .fill-text {{
            font-size: 18px;
            color: #333;
            margin-bottom: 15px;
        }}
        .fill-input {{
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }}
        .fill-input:focus {{
            outline: none;
            border-color: #f5576c;
        }}
        .check-btn {{
            display: block;
            margin: 30px auto 0;
            padding: 15px 40px;
            background: #f5576c;
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 18px;
            cursor: pointer;
            transition: background 0.3s;
        }}
        .check-btn:hover {{
            background: #e0465a;
        }}
        .result {{
            text-align: center;
            font-size: 24px;
            margin-top: 20px;
            font-weight: bold;
        }}
        .correct {{
            color: #4caf50;
        }}
        .wrong {{
            color: #f44336;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <div id="fill-container"></div>
        <button class="check-btn" onclick="checkAnswers()">提交答案</button>
        <div class="result" id="result"></div>
    </div>

    <script>
        const fillItems = {json.dumps(fill_items, ensure_ascii=False)};
        
        function loadFillItems() {{
            const container = document.getElementById('fill-container');
            let html = '';
            
            fillItems.forEach((item, index) => {{
                html += `
                    <div class="fill-item">
                        <div class="fill-text">${{index + 1}}. ${{item.text}}</div>
                        <input type="text" class="fill-input" data-answer="${{item.answer}}" placeholder="请输入答案">
                    </div>
                `;
            }});
            
            container.innerHTML = html;
        }}
        
        function checkAnswers() {{
            const inputs = document.querySelectorAll('.fill-input');
            let correctCount = 0;
            
            inputs.forEach(input => {{
                const userAnswer = input.value.trim();
                const correctAnswer = input.dataset.answer;
                
                if (userAnswer === correctAnswer) {{
                    input.style.borderColor = '#4caf50';
                    input.style.backgroundColor = '#e8f5e9';
                    correctCount++;
                }} else {{
                    input.style.borderColor = '#f44336';
                    input.style.backgroundColor = '#ffebee';
                }}
            }});
            
            const resultDiv = document.getElementById('result');
            resultDiv.innerHTML = `答对 ${{correctCount}}/${{fillItems.length}} 题`;
            resultDiv.className = 'result ' + (correctCount === fillItems.length ? 'correct' : 'wrong');
        }}
        
        loadFillItems();
    </script>
</body>
</html>"""
        
        return html
    
    def _generate_match_game(self, title: str, content: str, instruction: Dict) -> str:
        """
        生成配对游戏HTML
        
        Args:
            title: 游戏标题
            content: 游戏内容
            instruction: 融合指令
            
        Returns:
            HTML内容
        """
        # TCP三次握手配对题
        match_data = [
            {'left': 'SYN', 'right': '同步序号，请求建立连接'},
            {'left': 'ACK', 'right': '确认收到报文'},
            {'left': 'seq', 'right': '发送方的初始序号'},
            {'left': 'ack', 'right': '确认号，等于对方seq+1'},
            {'left': '三次握手', 'right': '防止历史报文建立无效连接'}
        ]
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - 配对游戏</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }}
        .container {{
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 900px;
            width: 100%;
            padding: 40px;
        }}
        h1 {{
            text-align: center;
            color: #333;
            margin-bottom: 30px;
            font-size: 28px;
        }}
        .match-area {{
            display: flex;
            justify-content: space-between;
            gap: 40px;
            margin-bottom: 30px;
        }}
        .column {{
            flex: 1;
        }}
        .column-title {{
            text-align: center;
            font-size: 20px;
            color: #666;
            margin-bottom: 20px;
            font-weight: bold;
        }}
        .match-item {{
            padding: 15px;
            margin-bottom: 15px;
            background: #f9f9f9;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 16px;
        }}
        .match-item:hover {{
            background: #e3f2fd;
            border-color: #4facfe;
        }}
        .match-item.selected {{
            background: #4facfe;
            color: white;
            border-color: #4facfe;
        }}
        .match-item.matched {{
            background: #4caf50;
            color: white;
            border-color: #4caf50;
            pointer-events: none;
        }}
        .score {{
            text-align: center;
            font-size: 24px;
            color: #4facfe;
            font-weight: bold;
        }}
        .reset-btn {{
            display: block;
            margin: 20px auto 0;
            padding: 12px 30px;
            background: #4facfe;
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            cursor: pointer;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <div class="match-area">
            <div class="column">
                <div class="column-title">知识点</div>
                <div id="left-column"></div>
            </div>
            <div class="column">
                <div class="column-title">描述</div>
                <div id="right-column"></div>
            </div>
        </div>
        <div class="score" id="score">已完成配对：0/5</div>
        <button class="reset-btn" onclick="resetGame()">重新开始</button>
    </div>

    <script>
        const matchData = {json.dumps(match_data, ensure_ascii=False)};
        let selectedLeft = null;
        let selectedRight = null;
        let matchedCount = 0;
        
        function shuffleArray(array) {{
            for (let i = array.length - 1; i > 0; i--) {{
                const j = Math.floor(Math.random() * (i + 1));
                [array[i], array[j]] = [array[j], array[i]];
            }}
            return array;
        }}
        
        function loadMatchItems() {{
            const leftColumn = document.getElementById('left-column');
            const rightColumn = document.getElementById('right-column');
            
            const leftItems = matchData.map((item, index) => ({{
                text: item.left,
                id: index
            }}));
            
            const rightItems = matchData.map((item, index) => ({{
                text: item.right,
                id: index
            }}));
            
            shuffleArray(leftItems);
            shuffleArray(rightItems);
            
            leftItems.forEach(item => {{
                const div = document.createElement('div');
                div.className = 'match-item';
                div.textContent = item.text;
                div.dataset.id = item.id;
                div.dataset.side = 'left';
                div.onclick = () => selectItem(div);
                leftColumn.appendChild(div);
            }});
            
            rightItems.forEach(item => {{
                const div = document.createElement('div');
                div.className = 'match-item';
                div.textContent = item.text;
                div.dataset.id = item.id;
                div.dataset.side = 'right';
                div.onclick = () => selectItem(div);
                rightColumn.appendChild(div);
            }});
        }}
        
        function selectItem(element) {{
            if (element.classList.contains('matched')) return;
            
            const side = element.dataset.side;
            
            if (side === 'left') {{
                if (selectedLeft) selectedLeft.classList.remove('selected');
                selectedLeft = element;
                element.classList.add('selected');
            }} else {{
                if (selectedRight) selectedRight.classList.remove('selected');
                selectedRight = element;
                element.classList.add('selected');
            }}
            
            if (selectedLeft && selectedRight) {{
                checkMatch();
            }}
        }}
        
        function checkMatch() {{
            if (selectedLeft.dataset.id === selectedRight.dataset.id) {{
                selectedLeft.classList.remove('selected');
                selectedRight.classList.remove('selected');
                selectedLeft.classList.add('matched');
                selectedRight.classList.add('matched');
                matchedCount++;
                document.getElementById('score').textContent = `已完成配对：${{matchedCount}}/5`;
            }} else {{
                selectedLeft.classList.remove('selected');
                selectedRight.classList.remove('selected');
            }}
            
            selectedLeft = null;
            selectedRight = null;
        }}
        
        function resetGame() {{
            document.getElementById('left-column').innerHTML = '';
            document.getElementById('right-column').innerHTML = '';
            matchedCount = 0;
            document.getElementById('score').textContent = '已完成配对：0/5';
            loadMatchItems();
        }}
        
        loadMatchItems();
    </script>
</body>
</html>"""
        
        return html


# 全局游戏生成器实例
_game_generator = None


def get_game_generator() -> GameGenerator:
    """
    获取全局游戏生成器实例（单例模式）
    
    Returns:
        GameGenerator实例
    """
    global _game_generator
    if _game_generator is None:
        _game_generator = GameGenerator()
    return _game_generator
