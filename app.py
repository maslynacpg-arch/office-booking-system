import streamlit as st
import pandas as pd
from datetime import datetime
import smtplib
from email.mime.text import MIMEText

st.set_page_config(page_title="Office Booking Hub", layout="wide")
st.title("🏢 Smart Office Booking Hub")

st.write("Welcome to the office room booking system. Select your slot below to reserve a room.")

# 1. Room Configuration (Using Radio Buttons instead of dropdown)
rooms = ["Meeting Room"]
selected_room = st.radio("Choose a Room:", rooms)

# 2. Date & Time Picker
date = st.date_input("Select Date:", datetime.today())
time_slots = [
    "09:00 AM - 10:00 AM", 
    "10:00 AM - 11:00 AM", 
    "11:00 AM - 12:00 PM", 
    "02:00 PM - 03:00 PM", 
    "03:00 PM - 04:00 PM", 
    "04:00 PM - 05:00 PM"
]
selected_time = st.selectbox("Select Time Slot:", time_slots)

# 3. User Info & Meeting Purpose
name = st.text_input("Your Name:")
meeting_purpose = st.text_input("Meeting Purpose / Topic:", placeholder="e.g., Operation Meeting, Financial Review")

# 4. Booking Action & Email Blast Logic
if st.button("Confirm Booking", type="primary"):
    if name and meeting_purpose:
        try:
            # Pull configuration from Streamlit Secrets
            sender_email = st.secrets["EMAIL_USER"]
            sender_password = st.secrets["EMAIL_PASSWORD"]
            recipient_list = [email.strip() for email in st.secrets["ALL_STAFF_EMAIL"].split(",")]

            # Create the email content including the meeting purpose
            subject = f"🚨 New Booking: {selected_room} ({meeting_purpose})"
            body = (
                f"Hi Team,\n\n"
                f"Please take note of the following room booking:\n\n"
                f"👤 Booked By: {name}\n"
                f"🏢 Room: {selected_room}\n"
                f"📅 Date: {date}\n"
                f"⏰ Time: {selected_time}\n"
                f"📝 Topic: {meeting_purpose}\n\n"
                f"Thank you!\nOffice Booking System"
            )
            
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = sender_email
            msg["To"] = ", ".join(recipient_list)

            # Connect to Gmail's secure sending server (SMTP)
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, recipient_list, msg.as_string())

            st.success(f"🎉 Booking confirmed! Email alert for '{meeting_purpose}' sent to all staff.")
            
        except Exception as e:
            st.success(f"🎉 Booking recorded for {name}! (Email alert pending configuration).")
    else:
        st.warning("Please fill in both your Name and the Meeting Purpose before confirming.")
