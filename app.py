import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="SAP QC Plant Dashboard", layout="wide")

st.title("🏭 SAP Quality Control Pending Dashboard")
st.write("Processing rows explicitly marked for **MOVE TO QC** extraction.")

# --- DYNAMIC DATABASE LOADER FRAMEWORK ---
DB_FILE = "electrical_groups.txt"

if os.path.exists(DB_FILE):
    with open(DB_FILE, "r") as f:
        raw_lines = f.read().splitlines()
        ELECTRICAL_GROUPS = [line.strip().split('.')[0] for line in raw_lines if line.strip()]
else:
    ELECTRICAL_GROUPS = ["10113", "10104", "10103", "10096", "10098", "10097"]

ELECTRICAL_GROUPS = list(set(ELECTRICAL_GROUPS))

st.sidebar.header("📁 Electrical Groups Manager")
st.sidebar.write(f"Total groups loaded: **{len(ELECTRICAL_GROUPS)}**")

uploaded_file = st.file_uploader("Upload SAP Spreadsheet (.xlsx or .xls)", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        
        # --- FIXED PATHWAYS FOR PLACEMENT MATCHING ---
        # Column C = Plant (Index 2) | Column D = Material Group (Index 3)
        # Column I = GRN NO (Index 8) | Column N = Currency (Index 13)
        # Column T = Value in QualInsp. (Index 19)
        plant_col = df.columns[2]
        mat_col = df.columns[3]
        grn_col = df.columns[8]
        curr_col = df.columns[13]
        val_col = df.columns[19]
        
        # --- STRIP LABELS & CLEAN DATA ---
        df[plant_col] = df[plant_col].fillna("").astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
        df[grn_col] = df[grn_col].fillna("").astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
        df[curr_col] = df[curr_col].fillna("").astype(str).str.strip()
        
        df[mat_col] = df[mat_col].fillna("").astype(str).str.strip()
        df[mat_col] = df[mat_col].apply(lambda x: str(x).split('.')[0] if '.' in str(x) else str(x))
        
        df[val_col] = df[val_col].astype(str).str.replace(r'\s+', '', regex=True).str.replace(',', '')
        df[val_col] = pd.to_numeric(df[val_col], errors='coerce').fillna(0.0)
        
        # --- STAGE FILTER: ONLY TAKE 'MOVE TO QC' ROWS ---
        # Scans columns dynamically to find where 'MOVE TO QC' text is written
        status_col = None
        for col in df.columns:
            if df[col].astype(str).str.upper().str.contains("MOVE TO QC").any():
                status_col = col
                break
        
        if status_col is not None:
            # Filter sheet to only look at 'MOVE TO QC' data rows
            qc_mask = df[status_col].astype(str).str.upper().str.contains("MOVE TO QC")
            pending_df = df[qc_mask & (df[val_col] > 0)].copy()
            st.success(f"Successfully locked onto target status column: **'{status_col}'**")
        else:
            # Fallback filter to validation values if string is missing
            pending_df = df[df[val_col] > 0].copy()
            st.warning("Could not find a column explicitly containing 'MOVE TO QC' text. Defaulting to all active values.")

        # --- PLANT NAVIGATION CONTROL INTERFACE ---
        st.write("---")
        st.subheader("🌐 Plant Selection Workspace")
        
        available_plants = sorted(list(pending_df[plant_col].unique()))
        
        def format_plant_label(p_id):
            if "1201" in p_id:
                return "🏢 1201 - ECITY"
            elif "1202" in p_id:
                return "🏭 1202 - Vemgal"
            return f"📍 Plant {p_id}"
            
        selected_plant_id = st.selectbox(
            "Select Plant to View Worklist Data:", 
            options=available_plants,
            format_func=format_plant_label
        )
        
        plant_filtered_df = pending_df[pending_df[plant_col] == selected_plant_id]
        
        # --- DEPARTMENT WORKLOAD DISTRIBUTOR ---
        elec_df = plant_filtered_df[plant_filtered_df[mat_col].isin(ELECTRICAL_GROUPS)]
        mech_df = plant_filtered_df[~plant_filtered_df[mat_col].isin(ELECTRICAL_GROUPS)]
        
        # Calculations (Row counts equal total inspection lots)
        total_elec_value = elec_df[val_col].sum()
        total_elec_grns = elec_df[grn_col].nunique()
        total_elec_lots = len(elec_df)
        
        total_mech_value = mech_df[val_col].sum()
        total_mech_grns = mech_df[grn_col].nunique()
        total_mech_lots = len(mech_df)
        
        # --- DISPLAY PANEL COMPONENT MAPS ---
        st.write("---")
        st.markdown(f"### 📈 Worklist Metrics for **{format_plant_label(selected_plant_id)}**")
        
        dash_col1, dash_col2 = st.columns(2)
        
        with dash_col1:
            st.markdown("#### ⚡ Electrical Department Summary")
            st.metric(label="Pending Inspection Value", value=f"₹{total_elec_value:,.2f}")
            sub_col1, sub_col2 = st.columns(2)
            sub_col1.metric(label="Pending GRNs Count", value=f"{total_elec_grns}")
            sub_col2.metric(label="Total Inspection Lots (Rows)", value=f"{total_elec_lots}")
            
        with dash_col2:
            st.markdown("#### ⚙️ Mechanical / Other Summary")
            st.metric(label="Pending Inspection Value", value=f"₹{total_mech_value:,.2f}")
            sub_col3, sub_col4 = st.columns(2)
            sub_col3.metric(label="Pending GRNs Count", value=f"{total_mech_grns}")
            sub_col4.metric(label="Total Inspection Lots (Rows)", value=f"{total_mech_lots}")
            
        st.write("---")
        
        tab1, tab2 = st.tabs(["⚡ Filtered Electrical Rows", "⚙️ Filtered Mechanical Rows"])
        
        with tab1:
            st.subheader("Active Electrical Batches")
            if not elec_df.empty:
                display_elec = elec_df[[grn_col, mat_col, curr_col, val_col]].copy()
                display_elec.columns = ['GRN NO (Col I)', 'Material Group (Col D)', 'Currency (Col N)', 'Value in QualInsp. (Col T)']
                st.dataframe(display_elec.sort_values(by='Value in QualInsp. (Col T)', ascending=False), use_container_width=True)
            else:
                st.warning("No pending Electrical rows found matching 'MOVE TO QC'.")
                
        with tab2:
            st.subheader("Active Mechanical / Remaining Batches")
            if not mech_df.empty:
                display_mech = mech_df[[grn_col, mat_col, curr_col, val_col]].copy()
                display_mech.columns = ['GRN NO (Col I)', 'Material Group (Col D)', 'Currency (Col N)', 'Value in QualInsp. (Col T)']
                st.dataframe(display_mech.sort_values(by='Value in QualInsp. (Col T)', ascending=False), use_container_width=True)
            else:
                st.info("No remaining mechanical records waiting in queue.")
                
    except Exception as e:
        st.error(f"Error executing sheet filter alignments: {e}")
else:
    st.info("Awaiting SAP spreadsheet upload to calculate metrics.")
