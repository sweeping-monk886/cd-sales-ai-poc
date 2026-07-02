"""
洞察能力 - 数据分析与主动建议
"""
import sqlite3
import pandas as pd
from datetime import datetime
from typing import List, Dict

DB_PATH = "data/sales.db"


class InsightEngine:
    """洞察引擎 - 生成前瞻性分析和行动建议"""
    
    def __init__(self):
        self.insights = []
    
    def generate_daily_insights(self) -> List[Dict]:
        """生成每日洞察报告"""
        self.insights = []
        conn = sqlite3.connect(DB_PATH)
        
        try:
            # 1. KPI完成率预警
            self._check_kpi_alerts(conn)
            
            # 2. 销售趋势分析
            self._analyze_sales_trend(conn)
            
            # 3. 区域对比分析
            self._analyze_region_performance(conn)
            
            # 4. 产品结构分析
            self._analyze_product_mix(conn)
            
            # 5. 生成行动建议
            self._generate_action_suggestions(conn)
            
        finally:
            conn.close()
        
        return self.insights
    
    def _check_kpi_alerts(self, conn):
        """检查KPI完成情况，生成预警"""
        query = """
        SELECT d.dealer_name, d.region, d.city, d.level,
               k.month, k.target_amount, k.actual_amount,
               ROUND(k.completion_rate * 100, 1) as completion_pct,
               k.rank_in_region
        FROM dealer_kpi k
        JOIN dealers d ON k.dealer_id = d.dealer_id
        WHERE k.month = (SELECT MAX(month) FROM dealer_kpi)
        ORDER BY k.completion_rate ASC
        """
        df = pd.read_sql_query(query, conn)
        
        # 严重未达标（<60%）
        critical = df[df['completion_pct'] < 60]
        if len(critical) > 0:
            for _, row in critical.iterrows():
                self.insights.append({
                    "type": "critical",
                    "icon": "🚨",
                    "title": f"严重预警: {row['dealer_name']}",
                    "detail": f"完成率仅{row['completion_pct']}%，"
                             f"目标{row['target_amount']:,.0f}，"
                             f"实际完成{row['actual_amount']:,.0f}，"
                             f"差距{row['target_amount']-row['actual_amount']:,.0f}",
                    "action": "建议立即联系经销商了解困难原因，安排销售总监上门辅导"
                })
        
        # 未达标（60-80%）
        warning = df[(df['completion_pct'] >= 60) & (df['completion_pct'] < 80)]
        if len(warning) > 0:
            names = ', '.join(warning['dealer_name'].head(5).tolist())
            self.insights.append({
                "type": "warning",
                "icon": "⚠️",
                "title": f"关注名单: {len(warning)}家经销商完成率偏低",
                "detail": f"包括: {names}，平均完成率{warning['completion_pct'].mean():.1f}%",
                "action": "建议逐一了解情况，提供促销方案支持或调整目标"
            })
        
        # 超额完成
        excellent = df[df['completion_pct'] >= 110]
        if len(excellent) > 0:
            names = ', '.join(excellent['dealer_name'].head(3).tolist())
            self.insights.append({
                "type": "positive",
                "icon": "🌟",
                "title": f"优秀表现: {len(excellent)}家经销商超额完成",
                "detail": f"包括: {names}，超额完成目标",
                "action": "建议总结优秀经验，组织区域分享会"
            })
    
    def _analyze_sales_trend(self, conn):
        """分析销售趋势"""
        query = """
        SELECT k.month, 
               SUM(k.actual_amount) as total_sales,
               ROUND(AVG(k.completion_rate) * 100, 1) as avg_completion
        FROM dealer_kpi k
        GROUP BY k.month
        ORDER BY k.month
        """
        df = pd.read_sql_query(query, conn)
        
        if len(df) >= 2:
            latest = df.iloc[-1]['total_sales']
            prev = df.iloc[-2]['total_sales']
            change = (latest - prev) / prev * 100
            
            if change < -10:
                self.insights.append({
                    "type": "warning",
                    "icon": "📉",
                    "title": "整体销售下滑",
                    "detail": f"环比下降{abs(change):.1f}%，"
                             f"本月{latest:,.0f}，上月{prev:,.0f}",
                    "action": "建议分析下滑原因，检查是否有市场变化或竞品冲击"
                })
            elif change > 10:
                self.insights.append({
                    "type": "positive",
                    "icon": "📈",
                    "title": "整体销售增长",
                    "detail": f"环比增长{change:.1f}%，"
                             f"本月{latest:,.0f}，上月{prev:,.0f}",
                    "action": "建议保持势头，总结成功经验"
                })
    
    def _analyze_region_performance(self, conn):
        """区域对比分析"""
        query = """
        SELECT d.region,
               COUNT(DISTINCT d.dealer_id) as dealer_count,
               SUM(k.actual_amount) as total_sales,
               ROUND(AVG(k.completion_rate) * 100, 1) as avg_completion
        FROM dealer_kpi k
        JOIN dealers d ON k.dealer_id = d.dealer_id
        WHERE k.month = (SELECT MAX(month) FROM dealer_kpi)
        GROUP BY d.region
        """
        df = pd.read_sql_query(query, conn)
        
        if len(df) >= 2:
            # 找出最差区域
            worst = df.nsmallest(1, 'avg_completion').iloc[0]
            best = df.nlargest(1, 'avg_completion').iloc[0]
            
            if worst['avg_completion'] < 80:
                self.insights.append({
                    "type": "warning",
                    "icon": "🗺️",
                    "title": f"{worst['region']}区域整体表现不佳",
                    "detail": f"平均完成率{worst['avg_completion']}%，"
                             f"共{worst['dealer_count']}家经销商，"
                             f"总销售额{worst['total_sales']:,.0f}",
                    "action": f"建议重点关注{worst['region']}区域，"
                             f"可参考{best['region']}区域（完成率{best['avg_completion']}%）的经验"
                })
    
    def _analyze_product_mix(self, conn):
        """产品结构分析"""
        query = """
        SELECT p.category,
               SUM(s.amount) as total_sales,
               SUM(s.quantity) as total_qty
        FROM sales_detail s
        JOIN products p ON s.product_id = p.product_id
        GROUP BY p.category
        """
        df = pd.read_sql_query(query, conn)
        
        if not df.empty:
            total = df['total_sales'].sum()
            df['pct'] = df['total_sales'] / total * 100
            
            # 检查品类集中度
            top_category = df.nlargest(1, 'pct').iloc[0]
            if top_category['pct'] > 60:
                self.insights.append({
                    "type": "info",
                    "icon": "📦",
                    "title": f"产品结构单一风险",
                    "detail": f"{top_category['category']}占比{top_category['pct']:.1f}%，"
                             f"建议关注其他品类",
                    "action": "建议加强空调/洗衣机等品类的推广，降低单一品类依赖"
                })
    
    def _generate_action_suggestions(self, conn):
        """生成综合行动建议"""
        # 获取当月数据概况
        query = """
        SELECT 
            COUNT(DISTINCT d.dealer_id) as total_dealers,
            ROUND(AVG(k.completion_rate) * 100, 1) as avg_completion,
            SUM(k.actual_amount) as total_sales,
            SUM(k.target_amount) as total_target
        FROM dealer_kpi k
        JOIN dealers d ON k.dealer_id = d.dealer_id
        WHERE k.month = (SELECT MAX(month) FROM dealer_kpi)
        """
        df = pd.read_sql_query(query, conn)
        
        if not df.empty:
            row = df.iloc[0]
            completion_gap = row['total_target'] - row['total_sales']
            
            if completion_gap > 0 and row['avg_completion'] < 90:
                days_left = 30  # 假设月底
                daily_needed = completion_gap / max(days_left, 1)
                
                self.insights.append({
                    "type": "action",
                    "icon": "🎯",
                    "title": "月度冲刺建议",
                    "detail": f"距目标还差{completion_gap:,.0f}，"
                             f"日均需完成{daily_needed:,.0f}",
                    "action": "建议: 1) 重点帮扶低完成率经销商; "
                             "2) 组织促销活动拉动; "
                             "3) 检查库存确保供货"
                })


def format_insights_report(insights: List[Dict]) -> str:
    """格式化洞察报告"""
    if not insights:
        return "今日暂无特殊洞察，业务运行正常。"
    
    report_parts = ["# 📊 智能洞察日报\n"]
    
    # 按优先级分组
    critical = [i for i in insights if i['type'] == 'critical']
    warning = [i for i in insights if i['type'] == 'warning']
    positive = [i for i in insights if i['type'] == 'positive']
    info = [i for i in insights if i['type'] in ['info', 'action']]
    
    if critical:
        report_parts.append("## 🚨 紧急预警")
        for item in critical:
            report_parts.append(f"\n### {item['icon']} {item['title']}")
            report_parts.append(f"**情况**: {item['detail']}")
            report_parts.append(f"**建议**: {item['action']}")
    
    if warning:
        report_parts.append("\n## ⚠️ 需要关注")
        for item in warning:
            report_parts.append(f"\n### {item['icon']} {item['title']}")
            report_parts.append(f"**情况**: {item['detail']}")
            report_parts.append(f"**建议**: {item['action']}")
    
    if positive:
        report_parts.append("\n## ✅ 积极信号")
        for item in positive:
            report_parts.append(f"\n### {item['icon']} {item['title']}")
            report_parts.append(f"**情况**: {item['detail']}")
            report_parts.append(f"**建议**: {item['action']}")
    
    if info:
        report_parts.append("\n## 💡 分析建议")
        for item in info:
            report_parts.append(f"\n### {item['icon']} {item['title']}")
            report_parts.append(f"**分析**: {item['detail']}")
            report_parts.append(f"**行动**: {item['action']}")
    
    return "\n".join(report_parts)


# 单例实例
_insight_engine = None

def get_insight_engine() -> InsightEngine:
    global _insight_engine
    if _insight_engine is None:
        _insight_engine = InsightEngine()
    return _insight_engine
