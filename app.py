import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="SAP QC Inspection Dashboard", layout="wide")

st.title("🏭 SAP Quality Control Pending Dashboard")
st.write("Upload your raw SAP inspection export sheet to separate Electrical and Mechanical workloads.")

# --- STEP 3A: LOAD MATERIAL GROUPS FROM THE STORED FILE ---
DB_FILE = "electrical_groups.txt"

if os.path.exists(DB_FILE):
    with open(DB_FILE, "r") as f:
        # Read file, drop empty lines, remove hidden spaces
        ELECTRICAL_GROUPS = [line.strip() for line in f.read().splitlines() if line.strip()]
else:
    # Safe backup fallback list if the file is missing
    ELECTRICAL_GROUPS = ["10113", "10104", "10103", "10096", "10098", "10097"]

# Sidebar display to verify stored list
st.sidebar.header("📁 Stored Database")
st.sidebar.write("**Active Electrical Groups:**")
st.sidebar.json(ELECTRICAL_GROUPS)

# --- STEP 3B: FILE UPLOADER ENGINE ---
uploaded_file = st.file_uploader("Upload SAP QC Spreadsheet (.xlsx or .xls)", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        # Read the file cleanly
        df = pd.read_excel(uploaded_file)
        
        # Exact column headers from your layout screenshot
        mat_col = "Material Group"
        grn_col = "GRN NO"
        val_col = "Value in QualInsp."
        
        # Verify that the required columns are present in the Excel sheet
        if mat_col in df.columns and grn_col in df.columns and val_col in df.columns:
            
            # --- DATA CLEANING ---
            df[mat_col] = df[mat_col].fillna("").astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
            df[grn_col] = df[grn_col].fillna("").astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
            
            # Clean thousands-separator spaces inside values (e.g., "12 322.10" -> "12322.10")
            df[val_col] = df[val_col].astype(str).str.replace(r'\s+', '', regex=True)
            df[val_col] = pd.to_numeric(df[val_col], errors='coerce').fillna(0)
            
            # --- FILTERING & SPLIT LOGIC ---
            pending_df = df[df[val_col] > 0]
            
            # Split items using the database loaded from your text file
            elec_df = pending_df[pending_df[mat_col].isin(ELECTRICAL_GROUPS)]
            mech_df = pending_df[~pending_df[mat_col].isin(ELECTRICAL_GROUPS)]
            
            # Calculate Summary Numbers
            total_elec_value = elec_df[val_col].sum()
            total_elec_grns = elec_df[grn_col].nunique()
            
            total_mech_value = mech_df[val_col].sum()
            total_mech_grns = mech_df[grn_col].nunique()
            
            # --- UI METRICS LAYOUT ---
            st.write("### 💰 Grand Pending Summary")
            col1, col2 = st.columns(2)
            with col1:
                st.metric(
                    label="⚡ Total Electrical Pending Value", 
                    value=f"₹{total_elec_value:,.2f}", 
                    delta=f"{total_elec_grns} Unique GRNs Active"
                )
            with col2:
                st.metric(
                    label="⚙️ Total Mechanical Pending Value (Other Groups)", 
                    value=f"₹{total_mech_value:,.2f}", 
                    delta=f"{total_mech_grns} Unique GRNs Active"
                )
                
            st.write("---")
            
            # --- DEPARTMENT TAB WORKLISTS ---
            tab1, tab2 = st.tabs(["⚡ Electrical Items", "⚙️ Mechanical Items"])
            
            with tab1:
                st.subheader("Electrical Worklist Details")
                if not elec_df.empty:
                    display_elec = elec_df[[grn_col, mat_col, val_col]].copy()
                    display_elec.columns = ['GRN No.', 'Material Group', 'Pending Value']
                    st.dataframe(display_elec.sort_values(by='Pending Value', ascending=False), use_container_width=True)
                else:
                    st.warning("No pending items found matching your stored Electrical Material Groups.")
                    
            with tab2:
                st.subheader("Mechanical / Other Worklist Details")
                if not mech_df.empty:
                    display_mech = mech_df[[grn_col, mat_col, val_col]].copy()
                    display_mech.columns = ['GRN No.', 'Material Group', 'Pending Value']
                    st.dataframe(display_mech.sort_values(by='Pending Value', ascending=False), use_container_width=True)
                else:
                    st.info("No mechanical items pending inspection processing.")
                    
        else:
            st.error(f"Mapping error! Ensure your column headers match exactly: **'{mat_col}'**, **'{grn_col}'**, and **'{val_col}'**.")
            st.write("Detected columns in your file:", list(df.columns))
            
    except Exception as e:
        st.error(f"Error executing dashboard mapping logic: {e}")
else:
    st.info("Awaiting SAP spreadsheet upload to calculate metrics.")
