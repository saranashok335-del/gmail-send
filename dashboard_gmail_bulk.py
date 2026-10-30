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
GMAIL_REDIRECT_URI = "https://gmail-send-ifeugtcmc9zyjyg7ryxy7n.streamlit.app/"


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
    """Show the browser-based Gmail connection control."""
    if st.session_state.get("gmail_credentials_json"):
        st.success("Gmail connected for this browser session.")
        if st.button("Disconnect Gmail", key="disconnect_gmail"):
            st.session_state.pop("gmail_credentials_json", None)
            st.rerun()
        return True

    st.info("Connect the authorised sender Gmail account before sending the campaign.")
    if st.button("Connect Gmail", type="secondary", key="connect_gmail"):
        flow = create_oauth_flow()
        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="select_account consent",
        )
        st.session_state["gmail_oauth_state"] = state
        st.link_button("Continue to Google sign-in", authorization_url)
        st.caption("After approving Gmail access, Google will return you to this app.")
    return False


def send_gmail_message(recipient, subject, body):
    """Send one plain-text email using the connected Gmail account."""
    if not recipient or "@" not in recipient:
        raise ValueError("Please enter a valid customer email address.")
    message = MIMEText(body, "plain", "utf-8")
    message["to"] = recipient
    message["subject"] = subject
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    service = get_gmail_service()
    return service.users().messages().send(
        userId="me", body={"raw": raw_message}
    ).execute()


def find_email_column(dataframe):
    """Find a likely email column in the uploaded customer dataset."""
    candidates = ["Email", "email", "Email Address", "email_address",
                  "Customer_Email", "customer_email", "E-mail"]
    return next((column for column in candidates if column in dataframe.columns), None)


# --- Page Configuration ---
st.set_page_config(
    page_title="Market Segment AI | Campaign Automation",
    page_icon="⚡",
    layout="wide"
)

# Complete a Google OAuth redirect, if the user has just returned from Google.
process_oauth_callback()

# --- Stunning Dark Theme & High-Visibility CSS ---
st.markdown("""
    <style>
    @keyframes gradientBG {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    .stApp {
        background: linear-gradient(-45deg, #0f172a, #1e1b4b, #311042, #0f172a);
        background-size: 400% 400%;
        animation: gradientBG 15s ease infinite;
        font-family: 'Inter', sans-serif;
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #0f172a !important;
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }
    [data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }

    /* Bright, Visible Content Card */
    .content-card {
        background: rgba(15, 23, 42, 0.9);
        backdrop-filter: blur(16px);
        padding: 35px;
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.15);
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6);
        margin-top: 20px;
        color: #ffffff;
    }

    h1, h2, h3, h4, h5, h6 {
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    p, span, label, div {
        color: #e2e8f0;
    }

    /* Email Preview Container */
    .email-container {
        background: #ffffff;
        color: #1e293b;
        padding: 30px;
        border-radius: 16px;
        border: 1px solid #cbd5e1;
        box-shadow: 0 10px 25px rgba(0,0,0,0.3);
        margin-top: 15px;
    }
    .email-container * {
        color: #1e293b !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR: Data Ingestion & Discount Policy Controls ---
with st.sidebar:
    st.markdown("### 📂 Data Ingestion")
    uploaded_file = st.file_uploader("Upload CSV or Excel Dataset", type=["csv", "xlsx", "xls"])
    st.markdown("<p style='font-size: 0.75rem; color: #94a3b8;'>200MB per file • CSV, XLSX, XLS</p>", unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### ⚙️ Discount Policy Limits")
    min_discount_val = st.slider("Minimum Discount (%)", min_value=0.0, max_value=15.0, value=2.0, step=0.5)
    max_discount_val = st.slider("Maximum Discount (%)", min_value=10.0, max_value=50.0, value=25.0, step=1.0)

    st.markdown("---")
    st.markdown("### 🤖 Agent Status")
    st.success("🟢 Online & Ready")
    st.markdown("<p style='font-size: 0.8rem; color: #94a3b8;'>Adjustable bounds engine active.</p>", unsafe_allow_html=True)

# --- MAIN DASHBOARD AREA ---
st.markdown("<h1 style='color: #ffffff; font-size: 2.2rem;'>Market Segment AI | Dynamic Campaign Studio</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #94a3b8; font-size: 1.05rem;'>Autonomous RFM segmentation, tunable behavioral discounting limits, and automated email simulation.</p>", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# --- Main Dashboard Logic ---
if uploaded_file is not None:
    file_path = uploaded_file.name
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    with st.spinner("✨ AI Agent is computing unique behavioral discounts within your set limits..."):
        agent = AICustomerSegmentationAgent(file_path)
        results = agent.run_pipeline("web_campaign_results.csv", min_discount=min_discount_val, max_discount=max_discount_val)
    
    st.success(f"✅ Dataset analyzed! Discounts clamped between **{min_discount_val}%** and **{max_discount_val}%**.")
    st.markdown("<br>", unsafe_allow_html=True)

    # --- DIVISION SELECTOR ---
    st.markdown("### 🎛️ Select Dashboard Division")
    view_mode = st.radio(
        "Choose which section to display:",
        ["Show All Divisions", "1: Executive Performance Metrics", "2: Behavioral Segment Breakdown & Charts", "3: Demo Automated Email Simulator", "4: Master Dataset & Export Center"],
        horizontal=True
    )
    st.markdown("---")

    # ==========================================
    # DIVISION 1: EXECUTIVE PERFORMANCE METRICS
    # ==========================================
    if view_mode in ["Show All Divisions", "1: Executive Performance Metrics"]:
        st.markdown("### 📈 Division 1: Executive Performance Metrics")
        
        total_customers = len(results)
        total_revenue = results['Monetary'].sum() if 'Monetary' in results.columns else 0
        avg_spend = results['Monetary'].mean() if 'Monetary' in results.columns else 0
        avg_discount = results['Assigned_Discount_%'].mean() if 'Assigned_Discount_%' in results.columns else 0

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Total Customers", f"{total_customers:,}")
        with m2:
            st.metric("Total Revenue", f"${total_revenue:,.2f}")
        with m3:
            st.metric("Average Spend", f"${avg_spend:,.2f}")
        with m4:
            st.metric("Avg Dynamic Discount", f"{avg_discount:.1f}%")
        st.markdown("<br>", unsafe_allow_html=True)

    # ==========================================
    # DIVISION 2: BEHAVIORAL SEGMENTATION
    # ==========================================
    if view_mode in ["Show All Divisions", "2: Behavioral Segment Breakdown & Charts"]:
        st.markdown("### 🎯 Division 2: Behavioral Segmentation & Distributions")
        
        chart_col1, chart_col2 = st.columns(2, gap="large")
        
        with chart_col1:
            st.markdown("#### 👥 Customer Segment Breakdown")
            if 'Segment' in results.columns:
                seg_table = results['Segment'].value_counts().reset_index()
                seg_table.columns = ['Segment', 'Count']
                st.dataframe(seg_table, use_container_width=True, hide_index=True)
            
        with chart_col2:
            st.markdown("#### 📊 Segment Distribution Chart")
            if 'Segment' in results.columns:
                st.bar_chart(results['Segment'].value_counts(), color="#a855f7")
        st.markdown("<br>", unsafe_allow_html=True)

    # ==========================================
    # DIVISION 3: DEMO AUTOMATED EMAIL SIMULATOR
    # ==========================================
    if view_mode in ["Show All Divisions", "3: Demo Automated Email Simulator"]:
        st.markdown("### ✉️ Division 3: Demo Automated Email Simulator")
        st.markdown("Select any customer ID below to view their unique behavioral discount restricted to your active minimum and maximum limits.")
        
        selected_customer = st.selectbox("🔍 Select Customer ID for Email Preview:", results['CustomerID'].tolist())
        
        if selected_customer:
            cust_row = results[results['CustomerID'] == selected_customer].iloc[0]
            c_segment = cust_row['Segment']
            c_discount = cust_row['Assigned_Discount_%']
            c_msg = cust_row['Automated_Message']
            c_monetary = cust_row['Monetary']
            c_freq = cust_row['Frequency']
            c_recency = cust_row['Recency']
            
            estimated_budget = c_monetary * (c_discount / 100.0)
            email_column = find_email_column(results)
            actual_customer_email = (
                str(cust_row[email_column]).strip()
                if email_column and pd.notna(cust_row[email_column]) else ""
            )
            customer_name = str(cust_row["Name"]) if "Name" in results.columns else str(selected_customer)

            b1, b2, b3, b4 = st.columns(4)
            with b1:
                st.metric(label="Assigned Discount", value=f"{c_discount}% OFF")
            with b2:
                st.metric(label="Spend (Monetary)", value=f"${c_monetary:,.2f}")
            with b3:
                st.metric(label="Frequency", value=f"{c_freq} orders")
            with b4:
                st.metric(label="Recency", value=f"{c_recency} days")

            st.markdown(f"""
                <div class="email-container">
                    <div style="background: #f1f5f9; padding: 12px; border-radius: 8px; font-size: 0.85rem; color: #475569; margin-bottom: 15px; border-left: 4px solid #4f46e5;">
                        <b>From:</b> Your connected Gmail account<br>
                        <b>To:</b> {actual_customer_email or "No email address found in dataset"} &nbsp;|&nbsp; <span style="color: #059669; font-weight: bold;">● Tuned Bounds Active</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #e2e8f0; padding-bottom: 15px; margin-bottom: 20px;">
                        <h3 style="color: #4f46e5 !important; margin: 0; font-size: 1.5rem;">⚡ AI Brand Co.</h3>
                        <span style="background: #e0e7ff; color: #3730a3; padding: 5px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: bold; text-transform: uppercase;">Tier: {c_segment}</span>
                    </div>
                    <p style="font-size: 1.05rem; color: #334155;">Hello <b>{customer_name}</b>,</p>
                    <div style="background: #f8fafc; border: 1px solid #e2e8f0; padding: 20px; border-radius: 12px; font-style: italic; color: #1e293b; font-size: 1.1rem; line-height: 1.6; margin: 15px 0;">
                        "{c_msg}"
                    </div>
                    <div style="background: linear-gradient(135deg, #4f46e5, #6366f1); color: white; padding: 20px; border-radius: 12px; text-align: center; margin-top: 20px;">
                        <p style="margin: 0; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.9;">Your Tuned Behavioral Voucher</p>
                        <h3 style="color: white !important; margin: 8px 0; font-size: 1.8rem;">{c_discount}% OFF</h3>
                        <p style="margin: 0; font-size: 0.8rem; opacity: 0.8;">Calculated Subsidy: ${estimated_budget:,.2f} | Bounded ({min_discount_val}% - {max_discount_val}%)</p>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            
            # --- BULK GMAIL CAMPAIGN DISPATCHER ---
            st.markdown("#### 📤 Bulk Gmail Campaign Dispatcher")
            gmail_connected = render_gmail_connection()
            email_column = find_email_column(results)

            if not email_column:
                st.error("Your dataset needs an email column such as Email or Customer_Email.")
            else:
                # Build one personalised email preview for every customer with a valid address.
                campaign_rows = []
                seen_emails = set()
                skipped_invalid = 0
                skipped_duplicate = 0

                for _, row in results.iterrows():
                    recipient = str(row.get(email_column, "")).strip()
                    if not recipient or recipient.lower() in {"nan", "none"} or "@" not in recipient:
                        skipped_invalid += 1
                        continue

                    email_key = recipient.lower()
                    if email_key in seen_emails:
                        skipped_duplicate += 1
                        continue
                    seen_emails.add(email_key)

                    name = str(row.get("Name", row.get("CustomerID", "Customer")))
                    if name.lower() == "nan":
                        name = str(row.get("CustomerID", "Customer"))

                    discount = row.get("Assigned_Discount_%", 0)
                    try:
                        discount_text = f"{float(discount):.1f}".rstrip("0").rstrip(".")
                    except (TypeError, ValueError):
                        discount_text = str(discount)

                    message_text = str(row.get("Automated_Message", ""))
                    if message_text.lower() == "nan":
                        message_text = ""

                    segment = str(row.get("Segment", "Customer"))
                    if segment.lower() == "nan":
                        segment = "Customer"

                    subject = f"Your personalised {discount_text}% offer is here!"
                    body = (
                        f"Hello {name},\\n\\n"
                        f"{message_text}\\n\\n"
                        f"As a {segment} customer, you have a personalised discount "
                        f"of {discount_text}% OFF.\\n\\n"
                        "Thank you for shopping with us!"
                    )
                    campaign_rows.append({
                        "Customer": name,
                        "Email": recipient,
                        "Segment": segment,
                        "Discount": f"{discount_text}%",
                        "Subject": subject,
                        "Message": body
                    })

                campaign_df = pd.DataFrame(campaign_rows)
                st.write(f"**Ready to send:** {len(campaign_df):,} unique customer email(s)")
                st.caption(
                    f"Skipped invalid/missing email addresses: {skipped_invalid:,} · "
                    f"Skipped duplicate email addresses: {skipped_duplicate:,}"
                )

                if not campaign_df.empty:
                    with st.expander("Preview personalised campaign emails", expanded=True):
                        st.dataframe(
                            campaign_df[["Customer", "Email", "Segment", "Discount", "Subject"]],
                            use_container_width=True,
                            hide_index=True
                        )
                        preview_choice = st.selectbox(
                            "Preview message for customer:",
                            campaign_df["Email"].tolist(),
                            key="bulk_email_preview_choice"
                        )
                        preview_row = campaign_df[campaign_df["Email"] == preview_choice].iloc[0]
                        st.text(preview_row["Message"])

                    st.warning(
                        "Only send marketing emails to customers who have agreed to receive them. "
                        "Gmail and Google impose sending and API quotas; this is not unlimited sending. "
                        "Large campaigns may be stopped or partially sent if a quota is reached."
                    )
                    confirm_bulk_send = st.checkbox(
                        f"I confirm that these {len(campaign_df):,} customers have consented to receive marketing emails.",
                        key="bulk_email_consent"
                    )

                    if st.button(
                        f"📨 Send Mail to All {len(campaign_df):,} Customers",
                        type="primary",
                        disabled=(not confirm_bulk_send or not gmail_connected),
                        key="send_bulk_campaign"
                    ):
                        delivery_log = []
                        progress = st.progress(0)
                        status_text = st.empty()
                        sent_count = 0
                        failed_count = 0

                        try:
                            with st.spinner("Connecting to your authorised Gmail account..."):
                                gmail_service = get_gmail_service()

                            for index, campaign in campaign_df.iterrows():
                                status_text.write(
                                    f"Sending {index + 1:,} of {len(campaign_df):,}: "
                                    f"{campaign['Email']}"
                                )
                                try:
                                    raw = MIMEText(campaign["Message"], "plain", "utf-8")
                                    raw["to"] = campaign["Email"]
                                    raw["subject"] = campaign["Subject"]
                                    encoded = base64.urlsafe_b64encode(raw.as_bytes()).decode("utf-8")
                                    response = gmail_service.users().messages().send(
                                        userId="me", body={"raw": encoded}
                                    ).execute()

                                    sent_count += 1
                                    delivery_log.append({
                                        "Customer": campaign["Customer"],
                                        "Email": campaign["Email"],
                                        "Status": "Sent",
                                        "Gmail Message ID": response.get("id", "")
                                    })
                                except Exception as exc:
                                    failed_count += 1
                                    delivery_log.append({
                                        "Customer": campaign["Customer"],
                                        "Email": campaign["Email"],
                                        "Status": f"Failed: {str(exc)[:180]}",
                                        "Gmail Message ID": ""
                                    })

                                progress.progress((index + 1) / len(campaign_df))

                            st.session_state["bulk_email_delivery_log"] = pd.DataFrame(delivery_log)
                            status_text.empty()
                            st.success(
                                f"Campaign completed. Successfully sent: {sent_count:,} · "
                                f"Failed: {failed_count:,} · "
                                f"Total processed: {len(campaign_df):,}"
                            )
                            if failed_count:
                                st.warning(
                                    "Some emails failed. Review the delivery report below; "
                                    "failed emails are not reported as sent."
                                )
                            st.balloons()
                        except Exception as exc:
                            st.error(f"Could not start the Gmail campaign: {exc}")
                            st.info(
                                "Confirm that the [google_oauth] Secrets are correct, "
                                "the Gmail API is enabled, and the sender account is an authorised "
                                "Google OAuth test user."
                            )

                if "bulk_email_delivery_log" in st.session_state:
                    st.markdown("#### 📋 Latest Bulk Email Delivery Report")
                    st.dataframe(
                        st.session_state["bulk_email_delivery_log"],
                        use_container_width=True,
                        hide_index=True
                    )
                    st.download_button(
                        "📥 Download Email Delivery Report",
                        data=st.session_state["bulk_email_delivery_log"].to_csv(index=False).encode("utf-8"),
                        file_name="bulk_email_delivery_report.csv",
                        mime="text/csv"
                    )

        st.markdown("<br>", unsafe_allow_html=True)

    # ==========================================
    # DIVISION 4: DATASET TABLE & EXPORT CENTER
    # ==========================================
    if view_mode in ["Show All Divisions", "4: Master Dataset & Export Center"]:
        st.markdown("### 📋 Division 4: Master Dataset & Export Center")
        st.markdown(f"All customer discounts are strictly clamped between **{min_discount_val}%** and **{max_discount_val}%**:")
        st.dataframe(results, use_container_width=True)
        
        st.download_button(
            label="📥 Download Master Campaign Results (CSV)",
            data=results.to_csv(index=False).encode('utf-8'),
            file_name='master_marketing_campaigns.csv',
            mime='text/csv',
        )

else:
    st.markdown("""
        <div class="content-card" style="text-align: center;">
            <h3 style="color: #ffffff; margin-bottom: 10px;">👉 Get Started: Upload Your Dataset</h3>
            <p style="color: #94a3b8; font-size: 1rem;">Please upload your customer dataset (.csv or .xlsx) in the left sidebar to generate individual behavioral discounts bounded by your custom limits.</p>
        </div>
    """, unsafe_allow_html=True)
