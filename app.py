import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="SAP QC Plant Dashboard", layout="wide")

st.title("🏭 SAP Quality Control Pending Dashboard")
st.write("Match your columns manually below to process records matching **MOVE TO QC**.")

# --- DATABASE LOADER ---
DB_FILE = "electrical_groups.txt"

if os.path.exists(DB_FILE):
    with open(DB_FILE, "r") as f:
        raw_lines = f.read().splitlines()
        ELECTRICAL_GROUPS = [line.strip() for line in raw_lines if line.strip()]
else:
    ELECTRICAL_GROUPS = ["10113", "10104", "10103", "10096", "10098", "10097"]

ELECTRICAL_GROUPS = list(set(ELECTRICAL_GROUPS))

st.sidebar.header("📁 Electrical Groups Manager")
st.sidebar.write(f"Total groups loaded: **{len(ELECTRICAL_GROUPS)}**")
with st.sidebar.expander("👁️ View active Electrical codes"):
    st.json(sorted(ELECTRICAL_GROUPS))

uploaded_file = st.file_uploader("Upload SAP Spreadsheet (.xlsx or .xls)", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        # Load data cleanly
        df = pd.read_excel(uploaded_file)
        all_cols = [str(c) for c in df.columns]
        
        # --- MANUAL VISUAL COLUMN OVERRIDES ---
        st.subheader("⚙️ Column Configuration Panel")
        st.info("Select the correct columns from your uploaded file if they weren't auto-selected:")
        
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            plant_col = st.selectbox("Plant Column (C):", all_cols, index=next((i for i, c in enumerate(all_cols) if "plant" in c.lower()), min(2, len(all_cols)-1)))
        with c2:
            mat_id_col = st.selectbox("Material Column:", all_cols, index=next((i for i, c in enumerate(all_cols) if "material" in c.lower() and "group" not in c.lower()), min(1, len(all_cols)-1)))
        with c3:
            mat_col = st.selectbox("Material Group Column (D):", all_cols, index=next((i for i, c in enumerate(all_cols) if "group" in c.lower() or "grup" in c.lower()), min(3, len(all_cols)-1)))
        with c4:
            grn_col = st.selectbox("GRN No Column (I):", all_cols, index=next((i for i, c in enumerate(all_cols) if "grn" in c.lower()), min(8, len(all_cols)-1)))
        with c5:
            val_col = st.selectbox("QualInsp Value Column (T):", all_cols, index=next((i for i, c in enumerate(all_cols) if "insp" in c.lower() or "value" in c.lower()), min(19, len(all_cols)-1)))

        # Find status column for MOVE TO QC
        status_col = None
        for col in df.columns:
            if df[col].astype(str).str.upper().str.contains("MOVE TO QC", na=False).any():
                status_col = col
                break
        
        if not status_col:
            status_col = st.selectbox("Status / Action Column:", all_cols, index=0)
            
        st.write("---")

        # --- DATA CLEANING LAYER ---
        df[plant_col] = df[plant_col].fillna("").astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
        df[grn_col] = df[grn_col].fillna("").astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
        df[mat_id_col] = df[mat_id_col].fillna("").astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
        df[mat_col] = df[mat_col].fillna("").astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
        
        # Clean currency punctuation spacing
        df[val_col] = df[val_col].astype(str).str.replace(r'[\s,]', '', regex=True)
        df[val_col] = pd.to_numeric(df[val_col], errors='coerce').fillna(0.0)
        
        # --- FILTER CORES ---
        qc_mask = df[status_col].astype(str).str.upper().str.contains("MOVE TO QC", na=False)
        pending_df = df[qc_mask & (df[val_col] > 0)].copy()
        
        # --- PLANT NAVIGATOR ---
        st.subheader("🌐 Plant Selection Workspace")
        available_plants = sorted(list(pending_df[plant_col].unique()))
        
        def format_plant_label(p_id):
            if "1201" in str(p_id):
                return "🏢 1201 - ECITY"
            elif "1202" in str(p_id):
                return "🏭 1202 - Vemgal"
            return f"📍 Plant {p_id}"
            
        if available_plants:
            selected_plant_id = st.selectbox(
                "Select Plant to View Worklist Data:", 
                options=available_plants,
                format_func=format_plant_label
            )
            
            plant_filtered_df = pending_df[pending_df[plant_col] == selected_plant_id]
            
            # --- DEPARTMENT SPLIT ---
            elec_df = plant_filtered_df[plant_filtered_df[mat_col].isin(ELECTRICAL_GROUPS)]
            mech_df = plant_filtered_df[~plant_filtered_df[mat_col].isin(ELECTRICAL_GROUPS)]
            
            total_elec_value = elec_df[val_col].sum()
            total_elec_grns = elec_df[grn_col].nunique()
            total_elec_lots = len(elec_df)
            
            total_mech_value = mech_df[val_col].sum()
            total_mech_grns = mech_df[grn_col].nunique()
            total_mech_lots = len(mech_df)
            
            # --- UI METRICS ---
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
                    display_elec = elec_df[[grn_col, mat_id_col, mat_col, val_col]].copy()
                    display_elec.columns = ['GRN NO', 'Material ID', 'Material Group', 'Value in QualInsp.']
                    st.dataframe(display_elec.sort_values(by='Value in QualInsp.', ascending=False), use_container_width=True)
                else:
                    st.warning("No pending Electrical rows found matching your 100 codes list under 'MOVE TO QC'.")
                    
            with tab2:
                st.subheader("Active Mechanical / Remaining Batches")
                if not mech_df.empty:
                    display_mech = mech_df[[grn_col, mat_id_col, mat_col, val_col]].copy()
                    display_mech.columns = ['GRN NO', 'Material ID', 'Material Group', 'Value in QualInsp.']
                    st.dataframe(display_mech.sort_values(by='Value in QualInsp.', ascending=False), use_container_width=True)
                else:
                    st.info("No remaining mechanical records waiting in queue.")
        else:
            st.warning("No records containing active values (>0) were found under the 'MOVE TO QC' status filter.")
            
    except Exception as e:
        st.error(f"Error executing validation dashboard layer: {e}")
else:
    st.info("Awaiting SAP spreadsheet upload to calculate metrics.")
