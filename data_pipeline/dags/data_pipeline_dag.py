from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from datetime import datetime, timedelta
from data_pipeline.scripts.pipeline_runner import run_pipeline


default_args = {
    'owner': 'Raghav G',
    'start_date': datetime(2025, 1, 15),
    'retries': 0,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'Data_Pipeline',
    default_args=default_args,
    description='Data Pipeline DAG for FrontShiftAI',
    catchup=False,
)as dag:
    
    pipeline_runner_task = PythonOperator(
        task_id= 'pipeline_runner',
        python_callable= run_pipeline,
    )


    # Set task dependencies
    pipeline_runner_task


if __name__ == '__main__':
    dag.test()

