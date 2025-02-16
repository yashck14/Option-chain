import json
import os
import time

import matplotlib.pyplot as plt
import pandas as pd
import requests

def setup_directory(directory_name="market_insights"):
    if not os.path.exists(directory_name):
        os.makedirs(directory_name)

def configure_request_session():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/option-chain",
        "Connection": "keep-alive"
    })
    return session

def retrieve_market_snapshot(api_endpoint, stock_symbol):
    try:
        session = configure_request_session()
        session.get("https://www.nseindia.com", timeout=5)
        response = session.get(api_endpoint, timeout=10)
        response.raise_for_status()
        snapshot = response.json()
        
        file_path = f"market_insights/{stock_symbol}_data.json"
        with open(file_path, "w") as file:
            json.dump(snapshot, file, indent=4)
        
        print(f"\nData successfully retrieved and saved for {stock_symbol} at {file_path}")
        return snapshot
    except requests.exceptions.RequestException as err:
        print(f"Data retrieval failed for {stock_symbol}: {err}")
        return None

def process_option_chain(option_data, expiry_date):
    options = option_data.get("records", {}).get("data", [])
    current_price = option_data.get("records", {}).get("underlyingValue")
    
    if current_price is None:
        print("Market price unavailable.")
        return None
    
    extracted_data = []
    for option in options:
        if option.get("expiryDate") == expiry_date:
            extracted_data.append({
                "Strike": option.get("strikePrice"),
                "Call OI": option.get("CE", {}).get("openInterest", 0),
                "Call LTP": option.get("CE", {}).get("lastPrice", 0),
                "Put OI": option.get("PE", {}).get("openInterest", 0),
                "Put LTP": option.get("PE", {}).get("lastPrice", 0),
            })
    
    df = pd.DataFrame(extracted_data).sort_values("Strike").reset_index(drop=True)
    
    nearest_idx = (df["Strike"] - current_price).abs().idxmin()
    df_filtered = df.iloc[max(nearest_idx - 5, 0): min(nearest_idx + 6, len(df))].reset_index()
    
    print(f"\nExpiry: {expiry_date} | Market Price: {current_price}")
    print("\nRelevant Option Chain Data:")
    print(df_filtered.to_string(index=False))
    
    return df_filtered

def plot_open_interest(df, stock_symbol):
    plt.figure(figsize=(15, 8))
    plt.plot(df["Strike"], df["Call OI"], marker="D", linestyle="-", color="blue", linewidth=2.5, markersize=7, label="Call OI")
    plt.plot(df["Strike"], df["Put OI"], marker="o", linestyle="--", color="red", linewidth=2.5, markersize=7, label="Put OI")
    plt.xlabel("Strike Price", fontsize=14, fontweight='bold')
    plt.ylabel("Open Interest", fontsize=14, fontweight='bold')
    plt.title(f"{stock_symbol} - Open Interest Movement", fontsize=16, fontweight='bold')
    plt.legend(fontsize=12, loc='upper left')
    plt.grid(True, linestyle="--", alpha=0.7)
    plt.xticks(fontsize=12)
    plt.yticks(fontsize=12)
    plt.show()

def run():
    setup_directory()
    assets = {"NIFTY": "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY", 
              "HDFCBANK": "https://www.nseindia.com/api/option-chain-equities?symbol=HDFCBANK"}
    
    while True:
        for stock_symbol, api_endpoint in assets.items():
            data = retrieve_market_snapshot(api_endpoint, stock_symbol)
            if data:
                expiry = data["records"]["expiryDates"][0]
                df = process_option_chain(data, expiry)
                if df is not None:
                    plot_open_interest(df, stock_symbol)
        
        print("\nWaiting 3 minutes before next update...")
        time.sleep(180)

if __name__ == "__main__":
    run()
