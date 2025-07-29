# app.py
import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# --- PAGE SETUP ---
st.set_page_config(page_title="Social Pulse", layout="wide")
st.title("📡 Social Pulse Dashboard")
st.caption("Auto-updating social media intelligence from an n8n + Twitter + Google Sheets pipeline")

# --- DATA LOADING ---
csv_url = (
    "https://docs.google.com/spreadsheets/d/"
    "1V6Jtz-mMtltQKhaslIQRZ-AtHGaVo0Fy58KtLAzgKtg/export?format=csv&gid=0"
)
df = pd.read_csv(csv_url, on_bad_lines='skip')  # Skips malformed rows

# --- METRICS ---
st.subheader("📊 Metrics Overview")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Posts", len(df))
col2.metric("Total Views", df['Views'].sum())
col3.metric("Total Likes", df['Likes'].sum())
col4.metric("Total Retweets", df['Retweets'].sum())

# --- WORDCLOUD ---
st.subheader("☁️ Word Cloud of Post Content")

# --- CLEANING ---
from wordcloud import STOPWORDS
custom_stopwords = set(STOPWORDS).union({"https", "rt", "tco", "scott"})

# Fallback to auto-detect the cleaned column
clean_col = [col for col in df.columns if "Cleaned" in col][0]
text_data = " ".join(df[clean_col].dropna().astype(str).tolist())

# Word cloud configuration
wordcloud = WordCloud(
    width=1000,
    height=500,
    background_color="white",
    max_words=75,
    stopwords=custom_stopwords,
    collocations=False,
    prefer_horizontal=1
).generate(text_data)

# Display it cleanly inside Streamlit
image = wordcloud.to_image()
st.image(image, use_container_width=True)


# --- RAW TABLE ---
with st.expander("📋 View Raw Data"):
    st.dataframe(df)
