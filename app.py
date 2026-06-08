# ==========================================
# TAB 2: CANCELLATION SYSTEM
# ==========================================
with tab2:
    st.subheader("Cancel an Existing Reservation")
    if not df_bookings.empty and "Status" in df_bookings.columns:
        active_list = df_bookings[df_bookings["Status"].str.lower() == "confirmed"]
        if not active_list.empty:
            # Create a clear display text for the dropdown selection
            active_list["Display_Text"] = active_list["Date"] + " | " + active_list["Time Slot"] + " | " + active_list["Room"] + " (" + active_list["Booked By"] + ")"
            cancel_selection = st.selectbox("Select booking to release:", active_list["Display_Text"].tolist())
            cancel_reason = st.text_input("Reason for Cancellation:", placeholder="e.g., Meeting rescheduled / postponed")
            
            if st.button("Submit Cancellation Request", type="secondary"):
                if cancel_reason:
                    # Look up the details of the selected row to include in the email
                    selected_row = active_list[active_list["Display_Text"] == cancel_selection].iloc[0]
                    c_date = selected_row["Date"]
                    c_slot = selected_row["Time Slot"]
                    c_room = selected_row["Room"]
                    c_name = selected_row["Booked By"]
                    
                    st.success("🎉 Cancellation logged successfully!")
                    
                    # Send the cancellation email alert automatically
                    email_subject = f"❌ Room Booking Cancelled: {c_room}"
                    email_body = f"Hi Team,\n\nThe following room reservation has been cancelled and the slot is now open:\n\n👤 Original Booker: {c_name}\n📍 Room: {c_room}\n📅 Date: {c_date}\n⏰ Released Time: {c_slot}\n⚠️ Reason: {cancel_reason}"
                    send_email_alert(email_subject, email_body)
                    
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.warning("Please type a reason for the cancellation so the team knows why it was removed.")
        else:
            st.info("There are no active bookings to track right now.")
    else:
        st.info("There are no active bookings to track right now.")
