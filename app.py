"""
CD销售AI助手 - 给销售用的小工具
之前手工Execl搞半天，现在问一句话就行
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.agent import get_agent
from data.init_db import init_database
import os

# 初始化数据库
if not os.path.exists("data/sales.db"):
    init_database()

# 页面配置
st.set_page_config(
    page_title="销售小助手",
    page_icon="📊",
    layout="wide"
)

# 简单样式
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        color: #333;
        padding: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# 侧边栏
with st.sidebar:
    st.title("销售小助手")
    st.markdown("---")
    page = st.radio(
        "功能",
        ["💬 问答", "📊 看板", "🎯 洞察", "📖 说明"]
    )
    st.markdown("---")
    st.markdown("**试试这些：**")
    
    if page == "💬 问答":
        st.markdown("""
- 冰箱Pro X1怎么卖？
- 华东区这月完成得怎么样
- TOP10经销商是谁
        """)

# 主页面
st.markdown('<div class="main-header">🤖 CD销售AI助手 POC</div>', unsafe_allow_html=True)
st.markdown("### AI赋能销售，提升经销商效能")

# 获取Agent
agent = get_agent()

# 问答页面
if page == "💬 问答":
    
    st.markdown("问点啥：")
    
    # 对话区域
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    if question := st.chat_input("输入问题..."):
        with st.chat_message("user"):
            st.markdown(question)
        st.session_state.messages.append({"role": "user", "content": question})
        
        with st.chat_message("assistant"):
            with st.spinner("查一下..."):
                answer, intent = agent.answer(question)
                st.markdown(answer)
        
        st.session_state.messages.append({"role": "assistant", "content": answer})

# 数据看板
elif page == "📊 看板":
    
    import sqlite3
    conn = sqlite3.connect("data/sales.db")
    
    st.markdown("### 本月数据")
    col1, col2, col3 = st.columns(3)
    
    total_sales = pd.read_sql_query("""
        SELECT SUM(actual_amount) as total FROM dealer_kpi 
        WHERE month = (SELECT MAX(month) FROM dealer_kpi)
    """, conn).iloc[0]['total']
    
    avg_completion = pd.read_sql_query("""
        SELECT ROUND(AVG(completion_rate) * 100, 1) as avg FROM dealer_kpi 
        WHERE month = (SELECT MAX(month) FROM dealer_kpi)
    """, conn).iloc[0]['avg']
    
    with col1:
        st.metric("总销售额", f"¥{total_sales:,.0f}")
    with col2:
        st.metric("平均完成率", f"{avg_completion}%")
    
    st.markdown("---")
    
    # 区域对比
    st.markdown("### 各区域情况")
    region_data = pd.read_sql_query("""
        SELECT d.region, SUM(k.actual_amount) as sales,
               ROUND(AVG(k.completion_rate) * 100, 1) as completion
        FROM dealer_kpi k
        JOIN dealers d ON k.dealer_id = d.dealer_id
        WHERE k.month = (SELECT MAX(month) FROM dealer_kpi)
        GROUP BY d.region
    """, conn)
    
    fig = px.bar(region_data, x='region', y='sales', color='region')
    st.plotly_chart(fig, use_container_width=True)
    
    # 经销商排名
    st.markdown("### 经销商完成率排名")
    dealer_ranking = pd.read_sql_query("""
        SELECT d.dealer_name, d.region, d.city,
               ROUND(k.completion_rate * 100, 1) as completion
        FROM dealer_kpi k
        JOIN dealers d ON k.dealer_id = d.dealer_id
        WHERE k.month = (SELECT MAX(month) FROM dealer_kpi)
        ORDER BY k.completion_rate DESC
    """, conn)
    
    def color_completion(val):
        if val >= 100:
            return 'background-color: #d4edda'
        elif val >= 80:
            return 'background-color: #fff3cd'
        else:
            return 'background-color: #f8d7da'
    
    st.dataframe(
        dealer_ranking.style.map(color_completion, subset=['completion']),
        use_container_width=True,
        height=400
    )
    
    conn.close()

# 洞察页面
elif page == "🎯 洞察":
    st.markdown("### 需要关注的点")
    
    with st.spinner("分析中..."):
        from utils.insight import get_insight_engine, format_insights_report
        engine = get_insight_engine()
        insights = engine.generate_daily_insights()
        report = format_insights_report(insights)
    
    st.markdown(report)

# 说明页面
elif page == "📖 说明":
    st.markdown("### 简单说明")
    
    st.markdown("""
**这个工具能干嘛：**

1. **问知识** - 产品卖点、话术、FAQ，问了就答
2. **查数据** - KPI、销量、排名，不用翻Excel
3. **看洞察** - 哪些经销商要关注，哪些做得好

**怎么用：**
- 左边选"问答"，直接打字问
- 选"看板"，看数据图表
- 选"洞察"，看分析报告

**数据说明：**
- 现在是模拟数据，20个经销商，6个月
- 真实用的话要接你们的数据库
    """)
