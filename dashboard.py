import streamlit as st
import pandas as pd
import httpx
import asyncio
import plotly.express as px
import time

# 1. Page Configuration
st.set_page_config(page_title="Distributed E-commerce Analytics", page_icon="🛒", layout="wide")

# 2. Custom CSS for Premium Look
st.markdown("""
    <style>
    .main {background-color: #0E1117;}
    h1 {color: #4CAF50;}
    .stMetric {background-color: #1E2127; padding: 15px; border-radius: 10px; border-left: 5px solid #4CAF50;}
    </style>
    """, unsafe_allow_html=True)

st.title("🛒 Distributed E-commerce Analytics Platform")
st.markdown("Real-time Data Aggregation from **Distributed Nodes** (West & East Malaysia)")

# 3. Core Function: Async Data Fetching
async def fetch_node_data(client, url, name):
    try:
        start_time = time.time()
        response = await client.get(url, timeout=10.0)
        latency = (time.time() - start_time) * 1000
        res = response.json()
        
        if "error" in res:
            return {"name": name, "data": pd.DataFrame(), "error": res["error"], "latency": latency, "status": "error"}
        
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
    return asyncio.run(get_all_data())

# 4. Data Loading
with st.spinner("🚀 Fetching data from distributed nodes in parallel..."):
    results = fetch_data()
    
    # Parse Results
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
            # Tag data based on node source
            if "West" in res["name"]:
                temp_df['region'] = "West Malaysia"
            else:
                temp_df['region'] = "East Malaysia"
            dfs.append(temp_df)
    
    if dfs:
        df = pd.concat(dfs, ignore_index=True)
        # Format Date and Currency
        if 'order_date' in df.columns:
            df['order_date'] = pd.to_datetime(df['order_date'])
            # Sort by date descending
            df = df.sort_values(by='order_date', ascending=False)
        
        if 'unit_price_rm' in df.columns:
            df['unit_price_rm'] = pd.to_numeric(df['unit_price_rm'])
            df['total_sales_rm'] = pd.to_numeric(df['total_sales_rm'])
    else:
        df = pd.DataFrame()

# 5. UI Rendering
if not df.empty:
    
    # --- Sidebar: Controls ---
    st.sidebar.header("🛠️ Dashboard Controls")
    
    # Node Monitoring
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
    
    # Filters
    regions = st.sidebar.multiselect("Select Region", options=df['region'].unique(), default=df['region'].unique())
    categories = st.sidebar.multiselect("Select Category", options=df['category'].unique(), default=df['category'].unique())
    
    # Date Range Filter
    min_date = df['order_date'].min().date()
    max_date = df['order_date'].max().date()
    date_range = st.sidebar.date_input("Select Date Range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    
    # Apply Filters
    mask = (df['region'].isin(regions)) & (df['category'].isin(categories))
    if len(date_range) == 2:
        start_date, end_date = date_range
        mask = mask & (df['order_date'].dt.date >= start_date) & (df['order_date'].dt.date <= end_date)
    
    filtered_df = df[mask]
    
    if filtered_df.empty:
        st.warning("No data matches the selected filters.")
    else:
        # --- KPI Cards ---
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

        # --- Charts Area 1 ---
        col_chart1, col_chart2 = st.columns([2, 1])
        
        with col_chart1:
            st.markdown("#### 📅 Monthly Revenue Trend")
            filtered_df['month'] = filtered_df['order_date'].dt.to_period('M').astype(str)
            trend_df = filtered_df.groupby(['month', 'region'])['total_sales_rm'].sum().reset_index()
            fig_line = px.line(trend_df, x='month', y='total_sales_rm', color='region', markers=True, 
                               line_shape="spline", color_discrete_sequence=['#4CAF50', '#FF9800'])
            fig_line.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_line, use_container_width=True)
            
        with col_chart2:
            st.markdown("#### 🌐 Node Contribution")
            fig_pie = px.pie(filtered_df, values='total_sales_rm', names='region', hole=0.4,
                             color_discrete_sequence=['#4CAF50', '#FF9800'])
            fig_pie.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_pie, use_container_width=True)

        # --- Charts Area 2 ---
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
            pay_df = filtered_df['payment_method'].value_counts().reset_index()
            pay_df.columns = ['payment_method', 'count']
            fig_bar_h = px.bar(pay_df, y='payment_method', x='count', orientation='h', color='payment_method')
            fig_bar_h.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
            st.plotly_chart(fig_bar_h, use_container_width=True)

        # --- Data Table Area ---
        col_raw, col_export = st.columns([3, 1])
        with col_raw:
            st.markdown("#### 🔍 Raw Aggregated Data")
        with col_export:
            csv = filtered_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export to CSV",
                data=csv,
                file_name='ecommerce_sales_report.csv',
                mime='text/csv',
            )
        
        st.dataframe(filtered_df.head(100), use_container_width=True)

        # --- Distributed Order Entry ---
        st.markdown("---")
        with st.expander("📝 Register New Distributed Order"):
            st.info("System will automatically route the request based on region.")
            
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
                    
                    target_port = 5001 if new_region == "West Malaysia" else 5002
                    target_url = f"http://127.0.0.1:{target_port}/api/orders"
                    
                    try:
                        import requests
                        with st.spinner("Writing to Supabase..."):
                            r = requests.post(target_url, json=order_payload, timeout=15)
                            res_data = r.json()
                        if r.status_code == 200:
                            st.success(f"✅ Success! {res_data.get('message')}")
                            st.balloons()
                        else:
                            st.error(f"❌ Failed: {res_data.get('message')}")
                    except Exception as e:
                        st.error(f"❌ Connection error: {e}")
else:
    st.error("No data fetched. Please check if Flask nodes are running.")