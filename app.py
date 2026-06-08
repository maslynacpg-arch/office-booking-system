import streamlit as st
import pandas as pd
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Office Booking Hub", layout="wide")
st.title("🏢 Smart Office Booking Hub")

st.write("Welcome to the office room booking system. Select your slot below to reserve a room.")

# Connect to Google Sheets using the URL from Secrets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Read existing bookings; clear cache every time to ensure live updates
    existing_data = conn.read(spreadsheet=st.secrets["GSHEET_URL"], ttl=0)
    df_bookings = pd.DataFrame(existing_data)
except Exception as e:
    df_bookings = pd.DataFrame(columns=["Date", "Time Slot", "Room", "Booked By", "Purpose"])

# 1. Room Configuration
rooms = ["Meeting Room"]
selected_room = st.radio("Choose a Room:", rooms)

# 2. Date Picker
selected_date = st.date_input("Select Date:", datetime.today())
date_str = selected_date.strftime("%Y-%m-%d")

# All available time slots
all_slots = [
    "09:00 AM - 10:00 AM", 
    "10:00 AM - 11:00 AM", 
    "11:00 AM - 12:00 PM", 
    "02:00 PM - 03:00 PM", 
    "03:00 PM - 04:00 PM", 
    "04:00 PM - 05:00 PM"
]

# Find slots already booked for this specific room and date
booked_slots = []
if not df_bookings.empty:
    # Clean up column names to prevent matching issues
    df_bookings.columns = df_bookings.columns.str.strip()
    
    # Filter bookings matching the selected room and date
    filtered = df_bookings[
        (df_bookings["Room"].astype(str).str.strip() == selected_room) & 
        (df_bookings["Date"].astype(str).str.strip() == date_str)
    ]
    booked_slots = filtered["Time Slot"].tolist()

# Filter out the booked slots from the dropdown list
available_slots = [slot for slot in all_slots if slot not in booked_slots]

# 3. Time Picker Dashboard Layout
if available_slots:
    selected_time = st.selectbox("Select Available Time Slot:", available_slots)
else:
    st.error("❌ All time slots for this room are fully booked on this day. Please select another date or room.")
    selected_time = None

# 4. User Info & Meeting Purpose
name = st.text_input("Your Name:")
meeting_purpose = st.text_input("Meeting Purpose / Topic:", placeholder="e.g., Operation Meeting, Financial Review")

# 5. Booking Action & Email Blast Logic
if st.button("Confirm Booking", type="primary"):
    if not selected_time:
        st.error("Cannot confirm booking. No available time slots.")
    elif name and meeting_purpose:
        try:
            # A. Prepare data for Google Sheets
            new_booking = pd.DataFrame([{
                "Date": date_str,
                "Time Slot": selected_time,
                "Room": selected_room,
                "Booked By": name,
                "Purpose": meeting_purpose
            }])
            
            # Append to current data and update sheet
            updated_df = pd.concat([df_bookings, new_booking], ignore_index=True)
            conn.update(spreadsheet=st.secrets["GSHEET_URL"], data=updated_df)
            
            # B. Trigger the working Email Blast
            sender_email = st.secrets["EMAIL_USER"]
            sender_password = st.secrets["EMAIL_PASSWORD"]
            recipient_list = [email.strip() for email in st.secrets["ALL_STAFF_EMAIL"].split(",")]

            subject = f"🚨 New Booking: {selected_room} ({meeting_purpose})"
            body = (
                f"Hi Team,\n\n"
                f"Please take note of the following room booking:\n\n"
                f"👤 Booked By: {name}\n"
                f"🏢 Room: {selected_room}\n"
                f"📅 Date: {date_str}\n"
                f"⏰ Time: {selected_time}\n"
                f"📝 Topic: {meeting_purpose}\n\n"
                f"Thank you!\nOffice Booking System"
            )
            
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = sender_email
            msg["To"] = ", ".join(recipient_list)

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, recipient_list, msg.as_string())

            st.success(f"🎉 Booking confirmed! Logged to database and email alert sent to all staff.")
            st.balloons()
            
        except Exception as e:
            st.error(f"Something went wrong: {str(e)}")
    else:
        st.warning("Please fill in both your Name and the Meeting Purpose before confirming.")

# 6. View Live Calendar/Schedule Board
st.markdown("---")
st.subheader("📅 Today's Live Schedule Status")
if not df_bookings.empty:
    # Filter to display only today's bookings on screen for easy reading
    today_str = datetime.today().strftime("%Y-%m-%d")
    today_df = df_bookings[df_bookings["Date"] == today_str]
    if not today_df.empty:
        st.dataframe(today_df[["Time Slot", "Room", "Booked By", "Purpose"]], use_container_width=True, hide_index=True)
    else:
        st.info("No bookings recorded for today yet.")
else:
    st.info("No bookings recorded in the system yet.")
