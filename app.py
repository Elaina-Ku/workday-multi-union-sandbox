import streamlit as st
import pandas as pd
from datetime import datetime

# -------------------------------------------------------------
# 1. Page Configuration & Header
# -------------------------------------------------------------
st.set_page_config(
    page_title="Workday Multi-Union Bi-Weekly HRIS Sandbox",
    page_icon="⚙️",
    layout="wide"
)

st.title("⚙️ Workday Multi-Union HRIS & Bi-Weekly Payroll Sandbox")
st.caption("Proof-of-Concept Enterprise Architecture: Simulating Bi-Weekly (26 Pay Cycles) Payroll & Collective Agreement Configuration")

# -------------------------------------------------------------
# 2. Session State Initialization (Bi-Weekly Configuration Rules)
# -------------------------------------------------------------
if "init" not in st.session_state:
    st.session_state.init = True
    
    # Tab 1: Foundation Data
    st.session_state.unions = {
        "UNION_USW_2009": {"Name": "United Steelworkers Local 2009", "Site": "Ontario Concentrator Plant", "CA_ID": "CA_USW_ON", "Frequency": "Bi-Weekly (26 P/Y)"},
        "UNION_MET_9414": {"Name": "Syndicat des Métallos Local 9414", "Site": "Val-d'Or Underground Mine", "CA_ID": "CA_MET_QC", "Frequency": "Bi-Weekly (26 P/Y)"}
    }
    
    # Tab 2: Wage Grids (Hourly base rates)
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
    
    # Tab 4: Bi-Weekly Deduction Rules
    st.session_state.usw_dues_pct = 1.85
    st.session_state.usw_dues_biweekly_flat = 2.50  # Half of monthly $5.00 strike fund
    st.session_state.met_dues_hours_per_month = 2.0  # 2 hours base wage per month (converted to 1 hr bi-weekly)
    st.session_state.mepp_rate_usw = 2.50           # $2.50 per worked hour
    st.session_state.mepp_rate_met = 3.00           # $3.00 per worked hour

# Tabs Declaration
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏛️ Tab 1: Foundation & Condition Rules",
    "📊 Tab 2: Compensation & Step Progression",
    "⏱️ Tab 3: Time Tracking & CBA Rules",
    "💳 Tab 4: Bi-Weekly Deductions & MEPP",
    "🚀 Tab 5: Bi-Weekly Pay Run Simulation"
])

# =============================================================
# TAB 1: Foundation & Condition Rules
# =============================================================
with tab1:
    st.header("1. HCM Foundation: Organization & Collective Agreement Setup")
    st.markdown("""
    Workday uses **Condition Rules** evaluated during Business Processes (*Hire*, *Change Job*) 
    to automatically enroll workers into the correct **Union Organization**, **Collective Agreement**, and **Bi-Weekly Pay Group**.
    """)
    st.write("---")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Active Union Organizations")
        for u_id, u_info in st.session_state.unions.items():
            st.info(f"**{u_info['Name']}**\n- Org ID: `{u_id}`\n- Operating Site: {u_info['Site']}\n- Linked CA: `{u_info['CA_ID']}`\n- Pay Frequency: **{u_info['Frequency']}**")

    with col2:
        st.subheader("Workday Condition Rule Matrix")
        cr_matrix = [
            {"Rule Name": "CR_ELIG_USW_Plant", "Evaluation Expression": "Location == 'Ontario Concentrator' AND Job_Family == 'Operations'", "Pay Frequency": "Bi-Weekly", "Assigned CA": "CA_USW_ON"},
            {"Rule Name": "CR_ELIG_Metallos_Mine", "Evaluation Expression": "Location == 'Val-d'Or Mine' AND Union_Required == True", "Pay Frequency": "Bi-Weekly", "Assigned CA": "CA_MET_QC"},
            {"Rule Name": "CR_EXCLUDE_Corporate", "Evaluation Expression": "Location == 'Vancouver HQ' OR Management_Level in ['Manager', 'Director']", "Pay Frequency": "Bi-Weekly", "Assigned CA": "Non-Union Exempt"}
        ]
        st.table(pd.DataFrame(cr_matrix))

    st.caption("💡 All union bargaining units and corporate salaried staff operate on a synchronized 14-day bi-weekly payroll cycle (26 pay periods per tax year).")

# =============================================================
# TAB 2: Compensation & Step Progression
# =============================================================
with tab2:
    st.header("2. Compensation: Grade Profiles & Step Progression")
    st.markdown("""
    Under multi-union collective agreements, pay rates are locked to **Grade Profiles and Steps**. 
    Workers progress automatically based on accumulated hours or seniority.
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
    st.subheader("Bi-Weekly Equivalent Base Earnings (Standard 80.0 Hours)")
    usw_biweekly_preview = {k: f"${v * 80:,.2f}" for k, v in st.session_state.grades["CA_USW_ON"].items()}
    met_biweekly_preview = {k: f"${v * 80:,.2f}" for k, v in st.session_state.grades["CA_MET_QC"].items()}
    
    col_prev1, col_prev2 = st.columns(2)
    with col_prev1:
        st.write("**USW Bi-Weekly Gross Pay (80h Base):**")
        st.json(usw_biweekly_preview)
    with col_prev2:
        st.write("**Métallos Bi-Weekly Gross Pay (80h Base):**")
        st.json(met_biweekly_preview)

# =============================================================
# TAB 3: Time Tracking & CBA Rules
# =============================================================
with tab3:
    st.header("3. Time Tracking: Collective Agreement Calculation Rules")
    st.markdown("Configure how bi-weekly timecard batches are scrubbed and translated into payable hours.")
    st.write("---")

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.subheader("Emergency Call-Out Minimum (Art. 17.01)")
        st.session_state.callout_min = st.number_input("Minimum Guaranteed Paid Hours per Call-Out", value=st.session_state.callout_min, step=0.5)
        st.session_state.callout_mult = st.number_input("Call-Out Multiplier (e.g. 2.0x Double Time)", value=st.session_state.callout_mult, step=0.25)
        st.caption("Any emergency call-out incident in the 2-week period below this threshold auto-expands to the guaranteed minimum.")

    with col_t2:
        st.subheader("Bi-Weekly Shift Premiums")
        st.session_state.night_diff = st.number_input("Graveyard Shift Premium ($/hr)", value=st.session_state.night_diff, step=0.25)
        st.session_state.underground_prem = st.number_input("Underground Hazard Premium ($/hr)", value=st.session_state.underground_prem, step=0.25)
        st.session_state.anti_pyramiding = st.checkbox("Enforce Anti-Pyramiding Rule (Prevent stacking overtime on shift premiums)", value=st.session_state.anti_pyramiding)

# =============================================================
# TAB 4: Bi-Weekly Deductions & MEPP
# =============================================================
with tab4:
    st.header("4. Payroll: Bi-Weekly Union Dues & MEPP Pensions")
    st.markdown("Configure bi-weekly deduction schedules for multi-union remittances and pension trusts.")
    st.write("---")

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.subheader("USW Local 2009 Bi-Weekly Deductions")
        st.session_state.usw_dues_pct = st.number_input("USW Dues Percentage of Gross (%)", value=st.session_state.usw_dues_pct, step=0.05)
        st.session_state.usw_dues_biweekly_flat = st.number_input("USW Flat Bi-Weekly Strike Fund ($)", value=st.session_state.usw_dues_biweekly_flat, step=0.50)
        st.session_state.mepp_rate_usw = st.number_input("Steelworkers Pension Trust (MEPP $/worked hr)", value=st.session_state.mepp_rate_usw, step=0.25)
        st.info("Formula: `(Bi-Weekly Gross × 1.85%) + $2.50 flat`")

    with col_d2:
        st.subheader("Métallos Local 9414 Bi-Weekly Deductions")
        st.session_state.met_dues_hours_per_month = st.number_input("Métallos Monthly Dues Standard (Hours of Base Pay)", value=st.session_state.met_dues_hours_per_month, step=0.5)
        st.session_state.mepp_rate_met = st.number_input("Fonds de retraite Métallos (MEPP $/worked hr)", value=st.session_state.mepp_rate_met, step=0.25)
        st.info(f"Bi-Weekly Conversion: `(Base Hourly Rate × {st.session_state.met_dues_hours_per_month}h) ÷ 2` = 1.0 hour base wage deducted per bi-weekly cycle.")

# =============================================================
# TAB 5: Bi-Weekly Pay Run Simulation & Trace Engine
# =============================================================
with tab5:
    st.header("5. Bi-Weekly Pay Run Simulation & Calculation Trace Engine")
    st.markdown("""
    Execute a full **14-Day (80-Hour Regular Schedule) Bi-Weekly Pay Period Calculation**. 
    Inspect how Workday's calculation engine applies grade progression, overtime thresholds, contractual minimums, and deduction sequencing.
    """)
    st.write("---")

    # Worker Profiles
    workers = {
        "Marc Bouchard (EMP1001)": {
            "Location": "Val-d'Or Mine (QC)", "Role": "Underground Miner", "CA": "CA_MET_QC",
            "Default_Step": "Step 3 (Intermediate)", "Underground_Role": True, "Pay_Type": "Hourly Union"
        },
        "Sarah Jenkins (EMP1002)": {
            "Location": "Ontario Concentrator (ON)", "Role": "Mill Operator", "CA": "CA_USW_ON",
            "Default_Step": "Step 2 (Junior)", "Underground_Role": False, "Pay_Type": "Hourly Union"
        },
        "David Tremblay (EMP1003)": {
            "Location": "Val-d'Or Mine (QC)", "Role": "Industrial Electrician", "CA": "CA_MET_QC",
            "Default_Step": "Step 4 (Journeyperson)", "Underground_Role": True, "Pay_Type": "Hourly Union"
        },
        "Elena Rostova (EMP1004)": {
            "Location": "Vancouver HQ (BC)", "Role": "Senior Mine Engineer", "CA": "Non-Union Exempt",
            "Default_Step": "Salaried Staff ($95,000)", "Underground_Role": False, "Pay_Type": "Salaried Staff", "Annual_Salary": 95000.0
        }
    }

    # Worker Selection Bar
    c_sel1, c_sel2, c_sel3 = st.columns(3)
    with c_sel1:
        sel_worker_name = st.selectbox("Select Employee for Pay Period", list(workers.keys()))
        worker = workers[sel_worker_name]
    with c_sel2:
        st.info(f"**Workday HCM Profile:**\n- Operating Location: {worker['Location']}\n- Collective Agreement: `{worker['CA']}`\n- Pay Schedule: **Bi-Weekly (Pay Period 18 of 26)**")
    with c_sel3:
        if worker["Pay_Type"] == "Hourly Union":
            step_options = list(st.session_state.grades[worker['CA']].keys())
            sel_step = st.selectbox("Assigned Wage Step", step_options, index=step_options.index(worker['Default_Step']))
            base_hourly = st.session_state.grades[worker['CA']][sel_step]
            st.metric("Effective Base Hourly Rate", f"${base_hourly:.2f}/hr")
        else:
            base_hourly = worker["Annual_Salary"] / 2080.0
            biweekly_salary = worker["Annual_Salary"] / 26.0
            st.metric("Bi-Weekly Standard Gross Salary", f"${biweekly_salary:,.2f}", f"${base_hourly:.2f}/hr equivalent")

    st.write("---")
    st.subheader("14-Day Bi-Weekly Timecard Batch Inputs")

    if worker["Pay_Type"] == "Hourly Union":
        t_col1, t_col2, t_col3 = st.columns(3)
        with t_col1:
            st.markdown("**Core Working Hours (14-Day Period)**")
            reg_hours_input = st.number_input("Standard Regular Hours Worked", min_value=0.0, max_value=120.0, value=80.0, step=1.0)
            ot15_hours_input = st.number_input("Scheduled Overtime Hours (1.5x)", min_value=0.0, max_value=40.0, value=6.0, step=0.5)

        with t_col2:
            st.markdown("**Emergency Call-Out Incidents (Art. 17.01)**")
            callout_count = st.number_input("Number of Emergency Call-Outs in Pay Period", min_value=0, max_value=5, value=1, step=1)
            callout_actual_hrs = st.number_input("Total Actual Hours Punched on Call-Outs", min_value=0.0, max_value=24.0, value=2.0, step=0.5)
            st.caption(f"Contract guarantees {st.session_state.callout_min}h minimum per incident @ {st.session_state.callout_mult}x base rate.")

        with t_col3:
            st.markdown("**Shift Premium Qualifying Hours**")
            night_hours_input = st.number_input("Graveyard Shift Hours (19:00 - 07:00)", min_value=0.0, max_value=84.0, value=36.0, step=1.0)
            ug_hours_input = st.number_input("Underground Shift Hours", min_value=0.0, max_value=84.0, value=48.0 if worker["Underground_Role"] else 0.0, step=1.0, disabled=not worker["Underground_Role"])
    else:
        st.info("Salaried corporate positions are exempt from standard daily and bi-weekly overtime tracking pursuant to provincial employment standards.")
        reg_hours_input = 80.0
        ot15_hours_input = 0.0
        callout_count = 0
        callout_actual_hrs = 0.0
        night_hours_input = 0.0
        ug_hours_input = 0.0

    # Pay Calculation Execution
    if st.button("⚡ Execute Bi-Weekly Pay Calculation (Gross-to-Net)", type="primary"):
        trace = []
        trace.append(f"<b>[Pay Group Resolution]</b> Employee mapped to <code>Bi-Weekly Standard Schedule (Cycle 18/26)</code>. Base hourly resolved to <code>${base_hourly:.2f}/hr</code>.")

        # 1. Hours & Gross Earnings Calculation
        if worker["Pay_Type"] == "Hourly Union":
            # Regular Base Pay
            reg_gross = reg_hours_input * base_hourly
            trace.append(f"<b>[Earnings: REG_UN]</b> {reg_hours_input:.1f} Regular Hours × ${base_hourly:.2f} = <code>${reg_gross:,.2f}</code>.")

            # Overtime Pay (1.5x)
            ot15_gross = ot15_hours_input * (base_hourly * 1.5)
            if ot15_hours_input > 0:
                trace.append(f"<b>[Earnings: OT_15U]</b> {ot15_hours_input:.1f} Overtime Hours × (${base_hourly:.2f} × 1.5) = <code>${ot15_gross:,.2f}</code>.")

            # Emergency Call-Outs (2.0x with 4h Guarantee per incident)
            callout_guaranteed_hrs = callout_count * st.session_state.callout_min
            credited_callout_hrs = max(callout_actual_hrs, callout_guaranteed_hrs)
            callout_gross = credited_callout_hrs * (base_hourly * st.session_state.callout_mult)

            if callout_count > 0:
                if callout_actual_hrs < callout_guaranteed_hrs:
                    trace.append(f"<b>[Time Tracking Rule: Art. 17.01]</b> {callout_count} Call-out(s) logged {callout_actual_hrs:.1f} actual hrs. <b>Auto-expanded to contractual minimum {credited_callout_hrs:.1f} hrs @ {st.session_state.callout_mult}x</b> = <code>${callout_gross:,.2f}</code>.")
                else:
                    trace.append(f"<b>[Time Tracking Rule: Art. 17.01]</b> {callout_count} Call-out(s) logged {credited_callout_hrs:.1f} hrs @ {st.session_state.callout_mult}x = <code>${callout_gross:,.2f}</code>.")
            else:
                callout_gross = 0.0

            # Shift Differentials (Night & Underground)
            shift_prem_gross = night_hours_input * st.session_state.night_diff
            hazard_prem_gross = ug_hours_input * st.session_state.underground_prem
            if night_hours_input > 0:
                trace.append(f"<b>[Premium: SHFT_GY]</b> {night_hours_input:.1f} Graveyard Hours × ${st.session_state.night_diff:.2f}/hr = <code>${shift_prem_gross:,.2f}</code>.")
            if ug_hours_input > 0:
                trace.append(f"<b>[Premium: PREM_UG]</b> {ug_hours_input:.1f} Underground Hours × ${st.session_state.underground_prem:.2f}/hr = <code>${hazard_prem_gross:,.2f}</code>.")

            total_biweekly_gross = reg_gross + ot15_gross + callout_gross + shift_prem_gross + hazard_prem_gross
            total_worked_hours = reg_hours_input + ot15_hours_input + callout_actual_hrs
            total_payable_hours = reg_hours_input + ot15_hours_input + credited_callout_hrs

        else:
            # Salaried Staff
            total_biweekly_gross = worker["Annual_Salary"] / 26.0
            reg_gross = total_biweekly_gross
            ot15_gross = 0.0
            callout_gross = 0.0
            shift_prem_gross = 0.0
            hazard_prem_gross = 0.0
            total_worked_hours = 80.0
            total_payable_hours = 80.0
            trace.append(f"<b>[Earnings: SAL_NR]</b> Bi-Weekly Gross Salary evaluated: <code>${total_biweekly_gross:,.2f}</code>.")

        # 2. Bi-Weekly Union Dues & MEPP Pension Calculations
        union_dues = 0.0
        mepp_pension = 0.0

        if worker["CA"] == "CA_USW_ON":
            union_dues = (total_biweekly_gross * (st.session_state.usw_dues_pct / 100.0)) + st.session_state.usw_dues_biweekly_flat
            mepp_pension = total_worked_hours * st.session_state.mepp_rate_usw
            trace.append(f"<b>[Deduction: USW Dues]</b> ({st.session_state.usw_dues_pct}% of ${total_biweekly_gross:,.2f}) + ${st.session_state.usw_dues_biweekly_flat:.2f} flat = <code>${union_dues:,.2f}</code>.")
            trace.append(f"<b>[Deduction: USW MEPP]</b> {total_worked_hours:.1f} Total Worked Hours × ${st.session_state.mepp_rate_usw:.2f}/hr = <code>${mepp_pension:,.2f}</code>.")

        elif worker["CA"] == "CA_MET_QC":
            # Métallos dues: 2.0 hours base pay per month / 2 = 1.0 hour base pay bi-weekly
            union_dues = (base_hourly * st.session_state.met_dues_hours_per_month) / 2.0
            mepp_pension = total_worked_hours * st.session_state.mepp_rate_met
            trace.append(f"<b>[Deduction: Métallos Dues]</b> (1.0 Hour Base Wage Equivalent): <code>${union_dues:,.2f}</code>.")
            trace.append(f"<b>[Deduction: Métallos MEPP]</b> {total_worked_hours:.1f} Total Worked Hours × ${st.session_state.mepp_rate_met:.2f}/hr = <code>${mepp_pension:,.2f}</code>.")
        else:
            trace.append("<b>[Deductions: Union Exemption]</b> Non-union classification. Zero union dues and zero MEPP contributions assessed.")

        # 3. Statutory Deductions (Bi-Weekly Canadian Payroll Estimates)
        # Bi-weekly basic CPP/QPP exemption = $3,500 / 26 = $134.62
        pensionable_earnings = max(0.0, total_biweekly_gross - 134.62)
        if "QC" in worker["Location"]:
            cpp_qpp_tax = pensionable_earnings * 0.064  # QPP 6.4%
            ei_tax = total_biweekly_gross * (0.0132 + 0.00494)  # Reduced EI + QPIP
            prov_tax_agency = "CRA & Revenu Québec (QPP, QPIP, Reduced EI)"
        else:
            cpp_qpp_tax = pensionable_earnings * 0.0595  # CPP 5.95%
            ei_tax = total_biweekly_gross * 0.0166  # Standard Federal EI 1.66%
            prov_tax_agency = "CRA Sole Agency (CPP, Federal EI)"

        stat_deductions = cpp_qpp_tax + ei_tax
        total_employee_deductions = union_dues + mepp_pension + stat_deductions
        estimated_net_pay = total_biweekly_gross - total_employee_deductions

        trace.append(f"<b>[Statutory Deductions]</b> Evaluated under <code>{prov_tax_agency}</code>: Pension=${cpp_qpp_tax:,.2f}, EI/QPIP=${ei_tax:,.2f}.")

        # 4. Display Results & Dashboards
        st.write("---")
        st.subheader("📋 Workday Bi-Weekly Pay Calculation Trace Log")
        with st.expander("Click to inspect complete Rule Engine Execution Steps", expanded=True):
            for step_log in trace:
                st.markdown(f"• {step_log}", unsafe_allow_html=True)

        st.write("---")
        st.subheader("💰 Bi-Weekly Pay Period Summary (Period 18 of 26)")

        res1, res2, res3, res4 = st.columns(4)
        res1.metric("Payable Hours Credited", f"{total_payable_hours:.1f} hrs", f"{total_payable_hours - total_worked_hours:+.1f}h CBA adjustment")
        res2.metric("Bi-Weekly Gross Earnings", f"${total_biweekly_gross:,.2f}")
        res3.metric("Total Deductions", f"${total_employee_deductions:,.2f}", f"Dues+MEPP: ${union_dues + mepp_pension:,.2f}")
        res4.metric("Estimated Net Pay", f"${estimated_net_pay:,.2f}", "Direct Deposit")

        # Detailed Earnings Breakdown
        c_tbl, c_ded = st.columns([3, 2])
        with c_tbl:
            st.markdown("**Bi-Weekly Gross Component Distribution**")
            earnings_breakdown = [
                {"Pay Component": "REG_UN / SAL_NR", "Description": "Regular Base Wages", "Hours": reg_hours_input, "Amount": f"${reg_gross:,.2f}"},
                {"Pay Component": "OT_15U", "Description": "Overtime (1.5x Base)", "Hours": ot15_hours_input, "Amount": f"${ot15_gross:,.2f}"},
                {"Pay Component": "CALL_MIN", "Description": "Emergency Call-Out (2.0x Guaranteed)", "Hours": credited_callout_hrs if worker["Pay_Type"] == "Hourly Union" else 0.0, "Amount": f"${callout_gross:,.2f}"},
                {"Pay Component": "SHFT_GY", "Description": "Graveyard Differential ($3.50/h)", "Hours": night_hours_input, "Amount": f"${shift_prem_gross:,.2f}"},
                {"Pay Component": "PREM_UG", "Description": "Underground Hazard ($4.25/h)", "Hours": ug_hours_input, "Amount": f"${hazard_prem_gross:,.2f}"}
            ]
            st.table(pd.DataFrame(earnings_breakdown))

        with c_ded:
            st.markdown("**Bi-Weekly Deductions & Remittances**")
            ded_breakdown = [
                {"Deduction Code": "DED_UNION_DUES", "Description": "Union Dues Remittance", "Amount": f"${union_dues:,.2f}"},
                {"Deduction Code": "DED_MEPP_PENSION", "Description": "Multi-Employer Pension Trust", "Amount": f"${mepp_pension:,.2f}"},
                {"Deduction Code": "TAX_CPP_QPP", "Description": "CPP / QPP Statutory Contribution", "Amount": f"${cpp_qpp_tax:,.2f}"},
                {"Deduction Code": "TAX_EI_QPIP", "Description": "EI & QPIP Statutory Premiums", "Amount": f"${ei_tax:,.2f}"}
            ]
            st.table(pd.DataFrame(ded_breakdown))

        # 5. General Ledger (GL) Balanced Journal Entry
        st.write("---")
        st.subheader("📑 Bi-Weekly General Ledger (GL) Interface Distribution")
        st.caption("Double-entry accounting journal lines automatically mapped to Workday Financials cost centers and balance sheet accounts.")

        gl_journal = [
            {"Account Code": "5100-LABOUR-REG", "Account Description": "Direct Operational Labour Expense", "Debit ($)": f"${reg_gross + ot15_gross:,.2f}", "Credit ($)": "-"},
            {"Account Code": "5105-LABOUR-CALLOUT", "Account Description": "Emergency Call-Out Premium Expense", "Debit ($)": f"${callout_gross:,.2f}", "Credit ($)": "-"},
            {"Account Code": "5110-SHIFT-DIFF", "Account Description": "Shift Differentials & Mine Hazard", "Debit ($)": f"${shift_prem_gross + hazard_prem_gross:,.2f}", "Credit ($)": "-"},
            {"Account Code": "2150-DUES-PAYABLE", "Account Description": "Union Dues Third-Party Remittance", "Debit ($)": "-", "Credit ($)": f"${union_dues:,.2f}"},
            {"Account Code": "2160-MEPP-PAYABLE", "Account Description": "Multi-Employer Pension Trust Clearing", "Debit ($)": "-", "Credit ($)": f"${mepp_pension:,.2f}"},
            {"Account Code": "2180-TAXES-PAYABLE", "Account Description": "Statutory Remittances Payable (CRA/RQ)", "Debit ($)": "-", "Credit ($)": f"${stat_deductions:,.2f}"},
            {"Account Code": "2100-NET-PAYROLL", "Account Description": "Net Direct Deposit Clearing Account", "Debit ($)": "-", "Credit ($)": f"${estimated_net_pay:,.2f}"}
        ]
        st.table(pd.DataFrame(gl_journal))
