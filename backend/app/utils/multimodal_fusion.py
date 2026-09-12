"""
多模态融合模块
融合教师意图、上传参考资料、本地RAG知识库，生成课件生成指令
"""

import logging
from typing import Dict, List, Optional
from .llm_client import get_llm_client
from ..rags.knowledge_base import get_knowledge_base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MultimodalFusion:
    """多模态信息融合器"""
    
    def __init__(self):
        """初始化融合器"""
        self.llm_client = get_llm_client()
        self.knowledge_base = get_knowledge_base()
        self.system_prompt = """你是一位专业的教学课件设计专家，擅长融合多模态信息生成高质量的教学课件。
你的任务是根据教师意图、参考资料和知识库内容，生成标准化的课件生成指令。"""
    
    def fuse(self, 
             teacher_intent: Dict, 
             reference_materials: List[Dict] = None, 
             use_knowledge_base: bool = True) -> Dict:
        """
        融合多模态信息
        
        Args:
            teacher_intent: 教师意图信息
            reference_materials: 参考资料解析结果列表
            use_knowledge_base: 是否使用知识库检索
            
        Returns:
            融合后的课件生成指令
        """
        # 1. 从知识库检索相关内容
        kb_context = ""
        if use_knowledge_base:
            kb_context = self._retrieve_from_knowledge_base(teacher_intent)
        
        # 2. 整理参考资料内容
        ref_context = self._format_reference_materials(reference_materials)
        
        # 3. 构建融合提示词
        prompt = self._build_fusion_prompt(teacher_intent, kb_context, ref_context)
        
        # 4. 调用大模型生成融合指令（此处不需要RAG，因为已经手动检索了知识库）
        try:
            fusion_result = self.llm_client.structured_completion(prompt, self.system_prompt, use_rag=False)
            logger.info("多模态信息融合完成")
            return fusion_result
        except Exception as e:
            logger.error(f"信息融合失败: {e}")
            # 使用降级融合策略
            return self._fallback_fusion(teacher_intent, reference_materials)
    
    def _retrieve_from_knowledge_base(self, intent: Dict, top_k: int = 5) -> str:
        """
        从知识库检索相关内容
        
        Args:
            intent: 教师意图
            top_k: 检索数量
            
        Returns:
            检索到的知识库内容
        """
        # 构建查询
        query_parts = []
        
        # 处理教学目标（可能是字典或字符串）
        teaching_objective = intent.get('teaching_objective')
        if teaching_objective:
            if isinstance(teaching_objective, dict):
                # 新结构：提取三层目标
                for obj_type in ['knowledge_objective', 'ability_objective', 'quality_objective']:
                    obj_value = teaching_objective.get(obj_type)
                    if obj_value:
                        query_parts.append(str(obj_value))
            else:
                # 旧结构：直接添加
                query_parts.append(str(teaching_objective))
        
        # 处理知识点
        knowledge_points = intent.get('knowledge_points', [])
        if knowledge_points:
            if isinstance(knowledge_points, list):
                query_parts.extend([str(point) for point in knowledge_points])
            else:
                query_parts.append(str(knowledge_points))
        
        # 处理重难点（可能是字典或列表）
        key_difficulties = intent.get('key_difficulties')
        if key_difficulties:
            if isinstance(key_difficulties, dict):
                # 新结构：提取重点和难点
                key_points = key_difficulties.get('key_points', [])
                if key_points:
                    query_parts.extend([str(point) for point in key_points])
                
                difficult_points = key_difficulties.get('difficult_points', [])
                if difficult_points:
                    if isinstance(difficult_points[0], dict) if difficult_points else False:
                        # 难点是字典列表
                        for dp in difficult_points:
                            if isinstance(dp, dict):
                                dp_content = dp.get('content', '')
                                if dp_content:
                                    query_parts.append(str(dp_content))
                            else:
                                query_parts.append(str(dp))
                    else:
                        # 难点是字符串列表
                        query_parts.extend([str(dp) for dp in difficult_points])
            else:
                # 旧结构：直接添加
                if isinstance(key_difficulties, list):
                    query_parts.extend([str(item) for item in key_difficulties])
                else:
                    query_parts.append(str(key_difficulties))
        
        # 处理受众年级
        target_grade = intent.get('target_grade')
        if target_grade:
            query_parts.append(str(target_grade))
        
        if not query_parts:
            return ""
        
        query = " ".join(query_parts)
        
        try:
            results = self.knowledge_base.search(query, top_k=top_k)
            
            if not results:
                logger.info("知识库未检索到相关内容")
                return ""
            
            # 格式化检索结果
            kb_content = "【知识库相关内容】\n"
            for i, result in enumerate(results, 1):
                kb_content += f"{i}. {result['content']}\n"
                if result.get('metadata'):
                    kb_content += f"   来源: {result['metadata'].get('source', '未知')}\n"
            
            logger.info(f"从知识库检索到 {len(results)} 条相关内容")
            return kb_content
        except Exception as e:
            logger.error(f"知识库检索失败: {e}")
            return ""
    
    def _format_reference_materials(self, materials: List[Dict]) -> str:
        """
        格式化参考资料
        
        Args:
            materials: 参考资料列表
            
        Returns:
            格式化后的参考资料内容
        """
        if not materials:
            return ""
        
        ref_content = "【上传的参考资料】\n"
        
        for i, material in enumerate(materials, 1):
            file_name = material.get('file_name', f'文件{i}')
            file_type = material.get('file_type', 'unknown')
            full_text = material.get('full_text', '')
            
            ref_content += f"\n{i}. {file_name} ({file_type})\n"
            
            # 根据文件类型提取关键信息
            if file_type == 'pdf':
                ref_content += f"   页数: {material.get('total_pages', 'N/A')}\n"
            elif file_type == 'pptx':
                ref_content += f"   幻灯片数: {material.get('total_slides', 'N/A')}\n"
            elif file_type == 'video':
                ref_content += f"   时长: {material.get('duration', 'N/A')}秒\n"
            
            # 添加文本内容（限制长度）
            if full_text:
                ref_content += f"   内容摘要: {full_text[:500]}...\n"
        
        return ref_content
    
    def _build_fusion_prompt(self, intent: Dict, kb_context: str, ref_context: str) -> str:
        """
        构建融合提示词
        
        Args:
            intent: 教师意图
            kb_context: 知识库上下文
            ref_context: 参考资料上下文
            
        Returns:
            融合提示词
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
            if isinstance(difficult_points[0], dict) if difficult_points else False:
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
        
        prompt = f"""请根据以下信息，生成标准化的课件生成指令：

【教师教学意图】
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

        if kb_context:
            prompt += kb_context + "\n"
        
        if ref_context:
            prompt += ref_context + "\n"
        
        prompt += """
请以JSON格式返回课件生成指令，包含以下字段：
{
    "course_title": "课件标题",
    "teaching_objective": "教学目标（详细描述）",
    "target_audience": "目标受众",
    "duration": "授课时长",
    "knowledge_structure": [
        {
            "module": "模块名称",
            "points": ["知识点1", "知识点2"]
        }
    ],
    "key_points": ["重点1", "重点2"],
    "difficult_points": ["难点1", "难点2"],
    "teaching_flow": [
        {
            "stage": "导入/新授/练习/总结",
            "content": "阶段内容描述",
            "time_allocation": "时间分配"
        }
    ],
    "classroom_activities": [
        {
            "activity": "活动名称",
            "description": "活动描述",
            "interaction_type": "问答/讨论/游戏/演示"
        }
    ],
    "homework": "课后作业设计",
    "blackboard_design": "板书设计",
    "ppt_structure": [
        {
            "slide_type": "封面/目录/知识页/案例页/互动页/总结页/结尾页",
            "title": "幻灯片标题",
            "content": "幻灯片内容要点",
            "visual_elements": "视觉元素建议"
        }
    ],
    "interactive_game": {
        "type": "问答游戏/填空游戏/配对游戏",
        "title": "游戏标题",
        "content": "游戏内容设计"
    }
}
"""
        return prompt
    
    def _fallback_fusion(self, intent: Dict, materials: List[Dict]) -> Dict:
        """
        降级融合策略（当大模型调用失败时）
        
        Args:
            intent: 教师意图
            materials: 参考资料
            
        Returns:
            基础融合结果
        """
        logger.warning("使用降级融合策略")
        
        # 适配新的教学目标结构
        teaching_objective = intent.get('teaching_objective', {})
        if isinstance(teaching_objective, dict):
            objective_text = teaching_objective.get('knowledge_objective', '教学课件')
        else:
            objective_text = teaching_objective if teaching_objective else '教学课件'
        
        # 适配新的重难点结构
        key_difficulties = intent.get('key_difficulties', {})
        if isinstance(key_difficulties, dict):
            key_points = key_difficulties.get('key_points', ['重点1'])
            difficult_points = key_difficulties.get('difficult_points', [{'content': '难点1', 'reason': '难理解'}])
            if difficult_points and isinstance(difficult_points[0], dict):
                difficult_content = [dp.get('content', '难点') for dp in difficult_points]
            else:
                difficult_content = difficult_points
        else:
            key_points = key_difficulties[:len(key_difficulties)//2] if key_difficulties else ['重点1']
            difficult_content = key_difficulties[len(key_difficulties)//2:] if key_difficulties else ['难点1']
        
        # 适配新的课堂活动结构
        classroom_activities = intent.get('classroom_activities', [])
        if classroom_activities and isinstance(classroom_activities[0], dict):
            activities = classroom_activities
        else:
            activities = [
                {
                    "activity": activity,
                    "description": f"{activity}互动环节",
                    "interaction_type": "讨论"
                } for activity in (classroom_activities if classroom_activities else ['课堂讨论'])
            ]
        
        return {
            "course_title": objective_text,
            "teaching_objective": objective_text,
            "target_audience": intent.get('target_grade', ''),
            "duration": intent.get('duration', '45分钟'),
            "knowledge_structure": [
                {
                    "module": "知识模块",
                    "points": intent.get('knowledge_points', ['知识点1', '知识点2'])
                }
            ],
            "key_points": key_points,
            "difficult_points": difficult_content,
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
            "classroom_activities": activities,
            "homework": "完成课后练习题",
            "blackboard_design": "板书设计待完善",
            "ppt_structure": [
                {
                    "slide_type": "cover",
                    "title": objective_text,
                    "content": "课程标题、授课教师、日期",
                    "visual_elements": "简洁大气的封面设计"
                },
                {
                    "slide_type": "directory",
                    "title": "课程目录",
                    "content": "列出主要章节",
                    "visual_elements": "清晰的目录结构"
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


# 全局融合器实例
_multimodal_fusion = None


def get_multimodal_fusion() -> MultimodalFusion:
    """
    获取全局融合器实例（单例模式）
    
    Returns:
        MultimodalFusion实例
    """
    global _multimodal_fusion
    if _multimodal_fusion is None:
        _multimodal_fusion = MultimodalFusion()
    return _multimodal_fusion
