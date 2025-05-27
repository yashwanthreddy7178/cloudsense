import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="CloudSense UI", layout="centered")
st.title("🔍 CloudSense - VM Resource Exhaustion Predictor")

st.markdown("Upload telemetry CSV to get predictions using the latest trained model.")

uploaded_file = st.file_uploader("📁 Upload Telemetry CSV", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    st.subheader("Preview of Uploaded Data")
    st.write(df.head())

    st.markdown("🎯 Sending rows to prediction API...")

    results = []
    for _, row in df.iterrows():
        payload = row.to_dict()
        try:
            response = requests.post("http://localhost:5000/predict", json=payload)
            response.raise_for_status()
            result = response.json()
            results.append({
                "prediction": result["prediction"],
                "probability": round(result["probability"], 3)
            })
        except Exception as e:
            results.append({"prediction": "error", "probability": "error"})

    results_df = pd.concat([df.reset_index(drop=True), pd.DataFrame(results)], axis=1)

    st.subheader("📊 Predictions")
    st.dataframe(results_df)

    st.markdown("✅ Done. You can download the results.")
    st.download_button("Download Results", data=results_df.to_csv(index=False), file_name="cloudsense_predictions.csv")
