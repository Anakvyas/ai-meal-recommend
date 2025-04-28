# datapreprocess.py - Clean Dataset & Train Model

import pandas as pd
import numpy as np
import joblib
import os
from sklearn.preprocessing import OneHotEncoder, LabelEncoder
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

def prepare_dataset(input_path, output_path):
    print(f"[DATA] Loading data from {input_path}")
    df = pd.read_csv(input_path, quoting=1)
    df.columns = df.columns.str.strip()

    initial = len(df)
    df.drop_duplicates(inplace=True)
    print(f"[DATA] Removed {initial - len(df)} duplicates")

    req_cols = ['meal_time', 'diet_type', 'goal', 'meal_description', 'total_calories']
    for col in req_cols:
        if col not in df.columns:
            raise ValueError(f"Missing column: {col}")

    if df.isnull().sum().sum() > 0:
        print("[DATA] Dropping missing values")
        df.dropna(inplace=True)

    df = df[df['meal_time'].isin(['breakfast', 'lunch', 'dinner'])]
    df = df[df['diet_type'].isin(['veg', 'non_veg'])]
    df = df[df['goal'].isin(['weight_loss', 'muscle_gain', 'endurance'])]

    df.to_csv(output_path, index=False)
    print(f"[DATA] Saved cleaned data to {output_path}")
    return df

def train_model(dataset_path):
    print("[TRAIN] Training model...")
    df = pd.read_csv(dataset_path)
    label_encoder = LabelEncoder()
    df['meal_label'] = label_encoder.fit_transform(df['meal_description'])

    X = df[['meal_time', 'diet_type', 'goal']]
    y = df['meal_label']

    preprocessor = ColumnTransformer([
        ('onehot', OneHotEncoder(handle_unknown='ignore'), ['meal_time', 'diet_type', 'goal'])
    ])

    model = Pipeline([
        ('preprocessor', preprocessor),
        ('classifier', RandomForestClassifier(n_estimators=100, random_state=42))
    ])

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model.fit(X_train, y_train)
    print(f"[TRAIN] Accuracy: {model.score(X_test, y_test):.4f}")
    return model, label_encoder

def save_model(model, encoder, model_path='meal_recommendation_model.pkl', encoder_path='meal_label_encoder.pkl'):
    joblib.dump(model, model_path)
    joblib.dump(encoder, encoder_path)
    print("[SAVE] Model and encoder saved.")

if __name__ == '__main__':
    raw = 'indian_meal_dataset.csv'
    processed = 'indian_meal_dataset.csv'
    prepare_dataset(raw, processed)
    model, enc = train_model(processed)
    save_model(model, enc)