import pandas_ta as ta
import pandas as pd

# Create dummy data
df = pd.DataFrame({
    'high': [10, 12, 11, 13, 15] * 20,
    'low': [8, 9, 8, 10, 12] * 20,
    'close': [9, 11, 10, 12, 14] * 20
})

st = ta.supertrend(df['high'], df['low'], df['close'], length=10, multiplier=3)
print("Columns:", st.columns)
print("Content:", st.head())
