from dash import Dash, html, Input, Output, dcc, dash_table
import psycopg2
import pandas as pd
import plotly.graph_objects as go

# Connect to the PostgreSQL server
def get_data(interval='1 day'):
    try:
        conn = psycopg2.connect(
            host='95.217.3.61',
            port='5432',
            database='minor_s1129500',
            user='s1129500',
            password='9820'
        )
        query = f"""
            SELECT temperatuur, luchtvochtigheid, timestamp
            FROM stream.kafka
            WHERE timestamp >= NOW() - INTERVAL '{interval}'
            ORDER BY timestamp ASC;
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame()

# Calculate spikes (differences from the previous reading)
def calculate_spikes(df):
    if df.empty or len(df) < 2:
        return pd.DataFrame()

    df['temp_spike'] = df['temperatuur'].diff()
    df['humidity_spike'] = df['luchtvochtigheid'].diff()
    return df

# Initialize the Dash app
app = Dash(__name__)

# Layout of the app
app.layout = html.Div([  
        html.Div([
            html.Div(children=[
                html.H1("Live data"),
                dcc.Graph(id='latest-temperature-gauge', style={'height': '300px'}),  # Gauge chart for temperature
                html.Div(id='latest-humidity', style={'fontSize': '24px', 'marginTop': '10px'}),
                html.Div(id='latest-timestamp', style={'fontSize': '20px', 'marginTop': '10px'}),
            ], className="realtime-card"),
            html.Div( className="dcc-graph", children=[
                html.H1("Temperatuur en Luchtvochtigheid"),
                dcc.Dropdown(
                    id='time-interval',
                    options=[
                        {'label': 'Laatste 1 uur', 'value': '1 hour'},
                        {'label': 'Laatste 1 dag', 'value': '1 day'},
                        {'label': 'Laatste 1 week', 'value': '1 week'},
                        {'label': 'Laatste 1 maand', 'value': '1 month'},
                    ],
                    value='1 day',  # Standaardwaarde
                ),
                dcc.Graph(id='line-chart'),
            ]),
            dcc.Store(id='spikes-store', data=[]),  # Voeg de dcc.Store toe aan de layout
            html.Div(
                className="dashboard-content",
                children=[
                    html.Div(
                    className="spikes-card",
                    children=[
                            html.H1("Spikes"),
                        # Inner div for the gradient
                            html.Div(
                                className="spikes-gradient"
                            ),
                        # Content of the spikes card
                            html.Div(
                                id='spikes-text',
                            )
                        ]
                    ),
                    html.Div(
                        className="dash-table-container",
                        children=[
                            html.H1("Extremen"),
                            dash_table.DataTable(
                                id='extremes-table',
                                columns=[
                                    {'name': 'Type', 'id': 'type'},
                                    {'name': 'Waarde', 'id': 'value'},
                                    {'name': 'Tijdstip', 'id': 'timestamp'}
                                ],
                                style_table={'width': '100%', 'color': '#000000'},
                                style_cell={'textAlign': 'center', 'color': '#000000'},
                                style_header={'fontWeight': 'bold', 'color': '#000000'}
                            )
                        ]
                    )
                ]
            )
        ], className="main"),  # Hier is een komma toegevoegd om de lijst correct af te sluiten

        dcc.Interval(
            id='interval-component',
            interval=5*1000,  # Elke 5 seconden (in milliseconden)
            n_intervals=0  # Aantal intervallen sinds de start
        )
], className="page")

# Callback to update the graph
@app.callback(
     Output('line-chart', 'figure'),
    [Input('time-interval', 'value'),
     Input('interval-component', 'n_intervals')]
)


def update_graph(interval, n_intervals):
    df = get_data(interval)
    if df.empty:
        # Empty graph if no data is available
        fig = go.Figure()
        fig.update_layout(
            title="Geen data beschikbaar",
            xaxis_title="Tijdstip",
            yaxis_title="Waarde",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white")
        )
        return fig

    # Create the graph with two lines
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['temperatuur'],
        mode='lines',
        name='Temperatuur (°C)',
        line=dict(color='orange')
    ))
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['luchtvochtigheid'],
        mode='lines',
        name='Luchtvochtigheid (%)',
        line=dict(color='blue')
    ))

    # Update the layout of the graph with a range slider
    fig.update_layout(
        title="Temperatuur en Luchtvochtigheid Over Tijd",
        xaxis_title="Tijdstip",
        yaxis_title="Waarde",
        xaxis=dict(
            rangeslider={"visible": True},  # Add the range slider
            type="date"
        ),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

# Callback to update the latest temperature, humidity, and timestamp
@app.callback(
    [Output('latest-temperature-gauge', 'figure'),
     Output('latest-humidity', 'children'),
     Output('latest-timestamp', 'children')],
    Input('interval-component', 'n_intervals')
)
def update_latest_data(n_intervals):
    df = get_data('1 day')  # Fetch data for the last day
    if df.empty:
        # Return empty gauge and placeholder texts if no data is available
        gauge_fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=0,
            title={'text': "Temperatuur (°C)"},
            gauge={'axis': {'range': [0, 50]}}
        ))
        return gauge_fig, "Geen data beschikbaar", "Geen data beschikbaar"

    last_row = df.iloc[-1]

    # Create the gauge chart for temperature
    gauge_fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=last_row['temperatuur'],
        title={'text': "Temperatuur (°C)"},
        gauge={
            'axis': {'range': [0, 50]},  # Adjust range based on your data
            'bar': {'color': "orange"},
            'steps': [
                {'range': [0, 10], 'color': "lightblue"},
                {'range': [10, 25], 'color': "lightgreen"},
                {'range': [25, 50], 'color': "red"}
            ]
        }
    ))

    # Text for humidity
    latest_humidity = f"Laatste luchtvochtigheid: {last_row['luchtvochtigheid']:.2f}%"

    # Text for timestamp
    latest_timestamp = f"Laatste tijdstip: {last_row['timestamp']}"

    return gauge_fig, latest_humidity, latest_timestamp

# Callback to display and store spikes
@app.callback(
    [Output('spikes-text', 'children'),
     Output('spikes-store', 'data')],
    [Input('time-interval', 'value'),
     Input('interval-component', 'n_intervals')],
    [Input('spikes-store', 'data')]
)
def update_spikes_text(interval, n_intervals, stored_spikes):
    df = get_data(interval)
    df = calculate_spikes(df)
    if df.empty or df[['temp_spike', 'humidity_spike']].isna().all().all():
        return stored_spikes, stored_spikes

    # Copy existing spikes
    spikes = stored_spikes.copy() if stored_spikes else []

    last_row = df.iloc[-1]

    temp_spike_div = None
    humidity_spike_div = None

    # Check temperature spike
    if not pd.isna(last_row['temp_spike']) and last_row['temp_spike'] != 0:
        color = 'red' if last_row['temp_spike'] < 0 else 'blue'
        arrow = '↓' if last_row['temp_spike'] < 0 else '↑'
        temp_spike_div = html.Div([
            html.Span(f"Temperatuur: {arrow} {'+' if last_row['temp_spike'] > 0 else ''}{last_row['temp_spike']:.2f}°C",
                      style={'color': color, 'fontSize': '24px', 'fontWeight': 'bold'}),
            html.Br(),
            html.Span(f"Tijdstip: {last_row['timestamp']}")
        ])
        spikes.append({'type': 'temp', 'content': temp_spike_div})

    # Check humidity spike
    if not pd.isna(last_row['humidity_spike']) and last_row['humidity_spike'] != 0:
        color = 'red' if last_row['humidity_spike'] < 0 else 'blue'
        arrow = '↓' if last_row['humidity_spike'] < 0 else '↑'
        humidity_spike_div = html.Div([
            html.Span(f"Luchtvochtigheid: {arrow} {'+' if last_row['humidity_spike'] > 0 else ''}{last_row['humidity_spike']:.2f}%",
                      style={'color': color, 'fontSize': '24px', 'fontWeight': 'bold'}),
            html.Br(),
            html.Span(f"Tijdstip: {last_row['timestamp']}")
        ])
        spikes.append({'type': 'humidity', 'content': humidity_spike_div})

    # Combine all spikes for display
    children = [spike['content'] for spike in spikes]

    return children, spikes

# Callback to update the extremes table
@app.callback(
    Output('extremes-table', 'data'),
    [Input('time-interval', 'value'),
     Input('interval-component', 'n_intervals')]
)
def update_extremes_table(interval, n_intervals):
    df = get_data(interval)
    if df.empty:
        return []

    # Calculate max and min values
    max_temp = df['temperatuur'].max()
    max_temp_time = df.loc[df['temperatuur'].idxmax(), 'timestamp']
    min_temp = df['temperatuur'].min()
    min_temp_time = df.loc[df['temperatuur'].idxmin(), 'timestamp']

    max_humidity = df['luchtvochtigheid'].max()
    max_humidity_time = df.loc[df['luchtvochtigheid'].idxmax(), 'timestamp']
    min_humidity = df['luchtvochtigheid'].min()
    min_humidity_time = df.loc[df['luchtvochtigheid'].idxmin(), 'timestamp']

    # Prepare data for the table
    extremes_data = [
        {"type": "Max Temperatuur", "value": max_temp, "timestamp": max_temp_time},
        {"type": "Min Temperatuur", "value": min_temp, "timestamp": min_temp_time},
        {"type": "Max Luchtvochtigheid", "value": max_humidity, "timestamp": max_humidity_time},
        {"type": "Min Luchtvochtigheid", "value": min_humidity, "timestamp": min_humidity_time}
    ]
    return extremes_data

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
