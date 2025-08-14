# pages/3_Leaders_Now.py
import streamlit as st
import pandas as pd
import numpy as np
import re
from app_settings import STREAMS, HEAT

st.set_page_config(page_title="Leaders Now • Social Pulse", layout="wide", page_icon="🏛️")

@st.cache_data(ttl=1800)
def load_stream(url: str) -> pd.DataFrame:
    df = pd.read_csv(url, on_bad_lines="skip")

    # --- Dates: parse as UTC-aware so all math/comparisons are consistent ---
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce", utc=True)

    # --- Ensure numeric interaction cols exist ---
    for c in ["Likes", "Retweets", "Replies", "Quotes", "Views"]:
        if c not in df.columns:
            df[c] = 0

    # --- Optional metadata (will be NaN on test data) ---
    for c in ["Party", "Role", "State", "Official"]:
        if c not in df.columns:
            df[c] = pd.NA

    return df

def compute_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Interactions & ER
    df["Interactions"] = df[["Likes", "Retweets", "Replies", "Quotes"]].sum(axis=1)
    df["ER"] = df["Interactions"] / df["Views"].replace({0: np.nan})

    # --- Heat Index with time decay (use UTC-aware now to match df["Date"]) ---
    now_utc = pd.Timestamp.now(tz="UTC")
    if "Date" in df.columns and df["Date"].notna().any():
        age_hours = (now_utc - df["Date"]).dt.total_seconds() / 3600
        # Treat missing/invalid dates as very old (Heat ~ 0)
        age_hours = age_hours.fillna(1e6)
    else:
        age_hours = pd.Series(1e6, index=df.index)

    # Use explicit keys (don’t rely on dict order)
    alpha = HEAT["alpha_likes"]
    beta = HEAT["beta_retweets"]
    gamma = HEAT["gamma_replies"]
    delta = HEAT["delta_quotes"]
    lam   = HEAT["lambda_decay"]

    base  = np.log1p(df["Views"]) + alpha*df["Likes"] + beta*df["Retweets"] + gamma*df["Replies"] + delta*df["Quotes"]
    decay = np.exp(-lam * age_hours)
    df["Heat"] = base * decay

    return df

def top_ngrams(df: pd.DataFrame, text_col="Cleaned Content", n=2, topn=20):
    # Fallback to Content if Cleaned not present
    if text_col not in df.columns:
        text_col = "Content" if "Content" in df.columns else None
    if not text_col:
        return pd.DataFrame(columns=["gram", "count", "avg_ER", "avg_Heat"])

    rows = []
    for _, r in df.dropna(subset=[text_col]).iterrows():
        toks = re.findall(r"(?:[#@]?\w+)", str(r[text_col]).lower())
        toks = [t for t in toks if t not in {"rt", "https", "tco"}]
        if len(toks) < n:
            continue
        grams = list(zip(*[toks[i:] for i in range(n)]))
        for g in grams:
            rows.append({
                "gram": " ".join(g),
                "ER":   r.get("ER", np.nan),
                "Heat": r.get("Heat", np.nan),
            })

    if not rows:
        return pd.DataFrame(columns=["gram", "count", "avg_ER", "avg_Heat"])

    gdf = pd.DataFrame(rows)
    agg = gdf.groupby("gram").agg(
        count=("gram", "count"),
        avg_ER=("ER", "mean"),
        avg_Heat=("Heat", "mean"),
    ).reset_index()

    return agg.sort_values(["avg_Heat", "count"], ascending=[False, False]).head(topn)

# ---------- DATA ----------
df = compute_metrics(load_stream(STREAMS["leaders"]))

st.title("🏛️ Leaders Now")
st.caption("Live view of what U.S. leaders are saying right now (designed for high-volume hourly updates).")

# ---------- FILTERS ----------
with st.sidebar:
    st.header("Filters")

    # Timeframe (make start/end UTC-aware to match df["Date"])
    if "Date" in df.columns and df["Date"].notna().any():
        maxd = df["Date"].max()  # tz-aware
        default_start = (maxd - pd.Timedelta(days=1)).date()
        start_date, end_date = st.date_input("Date range", (default_start, maxd.date()))

        # Convert to UTC-aware bounds (end inclusive)
        start = pd.to_datetime(start_date).tz_localize("UTC")
        end   = pd.to_datetime(end_date).tz_localize("UTC") + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
        df = df[(df["Date"] >= start) & (df["Date"] <= end)]

    # Official-only (will no-op on test data)
    official_only = st.checkbox("Official accounts only", value=True)
    if official_only and "Official" in df.columns and df["Official"].notna().any():
        df = df[df["Official"].astype(str).str.lower().isin(["true", "1"])]

    # Party filters (works when Party exists)
    parties = sorted(df.get("Party", pd.Series(dtype=str)).dropna().unique().tolist())
    sel_party = st.multiselect("Party", parties, default=parties if parties else [])
    if sel_party:
        df = df[df["Party"].isin(sel_party)]

    # Min views to tame the firehose
    mv = st.slider("Minimum Views", 0, int(df["Views"].max() or 0), int(df["Views"].median() or 0))

# Apply min-views filter
df = df[df["Views"] >= mv] if "Views" in df.columns else df

# ---------- KPIs ----------
st.subheader("🎯 Right Now")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Posts", f"{len(df):,}")
k2.metric("Views (24h)", f"{int(df['Views'].sum()):,}")
k3.metric("Avg ER", f"{df['ER'].mean(skipna=True):.2%}" if len(df) else "—")
k4.metric("Heat Index", f"{df['Heat'].sum():,.0f}")

st.markdown("---")

# ---------- TOPICS ----------
c1, c2 = st.columns(2)
with c1:
    st.subheader("🔥 Top Topics (by Heat)")
    st.dataframe(top_ngrams(df, n=2, topn=25), use_container_width=True, hide_index=True)

with c2:
    st.subheader("📌 Top Hashtags (by Heat)")
    if "Content" in df.columns and len(df):
        contents = df["Content"].dropna().astype(str).str.lower()
        tags = contents.apply(lambda t: re.findall(r"#\w+", t)).explode()
        if tags.notna().any():
            ht = pd.DataFrame({
                "Hashtag": tags,
                "Heat": df.loc[tags.index, "Heat"].values
            })
            ttab = ht.groupby("Hashtag").agg(
                count=("Hashtag", "count"),
                avg_Heat=("Heat", "mean")
            ).reset_index()
            st.dataframe(
                ttab.sort_values(["avg_Heat", "count"], ascending=[False, False]).head(25),
                use_container_width=True, hide_index=True
            )
        else:
            st.info("No hashtags found in this slice.")
    else:
        st.info("No Content column available.")

st.markdown("---")

# ---------- LEADERS FEED ----------
st.subheader("🗞️ Leaders Feed")
cols = [c for c in ["Date","Party","Role","Author","Content","Views","Likes","Retweets","Replies","Quotes","ER","Heat","URL"] if c in df.columns]
feed = df.sort_values("Heat", ascending=False).head(100)[cols] if len(df) else df
st.dataframe(feed, use_container_width=True, hide_index=True)

# ---------- CROSS-PARTY CONTRAST ----------
st.markdown("---")
st.subheader("⚖️ Cross-Party Contrast (last 24h)")
if "Date" in df.columns and df["Date"].notna().any():
    recent = df[df["Date"] >= (df["Date"].max() - pd.Timedelta(hours=24))]
    if "Party" in recent.columns and recent["Party"].notna().any():
        left = recent[recent["Party"].str.contains("Dem", case=False, na=False)]
        right = recent[recent["Party"].str.contains("Rep", case=False, na=False)]
        c3, c4 = st.columns(2)
        with c3:
            st.markdown("**Democrats — Top Bigrams (by Heat)**")
            st.dataframe(top_ngrams(left, n=2, topn=15), use_container_width=True, hide_index=True)
        with c4:
            st.markdown("**Republicans — Top Bigrams (by Heat)**")
            st.dataframe(top_ngrams(right, n=2, topn=15), use_container_width=True, hide_index=True)
    else:
        st.info("Party metadata not present yet—add a Party column to unlock this view.")

# ---------- ANOMALY RADAR ----------
st.markdown("---")
st.subheader("📈 Anomaly Radar (vs 7-day baseline)")
if "Date" in df.columns and df["Date"].notna().any():
    maxd = df["Date"].max()
    baseline = df[(df["Date"] >= maxd - pd.Timedelta(days=7)) & (df["Date"] < maxd - pd.Timedelta(days=1))]
    window   = df[df["Date"] >= maxd - pd.Timedelta(days=1)]

    base_tbl = top_ngrams(baseline, n=2, topn=9999).set_index("gram") if len(baseline) else pd.DataFrame(columns=["gram","count","avg_Heat"]).set_index("gram")
    win_tbl  = top_ngrams(window,   n=2, topn=9999).set_index("gram") if len(window)   else pd.DataFrame(columns=["gram","count","avg_Heat"]).set_index("gram")

    merged = win_tbl.join(base_tbl, how="left", lsuffix="_now", rsuffix="_base").fillna({"avg_Heat_base": 0, "count_base": 0})
    merged["Heat_lift"] = merged["avg_Heat_now"] - merged["avg_Heat_base"]

    st.dataframe(
        merged.sort_values("Heat_lift", ascending=False).head(20).reset_index().rename(columns={"index": "bigram"}),
        use_container_width=True, hide_index=True
    )
else:
    st.info("Need Date to compute anomalies.")
