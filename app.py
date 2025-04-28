

from flask import Flask, request, jsonify
import joblib
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import json
import os
from flask import Flask
from flask_cors import CORS
from datapreprocess import prepare_dataset, train_model, save_model
from datetime import datetime, timedelta
from collections import Counter


MODEL_FILE = 'meal_recommendation_model.pkl'
ENCODER_FILE = 'meal_label_encoder.pkl'
DATASET_FILE = 'indian_meal_dataset.csv'
USER_HISTORY_FILE = 'user_meal_history.json'

app = Flask(__name__)
CORS(app)

# Load dataset
try:
    df = pd.read_csv(DATASET_FILE)
    print(f"Loaded dataset with {len(df)} rows")
except:
    df = None

# Load model + encoder
def load_model():
    global remodel, label_encoder
    remodel = joblib.load(MODEL_FILE)
    label_encoder = joblib.load(ENCODER_FILE)
    print("Model and encoder reloaded.")

try:
    load_model()
except:
    remodel = None
    label_encoder = None

# Utils
def get_user_history(user_id):
    if not os.path.exists(USER_HISTORY_FILE):
        return {}
    with open(USER_HISTORY_FILE, 'r') as f:
        return json.load(f).get(user_id, {})

def update_user_history(user_id, date, meal_time, meal):
    try:
        with open(USER_HISTORY_FILE, 'r') as f:
            all_history = json.load(f)
    except:
        all_history = {}

    all_history.setdefault(user_id, {}).setdefault(date, {})[meal_time] = meal

    with open(USER_HISTORY_FILE, 'w') as f:
        json.dump(all_history, f)

def get_meal_details(meal):
    match = df[df['meal_description'] == meal]
    return match.iloc[0].to_dict() if not match.empty else None

# Recommendation Logic
def recommend_meals(goal, diet_type, date, user_id):
    filtered_df = df[df['diet_type'] == diet_type]
    user_history = get_user_history(user_id)
    past_meals = set()
    for meals in user_history.values():
        past_meals.update(meals.values())

    recommendations = {}
    random.seed(hash(user_id + date + goal))

    for meal_time in ['breakfast', 'lunch', 'dinner']:
        input_df = pd.DataFrame([{ 'meal_time': meal_time, 'diet_type': diet_type, 'goal': goal }])
        if remodel:
            probs = remodel.predict_proba(input_df)[0]
            meals, weights = [], []
            for idx, prob in enumerate(probs):
                meal = label_encoder.inverse_transform([idx])[0]
                if meal in filtered_df['meal_description'].values:
                    meals.append(meal)
                    weights.append(prob)

            weights = np.array(weights) / sum(weights)
            meal_choices = random.choices(meals, weights=weights, k=min(5, len(meals)))
            unique_selected = []
            seen = set()
            for m in meal_choices:
                if m not in seen:
                    seen.add(m)
                    unique_selected.append(m)
                if len(unique_selected) == 2:
                    break
            recommendations[meal_time] = unique_selected or meal_choices[:2]

        else:
            recommendations[meal_time] = ["Model not loaded"]

    return recommendations

# Endpoints
@app.route('/recommend', methods=['POST'])
def recommend():
    data = request.get_json()
    goal = data['goal']
    diet_type = data['diet_type']
    user_id = data.get('user_id', 'default_user')
    date = data.get('date', datetime.today().strftime('%Y-%m-%d'))

    result = recommend_meals(goal, diet_type, date, user_id)
    details = {
        mt: [get_meal_details(m) for m in meals] for mt, meals in result.items()
    }
    for mt, meals in result.items():
        for m in meals:
            update_user_history(user_id, date, mt, m)

    return jsonify({ 'status': 'success', 'recommendations': result, 'meal_details': details })

@app.route('/weekly_stats')
def weekly_stats():
    user_id = request.args.get('user_id', 'default_user')
    history = get_user_history(user_id)
    meal_count = {k: {} for k in ['breakfast', 'lunch', 'dinner']}
    avg_cals = {k: 0 for k in meal_count}
    total = {k: 0 for k in meal_count}

    for day in history.values():
        for mt, m in day.items():
            if m:
                meal_count[mt][m] = meal_count[mt].get(m, 0) + 1
                det = get_meal_details(m)
                if det:
                    avg_cals[mt] += det['total_calories']
                    total[mt] += 1

    common = {
        k: max(v.items(), key=lambda x: x[1])[0] if v else "No data"
        for k, v in meal_count.items()
    }

    avg_data = [
        { 'meal_type': k, 'average': round(avg_cals[k]/total[k], 2) if total[k] else 0 }
        for k in ['breakfast', 'lunch', 'dinner']
    ]

    return jsonify({ 'calories': avg_data, 'common_meals': common })

@app.route('/retrain_model', methods=['POST'])
def retrain():
    try:
        print("[RETRAIN] Preparing dataset...")
        prepare_dataset(DATASET_FILE, DATASET_FILE)
        print("[RETRAIN] Training model...")
        remodel, encoder = train_model(DATASET_FILE)
        save_model(remodel, encoder)
        load_model()
        return jsonify({ 'status': 'success', 'message': 'Model retrained and reloaded.' })
    except Exception as e:
        return jsonify({ 'status': 'error', 'message': str(e) })

@app.route('/history/<user_id>')
def history(user_id):
    return jsonify({ 'status': 'success', 'history': get_user_history(user_id) })

# Add this route to app.py
import random

def get_user_meal_preference(user_id):
    # You can retrieve the user's preference from the database or any other source
    # For now, let's assume the preference is stored in the user history JSON file
    user_history = get_user_history(user_id)
    
    # This is just a simple assumption: if there's history for the user, use their most frequent meal type
    # If no history, default to "veg" (or any other default logic)
    meal_count = {'veg': 0, 'non-veg': 0}
    
    for day in user_history.values():
        for meal_time, meal in day.items():
            if meal:
                if 'veg' in meal.lower():
                    meal_count['veg'] += 1
                else:
                    meal_count['non-veg'] += 1
    
    # Return the preference based on most frequent meal type
    if meal_count['veg'] > meal_count['non-veg']:
        return 'veg'
    elif meal_count['veg'] < meal_count['non-veg']:
        return 'non-veg'
    else:
        return 'veg'  # Default to 'veg' if there's a tie or no preference
def get_user_preferences(user_id):
    try:
        with open('user_profiles.json') as f:
            users = json.load(f)
        return users.get(user_id, {'goal': 'weight_loss', 'diet_type': get_user_meal_preference(user_id)})
    except Exception as e:
        print(f"Error loading user preferences: {e}")
        return {'goal': 'weight_loss', 'diet_type': get_user_meal_preference(user_id)}

# Read meal dataset
meals_df = pd.read_csv('indian_meal_dataset.csv')
@app.route('/predict_week', methods=['GET'])
def predict_week():
    try:
        # Get user input from query params
        user_id = request.args.get('user_id', 'default_user')
        start_date_str = request.args.get('start_date', datetime.today().strftime('%Y-%m-%d'))
        goal = request.args.get('goal', 'weight_loss')  # Default to 'weight_loss' if not provided
        diet_type = request.args.get('diet_type', 'veg')  # Default to 'veg' if not provided
        
        # Debugging: print goal and diet_type to verify
        print("Goal:", goal)
        print("Diet Type:", diet_type)

        # Validate required parameters
        if not start_date_str or not diet_type or not goal:
            return jsonify({"error": "Missing required parameters"}), 400

        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        week_predictions = []

        # Filter meals based on diet_type and goal
        filtered_df = meals_df[(meals_df['diet_type'] == diet_type) & (meals_df['goal'] == goal)]
        print(filtered_df)

        # Generate meal predictions for each day of the week
        for i in range(7):
            date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
            breakfast = random.choice(filtered_df[filtered_df['meal_time'] == 'breakfast']['meal_description'].tolist())
            lunch = random.choice(filtered_df[filtered_df['meal_time'] == 'lunch']['meal_description'].tolist())
            dinner = random.choice(filtered_df[filtered_df['meal_time'] == 'dinner']['meal_description'].tolist())

            week_predictions.append({
                "date": date,
                "breakfast": breakfast,
                "lunch": lunch,
                "dinner": dinner
            })

        return jsonify(week_predictions)

    except Exception as e:
        print("🔥 Error in /predict_week:", e)
        return jsonify({"error": str(e)}), 500
    
# --------------------------------------------------------------------------------------------------------------------------------------
from clarifai.client.model import Model


# Clarifai Config
CLARIFAI_PAT = "2f68ef162b674d4e9b2965a3ad0c9fa0"  # <-- use your real PAT here
MODEL_URL = "https://clarifai.com/clarifai/main/models/food-item-recognition"

# Load model once
model = Model(url=MODEL_URL, pat=CLARIFAI_PAT)

nutrition = pd.read_csv("daily_food_nutrition_dataset.csv")

@app.route('/api/estimate-calories', methods=['POST'])
def estimate_calories():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400

    image = request.files['image']
    image_bytes = image.read()

    try:
        # Predict using base64 image
        prediction = model.predict_by_bytes(image_bytes)
        # Extract top food item
        concepts = prediction.outputs[0].data.concepts
        top_concept = concepts[0].name
        top_value = concepts[0].value

        # print(top_concept)
        matched_row = nutrition[nutrition['Food_Item'].str.lower() == top_concept.lower()]
        matched_row = matched_row.head(1)
        # print(matched_row)

        # Dummy calorie estimation based on food item
        if not matched_row.empty:
            nutrition_info = matched_row.iloc[0].to_dict()
        else:
            nutrition_info = {
                'Calories (kcal)': 250,
                'Protein (g)': 0,
                'Carbohydrates (g)': 0,
                'Fat (g)': 0,
                'Fiber (g)': 0,
                'Sugars (g)': 0,
                'Sodium (mg)': 0,
                'Cholesterol (mg)': 0,
                'Meal_Type': 'Unknown',
                'Water_Intake (ml)': 0
        }
        # print(nutrition_info)

        # estimated_calories = food_calories.get(top_concept.lower(), 250)  

        return jsonify({
            'food': top_concept,
            'confidence': top_value,
            'nutrition': nutrition_info
        })

    except Exception as e:
        print("Clarifai API error:", e)
        return jsonify({'error': 'Failed to estimate calories'}), 500
    

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

