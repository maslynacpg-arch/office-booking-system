# --- TAB 1: VISUAL GRID TIMELINE INTERFACE ---
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
    else:
        st.warning("Please select both a Start Date and an End Date from the calendar.")
        st.stop()

    # Generate list of dates within the selected range
    date_range_list = pd.date_range(start=start_date_obj, end=end_date_obj).strftime("%d/%m/%Y").tolist()
