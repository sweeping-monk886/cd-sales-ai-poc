"""
问知能力 - RAG知识库检索
"""
import os
import glob
from typing import List, Dict

class KnowledgeBase:
    """简易知识库实现"""
    
    def __init__(self, knowledge_dir: str = "knowledge_base"):
        self.knowledge_dir = knowledge_dir
        self.documents = []
        self.load_documents()
    
    def load_documents(self):
        """加载所有知识库文档"""
        md_files = glob.glob(os.path.join(self.knowledge_dir, "*.md"))
        
        for file_path in md_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 按段落分割
            chunks = self._split_document(content)
            
            for chunk in chunks:
                self.documents.append({
                    "content": chunk,
                    "source": os.path.basename(file_path),
                    "file_path": file_path
                })
        
        print(f"📚 知识库加载完成: {len(self.documents)} 个文档片段")
    
    def _split_document(self, content: str, chunk_size: int = 500) -> List[str]:
        """将文档分割为小段落"""
        chunks = []
        lines = content.split('\n')
        current_chunk = []
        current_size = 0
        
        for line in lines:
            current_chunk.append(line)
            current_size += len(line)
            
            if current_size >= chunk_size or line.startswith('##'):
                if current_chunk:
                    chunk_text = '\n'.join(current_chunk)
                    if chunk_text.strip():
                        chunks.append(chunk_text)
                    current_chunk = []
                    current_size = 0
        
        # 处理最后剩余的内容
        if current_chunk:
            chunk_text = '\n'.join(current_chunk)
            if chunk_text.strip():
                chunks.append(chunk_text)
        
        return chunks
    
    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        """简易关键词匹配搜索"""
        import re
        
        # 清理查询
        query_clean = query.lower().replace('？', '').replace('。', '').replace('?', '').replace('.', '')
        
        # 提取关键词（中文2-4字词 + 英文单词）
        keywords = set()
        # 中文关键词（2-4字组合）
        chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,4}', query_clean)
        keywords.update(chinese_words)
        # 英文单词
        english_words = re.findall(r'[a-zA-Z0-9]+', query_clean)
        keywords.update([w.lower() for w in english_words])
        # 单个汉字也加入（重要字符）
        single_chars = re.findall(r'[\u4e00-\u9fa5]', query_clean)
        keywords.update(single_chars)
        
        results = []
        
        for doc in self.documents:
            content_lower = doc["content"].lower()
            # 计算匹配分数
            score = 0
            matched_keywords = []
            for kw in keywords:
                if kw in content_lower:
                    score += len(kw)  # 长关键词权重更高
                    matched_keywords.append(kw)
            
            if score > 0:
                results.append({
                    "content": doc["content"],
                    "source": doc["source"],
                    "score": score,
                    "matched": matched_keywords
                })
        
        # 按分数排序
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
    
    def get_context_for_query(self, query: str) -> str:
        """为LLM生成上下文"""
        results = self.search(query, top_k=3)
        
        if not results:
            return "未找到相关知识信息。"
        
        context_parts = []
        for i, result in enumerate(results, 1):
            context_parts.append(f"【来源: {result['source']}】\n{result['content']}")
        
        return "\n\n---\n\n".join(context_parts)


# 单例实例
_knowledge_base = None

def get_knowledge_base() -> KnowledgeBase:
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = KnowledgeBase()
    return _knowledge_base
