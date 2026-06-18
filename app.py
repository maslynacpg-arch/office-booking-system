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

# 3. DEFINE EMAIL SYSTEM
try:
    SENDER_EMAIL = st.secrets["EMAIL_USER"]
    SENDER_PASSWORD = st.secrets["EMAIL_PASSWORD"]
    RECIPIENT_LIST = [email.strip() for email in st.secrets["ALL_STAFF_EMAIL"].split(",")]
except KeyError:
    st.error("❌ Secrets Configuration Missing in Streamlit Settings.")
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
tab1, tab2, tab3 = st.tabs(["📝 Reserve a Room", "❌ Cancel a Booking", "🔄 Reschedule a Booking"])

# Get current date info for filtering out past dates
today_obj = datetime.today()

# --- ADJUSTMENT 1: SMART FORMAT PARSING FOR MIXED DATE INPUTS ---
def is_past_date(date_string):
    try:
        clean_date = date_string.replace("-", "/")
        if len(clean_date.split('/')[0]) == 4:
            booking_date = datetime.strptime(clean_date, "%Y/%m/%d")
        else:
            booking_date = datetime.strptime(clean_date, "%d/%m/%Y")
        return booking_date.date() < today_obj.date()
    except Exception:
        return False

# ==========================================
# TAB 1: VISUAL GRID TIMELINE INTERFACE
# ==========================================
with tab1:
    st.subheader("Visual Schedule Planner")
    selected_date = st.date_input("1. Choose Date:", datetime.today(), key="book_date", format="DD/MM/YYYY")
    date_str = selected_date.strftime("%d/%m/%Y")
    
    st.markdown("### 📊 Interactive Daily Availability Timeline")
    
    for room in rooms:
        room_active = pd.DataFrame()
        if not df_bookings.empty and "Status" in df_bookings.columns:
            room_active = df_bookings[
                ((df_bookings["Date"] == date_str) | (df_bookings["Date"] == selected_date.strftime("%Y-%m-%d"))) & 
                (df_bookings["Room"] == room) & 
                (df_bookings["Status"].str.lower() == "confirmed")
            ]
        
        html_content = f"""
        <div style="margin-bottom: 25px; font-family: sans-serif;">
            <div style="font-weight: bold; font-size: 16px; margin-bottom: 8px; color: #1E293B;">📍 {room}</div>
            <div style="display: flex; flex-wrap: wrap; gap: 6px;">
        """
        
        for t_slot in time_options:
            is_slot_taken = False
            booked_by_name = ""
            
            if not room_active.empty:
                for _, b_row in room_active.iterrows():
                    try:
                        ex_start, ex_end = b_row["Time Slot"].split(" - ")
                        s_idx = time_options.index(ex_start)
                        e_idx = time_options.index(ex_end)
                        target_idx = time_options.index(t_slot)
                        
                        if s_idx <= target_idx < e_idx:
                            is_slot_taken = True
                            booked_by_name = b_row['Booked By']
                            break
                    except Exception:
                        continue
            
            if is_slot_taken:
                bg_color = "#FCA5A5"
                text_color = "#991B1B"
                border_color = "#EF4444"
                title_desc = f"Booked by {booked_by_name}"
                status_text = f"✕ {t_slot}"
            else:
                bg_color = "#A7F3D0"
                text_color = "#065F46"
                border_color = "#10B981"
                title_desc = "Available for selection"
                status_text = t_slot
                
            html_content += f"""
            <div title="{title_desc}" style="
                flex: 1; min-width: 85px; text-align: center; padding: 10px 4px;
                border-radius: 6px; font-size: 12px; font-weight: 600;
                background-color: {bg_color}; color: {text_color}; border: 1px solid {border_color};
                box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            ">
                {status_text}
            </div>
            """
            
        html_content += "</div></div>"
        st.html(html_content)

    st.markdown("---")
    st.subheader("2. Input Custom Booking Details")
    selected_room = st.radio("Choose Room Target:", rooms, key="book_room")
    
    col1, col2 = st.columns(2)
    with col1:
        start_time = st.selectbox("Select Start Time:", time_options, index=2, key="start_book")
    with col2:
        end_time = st.selectbox("Select End Time:", time_options, index=4, key="end_book")

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
                is_clashed = False
                if not df_bookings.empty and "Status" in df_bookings.columns:
                    # --- CRITICAL CLASH HANDLING UPGRADE FOR RESCHEDULES ---
                    check_board = df_bookings.copy()
                    
                    def quick_clean(d):
                        try:
                            d_str = str(d).strip()
                            if "/" in d_str:
                                return datetime.strptime(d_str, "%d/%m/%Y").strftime("%Y-%m-%d")
                            return datetime.strptime(d_str, "%Y-%m-%d").strftime("%Y-%m-%d")
                        except:
                            return str(d)
                    check_board["Date"] = check_board["Date"].apply(quick_clean)

                    match_cols = ["Time Slot", "Room", "Booked By", "Purpose"]
                    reschedule_indices = []
                    
                    grouped = check_board[check_board["Status"].str.lower() == "confirmed"].groupby(match_cols)
                    for specs, group in grouped:
                        if len(group) > 1:
                            sorted_group = group.sort_values("Date")
                            older_indices = sorted_group.iloc[:-1].index.tolist()
                            reschedule_indices.extend(older_indices)
                            
                    # Remove older parts of a reschedule sequence from clash checking
                    active_validations = check_board.drop(index=reschedule_indices)
                    
                    # Look up conflicts matching the current target date format
