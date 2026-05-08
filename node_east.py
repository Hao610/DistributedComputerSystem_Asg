from flask import Flask, jsonify, request
from supabase import create_client, Client
import time

app = Flask(__name__)

# Supabase Credentials
SUPABASE_URL = "YOUR_SUPABASE_URL_HERE"
SUPABASE_KEY = "YOUR_SUPABASE_KEY_HERE"

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
        # Fetch data from Supabase
        response = (supabase.table("node_east")
                    .select("*")
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
        # Insert new order into Supabase
        result = supabase.table("node_east").insert(new_order).execute()
        if result.data:
            return jsonify({"status": "success", "message": "Successfully saved to Supabase"})
        else:
            return jsonify({"status": "failed", "message": "Supabase insertion failed (check RLS)"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5002)