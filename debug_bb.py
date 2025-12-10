import pandas_ta as ta
import pandas as pd

df = pd.DataFrame({
    'high': [10, 12, 11, 13, 15] * 20,
    'low': [8, 9, 8, 10, 12] * 20,
    'close': [9, 11, 10, 12, 14] * 20
})

bb = ta.bbands(df['close'], length=20, std=2)
print("Columns:", bb.columns)
