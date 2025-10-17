# streamlit_app/utils.py
import tensorflow as tf
from tensorflow.keras.models import load_model
import numpy as np
import pandas as pd
import pickle
from datetime import datetime, time
from sklearn.preprocessing import MinMaxScaler # Import for type hinting, though loaded from pickle

# Define your sequence length (must match training)
SEQUENCE_LENGTH = 24
N_STEPS = 6 # For hybrid model
N_SEQ = 4   # For hybrid model

# Helper function from your training script for schedule features
def create_schedule_features(df_index):
    """
    Create comprehensive schedule-based features for the university library
    """
    features = pd.DataFrame(index=df_index)

    # Basic time features
    features['hour'] = df_index.hour
    features['day_of_week'] = df_index.dayofweek # Monday=0, Sunday=6
    features['date'] = df_index.date

    # Academic schedule features
    features['is_weekend'] = (features['day_of_week'] >= 5).astype(int)
    features['is_sunday'] = (features['day_of_week'] == 6).astype(int)

    # Library operating hours
    # Weekdays: 7:30 AM - 8:00 PM (19:30 - 20:00 in 24hr format)
    # Saturday: 7:30 AM - 12:00 PM (07:30 - 12:00)
    # Sunday: Closed
    features['library_open'] = 0

    # Weekday hours (Mon-Fri): 7:30 AM - 8:00 PM
    weekday_mask = (features['day_of_week'] < 5)
    weekday_hours_mask = (features['hour'] >= 7) & (features['hour'] < 20)
    # Include 7:30 AM slot (hour 7 covers 7:00-7:59, so 7:30 is included)
    features.loc[weekday_mask & weekday_hours_mask, 'library_open'] = 1

    # Saturday hours: 7:30 AM - 12:00 PM
    saturday_mask = (features['day_of_week'] == 5)
    saturday_hours_mask = (features['hour'] >= 7) & (features['hour'] < 12)
    features.loc[saturday_mask & saturday_hours_mask, 'library_open'] = 1

    # Class schedule features (7:30 AM - 9:30 PM on weekdays)
    features['class_hours'] = 0
    class_hours_mask = (features['hour'] >= 7) & (features['hour'] < 22)  # 7:30 AM - 9:30 PM
    features.loc[weekday_mask & class_hours_mask, 'class_hours'] = 1

    # Activity period (Mon, Wed 3-6 PM) - no classes but students may use library
    features['activity_period'] = 0
    activity_days = (features['day_of_week'] == 0) | (features['day_of_week'] == 2)  # Mon=0, Wed=2
    activity_hours = (features['hour'] >= 15) & (features['hour'] < 18)  # 3-6 PM
    features.loc[activity_days & activity_hours, 'activity_period'] = 1

    # Peak academic hours (common class times)
    # Morning peak: 8-11 AM, Afternoon peak: 1-4 PM, Evening: 6-8 PM
    features['morning_peak'] = ((features['hour'] >= 8) & (features['hour'] < 11) & weekday_mask).astype(int)
    features['afternoon_peak'] = ((features['hour'] >= 13) & (features['hour'] < 16) & weekday_mask).astype(int)
    features['evening_peak'] = ((features['hour'] >= 18) & (features['hour'] < 20) & weekday_mask).astype(int)

    # Holiday flags
    features['is_holiday'] = 0

    # Specific holidays for 2024 (adjust year as needed)
    holidays_2024 = [
        '2024-08-15',  # Kadayawan holiday
        '2024-08-21',  # Ninoy Aquino Day (Thursday)
        '2024-08-25',  # National Heroes' Day (Monday)
    ]

    for holiday in holidays_2024:
        holiday_date = pd.to_datetime(holiday).date()
        features.loc[features['date'] == holiday_date, 'is_holiday'] = 1

    # Preliminary week (Aug 18-23, 2024) - no regular classes
    prelim_start = pd.to_datetime('2024-08-18').date()
    prelim_end = pd.to_datetime('2024-08-23').date()
    features['is_preliminary'] = 0
    prelim_mask = (features['date'] >= prelim_start) & (features['date'] <= prelim_end)
    features.loc[prelim_mask, 'is_preliminary'] = 1

    # During preliminary week, override class_hours since there are no regular classes
    features.loc[prelim_mask, 'class_hours'] = 0

    # Study intensity indicator (combination of factors that increase library usage)
    features['study_intensity'] = (
        features['library_open'] *
        (features['class_hours'] + features['activity_period'] +
         (1 - features['is_holiday']) + (1 - features['is_preliminary']))
    ).clip(0, 1)

    # Time of day categories for cyclic encoding
    features['time_category'] = 'other'
    features.loc[(features['hour'] >= 7) & (features['hour'] < 12), 'time_category'] = 'morning'
    features.loc[(features['hour'] >= 12) & (features['hour'] < 17), 'time_category'] = 'afternoon'
    features.loc[(features['hour'] >= 17) & (features['hour'] < 20), 'time_category'] = 'evening'

    return features


def load_model_and_scaler(location, model_type):
    """Loads the trained Keras model and MinMaxScaler."""
    model_path = f'/app/models/{location}_{model_type}.h5'
    scaler_path = f'/app/models/{location}_{model_type}_scaler.pkl'

    try:
        model = load_model(model_path)
        with open(scaler_path, 'rb') as f:
            scaler = pickle.load(f)
        return model, scaler
    except FileNotFoundError:
        return None, None
    except Exception as e:
        print(f"Error loading {model_type} model or scaler for {location}: {e}")
        return None, None

def load_advanced_model_components(location):
    """Loads the advanced CNN-LSTM with Attention model, scaler, and encoder."""
    model_path = f'/app/models/{location}_cnn_lstm_attention_auxiliary_shap.h5'
    occ_scaler_path = f'/app/models/{location}_cnn_lstm_attention_auxiliary_shap_occ_scaler.pkl'
    encoder_path = f'/app/models/{location}_cnn_lstm_attention_auxiliary_shap_encoder.pkl'

    try:
        model = load_model(model_path)
        with open(occ_scaler_path, 'rb') as f:
            occ_scaler = pickle.load(f)
        with open(encoder_path, 'rb') as f:
            encoder = pickle.load(f)
        return model, occ_scaler, encoder
    except FileNotFoundError:
        return None, None, None
    except Exception as e:
        print(f"Error loading advanced model components for {location}: {e}")
        return None, None, None


def get_realtime_features(location_data_path, current_datetime, occ_scaler=None, encoder=None):
    """
    Generates the feature vector for a single prediction based on current time
    and historical data.
    """
    try:
        df = pd.read_csv(location_data_path)
        df['Start_dt'] = pd.to_datetime(df['Start_dt'])
        df.set_index('Start_dt', inplace=True)
        occupancy_raw = df['Client MAC'].resample('h').nunique().rename('occupancy').reset_index()
        occupancy_raw.dropna(inplace=True)
        occupancy_raw.set_index('Start_dt', inplace=True)

        # Get the latest SEQUENCE_LENGTH hours of data
        # Ensure we have enough historical data up to current_datetime - 1 hour
        end_history_dt = current_datetime - pd.Timedelta(hours=1)
        start_history_dt = end_history_dt - pd.Timedelta(hours=SEQUENCE_LENGTH - 1)

        # Filter historical occupancy data
        historical_occupancy = occupancy_raw.loc[start_history_dt:end_history_dt, 'occupancy']

        if len(historical_occupancy) != SEQUENCE_LENGTH:
            # Handle cases where not enough historical data is available
            # For simplicity, we might pad with zeros or return None
            print(f"Warning: Not enough historical data for {location_data_path}. Needed {SEQUENCE_LENGTH}, got {len(historical_occupancy)}")
            return None, None

        # Create a DataFrame for historical + current hour for feature generation
        # The 'current_datetime' is for the hour *we are trying to predict*
        full_index = pd.to_datetime(pd.Series(historical_occupancy.index.tolist() + [current_datetime]))
        combined_df = pd.DataFrame(index=full_index)
        combined_df['occupancy'] = pd.Series(historical_occupancy.values.tolist() + [np.nan], index=full_index)

        schedule_features = create_schedule_features(combined_df.index)
        combined_df = combined_df.join(schedule_features)

        # Add cyclic encoding for hour and day of week
        combined_df['hour_sin'] = np.sin(2 * np.pi * combined_df['hour'] / 24)
        combined_df['hour_cos'] = np.cos(2 * np.pi * combined_df['hour'] / 24)
        combined_df['dow_sin'] = np.sin(2 * np.pi * combined_df['day_of_week'] / 7)
        combined_df['dow_cos'] = np.cos(2 * np.pi * combined_df['day_of_week'] / 7)

        # Scale occupancy using the provided scaler
        if occ_scaler:
            combined_df['occupancy_scaled'] = occ_scaler.transform(combined_df[['occupancy']])
        else: # For simple models, only occupancy is scaled, and the scaler is specific to occupancy
            temp_scaler = MinMaxScaler(feature_range=(0, 1))
            combined_df['occupancy_scaled'] = temp_scaler.fit_transform(combined_df[['occupancy']])
            # If `occ_scaler` is None, this means we are in the context of simple models.
            # We need to save and load the `temp_scaler` in `load_model_and_scaler`.
            # For this simplified version, let's assume `occ_scaler` will always be provided
            # if we are using models that need it (i.e., advanced model).
            # For simpler models, we'll only scale `occupancy_values` and `y_pred` with the loaded `scaler`.

        # Define feature columns (must match training order)
        feature_columns_advanced = [
            'occupancy_scaled', 'is_weekend', 'is_sunday', 'library_open', 'class_hours',
            'activity_period', 'morning_peak', 'afternoon_peak', 'evening_peak',
            'is_holiday', 'is_preliminary', 'study_intensity',
            'hour_sin', 'hour_cos', 'dow_sin', 'dow_cos'
        ]

        if encoder: # For advanced model
            numerical_features = combined_df[feature_columns_advanced].values
            cat_features = encoder.transform(combined_df[['hour', 'day_of_week']])
            all_features = np.hstack([numerical_features, cat_features])
        else: # For simple models, only occupancy is the feature, other time features might be handled implicitly
            # For simple models, we only need the scaled historical occupancy
            all_features = combined_df['occupancy_scaled'].values.reshape(-1, 1)

        # The input to the model should be the last `SEQUENCE_LENGTH` steps
        model_input = all_features[-SEQUENCE_LENGTH:]

        return model_input, occ_scaler # Return scaler for inverse transform if not already provided

    except Exception as e:
        print(f"Error getting realtime features for {location_data_path}: {e}")
        return None, None

# Define a custom callback to load model safely if needed (for custom objects)
# For simple Keras layers, this might not be strictly necessary, but good practice.
# from tensorflow.keras.utils import get_custom_objects
# class CustomAttention(tf.keras.layers.Layer):
#     # ... your attention layer implementation ...
# get_custom_objects().update({'CustomAttention': CustomAttention}) # if you had one


def predict_occupancy(model, scaler, model_input, model_type):
    """Makes a prediction and inverse transforms it."""
    try:
        # Reshape input based on model type
        if model_type in ['cnn_only', 'lstm_only']:
            model_input_reshaped = model_input.reshape(1, SEQUENCE_LENGTH, 1)
        elif model_type == 'hybrid_cnn_lstm':
            model_input_reshaped = model_input.reshape(1, N_SEQ, N_STEPS, 1)
        elif model_type == 'cnn_lstm_attention_auxiliary_shap':
            model_input_reshaped = model_input.reshape(1, SEQUENCE_LENGTH, model_input.shape[1])
        else:
            raise ValueError(f"Unknown model type: {model_type}")

        scaled_prediction = model.predict(model_input_reshaped, verbose=0)
        # Ensure the prediction is 2D for inverse_transform
        actual_prediction = scaler.inverse_transform(scaled_prediction.reshape(-1, 1))[0][0]
        return max(0, int(round(actual_prediction))) # Occupancy can't be negative, round to nearest integer
    except Exception as e:
        print(f"Error making prediction: {e}")
        return None