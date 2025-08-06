# app.py
import streamlit as st
import pandas as pd
from wordcloud import WordCloud, STOPWORDS
import matplotlib.pyplot as plt

# ── PAGE SETUP ────────────────────────────────────────────────
st.set_page_config(page_title="Social Pulse", layout="wide", page_icon="📡")
st.title("📡 Social Pulse Dashboard")
st.caption("Auto-updating social media intelligence from an n8n ➜ Twitter ➜ Google Sheets pipeline")

# ── DATA LOADING (cached 1 h) ────────────────────────────────
CSV_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1V6Jtz-mMtltQKhaslIQRZ-AtHGaVo0Fy58KtLAzgKtg/export?format=csv&gid=0"
)

@st.cache_data(ttl=3600)
def load_data(url: str) -> pd.DataFrame:
    return pd.read_csv(url, on_bad_lines="skip")

df = load_data(CSV_URL)

# ensure a datetime column
if "Date" in df.columns:
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

# ── METRICS OVERVIEW ─────────────────────────────────────────
st.subheader("📊 Metrics Overview")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Posts", f"{len(df):,}")
col2.metric("Total Views", f"{df['Views'].sum():,}")
col3.metric("Total Likes", f"{df['Likes'].sum():,}")
col4.metric("Total Retweets", f"{df['Retweets'].sum():,}")

# ── TOP ROW — Word-Cloud & Volume-Over-Time ──────────────────
st.subheader("⚡ Conversation Snapshot")
wc_col, vot_col = st.columns(2)

# Word-cloud
with wc_col:
    custom_stop = STOPWORDS.union({"https", "rt", "tco", "scott"})
    clean_cols = [c for c in df.columns if "Cleaned" in c]
    if clean_cols:
        text_blob = " ".join(df[clean_cols[0]].dropna().astype(str))
        wc = WordCloud(
            width=800,
            height=400,
            background_color="white",
            max_words=75,
            stopwords=custom_stop,
            collocations=False,
            prefer_horizontal=1,
        ).generate(text_blob)
        st.image(wc.to_image(), use_column_width=True)
    else:
        st.info("No cleaned-text column found — skipping word-cloud.")

# Volume-over-time
with vot_col:
    if "Date" in df.columns and not df["Date"].isna().all():
        daily_posts = df.groupby(df["Date"].dt.date).size()
        st.line_chart(daily_posts, height=400)
    else:
        st.info("No date column available for volume-over-time chart.")

# ── SECOND ROW — Leaderboards ────────────────────────────────
lead_left, lead_right = st.columns(2)

# Engagement score helper
df["Engagement"] = (
    df.get("Likes", 0) + df.get("Retweets", 0) + df.get("Views", 0)
)

# Top authors
with lead_left:
    st.subheader("🏆 Top Authors (Engagement)")
    if "Author" in df.columns:
        top_auth = (
            df.groupby("Author")["Engagement"]
            .sum()
            .sort_values(ascending=False)
            .head(10)
            .reset_index()
        )
        st.dataframe(top_auth, use_container_width=True, hide_index=True)
    else:
        st.info("No Author column found.")

# Top posts
with lead_right:
    st.subheader("🔥 Top Posts (Engagement)")
    if all(c in df.columns for c in ["Content", "Engagement"]):
        top_posts = (
            df[["Content", "Engagement"]]
            .sort_values("Engagement", ascending=False)
            .head(10)
            .reset_index(drop=True)
        )
        st.dataframe(top_posts, use_container_width=True, hide_index=True)
    else:
        st.info("Need Content & Engagement columns to build leaderboard.")

# ── RAW DATA ─────────────────────────────────────────────────
with st.expander("📋 View Raw Data"):
    st.dataframe(df, use_container_width=True)
