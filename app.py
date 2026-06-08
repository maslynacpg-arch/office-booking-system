import streamlit as st
import pandas as pd
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Office Booking Hub", layout="wide")
st.title("🏢 Smart Office Booking Hub")

# --- DATABASE CONNECTION FUNCTION ---
def get_booking_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # ttl=0 forces Streamlit to fetch fresh data from Google Sheets every time
        existing_data = conn.read(spreadsheet=st.secrets["GSHEET_URL"], ttl=0)
        df = pd.DataFrame(existing_data)
        if df.empty:
            return pd.DataFrame(columns=["Date", "Time Slot", "Room", "Booked By", "Purpose", "Status"])
        
        # Standardize column names and clean spaces
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
SENDER_EMAIL = st.secrets["EMAIL_USER"]
SENDER_PASSWORD = st.secrets["EMAIL_PASSWORD"]
RECIPIENT_LIST = [email.strip() for email in st.secrets["ALL_STAFF_EMAIL"].split(",")]

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

# Create Tabs for Booking vs Cancelling
tab1, tab2 = st.tabs(["📝 Reserve a Room", "❌ Cancel a Booking"])

# ==========================================
# TAB 1: BOOKING SYSTEM (ANTI-DOUBLE BOOKING)
# ==========================================
with tab1:
    st.subheader("New Reservation")
    selected_room = st.radio("Choose a Room:", rooms, key="book_room")
    selected_date = st.date_input("Select Date:", datetime.today(), key="book_date")
    date_str = selected_date.strftime("%Y-%m-%d")

    # Filter out active, confirmed bookings for this room and date
    booked_slots = []
    if not df_bookings.empty:
        active_bookings = df_bookings[
            (df_bookings["Room"] == selected_room) & 
            (df_bookings["Date"] == date_str) & 
            (df_bookings["Status"] == "Confirmed")
        ]
        booked_slots = active_bookings["Time Slot"].tolist()

    # Calculate available slots
    available_slots = [slot for slot in all_slots if slot not in booked_slots]

    if available_slots:
        selected_time = st.selectbox("Select Available Time Slot:", available_slots)
        name = st.text_input("Your Name:", key="book_name")
        meeting_purpose = st.text_input("Meeting Purpose:", placeholder="e.g., Operation Review", key="book_purpose")

        if st.button("Confirm Booking", type="primary"):
            if name and meeting_purpose:
                # CRITICAL STEP: Re-read sheet immediately to block double-booking races
                df_latest = get_booking_data()
                double_check = df_latest[
                    (df_latest["Room"] == selected_room) & 
                    (df_latest["Date"] == date_str) & 
                    (df_latest["Time Slot"] == selected_time) & 
                    (df_latest["Status"] == "Confirmed")
                ]
                
                if not double_check.empty:
                    st.error("❌ Double Booking Blocked! Someone just reserved this slot a moment ago. Please refresh or pick another time.")
                else:
                    # Proceed with safe booking row injection
                    new_row = pd.DataFrame([{
                        "Date": date_str,
                        "Time Slot": selected_time,
                        "Room": selected_room,
                        "Booked By": name,
                        "Purpose": meeting_purpose,
                        "Status": "Confirmed"
                    }])
                    
                    updated_df = pd.concat([df_bookings, new_row], ignore_index=True)
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    conn.update(spreadsheet=st.secrets["GSHEET_URL"], data=updated_df)
                    
                    # Send confirmation email
                    email_subject = f"🚨 New Booking: {selected_room} ({meeting_purpose})"
                    email_body = f"Hi Team,\n\nNew reservation recorded:\n\n👤 User: {name}\n🏢 Room: {selected_room}\n📅 Date: {date_str}\n⏰ Time: {selected_time}\n📝 Purpose: {meeting_purpose}"
                    send_email_alert(email_subject, email_body)
                    
                    st.success("🎉 Booking successfully secured! Database updated and emails dispatched.")
                    st.balloons()
                    st.rerun()
            else:
                st.warning("Please provide your name and meeting purpose.")
    else:
        st.error("❌ This room is entirely fully booked for this date. Try another date or workspace.")

# ==========================================
# TAB 2: CANCELLATION SYSTEM
# ==========================================
with tab2:
    st.subheader("Cancel an Existing Reservation")
    
    # Filter only confirmed bookings that can be cancelled
    if not df_bookings.empty:
        active_list = df_bookings[df_bookings["Status"] == "Confirmed"]
    else:
        active_list = pd.DataFrame()
        
    if active_list.empty:
        st.info("There are no active bookings to cancel right now.")
    else:
        # Create clear descriptions for user selection
        active_list["Display_Text"] = (
            active_list["Date"] + " | " + 
            active_list["Time Slot"] + " | " + 
            active_list["Room"] + " (" + active_list["Booked By"] + ")"
        )
        
        cancel_selection = st.selectbox("Select the booking you wish to cancel:", active_list["Display_Text"].tolist())
        cancel_reason = st.text_input("Reason for Cancellation:", placeholder="e.g., Postponed")
        
        if st.button("Cancel Selected Booking", type="secondary"):
            if cancel_reason:
                # Match selected row index back to original dataframe index
                selected_idx = active_list[active_list["Display_Text"] == cancel_selection].index[0]
                
                # Fetch details for notification before updating
                c_date = df_bookings.at[selected_idx, "Date"]
                c_slot = df_bookings.at[selected_idx, "Time Slot"]
                c_room = df_bookings.at[selected_idx, "Room"]
