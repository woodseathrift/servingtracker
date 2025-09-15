import pandas as pd

foods = pd.read_csv("2017-2018 FNDDS At A Glance - Foods and Beverages.csv")

print("DEBUG: Columns in foods →")
print(list(foods.columns))
