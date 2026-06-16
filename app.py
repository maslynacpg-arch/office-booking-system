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
        df.columns = df.columns.str.strip()
        
        if df.empty:
            return pd.DataFrame(columns=["Date", "Time Slot", "Room", "Booked By", "Purpose", "Status"])
        
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            
        def normalize_date(d):
            try:
                if "-" in d: return datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m/%Y")
                return d
            except: return d
            
        df["Date"] = df["Date"].apply(normalize_date)
        return df
    except Exception:
        return pd.DataFrame(columns=["Date", "Time Slot", "Room", "Booked By", "Purpose", "Status"])

# Initialize data globally
df_bookings = get_booking_data()
today_obj = datetime.today()

# 3. HELPER FUNCTIONS
def is_past_date(date_string):
    try:
        return datetime.strptime(date_string, "%d/%m/%Y").date() < today_obj.date()
    except: return False

def send_email_alert(subject, body):
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = st.secrets["EMAIL_USER"]
        msg["To"] = st.secrets["ALL_STAFF_EMAIL"]
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(st.secrets["EMAIL_USER"], st.secrets["EMAIL_PASSWORD"])
            server.sendmail(st.secrets["EMAIL_USER"], st.secrets["ALL_STAFF_EMAIL"], msg.as_string())
    except: pass

# 4. TABS
tab1, tab2, tab3 = st.tabs(["📝 Reserve a Room", "❌ Cancel a Booking", "🔄 Reschedule a Booking"])

with tab1:
    st.subheader("Reserve a Room")
    selected_date = st.date_input("Choose Date:", datetime.today(), format="DD/MM/YYYY")

with tab2:
    st.subheader("Cancel an Existing Reservation")
    if not df_bookings.empty and "Status" in df_bookings.columns:
        active_list = df_bookings[df_bookings["Status"].str.lower() == "confirmed"].copy()
        active_list = active_list[~active_list["Date"].apply(is_past_date)]
        if not active_list.empty:
            active_list["Display_Text"] = active_list["Date"] + " | " + active_list["Time Slot"] + " | " + active_list["Room"]
            st.selectbox("Select booking to release:", active_list["Display_Text"].tolist(), key="cancel_select")

with tab3:
    st.subheader("Reschedule an Existing Booking")
    if not df_bookings.empty and "Status" in df_bookings.columns:
        resched_list = df_bookings[df_bookings["Status"].str.lower() == "confirmed"].copy()
        resched_list = resched_list[~resched_list["Date"].apply(is_past_date)]
        if not resched_list.empty:
            resched_list["Display_Text"] = resched_list["Date"] + " | " + resched_list["Time Slot"] + " | " + resched_list["Room"]
            st.selectbox("Choose Meeting to Change:", resched_list["Display_Text"].tolist(), key="resched_select")
            st.date_input("Choose New Date:", datetime.today(), format="DD/MM/YYYY")

# 5. DASHBOARD FEED
st.markdown("---")
st.subheader("📋 Active Schedule Table Feed")
if not df_bookings.empty:
    display_board = df_bookings[~df_bookings["Date"].apply(is_past_date)].copy()
    def format_row(row):
        purpose = str(row["Purpose"])
        if "[RESCHED_TO:" in purpose:
            target = purpose.split("[RESCHED_TO:")[1].replace("]", "")
            return {**row, "Status/Notes": f"🔄 Rescheduled to {target}"}
        return {**row, "Status/Notes": "🟢 Active"}
    
    formatted_data = display_board.apply(format_row, axis=1, result_type="expand")
    st.dataframe(formatted_data, use_container_width=True, hide_index=True)
