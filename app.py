if st.button("Confirm Reservation Securely", type="primary"):
        if name and meeting_purpose:
            start_idx = time_options.index(start_time)
            end_idx = time_options.index(end_time)
            
            if start_idx >= end_idx:
                st.error("❌ Invalid Time Selection: End time must be later than the Start time.")
            else:
                # 🛡️ CLASH CHECKING ENGINE
                is_clashed = False
                if not df_bookings.empty and "Status" in df_bookings.columns:
                    # Filter active bookings for the exact target date and room
                    existing_room_bookings = df_bookings[
                        (df_bookings["Date"] == date_str) & 
                        (df_bookings["Room"] == selected_room) & 
                        (df_bookings["Status"].str.lower() == "confirmed")
                    ]
                    
                    for _, row in existing_room_bookings.iterrows():
                        try:
                            # Split the existing time slot string back into start and end times
                            ex_start, ex_end = row["Time Slot"].split(" - ")
                            ex_start_idx = time_options.index(ex_start)
                            ex_end_idx = time_options.index(ex_end)
                            
                            # Check if the requested window overlaps with an existing booking
                            if not (end_idx <= ex_start_idx or start_idx >= ex_end_idx):
                                is_clashed = True
                                clashed_by = row["Booked By"]
                                clashed_purpose = row["Purpose"]
                                clashed_slot = row["Time Slot"]
                                break
                        except Exception:
                            continue

                if is_clashed:
                    st.error(f"⚠️ **Schedule Clash!** {selected_room} is already reserved by **{clashed_by}** during **{clashed_slot}** for *'{clashed_purpose}'*. Please adjust your time slot or choose another room.")
                else:
                    # Clear to proceed with booking creation
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
