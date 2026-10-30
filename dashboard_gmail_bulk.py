import streamlit as st
import pandas as pd
import os
import base64
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from agent import AICustomerSegmentationAgent

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
GMAIL_REDIRECT_URI = "https://gmail-send-ifeugtcme9zyjg7ryyx7n.streamlit.app/"


def get_oauth_client_config():
    """Read the Web OAuth client from Streamlit Cloud Secrets."""
    try:
        oauth = st.secrets["google_oauth"]
        return {
            "web": {
                "client_id": oauth["client_id"],
                "client_secret": oauth["client_secret"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [GMAIL_REDIRECT_URI],
            }
        }
    except Exception as exc:
        raise RuntimeError(
            "Google OAuth Secrets are not configured. Add the [google_oauth] "
            "section in Streamlit app Settings → Secrets."
        ) from exc


def create_oauth_flow(state=None):
    flow = Flow.from_client_config(
        get_oauth_client_config(),
        scopes=GMAIL_SCOPES,
        state=state,
    )
    flow.redirect_uri = GMAIL_REDIRECT_URI
    return flow


def process_oauth_callback():
    """Exchange Google's callback code for Gmail credentials in this session."""
    params = st.query_params
    if "error" in params:
        st.error(f"Google sign-in was not completed: {params.get('error')}")
        st.query_params.clear()
        return

    code = params.get("code")
    if not code:
        return

    expected_state = st.session_state.get("gmail_oauth_state")
    returned_state = params.get("state")
    if not expected_state or not returned_state or returned_state != expected_state:
        st.error("Gmail sign-in state did not match. Please click Connect Gmail and try again.")
        st.query_params.clear()
        return

    try:
        flow = create_oauth_flow(state=expected_state)
        flow.fetch_token(code=code)
        st.session_state["gmail_credentials_json"] = flow.credentials.to_json()
        st.session_state["gmail_oauth_state"] = None
        st.query_params.clear()
        st.success("Gmail connected for this browser session.")
    except Exception as exc:
        st.error(f"Google authorization failed: {exc}")
        st.query_params.clear()


def get_gmail_service():
    """Return Gmail API service using credentials authorised in this browser session."""
    credentials_json = st.session_state.get("gmail_credentials_json")
    if not credentials_json:
        raise RuntimeError("Gmail is not connected. Click Connect Gmail first.")

    credentials = Credentials.from_authorized_user_info(
        __import__("json").loads(credentials_json), GMAIL_SCOPES
    )
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        st.session_state["gmail_credentials_json"] = credentials.to_json()

    if not credentials.valid:
        raise RuntimeError("Gmail session expired. Please connect Gmail again.")

    return build("gmail", "v1", credentials=credentials)


def render_gmail_connection():
