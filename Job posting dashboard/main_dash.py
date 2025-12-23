import dash
from dash import dcc, html, dash_table, Input, Output, State
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ---------------- Google Sheets Setup ----------------
SHEET_NAME = "Jobs_listings"  # Your sheet name
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

creds = Credentials.from_service_account_file(
    r"D:\Linkedin\selenium\service_account.json",  # Change to your path
    scopes=scope
)
client = gspread.authorize(creds)

# Function to fetch data fresh from Google Sheets
def load_data():
    try:
        sheet = client.open(SHEET_NAME).sheet1
        data = sheet.get_all_records()
        df = pd.DataFrame(data)

        # Normalize column names
        df.columns = df.columns.str.strip().str.lower()
        df.rename(columns={
            "job postings": "job_postings",
            "company": "company",
            "place": "place",
            "status": "status",
            "posted on": "posted_on",
            "url link": "url_link",
            "job_description": "job_description"
        }, inplace=True)

        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()

# ---------------- Dash App ----------------
app = dash.Dash(__name__, suppress_callback_exceptions=True)  # Handle dynamic components
app.title = "Job Postings Dashboard"

# ---------------- Layout ----------------
app.layout = html.Div([
    html.H1("📊 Job Postings Dashboard", style={"textAlign": "center"}),

    # Filters
    html.Div([
        html.Div([
            html.Label("Filter by Company"),
            dcc.Dropdown(id="company-filter", multi=True)
        ], style={"width": "23%", "display": "inline-block", "marginRight": "1%"}),

        html.Div([
            html.Label("Filter by Place"),
            dcc.Dropdown(id="place-filter", multi=True)
        ], style={"width": "23%", "display": "inline-block", "marginRight": "1%"}),

        html.Div([
            html.Label("Filter by Status"),
            dcc.Dropdown(id="status-filter", multi=True)
        ], style={"width": "23%", "display": "inline-block", "marginRight": "1%"}),

        html.Div([
            html.Label("Search Keywords (comma separated)"),
            dcc.Input(id="keyword-filter", type="text", placeholder="e.g. AWS, Python, Java",
                      style={"width": "100%"})
        ], style={"width": "29%", "display": "inline-block"})
    ], style={"margin": "20px"}),

    html.Hr(),

    # DataTable
    dash_table.DataTable(
        id="data-table",
        columns=[{"name": c.replace('_', ' ').title(), "id": c} for c in
                 ["job_postings", "company", "place", "status", "posted_on", "url_link"]],
        data=[],
        row_selectable="single",
        filter_action="native",
        sort_action="native",
        page_size=10,
        style_table={"overflowX": "auto"},
        style_cell={"textAlign": "left", "whiteSpace": "normal", "height": "auto"}
    ),

    # Drawer (Hidden Initially)
    html.Div(
        id="drawer",
        style={
            "position": "fixed",
            "top": 0,
            "right": "-40%",
            "height": "100%",
            "width": "40%",
            "backgroundColor": "white",
            "boxShadow": "-2px 0px 5px rgba(0,0,0,0.3)",
            "padding": "20px",
            "overflowY": "scroll",
            "transition": "right 0.5s ease-in-out",
            "zIndex": 1000
        },
        children=[]
    )
])

# ---------------- Callbacks ----------------

# Update filters + table
@app.callback(
    Output("company-filter", "options"),
    Output("place-filter", "options"),
    Output("status-filter", "options"),
    Output("data-table", "data"),
    Input("company-filter", "value"),
    Input("place-filter", "value"),
    Input("status-filter", "value"),
    Input("keyword-filter", "value")
)
def update_table(companies, places, statuses, keywords):
    df = load_data()

    # Handle empty DataFrame case
    if df.empty:
        return [], [], [], []

    # Populate filter dropdowns dynamically
    company_options = [{"label": c, "value": c} for c in sorted(df["company"].dropna().unique())]
    place_options = [{"label": p, "value": p} for p in sorted(df["place"].dropna().unique())]
    status_options = [{"label": s, "value": s} for s in sorted(df["status"].dropna().unique())]  # Fixed typo here

    # Apply filters
    filtered_df = df.copy()
    if companies:
        filtered_df = filtered_df[filtered_df["company"].isin(companies)]
    if places:
        filtered_df = filtered_df[filtered_df["place"].isin(places)]
    if statuses:
        filtered_df = filtered_df[filtered_df["status"].isin(statuses)]
    if keywords:
        terms = [k.strip().lower() for k in keywords.split(",") if k.strip()]
        mask = filtered_df["job_description"].fillna("").str.lower().apply(
            lambda text: any(term in text for term in terms)
        )
        filtered_df = filtered_df[mask]

    return company_options, place_options, status_options, filtered_df.to_dict("records")

# Drawer Display
@app.callback(
    Output("drawer", "style"),
    Output("drawer", "children"),
    Input("data-table", "selected_rows"),
    State("data-table", "data"),
    State("drawer", "style")
)
def display_drawer(selected_rows, table_data, drawer_style):
    if not selected_rows or not table_data:
        return {**drawer_style, "right": "-40%"}, []

    row = table_data[selected_rows[0]]

    # Format job description into bullet points
    description = row.get("job_description", "No description available")
    if description and description.strip():
        bullets = [html.Li(part.strip()) for part in description.replace("\n", " ").split(",") if part.strip()]
        desc_content = html.Ul(bullets)
    else:
        desc_content = html.P("No description available.")

    content = html.Div([
        html.Button("❌ Close", id="close-drawer", style={
            "float": "right", "background": "red", "color": "white", "border": "none",
            "padding": "5px 10px", "cursor": "pointer", "borderRadius": "5px"
        }),

        html.H2(row.get("job_postings", "N/A"), style={"marginTop": "0px"}),
        html.P(f"📌 Company: {row.get('company', 'N/A')}", style={"fontWeight": "bold"}),
        html.P(f"📍 Location: {row.get('place', 'N/A')}"),
        html.P(f"📝 Status: {row.get('status', 'N/A')}"),
        html.P(f"📅 Posted On: {row.get('posted_on', 'N/A')}"),
        html.A("🔗 View Job Posting", href=row.get("url_link", "#"),
               target="_blank", style={"color": "blue", "textDecoration": "underline"}),

        html.H3("📄 Job Description", style={"marginTop": "20px", "borderBottom": "1px solid #ddd"}),
        desc_content
    ])

    return {**drawer_style, "right": "0%"}, content

# Close Drawer
@app.callback(
    Output("drawer", "style", allow_duplicate=True),
    Input("close-drawer", "n_clicks"),
    State("drawer", "style"),
    prevent_initial_call=True
)
def close_drawer(n_clicks, drawer_style):
    if n_clicks:
        return {**drawer_style, "right": "-40%"}
    return drawer_style

# Run app
if __name__ == "__main__":
    app.run(debug=True)