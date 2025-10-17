Repository for our thesis on WiFi-based occupancy prediction at Ateneo de Davao University, utilizing an attention-enhanced CNN-LSTM architecture.

# Library Occupancy Prediction System

This project automates the training of deep learning models for predicting library occupancy and provides a real-time prediction interface using Streamlit.

## Architecture

- **Airflow:** Orchestrates the training pipeline for various deep learning models (CNN-Only, LSTM-Only, Hybrid CNN-LSTM, CNN-LSTM with Attention and Auxiliary Features).
- **TensorFlow/Keras:** Used for building and training the deep learning models.
- **Pandas/Numpy/Scikit-learn:** For data preprocessing and feature engineering.
- **Streamlit:** Provides a user-friendly web interface for real-time occupancy predictions.
- **Docker/Docker Compose:** Containerizes all components for isolated and reproducible environments.
