import pandas as pd
import matplotlib.pyplot as plt

# Load the Excel data
# Replace 'your_data.xlsx' with your actual filename
df = pd.read_excel('./basins/gee-data.xlsx')

# Clean column names just in case (handles spaces and casing)
df.columns = df.columns.str.strip().str.lower()

# Ensure 'date' column is in datetime format
df['date'] = pd.to_datetime(df['date'])

# Extract month from date
df['month'] = df['date'].dt.month

# Group by month and calculate mean NDVI
ndvi_col = 'ndvi_basin_mean' if 'ndvi_basin_mean' in df.columns else 'NDVI_basin_mean'
monthly_mean_ndvi = df.groupby('month')[ndvi_col].mean()

# Define your seasons using month numbers (1 = Jan, 12 = Dec)
# ADJUST THESE LISTS TO MATCH YOUR REGION'S CLIMATE:
wet_months = [10, 11, 12, 1, 2, 3, 4]
# Dry months will automatically be whatever is left over

# Assign colors based on the month index
bar_colors = []
for month in monthly_mean_ndvi.index:
    if month in wet_months:
        bar_colors.append('#1f77b4')  # Deep blue for wet season
    else:
        bar_colors.append('#ee7402')  # Warm orange/brown for dry season

# Create month labels
months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

# Plot bar chart
plt.figure(figsize=(8,4))
monthly_mean_ndvi.plot(kind='bar', color=bar_colors, width=0.8)
plt.xticks(range(0,12), months)

# Add a custom legend so people know what the colors mean
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor='#1f77b4', label='Wet Season'),
    Patch(facecolor='#ee7402', label='Dry Season')
]
plt.legend(handles=legend_elements, loc='upper right')


plt.xlabel('Month')
plt.ylabel('Mean NDVI')
plt.title('Seasonal Cycle — Mean NDVI by Month')
plt.grid(axis='y', linestyle='--', alpha=0.2)
plt.tight_layout()
plt.show()