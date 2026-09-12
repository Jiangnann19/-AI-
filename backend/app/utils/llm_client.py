"""
大语言模型客户端（Python3.7 + openai==0.28.1兼容版）
支持模拟模式和真实API模式，集成RAG知识增强
"""

import os
import json
from typing import List, Dict, Optional
import logging
import openai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMClient:
    """大语言模型客户端（Python3.7兼容版）"""
    
    def __init__(self):
        """初始化LLM客户端"""
        from dotenv import load_dotenv
        load_dotenv()
        
        # 从环境变量读取配置
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.api_base = os.getenv('OPENAI_API_BASE', 'https://api.openai.com/v1')
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4')
        self.top_k_retrieval = int(os.getenv('TOP_K_RETRIEVAL', '5'))
        
        # 检查是否配置了有效的API密钥
        self.use_mock = not self.api_key or self.api_key == 'sk-demo-key-replace-with-real-key'
        
        if self.use_mock:
            logger.warning("未配置有效的API密钥，使用模拟模式")
        else:
            # 配置openai全局设置（0.28.1版本）
            openai.api_key = self.api_key
            openai.api_base = self.api_base
            logger.info(f"LLM客户端初始化完成，模型: {self.model}, API Base: {self.api_base}")
    
    def chat(self, messages: List[Dict], temperature: float = 0.7, max_tokens: int = 2000, use_rag: bool = True, rag_context: str = None) -> str:
        """
        对话接口
        
        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            temperature: 温度参数，控制随机性
            max_tokens: 最大生成token数
            use_rag: 是否使用RAG知识增强
            rag_context: 外部传入的RAG上下文（如果提供，优先使用）
            
        Returns:
            模型回复文本
        """
        if self.use_mock:
            return self._mock_chat(messages)
        
        try:
            # RAG知识增强
            if use_rag:
                messages = self._enhance_with_rag(messages, rag_context)
            
            # 使用openai 0.28.1版本的调用方式
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # 返回大模型原始文本结果
            return response.choices[0].message.content
        except openai.error.APIError as e:
            logger.error(f"OpenAI API错误: {e}")
            raise
        except openai.error.RateLimitError as e:
            logger.error(f"OpenAI API速率限制: {e}")
            raise
        except openai.error.AuthenticationError as e:
            logger.error(f"OpenAI API认证错误: {e}")
            raise
        except openai.error.NetworkError as e:
            logger.error(f"OpenAI API网络错误: {e}")
            raise
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            raise
    
    def _enhance_with_rag(self, messages: List[Dict], external_rag_context: str = None) -> List[Dict]:
        """
        使用RAG知识增强消息
        
        Args:
            messages: 原始消息列表
            external_rag_context: 外部传入的RAG上下文（如果提供，优先使用）
            
        Returns:
            增强后的消息列表
        """
        try:
            # 如果提供了外部RAG上下文，直接使用
            if external_rag_context:
                kb_context = f"【相关知识库内容】\n{external_rag_context}"
                logger.info("使用外部传入的RAG上下文进行增强")
            else:
                # 否则执行内部RAG检索
                from app.rags.knowledge_base import get_knowledge_base
                
                kb = get_knowledge_base()
                
                # 提取用户查询用于检索
                query = ""
                for msg in reversed(messages):
                    if msg.get('role') == 'user':
                        query = msg.get('content', '')
                        break
                
                if not query:
                    return messages
                
                # 从知识库检索相关内容
                results = kb.search(query, top_k=self.top_k_retrieval)
                
                if not results:
                    logger.info("知识库未检索到相关内容")
                    return messages
                
                # 构建知识库上下文
                kb_context = "【相关知识库内容】\n"
                for i, result in enumerate(results, 1):
                    kb_context += f"{i}. {result['content']}\n"
                    if result.get('metadata'):
                        source = result['metadata'].get('source', '未知')
                        kb_context += f"   来源: {source}\n"
                
                logger.info(f"从知识库检索到 {len(results)} 条相关内容进行增强")
            
            # 将知识库内容添加到system消息中
            enhanced_messages = []
            for msg in messages:
                if msg.get('role') == 'system':
                    # 在原有system prompt后添加知识库内容
                    enhanced_msg = msg.copy()
                    enhanced_msg['content'] = msg['content'] + "\n\n" + kb_context
                    enhanced_messages.append(enhanced_msg)
                else:
                    enhanced_messages.append(msg)
            
            return enhanced_messages
            
        except Exception as e:
            logger.error(f"RAG知识增强失败: {e}")
            # RAG失败时返回原始消息
            return messages

    def _mock_chat(self, messages: List[Dict]) -> str:
        """
        模拟对话响应
        
        Args:
            messages: 消息列表
            
        Returns:
            模拟回复
        """
        # 获取最后一条用户消息
        user_message = ""
        for msg in reversed(messages):
            if msg.get('role') == 'user':
                user_message = msg.get('content', '')
                break
        
        # 简单的关键词匹配模拟响应
        if '教学目标' in user_message or '目标' in user_message:
            return "请明确您的教学目标，例如：让学生掌握某个知识点、培养学生的某种能力等。"
        elif '授课时长' in user_message or '时长' in user_message or '时间' in user_message:
            return "请提供授课时长，例如：45分钟、90分钟等。"
        elif '知识点' in user_message or '内容' in user_message:
            return "请列出本课的主要知识点，例如：概念定义、原理、公式等。"
        elif '年级' in user_message or '受众' in user_message:
            return "请说明授课对象，例如：小学三年级、高中一年级等。"
        elif '重难点' in user_message or '重点' in user_message or '难点' in user_message:
            return "请说明本课的教学重点和难点，这将帮助我更好地设计课件。"
        elif '风格' in user_message:
            return "请说明您偏好的课件风格，例如：简洁现代、活泼生动、专业严谨等。"
        else:
            return "我已收到您的信息。为了更好地为您生成课件，请提供更多详细信息，如教学目标、授课时长、知识点、受众年级等。"
    
    def structured_completion(self, prompt: str, system_prompt: str = None, use_rag: bool = True, rag_context: str = None) -> Dict:
        """
        结构化补全，返回JSON格式结果
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            use_rag: 是否使用RAG知识增强
            rag_context: 外部传入的RAG上下文（如果提供，优先使用）
            
        Returns:
            结构化结果字典
        """
        if self.use_mock:
            return self._mock_structured_completion(prompt)
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # 添加JSON格式要求
        messages.append({"role": "user", "content": "请以JSON格式返回结果，不要包含其他文字说明。"})
        
        try:
            response = self.chat(messages, temperature=0.3, use_rag=use_rag, rag_context=rag_context)
            
            # 尝试解析JSON
            try:
                # 清理可能的markdown代码块标记
                response = response.strip()
                if response.startswith('```json'):
                    response = response[7:]
                if response.startswith('```'):
                    response = response[3:]
                if response.endswith('```'):
                    response = response[:-3]
                response = response.strip()
                
                return json.loads(response)
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {e}, 原始响应: {response}")
                raise ValueError(f"无法解析JSON响应: {e}")
                
        except Exception as e:
            logger.error(f"结构化补全失败: {e}")
            raise
    
    def _mock_structured_completion(self, prompt: str) -> Dict:
        """
        模拟结构化补全响应
        
        Args:
            prompt: 用户提示词
            
        Returns:
            模拟的结构化结果
        """
        # 根据提示词内容返回模拟的JSON结构
        if '课件' in prompt or '生成' in prompt:
            return {
                "course_title": "教学课件",
                "teaching_objective": {
                    "knowledge_objective": "通过本课学习，学生能够掌握相关知识点",
                    "ability_objective": "学生能够运用所学知识解决实际问题",
                    "quality_objective": "培养学生的逻辑思维能力和创新意识"
                },
                "target_audience": "学生",
                "duration": "45分钟",
                "knowledge_structure": [
                    {
                        "module": "知识模块一",
                        "points": ["知识点1", "知识点2"]
                    }
                ],
                "key_points": ["重点内容1", "重点内容2"],
                "difficult_points": [{"content": "难点内容1", "reason": "概念抽象，理解困难"}],
                "teaching_flow": [
                    {
                        "stage": "导入",
                        "content": "课程导入",
                        "time_allocation": "5分钟"
                    },
                    {
                        "stage": "新授",
                        "content": "新知识讲解",
                        "time_allocation": "25分钟"
                    },
                    {
                        "stage": "练习",
                        "content": "课堂练习",
                        "time_allocation": "10分钟"
                    },
                    {
                        "stage": "总结",
                        "content": "课程总结",
                        "time_allocation": "5分钟"
                    }
                ],
                "classroom_activities": [
                    {
                        "activity": "课堂讨论",
                        "description": "针对知识点进行小组讨论",
                        "interaction_type": "讨论"
                    },
                    {
                        "activity": "问答互动",
                        "description": "教师提问学生回答",
                        "interaction_type": "问答"
                    }
                ],
                "classroom_questions": ["什么是本课的核心概念？", "如何应用所学知识？", "这个知识点和之前的内容有什么联系？"],
                "homework": "完成课后练习题",
                "blackboard_design": "板书设计待完善",
                "ppt_structure": [
                    {
                        "slide_type": "cover",
                        "title": "教学课件",
                        "content": "课程标题",
                        "visual_elements": "封面设计"
                    },
                    {
                        "slide_type": "directory",
                        "title": "课程目录",
                        "content": "主要章节",
                        "visual_elements": "目录结构"
                    },
                    {
                        "slide_type": "tcp_handshake",
                        "title": "TCP三次握手：连接建立的核心机制",
                        "content": "三次握手流程、序号规则、报文含义、设计目的",
                        "visual_elements": "淡蓝色渐变背景、深蓝色标题横幅、四块结构化内容"
                    }
                ],
                "interactive_game": {
                    "type": "问答游戏",
                    "title": "TCP握手序号大挑战",
                    "content": "基于TCP三次握手知识点的问答互动"
                }
            }
        else:
            return {
                "teaching_objective": {
                    "knowledge_objective": "",
                    "ability_objective": "",
                    "quality_objective": ""
                },
                "duration": "",
                "knowledge_points": [],
                "key_difficulties": {
                    "key_points": [],
                    "difficult_points": []
                },
                "target_grade": "",
                "audience_analysis": {
                    "prerequisite_knowledge": "",
                    "cognitive_misconceptions": []
                },
                "classroom_activities": [],
                "classroom_questions": [],
                "style_preference": "",
                "special_requirements": "",
                "missing_fields": ["教学目标", "授课时长", "知识点", "受众年级"],
                "clarification_question": "请提供教学目标、授课时长、知识点和受众年级信息"
            }


# 全局LLM客户端实例
_llm_client = None


def get_llm_client() -> LLMClient:
    """
    获取全局LLM客户端实例（单例模式）
    
    Returns:
        LLMClient实例
    """
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
