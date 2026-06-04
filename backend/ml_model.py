import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
import datetime

class RevenuePredictionModel:
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.is_trained = False

    def generate_dummy_data(self, facility_id: int, base_price: int, total_rooms: int, days=365):
        """
        Generates dummy historical data to train the model.
        Simulates higher demand on weekends and certain seasons.
        """
        data = []
        start_date = datetime.date.today() - datetime.timedelta(days=days)

        for i in range(days):
            current_date = start_date + datetime.timedelta(days=i)
            day_of_week = current_date.weekday() # 0: Mon, 6: Sun
            month = current_date.month

            # Base demand factor
            demand_factor = 0.5

            # Weekend effect
            if day_of_week >= 5:
                demand_factor += 0.3

            # Season effect (e.g. summer and winter holidays)
            if month in [7, 8, 12]:
                demand_factor += 0.2

            # Random noise
            demand_factor += np.random.uniform(-0.1, 0.1)
            demand_factor = min(max(demand_factor, 0.1), 1.0)

            # Simulate historical occupancy and price
            occupancy_rate = demand_factor

            # Historical pricing strategy: increased price slightly on high demand
            historical_price = base_price * (1 + (occupancy_rate - 0.5) * 0.5)

            # Calculate Revenue
            revenue = int(occupancy_rate * total_rooms) * historical_price

            data.append({
                'facility_id': facility_id,
                'day_of_week': day_of_week,
                'month': month,
                'historical_occupancy': occupancy_rate,
                'price': historical_price,
                'revenue': revenue
            })

        return pd.DataFrame(data)

    def train(self, df: pd.DataFrame):
        """
        Trains the model to predict the optimal price multiplier based on day/month/occupancy.
        We want to predict the price that maximizes revenue.
        For simplicity in this prototype, we'll train it to predict the 'historical_price'
        that led to high revenue, but scaled.
        """
        if df.empty:
            return

        # Simple feature set
        X = df[['day_of_week', 'month', 'historical_occupancy']]

        # Target: For prototype, let's predict what the optimal price should be
        # based on historical data where revenue was high.
        # We will use the 'price' as target directly just to show it learns patterns.
        y = df['price']

        self.model.fit(X, y)
        self.is_trained = True

    def predict_optimal_price(self, date_str: str, current_occupancy_rate: float, base_price: int) -> int:
        """
        Predicts optimal price using the trained model.
        """
        if not self.is_trained:
            # Fallback if not trained
            return base_price

        target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()

        X_pred = pd.DataFrame([{
            'day_of_week': target_date.weekday(),
            'month': target_date.month,
            'historical_occupancy': current_occupancy_rate
        }])

        predicted_price = self.model.predict(X_pred)[0]
        return int(predicted_price)

# Singleton instance for the prototype
ml_predictor = RevenuePredictionModel()
