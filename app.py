import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
import smtplib
from email.mime.text import MIMEText

# Set page layout to wide for better table presentation
st.set_page_config(page_title="Office Booking Hub", layout="wide")
st.title("🏢 Smart Office Booking Hub")

# --- DATABASE CONNECTION FUNCTION ---
def get_booking_data():
    try:
        from streamlit_gsheets import GSheetsConnection
        conn = st.connection("gsheets", type=GSheetsConnection)
        existing_data = conn.read(spreadsheet=st.secrets["GSHEET_URL"], ttl=0)
        df = pd.DataFrame(existing_data)
        
        if df.empty or len(df.columns) == 0:
            return pd.DataFrame(columns=["Date", "Time Slot", "Room", "Booked By", "Purpose", "Status"])
        
        df.columns = df.columns.str.strip()
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()
        return df
    except Exception:
        try:
            base_url = st.secrets["GSHEET_URL"].split("/edit")[0]
            csv_url = f"{base_url}/export?format=csv&nocache={int(time.time())}"
            df = pd.read_csv(csv_url)
            df.columns = df.columns.str.strip()
            for col in df.columns:
                df[col] = df[col].astype(str).str.strip()
            return df
        except Exception:
            return pd.DataFrame(columns=["Date", "Time Slot", "Room", "Booked By", "Purpose", "Status"])

# Load data on refresh
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

    # Build an interactive visual schedule dashboard matrix for the chosen day
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
    
    # Dynamically look up taken slots for this specific room and day
    booked_slots = []
    if not df_bookings.empty and "Status" in df_bookings.columns:
        active_bookings = df_bookings[
            (df_bookings["Room"].str.lower() == selected_room.lower()) & 
            (df_bookings["Date"] == date_str) & 
            (df_bookings["Status"].str.lower() == "confirmed")
        ]
        booked_slots = active_bookings["Time Slot"].tolist()

    # Create drop-down options showing ONLY slots that are empty
    available_slots = [slot for slot in all_slots if slot not in booked_slots]

    if available_slots:
        selected_time = st.selectbox("Select An Available Time Window:", available_slots)
        name = st.text_input("Your Name:", key="book_name")
        meeting_purpose = st.text_input("Meeting Purpose / Agenda:", placeholder="e.g., Mill Deduction Review", key="book_purpose")

        if st.button("Confirm Reservation Securely", type="primary"):
            if name and meeting_purpose:
                # Double-check live cloud status inside button processing thread to absolute-block cross-booking races
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
                    new_row = pd.DataFrame([{
                        "Date": date_str,
                        "Time Slot": selected_time,
                        "Room": selected_room,
                        "Booked By": name,
                        "Purpose": meeting_purpose,
                        "Status": "Confirmed"
                    }])
                    
                    from streamlit_gsheets import GSheetsConnection
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    updated_df = pd.concat([df_bookings, new_row], ignore_index=True)
                    conn.update(spreadsheet=st.secrets["GSHEET_URL"], data=updated_df)
                    
                    # Professional corporate sentence alert dispatch block
                    email_subject = f"🏢 Room Booking Confirmed: {selected_room}"
                    email_body = f"Hi Team,\n\nA new room reservation has been officially registered in the system:\n\n👤 Staff Name: {name}\n📍 Facility: {selected_room}\n📅 Date: {date_str}\n⏰ Duration: {selected_time}\n📝 Agenda: {meeting_purpose}\n\nPlease refer to the Live Schedule Board if you need to coordinate timings."
                    send_email_alert(email_subject, email_body)
                    
                    st.success("🎉 Booking successfully logged! Alerts broadcasted to staff.")
                    st.balloons()
                    time.sleep(1.5)
                    st.rerun()
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
                selected_idx = active_list[active_list["Display_Text"] == cancel_selection].index[0]
                c_date = df_bookings.at[selected_idx, "Date"]
                c_slot = df_bookings.at[selected_idx, "Time Slot"]
                c_room = df_bookings.at[selected_idx, "Room"]
                c_name = df_bookings.at[selected_idx, "Booked By"]
                
                df_bookings.at[selected_idx, "Status"] = "Cancelled"
                df_bookings.at[selected_idx, "Purpose"] = f"{df_bookings.at[selected_idx, 'Purpose']} (CANCELLED: {cancel_reason})"
                
                if "Display_Text" in df_bookings.columns:
                    df_bookings = df_bookings.drop(columns=["Display_Text"])
                    
                from streamlit_gsheets import GSheetsConnection
                conn = st.connection("gsheets", type=GSheetsConnection)
                conn.update(spreadsheet=st.secrets["GSHEET_URL"], data=df_bookings)
                
                email_subject = f"❌ Room Booking Cancelled: {c_room}"
                email_body = f"Hi Team,\n\nThe following room reservation has been removed and is now available for booking:\n\n👤 Original Booker: {c_name}\n📍 Facility: {c_room}\n📅 Date: {c_date}\n⏰ Released Time: {c_slot}\n⚠️ Reason: {cancel_reason}"
                send_email_alert(email_subject, email_body)
                
                st.success("Slot successfully released!")
                time.sleep(1.5)
                st.rerun()
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
