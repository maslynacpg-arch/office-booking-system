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

# --- SMART FORMAT PARSING FOR MIXED DATE INPUTS ---
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

# Helper to remove older rescheduled elements from active calculations
def get_active_validations_df(df):
    if df.empty:
        return df.copy()
    check_board = df.copy()
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
    return check_board.drop(index=reschedule_indices)

# Helper to remove corrupt/incomplete/nan rows from selectbox sources
def filter_valid_bookings(df):
    if df.empty:
        return df
    valid_mask = (
        df["Date"].notna() & (df["Date"].str.lower() != "nan") & (df["Date"].str.strip() != "") &
        df["Time Slot"].notna() & (df["Time Slot"].str.lower() != "nan") & (df["Time Slot"].str.strip() != "") &
        df["Room"].notna() & (df["Room"].str.lower() != "nan") & (df["Room"].str.strip() != "") &
        df["Booked By"].notna() & (df["Booked By"].str.lower() != "nan") & (df["Booked By"].str.strip() != "")
    )
    return df[valid_mask].copy()

# ==========================================
# TAB 1: VISUAL GRID TIMELINE INTERFACE
# ==========================================
with tab1:
    st.subheader("Visual Schedule Planner")
    
    # Range selection for Start Date and End Date
    selected_dates = st.date_input(
        "1. Choose Date Range:",
        value=(datetime.today(), datetime.today()),
        key="book_date_range",
        format="DD/MM/YYYY"
    )
    
    # Ensure user has selected both start and end dates
    if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
        start_date_obj, end_date_obj = selected_dates
    elif isinstance(selected_dates, tuple) and len(selected_dates) == 1:
        start_date_obj = selected_dates[0]
        end_date_obj = selected_dates[0]
    else:
        start_date_obj = datetime.today()
        end_date_obj = datetime.today()

    # Generate list of dates within the selected range
    date_range_list = pd.date_range(start=start_date_obj, end=end_date_obj).strftime("%d/%m/%Y").tolist()

    st.markdown("### 📊 Interactive Daily Availability Timeline")
    
    cleaned_active_df = get_active_validations_df(df_bookings)
    target_date_formatted = start_date_obj.strftime("%Y-%m-%d")
    date_str = start_date_obj.strftime("%d/%m/%Y")

    for room in rooms:
        room_active = pd.DataFrame()
        if not cleaned_active_df.empty and "Status" in cleaned_active_df.columns:
            room_active = cleaned_active_df[
                ((cleaned_active_df["Date"] == date_str) | (cleaned_active_df["Date"] == target_date_formatted)) & 
                (cleaned_active_df["Room"] == room) & 
                (cleaned_active_df["Status"].str.lower() == "confirmed")
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

    custom_time
