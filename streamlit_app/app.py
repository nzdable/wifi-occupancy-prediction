# streamlit_app/app.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os
from streamlit_app.utils import (
    load_model_and_scaler, load_advanced_model_components,
    get_realtime_features, predict_occupancy,
    SEQUENCE_LENGTH, N_STEPS, N_SEQ
)

st.set_page_config(layout="wide")

# Paths
MODEL_DIR = './models'
DATA_DIR = './data'

# File names for locations (must match your CSVs)
LOCATION_FILES = {
    'Miguel Pro': 'Miguel_Pro_cleaned.csv',
    'Gisbert 2nd Floor': 'Gisbert_2nd_Floor_cleaned.csv',
    'American Corner': 'American_Corner_cleaned.csv',
    'Gisbert 4th Floor': 'Gisbert_4th_Floor_cleaned.csv',
    'Gisbert 5th Floor': 'Gisbert_5th_Floor_cleaned.csv',
    'Gisbert 3rd Floor': 'Gisbert_3rd_Floor_cleaned.csv'
}

MODEL_TYPES = {
    'CNN Only': 'cnn_only',
    'LSTM Only': 'lstm_only',
    'Hybrid CNN-LSTM': 'hybrid_cnn_lstm',
    'CNN-LSTM with Attention & Auxiliary Features': 'cnn_lstm_attention_auxiliary_shap'
}

st.title("📚 Library Occupancy Prediction")
st.markdown("Predicting real-time occupancy for various library sections using trained deep learning models.")

# Sidebar for controls
st.sidebar.header("Prediction Settings")
selected_location_name = st.sidebar.selectbox("Select Library Location", list(LOCATION_FILES.keys()))
selected_model_name = st.sidebar.selectbox("Select Model Type", list(MODEL_TYPES.keys()))

selected_location_file = LOCATION_FILES[selected_location_name]
selected_model_type = MODEL_TYPES[selected_model_name]

# Date and time input for prediction (default to next hour)
current_time = datetime.now()
next_hour = current_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

st.sidebar.subheader("Prediction Target Date & Time")
prediction_date = st.sidebar.date_input("Date", value=next_hour.date())
prediction_time = st.sidebar.time_input("Time", value=next_hour.time())

target_datetime = datetime.combine(prediction_date, prediction_time)

# --- Load Models and Scalers ---
model = None
scaler = None
encoder = None # Only for advanced model

if selected_model_type == 'cnn_lstm_attention_auxiliary_shap':
    model, scaler, encoder = load_advanced_model_components(selected_location_name.replace(" ", "_"))
else:
    model, scaler = load_model_and_scaler(selected_location_name.replace(" ", "_"), selected_model_type)

if model is None or scaler is None:
    st.error(f"**Error:** Could not load the {selected_model_name} model for {selected_location_name}. "
             f"Please ensure the Airflow DAG has been run successfully to train and save the models "
             f"to the `models` directory. Expected files: "
             f"`{selected_location_name.replace(' ', '_')}_{selected_model_type}.h5` and "
             f"`{selected_location_name.replace(' ', '_')}_{selected_model_type}_scaler.pkl` "
             f"(or `_occ_scaler.pkl` and `_encoder.pkl` for advanced model).")
    st.stop()


# --- Real-time Prediction ---
st.header(f"Real-time Occupancy Prediction for {selected_location_name}")
st.subheader(f"Using {selected_model_name} Model")

st.info(f"Predicting occupancy for: **{target_datetime.strftime('%Y-%m-%d %H:00')}**")

# Get features for the prediction
location_data_path = os.path.join(DATA_DIR, selected_location_file)

model_input, actual_scaler_for_inverse_transform = get_realtime_features(
    location_data_path,
    target_datetime,
    occ_scaler=scaler if selected_model_type == 'cnn_lstm_attention_auxiliary_shap' else None,
    encoder=encoder
)

if model_input is None:
    st.warning("Not enough historical data available to make a prediction for the selected time. Please choose a later time or check data completeness.")
else:
    # Use the scaler that was actually used to scale the occupancy values for inverse transform.
    # For simple models, `scaler` is the one used for inverse transform.
    # For advanced model, `scaler` (which is `occ_scaler`) is also used.
    final_scaler_for_prediction = scaler if selected_model_type == 'cnn_lstm_attention_auxiliary_shap' else scaler

    predicted_occupancy = predict_occupancy(model, final_scaler_for_prediction, model_input, selected_model_type)

# streamlit_app/app.py (continued)

    if predicted_occupancy is not None:
        st.metric(label=f"Predicted Occupancy at {target_datetime.strftime('%H:00')}", value=f"{predicted_occupancy} users")

        st.subheader("Last 24 Hours Actual Occupancy (from historical data)")

        # Load historical data to plot
        try:
            df_hist = pd.read_csv(location_data_path)
            df_hist['Start_dt'] = pd.to_datetime(df_hist['Start_dt'])
            df_hist.set_index('Start_dt', inplace=True)
            occupancy_hist = df_hist['Client MAC'].resample('h').nunique().rename('occupancy')
            occupancy_hist.dropna(inplace=True)

            # Get the last 24 actual hours before the target prediction time
            # For visualization, we plot up to the hour *before* the prediction
            plot_end_dt = target_datetime - timedelta(hours=1)
            plot_start_dt = plot_end_dt - timedelta(hours=SEQUENCE_LENGTH - 1) # Last 24 hours

            recent_actual_occupancy = occupancy_hist.loc[plot_start_dt:plot_end_dt]

            # Create a dataframe for plotting
            plot_df = pd.DataFrame(index=pd.date_range(start=plot_start_dt, end=target_datetime, freq='h'))
            plot_df['Actual'] = recent_actual_occupancy
            plot_df['Predicted'] = np.nan
            plot_df.loc[target_datetime, 'Predicted'] = predicted_occupancy


            fig, ax = plt.subplots(figsize=(12, 6))
            ax.plot(plot_df['Actual'], marker='o', linestyle='-', color='blue', label='Actual Occupancy (Last 24h)')
            ax.plot(plot_df.index[-1], plot_df['Predicted'].iloc[-1], marker='X', markersize=10, color='red', label=f'Predicted Occupancy ({target_datetime.strftime("%H:00")})')
            ax.axvline(target_datetime, color='gray', linestyle='--', label='Prediction Point')

            ax.set_title(f'Occupancy Trends for {selected_location_name} with {selected_model_name} Prediction')
            ax.set_xlabel('Time')
            ax.set_ylabel('Number of Users')
            ax.legend()
            ax.grid(True, linestyle=':', alpha=0.6)
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            st.pyplot(fig)

        except Exception as e:
            st.error(f"Error loading historical data for plotting: {e}")

st.sidebar.markdown("---")
st.sidebar.markdown("Developed with Airflow, Streamlit, TensorFlow")