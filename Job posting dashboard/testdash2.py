import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output
from dash.dash_table import DataTable
from datetime import datetime, timedelta
import os

# Define API scopes
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Load credentials
try:
    creds = Credentials.from_service_account_file(
        r"D:\Linkedin\selenium\service_account.json", scopes=scope
    )
except FileNotFoundError:
    print("❌ Error: Service account JSON file not found. Please check the file path.")
    exit()

# Authorize and open Google Sheet
client = gspread.authorize(creds)
try:
    sheet = client.open("Jobs_listings").sheet1
except gspread.exceptions.SpreadsheetNotFound:
    print("❌ Error: Google Sheet 'Jobs_listings' not found. Please verify the sheet name.")
    exit()

# Fetch sheet data
data = sheet.get_all_values()
if not data or len(data) < 2:
    print("❌ Error: The Google Sheet is empty or has no data rows.")
    exit()

# Convert to DataFrame
df = pd.DataFrame(data[1:], columns=data[0])
df.columns = df.columns.str.strip().str.lower()

# Standardize column names
expected_columns = {
    'job postings': 'job_postings',
    'company': 'company',
    'place': 'place',
    'status': 'status',
    'posted on': 'posted_on',
    'url link': 'url_link'
}
df.rename(columns={col: expected_columns.get(col, col) for col in df.columns}, inplace=True)

# Check for missing columns
missing_cols = [col for col in expected_columns.values() if col not in df.columns]
if missing_cols:
    print(f"❌ Missing critical columns: {missing_cols}. Please check sheet headers.")
    exit()

# Function to parse dates like "2 weeks ago"
def parse_relative_date(date_str, reference_date=None):
    if reference_date is None:
        reference_date = datetime.now()
    try:
        s = date_str.lower()
        if "ago" in s:
            if "month" in s:
                months = int(s.split()[0])
                return reference_date - timedelta(days=months * 30)
            elif "week" in s:
                weeks = int(s.split()[0])
                return reference_date - timedelta(weeks=weeks)
            elif "day" in s:
                days = int(s.split()[0])
                return reference_date - timedelta(days=days)
        return pd.to_datetime(date_str, errors="coerce")
    except Exception:
        return pd.NaT

# Clean data
df['posted_on'] = df['posted_on'].apply(parse_relative_date)
df = df.dropna(subset=['posted_on'])
df['job_postings'] = df['job_postings'].str.strip()
df['company'] = df['company'].str.strip()
df['place'] = df['place'].str.strip()
df['city'] = df['place'].str.split(',').str[0].str.strip()
df = df.sort_values(by='posted_on', ascending=False)

# Initialize Dash
app = Dash(__name__)

# Initial plots
def make_figures(filtered_df):
    status_counts = filtered_df['status'].value_counts().reset_index()
    status_counts.columns = ['status', 'count']

    top_companies = filtered_df['company'].value_counts().head(5).reset_index()
    top_companies.columns = ['company', 'count']

    top_places = filtered_df['place'].value_counts().head(5).reset_index()
    top_places.columns = ['place', 'count']

    city_counts = filtered_df['city'].value_counts().head(5).reset_index()
    city_counts.columns = ['city', 'count']

    postings_by_month = (
        filtered_df.groupby(filtered_df['posted_on'].dt.to_period('M'))
        .size()
        .reset_index(name="count")
    )
    postings_by_month['posted_on'] = postings_by_month['posted_on'].astype(str)

    return (
        px.pie(status_counts, values="count", names="status", title="Job Status Distribution"),
        px.bar(top_companies, x="company", y="count", title="Top 5 Companies"),
        px.bar(top_places, x="place", y="count", title="Top 5 Locations"),
        px.bar(city_counts, x="city", y="count", title="Top 5 Cities"),
        px.line(postings_by_month, x="posted_on", y="count", title="Monthly Job Postings Trend")
    )

# Dashboard layout
app.layout = html.Div([
    html.H1("Job Postings Dashboard"),
    html.Div([
        dcc.Input(id="keyword-input", type="text", placeholder="Enter keyword", style={"width": "50%"}),
        html.Button("Apply Filter", id="filter-button", n_clicks=0),
    ], style={"margin": "10px"}),

    html.Div(id="metrics-container", style={"display": "flex", "gap": "20px", "margin": "20px 0"}),

    dcc.Graph(id="status-graph"),
    dcc.Graph(id="companies-graph"),
    dcc.Graph(id="places-graph"),
    dcc.Graph(id="cities-graph"),
    dcc.Graph(id="time-graph"),

    html.H2("Job Postings Data"),
    DataTable(
        id="data-table",
        columns=[{"name": col, "id": col} for col in ["job_postings", "company", "place", "status", "posted_on", "url_link"]],
        data=df.to_dict("records"),
        page_size=10,
        style_table={"overflowX": "auto"},
        style_cell={"textAlign": "left"},
    ),

    html.H2("Insights"),
    dcc.Markdown(id="insights-text")
])

# Callback for filtering
@app.callback(
    [
        Output("metrics-container", "children"),
        Output("status-graph", "figure"),
        Output("companies-graph", "figure"),
        Output("places-graph", "figure"),
        Output("cities-graph", "figure"),
        Output("time-graph", "figure"),
        Output("data-table", "data"),
        Output("insights-text", "children")
    ],
    [Input("filter-button", "n_clicks")],
    [Input("keyword-input", "value")]
)
def update_dashboard(n_clicks, keyword):
    filtered_df = df
    if keyword:
        filtered_df = df[df["job_postings"].str.contains(keyword, case=False, na=False)]

    fig_status, fig_companies, fig_places, fig_cities, fig_time = make_figures(filtered_df)

    metrics = [
        html.Div(f"Total Postings: {len(filtered_df)}"),
        html.Div(f"Unique Companies: {filtered_df['company'].nunique()}"),
        html.Div(f"Unique Locations: {filtered_df['place'].nunique()}"),
    ]

    sample_row = filtered_df.iloc[0] if not filtered_df.empty else {}
    insights = f"""
    - **Location**: {sample_row.get('place', 'N/A')}
    - **Company**: {sample_row.get('company', 'N/A')}
    - **Role**: {sample_row.get('job_postings', 'N/A')}
    - **Status**: {sample_row.get('status', 'N/A')}
    - **Posted On**: {sample_row.get('posted_on').strftime('%B %Y') if pd.notna(sample_row.get('posted_on', None)) else 'N/A'}
    """

    return metrics, fig_status, fig_companies, fig_places, fig_cities, fig_time, filtered_df.to_dict("records"), insights

if __name__ == "__main__":
    app.run(debug=True)
