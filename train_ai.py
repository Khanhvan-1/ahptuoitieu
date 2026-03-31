import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib

data = pd.read_csv("irrigation_dataset.csv")

X = data[[
"soil",
"rain",
"eto",
"temp",
"humidity",
"radiation"
]]

y = data["irrigation"]

model = RandomForestClassifier(n_estimators=200)

model.fit(X,y)

joblib.dump(model,"irrigation_ai.pkl")

print("AI trained")