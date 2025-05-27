# model/training_pipeline.py

import os
import pandas as pd
import lightgbm as lgb
import optuna
import mlflow
import mlflow.lightgbm
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score
import joblib
import json
import logging
import psycopg2
from sqlalchemy import create_engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure MLflow
MLFLOW_TRACKING_URI = "postgresql://airflow:airflow@postgres/airflow"
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

def train_model():
    """
    Main training function that can be called by Airflow DAG.
    Returns True if training was successful, False otherwise.
    """
    try:
        logger.info("Starting model training pipeline...")
        
        # Load data
        DATA_PATH = "/opt/airflow/data/processed/telemetry_features.parquet"
        logger.info(f"Loading data from {DATA_PATH}")
        df = pd.read_parquet(DATA_PATH)

        # Target and features
        TARGET = "label_exhausted"
        X = df.drop(columns=[TARGET, "timestamp", "vm_id", "vm_type"], errors="ignore")
        y = df[TARGET]

        # Train-test split
        X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

        # MLflow
        mlflow.lightgbm.autolog()

        # Optuna study config
        study_name = "cloudsense_lgbm_study"
        storage = "postgresql://airflow:airflow@postgres/airflow"

        # Ensure directories exist
        os.makedirs("/opt/airflow/model", exist_ok=True)
        os.makedirs("/opt/airflow/api", exist_ok=True)

        # Test database connection
        try:
            conn = psycopg2.connect(
                dbname="airflow",
                user="airflow",
                password="airflow",
                host="postgres"
            )
            conn.close()
            logger.info("✅ Successfully connected to PostgreSQL database")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL database: {str(e)}")
            raise

        # Objective function
        def objective(trial):
            params = {
                "objective": "binary",
                "metric": "binary_logloss",
                "boosting_type": "gbdt",
                "learning_rate": trial.suggest_float("learning_rate", 1e-3, 0.3, log=True),
                "num_leaves": trial.suggest_int("num_leaves", 16, 128),
                "max_depth": trial.suggest_int("max_depth", 3, 12),
                "min_data_in_leaf": trial.suggest_int("min_data_in_leaf", 20, 100),
                "feature_fraction": trial.suggest_float("feature_fraction", 0.6, 1.0),
                "bagging_fraction": trial.suggest_float("bagging_fraction", 0.6, 1.0),
                "bagging_freq": trial.suggest_int("bagging_freq", 1, 5),
                "verbosity": -1,
                "seed": 42
            }

            with mlflow.start_run(nested=True):
                dtrain = lgb.Dataset(X_train, label=y_train)
                dvalid = lgb.Dataset(X_val, label=y_val, reference=dtrain)
                model = lgb.train(params, dtrain, valid_sets=[dvalid])
                preds = model.predict(X_val)
                preds_binary = (preds > 0.5).astype(int)
                return f1_score(y_val, preds_binary)

        logger.info("🔁 Connecting to Optuna study...")
        try:
            # Try to load existing study
            study = optuna.create_study(
                direction="maximize",
                study_name=study_name,
                storage=storage,
                load_if_exists=True
            )
        except Exception as e:
            logger.warning(f"Failed to load existing study: {str(e)}")
            logger.info("Creating new study...")
            # Drop existing study if it exists
            # Delete old/broken study if exists
            try:
                optuna.delete_study(study_name=study_name, storage=storage)
                logger.info(f"🧹 Deleted existing Optuna study '{study_name}' to fix schema issues.")
            except Exception as e:
                logger.warning(f"Failed to delete old study: {str(e)}")

            # Create new study
            study = optuna.create_study(
                direction="maximize",
                study_name=study_name,
                storage=storage
            )

        logger.info("🧪 Starting/resuming tuning...")
        with mlflow.start_run(run_name="optuna_lightgbm_run", nested=False):
            study.optimize(objective, n_trials=25)

        logger.info(f"🏆 Best trial: {study.best_trial.number}")
        logger.info(f"✅ Best params: {study.best_params}")
        logger.info(f"✅ Best F1: {study.best_value}")

        # Retrain model using best params
        logger.info("💾 Training final model on full training set...")
        best_params = {**study.best_params, "objective": "binary", "metric": "binary_logloss", "verbosity": -1, "seed": 42}
        dtrain = lgb.Dataset(X_train, label=y_train)
        best_model = lgb.train(best_params, dtrain)

        # Save model and config
        model_path = "/opt/airflow/model/best_model.pkl"
        config_path = "/opt/airflow/api/model_config.json"
        
        joblib.dump(best_model, model_path)
        logger.info(f"✅ Saved model to {model_path}")

        with open(config_path, "w") as f:
            json.dump({"features": list(X.columns)}, f)
        logger.info(f"✅ Saved config to {config_path}")
        
        return True

    except Exception as e:
        logger.error(f"Error during model training: {str(e)}")
        return False

if __name__ == "__main__":
    train_model()
