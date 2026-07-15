"""DAG Air Quality Pipeline — Automatisation Airflow

Tourne toutes les heures : extract → transform → validate → load vers Neon.tech
Les scripts pipelines sont dans dags/pipeline/ (version adaptée pour Airflow).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

PIPELINE_DIR = "/opt/airflow/dags/pipeline"

default_args = {
    "owner": "airflow",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

with DAG(
    dag_id="air_quality_pipeline",
    description="OpenWeatherMap → Neon.tech",
    default_args=default_args,
    schedule="@hourly",
    start_date=datetime(2026, 7, 1),
    catchup=False,
    tags=["air-quality"],
) as dag:

    extract = BashOperator(
        task_id="extract",
        bash_command="python3 extract.py",
        cwd=PIPELINE_DIR,
    )

    transform = BashOperator(
        task_id="transform",
        bash_command="python3 transform.py",
        cwd=PIPELINE_DIR,
    )

    validate = BashOperator(
        task_id="validate",
        bash_command="python3 validate.py",
        cwd=PIPELINE_DIR,
    )

    load = BashOperator(
        task_id="load_warehouse",
        bash_command="python3 load_warehouse.py",
        cwd=PIPELINE_DIR,
    )

    extract >> transform >> validate >> load
