import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import pandas as pd
import psycopg2
import plotly.graph_objs as go

# PostgreSQL connection details
DB_HOST = '95.217.3.61'
DB_PORT = '5432'
DB_NAME = 'minor_s1129500'
DB_USER = 's1129500'
DB_PASS = '9820'
TABLE_NAME = 'stream.kafka'

# Initialize Dash app
app = dash.Dash(__name__)

# Full page styling using index_string
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        <title>Live Sensor Dashboard</title>
        <link href="https://fonts.googleapis.com/css2?family=Roboto&display=swap" rel="stylesheet">
        <style>
            html, body {
                background-color: #0F172A;
                margin: 0;
                padding: 0;
                font-family: 'Outfit', sans-serif;
                color: white;
                height: 100vh;
            }
            .container {
                display: grid;
                grid-template-columns: 2fr 1fr;
                gap: 20px;
                padding: 20px;
                height: 20vh;
            }
            .container2 {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                padding: 20px;
                margin-top: 20px;
                height: 50vh;
            }
            .box {
                background-color: #1E293B;
                border-radius: 10px;
                padding: 20px;
                border: 1px solid #334155;
                height: 100%;
            }
            .live-box {
                background-color: #1E293B;
                border-radius: 10px;
                padding: 20px;
                border: 1px solid #334155;
                display: flex;
                flex-direction: row;
                justify-content: space-between;
                align-items: center;
                height: 100%;
            }
            h1 {
                text-align: center;
                color: #F5F5F5;
                font-size: 36px;
                margin-bottom: 30px;
            }
            .sensor-text {
                font-size: 28px;
                text-align: center;
                margin-bottom: 20px;
                color: #00BFFF;
            }
            .timestamp-text {
                font-size: 22px;
                text-align: center;
                margin-top: 20px;
                color: #B0BEC5;
            }
            .table-container {
                display: flex;
                justify-content: center;
                margin-top: 30px;
            }
            .sensor-table {
                background-color: #1E1E1E;
                color: #E0E0E0;
                padding: 15px;
                border-radius: 8px;
                width: 40%;
                border: 1px solid #333;
                box-shadow: 0 0 15px rgba(0,0,0,0.5);
            }
            .sensor-table th {
                color: #00BFFF;
                font-size: 18px;
                border-bottom: 1px solid #333;
                padding-bottom: 10px;
            }
            .sensor-table td {
                padding: 12px 8px;
                font-size: 16px;
            }
            .graph-container {
                display: flex;
                justify-content: space-between;
                gap: 25px;
                margin-top: 30px;
            }
            .realtime-container {
                display: flex;
                justify-content: center;
                align-items: center;
                background-color: #1E1E1E;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 0 15px rgba(0,0,0,0.5);
            }
            .top-row {
                height: 100%;
                gap: 20px;
            }
            .bottom-row {
                height: 100%;
                gap: 20px;
                margin-top: 20px;
            }
            .metric {
                font-size: 40px;
                font-weight: 700;
            }
            .label {
                font-size: 14px;
                color: #94A3B8;
            }
            .small-title {
                font-size: 20px;
                font-weight: 600;
                margin-bottom: 10px;
            }
            .big-text {
                font-size: 64px;
                font-weight: bold;
            }
            .dash-graph .js-plotly-plot .plot-container .svg-container {
                background-color: #1E1E1E !important;
                border-radius: 8px;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Function to generate the sensor data table
def generate_sensor_table():
    return html.Table(
        className="sensor-table",
        children=[
            html.Tr([html.Th("Sensor Data"), html.Th("Value")]),
            html.Tr([html.Td("Min Temperature (°C)"), html.Td(id="min-temp")]),
            html.Tr([html.Td("Max Temperature (°C)"), html.Td(id="max-temp")]),
            html.Tr([html.Td("Min Humidity (%)"), html.Td(id="min-humidity")]),
            html.Tr([html.Td("Max Humidity (%)"), html.Td(id="max-humidity")]),
        ]
    )

# Layout of the app
app.layout = html.Div([    
    dcc.Interval(id='interval-component', interval=2*1000, n_intervals=0),  # Refresh every 2 sec
    html.Div([
        html.Div(className="live-box", children=[
            html.Div([
                html.Div("temperatuur:", className="label"),
                html.Div(id='temperatuur-text', className='big-text'),
            ]),
            html.Div([
                html.Div("luchtvochtigheid:", className="label"),
                html.Div(id='luchtvochtigheid-text', className='big-text'),
            ]),
            html.Div([
                html.Div("timestamp", className="label"),
                html.Div(id='timestamp-text', className='big-text'),
            ]),

        ],),

            # Table to show min and max temperature and humidity
        html.Div([
            html.Div("extremes", className="small-title"),
            html.Div([
                html.Div(id="min-temp", style={"margin-bottom": "5px", "margin-top": "10px"}),
                html.Div(id="max-temp", style={"margin-bottom": "5px", "margin-top": "10px"}),
                html.Div(id="min-humidity", style={"margin-bottom": "5px", "margin-top": "10px"}),
                html.Div(id="max-humidity", style={"margin-bottom": "5px", "margin-top": "10px"}),
            ])
        ], className="box")

    ], className="container"),
    # Div container to display graphs side by side
    html.Div(
        className="container2",
        children=[
            dcc.Graph(id='temperature-graph', className="box"),
            dcc.Graph(id='humidity-graph')
        ],
    ),

])

# Function to fetch the latest data from the database
def fetch_latest_data(limit=1):
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        query = f"""
            SELECT luchtvochtigheid, temperatuur, timestamp
            FROM {TABLE_NAME}
            ORDER BY timestamp DESC
            LIMIT {limit};
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame()

# Function to build the gauge chart
def build_gauge(temperatuur):
    return go.Figure(go.Indicator(
        mode="gauge+number",
        value=temperatuur,
        title={'text': "Temperatuur (°C)"},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': "orange"},
            'steps': [
                {'range': [0, 80], 'color': "lightgreen"},
                {'range': [80, 100], 'color': "tomato"}
            ],
        }
    ))

# Function to query data for the last day (past 24 hours)
def fetch_data_for_last_day(latest_timestamp):
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )

        query = f"""
            SELECT luchtvochtigheid, temperatuur, timestamp
            FROM {TABLE_NAME}
            WHERE timestamp BETWEEN '{latest_timestamp}'::timestamp - INTERVAL '1 day'
                            AND '{latest_timestamp}'::timestamp
            ORDER BY timestamp DESC;
        """
        history_df = pd.read_sql(query, conn)
        conn.close()
        return history_df
    except Exception as e:
        print(f"Error fetching history data: {e}")
        return pd.DataFrame()

# Function to build the temperature graph
def build_temperature_graph(history_df):
    if not history_df.empty:
        timestamps = history_df['timestamp'].astype(str)
        temperatures = history_df['temperatuur']

        temperature_graph_fig = go.Figure(go.Scatter(
            x=timestamps,
            y=temperatures,
            mode='lines+markers',
            name="Temperatuur",
            line=dict(color='orange')
        ))

        temperature_graph_fig.update_layout(
            title="Temperature over the Last Day",
            xaxis_title="Timestamp",
            yaxis_title="Temperature (°C)",
            yaxis=dict(range=[15, 30]),  # Fixed y-axis range
            plot_bgcolor="#1A1A1A",
            paper_bgcolor="#1A1A1A",
            font=dict(color="white")
        )

        return temperature_graph_fig
    else:
        return go.Figure()  # Empty graph if no data

# Function to build the humidity graph
def build_humidity_graph(history_df):
    if not history_df.empty:
        timestamps = history_df['timestamp'].astype(str)
        humidity = history_df['luchtvochtigheid']

        humidity_graph_fig = go.Figure(go.Scatter(
            x=timestamps,
            y=humidity,
            mode='lines+markers',
            name="Humidity",
            line=dict(color='blue')
        ))

        humidity_graph_fig.update_layout(
            title="Humidity over the Last Day",
            xaxis_title="Timestamp",
            yaxis_title="Humidity (%)",
            yaxis=dict(range=[20, 35]),  # Fixed y-axis range for humidity
            plot_bgcolor="#1A1A1A",
            paper_bgcolor="#1A1A1A",
            font=dict(color="white"),
            responsive=True
        )

        return humidity_graph_fig
    else:
        return go.Figure()  # Empty graph if no data

# Callback to update the data
@app.callback(
    Output('luchtvochtigheid-text', 'children'),
    Output('temperatuur-text', 'children'),
    Output('timestamp-text', 'children'),
    Output('temperature-graph', 'figure'),
    Output('humidity-graph', 'figure'),
    Output('min-temp', 'children'),
    Output('max-temp', 'children'),
    Output('min-humidity', 'children'),
    Output('max-humidity', 'children'),
    Input('interval-component', 'n_intervals'),
)
def update_display(n):
    df = fetch_latest_data(limit=1)
    
    if not df.empty:
        luchtvochtigheid = df['luchtvochtigheid'].iloc[0]
        temperatuur = df['temperatuur'].iloc[0]
        latest_timestamp = df['timestamp'].iloc[0]

        # Build the gauge chart
        gauge_fig = build_gauge(temperatuur)

        # Query data for the last day (past 24 hours)
        history_df = fetch_data_for_last_day(latest_timestamp)

        # Prepare data for the temperature and humidity graphs
        temperature_graph_fig = build_temperature_graph(history_df)
        humidity_graph_fig = build_humidity_graph(history_df)

        # Calculate min and max values
        min_temp = history_df['temperatuur'].min() if not history_df.empty else 'N/A'
        max_temp = history_df['temperatuur'].max() if not history_df.empty else 'N/A'
        min_humidity = history_df['luchtvochtigheid'].min() if not history_df.empty else 'N/A'
        max_humidity = history_df['luchtvochtigheid'].max() if not history_df.empty else 'N/A'

        return (
            f"{luchtvochtigheid}%",
            f"{temperatuur}°C",    
            f"{latest_timestamp}",
            temperature_graph_fig,
            humidity_graph_fig,
            f"Min Temp: {min_temp}°C",
            f"Max Temp: {max_temp}°C",
            f"Min Humid: {min_humidity}%",
            f"Max Humid: {max_humidity}%",
        )
    else:
        # Fallback if no data is available
        return "No Data", go.Figure(), "No Data", go.Figure(), go.Figure(), 'N/A', 'N/A', 'N/A', 'N/A'


if __name__ == '__main__':
    app.run(debug=True)
