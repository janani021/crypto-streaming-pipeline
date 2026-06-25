from datetime import datetime
from airflow import DAG
from airflow.operators.bash import BashOperator

DBT_PROJECT_DIR = "/opt/airflow/dbt/crypto_risk"

with DAG(
    dag_id="crypto_risk_dbt",
    description="Run dbt models and tests for crypto risk analytics",
    start_date=datetime(2026, 1, 1),
    schedule="*/5 * * * *",
    catchup=False,
    tags=["crypto", "dbt", "analytics"],
) as dag:

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command="export DBT_PROFILES_DIR=/home/airflow/.dbt && cd /opt/airflow/dbt/crypto_risk && dbt run",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command="export DBT_PROFILES_DIR=/home/airflow/.dbt && cd /opt/airflow/dbt/crypto_risk && dbt test",
    )

    dbt_run >> dbt_test