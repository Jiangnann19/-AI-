import json
import os
import re
import logging

# 知识库存储路径
DB_PATH = "./backend/knowledge_base/knowledge.json"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JsonKnowledgeBase:
    def __init__(self):
        self.init_db()

    def init_db(self):
        if not os.path.exists(os.path.dirname(DB_PATH)):
            os.makedirs(os.path.dirname(DB_PATH))
        if not os.path.exists(DB_PATH):
            with open(DB_PATH, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False)

    # 文本分块，和原接口保持一致
    def chunk_text(self, text, chunk_size=500, overlap=50):
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start += (chunk_size - overlap)
        return chunks

    # 添加文档，兼容metadatas参数
    def add_documents(self, chunks, metadatas=None):
        self.init_db()
        with open(DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if metadatas is None:
            metadatas = [{} for _ in chunks]
        
        added_count = 0
        for idx, chunk in enumerate(chunks):
            meta = metadatas[idx] if idx < len(metadatas) else {}
            # 只有当chunk不为空时才添加
            if chunk and chunk.strip():
                data.append({
                    "content": chunk,
                    "metadata": meta
                })
                added_count += 1
        
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"知识库入库完成: 尝试添加{len(chunks)}个块，成功入库{added_count}个块")
        return added_count

    def search(self, query, top_k=5, similarity_threshold=0.015):
        self.init_db()
        with open(DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 中文直接子串包含匹配，不再使用\w+正则
        query_str = query.strip().lower()
        scored = []
        
        for item in data:
            text_low = item["content"].lower()
            if query_str in text_low:
                # 优化相似度计算
                match_count = text_low.count(query_str)
                match_length = len(query_str) * match_count
                text_length = len(text_low)
                
                # 基础相似度：匹配长度占比
                base_similarity = match_length / text_length if text_length > 0 else 0
                
                # 奖励因子：出现次数越多，相似度越高
                count_bonus = min(match_count * 0.1, 0.5)  # 最多增加0.5
                
                # 位置奖励：查询词出现在文本开头（前20%）有额外奖励
                first_occurrence = text_low.find(query_str)
                position_bonus = 0
                if first_occurrence >= 0 and first_occurrence < len(text_low) * 0.2:
                    position_bonus = 0.2
                
                # 综合相似度
                similarity = base_similarity + count_bonus + position_bonus
                similarity = min(similarity, 1.0)  # 限制最大为1.0
                
                # 匹配成功，加入结果
                scored.append((similarity, item["content"], item["metadata"]))
        
        # 按相似度降序排序
        scored.sort(reverse=True)
        
        result_list = []
        for item in scored[:top_k]:
            similarity = item[0]
            # 生成简短预览标题（取匹配位置前后20字符）
            content_lower = item[1].lower()
            match_pos = content_lower.find(query_str)
            preview_start = max(0, match_pos - 20)
            preview_end = min(len(item[1]), match_pos + len(query_str) + 20)
            preview = item[1][preview_start:preview_end]
            if preview_start > 0:
                preview = "..." + preview
            if preview_end < len(item[1]):
                preview = preview + "..."
            
            result_list.append({
                "content": item[1],
                "metadata": item[2],
                "distance": 1 - similarity,  # 兼容前端distance字段
                "similarity": similarity,  # 新增相似度字段
                "preview": preview,  # 新增预览字段
                "is_low_similarity": similarity < similarity_threshold  # 新增低相似度标记
            })
        
        # 打印检索结果日志
        logger.info(f"知识库检索: 查询='{query}', 返回{len(result_list)}个结果")
        for i, result in enumerate(result_list):
            logger.info(f"  结果{i+1}: 相似度={result['similarity']:.4f}, 预览='{result['preview'][:50]}...'")
        
        # 边界处理：即使相似度较低，也返回匹配度最高的结果
        if not result_list and data:
            # 如果没有精确匹配，返回最接近的片段（基于字符重叠）
            logger.warning(f"未找到精确匹配，尝试返回最接近的片段")
            best_match = None
            best_score = 0
            
            for item in data:
                # 计算字符重叠度
                overlap = len(set(query_str) & set(item["content"].lower()))
                score = overlap / len(item["content"]) if item["content"] else 0
                if score > best_score:
                    best_score = score
                    best_match = item
            
            if best_match:
                preview = best_match["content"][:100]
                if len(best_match["content"]) > 100:
                    preview += "..."
                result_list.append({
                    "content": best_match["content"],
                    "metadata": best_match["metadata"],
                    "distance": 1 - best_score,
                    "similarity": best_score,
                    "preview": preview,
                    "is_low_similarity": True
                })
                logger.info(f"  返回最接近片段: 相似度={best_score:.4f}")
        
        return result_list


    # 知识库统计
    def get_stats(self):
        self.init_db()
        with open(DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 统计每个文档的块数
        doc_stats = {}
        for item in data:
            source = item.get("metadata", {}).get("source", "unknown")
            doc_stats[source] = doc_stats.get(source, 0) + 1
        
        return {
            "total_chunks": len(data),
            "total_documents": len(data),  # 兼容前端接口
            "documents": list(doc_stats.keys()),  # 文档列表
            "doc_stats": doc_stats  # 每个文档的块数统计
        }
    
    # 删除指定文档的所有块
    def delete_document(self, source_name):
        self.init_db()
        with open(DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        original_count = len(data)
        # 过滤掉指定来源的块
        data = [item for item in data if item.get("metadata", {}).get("source") != source_name]
        deleted_count = original_count - len(data)
        
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"删除文档: {source_name}, 删除了{deleted_count}个块")
        return deleted_count
    
    # 清空知识库
    def clear_all(self):
        self.init_db()
        with open(DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        original_count = len(data)
        
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        
        logger.info(f"清空知识库: 删除了{original_count}个块")
        return original_count

# 全局单例
_kb_instance = None
def get_knowledge_base():
    global _kb_instance
    if _kb_instance is None:
        _kb_instance = JsonKnowledgeBase()
    return _kb_instance
