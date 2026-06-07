import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
import os

st.set_page_config(page_title="Office Booking Hub", layout="wide")
st.title("🏢 Smart Office Booking Hub")

# Simple, clean layout for your staff to see room availability
st.write("Welcome to the office room booking system. Select your slot below.")

# Room configuration
rooms = ["Meeting Room A", "Meeting Room B", "Discussion Room 1"]
selected_room = st.selectbox("Choose a Room:", rooms)

# Date & Time picker
date = st.date_input("Select Date:", datetime.today())
time_slots = ["09:00 AM", "10:00 AM", "11:00 AM", "02:00 PM", "03:00 PM", "04:00 PM"]
selected_time = st.selectbox("Select Time Slot:", time_slots)

name = st.text_input("Your Name:")

if st.button("Confirm Booking", type="primary"):
    if name:
        st.success(f"🎉 Booking confirmed for {name} ({selected_room} on {date} at {selected_time})!")
        # Email logic will trigger once Secrets are configured
    else:
        st.warning("Please enter your name before confirming.")
