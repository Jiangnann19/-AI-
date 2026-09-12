"""
教学意图理解模块
使用大模型结构化解析教师的对话意图
"""

import json
import logging
from typing import Dict, List, Optional
from .llm_client import get_llm_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IntentAnalyzer:
    """教学意图分析器"""
    
    def __init__(self):
        """初始化意图分析器"""
        self.llm_client = get_llm_client()
        self.system_prompt = """你是大学计算机网络专业教学设计专家。你的任务不是简单摘抄原文填表，而是深度解析用户教学需求，进行教学设计推理。

规则：
1. 教学目标：拆分为【知识目标、能力目标、素养目标】三层，不要直接复制用户一句话
2. 受众分析：针对大学一年级学生，预判前置知识、学生容易踩的认知误区
3. 重难点：区分【教学重点：必须掌握的核心知识】、【教学难点：学生容易混淆、难以理解的内容】，并简单解释难点成因
4. 自动生成适配本知识点的课堂提问、简短课堂小活动。

输出必须严格遵守给定JSON结构，字段名称保持不变。
如果用户缺少必要信息，填写missing_fields数组，并生成澄清提问。
禁止直接原样复制用户输入，必须做教学层面的加工、拆解、推理。"""
    
    def analyze(self, user_input: str, conversation_history: List[Dict] = None, rag_context: str = None) -> Dict:
        """
        分析用户输入的教学意图
        
        Args:
            user_input: 用户输入文本
            conversation_history: 对话历史
            rag_context: 外部传入的RAG上下文
            
        Returns:
            结构化的教学意图信息
        """
        # 构建提示词
        prompt = f"""请分析以下教师的教学需求输入，提取结构化的教学要素：

教师输入：{user_input}

"""

        if conversation_history:
            prompt += f"\n对话历史：\n"
            for msg in conversation_history[-5:]:  # 只取最近5轮对话
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                prompt += f"{role}: {content}\n"

        prompt += """
请以JSON格式返回分析结果，包含以下字段：
{
    "teaching_objective": {
        "knowledge_objective": "知识目标：学生应该掌握的具体知识内容",
        "ability_objective": "能力目标：学生应该具备的技能和能力",
        "quality_objective": "素养目标：学生应该培养的综合素质和价值观"
    },
    "duration": "授课时长（如：45分钟、90分钟）",
    "knowledge_points": ["知识点1", "知识点2", ...],
    "key_difficulties": {
        "key_points": ["教学重点1", "教学重点2"],
        "difficult_points": [{"content": "教学难点内容", "reason": "难点成因解释"}]
    },
    "target_grade": "受众年级（如：大学一年级高职学生）",
    "audience_analysis": {
        "prerequisite_knowledge": "前置知识要求",
        "cognitive_misconceptions": ["学生容易存在的认知误区1", "认知误区2"]
    },
    "classroom_activities": [
        {
            "activity": "活动名称",
            "description": "活动描述",
            "interaction_type": "问答/讨论/游戏/演示"
        }
    ],
    "classroom_questions": ["课堂提问1", "课堂提问2", "课堂提问3"],
    "style_preference": "课件风格偏好（如：简洁现代、活泼生动、专业严谨）",
    "special_requirements": "其他特殊要求",
    "missing_fields": ["缺失的字段1", "缺失的字段2", ...],
    "clarification_question": "如果信息缺失，生成一个针对性的追问问题，优先追问最重要的缺失信息"
}

注意事项：
1. 如果对话历史中已经包含了某些信息，请在分析时融合这些信息
2. 追问问题应该具体、有针对性，不要一次问太多问题
3. 优先追问教学目标、授课时长、知识点、受众年级这四个核心信息
4. 教学目标必须按照知识、能力、素养三层进行拆解，不能简单复制用户原话
5. 重难点要区分重点和难点，并解释难点成因
6. 要预判学生的前置知识和认知误区
7. 自动生成3-5个适配知识点的课堂提问
"""

        try:
            result = self.llm_client.structured_completion(prompt, self.system_prompt, rag_context=rag_context)
            logger.info(f"意图分析完成: {result.get('teaching_objective', 'N/A')}")
            return result
        except Exception as e:
            logger.error(f"意图分析失败: {e}")
            # LLM调用失败时返回降级结果
            return {
                "error": str(e),
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
    
    def generate_clarification(self, current_intent: Dict) -> str:
        """
        根据当前意图状态生成追问问题
        
        Args:
            current_intent: 当前已提取的意图信息
            
        Returns:
            追问问题
        """
        missing_fields = current_intent.get('missing_fields', [])
        
        if not missing_fields:
            return None
        
        # 优先追问重要字段
        priority_fields = ['教学目标', '授课时长', '知识点', '受众年级']
        for field in priority_fields:
            if any(field in mf for mf in missing_fields):
                return f"请提供{field}信息，这将帮助我更好地为您生成课件。"
        
        return f"还需要了解以下信息：{', '.join(missing_fields[:3])}"
    
    def summarize_intent(self, intent: Dict) -> str:
        """
        总结教学意图
        
        Args:
            intent: 意图信息字典
            
        Returns:
            总结文本
        """
        # 适配新的教学目标结构
        teaching_objective = intent.get('teaching_objective', {})
        if isinstance(teaching_objective, dict):
            objective_text = f"""
知识目标：{teaching_objective.get('knowledge_objective', '未指定')}
能力目标：{teaching_objective.get('ability_objective', '未指定')}
素养目标：{teaching_objective.get('quality_objective', '未指定')}
"""
        else:
            objective_text = f"教学目标：{teaching_objective}"
        
        # 适配新的重难点结构
        key_difficulties = intent.get('key_difficulties', {})
        if isinstance(key_difficulties, dict):
            key_points = key_difficulties.get('key_points', [])
            difficult_points = key_difficulties.get('difficult_points', [])
            if difficult_points and isinstance(difficult_points[0], dict):
                difficulties_text = '\n'.join([f"{dp.get('content', '')}（{dp.get('reason', '')}）" for dp in difficult_points])
            else:
                difficulties_text = ', '.join(difficult_points)
            difficulties = f"教学重点：{', '.join(key_points)}\n教学难点：{difficulties_text}"
        else:
            difficulties = f"教学重难点：{', '.join(key_difficulties)}"
        
        # 适配新的受众分析结构
        audience_analysis = intent.get('audience_analysis', {})
        if isinstance(audience_analysis, dict):
            audience_text = f"""
前置知识：{audience_analysis.get('prerequisite_knowledge', '未指定')}
认知误区：{', '.join(audience_analysis.get('cognitive_misconceptions', []))}
"""
        else:
            audience_text = ""
        
        # 适配新的课堂活动结构
        classroom_activities = intent.get('classroom_activities', [])
        if classroom_activities and isinstance(classroom_activities[0], dict):
            activities_text = '\n'.join([f"{act.get('activity', '')}: {act.get('description', '')}" for act in classroom_activities])
        else:
            activities_text = ', '.join(classroom_activities)
        
        # 获取课堂提问
        classroom_questions = intent.get('classroom_questions', [])
        questions_text = '\n'.join([f"{i+1}. {q}" for i, q in enumerate(classroom_questions)])
        
        summary = f"""
【教学需求确认】
{objective_text}
授课时长：{intent.get('duration', '未指定')}
受众年级：{intent.get('target_grade', '未指定')}
{audience_text}
知识点：{', '.join(intent.get('knowledge_points', []))}
{difficulties}
课堂活动：
{activities_text}
课堂提问：
{questions_text}
课件风格：{intent.get('style_preference', '未指定')}
特殊要求：{intent.get('special_requirements', '无')}
"""
        return summary.strip()
    
    def check_completeness(self, intent: Dict) -> bool:
        """
        检查意图信息是否完整
        
        Args:
            intent: 意图信息字典
            
        Returns:
            是否完整
        """
        # 检查新的数据结构
        teaching_objective = intent.get('teaching_objective')
        if teaching_objective:
            # 新结构：检查三层目标
            if isinstance(teaching_objective, dict):
                has_objective = any([
                    teaching_objective.get('knowledge_objective'),
                    teaching_objective.get('ability_objective'),
                    teaching_objective.get('quality_objective')
                ])
            else:
                # 兼容旧结构
                has_objective = bool(teaching_objective)
        else:
            has_objective = False
        
        if not has_objective:
            logger.info("意图信息不完整，缺失教学目标")
            return False
        
        if not intent.get('duration'):
            logger.info("意图信息不完整，缺失授课时长")
            return False
        
        if not intent.get('knowledge_points'):
            logger.info("意图信息不完整，缺失知识点")
            return False
        
        if not intent.get('target_grade'):
            logger.info("意图信息不完整，缺失受众年级")
            return False
        
        return True

    def apply_modification(self, current_intent: Dict, modification: str) -> Dict:
        """
        应用用户修改指令到当前意图
        
        Args:
            current_intent: 当前意图信息
            modification: 用户修改指令
            
        Returns:
            更新后的意图信息
        """
        # 构建修改指令处理提示词
        prompt = f"""请根据用户的修改指令，更新当前的教学意图信息。

当前教学意图：
{json.dumps(current_intent, ensure_ascii=False, indent=2)}

用户修改指令：{modification}

请以JSON格式返回更新后的教学意图，保持原有的字段结构。如果修改指令涉及某个字段的更新，请更新该字段；如果涉及新增内容，请相应添加。注意教学目标需要按照知识、能力、素养三层结构返回。

返回格式：
{{
    "teaching_objective": {{
        "knowledge_objective": "知识目标",
        "ability_objective": "能力目标", 
        "quality_objective": "素养目标"
    }},
    "duration": "更新后的授课时长",
    "knowledge_points": ["更新后的知识点列表"],
    "key_difficulties": {{
        "key_points": ["教学重点"],
        "difficult_points": [{{"content": "教学难点", "reason": "难点成因"}}]
    }},
    "target_grade": "更新后的受众年级",
    "audience_analysis": {{
        "prerequisite_knowledge": "前置知识",
        "cognitive_misconceptions": ["认知误区"]
    }},
    "classroom_activities": [
        {{
            "activity": "活动名称",
            "description": "活动描述",
            "interaction_type": "互动类型"
        }}
    ],
    "classroom_questions": ["课堂提问"],
    "style_preference": "更新后的风格偏好",
    "special_requirements": "更新后的特殊要求",
    "missing_fields": [],
    "clarification_question": ""
}}
"""

        try:
            updated_intent = self.llm_client.structured_completion(prompt, self.system_prompt)
            logger.info(f"修改指令应用完成: {modification}")
            # 确保返回的数据结构完整
            if not isinstance(updated_intent.get('teaching_objective'), dict):
                # 如果返回的是旧结构，进行转换
                old_objective = updated_intent.get('teaching_objective', '')
                updated_intent['teaching_objective'] = {
                    "knowledge_objective": old_objective,
                    "ability_objective": "",
                    "quality_objective": ""
                }
            if not isinstance(updated_intent.get('key_difficulties'), dict):
                # 如果返回的是旧结构，进行转换
                old_difficulties = updated_intent.get('key_difficulties', [])
                updated_intent['key_difficulties'] = {
                    "key_points": old_difficulties[:len(old_difficulties)//2] if old_difficulties else [],
                    "difficult_points": [{"content": dp, "reason": ""} for dp in (old_difficulties[len(old_difficulties)//2:] if old_difficulties else [])]
                }
            if not isinstance(updated_intent.get('audience_analysis'), dict):
                # 如果缺少受众分析，添加默认值
                updated_intent['audience_analysis'] = {
                    "prerequisite_knowledge": "",
                    "cognitive_misconceptions": []
                }
            if 'classroom_questions' not in updated_intent:
                # 如果缺少课堂提问，添加默认值
                updated_intent['classroom_questions'] = []
            return updated_intent
        except Exception as e:
            logger.error(f"修改指令应用失败: {e}")
            # 降级处理：返回原意图
            return current_intent


# 全局意图分析器实例
_intent_analyzer = None


def get_intent_analyzer() -> IntentAnalyzer:
    """
    获取全局意图分析器实例（单例模式）
    
    Returns:
        IntentAnalyzer实例
    """
    global _intent_analyzer
    if _intent_analyzer is None:
        _intent_analyzer = IntentAnalyzer()
    return _intent_analyzer
