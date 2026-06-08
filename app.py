import streamlit as st
import pandas as pd
from datetime import datetime
import time
import smtplib
from email.mime.text import MIMEText
import requests
import json

# 1. SETUP PAGE CONFIGURATION FIRST
st.set_page_config(page_title="Office Booking Hub", layout="wide")
st.title("🏢 Smart Office Booking Hub")

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

# Load data safely
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
    except Exception:
        pass

# 4. DEFINE FIXED SYSTEM CONSTANTS
rooms = ["Meeting Room SOM", "Meeting Room KGO"]
all_slots = [
    "09:00 AM - 10:00 AM", "10:00 AM - 11:00 AM", "11:00 AM - 12:00 PM", 
    "02:00 PM - 03:00 PM", "03:00 PM - 04:00 PM", "04:00 PM - 05:00 PM"
]

# 5. CREATE THE TABS SYSTEM BEFORE USING THEM
tab1, tab2 = st.tabs(["📝 Reserve a Room", "❌ Cancel a Booking"])

# ==========================================
# TAB 1: VISUAL BOOKING SYSTEM
# ==========================================
with tab1:
    st.subheader("Visual Schedule Planner")
    selected_date = st.date_input("1. Choose Date:", datetime.today(), key="book_date")
    date_str = selected_date.strftime("%Y-%m-%d")
    
    st.markdown("### 📅 Live Availability Calendar Grid")
    day_status = []
    for slot in all_slots:
        row_status = {"Time Slot": slot}
        for room in rooms:
            if not df_bookings.empty and "Status" in df_bookings.columns:
                match = df_bookings[
                    (df_bookings["Date"] == date_str) & 
                    (df_bookings["Room"].str.lower() == room.lower()) & 
                    (df_bookings["Time Slot"].str.lower() == slot.lower()) & 
                    (df_bookings["Status"].str.lower() == "confirmed")
                ]
                if not match.empty:
                    row_status[room] = f"🛑 Taken by {match.iloc[0]['Booked By']}"
                else:
                    row_status[room] = "🟢 Available"
            else:
                row_status[room] = "🟢 Available"
        day_status.append(row_status)
        
    st.dataframe(pd.DataFrame(day_status).set_index("Time Slot"), use_container_width=True)

    st.markdown("---")
    st.subheader("2. Input Booking Details")
    selected_room = st.radio("Choose Room Target:", rooms, key="book_room")
    
    booked_slots = []
    if not df_bookings.empty and "Status" in df_bookings.columns:
        booked_slots = df_bookings[
            (df_bookings["Room"].str.lower() == selected_room.lower()) & 
            (df_bookings["Date"] == date_str) & 
            (df_bookings["Status"].str.lower() == "confirmed")
        ]["Time Slot"].tolist()

    available_slots = [slot for slot in all_slots if slot not in booked_slots]

    if available_slots:
        selected_time = st.selectbox("Select An Available Time Window:", available_slots)
        name = st.text_input("Your Name:", key="book_name")
        meeting_purpose = st.text_input("Meeting Purpose / Agenda:", key="book_purpose")

        if st.button("Confirm Reservation Securely", type="primary"):
            if name and meeting_purpose:
                df_latest = get_booking_data()
                if not df_latest.empty and "Status" in df_latest.columns:
                    double_check = df_latest[
                        (df_latest["Room"].str.lower() == selected_room.lower()) & 
                        (df_latest["Date"] == date_str) & 
                        (df_latest["Time Slot"].str.lower() == selected_time.lower()) & 
                        (df_latest["Status"].str.lower() == "confirmed")
                    ]
                else:
                    double_check = pd.DataFrame()
                
                if not double_check.empty:
                    st.error("❌ Double Booking Prevented!")
                else:
                    payload = {
                        "Date": date_str,
                        "Time_Slot": selected_time,
                        "Room": selected_room,
                        "Booked_By": name,
                        "Purpose": meeting_purpose,
                        "Status": "Confirmed"
                    }
                    response = requests.post(st.secrets["SCRIPT_URL"], data=json.dumps(payload))
                    
                    if response.status_code == 200:
                        st.success("🎉 Booking recorded successfully!")
                        send_email_alert(f"🏢 Confirmed: {selected_room}", f"Details:\n\n👤 Name: {name}\n📅 Date: {date_str}\n⏰ Time: {selected_time}")
                        st.balloons()
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("Failed writing data to Google Engine connection endpoints.")
            else:
                st.warning("Please fill out all identity fields.")
    else:
        st.error("❌ Fully booked for this date.")

# ==========================================
# TAB 2: CANCELLATION SYSTEM
# ==========================================
with tab2:
    st.subheader("Cancel an Existing Reservation")
    if not df_bookings.empty and "Status" in df_bookings.columns:
        active_list = df_bookings[df_bookings["Status"].str.lower() == "confirmed"]
        if not active_list.empty:
            active_list["Display_Text"] = active_list["Date"] + " | " + active_list["Time Slot"] + " | " + active_list["Room"] + " (" + active_list["Booked By"] + ")"
            cancel_selection = st.selectbox("Select booking to release:", active_list["Display_Text"].tolist())
            cancel_reason = st.text_input("Reason for Cancellation:", placeholder="e.g., Meeting rescheduled / postponed")
            
            if st.button("Submit Cancellation Request", type="secondary"):
                if cancel_reason:
                    selected_row =
