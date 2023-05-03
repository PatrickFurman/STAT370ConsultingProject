import pandas as pd
import numpy as np
from tsmoothie.smoother import LowessSmoother
# Slot utilization data
slot_util = pd.read_csv("./Slot Utilization.csv")
slot_util['DATE_EXTRACT'] = pd.to_datetime(slot_util['DATE_EXTRACT'])

# Remove rows with no capacity and where branches are equal to X1, X6, or X7 and not stock yards
slot_util = slot_util[slot_util['CAPACITY'].notna()]
slot_util = slot_util[~slot_util['BRNCH_CD'].isin(['X1', 'X6', 'X7'])]
slot_util = slot_util[~slot_util['FULL_MARKET_NAME'].str.contains('STOCK YARDS')]
slot_util_main = slot_util[slot_util['CAPACITY'] != 0]
# Automated method for outlier detection for comparison with below
slot_util_ts = slot_util.groupby(['DATE_EXTRACT','BRNCH_CD']).agg(np.mean).reset_index().drop(
    ['WAREHOUSE_LOCN', 'SUM(PALLET_USED)', 'SUM(PALLET_POSITIONS)'], axis=1)
slot_util_ts['OUTLIER'] = 'NA'
for b in np.unique(slot_util['BRNCH_CD']):
        sub = slot_util_ts[slot_util_ts['BRNCH_CD'] == b].groupby('DATE_EXTRACT').agg(np.mean).reset_index()
        smoother = LowessSmoother(smooth_fraction=.5, iterations=1, batch_size=None)
        sub.set_index('DATE_EXTRACT', inplace=True)
        smoother.smooth(sub)
        smoothed = smoother.smooth_data
        lower, upper = smoother.get_intervals('confidence_interval', confidence=0.1)
        upper = upper[0]
        lower = lower[0]
        for i, row in enumerate(sub.itertuples()):
            if (row[1] > upper[i]) | (row[1] < lower[i]):
                slot_util_ts[(slot_util_ts['BRNCH_CD'] == b) & (slot_util_ts['DATE_EXTRACT'] == row[0])].loc[0,'OUTLIER'] = "Yes"
slot_util_ts

slot_util_ts['OUTLIER'].value_counts()