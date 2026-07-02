"""
初始化模拟数据库 - CD销售场景
"""
import sqlite3
import random
from datetime import datetime, timedelta

DB_PATH = "data/sales.db"

def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 经销商表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dealers (
        dealer_id TEXT PRIMARY KEY,
        dealer_name TEXT,
        region TEXT,
        city TEXT,
        level TEXT,  -- S/A/B/C
        manager TEXT,
        phone TEXT
    )""")
    
    # 产品表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        product_id TEXT PRIMARY KEY,
        product_name TEXT,
        category TEXT,
        price DECIMAL(10,2),
        cost DECIMAL(10,2)
    )""")
    
    # 月度KPI表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dealer_kpi (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dealer_id TEXT,
        month TEXT,
        target_amount DECIMAL(12,2),
        actual_amount DECIMAL(12,2),
        completion_rate DECIMAL(5,4),
        rank_in_region INTEGER,
        FOREIGN KEY (dealer_id) REFERENCES dealers(dealer_id)
    )""")
    
    # 销售明细表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sales_detail (
        order_id TEXT PRIMARY KEY,
        dealer_id TEXT,
        product_id TEXT,
        quantity INTEGER,
        amount DECIMAL(12,2),
        sale_date TEXT,
        region TEXT,
        FOREIGN KEY (dealer_id) REFERENCES dealers(dealer_id),
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    )""")
    
    # 填充模拟数据
    # 经销商数据
    dealers = [
        ("D001", "华东旗舰店", "华东", "上海", "S", "张伟", "13800138001"),
        ("D002", "南京体验中心", "华东", "南京", "A", "李娜", "13800138002"),
        ("D003", "杭州专卖店", "华东", "杭州", "A", "王芳", "13800138003"),
        ("D004", "苏州专营店", "华东", "苏州", "B", "刘强", "13800138004"),
        ("D005", "宁波电器行", "华东", "宁波", "B", "陈静", "13800138005"),
        ("D011", "华南总店", "华南", "广州", "S", "赵磊", "13800138011"),
        ("D012", "深圳旗舰店", "华南", "深圳", "S", "孙丽", "13800138012"),
        ("D013", "东莞专营店", "华南", "东莞", "A", "周杰", "13800138013"),
        ("D014", "佛山电器城", "华南", "佛山", "B", "吴敏", "13800138014"),
        ("D015", "珠海专卖店", "华南", "珠海", "B", "郑涛", "13800138015"),
        ("D021", "华中中心店", "华中", "武汉", "A", "黄鹏", "13800138021"),
        ("D022", "长沙旗舰店", "华中", "长沙", "A", "朱婷", "13800138022"),
        ("D023", "郑州专营店", "华中", "郑州", "B", "马超", "13800138023"),
        ("D024", "南昌电器行", "华中", "南昌", "C", "胡燕", "13800138024"),
        ("D025", "合肥专卖店", "华中", "合肥", "B", "林峰", "13800138025"),
        ("D031", "华北旗舰店", "华北", "北京", "S", "高峰", "13800138031"),
        ("D032", "天津专营店", "华北", "天津", "A", "罗佳", "13800138032"),
        ("D033", "石家庄电器城", "华北", "石家庄", "B", "梁宇", "13800138033"),
        ("D034", "太原专卖店", "华北", "太原", "C", "宋涛", "13800138034"),
        ("D035", "济南体验中心", "华北", "济南", "A", "唐敏", "13800138035"),
    ]
    cursor.executemany("INSERT OR IGNORE INTO dealers VALUES (?,?,?,?,?,?,?)", dealers)
    
    # 产品数据
    products = [
        ("P001", "智能冰箱 Pro X1", "冰箱", 6999.00, 4200.00),
        ("P002", "智能冰箱 Lite S2", "冰箱", 3999.00, 2400.00),
        ("P003", "智能空调 Star V3", "空调", 3999.00, 2200.00),
        ("P004", "智能空调 Cool V2", "空调", 2999.00, 1600.00),
        ("P005", "智能空调 Master X1", "空调", 8999.00, 5400.00),
        ("P006", "智能洗衣机 Wave Pro", "洗衣机", 4599.00, 2700.00),
        ("P007", "智能洗衣机 Clean S1", "洗衣机", 2599.00, 1500.00),
    ]
    cursor.executemany("INSERT OR IGNORE INTO products VALUES (?,?,?,?,?)", products)
    
    # 生成最近6个月的KPI数据
    random.seed(42)
    months = ["2024-01", "2024-02", "2024-03", "2024-04", "2024-05", "2024-06"]
    
    for month in months:
        for dealer in dealers:
            dealer_id = dealer[0]
            level = dealer[4]
            
            # 根据等级设置不同目标
            base_target = {"S": 800000, "A": 500000, "B": 300000, "C": 150000}[level]
            target = base_target * random.uniform(0.9, 1.1)
            
            # 实际完成率有波动，部分经销商表现好，部分差
            if random.random() < 0.3:  # 30%的经销商超额完成
                completion = random.uniform(1.0, 1.25)
            elif random.random() < 0.4:  # 40%基本完成
                completion = random.uniform(0.8, 1.0)
            else:  # 30%未达标
                completion = random.uniform(0.5, 0.8)
            
            actual = target * completion
            rank = random.randint(1, 5)
            
            cursor.execute("""
                INSERT OR IGNORE INTO dealer_kpi 
                (dealer_id, month, target_amount, actual_amount, completion_rate, rank_in_region)
                VALUES (?,?,?,?,?,?)
            """, (dealer_id, month, round(target, 2), round(actual, 2), round(completion, 4), rank))
    
    # 生成销售明细数据
    product_ids = [p[0] for p in products]
    quantities = [1, 2, 3, 5]
    
    order_id = 1000
    for month in months:
        year, mon = month.split("-")
        for _ in range(100):  # 每月100条销售记录
            order_id += 1
            dealer = random.choice(dealers)
            product = random.choice(products)
            qty = random.choice(quantities)
            amount = product[3] * qty
            
            # 随机日期
            day = random.randint(1, 28)
            sale_date = f"{year}-{mon}-{day:02d}"
            
            cursor.execute("""
                INSERT OR IGNORE INTO sales_detail 
                (order_id, dealer_id, product_id, quantity, amount, sale_date, region)
                VALUES (?,?,?,?,?,?,?)
            """, (f"ORD{order_id}", dealer[0], product[0], qty, round(amount, 2), sale_date, dealer[2]))
    
    conn.commit()
    conn.close()
    print(f"✅ 数据库初始化完成: {DB_PATH}")
    print(f"   - {len(dealers)} 个经销商")
    print(f"   - {len(products)} 个产品")
    print(f"   - {len(dealers)*len(months)} 条KPI记录")
    print(f"   - {100*len(months)} 条销售记录")

if __name__ == "__main__":
    init_database()
