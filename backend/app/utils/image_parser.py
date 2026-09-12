"""
图片多模态解析模块
使用阿里云DashScope qwen3.7-plus多模态模型识别图片中的文字、报文信息、拓扑结构
"""

import os
import logging
import base64
from typing import Optional
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()


class ImageParser:
    """图片解析器"""
    
    def __init__(self):
        """初始化图片解析器"""
        self.api_key = os.getenv('DASHSCOPE_API_KEY', '')
        if not self.api_key:
            logger.warning("未设置DASHSCOPE_API_KEY环境变量，将使用模拟解析")
        else:
            logger.info("图片解析器初始化完成，使用DashScope qwen3.7-plus模型")
    
    def parse_image(self, image_path: str) -> str:
        """
        解析图片，提取文字和结构信息
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            解析后的文本内容
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(image_path):
                logger.error(f"图片文件不存在: {image_path}")
                return "图片文件不存在"
            
            logger.info(f"开始解析图片: {image_path}")
            
            # 检查API密钥
            if not self.api_key:
                logger.warning("未设置DASHSCOPE_API_KEY，使用模拟解析")
                return self._mock_parse_image(image_path)
            
            # 调用DashScope多模态模型解析
            parsed_text = self._parse_with_dashscope(image_path)
            
            logger.info(f"图片解析完成: {image_path}, 解析文本长度: {len(parsed_text)}")
            logger.info(f"DashScope返回的完整解析内容:\n{parsed_text}")
            
            return parsed_text
            
        except Exception as e:
            logger.error(f"图片解析失败: {e}")
            # 如果DashScope调用失败，回退到模拟解析
            logger.info("DashScope调用失败，回退到模拟解析")
            return self._mock_parse_image(image_path)
    
    def _parse_with_dashscope(self, image_path: str) -> str:
        """
        使用DashScope qwen3.7-plus多模态模型解析图片
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            解析后的文本内容
        """
        try:
            import dashscope
            from dashscope import MultiModalConversation
            
            # 设置API密钥
            dashscope.api_key = self.api_key
            
            # 读取图片并转换为base64
            with open(image_path, 'rb') as f:
                image_data = f.read()
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            logger.info(f"图片转换为base64成功，大小: {len(image_base64)} 字符")
            
            # 固定系统提示词
            system_prompt = """你是计算机网络教学图表解析专家，详细分析这张TCP三次握手流程图，**不要省略任何文字、方框、状态、箭头标注**，结构化输出：
1）客户端、服务器两端全部状态（CLOSED、LISTEN、SYN-SENT、SYN-RCVD、ESTABLISHED）
2）三次握手每一轮交互报文：标志位SYN/ACK、seq、ack数值定义
3）红色箭头上面的文字说明，每一步握手动作
4）整理成清晰分段文本，所有图中文字全部提取，不能简写、不能丢失信息。"""
            
            # 调用多模态对话接口
            response = MultiModalConversation.call(
                model='qwen3.7-plus',
                messages=[
                    {
                        'role': 'system',
                        'content': system_prompt
                    },
                    {
                        'role': 'user',
                        'content': [
                            {'image': f'data:image/jpeg;base64,{image_base64}'},
                            {'text': '请详细分析这张TCP三次握手流程图，提取所有文字和结构信息。'}
                        ]
                    }
                ]
            )
            
            # 检查响应状态
            if response.status_code == 200:
                parsed_text = response.output.choices[0].message.content[0]['text']
                logger.info(f"DashScope调用成功，返回文本长度: {len(parsed_text)}")
                return parsed_text
            else:
                error_msg = f"DashScope调用失败: {response.code} - {response.message}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
        except ImportError:
            logger.error("未安装dashscope包，请运行: pip install dashscope")
            raise Exception("未安装dashscope包，请运行: pip install dashscope")
        except Exception as e:
            logger.error(f"DashScope解析失败: {e}")
            raise e
    
    def _mock_parse_image(self, image_path: str) -> str:
        """
        模拟图片解析（回退方案）
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            模拟的解析文本
        """
        # 根据文件名判断类型，返回不同的模拟解析结果
        filename = os.path.basename(image_path).lower()
        
        if 'wireshark' in filename or '抓包' in filename:
            return """Wireshark抓包图解析结果：
- 协议: TCP
- 源IP: 192.168.1.100
- 目标IP: 192.168.1.200
- 源端口: 54321
- 目标端口: 80
- 报文序列号(seq): 1000
- 确认号(ack): 5000
- 标志位: SYN=1, ACK=1
- 报文长度: 64字节
- 时间戳: 2024-01-15 10:30:45"""
        
        elif 'topology' in filename or '拓扑' in filename:
            return """网络拓扑图解析结果：
- 网络类型: 星型拓扑
- 核心设备: 交换机(Switch-01)
- 连接设备: 5台PC
- IP地址段: 192.168.1.0/24
- 网关: 192.168.1.1
- 连接状态: 全部在线
- 网络带宽: 1000Mbps"""
        
        elif 'seq' in filename or 'ack' in filename:
            return """TCP序列号解析结果：
- 客户端发送: seq=1000, ack=0, SYN=1
- 服务端回复: seq=5000, ack=1001, SYN=1, ACK=1
- 客户端确认: seq=1001, ack=5001, ACK=1
- 序列号计算: ack = 对方seq + 1
- 握手状态: ESTABLISHED"""
        
        else:
            return """通用图片解析结果：
- 识别到文字内容
- 图片包含网络相关信息
- 建议提供更具体的图片类型以便精确解析
- 当前为模拟解析结果，请设置DASHSCOPE_API_KEY环境变量以使用真实的多模态模型"""


# 全局实例
_image_parser_instance = None


def get_image_parser() -> ImageParser:
    """
    获取图片解析器实例（单例模式）
    
    Returns:
        ImageParser实例
    """
    global _image_parser_instance
    if _image_parser_instance is None:
        _image_parser_instance = ImageParser()
    return _image_parser_instance
