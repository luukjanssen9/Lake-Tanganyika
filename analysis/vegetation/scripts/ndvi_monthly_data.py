import pandas as pd

# Load the level-12 NDVI file
ndvi = pd.read_excel('basins/ndvi.xlsx')
ndvi['date'] = pd.to_datetime(ndvi['date'])

# Extract year and month
ndvi['year'] = ndvi['date'].dt.year
ndvi['month'] = ndvi['date'].dt.month

# Aggregate: 1 mean NDVI per river per month
ndvi_monthly = (ndvi.groupby(['river', 'year', 'month'], as_index=False)['NDVI_mean']
                    .mean()
                    .rename(columns={'river': 'river', 'NDVI_mean': 'ndvi_basin_mean'}))

print(ndvi_monthly.head())
print(f"Rows: {len(ndvi_monthly)}  (≈10 rivers × 287 months)")

# Load the existing master dataset
master_path = 'data/outputs/master_dataset_monthly.csv'
master = pd.read_csv(master_path)

# Safety check: don't double-add the column if you run this twice
if 'ndvi_basin_mean' in master.columns:
    master = master.drop(columns=['ndvi_basin_mean'])

# Merge on river + year + month (preserves all original rows)
master = master.merge(ndvi_monthly, on=['river', 'year', 'month'], how='left')

# Overwrite the existing file
master.to_csv(master_path, index=False)

# Confirm
print(f"Rows after merge: {len(master)}  (should match original: 4664)")
print(f"NDVI values filled: {master['ndvi_basin_mean'].notna().sum()}")
print(f"NDVI missing: {master['ndvi_basin_mean'].isna().sum()}  (pre-2000, expected)")