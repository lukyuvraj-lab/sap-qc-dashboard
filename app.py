import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="SAP QC Plant Dashboard", layout="wide")

st.title("🏭 SAP Quality Control Plant Dashboard")
st.write("Filter pending inspection metrics dynamically by plant codes and material group rules.")

# --- DYNAMIC DATABASE LOADER FRAMEWORK ---
DB_FILE = "electrical_groups.txt"

# Read your stored group values safely
if os.path.exists(DB_FILE):
    with open(DB_FILE, "r") as f:
        ELECTRICAL_GROUPS = [line.strip() for line in f.read().splitlines() if line.strip()]
else:
    # Small fallback list if the file is missing
    ELECTRICAL_GROUPS = ["10113", "10104", "10103", "10096", "10098", "10097"]

# --- SIDEBAR DATABASE MANAGER TOOL ---
st.sidebar.header("📁 Electrical Groups Manager")
st.sidebar.write(f"Total groups stored: **{len(ELECTRICAL_GROUPS)}**")

# Interactive tool to temporarily append code layers right on screen
new_code = st.sidebar.text_input("Quick-add temporary Material Group code:", value="")
if new_code.strip():
    clean_code = new_code.strip()
    if clean_code not in ELECTRICAL_GROUPS:
        ELECTRICAL_GROUPS.append(clean_code)
        st.sidebar.success(f"Code {clean_code} added to current workspace session!")

# Collapsible section to inspect all active electrical codes
with st.sidebar.expander("👁️ View all stored Electrical Group codes"):
    st.json(ELECTRICAL_GROUPS)


# --- MAIN ENGINE WORKSPACE ---
uploaded_file = st.file_uploader("Upload SAP QC Spreadsheet (.xlsx or .xls)", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        # Read the file cleanly
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
        
        # --- DATA CLEANING LAYER ---
        df[plant_col] = df[plant_col].fillna("").astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
        df[mat_col] = df[mat_col].fillna("").astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
        df[grn_col] = df[grn_col].fillna("").astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
        df[curr_col] = df[curr_col].fillna("").astype(str).str.strip()
        
        # Strip all thousands-separator blank space characters inside numbers safely
        df[val_col] = df[val_col].astype(str).str.replace(r'\s+', '', regex=True).str.replace(',', '')
        df[val_col] = pd.to_numeric(df[val_col], errors='coerce').fillna(0.0)
        
        # Target active items currently pending inspection checks
        pending_df = df[df[val_col] > 0].copy()
        
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
        
        # Metrics Calculations
        total_elec_value = elec_df[val_col].sum()
        total_elec_grns = elec_df[grn_col].nunique()
        total_elec_lots = len(elec_df)  # Active items / rows count as total lots
        
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
        
        # Detailed Splits Tables Tab Panels
        tab1, tab2 = st.tabs(["⚡ Filtered Electrical Rows", "⚙️ Filtered Mechanical Rows"])
        
        with tab1:
            st.subheader("Active Electrical Batches")
            if not elec_df.empty:
                display_elec = elec_df[[grn_col, mat_col, curr_col, val_col]].copy()
                display_elec.columns = ['GRN NO (Col I)', 'Material Group (Col D)', 'Currency (Col N)', 'Value in QualInsp. (Col T)']
                st.dataframe(display_elec.sort_values(by='Value in QualInsp. (Col T)', ascending=False), use_container_width=True)
            else:
                st.warning("No pending Electrical items found inside this plant data.")
                
        with tab2:
            st.subheader("Active Mechanical / Remaining Batches")
            if not mech_df.empty:
                display_mech = mech_df[[grn_col, mat_col, curr_col, val_col]].copy()
                display_mech.columns = ['GRN NO (Col I)', 'Material Group (Col D)', 'Currency (Col N)', 'Value in QualInsp. (Col T)']
                st.dataframe(display_mech.sort_values(by='Value in QualInsp. (Col T)', ascending=False), use_container_width=True)
            else:
                st.info("No remaining mechanical records waiting in queue.")
                
    except Exception as e:
        st.error(f"Error executing sheet index alignments: {e}")
else:
    st.info("Awaiting SAP spreadsheet upload to calculate metrics.")
