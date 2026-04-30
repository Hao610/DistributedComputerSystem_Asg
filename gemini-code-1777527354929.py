import pandas as pd
import sqlite3

print("⏳ 正在读取 CSV 数据...")
# 1. 读取刚刚生成的 CSV 文件
df_west = pd.read_csv("node_west_data.csv")
df_east = pd.read_csv("node_east_data.csv")

print("⏳ 正在创建并导入分布式 SQL 数据库...")
# 2. 连接到 SQLite 数据库 (如果文件不存在，会自动创建)
# 节点 A (西马) 的数据库
conn_west = sqlite3.connect("db_west.sqlite")
# 节点 B (东马) 的数据库
conn_east = sqlite3.connect("db_east.sqlite")

# 3. 将 DataFrame 写入 SQL 数据库中
# 表名命名为 'sales_records'
df_west.to_sql("sales_records", conn_west, if_exists="replace", index=False)
df_east.to_sql("sales_records", conn_east, if_exists="replace", index=False)

# 4. 关闭连接
conn_west.close()
conn_east.close()

print("✅ 成功！")
print("👉 节点 A 数据库已生成: db_west.sqlite")
print("👉 节点 B 数据库已生成: db_east.sqlite")