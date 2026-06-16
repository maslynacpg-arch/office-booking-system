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

# 2. DATABASE FUNCTION
def get_booking_data():
    try:
        base_url = st.secrets["GSHEET_URL"].split("/edit")[0]
        csv_url = f"{base_url}/export?format=csv&nocache={int(time.time())}"
        df = pd.read_csv(csv_url)
        df.columns = df.columns.str.strip()
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()
        return df
    except Exception:
        return pd.DataFrame(columns=["Date", "Time Slot", "Room", "Booked By", "Purpose", "Status"])

df_bookings = get_booking_data()
today_obj = datetime.today()

# 3. HELPER FUNCTIONS
def is_past_date(date_string):
    try:
        return datetime.strptime(date_string, "%d/%m/%Y").date() < today_obj.date()
    except: return False

time_options = [f"{h:02d}:{m:02d} {'AM' if h < 12 else 'PM'}" for h in range(8, 19) for m in [0, 30] if not (h == 18 and m == 30)]

# 4. TABS
tab1, tab2, tab3 = st.tabs(["📝 Reserve a Room", "❌ Cancel a Booking", "🔄 Reschedule a Booking"])

with tab1:
    st.subheader("Reserve a Room")
    selected_date = st.date_input("1. Choose Date:", datetime.today(), format="DD/MM/YYYY")

with tab2:
    st.subheader("Cancel an Existing Reservation")
    if not df_bookings.empty:
        active_list = df_bookings[df_bookings["Status"].str.lower() == "confirmed"].copy()
        active_list = active_list[~active_list["Date"].apply(is_past_date)]
        if not active_list.empty:
            active_list["Display_Text"] = active_list["Date"] + " | " + active_list["Time Slot"] + " | " + active_list["Room"]
            st.selectbox("Select booking to release:", active_list["Display_Text"].tolist())

with tab3:
    st.subheader("Reschedule an Existing Booking")
    if not df_bookings.empty:
        resched_list = df_bookings[df_bookings["Status"].str.lower() == "confirmed"].copy()
        resched_list = resched_list[~resched_list["Date"].apply(is_past_date)]
        if not resched_list.empty:
            resched_list["Display_Text"] = resched_list["Date"] + " | " + resched_list["Time Slot"] + " | " + resched_list["Room"]
            st.selectbox("1. Choose Meeting to Change:", resched_list["Display_Text"].tolist())
            st.date_input("Choose New Date:", datetime.today(), format="DD/MM/YYYY")

# 5. DASHBOARD FEED
st.markdown("---")
st.subheader("📋 Active Schedule Table Feed")
if not df_bookings.empty:
    display_board = df_bookings[~df_bookings["Date"].apply(is_past_date)].copy()
    def format_row(row):
        if "[RESCHED_TO:" in str(row["Purpose"]):
            target = row["Purpose"].split("[RESCHED_TO:")[1].replace("]", "")
            return {**row, "Status/Notes": f"🔄 Rescheduled to {target}"}
        return {**row, "Status/Notes": "🟢 Active"}
    formatted_data = display_board.apply(format_row, axis=1, result_type="expand")
    st.dataframe(formatted_data, use_container_width=True, hide_index=True)
