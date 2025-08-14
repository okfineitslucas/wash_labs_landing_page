# config.py
STREAMS = {
    # For now, all three can point to your test sheet. Swap these URLs when real streams are ready.
    "leaders": "https://docs.google.com/spreadsheets/d/1V6Jtz-mMtltQKhaslIQRZ-AtHGaVo0Fy58KtLAzgKtg/export?format=csv&gid=0",
    "dems":    "https://docs.google.com/spreadsheets/d/1V6Jtz-mMtltQKhaslIQRZ-AtHGaVo0Fy58KtLAzgKtg/export?format=csv&gid=0",
    "reps":    "https://docs.google.com/spreadsheets/d/1V6Jtz-mMtltQKhaslIQRZ-AtHGaVo0Fy58KtLAzgKtg/export?format=csv&gid=0",
}

# Default weights for Heat Index (tweak in UI later)
HEAT = {
    "alpha_likes": 1.0,
    "beta_retweets": 2.0,
    "gamma_replies": 0.5,
    "delta_quotes": 0.5,
    "lambda_decay": 0.12,  # hourly decay; higher = more “now”
}
