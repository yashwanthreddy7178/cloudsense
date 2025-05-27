import pandas as pd
import joblib
from flask import Flask, request, jsonify
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
metrics = PrometheusMetrics(app)

# 🔥 Load the trained model ONCE at startup
model = joblib.load("model/best_model.pkl")

# Features expected by the model
FEATURES = [
    "cpu_util", "mem_util", "disk_io", "net_io",
    "active_processes", "hour_of_day", "day_of_week",
    "io_ratio", "cpu_mem_ratio", "load_score"
]

@app.route("/")
def index():
    return "CloudSense Inference API is running!"

@app.route("/predict", methods=["POST"])
@metrics.counter("predict_requests_total", "Total prediction requests")
def predict():
    try:
        data = request.get_json(force=True)
        df = pd.Series(data).to_frame().T[FEATURES]
        prob = model.predict(df)[0]
        return jsonify({
            "prediction": int(prob > 0.5),
            "probability": float(prob)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
