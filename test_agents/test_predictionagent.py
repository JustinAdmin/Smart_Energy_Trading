"""Test_PredictionAgent.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1vPNVZjKCGu3dJiOOfgu1uXfSOR1MjGvD
"""
import os
import numpy as np
import tensorflow as tf # to Import TensorFlow, you may need to run -----------> pip install tensorflow
import random

# Get the project directory dynamically based on the script location
project_dir = os.path.dirname(os.path.dirname(__file__))

# Define paths relative to the project directory
model_path = os.path.join(project_dir, "models","energy_lstm.keras")
data_path = os.path.join(project_dir,"models", "energy_test_set.npz")
print(model_path)
# Load the trained LSTM model
model = tf.keras.models.load_model(model_path)

# Load the saved test set
data = np.load(data_path)
X_test = data["X_test"]
y_test = data["y_test"]
y_scaled = data["y_scaled"]
X_scaled = data["X_scaled"]
 
# Select a Random Sample from Test Set
random_idx = random.randint(0, len(X_test) - 1)  # Pick a random index
random_test_sample = X_test[random_idx].reshape(1, X_test.shape[1], 1)  # Reshape for LSTM input
#print(f"🔹 Random Test Set Sample: {random_test_sample.shape}")#=>(1,18,1)
# Make Prediction
random_prediction = model.predict(random_test_sample)

print(f"🔹 Random test set Sample Prediction:")
print(f"   - Energy Demand: {random_prediction[0][0]:.2f} kWh")
print(f"   - Solar Production: {random_prediction[0][1]:.2f} kWh")
