import streamlit as st
import pandas as pd
from datetime import datetime
import time
import smtplib
from email.mime.text import MIMEText
import requests
import json

# 1. SETUP PAGE CONFIGURATION
st.set_page_config(page_title="Meeting Room Booking", layout="wide")
st.title("🏢 Meeting Room Booking")

# 2. DEFINE DATABASE FUNCTION (WITH DATE NORMALIZATION)
def get_booking_data():
    try:
        base_url = st.secrets["GSHEET_URL"].split("/edit")[0]
        csv_url = f"{base_url}/export?format=csv&nocache={int(time.time())}"
        df = pd.read_csv(csv_url)
        if df.empty or len(df.columns) == 0:
            return pd.DataFrame(columns=["Date", "Time Slot", "Room", "Booked By", "Purpose", "Status"])
        df.columns = df.columns.str.strip()
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()
        
        # Standardize Date Format to DD/MM/YYYY
        def normalize_date(d):
            try:
                if "-" in d and len(d.split('-')[0]) == 4:
                    return datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m/%Y")
                return d
            except: return d
        df["Date"] = df["Date"].apply(normalize_date)
        return df
    except Exception:
        return pd.DataFrame(columns=["Date", "Time Slot", "Room", "Booked By", "Purpose", "Status"])

df_bookings = get_booking_data()

# 3. EMAIL SYSTEM (AS PER YOUR ORIGINAL)
try:
    SENDER_EMAIL = st.secrets["EMAIL_USER"]
    SENDER_PASSWORD = st.secrets["EMAIL_PASSWORD"]
    RECIPIENT_LIST = [email.strip() for email in st.secrets["ALL_STAFF_EMAIL"].split(",")]
except KeyError:
    st.error("❌ Secrets Configuration Missing.")
    st.stop()

def send_email_alert(subject, body):
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = ", ".join(RECIPIENT_LIST)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECIPIENT_LIST, msg.as_string())
    except: pass

# 4. SYSTEM CONSTANTS & TABS
rooms = ["Meeting Room SOM", "Meeting Room KGO"]
time_options = [f"{h:02d}:{m:02d} {'AM' if h < 12 else 'PM'}" for h in range(8, 19) for m in [0, 30] if not (h == 18 and m == 30)]
tab1, tab2, tab3 = st.tabs(["📝 Reserve a Room", "❌ Cancel a Booking", "🔄 Reschedule a Booking"])
today_obj = datetime.today()

def is_past_date(date_string):
    try: return datetime.strptime(date_string, "%d/%m/%Y").date() < today_obj.date()
    except: return False

# --- INSERT YOUR ORIGINAL TAB 1, 2, AND 3 LOGIC HERE ---
# (Keep your existing booking, cancel, and reschedule logic exactly as you have it)

# 6. LIVE REFRESHED DASHBOARD FEED (WITH DYNAMIC LABELS)
st.markdown("---")
st.subheader("📋 Active Schedule Table Feed")
if not df_bookings.empty:
    # Use your existing filtering logic
    display_board = df_bookings[~df_bookings["Date"].apply(is_past_date)].copy()
    
    def format_row(row):
        purpose_text = str(row["Purpose"])
        status = str(row["Status"]).strip().lower()
        
        # Reschedule Logic
        if "[RESCHED_TO:" in purpose_text:
            target_date = purpose_text.split("[RESCHED_TO:")[1].replace("]", "").strip()
            return {**row, "Status/Notes": f"🔄 Rescheduled to {target_date}"}
        # Cancel Logic
        if status == "cancelled":
            return {**row, "Status/Notes": "❌ Cancelled & Now Open"}
        # Default Logic
        return {**row, "Status/Notes": "🟢 Active & Secured"}

    formatted_data = display_board.apply(format_row, axis=1, result_type="expand")
    # Clean up column order to show Status/Notes instead of raw Status
    st.dataframe(formatted_data[["Date", "Time Slot", "Room", "Booked By", "Purpose", "Status/Notes"]], use_container_width=True, hide_index=True)
else:
    st.info("System database is empty.")
