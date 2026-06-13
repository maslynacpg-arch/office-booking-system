import streamlit as st
import pandas as pd
from datetime import datetime
import time
import smtplib
from email.mime.text import MIMEText
import requests
import json

# 1. SETUP PAGE CONFIGURATION FIRST
st.set_page_config(page_title="Meeting Room Booking", layout="wide")
st.title("🏢 Meeting Room Booking")

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

# Get today's date string format (YYYY-MM-DD)
today_str = datetime.today().strftime("%Y-%m-%d")

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

# 5. CREATE THE TABS SYSTEM
tab1, tab2 = st.tabs(["📝 Reserve a Room", "❌ Cancel a Booking"])

# ==========================================
# TAB 1: VISUAL BOOKING SYSTEM & CLASH PREVENTION
# ==========================================
with tab1:
    st.subheader("Visual Schedule Planner")
    selected_date = st.date_input("1. Choose Date:", datetime.today(), key="book_date")
    date_str = selected_date.strftime("%Y-%m-%d")
    
    st.markdown("### 📅 Live Confirmed Bookings for Selected Date")
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
        start_time = st.selectbox("Select Start Time:", time_options, index=2)
    with col2:
        end_time = st.selectbox("Select End Time:", time_options, index=4)

    custom_time_slot = f"{start_time} - {end_time}"
    name = st.text_input("Your Name:", key="book_name")
    meeting_purpose = st.text_input("Meeting Purpose / Agenda:", key="book_purpose")

    if st.button("Confirm Reservation Securely", type="primary"):
        if name and meeting_purpose:
            start_idx = time_options.index(start_time)
            end_idx = time_options.index(end_time)
            
            if start_idx >= end_idx:
                st.error("❌ Invalid Time Selection: End time must be later than the Start time.")
            else:
                # 🛡️ BACKGROUND CLASH-CHECKING ENGINE
                is_clashed = False
                clashed_by = ""
                clashed_purpose = ""
                clashed_slot = ""
                
                if not df_bookings.empty and "Status" in df_bookings.columns:
                    existing_room_bookings = df_bookings[
                        (df_bookings["Date"] == date_str) & 
                        (df_bookings["Room"] == selected_room) & 
                        (df_bookings["Status"].str.lower() == "confirmed")
                    ]
                    
                    for _, row in existing_room_bookings.iterrows():
                        try:
                            ex_start, ex_end = row["Time Slot"].split(" - ")
                            ex_start_idx = time_options.index(ex_start)
                            ex_end_idx = time_options.index(ex_end)
                            
                            # Overlap verification logic
                            if start_idx < ex_end_idx and end_idx > ex_start_idx:
                                is_clashed = True
                                clashed_by = row["Booked By"]
                                clashed_purpose = row["Purpose"]
                                clashed_slot = row["Time Slot"]
                                break
                        except Exception:
                            continue

                if is_clashed:
                    st.error(f"⚠️ **Schedule Clash!** {selected_room} is already reserved by **{clashed_by}** during **{clashed_slot}** for *'{clashed_purpose}'*. Please change your time slot window or select a different room.")
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
                        st.success(f"🎉 Booking recorded successfully!")
                        
                        email_subject = f"📢 Workspace Secured: {selected_room} ({date_str})"
                        email_body = (
                            f"Dear Team,\n\n"
                            f"Please note that the following workspace has been secured for an upcoming session.\n\n"
                            f"📋 Reservation Details:\n"
                            f"📍 Workspace: {selected_room}\n"
                            f"👤 Reserved By: {name}\n"
                            f"📅 Session Date: {date_str}\n"
                            f"⏰ Time Window: {custom_time_slot}\n"
                            f"📝 Session Agenda: {meeting_purpose}\n\n"
                            f"---\n"
                            f"This is a system-generated notification. Please do not reply directly to this email."
                        )
                        send_email_alert(email_subject, email_body)
                        
                        st.balloons()
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("Failed writing data to Google Engine connection endpoints.")
        else:
            st.warning("Please fill out all identity fields.")

# ==========================================
# TAB 2: CANCELLATION SYSTEM (DATETIME AUTO-FILTER)
# ==========================================
with tab2:
    st.subheader("Cancel an Existing Reservation")
    if not df_bookings.empty and "Status" in df_bookings.columns:
        df_active = df_bookings.copy()
        df_active["Parsed_Date"] = pd.to_datetime(df_active["Date"], errors='coerce')
        today_date = pd.to_datetime(datetime.today().strftime("%Y-%m-%d"))
        
        active_list = df_active[
            (df_active["Status"].str.lower() == "confirmed") & 
            (df_active["Parsed_Date"] >= today_date)
        ].copy()
        
        if not active_list.empty:
            active_list["Display_Text"] = (
                active_list["Date"] + " | " + 
                active_list["Time Slot"] + " | " + 
                active_list["Room"] + " (" + active_list["Booked By"] + ") - 📝 " + active_list["Purpose"]
            )
            cancel_selection = st.selectbox("Select booking to release:", active_list["Display_Text"].tolist())
            cancel_reason = st.text_input("Reason for Cancellation:", placeholder="e.g., Meeting rescheduled / postponed")
            
            if st.button("Submit Cancellation Request", type="secondary"):
                if cancel_reason:
                    selected_row = active_list[active_list["Display_Text"] == cancel_selection].iloc[0]
                    c_date = selected_row["Date"]
                    c_slot = selected_row["Time Slot"]
                    c_room = selected_row["Room"]
                    c_name = selected_row["Booked By"]
                    c_purpose = selected_row["Purpose"]
                    
                    cancel_payload = {
                        "Action": "Cancel",
                        "Date": c_date,
                        "Time_Slot": c_slot,
                        "Room": c_room,
                        "Purpose": c_purpose
                    }
                    
                    response = requests.post(st.secrets["SCRIPT_URL"], data=json.dumps(cancel_payload))
                    
                    if response.status_code == 200:
                        st.success("🎉 Cancellation fully processed!")
                        
                        email_subject = f"❌ Workspace Released: {c_room} ({c_date})"
                        email_body = (
                            f"Dear Team,\n\n"
                            f"Please note that the workspace allocation below has been released and is now open for new reservations.\n\n"
                            f"🗑️ Released Reservation Details:\n"
                            f"📍 Workspace: {c_room}\n"
                            f"👤 Original Booker: {c_name}\n"
                            f"📅 Date Affected: {c_date}\n"
                            f"⏰ Released Slot: {c_slot}\n"
                            f"⚠️ Cancellation Reason: {cancel_reason}\n\n"
                            f"---\n"
                            f"This is a system-generated notification. Please do not reply directly to this email."
                        )
                        send_email_alert(email_subject, email_body)
                        
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.error("Failed to connect to Google Sheet database for cancellation processing.")
                else:
                    st.warning("Please type a reason for the cancellation.")
        else:
            st.info("There are no active upcoming bookings to release right now.")
    else:
        st.info("There are no active upcoming bookings to track right now.")

# ==========================================
# 6. LIVE REFRESHED DASHBOARD FEED (TODAY & UPCOMING ONLY)
# ==========================================
st.markdown("---")
st.subheader("📋 Active Schedule Table Feed (Today & Upcoming)")

if not df_bookings.empty and "Status" in df_bookings.columns:
    display_board = df_bookings.copy()
    display_board["Parsed_Date"] = pd.to_datetime(display_board["Date"], errors='coerce')
    today_date = pd.to_datetime(datetime.today().strftime("%Y-%m-%d"))
    
    display_board = display_board[display_board["Parsed_Date"] >= today_date]
    display_board = display_board.sort_values(by=["Parsed_Date", "Time Slot"])
    
    if not display_board.empty:
        def format_row(row):
            status = str(row["Status"]).strip().lower()
            if status == "cancelled":
                return {
                    "Date": f"~~{row['Date']}~~",
                    "Time Slot": f"~~{row['Time Slot']}~~",
                    "Room": f"~~{row['Room']}~~",
                    "Booked By": f"~~{row['Booked By']}~~",
                    "Purpose": f"~~{row['Purpose']}~~",
                    "Status/Notes": "❌ Cancelled & Now Open"
                }
            else:
                return {
                    "Date": row["Date"],
                    "Time Slot": row["Time Slot"],
                    "Room": row["Room"],
                    "Booked By": row["Booked By"],
                    "Purpose": row["Purpose"],
                    "Status/Notes": "🟢 Active & Secured"
                }
                
        formatted_data = display_board.apply(format_row, axis=1, result_type="expand")
        st.dataframe(
            formatted_data[["Date", "Time Slot", "Room", "Booked By", "Purpose", "Status/Notes"]], 
            use_container_width=True, 
            hide_index=True
        )
    else:
        st.info("No active schedules or reservations booked for today onwards.")
else:
    st.info("System database is empty.")
