import pandas as pd
import random

# đọc file NASA
df = pd.read_csv(
    "POWER_Point_Daily_20220101_20260101_012d69N_108d06E_LST.csv",
    skiprows=13
)

# đổi tên cột
df = df.rename(columns={
    "T2M": "temp",
    "RH2M": "humidity",
    "PRECTOTCORR": "rain",
    "ALLSKY_SFC_SW_DWN": "radiation"
})

# tạo soil moisture giả lập
df["soil"] = df["rain"].apply(
    lambda x: round(random.uniform(0.15,0.45),3)
)

# tính evapotranspiration (ETo gần đúng)
df["eto"] = df["radiation"] / 5

# tạo nhãn irrigation
def label(row):

    if row["soil"] < 0.20:
        return "high"

    elif row["soil"] < 0.30:
        return "medium"

    elif row["soil"] < 0.40:
        return "low"

    else:
        return "none"

df["irrigation"] = df.apply(label,axis=1)

# chọn cột cần thiết
dataset = df[[
    "soil",
    "rain",
    "eto",
    "temp",
    "humidity",
    "radiation",
    "irrigation"
]]

dataset.to_csv("irrigation_dataset.csv",index=False)

print("Dataset created")