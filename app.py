import streamlit as st
import pandas as pd
from datetime import datetime
import time
import smtplib
from email.mime.text import MIMEText

# --- SMART FALLBACK FOR THE GSHEETS LIBRARY ---
try:
    from streamlit_gsheets import GSheetsConnection
    HAS_GSHEETS = True
except ModuleNotFoundError:
    HAS_GSHEETS = False

st.set_page_config(page_title="Office Booking Hub", layout="wide")
st.title("🏢 Smart Office Booking Hub")

# --- DATABASE CONNECTION FUNCTION ---
def get_booking_data():
    try:
        if HAS_GSHEETS:
            conn = st.connection("gsheets", type=GSheetsConnection)
            existing_data = conn.read(spreadsheet=st.secrets["GSHEET_URL"], ttl=0)
            df = pd.DataFrame(existing_data)
        else:
            base_url = st.secrets["GSHEET_URL"].split("/edit")[0]
            csv_url = f"{base_url}/export?format=csv"
            df = pd.read_csv(csv_url)
            
        if df.empty:
            return pd.DataFrame(columns=["Date", "Time Slot", "Room", "Booked By", "Purpose", "Status"])
        
        df.columns = df.columns.str.strip()
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            
        if "Status" not in df.columns:
            df["Status"] = "Confirmed"
        return df
    except Exception:
        return pd.DataFrame(columns=["Date", "Time Slot", "Room", "Booked By", "Purpose", "Status"])

# Load current data
df_bookings = get_booking_data()

# Email Configuration from Secrets
try:
    SENDER_EMAIL = st.secrets["EMAIL_USER"]
    SENDER_PASSWORD = st.secrets["EMAIL_PASSWORD"]
    RECIPIENT_LIST = [email.strip() for email in st.secrets["ALL_STAFF_EMAIL"].split(",")]
except KeyError:
    st.error("❌ Secrets Error: Please check your Streamlit Secrets keys configuration.")
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
        st.error(f"Email alert failed to send: {str(e)}")

# --- SYSTEM CONFIGURATION ---
rooms = ["Meeting Room A", "Meeting Room B", "Discussion Room 1"]
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
# TAB 1: BOOKING SYSTEM
# ==========================================
with tab1:
    st.subheader("New Reservation")
    selected_room = st.radio("Choose a Room:", rooms, key="book_room")
    selected_date = st.date_input("Select Date:", datetime.today(), key="book_date")
    date_str = selected_date.strftime("%Y-%m-%d")

    booked_slots = []
    if not df_bookings.empty:
        active_bookings = df_bookings[
            (df_bookings["Room"] == selected_room) & 
            (df_bookings["Date"] == date_str) & 
            (df_bookings["Status"] == "Confirmed")
        ]
        booked_slots = active_bookings["Time Slot"].tolist()

    available_slots = [slot for slot in all_slots if slot not in booked_slots]

    if available_slots:
        selected_time = st.selectbox("Select Available Time Slot:", available_slots)
        name = st.text_input("Your Name:", key="book_name")
        meeting_purpose = st.text_input("Meeting Purpose:", placeholder="e.g., Operation Review", key="book_purpose")

        if st.button("Confirm Booking", type="primary"):
            if name and meeting_purpose:
                df_latest = get_booking_data()
                double_check = df_latest[
                    (df_latest["Room"] == selected_room) & 
                    (df_latest["Date"] == date_str) & 
                    (df_latest["Time Slot"] == selected_time) & 
                    (df_latest["Status"] == "Confirmed")
                ]
                
                if not double_check.empty:
                    st.error("❌ Double Booking Blocked! Someone just reserved this slot.")
                else:
                    new_row = pd.DataFrame([{
                        "Date": date_str,
                        "Time Slot": selected_time,
                        "Room": selected_room,
                        "Booked By": name,
                        "Purpose": meeting_purpose,
                        "Status": "Confirmed"
                    }])
                    
                    updated_df = pd.concat([df_bookings, new_row], ignore_index=True)
                    
                    if HAS_GSHEETS:
                        conn = st.connection("gsheets", type=GSheetsConnection)
                        conn.update(spreadsheet=st.secrets["GSHEET_URL"], data=updated_df)
                    
                    email_subject = f"🚨 New Booking: {selected_room} ({meeting_purpose})"
                    email_body = f"Hi Team,\n\nNew reservation recorded:\n\n👤 User: {name}\n🏢 Room: {selected_room}\n📅 Date: {date_str}\n⏰ Time: {selected_time}\n📝 Purpose: {meeting_purpose}"
                    send_email_alert(email_subject, email_body)
                    
                    st.success("🎉 Booking successfully processed! Email alerts dispatched.")
                    st.balloons()
                    time.sleep(1.5)
                    st.rerun()
            else:
                st.warning("Please provide your name and meeting purpose.")
    else:
        st.error("❌ This room is entirely fully booked for this date.")

# ==========================================
# TAB 2: CANCELLATION SYSTEM
# ==========================================
with tab2:
    st.subheader("Cancel an Existing Reservation")
    
    if not df_bookings.empty:
        active_list = df_bookings[df_bookings["Status"] == "Confirmed"]
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
        
        cancel_selection = st.selectbox("Select the booking you wish to cancel:", active_list["Display_Text"].tolist())
        cancel_reason = st.text_input("Reason for Cancellation:", placeholder="e.g., Postponed")
        
        if st.button("Cancel Selected Booking", type="secondary"):
            if cancel_reason:
                selected_idx = active_list[active_list["Display_Text"] == cancel_selection].index[0]
                
                c_date = df_bookings.at[selected_idx, "Date"]
                c_slot = df_bookings.at[selected_idx, "Time Slot"]
                c_room = df_bookings.at[selected_idx, "Room"]
                c_name = df_bookings.at[selected_idx, "Booked By"]
                
                df_bookings.at[selected_idx, "Status"] = "Cancelled"
                df_bookings.at[selected_idx, "Purpose"] = f"{df_bookings.at[selected_idx, 'Purpose']} (CANCELLED: {cancel_reason})"
                
                if "Display_Text" in df_bookings.columns:
                    df_bookings = df_bookings.drop(columns=["Display_Text"])
                    
                if HAS_GSHEETS:
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    conn.update(spreadsheet=st.secrets["GSHEET_URL"], data=df_bookings)
                
                email_subject = f"❌ CANCELLED: {c_room} Reservation"
                email_body = f"Hi Team,\n\nThe following room reservation has been cancelled:\n\n👤 Original Booker: {c_name}\n🏢 Room: {c_room}\n📅 Date: {c_date}\n⏰ Time: {c_slot}\n⚠️ Reason: {cancel_reason}"
                send_email_alert(email_subject, email_body)
                
                st.success("Slot successfully released!")
                time.sleep(1.5)
                st.rerun()
            else:
                st.warning("Please type a quick reason for the cancellation.")

# ==========================================
# SINGLE LIVE REFRESHED DASHBOARD FEED (OUTSIDE TABS)
# ==========================================
st.markdown("---")
st.subheader("📅 Live Schedule Board")
if not df_bookings.empty:
    display_board = df_bookings[df_bookings["Status"] == "Confirmed"]
    if not display_board.empty:
        st.dataframe(display_board[["Date", "Time Slot", "Room", "Booked By", "Purpose"]], use_container_width=True, hide_index=True)
    else:
        st.info("No active reservations booked at the moment.")
else:
    st.info("System database is empty.")
