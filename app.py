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

# Helper function to check if a date string is past due
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
                    existing_room_bookings = df_bookings[
                        ((df_bookings["Date"] == date_str) | (df_bookings["Date"] == selected_date.strftime("%Y-%m-%d"))) & 
                        (df_bookings["Room"] == selected_room) & 
                        (df_bookings["Status"].str.lower() == "confirmed")
                    ]
                    for _, row in existing_room_bookings.iterrows():
                        try:
                            ex_start, ex_end = row["Time Slot"].split(" - ")
                            if start_idx < time_options.index(ex_end) and end_idx > time_options.index(ex_start):
                                is_clashed = True
                                clashed_by = row["Booked By"]
                                clashed_slot = row["Time Slot"]
                                break
                        except Exception: continue

                if is_clashed:
                    st.error(f"⚠️ **Schedule Clash!** Reserved by **{clashed_by}** during **{clashed_slot}**.")
                else:
                    payload = {"Action": "Book", "Date": date_str, "Time_Slot": custom_time_slot, "Room": selected_room, "Booked_By": name, "Purpose": meeting_purpose}
                    response = requests.post(st.secrets["SCRIPT_URL"], data=json.dumps(payload))
                    if response.status_code == 200:
                        st.success("🎉 Booking recorded successfully!")
                        send_email_alert(f"📢 Workspace Secured: {selected_room} ({date_str})", f"Details:\nRoom: {selected_room}\nBy: {name}\nTime: {custom_time_slot}\nAgenda: {meeting_purpose}")
                        st.balloons()
                        time.sleep(1.5)
                        st.rerun()
        else:
            st.warning("Please fill out all identity fields.")

# ==========================================
# TAB 2: CANCELLATION SYSTEM
# ==========================================
with tab2:
    st.subheader("Cancel an Existing Reservation")
    if not df_bookings.empty and "Status" in df_bookings.columns:
        active_list = df_bookings[df_bookings["Status"].str.lower() == "confirmed"].copy()
        active_list = active_list[~active_list["Date"].apply(is_past_date)]
        
        if not active_list.empty:
            active_list["Display_Text"] = active_list["Date"] + " | " + active_list["Time Slot"] + " | " + active_list["Room"] + " (" + active_list["Booked By"] + ")"
            cancel_selection = st.selectbox("Select booking to release:", active_list["Display_Text"].tolist(), key="cancel_select")
            cancel_reason = st.text_input("Reason for Cancellation:", placeholder="e.g., Postponed", key="cancel_reason")
            
            if st.button("Submit Cancellation Request", type="secondary"):
                if cancel_reason:
                    selected_row = active_list[active_list["Display_Text"] == cancel_selection].iloc[0]
                    cancel_payload = {"Action": "Cancel", "Date": selected_row["Date"], "Time_Slot": selected_row["Time Slot"], "Room": selected_row["Room"], "Purpose": selected_row["Purpose"]}
                    response = requests.post(st.secrets["SCRIPT_URL"], data=json.dumps(cancel_payload))
                    if response.status_code == 200:
                        st.success("🎉 Cancellation fully processed!")
                        send_email_alert(f"❌ Workspace Released: {selected_row['Room']}", f"The slot {selected_row['Time Slot']} on {selected_row['Date']} was cancelled.\nReason: {cancel_reason}")
                        time.sleep(1.5)
                        st.rerun()
                else:
                    st.warning("Please type a reason.")
        else: st.info("No active upcoming bookings to release.")

# ==========================================
# TAB 3: RESCHEDULE SYSTEM (WITH SMART LABELS)
# ==========================================
with tab3:
    st.subheader("Reschedule an Existing Booking")
    if not df_bookings.empty and "Status" in df_bookings.columns:
        resched_list = df_bookings[df_bookings["Status"].str.lower() == "confirmed"].copy()
        resched_list = resched_list[~resched_list["Date"].apply(is_past_date)]
        
        if not resched_list.empty:
            resched_list["Display_Text"] = resched_list["Date"] + " | " + resched_list["Time Slot"] + " | " + resched_list["Room"] + " (" + resched_list["Booked By"] + ")"
            selected_meeting_text = st.selectbox("1. Choose Meeting to Change:", resched_list["Display_Text"].tolist(), key="resched_select")
            selected_meeting_row = resched_list[resched_list["Display_Text"] == selected_meeting_text].iloc[0]
            
            st.markdown("---")
            st.markdown("### 2. Enter New Allocation Details")
            
            new_date = st.date_input("Choose New Date:", datetime.today(), key="resched_date", format="DD/MM/YYYY")
            new_date_str = new_date.strftime("%d/%m/%Y")
            new_room = st.radio("Choose New Room Target:", rooms, key="resched_room")
            
            r_col1, r_col2 = st.columns(2)
            with r_col1:
                new_start = st.selectbox("New Start Time:", time_options, index=2, key="start_resched")
            with r_col2:
                new_end = st.selectbox("New End Time:", time_options, index=4, key="end_resched")
                
            new_time_slot = f"{new_start} - {new_end}"
            
            if st.button("Apply Reschedule Changes", type="primary"):
                new_start_idx = time_options.index(new_start)
                new_end_idx = time_options.index(new_end)
                
                if new_start_idx >= new_end_idx:
                    st.error("❌ End time must be later than start time.")
                else:
                    is_clashed = False
                    if not df_bookings.empty and "Status" in df_bookings.columns:
                        clash_filter = df_bookings[
                            ((df_bookings["Date"] == new_date_str) | (df_bookings["Date"] == new_date.strftime("%Y-%m-%d"))) & 
                            (df_bookings["Room"] == new_room) & 
                            (df_bookings["Status"].str.lower() == "confirmed")
                        ]
                        for _, row in clash_filter.iterrows():
                            try:
                                if (selected_meeting_row["Date"] == row["Date"] and 
                                    selected_meeting_row["Room"] == new_room and 
                                    selected_meeting_row["Time Slot"] == row["Time Slot"]):
                                    continue
                                    
                                ex_start, ex_end = row["Time Slot"].split(" - ")
                                if new_start_idx < time_options.index(ex_end) and new_end_idx > time_options.index(ex_start):
                                    is_clashed = True
                                    clashed_by = row["Booked By"]
                                    clashed_slot = row["Time Slot"]
                                    break
                            except Exception: continue
                            
                    if is_clashed:
                        st.error(f"⚠️ **Schedule Clash!** Already occupied by **{clashed_by}** ({clashed_slot}).")
                    else:
                        # Add a tracking keyword to the original purpose row so the table feed can identify it
                        tracked_purpose = f"{selected_meeting_row['Purpose']} [RESCHED_TO:{new_date_str}]"
                        
                        cancel_payload = {"Action": "Cancel", "Date": selected_meeting_row["Date"], "Time_Slot": selected_meeting_row["Time Slot"], "Room": selected_meeting_row["Room"], "Purpose": tracked_purpose}
                        res_c = requests.post(st.secrets["SCRIPT_URL"], data=json.dumps(cancel_payload))
                        
                        book_payload = {"Action": "Book", "Date": new_date_str, "Time_Slot": new_time_slot, "Room": new_room, "Booked_By": selected_meeting_row["Booked By"], "Purpose": selected_meeting_row["Purpose"]}
                        res_b = requests.post(st.secrets["SCRIPT_URL"], data=json.dumps(book_payload))
                        
                        if res_b.status_code == 200:
                            st.success("🔄 Booking successfully rescheduled!")
                            
                            subject = f"🔄 Meeting Rescheduled: {selected_meeting_row['Room']}"
                            body = (
                                f"Dear Team,\n\n"
                                f"Notice: The meeting detailed below has been rescheduled.\n\n"
                                f"🗓️ Previous Details:\n"
                                f"❌ Date/Time: {selected_meeting_row['Date']} ({selected_meeting_row['Time Slot']})\n"
                                f"❌ Room Location: {selected_meeting_row['Room']}\n\n"
                                f"✨ Updated Details:\n"
                                f"✅ New Date/Time: {new_date_str} ({new_time_slot})\n"
                                f"✅ New Room Location: {new_room}\n"
                                f"👤 Booker: {selected_meeting_row['Booked By']}\n"
                                f"📝 Purpose: {selected_meeting_row['Purpose']}\n"
                            )
                            send_email_alert(subject, body)
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.error("Failed to alter remote database entries.")
        else: st.info("No active upcoming bookings available to reschedule.")

# ==========================================
# 6. LIVE REFRESHED DASHBOARD FEED WITH DYNAMIC LABELS
# ==========================================
st.markdown("---")
st.subheader("📋 Active Schedule Table Feed")
if not df_bookings.empty:
    display_board = df_bookings[~df_bookings["Date"].apply(is_past_date)].copy()
    
    def format_row(row):
        purpose_text = str(row["Purpose"])
        status = str(row["Status"]).strip().lower()
        
        # Dynamic Labeling Logic
        if status == "cancelled" and "[RESCHED_TO:" in purpose_text:
            target_date = purpose_text.split("[RESCHED_TO:")[1].replace("]", "")
            return {**row, "Status/Notes": f"🔄 Rescheduled to {target_date}"}
        elif status == "cancelled":
            return {**row, "Status/Notes": "❌ Cancelled & Now Open"}
        return {**row, "Status/Notes": "🟢 Active & Secured"}

    formatted_data = display_board.apply(format_row, axis=1, result_type="expand")
    st.dataframe(formatted_data, use_container_width=True, hide_index=True)
else:
    st.info("System database is empty.")
