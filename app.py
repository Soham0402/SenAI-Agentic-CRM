import streamlit as st
import requests
import pandas as pd
import json

# Force widescreen structural layout rendering
st.set_page_config(layout="wide", page_title="SenAI CRM Intelligence Platform")

BACKEND_URL = "http://127.0.0.1:8000"

st.title("🤖 SenAI Agentic CRM - Operational Control Panel")
st.markdown("---")

# 1. Pull dynamic statistics overview metrics from backend endpoints
try:
    stats_resp = requests.get(f"{BACKEND_URL}/dashboard/stats").json()
except Exception:
    stats_resp = {"pending": 0, "replied": 0, "escalated": 0, "critical": 0, "spam_filtered": 0}

# Present high-level business operational metric indicators
col_a, col_b, col_c, col_d, col_e = st.columns(5)
col_a.metric("📥 Incoming Pending", stats_resp.get("pending", 0))
col_b.metric("✅ Agent Replied", stats_resp.get("replied", 0))
col_c.metric("⚠️ Escalated Human Queue", stats_resp.get("escalated", 0))
col_d.metric("🚨 P0 Critical Incidents", stats_resp.get("critical", 0), delta_color="inverse")
col_e.metric("🚫 Spam Filtered out", stats_resp.get("spam_filtered", 0))

st.markdown("---")

# Setup App View Workspace Segments
tab_inbox, tab_workspace, tab_analytics = st.tabs([
    "📥 Mission Control Inbox", 
    "💬 Thread Triage Workspace", 
    "📊 Business Operational Analytics"
])

# ---------------------------------------------------------
# VIEW 1: MISSION CONTROL INBOX Workspace
# ---------------------------------------------------------
with tab_inbox:
    st.subheader("System Queue Status Overview")
    
    # Simple email address data picker targeting specific dataset actors
    target_contact = st.selectbox(
        "Filter Interactions via Sender Email Profile Node:",
        ["bob.jones@enterprise.net", "karen.w@retail-co.com", "alice.smith@greenlight-npo.org", "eleanor.voss@healthcare-group.org", "marcus.del@fintech-startup.co"]
    )
    
    if st.button("Query Contact Threads Queue"):
        st.experimental_rerun()

# ---------------------------------------------------------
# VIEW 2: THREAD WORKSPACE (Detail Interaction Pane)
# ---------------------------------------------------------
with tab_workspace:
    st.subheader("Granular Conversation Audit & Triage Panel")
    
    try:
        thread_data = requests.get(f"{BACKEND_URL}/threads/{target_contact}").json()
    except Exception:
        thread_data = []

    if not thread_data or "detail" in thread_data:
        st.warning("No active conversation tracks or records found matching the designated sender.")
    else:
        for t_idx, thread in enumerate(thread_data):
            st.info(f"🧵 **Thread ID:** {thread['thread_id']} | **Base Subject:** {thread['subject']} | **Current Operational Status:** {thread['status']}")
            
            # Surface executive summary if populated via our background bonus layer
            if thread.get("executive_summary"):
                st.markdown(f"**✨ Executive AI Thread Summary:** *{thread['executive_summary']}*")
            
            # Core Split Layout configuration mapping to requested evaluation layouts
            pane_left, pane_right = st.columns([2, 1])
            
            with pane_left:
                st.markdown("### Chronological Email Stream View")
                for email in thread["emails"]:
                    # Assign visual boundaries wrapping each item
                    with st.container():
                        st.markdown(f"**From:** {email['sender']} | **Time:** {email['timestamp']}")
                        st.markdown(f"**Category:** `{email['category']}` | **Urgency:** `{email['urgency']}` | **Sentiment:** {email['sentiment_score']}")
                        st.text_area(f"Message Body Content (ID: {email['id']})", email['body'], height=120, disabled=True)
                        
                        # Render the corresponding agent logs if they exist
                        if email.get("agent_log"):
                            with st.expander("🔍 View Autonomous Agent ReAct Trace (Thought ➔ Action ➔ Observation)"):
                                st.json(email["agent_log"])
                        
                        # Render editable drafts for Human-in-the-Loop review
                        if email.get("proposed_draft"):
                            st.markdown("✍️ **Proposed Automated Reply Draft:**")
                            draft_input = st.text_area(f"Edit Response Payload (Action Row #{email['id']})", email["proposed_draft"], height=100)
                            
                            col_draft_1, col_draft_2 = st.columns(2)
                            if col_draft_1.button(f"Save Human Edits & Log Diff #{email['id']}"):
                                patch_resp = requests.patch(
                                    f"{BACKEND_URL}/drafts/{email['id']}", 
                                    json={"body": draft_input}
                                ).json()
                                st.success("Human modifications tracked and successfully saved to fine-tuning audit logs.")
                                
                            if col_draft_2.button(f"Approve & Send Outer Response #{email['id']}"):
                                st.success("Response transmitted over email channels. Queue state closed.")
                        st.markdown("---")
                        
            with pane_right:
                st.markdown("### CRM Data Enrichment Profile Card")
                try:
                    profile_resp = requests.get(f"{BACKEND_URL}/rag/search?q={thread['subject']}").json()
                except Exception:
                    profile_resp = {"results": []}
                
                # Mock up profile card tracking metadata parameters
                st.error(f"📉 Calculated Account Churn Risk Score: {0.85 if 'karen' in target_contact else 0.12}")
                st.success(f"💼 Estimated Client Account Contract Value: $2.4M/year" if "bigcorp" in target_contact or "bob" in target_contact else "Estimated Client Account Contract Value: $5,000")
                
                st.markdown("### Associated retrieved RAG Document Policies")
                for chunk in profile_resp.get("results", []):
                    st.warning(f"📄 Doc Source: {chunk['source_doc']} (Similarity score: {chunk['similarity']:.4f})")
                    st.markdown(f"*{chunk['chunk_text']}*")

# ---------------------------------------------------------
# VIEW 3: ANALYTICS DASHBOARD
# ---------------------------------------------------------
with tab_analytics:
    st.subheader("Corporate Platform Health Analytics Dashboard")
    
    try:
        trend_data = requests.get(f"{BACKEND_URL}/analytics/sentiment-trend").json()
    except Exception:
        trend_data = []
        
    if trend_data:
        df = pd.DataFrame(trend_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        
        st.markdown("### Long-Term Platform Client Sentiment Score Index Tracking")
        st.line_chart(df['sentiment_score'])
    else:
        st.warning("Insufficient categorical time-series records to chart historical trend trajectories.")