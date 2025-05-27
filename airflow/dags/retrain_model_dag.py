from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import sys
import os
import logging

# Add the model directory to Python path
sys.path.append('/opt/airflow/model')

# Import the training pipeline
try:
    from training_pipeline import train_model
except ImportError as e:
    logging.error(f"Failed to import training_pipeline: {e}")
    raise

def train_model_task():
    """
    Wrapper function for the training pipeline that raises an exception if training fails.
    """
    success = train_model()
    if not success:
        raise Exception("Model training failed")

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'retrain_model_weekly',
    default_args=default_args,
    description='Weekly model retraining pipeline',
    schedule_interval='0 0 * * 0',  # Run at midnight every Sunday
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['cloudsense', 'ml'],
)

retrain_task = PythonOperator(
    task_id='retrain_model',
    python_callable=train_model_task,
    dag=dag,
)

# This is required for Airflow to discover the DAG
globals()['retrain_model_weekly'] = dag 