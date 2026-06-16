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

# 2. DEFINE DATABASE FUNCTION
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
        return df
    except Exception:
        return pd.DataFrame(columns=["Date", "Time Slot", "Room", "Booked By", "Purpose", "Status"])

df_bookings = get_booking_data()

# 3. DEFINE EMAIL SYSTEM
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
    except Exception: pass

# 4. CONSTANTS & HELPERS
rooms = ["Meeting Room SOM", "Meeting Room KGO"]
time_options = [f"{h:02d}:{m:02d} {'AM' if h < 12 else 'PM'}" for h in range(8, 19) for m in [0, 30] if not (h == 18 and m == 30)]
today_obj = datetime.today()

def is_past_date(date_string):
    try:
        booking_date = datetime.strptime(date_string.replace("-", "/"), "%d/%m/%Y")
        return booking_date.date() < today_obj.date()
    except: return False

# 5. TABS
tab1, tab2, tab3 = st.tabs(["📝 Reserve", "❌ Cancel", "🔄 Reschedule"])

with tab1:
    selected_date = st.date_input("1. Choose Date:", datetime.today(), format="DD/MM/YYYY")
    date_str = selected_date.strftime("%d/%m/%Y")
    # ... (Keep existing timeline logic here)

with tab2:
    st.subheader("Cancel an Existing Reservation")
    active_list = df_bookings[df_bookings["Status"].str.lower() == "confirmed"].copy()
    active_list = active_list[~active_list["Date"].apply(is_past_date)]
    if not active_list.empty:
        active_list["Display_Text"] = active_list["Date"] + " | " + active_list["Time Slot"] + " | " + active_list["Room"]
        cancel_selection = st.selectbox("Select booking to release:", active_list["Display_Text"].tolist())
        # ... (Keep existing cancellation logic here)

with tab3:
    st.subheader("Reschedule an Existing Booking")
    resched_list = df_bookings[df_bookings["Status"].str.lower() == "confirmed"].copy()
    resched_list = resched_list[~resched_list["Date"].apply(is_past_date)]
    if not resched_list.empty:
        selected_meeting_text = st.selectbox("1. Choose Meeting:", resched_list["Display_Text"].tolist())
        selected_meeting_row = resched_list[resched_list["Display_Text"] == selected_meeting_text].iloc[0]
        new_date = st.date_input("Choose New Date:", datetime.today(), format="DD/MM/YYYY")
        new_date_str = new_date.strftime("%d/%m/%Y")
        # ... (Keep existing reschedule logic here)

# 6. DASHBOARD FEED (THE "RESCHEDULED" LABEL LOGIC)
st.markdown("---")
st.subheader("📋 Active Schedule Table Feed")
if not df_bookings.empty:
    display_board = df_bookings.copy()
    display_board = display_board[~display_board["Date"].apply(is_past_date)]
    def format_row(row):
        if str(row["Status"]).lower() == "cancelled" and "[RESCHED_TO:" in str(row["Purpose"]):
            target = row["Purpose"].split("[RESCHED_TO:")[1].replace("]", "")
            return {"Date": f"~~{row['Date']}~~", "Status/Notes": f"🔄 Rescheduled to {target}"}
        # ... (Keep existing active/cancelled formatting)
    st.dataframe(display_board, use_container_width=True)
