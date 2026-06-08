=import streamlit as st
import pandas as pd
from datetime import datetime, time as datetime_time
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

# 4. DEFINE SYSTEM CONSTANTS
rooms = ["Meeting Room SOM", "Meeting Room KGO"]

# Generate time options from 08:00 AM to 06:00 PM in 30-minute intervals
time_options = []
for hour in range(8, 19):
    for minute in [0, 30]:
        if hour == 18 and minute == 30: 
            break
        period = "AM" if hour < 12 else "PM"
        display_hour = hour if hour <= 12 else hour - 12
        if display_hour == 0: 
            display_hour = 12
        time_options.append(f"{display_hour:02d}:{minute:02d} {period}")

# 5. CREATE THE TABS SYSTEM BEFORE USING THEM
tab1, tab2 = st.tabs(["📝 Reserve a Room", "❌ Cancel a Booking"])

# ==========================================
# TAB 1: VISUAL BOOKING SYSTEM (FLEXIBLE TIME)
# ==========================================
with tab1:
    st.subheader("Visual Schedule Planner")
    selected_date = st.date_input("1. Choose Date:", datetime.today(), key="book_date")
    date_str = selected_date.strftime("%Y-%m-%d")
    
    st.markdown("### 📅 Live Confirmed Bookings for Today")
    # Filter and display current active schedules for the day so users can check conflicts visually
    if not df_bookings.empty and "Status" in df_bookings.columns:
        today_active = df_bookings[
            (df_bookings["Date"] == date_str) & 
            (df_bookings["Status"].str.lower() == "confirmed")
        ]
        if not today_active.empty:
            st.dataframe(today_active[["Time Slot", "Room", "Booked By", "Purpose"]], use_container_width=True, hide_index=True)
        else:
            st.text("🟢 No bookings reserved for this date yet. All times are available!")
    else:
        st.text("🟢 No bookings reserved for this date yet. All times are available!")

    st.markdown("---")
    st.subheader("2. Input Custom Booking Details")
    selected_room = st.radio("Choose Room Target:", rooms, key="book_room")
    
    col1, col2 = st.columns(2)
    with col1:
        start_time = st.selectbox("Select Start Time:", time_options, index=2) # Defaults to 09:00 AM
    with col2:
        end_time = st.selectbox("Select End Time:", time_options, index=4)     # Defaults to 10:00 AM

    custom_time_slot = f"{start_time} - {end_time}"
    name = st.text_input("Your Name:", key="book_name")
    meeting_purpose = st.text_input("Meeting Purpose / Agenda:", key="book_purpose")

    if st.button("Confirm Reservation Securely", type="primary"):
        if name and meeting_purpose:
            # Simple check to ensure start is before end
            start_idx = time_options.index(start_time)
            end_idx = time_options.index(end_time)
            
            if start_idx >= end_idx:
                st.error("❌ Invalid Time Selection: End time must be later than the Start time.")
            else:
                payload = {
                    "Action": "Book",
                    "Date": date_str,
                    "Time_Slot": custom_time_slot,
                    "Room": selected_room,
                    "Booked_By": name,
                    "Purpose": meeting_purpose
                }
                response = requests.post(st.secrets["SCRIPT_URL"], data=json.dumps(payload))
                
                if response.status_code == 200:
                    st.success(f"🎉 Booking recorded successfully for {custom_time_slot}!")
                    send_email_alert(f"🏢 Confirmed: {selected_room}", f"Details:\n\n👤 Name: {name}\n📅 Date: {date_str}\n⏰ Time: {custom_time_slot}\n📝 Purpose: {meeting_purpose}")
                    st.balloons()
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("Failed writing data to Google Engine connection endpoints.")
        else:
            st.warning("Please fill out all identity fields.")

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
                    selected_row = active_list[active_list["Display_Text"] == cancel_selection].iloc[0]
                    c_date = selected_row["Date"]
                    c_slot = selected_row["Time Slot"]
                    c_room = selected_row["Room"]
                    c_name = selected_row["Booked By"]
                    
                    cancel_payload = {
                        "Action": "Cancel",
                        "Date": c
