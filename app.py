import streamlit as st
import pandas as pd
from datetime import datetime
import time
import requests
import json
from email.mime.text import MIMEText
import smtplib

st.set_page_config(page_title="Meeting Room Booking", layout="wide")
st.title("🏢 Meeting Room Booking")

# --- DATABASE & HELPERS ---
def get_booking_data():
    try:
        base_url = st.secrets["GSHEET_URL"].split("/edit")[0]
        csv_url = f"{base_url}/export?format=csv&nocache={int(time.time())}"
        df = pd.read_csv(csv_url)
        df.columns = df.columns.str.strip()
        return df.fillna("")
    except: return pd.DataFrame(columns=["Date", "Time Slot", "Room", "Booked By", "Purpose", "Status"])

df_bookings = get_booking_data()
today_obj = datetime.today()

def is_past_date(date_string):
    try:
        # Handles both YYYY-MM-DD and DD/MM/YYYY
        fmt = "%Y-%m-%d" if "-" in date_string else "%d/%m/%Y"
        return datetime.strptime(date_string, fmt).date() < today_obj.date()
    except: return False

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["📝 Reserve", "❌ Cancel", "🔄 Reschedule"])

with tab1:
    selected_date = st.date_input("1. Choose Date:", datetime.today(), format="DD/MM/YYYY")
    # ... (Your existing timeline logic here)

with tab2:
    st.subheader("Cancel an Existing Reservation")
    if not df_bookings.empty:
        # Fix: Filter correctly and check if empty
        active_list = df_bookings[df_bookings["Status"].str.lower() == "confirmed"].copy()
        active_list = active_list[~active_list["Date"].apply(is_past_date)]
        
        if not active_list.empty:
            active_list["Display_Text"] = active_list["Date"] + " | " + active_list["Time Slot"] + " | " + active_list["Room"]
            cancel_selection = st.selectbox("Select booking to release:", active_list["Display_Text"].tolist())
            # ... (Rest of cancel logic)
        else: st.info("No active bookings to cancel.")

with tab3:
    st.subheader("Reschedule an Existing Booking")
    if not df_bookings.empty:
        resched_list = df_bookings[df_bookings["Status"].str.lower() == "confirmed"].copy()
        resched_list = resched_list[~resched_list["Date"].apply(is_past_date)]
        
        if not resched_list.empty:
            resched_list["Display_Text"] = resched_list["Date"] + " | " + resched_list["Time Slot"] + " | " + resched_list["Room"]
            selected_meeting_text = st.selectbox("1. Choose Meeting:", resched_list["Display_Text"].tolist())
            # ... (Rest of reschedule logic)
        else: st.info("No active bookings available to reschedule.")

# --- DASHBOARD ---
st.markdown("---")
st.subheader("📋 Active Schedule Table Feed")
if not df_bookings.empty:
    display_board = df_bookings[~df_bookings["Date"].apply(is_past_date)].copy()
    st.dataframe(display_board, use_container_width=True)
