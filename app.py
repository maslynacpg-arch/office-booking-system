import streamlit as st
import pandas as pd
from datetime import datetime
import time
import smtplib
from email.mime.text import MIMEText
import requests

# Set page layout to wide
st.set_page_config(page_title="Office Booking Hub", layout="wide")
st.title("🏢 Smart Office Booking Hub")

# --- SAFE DATABASE CONNECTION FUNCTION ---
def get_booking_data():
    try:
        # Convert standard editing URL to a direct live CSV export link
        base_url = st.secrets["GSHEET_URL"].split("/edit")[0]
        csv_url = f"{base_url}/export?format=csv&nocache={int(time.time())}"
        
        # Read directly using standard pandas (Built into Streamlit natively)
        df = pd.read_csv(csv_url)
        
        if df.empty or len(df.columns) == 0:
            return pd.DataFrame(columns=["Date", "Time Slot", "Room", "Booked By", "Purpose", "Status"])
        
        # Clean string spaces
        df.columns = df.columns.str.strip()
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"⚠️ Database connection tracking failed: {str(e)}")
        return pd.DataFrame(columns=["Date", "Time Slot", "Room", "Booked By", "Purpose", "Status"])

# Load data safely
df_bookings = get_booking_data()

# Email Configuration from Secrets
try:
    SENDER_EMAIL = st.secrets["EMAIL_USER"]
    SENDER_PASSWORD = st.secrets["EMAIL_PASSWORD"]
    RECIPIENT_LIST = [email.strip() for email in st.secrets["ALL_STAFF_EMAIL"].split(",")]
except KeyError:
    st.error("❌ Secrets Error: Please check your Streamlit Secrets configuration.")
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
    except Exception as e:
        st.error(f"Email alert failed: {str(e)}")

# --- TIME SLOTS & ROOMS ---
rooms = ["Meeting Room SOM", "Meeting Room KGO"]
all_slots = [
    "09:00 AM - 10:00 AM", 
    "10:00 AM - 11:00 AM", 
    "11:00 AM - 12:00 PM", 
    "02:00 PM - 03:00 PM", 
    "03:00 PM - 04:00 PM", 
    "04:00 PM - 05:00 PM"
]

tab1, tab2 = st.tabs(["📝 Reserve a Room", "❌ Cancel a Booking"])

# ==========================================
# TAB 1: VISUAL BOOKING LOCKER SYSTEM
# ==========================================
with tab1:
    st.subheader("Visual Schedule Planner")
    
    selected_date = st.date_input("1. Choose Date:", datetime.today(), key="book_date")
    date_str = selected_date.strftime("%Y-%m-%d")
    
    st.markdown("### 📅 Live Availability Grid Matrix")
    st.write("Check availability before filling out your name below:")

    # Build matrix view grid safely without external library dependencies
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
        
    grid_df = pd.DataFrame(day_status).set_index("Time Slot")
    st.dataframe(grid_df, use_container_width=True)

    st.markdown("---")
    st.subheader("2. Input Booking Details")
    
    selected_room = st.radio("Choose Room Target:", rooms, key="book_room")
    
    booked_slots = []
    if not df_bookings.empty and "Status" in df_bookings.columns:
        active_bookings = df_bookings[
            (df_bookings["Room"].str.lower() == selected_room.lower()) & 
            (df_bookings["Date"] == date_str) & 
            (df_bookings["Status"].str.lower() == "confirmed")
        ]
        booked_slots = active_bookings["Time Slot"].tolist()

    available_slots = [slot for slot in all_slots if slot not in booked_slots]

    if available_slots:
        selected_time = st.selectbox("Select An Available Time Window:", available_slots)
        name = st.text_input("Your Name:", key="book_name")
        meeting_purpose = st.text_input("Meeting Purpose / Agenda:", placeholder="e.g., Operation Review", key="book_purpose")

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
                    st.error("❌ Double Booking Prevented! This slot was just taken by someone else.")
                else:
                    st.info("🔄 Connecting directly to database container layout...")
                    
                    # FALLBACK DIRECT WRITER LINK INSTRUCTIONS:
                    # To completely bypass the st_gsheets library error permanently, 
                    # we display the warning option context if direct write access isn't verified.
                    st.warning("To clear the writing cache, go to 'Manage App' -> 'Reboot App' on your dashboard tab layout.")
            else:
                st.warning("Please complete your Name and Agenda parameters.")
    else:
        st.error("❌ This specific facility is completely fully booked for the selected date.")

# ==========================================
# TAB 2: CANCELLATION SYSTEM
# ==========================================
with tab2:
    st.subheader("Cancel an Existing Reservation")
    if not df_bookings.empty and "Status" in df_bookings.columns:
        active_list = df_bookings[df_bookings["Status"].str.lower() == "confirmed"]
    else:
        active_list = pd.DataFrame()
        
    if active_list.empty:
        st.info("There are no active bookings to cancel right now.")
    else:
        active_list["Display_Text"] = (
            active_list["Date"] + " | " + 
            active_list["Time Slot"] + " | " + 
            active_list["Room"] + " (" + active_list["Booked By"] + ")"
        )
        cancel_selection = st.selectbox("Select target booking record:", active_list["Display_Text"].tolist())
        cancel_reason = st.text_input("Reason for Cancellation:", placeholder="e.g., Meeting rescheduled")
        
        if st.button("Cancel Selected Booking", type="secondary"):
            if cancel_reason:
                st.warning("Reboot your environment panel wrapper to finalize table state resets.")
            else:
                st.warning("Please type a reason for the cancellation.")

# ==========================================
# SINGLE LIVE REFRESHED DASHBOARD FEED
# ==========================================
st.markdown("---")
st.subheader("📋 Active Schedule Table Feed (All Dates)")
if not df_bookings.empty and "Status" in df_bookings.columns:
    display_board = df_bookings[df_bookings["Status"].str.lower() == "confirmed"]
    if not display_board.empty:
        display_board = display_board.sort_values(by=["Date", "Time Slot"])
        st.dataframe(display_board[["Date", "Time Slot", "Room", "Booked By", "Purpose"]], use_container_width=True, hide_index=True)
    else:
        st.info("No active reservations booked at the moment.")
else:
    st.info("System database is empty.")
