import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os

# Define scope
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Load credentials (update the path to your service account JSON file if needed)
try:
    creds = Credentials.from_service_account_file(
        r"D:\Linkedin\selenium\service_account.json", scopes=scope
    )
except FileNotFoundError:
    print("Error: Service account JSON file not found. Please check the file path.")
    exit()

# Authorize
client = gspread.authorize(creds)

# Open Google Sheet
try:
    sheet = client.open("Jobs_listings").sheet1
except gspread.exceptions.SpreadsheetNotFound:
    print("Error: Google Sheet 'Jobs_listings' not found. Please verify the sheet name.")
    exit()

# Get all data from the sheet
data = sheet.get_all_values()

# Convert to pandas DataFrame
if not data or len(data) < 2:
    print("Error: The Google Sheet is empty or has no data rows.")
    exit()

df = pd.DataFrame(data[1:], columns=data[0])  # Assuming first row is headers

# Print column names for debugging
print("Column Names in the Sheet:", df.columns.tolist())

# Normalize column names (handle case sensitivity and extra spaces)
df.columns = df.columns.str.strip().str.lower()

# Define expected columns (lowercase for matching)
expected_columns = {
    'job postings': 'job_postings',
    'company': 'company',
    'place': 'place',
    'status': 'status',
    'posted on': 'posted_on',
    'url link': 'url_link'
}

# Map actual columns to expected ones
column_mapping = {}
for actual_col in df.columns:
    for expected_col in expected_columns:
        if actual_col.lower() == expected_col.lower():
            column_mapping[actual_col] = expected_columns[expected_col]

# Rename columns to standardized names
df.rename(columns=column_mapping, inplace=True)

# Check for missing critical columns
missing_cols = [col for col in expected_columns.values() if col not in df.columns]
if missing_cols:
    print(f"Error: Missing critical columns: {missing_cols}. Please check the sheet headers.")
    exit()

# Function to parse relative dates like "1 month ago"
def parse_relative_date(date_str, reference_date=None):
    if reference_date is None:
        reference_date = datetime(2025, 9, 5)  # Current date as per system
    try:
        if 'ago' in date_str.lower():
            if 'month' in date_str.lower():
                months = int(date_str.split()[0])
                return reference_date - timedelta(days=months * 30)
            elif 'week' in date_str.lower():
                weeks = int(date_str.split()[0])
                return reference_date - timedelta(weeks=weeks)
            elif 'day' in date_str.lower():
                days = int(date_str.split()[0])
                return reference_date - timedelta(days=days)
        return pd.to_datetime(date_str)
    except (ValueError, TypeError):
        return pd.NaT

# Clean and preprocess data
df['posted_on'] = df['posted_on'].apply(parse_relative_date)
df = df.dropna(subset=['posted_on'])  # Drop rows with invalid dates
df['job_postings'] = df['job_postings'].str.strip()  # Clean job titles
df['company'] = df['company'].str.strip()  # Clean company names
df['place'] = df['place'].str.strip()  # Clean place names

# Extract city from place (assuming format like "Bengaluru, Karnataka, India (Hybrid)")
df['city'] = df['place'].str.split(',').str[0].str.strip()

# Compute insights
total_postings = len(df)
unique_companies = df['company'].nunique()
unique_places = df['place'].nunique()
status_counts = df['status'].value_counts()
top_companies = df['company'].value_counts().head(5)
top_places = df['place'].value_counts().head(5)
city_counts = df['city'].value_counts().head(5)

# Group by month for time-based trends
df['month'] = df['posted_on'].dt.to_period('M')
postings_by_month = df['month'].value_counts().sort_index()

# Create output directory for plots
output_dir = "job_postings_plots"
os.makedirs(output_dir, exist_ok=True)

# Visualization 1: Status Distribution (Pie Chart)
plt.figure(figsize=(8, 6))
plt.pie(status_counts, labels=status_counts.index, autopct='%1.1f%%', colors=['#FF9999', '#66B2FF', '#99FF99', '#FFCC99'])
plt.title("Job Status Distribution")
plt.savefig(os.path.join(output_dir, "status_distribution.png"))
plt.close()

# Visualization 2: Top 5 Companies (Bar Plot)
plt.figure(figsize=(10, 6))
top_companies.plot(kind='bar', color='#636EFA')
plt.title("Top 5 Companies by Job Postings")
plt.xlabel("Company")
plt.ylabel("Number of Postings")
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "top_companies.png"))
plt.close()

# Visualization 3: Top 5 Locations (Bar Plot)
plt.figure(figsize=(10, 6))
top_places.plot(kind='bar', color='#EF553B')
plt.title("Top 5 Locations by Job Postings")
plt.xlabel("Location")
plt.ylabel("Number of Postings")
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "top_locations.png"))
plt.close()

# Visualization 4: Top 5 Cities (Bar Plot)
plt.figure(figsize=(10, 6))
city_counts.plot(kind='bar', color='#AB63FA')
plt.title("Top 5 Cities by Job Postings")
plt.xlabel("City")
plt.ylabel("Number of Postings")
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "top_cities.png"))
plt.close()

# Visualization 5: Postings Over Time (Line Plot)
plt.figure(figsize=(10, 6))
postings_by_month.plot(kind='line', marker='o', color='#00CC96')
plt.title("Monthly Job Postings Trend")
plt.xlabel("Month")
plt.ylabel("Number of Postings")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "monthly_trend.png"))
plt.close()

# Print Key Metrics
print("\n=== Key Metrics ===")
print(f"Total Job Postings: {total_postings}")
print(f"Unique Companies: {unique_companies}")
print(f"Unique Locations: {unique_places}")
print("\nStatus Distribution:")
print(status_counts)
print("\nTop 5 Companies:")
print(top_companies)
print("\nTop 5 Locations:")
print(top_places)
print("\nTop 5 Cities:")
print(city_counts)

# Insights for Client Enrichment
print("\n=== Insights for Client Enrichment and Engagement ===")
sample_row = df.iloc[0] if not df.empty else {}
print(f"""
Based on the job postings data, here are actionable insights for client enrichment and engagement activities:

1. **Location-Based Targeting**: 
   - Locations like "{sample_row.get('place', 'N/A')}" appear in the data. Focus client outreach in high-activity cities like {sample_row.get('city', 'N/A')}. Host webinars or job fairs in these regions to engage local talent and clients.

2. **Company Engagement Opportunities**: 
   - Companies like "{sample_row.get('company', 'N/A')}" are actively posting. Reach out to these companies for partnerships, sponsored content, or recruitment services tailored to their hiring needs.

3. **Job Role Insights**: 
   - Roles like "{sample_row.get('job_postings', 'N/A')}" appear. Analyze job titles for trends (e.g., tech roles like ASIC Design Verification). Offer specialized training or certifications to clients targeting these roles.

4. **Status-Based Follow-Ups**: 
   - Postings with statuses like "{sample_row.get('status', 'N/A')}" indicate active hiring. Create automated alerts for clients when new postings with "Actively reviewing applicants" appear, ensuring timely applications.

5. **Temporal Trends**: 
   - Group postings by 'posted on' to identify peak hiring months. For example, if recent postings cluster in {sample_row.get('month', 'N/A').strftime('%B %Y') if not df.empty else 'N/A'}, schedule engagement campaigns (e.g., email blasts, LinkedIn ads) during these periods.

6. **URL Link Analysis**: 
   - Most URLs point to LinkedIn (e.g., "{sample_row.get('url_link', 'N/A')}"). Analyze domain frequency to prioritize job board partnerships or advertising on platforms like LinkedIn for better client visibility.

7. **Personalized Client Reports**: 
   - Use pandas to filter data for specific clients (e.g., by company or city). Generate custom reports showing relevant job opportunities, helping clients stay competitive.

These insights can drive engagement through targeted campaigns, personalized job alerts, and strategic partnerships with high-activity companies or regions.
""")

# Instructions
print("\n=== Instructions ===")
print("1. Plots have been saved in the 'job_postings_plots' directory.")
print("2. Check the console output above for key metrics and insights.")
print("3. Ensure the following packages are installed: `pip install gspread oauth2client pandas matplotlib`")
print("4. Verify the service account JSON file is at `D:\\Linkedin\\selenium\\service_account.json`.")
print("5. If errors persist, check the Google Sheet headers and data format.")