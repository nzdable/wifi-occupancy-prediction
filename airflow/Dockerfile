# airflow/Dockerfile
FROM apache/airflow:2.7.2

# Install any Python packages required by your DAGs or scripts
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your training scripts into the Airflow container
COPY dags/ /opt/airflow/dags/
COPY scripts/ /opt/airflow/scripts/
# Mount data and models folders via docker-compose.yml volumes