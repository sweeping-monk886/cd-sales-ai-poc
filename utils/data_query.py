"""
问数能力 - Text-to-SQL 数据查询
"""
import sqlite3
import pandas as pd
from typing import Dict, List, Tuple
import re

DB_PATH = "data/sales.db"

# 数据库Schema描述
SCHEMA_DESC = """
数据库表结构：

1. dealers (经销商表)
   - dealer_id: 经销商ID (如 D001)
   - dealer_name: 经销商名称
   - region: 区域 (华东/华南/华中/华北)
   - city: 城市
   - level: 等级 (S/A/B/C)
   - manager: 负责人
   - phone: 联系电话

2. products (产品表)
   - product_id: 产品ID (如 P001)
   - product_name: 产品名称
   - category: 品类 (冰箱/空调/洗衣机)
   - price: 零售价
   - cost: 成本价

3. dealer_kpi (月度KPI表)
   - dealer_id: 经销商ID
   - month: 月份 (格式 2024-01)
   - target_amount: 目标金额
   - actual_amount: 实际金额
   - completion_rate: 完成率
   - rank_in_region: 区域排名

4. sales_detail (销售明细表)
   - order_id: 订单号
   - dealer_id: 经销商ID
   - product_id: 产品ID
   - quantity: 数量
   - amount: 金额
   - sale_date: 销售日期
   - region: 区域
"""

# SQL示例
SQL_EXAMPLES = """
示例问答对：

Q: 查询华东区经销商的KPI完成情况
SELECT d.dealer_name, k.month, k.target_amount, k.actual_amount, 
       ROUND(k.completion_rate * 100, 1) as completion_pct
FROM dealer_kpi k
JOIN dealers d ON k.dealer_id = d.dealer_id
WHERE d.region = '华东'
ORDER BY k.month, k.completion_rate DESC;

Q: 各区域总销售额是多少？
SELECT region, SUM(amount) as total_sales, COUNT(*) as order_count
FROM sales_detail
GROUP BY region
ORDER BY total_sales DESC;

Q: 本月销量TOP10的经销商
SELECT d.dealer_name, SUM(s.amount) as total_sales
FROM sales_detail s
JOIN dealers d ON s.dealer_id = d.dealer_id
WHERE s.sale_date LIKE '2024-06%'
GROUP BY s.dealer_id
ORDER BY total_sales DESC
LIMIT 10;

Q: 各产品品类的销售占比
SELECT p.category, 
       SUM(s.amount) as total_sales,
       ROUND(SUM(s.amount) * 100.0 / (SELECT SUM(amount) FROM sales_detail), 1) as pct
FROM sales_detail s
JOIN products p ON s.product_id = p.product_id
GROUP BY p.category
ORDER BY total_sales DESC;

Q: 完成率低于80%的经销商有哪些？
SELECT d.dealer_name, d.region, d.city,
       k.month, 
       ROUND(k.completion_rate * 100, 1) as completion_pct,
       k.target_amount,
       k.actual_amount
FROM dealer_kpi k
JOIN dealers d ON k.dealer_id = d.dealer_id
WHERE k.completion_rate < 0.8 AND k.month = '2024-06'
ORDER BY k.completion_rate ASC;
"""

def generate_sql(question: str) -> str:
    """基于规则的SQL生成（生产环境应使用LLM）"""
    question = question.lower()
    
    # 关键词匹配生成SQL
    if any(kw in question for kw in ['完成率', '未达标', '低于']):
        if '80%' in question or '80%以下' in question:
            return """
            SELECT d.dealer_name, d.region, d.city,
                   k.month, 
                   ROUND(k.completion_rate * 100, 1) as completion_pct,
                   k.target_amount,
                   k.actual_amount
            FROM dealer_kpi k
            JOIN dealers d ON k.dealer_id = d.dealer_id
            WHERE k.completion_rate < 0.8 AND k.month = (SELECT MAX(month) FROM dealer_kpi)
            ORDER BY k.completion_rate ASC
            """
        else:
            return """
            SELECT d.dealer_name, k.month, 
                   ROUND(k.completion_rate * 100, 1) as completion_pct,
                   k.target_amount, k.actual_amount
            FROM dealer_kpi k
            JOIN dealers d ON k.dealer_id = d.dealer_id
            WHERE k.month = (SELECT MAX(month) FROM dealer_kpi)
            ORDER BY k.completion_rate DESC
            """
    
    elif any(kw in question for kw in ['top', '排名', '排行', '最好', '最高']):
        limit = 10
        for num in ['5', '10', '15', '20']:
            if num in question:
                limit = int(num)
                break
        return f"""
        SELECT d.dealer_name, d.region, SUM(s.amount) as total_sales
        FROM sales_detail s
        JOIN dealers d ON s.dealer_id = d.dealer_id
        WHERE s.sale_date LIKE '2024-06%'
        GROUP BY s.dealer_name
        ORDER BY total_sales DESC
        LIMIT {limit}
        """
    
    elif any(kw in question for kw in ['区域', '大区', '华东', '华南', '华中', '华北']):
        region = None
        for r in ['华东', '华南', '华中', '华北']:
            if r in question:
                region = r
                break
        
        if region:
            return f"""
            SELECT d.dealer_name, d.city, k.month,
                   ROUND(k.completion_rate * 100, 1) as completion_pct,
                   k.actual_amount
            FROM dealer_kpi k
            JOIN dealers d ON k.dealer_id = d.dealer_id
            WHERE d.region = '{region}' AND k.month = (SELECT MAX(month) FROM dealer_kpi)
            ORDER BY k.completion_rate DESC
            """
        else:
            return """
            SELECT region, 
                   SUM(actual_amount) as total_actual,
                   ROUND(AVG(completion_rate) * 100, 1) as avg_completion
            FROM dealer_kpi k
            JOIN dealers d ON k.dealer_id = d.dealer_id
            WHERE k.month = (SELECT MAX(month) FROM dealer_kpi)
            GROUP BY region
            ORDER BY total_actual DESC
            """
    
    elif any(kw in question for kw in ['产品', '品类', '冰箱', '空调', '洗衣机']):
        category = None
        for c in ['冰箱', '空调', '洗衣机']:
            if c in question:
                category = c
                break
        
        if category:
            return f"""
            SELECT p.product_name, p.category,
                   SUM(s.quantity) as total_qty,
                   SUM(s.amount) as total_sales
            FROM sales_detail s
            JOIN products p ON s.product_id = p.product_id
            WHERE p.category = '{category}'
            GROUP BY p.product_name
            ORDER BY total_sales DESC
            """
        else:
            return """
            SELECT p.category,
                   SUM(s.quantity) as total_qty,
                   SUM(s.amount) as total_sales,
                   ROUND(SUM(s.amount) * 100.0 / (SELECT SUM(amount) FROM sales_detail), 1) as pct
            FROM sales_detail s
            JOIN products p ON s.product_id = p.product_id
            GROUP BY p.category
            ORDER BY total_sales DESC
            """
    
    elif any(kw in question for kw in ['经销商', '门店', '店铺']):
        return """
        SELECT d.dealer_name, d.region, d.city, d.level,
               SUM(s.amount) as total_sales
        FROM sales_detail s
        JOIN dealers d ON s.dealer_id = d.dealer_id
        GROUP BY s.dealer_id
        ORDER BY total_sales DESC
        LIMIT 20
        """
    
    elif any(kw in question for kw in ['趋势', '走势', '变化']):
        return """
        SELECT k.month,
               SUM(k.actual_amount) as total_actual,
               ROUND(AVG(k.completion_rate) * 100, 1) as avg_completion
        FROM dealer_kpi k
        GROUP BY k.month
        ORDER BY k.month
        """
    
    else:
        # 默认查询最新月份概况
        return """
        SELECT d.region,
               COUNT(DISTINCT d.dealer_id) as dealer_count,
               SUM(k.actual_amount) as total_sales,
               ROUND(AVG(k.completion_rate) * 100, 1) as avg_completion
        FROM dealer_kpi k
        JOIN dealers d ON k.dealer_id = d.dealer_id
        WHERE k.month = (SELECT MAX(month) FROM dealer_kpi)
        GROUP BY d.region
        ORDER BY total_sales DESC
        """


def execute_sql(sql: str) -> Tuple[pd.DataFrame, str]:
    """执行SQL查询"""
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(sql, conn)
        conn.close()
        
        if df.empty:
            return df, "查询结果为空，没有符合条件的数据。"
        
        return df, None
    except Exception as e:
        return pd.DataFrame(), f"SQL执行错误: {str(e)}"


def format_query_result(df: pd.DataFrame, question: str) -> str:
    """格式化查询结果为可读文本"""
    if df.empty:
        return "未查询到相关数据。"
    
    # 简单统计描述
    result_parts = []
    
    # 表格形式
    result_parts.append("📊 **查询结果：**")
    result_parts.append(df.to_markdown(index=False))
    
    # 基本统计
    if len(df) > 1:
        result_parts.append(f"\n共 {len(df)} 条记录")
        
        # 数值列统计
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
        for col in numeric_cols[:2]:  # 只显示前2个数值列
            if 'amount' in col or 'sales' in col:
                result_parts.append(f"- {col}: 总计 {df[col].sum():,.0f}")
            elif 'rate' in col or 'pct' in col:
                result_parts.append(f"- {col}: 平均 {df[col].mean():.1f}%")
    
    return "\n".join(result_parts)


def generate_data_insight(df: pd.DataFrame, question: str) -> str:
    """基于数据生成洞察"""
    insights = []
    
    if df.empty:
        return "数据为空，无法生成洞察。"
    
    # 检查完成率相关
    if 'completion_pct' in df.columns:
        low_completion = df[df['completion_pct'] < 80]
        high_completion = df[df['completion_pct'] >= 100]
        
        if len(low_completion) > 0:
            names = ', '.join(low_completion['dealer_name'].head(3).tolist())
            insights.append(f"⚠️ **预警**: {names}等{len(low_completion)}家经销商完成率低于80%，需重点关注。")
        
        if len(high_completion) > 0:
            names = ', '.join(high_completion['dealer_name'].head(3).tolist())
            insights.append(f"✅ **亮点**: {names}等{len(high_completion)}家经销商超额完成目标。")
    
    # 检查销售相关
    if 'total_sales' in df.columns:
        top = df.nlargest(3, 'total_sales')
        bottom = df.nsmallest(3, 'total_sales')
        
        if len(top) > 0:
            insights.append(f"🏆 **TOP3**: {', '.join(top['dealer_name'].head(3).tolist())}")
        
        if len(bottom) > 0 and len(df) > 5:
            insights.append(f"📉 **待提升**: {', '.join(bottom['dealer_name'].head(3).tolist())}")
    
    if insights:
        return "\n\n💡 **数据洞察：**\n" + "\n".join(insights)
    return ""


# 单例数据库描述
def get_schema_description() -> str:
    return SCHEMA_DESC + "\n" + SQL_EXAMPLES
