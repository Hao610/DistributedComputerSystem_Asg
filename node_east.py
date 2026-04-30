from flask import Flask, jsonify, request
from supabase import create_client, Client
import time

app = Flask(__name__)

# 你的专属 URL 和 Key
SUPABASE_URL = "https://prgjqwtovzeabuguvwyh.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InByZ2pxd3RvdnplYWJ1Z3V2d3loIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NzUxOTMwNCwiZXhwIjoyMDkzMDk1MzA0fQ.0Gt5aSSBrK-ramNp9dWx6_F2DxJ1tQyz2UPZD5f_5iA"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route('/api/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "node": "East Node (Cloud Only)",
        "timestamp": time.time()
    })

@app.route('/api/sales')
def get_east_sales():
    try:
        response = (supabase.table("node_east")
                    .select("*")
                    # 如果你的表本身就是按地区分片的，其实可以不加这个 eq
                    # 或者改用 ilike 模糊匹配
                    .order("order_date", desc=True)
                    .limit(10000)
                    .execute())
        return jsonify({
            "node": "East",
            "data": response.data
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/orders', methods=['POST'])
def add_order():
    new_order = request.json
    try:
        result = supabase.table("node_east").insert(new_order).execute()
        if result.data:
            return jsonify({"status": "success", "message": "Successfully saved to Supabase"})
        else:
            return jsonify({"status": "failed", "message": "Supabase insertion failed (check RLS)"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5002)