from flask import Flask
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
metrics = PrometheusMetrics(app)

@app.route("/")
def index():
    return "Hello from CloudSense!"

@app.route("/predict")
@metrics.counter("predict_requests_total", "Total prediction requests")
def predict():
    return {"result": "prediction simulated"}

if __name__ == "__main__":
    app.run(port=5000)
