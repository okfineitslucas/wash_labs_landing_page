# pages/2_Deep_Dive.py
import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Deep Dive • Social Pulse", layout="wide", page_icon="🧭")

CSV_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1V6Jtz-mMtltQKhaslIQRZ-AtHGaVo0Fy58KtLAzgKtg/export?format=csv&gid=0"
)

@st.cache_data(ttl=3600)
def load_data(url: str) -> pd.DataFrame:
    df = pd.read_csv(url, on_bad_lines="skip")
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    for col in ["Likes","Retweets","Replies","Quotes","Views"]:
        if col not in df.columns:
            df[col] = 0
    # Engagement + quality metrics
    df["Interactions"] = df[["Likes","Retweets","Replies","Quotes"]].sum(axis=1)
    df["Engagement"]  = df["Interactions"] + df["Views"]
    df["ER"] = df["Interactions"] / df["Views"].replace({0: pd.NA})  # per-view engagement rate
    return df

df = load_data(CSV_URL)

st.title("🧭 Deep Dive")
st.caption("Drill into authors, posts, hashtags & engagement quality.")

# ── SIDEBAR FILTERS ──────────────────────────────────────────
with st.sidebar:
    st.header("Filters")
    # Date range
    if "Date" in df.columns and not df["Date"].isna().all():
        min_d, max_d = df["Date"].min(), df["Date"].max()
        date_range = st.date_input("Date range", (min_d.date(), max_d.date()))
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start, end = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
            df = df[(df["Date"] >= start) & (df["Date"] <= end)]

    # Author filter
    authors = sorted([a for a in df["Author"].dropna().unique()]) if "Author" in df.columns else []
    sel_authors = st.multiselect("Authors", authors, default=[])
    if sel_authors:
        df = df[df["Author"].isin(sel_authors)]

    # Min views
    min_views = int(df["Views"].quantile(0.5)) if "Views" in df.columns else 0
    mv = st.slider("Minimum Views", 0, int(df["Views"].max() if "Views" in df.columns else 0), min_views)
    if "Views" in df.columns:
        df = df[df["Views"] >= mv]

    # Keyword search
    q = st.text_input("Keyword (search Content)")
    if q and "Content" in df.columns:
        df = df[df["Content"].str.contains(q, case=False, na=False)]

# ── TOP KPIs (FILTERED) ─────────────────────────────────────
st.subheader("🎯 Filtered Overview")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Posts", f"{len(df):,}")
k2.metric("Views", f"{int(df['Views'].sum()):,}")
k3.metric("Interactions", f"{int(df['Interactions'].sum()):,}")
avg_er = df["ER"].mean(skipna=True)
k4.metric("Avg ER", f"{avg_er:.2%}" if pd.notna(avg_er) else "—")

st.markdown("---")

# ── HASHTAGS & MENTIONS ─────────────────────────────────────
def extract_hashtags(text):
    return re.findall(r"#\w+", text or "")

def extract_mentions(text):
    return re.findall(r"@\w+", text or "")

if "Content" in df.columns:
    tags = df["Content"].dropna().apply(extract_hashtags).explode()
    mentions = df["Content"].dropna().apply(extract_mentions).explode()

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🏷️ Top Hashtags")
        top_tags = tags.value_counts().head(15).reset_index()
        top_tags.columns = ["Hashtag","Count"]
        st.dataframe(top_tags, use_container_width=True, hide_index=True)
    with c2:
        st.subheader("👤 Top Mentions")
        top_m = mentions.value_counts().head(15).reset_index()
        top_m.columns = ["Handle","Count"]
        st.dataframe(top_m, use_container_width=True, hide_index=True)

st.markdown("---")

# ── AUTHOR DRILLDOWN ────────────────────────────────────────
st.subheader("🧑‍💻 Author Drilldown")
author_for_drill = None
if "Author" in df.columns and len(df["Author"].dropna().unique()) > 0:
    author_for_drill = st.selectbox("Select author", ["(overall)"] + sorted(df["Author"].dropna().unique().tolist()))
else:
    st.info("No Author column available.")

df_drill = df if not author_for_drill or author_for_drill == "(overall)" else df[df["Author"] == author_for_drill]

# Trend
if "Date" in df_drill.columns and not df_drill["Date"].isna().all():
    trend = df_drill.groupby(df_drill["Date"].dt.date)[["Views","Interactions"]].sum()
    st.line_chart(trend, height=320)

# Best posts for the author/overall
keep = [c for c in ["Date","Author","Content","Views","Likes","Retweets","Replies","Quotes","ER","URL"] if c in df_drill.columns]
topn = st.slider("Rows to show", 5, 50, 10)
best = df_drill.sort_values(["Interactions","Views"], ascending=False).head(topn)[keep]
st.dataframe(best, use_container_width=True, hide_index=True)

# ── POST EXPLORER + DOWNLOAD ────────────────────────────────
st.markdown("---")
st.subheader("🔎 Post Explorer")
cols = [c for c in ["Date","Author","Name","Content","Views","Likes","Retweets","Replies","Quotes","ER","URL"] if c in df.columns]
st.dataframe(df[cols].sort_values("Date", ascending=False), use_container_width=True, hide_index=True)

csv = df[cols].to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Download filtered CSV", csv, file_name="social_pulse_filtered.csv", mime="text/csv")
