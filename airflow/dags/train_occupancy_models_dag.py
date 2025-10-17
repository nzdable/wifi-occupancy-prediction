# airflow/dags/train_occupancy_models_dag.py
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
import pendulum

# Define your file names and model scripts
FILE_NAMES = [
    'Miguel_Pro_cleaned.csv',
    'Gisbert_2nd_Floor_cleaned.csv',
    'American_Corner_cleaned.csv',
    'Gisbert_4th_Floor_cleaned.csv',
    'Gisbert_5th_Floor_cleaned.csv',
    'Gisbert_3rd_Floor_cleaned.csv'
]

MODEL_SCRIPTS = {
    'cnn_only': '/opt/airflow/scripts/cnn_only.py',
    'lstm_only': '/opt/airflow/scripts/lstm_only.py',
    'hybrid_cnn_lstm': '/opt/airflow/scripts/hybrid_cnn_lstm_model.py',
    'cnn_lstm_attention_auxiliary_shap': '/opt/airflow/scripts/cnn_lstm_with_attention_auxiliary_features_and_shap.py'
}

default_args = {
    'owner': 'airflow',
    'start_date': pendulum.datetime(2023, 1, 1, tz="UTC"),
    'retries': 1,
}

with DAG(
    dag_id='train_occupancy_models',
    default_args=default_args,
    description='Automate training of occupancy prediction models',
    schedule_interval=None, # Run manually or via external trigger
    tags=['occupancy', 'training', 'ml'],
    catchup=False,
) as dag:

    # Task to ensure model directory exists (important for initial runs)
    create_model_dir = BashOperator(
        task_id='create_model_directory',
        bash_command='mkdir -p /opt/airflow/models',
    )

    training_tasks = []
    for model_type, script_path in MODEL_SCRIPTS.items():
        # The Python script itself will handle loading data, training, and saving the model.
        # We pass arguments like the output directory for models.
        # Note: Your Python scripts currently print results to console and show plots.
        # You'll need to modify them to actually *save* the trained models
        # (e.g., using model.save('models/model_name.h5') for TensorFlow models)
        # and also save the scaler objects (e.g., using pickle or joblib).
        # For simplicity, this example just runs the scripts.
        # We assume the scripts will save models to /opt/airflow/models

        train_task = BashOperator(
            task_id=f'train_{model_type}_model',
            bash_command=f'python {script_path}',
            # environment variables or arguments could be passed here
            # to customize output paths within the script
            # Example: bash_command=f'python {script_path} --output_dir /opt/airflow/models'
        )
        training_tasks.append(train_task)

    create_model_dir >> training_tasks