import streamlit as st
import pandas as pd
import psycopg2
from streamlit_autorefresh import st_autorefresh
import plotly.graph_objects as go

# ---------------------- CONFIG ----------------------
st.set_page_config(page_title="Crypto Dashboard", layout="wide")
st_autorefresh(interval=5000, key="refresh")

st.title("🚀 Crypto Live Dashboard")

# ---------------------- DB CONNECTION ----------------------
@st.cache_resource
def get_connection():
    return psycopg2.connect(
        host="localhost",
        database="crypto",
        user="admin",
        password="admin"
    )

# ---------------------- LOAD DATA --------------------------
@st.cache_data(ttl=5)
def load_data():
    conn = get_connection()  # ✅ FIXED (no argument)

    query = """
        SELECT 
            symbol, 
            price, 
            timestamp AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata' AS timestamp
        FROM crypto_prices
        WHERE timestamp > NOW() - INTERVAL '3 hours'
        ORDER BY timestamp
    """

    df = pd.read_sql(query, conn)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    return df.sort_values("timestamp")

# ---------------------- FILTERS ----------------------
def apply_filters(df):
    st.sidebar.header("⚙️ Filters")

    coins = st.sidebar.multiselect(
        "Select Coins",
        options=df["symbol"].unique(),
        default=df["symbol"].unique()
    )

    time_filter = st.sidebar.selectbox(
        "Time Range",
        ["5 min", "15 min", "1 hour", "3 hour"]
    )

    df = df[df["symbol"].isin(coins)]

    now = pd.Timestamp.now()

    if time_filter == "5 min":
        df = df[df["timestamp"] > now - pd.Timedelta(minutes=5)]
    elif time_filter == "15 min":
        df = df[df["timestamp"] > now - pd.Timedelta(minutes=15)]
    elif time_filter == "1 hour":
        df = df[df["timestamp"] > now - pd.Timedelta(hours=1)]
    else:
        df = df[df["timestamp"] > now - pd.Timedelta(hours=3)]

    return df

# ---------------------- METRICS ----------------------
def show_metrics(df):
    st.subheader("💰 Live Market Overview")

    latest = df.groupby("symbol").tail(2)
    symbols = latest["symbol"].unique()

    cols = st.columns(len(symbols))

    for i, symbol in enumerate(symbols):
        coin_df = latest[latest["symbol"] == symbol]

        if len(coin_df) == 2:
            old_price = coin_df.iloc[0]["price"]
            new_price = coin_df.iloc[1]["price"]

            change_pct = ((new_price - old_price) / old_price) * 100

            cols[i].metric(
                label=symbol,
                value=round(new_price, 2),
                delta=f"{round(change_pct, 2)}%"
            )

# ---------------------- LINE CHART ----------------------
def plot_line_chart(df):
    df_pivot = df.pivot_table(
        index="timestamp",
        columns="symbol",
        values="price",
        aggfunc="last"
    ).sort_index()

   # df_smooth = df_pivot.rolling(window=5).mean()

    st.subheader("📈 Price Trend")
    st.line_chart(df_pivot)

   # st.subheader("📊 Smoothed Trend")
    #st.line_chart(df_smooth)

# ---------------------- CANDLESTICK ----------------------
def create_candlestick(df, symbol):
    df_coin = df[df["symbol"] == symbol].copy()
    df_coin.set_index("timestamp", inplace=True)

    # 🔥 Better candle density
    ohlc = df_coin["price"].resample("30s").ohlc().dropna()

    fig = go.Figure(data=[go.Candlestick(
        x=ohlc.index,
        open=ohlc['open'],
        high=ohlc['high'],
        low=ohlc['low'],
        close=ohlc['close']
    )])

    fig.update_layout(
        template="plotly_dark",
        title=f"{symbol} Candlestick Chart",
        height=600,
        xaxis_rangeslider_visible=True,
        margin=dict(l=10, r=10, t=40, b=10)
    )

    # Focus on last 50 candles
    if len(ohlc) > 50:
        fig.update_xaxes(range=[ohlc.index[-50], ohlc.index[-1]])

    return fig

def plot_candlestick(df):
    st.subheader("🕯️ Candlestick Chart")

    symbol = st.selectbox(
        "Select Coin",
        options=df["symbol"].unique()
    )

    fig = create_candlestick(df, symbol)
    st.plotly_chart(fig, use_container_width=True)

# ---------------------- MAIN ----------------------
df = load_data()

if df.empty:
    st.warning("No data available yet...")
    st.stop()

df = apply_filters(df)

show_metrics(df)
plot_line_chart(df)
plot_candlestick(df)

# ---------------------- DEBUG ----------------------
with st.expander("🔍 Debug Data"):
    st.write(df.tail())