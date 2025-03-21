import pandas as pd
import numpy as np
import math

import seaborn as sns
import matplotlib.pyplot as plt

from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.preprocessing import MinMaxScaler, StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.metrics import mean_squared_error

import tensorflow as tf

import time
import requests
import xml.etree.ElementTree as ET
from pathlib import Path

# Function to parse a single XML file and extract data
def parse_xml(xml_file):
    # Initialize an empty list to store extracted data
  data_records = []


  tree = ET.parse(xml_file)
  root = tree.getroot()

  # Extract metadata
  created_at = root.find("CreatedAt").text if root.find("CreatedAt") is not None else None
  created_by = root.find("CreateBy").text if root.find("CreateBy") is not None else None
  start_date = root.find("StartDate").text if root.find("StartDate") is not None else None

  # Iterate over each DataSet
  for dataset in root.findall("DataSet"):
      series_name = dataset.get("Series")  # Get the Series attribute

      # Extract all values inside <Data> elements
      for data in dataset.findall("Data"):
          value = data.find("Value").text if data.find("Value") is not None else None

          # Append row data
          data_records.append({
              "StartDate": start_date,
              "Series": series_name,
              "Value": float(value) if value is not None else None
          })

  # Convert extracted data into a DataFrame
  return pd.DataFrame(data_records)

# Import datsets from xml into dataframe
demand = parse_xml('datasets/ontario_demand_multiday.xml')
actual_demand = demand[demand["Series"] == 'Actual']['Value']
actual_demand.reset_index(drop=True, inplace=True)

price = parse_xml('datasets/price_multiday.xml')
HOEP_price = price[price["Series"] == 'HOEP']['Value']
HOEP_price.reset_index(drop=True, inplace=True)
HOEP_price.info()

supply = parse_xml('datasets/generation_fuel_type_multiday.xml')
biofuel_supply = supply[supply["Series"] == 'BIOFUEL']['Value']
biofuel_supply.reset_index(drop=True, inplace=True)
gas_supply = supply[supply["Series"] == 'GAS']['Value']
gas_supply.reset_index(drop=True, inplace=True)
hydro_supply = supply[supply["Series"] == 'HYDRO']['Value']
hydro_supply.reset_index(drop=True, inplace=True)
nuclear_supply = supply[supply["Series"] == 'NUCLEAR']['Value']
nuclear_supply.reset_index(drop=True, inplace=True)
solar_supply = supply[supply["Series"] == 'SOLAR']['Value']
solar_supply.reset_index(drop=True, inplace=True)
wind_supply = supply[supply["Series"] == 'WIND']['Value']
wind_supply.reset_index(drop=True, inplace=True)

dataframe = pd.concat([
    actual_demand,
    HOEP_price,
    biofuel_supply,
    gas_supply,
    hydro_supply,
    nuclear_supply,
    solar_supply,
    wind_supply
], axis = 1)
dataframe.columns = ["actual_demand",
                     "HOEP_price",
                     "biofuel_supply",
                     "gas_supply",
                     "hydro_supply",
                     "nuclear_supply",
                     "solar_supply",
                     "wind_supply"]

# Create column that represents the total supply of power
dataframe['total_supply'] = dataframe.iloc[:, -6:].sum(axis=1)
dataframe = dataframe.dropna()
dataframe.head()
dataframe.info()


# How to run and test model

def create_sequences(data, target, lookback=24):
    X = []
    y = []
    for i in range(lookback, len(data)):
        X.append(data[i-lookback:i])  # Last `lookback` hours of features
        y.append(target[i, 0])  # Target: actual_demand of the next hour
    return np.array(X), np.array(y)

# Load the model for inference in real-time
demand_model = tf.keras.models.load_model('models\lstm_cnn_demand_predictor.keras')

# Load the dataset
data = dataframe

# Normalize features using MinMaxScaler
scaler = MinMaxScaler()
scaled_data = scaler.fit_transform(data)
print(scaler.data_min_)
print(scaler.data_range_)
demand_X = scaled_data[:,-8:]
demand_y = scaled_data[:,:1]

# Create sequences for LSTM
lookback = 24  # Look at the last 24 hours (1 day)
X, y = create_sequences(demand_X, demand_y, lookback)
# Split the data into training and test sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

# Evaluate the model
loss, mae = demand_model.evaluate(X_test, y_test)
print(f"Mean Absolute Error on Test Set: {mae}")

# Make predictions
predictions = demand_model.predict(X_test)
print(X_test)

# Simulate data like the original dataset
np.random.seed(42)

# Parameters for the simulation
num_samples = 1000
lookback = 24  # Number of previous hours to look at
time_v = np.arange(num_samples)

# Simulating the energy data with sine waves + noise (you can adjust these)
actual_demand = 15000 + 1000 * np.sin(0.1 * time_v) + np.random.normal(0, 500, num_samples)
HOEP_price = 50 + 5 * np.sin(0.05 * time_v) + np.random.normal(0, 2, num_samples)
biofuel_supply = 12 + np.random.normal(0, 0.5, num_samples)
gas_supply = 2000 + 500 * np.sin(0.1 * time_v) + np.random.normal(0, 100, num_samples)
hydro_supply = 4000 + 500 * np.cos(0.1 * time_v) + np.random.normal(0, 200, num_samples)
nuclear_supply = 9000 + np.random.normal(0, 100, num_samples)
solar_supply = 0 + 1000 * np.sin(0.1 * time_v) + np.random.normal(0, 50, num_samples)
wind_supply = 3000 + 300 * np.cos(0.05 * time_v) + np.random.normal(0, 100, num_samples)
total_supply = 1700 + 2000 * np.cos(0.05 * time_v) + np.random.normal(0, 100, num_samples)

# Create a DataFrame to hold the data
data = pd.DataFrame({
    'actual_demand': actual_demand,
    'HOEP_price': HOEP_price,
    'biofuel_supply': biofuel_supply,
    'gas_supply': gas_supply,
    'hydro_supply': hydro_supply,
    'nuclear_supply': nuclear_supply,
    'solar_supply': solar_supply,
    'wind_supply': wind_supply,
    'total_supply' : total_supply
})


# Normalize features using MinMaxScaler
scaler = MinMaxScaler()
scaled_data = scaler.fit_transform(data)

demand_X = scaled_data[:,-8:]
demand_y = scaled_data[:,:1]

# Create sequences for LSTM model
X, y = create_sequences(demand_X, demand_y, lookback)

# Split the data into training and test sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

# Evaluate the model on the simulated test data
test_loss, test_mae = demand_model.evaluate(X_test, y_test)

print(f"Test Loss: {test_loss}")
print(f"Test MAE: {test_mae}")

# Make predictions with the model on the simulated test data
predictions = demand_model.predict(X_test)

plt.plot(y_test[:100], label='Actual Demand')
plt.plot(predictions[:100], label='Predicted Demand')
plt.legend()
plt.title('Actual vs Predicted Energy Demand')
plt.show()

# Load the model for inference in real-time
supply_model = tf.keras.models.load_model('models/lstm_cnn_supply_predictor.keras')

# Load the dataset
data = dataframe

# Normalize features using MinMaxScaler
scaler = MinMaxScaler()
scaled_data = scaler.fit_transform(data)

supply_X = scaled_data[:,:2]
supply_y = scaled_data[:,-1:]

lookback = 24  # Look at the last 24 hours (1 day)
X, y = create_sequences(supply_X, supply_y, lookback)

# Split the data into training and test sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

# Evaluate the model
loss, mae = supply_model.evaluate(X_test, y_test)
print(f"Mean Absolute Error on Test Set: {mae}")

# Make predictions
predictions = supply_model.predict(X_test)
print(predictions)
# Simulate data like the original dataset
np.random.seed(42)

# Parameters for the simulation
num_samples = 1000
lookback = 24  # Number of previous hours to look at
time_v = np.arange(num_samples)

# Simulating the energy data with sine waves + noise (you can adjust these)
actual_demand = 15000 + 1000 * np.sin(0.1 * time_v) + np.random.normal(0, 500, num_samples)
HOEP_price = 50 + 5 * np.sin(0.05 * time_v) + np.random.normal(0, 2, num_samples)
biofuel_supply = 12 + np.random.normal(0, 0.5, num_samples)
gas_supply = 2000 + 500 * np.sin(0.1 * time_v) + np.random.normal(0, 100, num_samples)
hydro_supply = 4000 + 500 * np.cos(0.1 * time_v) + np.random.normal(0, 200, num_samples)
nuclear_supply = 9000 + np.random.normal(0, 100, num_samples)
solar_supply = 0 + 1000 * np.sin(0.1 * time_v) + np.random.normal(0, 50, num_samples)
wind_supply = 3000 + 300 * np.cos(0.05 * time_v) + np.random.normal(0, 100, num_samples)
total_supply = 1700 + 2000 * np.cos(0.05 * time_v) + np.random.normal(0, 100, num_samples)

# Create a DataFrame to hold the data
data = pd.DataFrame({
    'actual_demand': actual_demand,
    'HOEP_price': HOEP_price,
    'biofuel_supply': biofuel_supply,
    'gas_supply': gas_supply,
    'hydro_supply': hydro_supply,
    'nuclear_supply': nuclear_supply,
    'solar_supply': solar_supply,
    'wind_supply': wind_supply,
    'total_supply' : total_supply
})

# Normalize features using MinMaxScaler
scaler = MinMaxScaler()
scaled_data = scaler.fit_transform(data)

supply_X = scaled_data[:,:2]
supply_y = scaled_data[:,-1:]

# reate sequences for LSTM model
X, y = create_sequences(supply_X, supply_y, lookback)

# Split the data into training and test sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

# Evaluate the model on the simulated test data
test_loss, test_mae = supply_model.evaluate(X_test, y_test)

print(f"Test Loss: {test_loss}")
print(f"Test MAE: {test_mae}")

# Make predictions with the model on the simulated test data
predictions = supply_model.predict(X_test)

plt.plot(y_test[:100], label='Actual Supply')
plt.plot(predictions[:100], label='Predicted Supply')
plt.legend()
plt.title('Actual vs Predicted Energy Supply')
plt.show()