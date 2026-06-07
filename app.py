# 4. Booking Action & Email Blast Logic
if st.button("Confirm Booking", type="primary"):
    if name and meeting_purpose:
        try:
            # Pull configuration from Streamlit Secrets
            sender_email = st.secrets["EMAIL_USER"]
            sender_password = st.secrets["EMAIL_PASSWORD"]
            recipient_list = [email.strip() for email in st.secrets["ALL_STAFF_EMAIL"].split(",")]

            # Create the email content including the meeting purpose
            subject = f"🚨 New Booking: {selected_room} ({meeting_purpose})"
            body = (
                f"Hi Team,\n\n"
                f"Please take note of the following room booking:\n\n"
                f"👤 Booked By: {name}\n"
                f"🏢 Room: {selected_room}\n"
                f"📅 Date: {date}\n"
                f"⏰ Time: {selected_time}\n"
                f"📝 Topic: {meeting_purpose}\n\n"
                f"Thank you!\nOffice Booking System"
            )
            
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = sender_email
            msg["To"] = ", ".join(recipient_list)

            # Connect to Gmail's secure sending server (SMTP)
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, recipient_list, msg.as_string())

            st.success(f"🎉 Booking confirmed! Email alert for '{meeting_purpose}' sent to all staff.")
            
        except Exception as e:
            # THIS WILL NOW SHOW THE REAL SYSTEM ERROR MESSAGE ON SCREEN
            st.success(f"🎉 Booking recorded for {name}! (Email failed because: {str(e)}).")
    else:
        st.warning("Please fill in both your Name and the Meeting Purpose before confirming.")
