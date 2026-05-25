import pandas as pd
import matplotlib.pyplot as plt

# Load the Excel data
# Replace 'your_data.xlsx' with your actual filename
df = pd.read_excel('./gee-data.xlsx')

# Ensure 'date' column is in datetime format
df['date'] = pd.to_datetime(df['date'])

# Extract month from date
df['month'] = df['date'].dt.month

# Group by month and calculate mean NDVI
monthly_mean_ndvi = df.groupby('month')['NDVI_basin_mean'].mean()

# Create month labels
months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

# Plot bar chart
plt.figure(figsize=(10,6))
monthly_mean_ndvi.plot(kind='bar', color='skyblue')
plt.xticks(range(0,12), months)
plt.xlabel('Month')
plt.ylabel('Mean NDVI')
plt.title('Seasonal Cycle — Mean NDVI by Month')
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.tight_layout()
plt.show()