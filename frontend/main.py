from http import HTTPStatus

import httpx
import streamlit as st

from src.api import BackendAPI
from src.settings import get_settings

st.set_page_config(page_title=get_settings().app_title)

st.title(get_settings().app_title)
st.write("Look up the dividend history for any US stock by ticker symbol.")

ticker = (
    st.text_input(
        "Ticker symbol",
        placeholder="e.g. AAPL, KO, JNJ",
    )
    .strip()
    .upper()
)

if not ticker:
    st.stop()

with st.spinner(f"Fetching dividend history for {ticker}..."):
    try:
        with BackendAPI() as client:
            response = client.get_dividend_history(ticker)
    except httpx.ConnectError:
        st.error("Could not connect to the API. Is the backend running?")
        st.stop()
    except httpx.TimeoutException:
        st.error("Request timed out. The backend may be busy scraping data. Try again.")
        st.stop()

match response.status_code:
    case HTTPStatus.OK:
        data = response.json()

        st.subheader(f"{data['company_name']} ({data['ticker_symbol']})")
        st.caption(
            f"Exchange: {data['exchange']} · Last refreshed: {data['date_refreshed']}"
        )

        events = data["events"]

        if not events:
            st.info("No dividend events found for this ticker.")
            st.stop()

        st.write(f"**{len(events)}** dividend events on record.")

        st.dataframe(
            events,
            column_config={
                "ex_dividend_date": st.column_config.DateColumn("Ex-Dividend Date"),
                "payout_date": st.column_config.DateColumn("Payout Date"),
                "cash_amount": st.column_config.NumberColumn(
                    "Amount ($)", format="%.2f"
                ),
                "pct_change": st.column_config.NumberColumn(
                    "Change (%)", format="%.1f"
                ),
            },
            use_container_width=True,
            hide_index=True,
        )

    case HTTPStatus.NOT_FOUND:
        detail = response.json().get("detail", "Ticker not found.")
        st.warning(detail)

    case HTTPStatus.GATEWAY_TIMEOUT:
        st.error("The data source timed out. Try again in a moment.")

    case HTTPStatus.SERVICE_UNAVAILABLE:
        st.error("The data source is currently unavailable. Try again later.")

    case HTTPStatus.BAD_GATEWAY:
        st.error("Received bad data from the source. This may be a temporary issue.")

    case _:
        st.error(f"Unexpected error (HTTP {response.status_code}).")
