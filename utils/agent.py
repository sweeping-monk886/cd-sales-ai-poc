"""
Agent核心模块 - 意图识别与路由
"""
from typing import Tuple
from utils.knowledge import get_knowledge_base
from utils.data_query import generate_sql, execute_sql, format_query_result, generate_data_insight
from utils.insight import get_insight_engine, format_insights_report


class SalesAgent:
    """销售AI助手"""
    
    def __init__(self):
        self.knowledge_base = get_knowledge_base()
        self.insight_engine = get_insight_engine()
    
    def classify_intent(self, question: str) -> str:
        """意图识别"""
        question = question.lower()
        
        # 问知关键词
        knowledge_keywords = [
            '是什么', '介绍', '功能', '参数', '配置', '特点', '卖点',
            '对比', '区别', '优势', '劣势', '话术', '怎么', '如何',
            '多少钱', '价格', '优惠', '活动', '质保', '安装', '售后',
            '问题', '解答', '说明', '手册', 'FAQ'
        ]
        
        # 问数关键词
        data_keywords = [
            '查询', '查看', '数据', '统计', '报表', '销量', '销售额',
            '完成率', '排名', '排行', 'TOP', 'top', '趋势', '走势',
            '多少', '几个', '几个', '总计', '汇总', '明细',
            '哪些', '哪些', '哪些', '分析'
        ]
        
        # 洞察关键词
        insight_keywords = [
            '洞察', '分析', '建议', '预警', '预测', '趋势',
            '今天', '最近', '关注', '重点', '异常', '问题',
            '怎么办', '建议', '行动', '策略'
        ]
        
        # 计算匹配分数
        knowledge_score = sum(1 for kw in knowledge_keywords if kw in question)
        data_score = sum(1 for kw in data_keywords if kw in question)
        insight_score = sum(1 for kw in insight_keywords if kw in question)
        
        # 简单路由
        scores = {
            'knowledge': knowledge_score,
            'data': data_score,
            'insight': insight_score
        }
        
        max_score = max(scores.values())
        if max_score == 0:
            return 'knowledge'  # 默认问知
        
        return max(scores, key=scores.get)
    
    def answer(self, question: str) -> Tuple[str, str]:
        """
        回答用户问题
        返回: (回答内容, 意图类型)
        """
        intent = self.classify_intent(question)
        
        if intent == 'knowledge':
            return self._handle_knowledge(question), '问知'
        elif intent == 'data':
            return self._handle_data(question), '问数'
        elif intent == 'insight':
            return self._handle_insight(question), '洞察'
        else:
            return self._handle_knowledge(question), '问知'
    
    def _handle_knowledge(self, question: str) -> str:
        """处理知识查询"""
        context = self.knowledge_base.get_context_for_query(question)
        
        prompt = f"""你是一位专业的家电销售顾问助手。
        
基于以下知识库内容回答用户问题：

{context}

用户问题: {question}

请给出专业、清晰的回答。如果知识库中没有相关信息，请说明。"""
        
        # 简化版：直接返回知识库检索结果
        results = self.knowledge_base.search(question, top_k=3)
        
        if not results:
            return "抱歉，知识库中暂未找到相关信息。建议您：\n1. 换个方式描述问题\n2. 联系产品部门获取最新信息"
        
        response_parts = [f"📚 **知识库检索结果** (共{len(results)}条相关)：\n"]
        
        for i, result in enumerate(results, 1):
            response_parts.append(f"**【{result['source']}】**")
            response_parts.append(result['content'][:500])  # 限制长度
            response_parts.append("---")
        
        return "\n".join(response_parts)
    
    def _handle_data(self, question: str) -> str:
        """处理数据查询"""
        # 生成SQL
        sql = generate_sql(question)
        
        # 执行查询
        df, error = execute_sql(sql)
        
        if error:
            return f"❌ 查询执行出错：{error}\n\n生成的SQL:\n```sql\n{sql}\n```"
        
        # 格式化结果
        result = format_query_result(df, question)
        
        # 生成数据洞察
        insight = generate_data_insight(df, question)
        
        # 组合回答
        response = f"🔍 **查询意图**: {question}\n\n"
        response += f"📝 **执行SQL**:\n```sql\n{sql.strip()}\n```\n\n"
        response += result
        
        if insight:
            response += f"\n\n{insight}"
        
        return response
    
    def _handle_insight(self, question: str) -> str:
        """处理洞察请求"""
        # 生成洞察报告
        insights = self.insight_engine.generate_daily_insights()
        report = format_insights_report(insights)
        
        return report


# 单例实例
_agent = None

def get_agent() -> SalesAgent:
    global _agent
    if _agent is None:
        _agent = SalesAgent()
    return _agent
