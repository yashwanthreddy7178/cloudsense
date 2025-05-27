# spark_jobs/preprocess_telemetry_logs.py

import os
import logging
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, hour, dayofweek
from pyspark.sql.types import DoubleType, IntegerType, StringType, TimestampType

# Set Hadoop path
os.environ['HADOOP_HOME'] = r"F:\de\hadoop-3.4.0"
os.environ['PATH'] += os.pathsep + r"F:\de\hadoop-3.4.0\bin"

# Set Java home for Spark
os.environ['JAVA_HOME'] = r"C:\Users\yashw\AppData\Roaming\Cursor\User\globalStorage\pleiades.java-extension-pack-jdk\java\11"

# Spark temp dir fix for Windows
os.environ['SPARK_LOCAL_DIRS'] = os.path.abspath("spark_tmp")
os.makedirs("spark_tmp", exist_ok=True)

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_and_cast(spark: SparkSession, path: str) -> DataFrame:
    logger.info(f"Reading CSV file from: {path}")
    df = spark.read.option("header", "true").csv(path)
    logger.info("Casting columns to appropriate types...")
    return df.withColumn("timestamp", col("timestamp").cast(TimestampType())) \
             .withColumn("cpu_util", col("cpu_util").cast(DoubleType())) \
             .withColumn("mem_util", col("mem_util").cast(DoubleType())) \
             .withColumn("disk_io", col("disk_io").cast(IntegerType())) \
             .withColumn("net_io", col("net_io").cast(IntegerType())) \
             .withColumn("active_processes", col("active_processes").cast(IntegerType())) \
             .withColumn("label_exhausted", col("label_exhausted").cast(IntegerType())) \
             .withColumn("vm_type", col("vm_type").cast(StringType()))

def add_features(df: DataFrame) -> DataFrame:
    logger.info("Engineering new features...")
    return df.withColumn("hour_of_day", hour("timestamp")) \
             .withColumn("day_of_week", dayofweek("timestamp")) \
             .withColumn("io_ratio", (col("disk_io") + 1) / (col("net_io") + 1)) \
             .withColumn("cpu_mem_ratio", col("cpu_util") / (col("mem_util") + 1e-6)) \
             .withColumn("load_score", col("cpu_util") * col("mem_util") * col("active_processes"))

def run_preprocessing(input_path="data/raw_telemetry_logs/telemetry_logs.csv",
                      output_path="data/processed/telemetry_features.parquet"):
    logger.info("🚀 Starting Spark session...")
    spark = (SparkSession.builder
            .appName("TelemetryPreprocessor")
            .config("spark.driver.memory", "2g")
            .config("spark.executor.memory", "2g")
            .config("spark.sql.shuffle.partitions", "2")
            .master("local[*]")
            .getOrCreate())

    try:
        df = load_and_cast(spark, input_path)
        df = add_features(df)

        logger.info("Filtering rows with missing data...")
        df = df.filter(df["cpu_util"].isNotNull() & df["mem_util"].isNotNull())

        logger.info(f"Saving output to: {output_path}")
        df.write.mode("overwrite").parquet(output_path)

        logger.info("✅ Preprocessing complete. Data saved successfully.")
    except Exception as e:
        logger.error(f"🔥 Error during preprocessing: {e}")
    finally:
        logger.info("🧹 Stopping Spark session.")
        spark.stop()

if __name__ == "__main__":
    run_preprocessing()
