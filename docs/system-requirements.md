# 🏗️ Wi-Fi Occupancy Prediction System

## System Scope and Requirements

### 🎯 System Overview
The Wi-Fi Occupancy Prediction System aims to estimate real-time and forecasted occupancy levels in campus library spaces using Wi-Fi connection logs and RFID entry data. The system leverages Next.js for the frontend, Django REST Framework for the backend, and Apache Airflow for data automation and model training.

By analyzing anonymized Wi-Fi data, the system enables administrators to understand space utilization patterns, while students can view real-time library occupancy before visiting.

### 🧭 System Goals
Predict occupancy trends using Wi-Fi and RFID data.

Visualize occupancy levels and trends in an intuitive dashboard.

Automate data ingestion, preprocessing, and model retraining.

Ensure privacy and data security through anonymization.

Support continuous improvement through reproducible pipelines.

### 👥 User Roles
Role Description Key Capabilities
Admin Responsible for managing data, users, and model retraining. 
• Upload and clean Wi-Fi/RFID datasets
• View and export reports
• Trigger Airflow pipelines (ETL, retraining)
• Manage student access and roles

Student Regular user who views occupancy and library trends. 
• View real-time and historical occupancy levels
• Filter data by date/time
• View predicted crowd trends before visiting the library

### 🧩 Functional Requirements
ID Category Requirement
FR-1 Prediction The system must predict occupancy levels at 15-, 30-, and 60-minute intervals using Wi-Fi log data.
FR-2 Visualization Display occupancy trends in real-time and historical charts.
FR-3 Data Management (Admin) Admins must be able to upload, clean, and manage Wi-Fi and RFID datasets.
FR-4 Automation Airflow automates ingestion, preprocessing, and model training on schedule or trigger.
FR-5 Ground Truth Integration Merge RFID entry logs to establish ground truth for training and evaluation.
FR-6 User Management Admins can add, remove, or update student accounts.
FR-7 Access Control Students can view dashboards only; Admins have full control.
FR-8 Storage Store all data and model artifacts in MinIO/S3.
FR-9 API Access Expose key endpoints for logs, predictions, and models through REST API.

### 🛡️ Non-Functional Requirements
ID Category Requirement
NFR-1 Scalability Must handle large Wi-Fi datasets and multiple access points.
NFR-2 Reproducibility Pipelines and models must be fully reproducible using Airflow DAGs.
NFR-3 Security All Wi-Fi MAC addresses must be anonymized (SHA-256). Access must be role-based.
NFR-4 Maintainability Modular structure (/frontend, /backend, /airflow, /infra, /docs) and Docker-based setup.
NFR-5 Performance API responses and charts load within 2 seconds under typical load.
NFR-6 Usability UI must be intuitive, responsive, and accessible to students and staff.
NFR-7 Reliability Scheduled Airflow jobs must run consistently with logging and failure notifications.
NFR-8 Data Privacy No personally identifiable information (PII) stored; all identifiers hashed.
NFR-9 Availability Target uptime of ≥ 99% for hosted systems.

### 🧮 Key Use Cases
Use Case Description Actor
UC-1: View Library Occupancy Dashboard Student views real-time and predicted occupancy levels through charts and graphs. Student
UC-2: Upload Wi-Fi Logs Admin uploads Wi-Fi log datasets from the UITO or MIS. Admin
UC-3: Automate Data Preprocessing Airflow processes raw Wi-Fi logs and cleans them automatically. Admin
UC-4: Train and Evaluate Models Admin triggers model retraining and views results/metrics. Admin
UC-5: Manage User Accounts Admin manages student accounts and access roles. Admin
UC-6: View Occupancy Trends Student filters and explores historical data for peak hours or specific dates. Student

### 🧱 Technical Scope
Frontend: Next.js + TailwindCSS

Backend: Django REST Framework

Database: PostgreSQL

Cache/Broker: Redis

Object Storage: MinIO/S3

Automation: Apache Airflow (ETL + Model Training)

Deployment: Docker Compose for development (Kubernetes optional for production)
