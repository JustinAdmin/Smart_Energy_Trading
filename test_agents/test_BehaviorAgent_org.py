import os
import joblib
import pandas as pd
import lightgbm as lgb
import numpy as np

# Get the project directory dynamically based on the script location
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Define paths relative to the project directory
model_filename = os.path.join(project_dir, "test_agents", "models", "lightgbm_ranker_model.pkl")
preprocess_test_data_filename = os.path.join(project_dir, "test_agents", "models", "preprocessed_smart_home_data.csv")

# Load the trained LightGBM model
try:
    model = joblib.load(model_filename)
    print(f"✅ Model loaded successfully from {model_filename}")
except Exception as e:
    print(f"❌ Error loading model: {e}")
    exit(1)

# Load the preprocessed test dataset
try:
    test_data = pd.read_csv(preprocess_test_data_filename)
    print(f"✅ Preprocessed test data loaded successfully from {preprocess_test_data_filename}")
except Exception as e:
    print(f"❌ Error loading preprocessed test data: {e}")
    exit(1)

# Drop unneeded features to match the model's expected input
columns_to_drop = [
    "timestamp", "occupancy_status", "hour", "date", "year",
    "is_weekday", "season_Autumn", "season_Spring", "season_Summer",
    "season_Winter", "appliance_encoded", "priority"
]
test_data.drop(columns=columns_to_drop, inplace=True, errors='ignore')

# Extract the required features for prediction
X_test = test_data.copy()

# Predict priority scores using the loaded model
try:
    y_pred = model.predict(X_test)
except Exception as e:
    print(f"❌ Prediction error: {e}")
    exit(1)

# Add predictions to the test DataFrame
X_test["predicted_priority"] = y_pred

# Normalize predictions between 0 and 1
y_pred_norm = (y_pred - y_pred.min()) / (y_pred.max() - y_pred.min())

# Check if predicted values have sufficient variance
if np.unique(y_pred_norm).size > 6:
    ranked_preds = pd.Series(y_pred_norm).rank(method="first")
    X_test["predicted_priority"] = pd.qcut(ranked_preds, 6, labels=[1, 2, 3, 4, 5, 6])
else:
    X_test["predicted_priority"] = pd.cut(y_pred_norm, bins=6, labels=[1, 2, 3, 4, 5, 6])

# Group by home_id and export data for each home (up to h10)
for home_id in range(1, 11):
    home_data = X_test[X_test['home_id'] == home_id]
    if not home_data.empty:
        output_path = os.path.join(project_dir, "test_agents", "models", f"house_{home_id}.csv")
        home_data.to_csv(output_path, index=False)
        print(f"✅ Data for house {home_id} saved to '{output_path}'")

print("✅ All house data successfully processed and exported.")
