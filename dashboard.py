import streamlit as st
import pandas as pd
import httpx
import asyncio
import plotly.express as px
import time

# 1. 页面基本设置 (必须放在第一行)
st.set_page_config(page_title="Distributed E-commerce Analytics", page_icon="🛒", layout="wide")

# 2. 自定义 CSS 让大屏看起来更高级
st.markdown("""
    <style>
    .main {background-color: #0E1117;}
    h1 {color: #4CAF50;}
    .stMetric {background-color: #1E2127; padding: 15px; border-radius: 10px; border-left: 5px solid #4CAF50;}
    </style>
    """, unsafe_allow_html=True)

st.title("🛒 Distributed E-commerce Analytics Platform")
st.markdown("Real-time Data Aggregation from **Distributed Nodes** (West & East Malaysia)")

# 3. 核心功能：向两个节点拉取数据 (带容错机制)
# 3. 异步获取数据 (提升并发性能)
async def fetch_node_data(client, url, name):
    try:
        start_time = time.time()
        response = await client.get(url, timeout=10.0)
        latency = (time.time() - start_time) * 1000
        res = response.json()
        
        if "error" in res:
            return {"name": name, "data": pd.DataFrame(), "error": res["error"], "latency": latency, "source": "error"}
        
        df = pd.DataFrame(res["data"])
        return {"name": name, "data": df, "latency": latency, "status": "online", "rows": len(df)}
    except Exception as e:
        return {"name": name, "data": pd.DataFrame(), "error": str(e), "latency": 0, "status": "offline", "rows": 0}

async def get_all_data():
    urls = [
        ("http://127.0.0.1:5001/api/sales", "Node A (West)"),
        ("http://127.0.0.1:5002/api/sales", "Node B (East)")
    ]
    async with httpx.AsyncClient() as client:
        tasks = [fetch_node_data(client, url, name) for url, name in urls]
        results = await asyncio.gather(*tasks)
    return results

def fetch_data():
    # Streamlit 运行异步函数的包装器
    return asyncio.run(get_all_data())

# 4. 加载数据
# 4. 加载数据
with st.spinner("🚀 Fetching data from distributed nodes in parallel..."):
    results = fetch_data()
    
    # 解析结果
    dfs = []
    node_stats = {}
    for res in results:
        node_stats[res["name"]] = {
            "latency": res["latency"],
            "status": res["status"],
            "rows": res.get("rows", 0),
            "error": res.get("error")
        }
        if not res["data"].empty:
            temp_df = res["data"]
            # 💡 核心修复：强制根据节点来源标记 Region，防止数据库里的字符串不一致
            if "West" in res["name"]:
                temp_df['region'] = "West Malaysia"
            else:
                temp_df['region'] = "East Malaysia"
            dfs.append(temp_df)
    
    if dfs:
        df = pd.concat(dfs, ignore_index=True)
        # 格式化日期和金额
        if 'order_date' in df.columns:
            df['order_date'] = pd.to_datetime(df['order_date'])
            # 💡 核心修复：按日期降序排列，确保 West 和 East 的最新订单都能排在 head(100) 里
            df = df.sort_values(by='order_date', ascending=False)
        
        if 'unit_price_rm' in df.columns:
            df['unit_price_rm'] = pd.to_numeric(df['unit_price_rm'])
            df['total_sales_rm'] = pd.to_numeric(df['total_sales_rm'])
    else:
        df = pd.DataFrame()

# 5. UI 渲染 (如果数据成功加载)
if not df.empty:
    
    # --- 侧边栏：交互式过滤 (极度加分项) ---
    st.sidebar.header("🛠️ Dashboard Controls")
    
    # 节点监控 (动态显示)
    st.sidebar.markdown("### ☁️ Cloud Node Status")
    for name, stats in node_stats.items():
        if stats["status"] == "offline":
            st.sidebar.error(f"{name}: Offline")
        else:
            st.sidebar.markdown(f"**{name}**")
            st.sidebar.markdown(f"- Status: `Online` | Rows: `{stats['rows']}`")
            st.sidebar.markdown(f"- Latency: `{stats['latency']:.0f}ms`")
            if stats["error"]:
                st.sidebar.warning(f"Error: {stats['error']}")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔍 Filters")
    
    # 过滤器
    regions = st.sidebar.multiselect("Select Region", options=df['region'].unique(), default=df['region'].unique())
    categories = st.sidebar.multiselect("Select Category", options=df['category'].unique(), default=df['category'].unique())
    
    # 日期范围过滤器 (实际业务加分项)
    min_date = df['order_date'].min().date()
    max_date = df['order_date'].max().date()
    date_range = st.sidebar.date_input("Select Date Range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    
    # 应用过滤
    mask = (df['region'].isin(regions)) & (df['category'].isin(categories))
    if len(date_range) == 2:
        start_date, end_date = date_range
        mask = mask & (df['order_date'].dt.date >= start_date) & (df['order_date'].dt.date <= end_date)
    
    filtered_df = df[mask]
    
    if filtered_df.empty:
        st.warning("No data matches the selected filters.")
    else:
        # --- 顶部 KPI 数据卡片 ---
        st.markdown("### 📊 Live Performance Metrics")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        
        total_sales = filtered_df['total_sales_rm'].sum()
        total_orders = len(filtered_df)
        west_sales = filtered_df[filtered_df['region'] == 'West Malaysia']['total_sales_rm'].sum()
        east_sales = filtered_df[filtered_df['region'] == 'East Malaysia']['total_sales_rm'].sum()

        kpi1.metric("💰 Total Revenue (RM)", f"RM {total_sales:,.0f}")
        kpi2.metric("📦 Total Orders", f"{total_orders:,}")
        kpi3.metric("🏢 Node A (West) Revenue", f"RM {west_sales:,.0f}")
        kpi4.metric("🌴 Node B (East) Revenue", f"RM {east_sales:,.0f}")
        
        st.markdown("<br>", unsafe_allow_html=True)

        # --- 图表区 1: 趋势图与对比图 ---
        col_chart1, col_chart2 = st.columns([2, 1]) # 2:1 比例布局
        
        with col_chart1:
            st.markdown("#### 📅 Monthly Revenue Trend")
            # 按月汇总
            filtered_df['month'] = filtered_df['order_date'].dt.to_period('M').astype(str)
            trend_df = filtered_df.groupby(['month', 'region'])['total_sales_rm'].sum().reset_index()
            fig_line = px.line(trend_df, x='month', y='total_sales_rm', color='region', markers=True, 
                               line_shape="spline", color_discrete_sequence=['#4CAF50', '#FF9800'])
            fig_line.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_line, use_container_width=True)
            
        with col_chart2:
            st.markdown("#### 🌐 Node Contribution (Sharding)")
            fig_pie = px.pie(filtered_df, values='total_sales_rm', names='region', hole=0.4,
                             color_discrete_sequence=['#4CAF50', '#FF9800'])
            fig_pie.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_pie, use_container_width=True)

        # --- 图表区 2: 商品分析 ---
        col_chart3, col_chart4 = st.columns(2)
        
        with col_chart3:
            st.markdown("#### 🛍️ Revenue by Category")
            cat_df = filtered_df.groupby(['category', 'region'])['total_sales_rm'].sum().reset_index()
            fig_bar = px.bar(cat_df, x='category', y='total_sales_rm', color='region', barmode='group',
                             text_auto='.2s', color_discrete_sequence=['#4CAF50', '#FF9800'])
            fig_bar.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with col_chart4:
            st.markdown("#### 💳 Payment Method Preference")
            # 🚨 这里已经彻底修复了！
            pay_df = filtered_df['payment_method'].value_counts().reset_index()
            pay_df.columns = ['payment_method', 'count']
            fig_bar_h = px.bar(pay_df, y='payment_method', x='count', orientation='h', color='payment_method')
            fig_bar_h.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
            st.plotly_chart(fig_bar_h, use_container_width=True)

        # --- 原始数据查看区 ---
        col_raw, col_export = st.columns([3, 1])
        with col_raw:
            st.markdown("#### 🔍 Raw Aggregated Data")
        with col_export:
            # 导出 CSV 功能 (实际业务非常有用)
            csv = filtered_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export to CSV",
                data=csv,
                file_name='ecommerce_sales_report.csv',
                mime='text/csv',
            )
        
        st.dataframe(filtered_df.head(100), use_container_width=True)

        # --- 分布式录入新订单 (实际业务操作) ---
        st.markdown("---")
        with st.expander("📝 Register New Distributed Order"):
            st.info("The system will automatically route the request to the correct node based on the region.")
            
            with st.form("new_order_form"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    new_id = st.text_input("Order ID", value=f"ORD{int(time.time())}")
                    new_cat = st.selectbox("Category", options=df['category'].unique())
                    new_prod = st.text_input("Product Name", value="New Product")
                with col2:
                    new_date = st.date_input("Order Date", value=pd.Timestamp.now())
                    new_price = st.number_input("Unit Price (RM)", min_value=1.0, value=100.0)
                    new_qty = st.number_input("Quantity", min_value=1, value=1)
                with col3:
                    new_region = st.selectbox("Region", options=["West Malaysia", "East Malaysia"])
                    new_state = st.text_input("State", value="Kuala Lumpur" if new_region == "West Malaysia" else "Sabah")
                    new_pay = st.selectbox("Payment", options=df['payment_method'].unique())
                
                submit = st.form_submit_button("🚀 Submit Distributed Order")
                
                if submit:
                    order_payload = {
                        "order_id": new_id,
                        "order_date": str(new_date),
                        "category": new_cat,
                        "product_name": new_prod,
                        "unit_price_rm": int(new_price),
                        "quantity": int(new_qty),
                        "total_sales_rm": int(new_price * new_qty),
                        "region": new_region,
                        "state": new_state,
                        "payment_method": new_pay
                    }
                    
                    # 智能路由逻辑
                    target_port = 5001 if new_region == "West Malaysia" else 5002
                    target_url = f"http://127.0.0.1:{target_port}/api/orders"
                    
                    try:
                        import requests
                        with st.spinner("Communicating with Distributed Node..."):
                            r = requests.post(target_url, json=order_payload, timeout=15)
                        res_data = r.json()
                        if r.status_code == 200:
                            st.success(f"✅ Success! {res_data.get('message')}")
                            st.balloons()
                        else:
                            st.error(f"❌ Failed to submit: {res_data.get('message')}")
                    except Exception as e:
                        st.error(f"❌ Connection error: {e}")