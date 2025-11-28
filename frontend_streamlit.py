import streamlit as st
import pandas as pd
import requests
import base64

# ========================
# CONFIG
# ========================
BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Smart Data Analysis - Streamlit",
    layout="wide"
)

# ========================
# STATE VARIABLES
# ========================
if "session_id" not in st.session_state:
    st.session_state.session_id = None

if "sheets" not in st.session_state:
    st.session_state.sheets = []

if "file_name" not in st.session_state:
    st.session_state.file_name = None

if "domain" not in st.session_state:
    st.session_state.domain = None

# Title
st.title("Smart Data Analysis (Streamlit Version)")

st.markdown("""
Upload an Excel file → preview individual sheets → see statistical summary →  
Generate **manual** and **AI-generated** visualizations.
""")

# 1. FILE UPLOAD
st.header("1. Upload Excel File")

uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx", "xls"])

if uploaded_file is not None:
    if st.button("Upload & Process File"):
        with st.spinner("Uploading..."):
            files = {"file": uploaded_file}

            resp = requests.post(f"{BASE_URL}/upload/excel", files=files)

            if resp.status_code != 200:
                st.error(f"Upload failed: {resp.text}")
            else:
                data = resp.json()
                st.session_state.session_id = data["session_id"]
                st.session_state.sheets = data["sheets"]
                st.session_state.file_name = data["file_name"]
                st.session_state.domain = data["domain"]

                st.success("File uploaded successfully!")

# 2. SHEET PREVIEW + STATS
st.header("2. Preview & Statistical Summary")

if st.session_state.session_id and st.session_state.sheets:

    sheet_names = [s["sheet_name"] for s in st.session_state.sheets]
    selected_sheet = st.selectbox("Select a sheet", sheet_names)

    if st.button("Load Preview & Stats"):
        with st.spinner(f"Loading preview & stats for {selected_sheet}..."):

            # ---- Preview ----
            preview_req = {
                "session_id": st.session_state.session_id,
                "sheet_name": selected_sheet,
                "n_rows": 20
            }
            prev_res = requests.post(f"{BASE_URL}/data/preview", json=preview_req).json()

            if "rows" in prev_res:
                st.subheader("Preview (first 20 rows)")
                df_prev = pd.DataFrame(prev_res["rows"])
                st.dataframe(df_prev, use_container_width=True)

            # ---- Stats ----
            stats_req = {
                "session_id": st.session_state.session_id,
                "sheet_name": selected_sheet
            }
            stats_res = requests.post(f"{BASE_URL}/data/stats", json=stats_req).json()

            st.subheader("Statistical Summary")

            if "summary" in stats_res:
                stat_rows = []
                for col, details in stats_res["summary"].items():
                    stat_rows.append({
                        "Column": col,
                        "Type": details["type"],
                        "Details": str(details)
                    })
                st.table(pd.DataFrame(stat_rows))

            if "missing_values" in stats_res:
                mv = stats_res["missing_values"]
                mv_rows = []
                for col, cnt in mv["count"].items():
                    mv_rows.append({
                        "Column": col,
                        "Missing Count": cnt,
                        "Missing %": f"{mv['percent'][col]}%"
                    })
                st.subheader("Missing Values")
                st.table(pd.DataFrame(mv_rows))

# Create isolated containers for each visualization section
manual_container = st.container()
ai_container = st.container()

# 3. MANUAL VISUALIZATIONS (ALL SHEETS)
with manual_container:
    st.header("3. Generate Manual Visualizations (All Sheets)")

    if st.session_state.session_id:
        if st.button("Generate Manual Visualizations", key="btn_manual"):
            with st.spinner("Generating visualizations for ALL sheets..."):
                req = {
                    "session_id": st.session_state.session_id,
                    "sheet_name": ""
                }

                resp = requests.post(f"{BASE_URL}/data/visualizations/all", json=req)

                if resp.status_code != 200:
                    st.error(f"Error: {resp.text}")
                else:
                    st.session_state["manual_viz"] = resp.json()
                    st.success("Manual visualizations generated!")

    # Render MANUAL visualizations
    if "manual_viz" in st.session_state:
        data = st.session_state["manual_viz"]

        for sheet, visualizations in data.items():
            st.subheader(f"Sheet: {sheet}")

            cols = st.columns(3)
            for i, viz in enumerate(visualizations):
                with cols[i % 3]:
                    st.markdown(f"**{viz['chart_type']}**")
                    st.caption(f"X: {viz['x']} | Y: {viz.get('y','—')}")
                    st.write(viz["description"])

                    if viz["image_base64"]:
                        img_bytes = base64.b64decode(viz["image_base64"])
                        st.image(img_bytes, width=300)



# 4. AI-GENERATED VISUALIZATIONS
with ai_container:
    st.header("4. AI-Generated Visualization Suggestions")
    st.markdown("These visualizations come from the **/visualizations/ai** endpoint using Groq LLM.")

    if st.session_state.session_id:
        if st.button("Generate AI Visualizations", key="btn_ai"):
            with st.spinner("Generating AI visualizations for ALL sheets..."):
                req = {
                    "session_id": st.session_state.session_id,
                    "sheet_name": ""
                }

                resp = requests.post(f"{BASE_URL}/data/visualizations/ai", json=req)

                if resp.status_code != 200:
                    st.error(f"Error: {resp.text}")
                else:
                    st.session_state["ai_viz"] = resp.json()
                    st.success("AI visualizations generated!")

    # Render AI visualizations
    if "ai_viz" in st.session_state:
        data = st.session_state["ai_viz"]

        for sheet, visualizations in data.items():
            st.subheader(f"AI Sheet: {sheet}")

            cols = st.columns(3)
            for i, viz in enumerate(visualizations):
                with cols[i % 3]:
                    st.markdown(f"**{viz['chart_type']}**")
                    st.caption(f"X: {viz['x']} | Y: {viz.get('y','—')}")
                    st.write(viz["description"])

                    if viz["image_base64"]:
                        img_bytes = base64.b64decode(viz["image_base64"])
                        st.image(img_bytes, width=300)
