from airflow import DAG
from datetime import datetime
from test_operator import S3ListOperator

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 1, 1),
    'retries': 1,
}

with DAG(
    's3_list_dag',
    default_args=default_args,
    description='DAG for listing files in S3 using a custom operator',
    schedule_interval='@daily',
    catchup=False,
) as dag:

    # S3 버킷의 파일 목록을 가져오는 작업
    list_s3_files = S3ListOperator(
        task_id='list_s3_files',
        aws_conn_id='aws_default',
        bucket_name='otto-glue',
    )

    list_s3_files
