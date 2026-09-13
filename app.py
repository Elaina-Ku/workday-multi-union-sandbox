import streamlit as st
import pandas as pd
from datetime import datetime

# -------------------------------------------------------------
# 1. Page Configuration & Header
# -------------------------------------------------------------
st.set_page_config(
    page_title="Workday Multi-Union HRIS Sandbox",
    page_icon="⚙️",
    layout="wide"
)

st.title("⚙️ Workday Multi-Union HRIS & Payroll Configuration Sandbox")
st.caption("Proof-of-Concept Enterprise Architecture: Simulating Workday HCM, Time Tracking, Benefits, and Payroll Integration")

# -------------------------------------------------------------
# 2. Session State Initialization (Persistent Configuration Data)
# -------------------------------------------------------------
if "init" not in st.session_state:
    st.session_state.init = True
    
    # Tab 1: Foundation Data
    st.session_state.unions = {
        "UNION_USW_2009": {"Name": "United Steelworkers Local 2009", "Site": "Ontario Concentrator Plant", "CA_ID": "CA_USW_ON"},
        "UNION_MET_9414": {"Name": "Syndicat des Métallos Local 9414", "Site": "Val-d'Or Underground Mine", "CA_ID": "CA_MET_QC"}
    }
    
    # Tab 2: Wage Grids
    st.session_state.grades = {
        "CA_USW_ON": {
            "Step 1 (Probation)": 32.50,
            "Step 2 (Junior)": 35.00,
            "Step 3 (Intermediate)": 38.50,
            "Step 4 (Journeyperson)": 42.00
        },
        "CA_MET_QC": {
            "Step 1 (Probation)": 34.00,
            "Step 2 (Junior)": 37.00,
            "Step 3 (Intermediate)": 40.50,
            "Step 4 (Journeyperson)": 44.50
        }
    }
    
    # Tab 3: Time Tracking Rules
    st.session_state.callout_min = 4.0
    st.session_state.callout_mult = 2.0
    st.session_state.night_diff = 3.50
    st.session_state.underground_prem = 4.25
    st.session_state.anti_pyramiding = True
    
    # Tab 4: Deduction Rules
    st.session_state.usw_dues_pct = 1.85
    st.session_state.usw_dues_flat = 5.00
    st.session_state.met_dues_hours = 2.0  # 2.0 hours base pay per month
    st.session_state.mepp_rate_usw = 2.50   # $2.50 per worked hour
    st.session_state.mepp_rate_met = 3.00   # $3.00 per worked hour

# 5개 탭 선언
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏛️ Tab 1: Foundation & Condition Rules",
    "📊 Tab 2: Compensation & Step Progression",
    "⏱️ Tab 3: Time Tracking & CBA Rules",
    "💳 Tab 4: Payroll Deductions & MEPP",
    "🚀 Tab 5: Pay Run Simulation & Trace Engine"
])

# =============================================================
# TAB 1: Foundation & Condition Rules
# =============================================================
with tab1:
    st.header("1. HCM Foundation: Organization & Collective Agreement Setup")
    st.markdown("""
    Workday uses **Condition Rules** evaluated during Business Processes (such as *Hire* or *Change Job*) 
    to automatically assign workers to the correct **Union Organization** and **Collective Agreement**.
    """)
    st.write("---")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Active Union Organizations")
        for u_id, u_info in st.session_state.unions.items():
            st.info(f"**{u_info['Name']}**\n- Org ID: `{u_id}`\n- Operating Jurisdiction: {u_info['Site']}\n- Linked Collective Agreement: `{u_info['CA_ID']}`")

    with col2:
        st.subheader("Workday Condition Rule Matrix (Logic Engine)")
        cr_matrix = [
            {"Rule Name": "CR_ELIG_USW_Plant", "Evaluation Expression": "Location == 'Ontario Concentrator' AND Job_Family == 'Operations'", "Assigned CA": "CA_USW_ON"},
            {"Rule Name": "CR_ELIG_Metallos_Mine", "Evaluation Expression": "Location == 'Val-d'Or Mine' AND Union_Required == True", "Assigned CA": "CA_MET_QC"},
            {"Rule Name": "CR_EXCLUDE_Corporate", "Evaluation Expression": "Location == 'Vancouver HQ' OR Management_Level in ['Manager', 'Director']", "Assigned CA": "Non-Union Exempt"}
        ]
        st.table(pd.DataFrame(cr_matrix))

    st.caption("💡 When a worker is assigned a Collective Agreement, Workday automatically exposes union-specific benefits, compensation step lists, and time calculation rules.")

# =============================================================
# TAB 2: Compensation & Step Progression
# =============================================================
with tab2:
    st.header("2. Compensation: Grade Profiles & Step Progression")
    st.markdown("""
    Under multi-union collective agreements, pay rates are locked to **Grade Profiles and Steps**. 
    Workers progress based on accumulated hours or bargaining unit seniority dates.
    """)
    st.write("---")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("USW Local 2009 (Ontario Plant) Wage Grid")
        for step, rate in st.session_state.grades["CA_USW_ON"].items():
            st.session_state.grades["CA_USW_ON"][step] = st.number_input(
                f"USW {step} Rate ($/hr)", value=float(rate), step=0.25, key=f"usw_{step}"
            )

    with c2:
        st.subheader("Métallos Local 9414 (Quebec Mine) Wage Grid")
        for step, rate in st.session_state.grades["CA_MET_QC"].items():
            st.session_state.grades["CA_MET_QC"][step] = st.number_input(
                f"Métallos {step} Rate ($/hr)", value=float(rate), step=0.25, key=f"met_{step}"
            )

    st.write("---")
    st.subheader("Step Progression Trigger Rule")
    st.markdown("""
    - **Step 1 ➔ Step 2:** Automatically executes upon completion of **480 Worked Hours** (Probation period cleared).
    - **Step 2 ➔ Step 3:** Automatically triggers at **1 Year (2,080 Hours)** of Bargaining Unit Seniority.
    - **Step 3 ➔ Step 4:** Automatically triggers at **2 Years (4,160 Hours)** or upon Red Seal Journeyperson certification.
    """)

# =============================================================
# TAB 3: Time Tracking & CBA Rules
# =============================================================
with tab3:
    st.header("3. Time Tracking: Collective Agreement Calculation Rules")
    st.markdown("Configure how frontline timecards are scrubbed and translated into pay components.")
    st.write("---")

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.subheader("Emergency Call-Out Minimum (Art. 17.01)")
        st.session_state.callout_min = st.number_input("Minimum Guaranteed Paid Hours", value=st.session_state.callout_min, step=0.5)
        st.session_state.callout_mult = st.number_input("Call-Out Multiplier (e.g. 2.0x Double Time)", value=st.session_state.callout_mult, step=0.25)
        st.caption("Punch intervals below this threshold will automatically expand in the calculation engine.")

    with col_t2:
        st.subheader("Shift Premiums & Anti-Pyramiding")
        st.session_state.night_diff = st.number_input("Graveyard Shift Premium ($/hr)", value=st.session_state.night_diff, step=0.25)
        st.session_state.underground_prem = st.number_input("Underground Hazard Premium ($/hr)", value=st.session_state.underground_prem, step=0.25)
        st.session_state.anti_pyramiding = st.checkbox("Enforce Anti-Pyramiding Rule (Prevent stacking of OT & Premiums)", value=st.session_state.anti_pyramiding)

# =============================================================
# TAB 4: Payroll Deductions & MEPP
# =============================================================
with tab4:
    st.header("4. Payroll: Union Dues & Multi-Employer Pension (MEPP)")
    st.markdown("Set up complex deduction formulas and third-party remittance (TPR) integrations.")
    st.write("---")

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.subheader("USW Local 2009 Formulas")
        st.session_state.usw_dues_pct = st.number_input("USW Dues Percentage of Gross (%)", value=st.session_state.usw_dues_pct, step=0.05)
        st.session_state.usw_dues_flat = st.number_input("USW Monthly Strike Fund (Flat $)", value=st.session_state.usw_dues_flat, step=1.0)
        st.session_state.mepp_rate_usw = st.number_input("Steelworkers Pension Trust (MEPP $/worked hr)", value=st.session_state.mepp_rate_usw, step=0.25)

    with col_d2:
        st.subheader("Métallos Local 9414 Formulas")
        st.session_state.met_dues_hours = st.number_input("Métallos Monthly Dues (Base Wage Hours equivalent)", value=st.session_state.met_dues_hours, step=0.5)
        st.session_state.mepp_rate_met = st.number_input("Fonds de retraite Métallos (MEPP $/worked hr)", value=st.session_state.mepp_rate_met, step=0.25)

# =============================================================
# TAB 5: Pay Run Simulation & Trace Engine
# =============================================================
with tab5:
    st.header("5. Pay Run Execution & Workday Calculation Trace")
    st.markdown("""
    Select an employee and input shift details. The engine will evaluate the configuration 
    and display a **real-time Workday Execution Trace Log** illustrating how rules interacted.
    """)
    st.write("---")

    # Worker Selection
    workers = {
        "Marc Bouchard (EMP1001)": {"Location": "Val-d'Or Mine (QC)", "Role": "Underground Miner", "CA": "CA_MET_QC", "Default_Step": "Step 3 (Intermediate)", "Underground_Role": True},
        "Sarah Jenkins (EMP1002)": {"Location": "Ontario Concentrator (ON)", "Role": "Mill Operator", "CA": "CA_USW_ON", "Default_Step": "Step 2 (Junior)", "Underground_Role": False},
        "David Tremblay (EMP1003)": {"Location": "Val-d'Or Mine (QC)", "Role": "Electrician", "CA": "CA_MET_QC", "Default_Step": "Step 4 (Journeyperson)", "Underground_Role": True},
        "Elena Rostova (EMP1004)": {"Location": "Vancouver HQ (BC)", "Role": "Mine Engineer", "CA": "Non-Union Exempt", "Default_Step": "N/A (Salary $95k)", "Underground_Role": False}
    }

    c_sel1, c_sel2, c_sel3 = st.columns(3)
    with c_sel1:
        sel_worker_name = st.selectbox("Select Worker Profile", list(workers.keys()))
        worker = workers[sel_worker_name]
    with c_sel2:
        st.info(f"**Workday HCM Profile:**\n- Operating Location: {worker['Location']}\n- Collective Agreement: `{worker['CA']}`\n- Role: {worker['Role']}")
    with c_sel3:
        if worker['CA'] != "Non-Union Exempt":
            step_options = list(st.session_state.grades[worker['CA']].keys())
            sel_step = st.selectbox("Current Wage Step", step_options, index=step_options.index(worker['Default_Step']))
            base_hourly = st.session_state.grades[worker['CA']][sel_step]
            st.metric("Effective Base Hourly Wage", f"${base_hourly:.2f}/hr")
        else:
            base_hourly = 95000.0 / 2080.0
            st.metric("Salary Equivalent Hourly", f"${base_hourly:.2f}/hr")

    st.write("---")
    st.subheader("Shift Timecard Input")
    st1, st2, st3, st4 = st.columns(4)
    with st1:
        worked_hours = st.number_input("Logged Shift Duration (hrs)", min_value=0.0, max_value=24.0, value=3.0, step=0.5)
    with st2:
        is_callout = st.checkbox("Emergency Call-Out Flag", value=True)
    with st3:
        is_night = st.checkbox("Graveyard Shift (Night)", value=True)
    with st4:
        is_ug = st.checkbox("Underground Work Area", value=worker['Underground_Role'], disabled=not worker['Underground_Role'])

    if st.button("⚡ Execute Workday Pay Calculation Run", type="primary"):
        # Execution Trace Log Container
        trace_logs = []
        
        # Step 1: Condition Rule Resolution
        trace_logs.append(f"<b>[HCM Evaluator]</b> Worker assigned to Collective Agreement: <code>{worker['CA']}</code> based on Location ({worker['Location']}).")
        
        # Step 2: Compensation Evaluation
        trace_logs.append(f"<b>[Compensation]</b> Resolved base pay: <code>${base_hourly:.2f}/hr</code>.")
        
        # Step 3: Time Calculation Rules
        payable_hours = worked_hours
        applied_ot_rate = 1.0
        
        if is_callout and worker['CA'] != "Non-Union Exempt":
            if worked_hours < st.session_state.callout_min:
                payable_hours = st.session_state.callout_min
                applied_ot_rate = st.session_state.callout_mult
                trace_logs.append(f"<b>[Time Tracking Rule: Art. 17.01]</b> Call-Out triggered. Logged {worked_hours}h expanded to minimum <code>{payable_hours}h</code> at <code>{applied_ot_rate}x</code> base rate.")
            else:
                applied_ot_rate = st.session_state.callout_mult
                trace_logs.append(f"<b>[Time Tracking Rule]</b> Call-Out applied at <code>{applied_ot_rate}x</code>.")
        else:
            trace_logs.append(f"<b>[Time Tracking Rule]</b> Standard shift duration evaluated: <code>{payable_hours}h</code>.")

        # Earnings Calculation
        gross_base_pay = payable_hours * base_hourly * applied_ot_rate
        shift_prem_pay = (worked_hours * st.session_state.night_diff) if (is_night and worker['CA'] != "Non-Union Exempt") else 0.0
        hazard_prem_pay = (worked_hours * st.session_state.underground_prem) if (is_ug and worker['CA'] != "Non-Union Exempt") else 0.0
        
        if is_night and worker['CA'] != "Non-Union Exempt":
            trace_logs.append(f"<b>[Shift Differential]</b> Night premium added: {worked_hours}h × ${st.session_state.night_diff:.2f} = <code>${shift_prem_pay:.2f}</code>.")
        if is_ug and worker['CA'] != "Non-Union Exempt":
            trace_logs.append(f"<b>[Hazard Premium]</b> Underground premium added: {worked_hours}h × ${st.session_state.underground_prem:.2f} = <code>${hazard_prem_pay:.2f}</code>.")
            
        total_gross = gross_base_pay + shift_prem_pay + hazard_prem_pay
        
        # Step 4: Deductions (Dues & MEPP)
        union_dues = 0.0
        mepp_pension = 0.0
        
        if worker['CA'] == "CA_USW_ON":
            union_dues = (total_gross * (st.session_state.usw_dues_pct / 100)) + (st.session_state.usw_dues_flat / 2) # Bi-weekly estimate
            mepp_pension = worked_hours * st.session_state.mepp_rate_usw
            trace_logs.append(f"<b>[Payroll Deduction: USW]</b> Union Dues ({st.session_state.usw_dues_pct}% + Flat): <code>${union_dues:.2f}</code>.")
            trace_logs.append(f"<b>[Payroll Deduction: MEPP]</b> Pension Trust ({worked_hours} worked hrs × ${st.session_state.mepp_rate_usw:.2f}): <code>${mepp_pension:.2f}</code>.")
        elif worker['CA'] == "CA_MET_QC":
            union_dues = (base_hourly * st.session_state.met_dues_hours) / 2 # Bi-weekly estimate
            mepp_pension = worked_hours * st.session_state.mepp_rate_met
            trace_logs.append(f"<b>[Payroll Deduction: Métallos]</b> Union Dues ({st.session_state.met_dues_hours}h base wage): <code>${union_dues:.2f}</code>.")
            trace_logs.append(f"<b>[Payroll Deduction: MEPP]</b> Pension Trust ({worked_hours} worked hrs × ${st.session_state.mepp_rate_met:.2f}): <code>${mepp_pension:.2f}</code>.")
        else:
            trace_logs.append("<b>[Payroll Deductions]</b> Non-union profile. Zero union dues or MEPP deductions evaluated.")

        net_estimate = total_gross - union_dues - mepp_pension

        # Render Trace Log
        st.write("---")
        st.subheader("📋 Workday System Execution Trace Log")
        with st.expander("Click to view step-by-step Rule Engine Evaluation", expanded=True):
            for log in trace_logs:
                st.markdown(f"• {log}", unsafe_allow_html=True)

        # Output Summary
        st.write("---")
        st.subheader("💰 Pay Calculation Results")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Payable Hours Credited", f"{payable_hours:.1f} hrs", f"{payable_hours - worked_hours:+.1f}h CBA adjustment")
        m2.metric("Total Shift Gross Pay", f"${total_gross:,.2f}")
        m3.metric("Union Dues & Pension", f"${union_dues + mepp_pension:,.2f}", f"Dues: ${union_dues:.2f}")
        m4.metric("Estimated Net Pay", f"${net_estimate:,.2f}", "Pre-tax estimate")

        # GL Clearing Matrix
        st.write("---")
        st.subheader("📑 General Ledger (GL) Interface Distribution")
        gl_records = [
            {"Account Code": "5100-LABOUR-DIR", "Description": "Direct Operational Labour", "Debit ($)": f"${gross_base_pay:,.2f}", "Credit ($)": "-"},
            {"Account Code": "5110-SHIFT-DIFF", "Description": "Night / Hazard Shift Differentials", "Debit ($)": f"${shift_prem_pay + hazard_prem_pay:,.2f}", "Credit ($)": "-"},
            {"Account Code": "2150-DUES-PAYABLE", "Description": "Union Dues Third-Party Remittance", "Debit ($)": "-", "Credit ($)": f"${union_dues:,.2f}"},
            {"Account Code": "2160-MEPP-PAYABLE", "Description": "Multi-Employer Pension Trust Clearing", "Debit ($)": "-", "Credit ($)": f"${mepp_pension:,.2f}"},
            {"Account Code": "2100-NET-PAYROLL", "Description": "Accrued Net Payroll Clearing", "Debit ($)": "-", "Credit ($)": f"${net_estimate:,.2f}"}
        ]
        st.table(pd.DataFrame(gl_records))
