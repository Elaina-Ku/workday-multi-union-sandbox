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
st.caption("Enterprise Architecture: Multi-Jurisdiction Gross-to-Net Engine with Real-Time CRA & Revenu Québec Withholdings")

# -------------------------------------------------------------
# 2. Session State Initialization
# -------------------------------------------------------------
if "init" not in st.session_state:
    st.session_state.init = True
    
    st.session_state.unions = {
        "UNION_USW_2009": {"Name": "United Steelworkers Local 2009", "Site": "Ontario Concentrator Plant", "CA_ID": "CA_USW_ON", "Frequency": "Bi-Weekly (26 P/Y)"},
        "UNION_MET_9414": {"Name": "Syndicat des Métallos Local 9414", "Site": "Val-d'Or Underground Mine", "CA_ID": "CA_MET_QC", "Frequency": "Bi-Weekly (26 P/Y)"}
    }
    
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
    
    st.session_state.callout_min = 4.0
    st.session_state.callout_mult = 2.0
    st.session_state.night_diff = 3.50
    st.session_state.underground_prem = 4.25
    st.session_state.anti_pyramiding = True
    
    st.session_state.usw_dues_pct = 1.85
    st.session_state.usw_dues_biweekly_flat = 2.50
    st.session_state.met_dues_hours_per_month = 2.0
    st.session_state.mepp_rate_usw = 2.50
    st.session_state.mepp_rate_met = 3.00

# -------------------------------------------------------------
# 3. Canadian Statutory Tax Calculation Engine (CRA & RQ Formulas)
# -------------------------------------------------------------
def calculate_canadian_statutory_taxes(gross_pay, union_dues, mepp_ded, province):
    """
    Computes Canadian statutory withholdings for a 26-pay-period bi-weekly schedule.
    Follows CRA T4032 & Revenu Québec TP-1015.3 calculation principles.
    """
    # Step 1: Pre-tax deduction reduction for Taxable Income (ITA 8(1)(i)(iv))
    taxable_gross = max(0.0, gross_pay - union_dues - mepp_ded)
    
    # Step 2: Pension (CPP vs QPP) with Bi-Weekly Basic Exemption ($3,500 / 26 = $134.61)
    pensionable_earnings = max(0.0, gross_pay - 134.61)
    
    if province == "QC":
        cpp = 0.0
        qpp = min(4160.0 / 26.0, pensionable_earnings * 0.064)  # QPP 6.40%
        ei = min(781.0 / 26.0, gross_pay * 0.0132)             # Reduced EI 1.32%
        qpip = min(460.0 / 26.0, gross_pay * 0.00494)          # QPIP 0.494%
        er_health_tax = gross_pay * 0.0426                     # QC HSF 4.26%
        er_wcb = (gross_pay / 100.0) * 3.95                    # CNESST Mining
    else:
        cpp = min(3867.50 / 26.0, pensionable_earnings * 0.0595) # CPP 5.95%
        qpp = 0.0
        ei = min(1049.12 / 26.0, gross_pay * 0.0166)           # Standard EI 1.66%
        qpip = 0.0
        if province == "ON":
            er_health_tax = gross_pay * 0.0195                 # ON EHT 1.95%
            er_wcb = (gross_pay / 100.0) * 2.85                # WSIB Class D
        else: # BC
            er_health_tax = gross_pay * 0.0195                 # BC EHT 1.95%
            er_wcb = (gross_pay / 100.0) * 0.18                # WorkSafeBC

    # Employer Matching Contributions
    er_cpp_qpp = qpp if province == "QC" else cpp
    er_ei = ei * 1.4
    er_qpip = qpip * 1.4

    # Step 3: Income Tax (Federal & Provincial Progressive Rates)
    annual_taxable = taxable_gross * 26.0
    
    # Federal Tax Brackets
    if annual_taxable <= 55867:
        fed_tax_annual = annual_taxable * 0.15
    elif annual_taxable <= 111733:
        fed_tax_annual = (55867 * 0.15) + ((annual_taxable - 55867) * 0.205)
    elif annual_taxable <= 173205:
        fed_tax_annual = (55867 * 0.15) + ((111733 - 55867) * 0.205) + ((annual_taxable - 111733) * 0.26)
    else:
        fed_tax_annual = (55867 * 0.15) + ((111733 - 55867) * 0.205) + ((173205 - 111733) * 0.26) + ((annual_taxable - 173205) * 0.29)
    
    # Federal Basic Personal Amount (BPA) Credit
    fed_bpa_credit = 15705.0 * 0.15
    fed_tax_annual = max(0.0, fed_tax_annual - fed_bpa_credit)
    
    # Quebec 16.5% Federal Abatement
    if province == "QC":
        fed_tax_annual = fed_tax_annual * (1.0 - 0.165)
        
    fed_tax_biweekly = fed_tax_annual / 26.0

    # Provincial Tax Brackets
    if province == "QC":
        if annual_taxable <= 51780:
            qc_tax_annual = annual_taxable * 0.14
        elif annual_taxable <= 103545:
            qc_tax_annual = (51780 * 0.14) + ((annual_taxable - 51780) * 0.19)
        else:
            qc_tax_annual = (51780 * 0.14) + ((103545 - 51780) * 0.19) + ((annual_taxable - 103545) * 0.24)
        qc_bpa_credit = 18056.0 * 0.14
        prov_tax_biweekly = max(0.0, qc_tax_annual - qc_bpa_credit) / 26.0
    elif province == "ON":
        if annual_taxable <= 51446:
            on_tax_annual = annual_taxable * 0.0505
        elif annual_taxable <= 102894:
            on_tax_annual = (51446 * 0.0505) + ((annual_taxable - 51446) * 0.0915)
        else:
            on_tax_annual = (51446 * 0.0505) + ((102894 - 51446) * 0.0915) + ((annual_taxable - 102894) * 0.1116)
        on_bpa_credit = 12399.0 * 0.0505
        prov_tax_biweekly = max(0.0, on_tax_annual - on_bpa_credit) / 26.0
    else: # BC
        if annual_taxable <= 47937:
            bc_tax_annual = annual_taxable * 0.0506
        elif annual_taxable <= 95875:
            bc_tax_annual = (47937 * 0.0506) + ((annual_taxable - 47937) * 0.0770)
        else:
            bc_tax_annual = (47937 * 0.0506) + ((95875 - 47937) * 0.0770) + ((annual_taxable - 95875) * 0.1050)
        bc_bpa_credit = 12580.0 * 0.0506
        prov_tax_biweekly = max(0.0, bc_tax_annual - bc_bpa_credit) / 26.0

    return {
        "Taxable_Gross": taxable_gross,
        "CPP": cpp,
        "QPP": qpp,
        "EI": ei,
        "QPIP": qpip,
        "Federal_Tax": fed_tax_biweekly,
        "Provincial_Tax": prov_tax_biweekly,
        "Total_Stat_Taxes": cpp + qpp + ei + qpip + fed_tax_biweekly + prov_tax_biweekly,
        "ER_CPP_QPP": er_cpp_qpp,
        "ER_EI": er_ei,
        "ER_QPIP": er_qpip,
        "ER_Health_Tax": er_health_tax,
        "ER_WCB": er_wcb
    }

# -------------------------------------------------------------
# 4. Tabs Navigation
# -------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏛️ Tab 1: Foundation & Condition Rules",
    "📊 Tab 2: Compensation & Step Progression",
    "⏱️ Tab 3: Time Tracking & CBA Rules",
    "💳 Tab 4: Bi-Weekly Deductions & MEPP",
    "🚀 Tab 5: Bi-Weekly Pay Run & Official Paystub"
])

# =============================================================
# TAB 1: Foundation & Condition Rules
# =============================================================
with tab1:
    st.header("1. HCM Foundation: Organization & Collective Agreement Setup")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Active Union Organizations")
        for u_id, u_info in st.session_state.unions.items():
            st.info(f"**{u_info['Name']}**\n- Org ID: `{u_id}`\n- Operating Site: {u_info['Site']}\n- Linked CA: `{u_info['CA_ID']}`\n- Pay Frequency: **{u_info['Frequency']}**")
    with col2:
        st.subheader("Workday Condition Rule Matrix")
        cr_matrix = [
            {"Rule Name": "CR_ELIG_USW_Plant", "Evaluation": "Location == 'Ontario Concentrator' AND Job_Family == 'Operations'", "Assigned CA": "CA_USW_ON"},
            {"Rule Name": "CR_ELIG_Metallos_Mine", "Evaluation": "Location == 'Val-d'Or Mine' AND Union_Required == True", "Assigned CA": "CA_MET_QC"},
            {"Rule Name": "CR_EXCLUDE_Corporate", "Evaluation": "Location == 'Vancouver HQ' OR Management_Level == 'Manager+'", "Assigned CA": "Non-Union Exempt"}
        ]
        st.table(pd.DataFrame(cr_matrix))

# =============================================================
# TAB 2: Compensation & Step Progression
# =============================================================
with tab2:
    st.header("2. Compensation: Grade Profiles & Step Progression")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("USW Local 2009 (Ontario Plant) Wage Grid")
        for step, rate in st.session_state.grades["CA_USW_ON"].items():
            st.session_state.grades["CA_USW_ON"][step] = st.number_input(f"USW {step} Rate ($/hr)", value=float(rate), step=0.25, key=f"usw_{step}")
    with c2:
        st.subheader("Métallos Local 9414 (Quebec Mine) Wage Grid")
        for step, rate in st.session_state.grades["CA_MET_QC"].items():
            st.session_state.grades["CA_MET_QC"][step] = st.number_input(f"Métallos {step} Rate ($/hr)", value=float(rate), step=0.25, key=f"met_{step}")

# =============================================================
# TAB 3: Time Tracking & CBA Rules
# =============================================================
with tab3:
    st.header("3. Time Tracking: Collective Agreement Calculation Rules")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.subheader("Emergency Call-Out Minimum (Art. 17.01)")
        st.session_state.callout_min = st.number_input("Minimum Guaranteed Paid Hours per Call-Out", value=st.session_state.callout_min, step=0.5)
        st.session_state.callout_mult = st.number_input("Call-Out Multiplier (e.g. 2.0x Double Time)", value=st.session_state.callout_mult, step=0.25)
    with col_t2:
        st.subheader("Bi-Weekly Shift Premiums")
        st.session_state.night_diff = st.number_input("Graveyard Shift Premium ($/hr)", value=st.session_state.night_diff, step=0.25)
        st.session_state.underground_prem = st.number_input("Underground Hazard Premium ($/hr)", value=st.session_state.underground_prem, step=0.25)

# =============================================================
# TAB 4: Bi-Weekly Deductions & MEPP
# =============================================================
with tab4:
    st.header("4. Payroll: Bi-Weekly Union Dues & MEPP Pensions")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.subheader("USW Local 2009 Formulas")
        st.session_state.usw_dues_pct = st.number_input("USW Dues Percentage of Gross (%)", value=st.session_state.usw_dues_pct, step=0.05)
        st.session_state.usw_dues_biweekly_flat = st.number_input("USW Flat Bi-Weekly Strike Fund ($)", value=st.session_state.usw_dues_biweekly_flat, step=0.50)
        st.session_state.mepp_rate_usw = st.number_input("Steelworkers Pension Trust (MEPP $/worked hr)", value=st.session_state.mepp_rate_usw, step=0.25)
    with col_d2:
        st.subheader("Métallos Local 9414 Formulas")
        st.session_state.met_dues_hours_per_month = st.number_input("Métallos Monthly Dues Standard (Hours of Base Pay)", value=st.session_state.met_dues_hours_per_month, step=0.5)
        st.session_state.mepp_rate_met = st.number_input("Fonds de retraite Métallos (MEPP $/worked hr)", value=st.session_state.mepp_rate_met, step=0.25)

# =============================================================
# TAB 5: Bi-Weekly Pay Run & Official Paystub
# =============================================================
with tab5:
    st.header("5. Bi-Weekly Pay Run & Official Paystub Generator")
    st.markdown("Execute a live Canadian gross-to-net pay run complete with pre-tax deduction adjustments, statutory CRA/RQ taxes, and an authentic pay statement.")
    st.write("---")

    workers = {
        "Marc Bouchard (EMP1001)": {
            "Location": "Val-d'Or Mine (QC)", "Province": "QC", "Role": "Underground Miner", "CA": "CA_MET_QC",
            "Default_Step": "Step 3 (Intermediate)", "Underground_Role": True, "Pay_Type": "Hourly Union", "SIN": "942-811-042"
        },
        "Sarah Jenkins (EMP1002)": {
            "Location": "Ontario Concentrator (ON)", "Province": "ON", "Role": "Mill Operator", "CA": "CA_USW_ON",
            "Default_Step": "Step 2 (Junior)", "Underground_Role": False, "Pay_Type": "Hourly Union", "SIN": "612-491-883"
        },
        "David Tremblay (EMP1003)": {
            "Location": "Val-d'Or Mine (QC)", "Province": "QC", "Role": "Industrial Electrician", "CA": "CA_MET_QC",
            "Default_Step": "Step 4 (Journeyperson)", "Underground_Role": True, "Pay_Type": "Hourly Union", "SIN": "915-201-772"
        },
        "Elena Rostova (EMP1004)": {
            "Location": "Vancouver HQ (BC)", "Province": "BC", "Role": "Senior Mine Engineer", "CA": "Non-Union Exempt",
            "Default_Step": "Salaried Staff ($95,000)", "Underground_Role": False, "Pay_Type": "Salaried Staff", "Annual_Salary": 95000.0, "SIN": "704-582-194"
        }
    }

    c_sel1, c_sel2, c_sel3 = st.columns(3)
    with c_sel1:
        sel_worker_name = st.selectbox("Select Employee Profile", list(workers.keys()))
        worker = workers[sel_worker_name]
    with c_sel2:
        st.info(f"**Workday HCM Profile:**\n- Operating Location: {worker['Location']}\n- Collective Agreement: `{worker['CA']}`\n- Pay Cycle: **Bi-Weekly (Period 18 of 26)**")
    with c_sel3:
        if worker["Pay_Type"] == "Hourly Union":
            step_options = list(st.session_state.grades[worker['CA']].keys())
            sel_step = st.selectbox("Assigned Wage Step", step_options, index=step_options.index(worker['Default_Step']))
            base_hourly = st.session_state.grades[worker['CA']][sel_step]
            st.metric("Effective Base Hourly Rate", f"${base_hourly:.2f}/hr")
        else:
            base_hourly = worker["Annual_Salary"] / 2080.0
            biweekly_salary = worker["Annual_Salary"] / 26.0
            st.metric("Bi-Weekly Standard Salary", f"${biweekly_salary:,.2f}", f"${base_hourly:.2f}/hr equivalent")

    st.write("---")
    st.subheader("Bi-Weekly Shift & Attendance Inputs (14-Day Cycle)")

    if worker["Pay_Type"] == "Hourly Union":
        t_col1, t_col2, t_col3 = st.columns(3)
        with t_col1:
            reg_hours_input = st.number_input("Standard Regular Hours Worked", min_value=0.0, max_value=120.0, value=80.0, step=1.0)
            ot15_hours_input = st.number_input("Scheduled Overtime Hours (1.5x)", min_value=0.0, max_value=40.0, value=6.0, step=0.5)
        with t_col2:
            callout_count = st.number_input("Emergency Call-Out Incidents", min_value=0, max_value=5, value=1, step=1)
            callout_actual_hrs = st.number_input("Actual Punched Call-Out Hours", min_value=0.0, max_value=24.0, value=2.0, step=0.5)
            st.caption(f"Guaranteed {st.session_state.callout_min}h minimum per call-out @ {st.session_state.callout_mult}x base rate.")
        with t_col3:
            night_hours_input = st.number_input("Graveyard Shift Hours (19:00 - 07:00)", min_value=0.0, max_value=84.0, value=36.0, step=1.0)
            ug_hours_input = st.number_input("Underground Shift Hours", min_value=0.0, max_value=84.0, value=48.0 if worker["Underground_Role"] else 0.0, step=1.0, disabled=not worker["Underground_Role"])
    else:
        st.info("Salaried corporate positions are exempt from standard overtime tracking under provincial ESA.")
        reg_hours_input = 80.0
        ot15_hours_input = 0.0
        callout_count = 0
        callout_actual_hrs = 0.0
        night_hours_input = 0.0
        ug_hours_input = 0.0

    if st.button("⚡ Generate Official Canadian Paystub & Run Pay", type="primary"):
        # 1. Gross Earnings Calculation
        if worker["Pay_Type"] == "Hourly Union":
            reg_gross = reg_hours_input * base_hourly
            ot15_gross = ot15_hours_input * (base_hourly * 1.5)
            callout_guaranteed_hrs = callout_count * st.session_state.callout_min
            credited_callout_hrs = max(callout_actual_hrs, callout_guaranteed_hrs)
            callout_gross = credited_callout_hrs * (base_hourly * st.session_state.callout_mult) if callout_count > 0 else 0.0
            shift_prem_gross = night_hours_input * st.session_state.night_diff
            hazard_prem_gross = ug_hours_input * st.session_state.underground_prem

            total_biweekly_gross = reg_gross + ot15_gross + callout_gross + shift_prem_gross + hazard_prem_gross
            total_worked_hours = reg_hours_input + ot15_hours_input + callout_actual_hrs
            total_payable_hours = reg_hours_input + ot15_hours_input + credited_callout_hrs
        else:
            total_biweekly_gross = worker["Annual_Salary"] / 26.0
            reg_gross = total_biweekly_gross
            ot15_gross = 0.0
            callout_gross = 0.0
            shift_prem_gross = 0.0
            hazard_prem_gross = 0.0
            credited_callout_hrs = 0.0
            total_worked_hours = 80.0
            total_payable_hours = 80.0

        # 2. Pre-Tax Union Dues & MEPP Pensions (ITA 8(1)(i)(iv))
        union_dues = 0.0
        mepp_pension = 0.0

        if worker["CA"] == "CA_USW_ON":
            union_dues = (total_biweekly_gross * (st.session_state.usw_dues_pct / 100.0)) + st.session_state.usw_dues_biweekly_flat
            mepp_pension = total_worked_hours * st.session_state.mepp_rate_usw
        elif worker["CA"] == "CA_MET_QC":
            union_dues = (base_hourly * st.session_state.met_dues_hours_per_month) / 2.0
            mepp_pension = total_worked_hours * st.session_state.mepp_rate_met

        # 3. Canadian Statutory Tax Calculation Engine (CRA & Revenu Québec)
        tax_results = calculate_canadian_statutory_taxes(
            total_biweekly_gross, union_dues, mepp_pension, worker["Province"]
        )

        total_stat_taxes = tax_results["Total_Stat_Taxes"]
        total_employee_deductions = union_dues + mepp_pension + total_stat_taxes
        net_pay = total_biweekly_gross - total_employee_deductions

        # Simulated YTD multiplier (Period 18 of 26)
        ytd_mult = 18

        # -------------------------------------------------------------
        # 4. OFFICIAL ENTERPRISE PAYSTUB DISPLAY
        # -------------------------------------------------------------
        st.write("---")
        st.subheader("📄 Official Employee Earnings Statement (Paystub)")

        paystub_container = st.container(border=True)
        with paystub_container:
            # Paystub Header
            h_col1, h_col2 = st.columns([3, 2])
            with h_col1:
                st.markdown("### **APEX MINING CORPORATION**")
                st.caption("Canadian Operations | Extraction & Processing Division")
                st.markdown(f"**Employee Name:** {sel_worker_name.split(' (')[0]}")
                st.markdown(f"**Employee ID:** `{sel_worker_name.split('(')[1].replace(')', '')}` &nbsp;&nbsp;|&nbsp;&nbsp; **SIN:** `***-***-{worker['SIN'][-3:]}`")
                st.markdown(f"**Job Title:** {worker['Role']} &nbsp;&nbsp;|&nbsp;&nbsp; **Department:** {worker['Location']}")
            with h_col2:
                st.markdown("#### **EARNINGS STATEMENT**")
                st.markdown("**Pay Frequency:** Bi-Weekly (26 Pay Periods/Yr)")
                st.markdown("**Pay Period:** 2026-08-24 to 2026-09-06 (Period 18)")
                st.markdown("**Pay Date:** **2026-09-11**")
                st.markdown(f"**Bargaining Unit:** `{worker['CA']}`")

            st.write("---")

            # Section A: Earnings Table
            st.markdown("##### **1. GROSS EARNINGS**")
            earnings_data = [
                {"Description": "Regular Base Wages", "Hours": f"{reg_hours_input:.1f}", "Rate": f"${base_hourly:.2f}", "Current Amount": f"${reg_gross:,.2f}", "YTD Amount": f"${reg_gross * ytd_mult:,.2f}"},
                {"Description": "Overtime 1.5x", "Hours": f"{ot15_hours_input:.1f}", "Rate": f"${base_hourly * 1.5:.2f}", "Current Amount": f"${ot15_gross:,.2f}", "YTD Amount": f"${ot15_gross * ytd_mult:,.2f}"},
                {"Description": "Emergency Call-Out 2.0x (Guaranteed)", "Hours": f"{credited_callout_hrs:.1f}", "Rate": f"${base_hourly * 2.0:.2f}", "Current Amount": f"${callout_gross:,.2f}", "YTD Amount": f"${callout_gross * ytd_mult:,.2f}"},
                {"Description": "Graveyard Shift Differential", "Hours": f"{night_hours_input:.1f}", "Rate": f"${st.session_state.night_diff:.2f}", "Current Amount": f"${shift_prem_gross:,.2f}", "YTD Amount": f"${shift_prem_gross * ytd_mult:,.2f}"},
                {"Description": "Underground Mine Hazard Premium", "Hours": f"{ug_hours_input:.1f}", "Rate": f"${st.session_state.underground_prem:.2f}", "Current Amount": f"${hazard_prem_gross:,.2f}", "YTD Amount": f"${hazard_prem_gross * ytd_mult:,.2f}"}
            ]
            st.table(pd.DataFrame(earnings_data))

            # Section B: Pre-Tax & Statutory Deductions Grid
            d_col1, d_col2 = st.columns(2)
            with d_col1:
                st.markdown("##### **2. PRE-TAX DEDUCTIONS (ITA 8(1)(i))**")
                pretax_data = [
                    {"Description": "Union Dues Remittance", "Current": f"${union_dues:,.2f}", "YTD": f"${union_dues * ytd_mult:,.2f}"},
                    {"Description": "Multi-Employer Pension Trust (MEPP)", "Current": f"${mepp_pension:,.2f}", "YTD": f"${mepp_pension * ytd_mult:,.2f}"}
                ]
                st.table(pd.DataFrame(pretax_data))
                st.caption(f"💡 **Taxable Gross Income:** `${tax_results['Taxable_Gross']:,.2f}` *(Gross minus Pre-tax Deductions)*")

            with d_col2:
                st.markdown("##### **3. STATUTORY TAX WITHHOLDINGS**")
                stat_data = [
                    {"Tax Description": "Federal Income Tax (CRA)", "Current": f"${tax_results['Federal_Tax']:,.2f}", "YTD": f"${tax_results['Federal_Tax'] * ytd_mult:,.2f}"},
                    {"Tax Description": f"Provincial Income Tax ({worker['Province']})", "Current": f"${tax_results['Provincial_Tax']:,.2f}", "YTD": f"${tax_results['Provincial_Tax'] * ytd_mult:,.2f}"},
                    {"Tax Description": "QPP Pension (Quebec)" if worker["Province"] == "QC" else "CPP Pension (Canada)", "Current": f"${tax_results['QPP'] if worker['Province'] == 'QC' else tax_results['CPP']:,.2f}", "YTD": f"${(tax_results['QPP'] if worker['Province'] == 'QC' else tax_results['CPP']) * ytd_mult:,.2f}"},
                    {"Tax Description": "Employment Insurance (EI)", "Current": f"${tax_results['EI']:,.2f}", "YTD": f"${tax_results['EI'] * ytd_mult:,.2f}"}
                ]
                if worker["Province"] == "QC":
                    stat_data.append({"Tax Description": "QPIP / RQAP Parental Plan", "Current": f"${tax_results['QPIP']:,.2f}", "YTD": f"${tax_results['QPIP'] * ytd_mult:,.2f}"})
                st.table(pd.DataFrame(stat_data))

            st.write("---")

            # Section C: Net Pay Waterfall & Direct Deposit
            st.markdown("##### **4. NET PAY & DISTRIBUTION SUMMARY**")
            w1, w2, w3, w4 = st.columns(4)
            w1.metric("Total Gross Earnings", f"${total_biweekly_gross:,.2f}")
            w2.metric("Pre-Tax Deductions", f"-${union_dues + mepp_pension:,.2f}", "Dues + Pension")
            w3.metric("Total Statutory Taxes", f"-${total_stat_taxes:,.2f}", "CRA & RQ Withheld")
            w4.metric("NET DIRECT DEPOSIT", f"${net_pay:,.2f}", delta="Period Net")

            st.info(f"**Direct Deposit Distribution:** Royal Bank of Canada (Transit: 04219 | Account: ****-8102) &nbsp;➔&nbsp; **Amount Deposited:** `${net_pay:,.2f}` on September 11, 2026.")

            # Section D: Employer Paid Contributions (Total Rewards)
            st.write("---")
            st.markdown("##### **5. EMPLOYER PAID CONTRIBUTIONS & STATUTORY LEVIES (Not Deducted from EE)**")
            er_data = [
                {"Benefit / Levy Description": "Employer CPP/QPP Matching", "Current Contribution": f"${tax_results['ER_CPP_QPP']:,.2f}", "YTD Amount": f"${tax_results['ER_CPP_QPP'] * ytd_mult:,.2f}"},
                {"Benefit / Levy Description": "Employer EI Premium (1.4x)", "Current Contribution": f"${tax_results['ER_EI']:,.2f}", "YTD Amount": f"${tax_results['ER_EI'] * ytd_mult:,.2f}"},
                {"Benefit / Levy Description": f"Provincial Health Tax ({'QC HSF @ 4.26%' if worker['Province'] == 'QC' else worker['Province'] + ' EHT @ 1.95%'})", "Current Contribution": f"${tax_results['ER_Health_Tax']:,.2f}", "YTD Amount": f"${tax_results['ER_Health_Tax'] * ytd_mult:,.2f}"},
                {"Benefit / Levy Description": f"Workers' Compensation Board ({'CNESST Mining' if worker['Province'] == 'QC' else 'WSIB/WorkSafeBC'})", "Current Contribution": f"${tax_results['ER_WCB']:,.2f}", "YTD Amount": f"${tax_results['ER_WCB'] * ytd_mult:,.2f}"}
            ]
            if worker["Province"] == "QC":
                er_data.append({"Benefit / Levy Description": "Employer QPIP Premium (1.4x)", "Current Contribution": f"${tax_results['ER_QPIP']:,.2f}", "YTD Amount": f"${tax_results['ER_QPIP'] * ytd_mult:,.2f}"})
            st.table(pd.DataFrame(er_data))

        # -------------------------------------------------------------
        # 5. GENERAL LEDGER JOURNAL BALANCING
        # -------------------------------------------------------------
        st.write("---")
        st.subheader("📑 Balanced General Ledger (GL) Interface Distribution")
        gl_journal = [
            {"Account Code": "5100-LABOUR-REG", "Account Description": "Direct Operational Labour Expense", "Debit ($)": f"${reg_gross + ot15_gross:,.2f}", "Credit ($)": "-"},
            {"Account Code": "5105-LABOUR-CALLOUT", "Account Description": "Emergency Call-Out Premium Expense", "Debit ($)": f"${callout_gross:,.2f}", "Credit ($)": "-"},
            {"Account Code": "5110-SHIFT-DIFF", "Account Description": "Shift Differentials & Mine Hazard", "Debit ($)": f"${shift_prem_gross + hazard_prem_gross:,.2f}", "Credit ($)": "-"},
            {"Account Code": "2150-DUES-PAYABLE", "Account Description": "Union Dues Third-Party Remittance", "Debit ($)": "-", "Credit ($)": f"${union_dues:,.2f}"},
            {"Account Code": "2160-MEPP-PAYABLE", "Account Description": "Multi-Employer Pension Trust Clearing", "Debit ($)": "-", "Credit ($)": f"${mepp_pension:,.2f}"},
            {"Account Code": "2180-FED-TAX-PAYABLE", "Account Description": "Federal Income Tax Withholding (CRA)", "Debit ($)": "-", "Credit ($)": f"${tax_results['Federal_Tax']:,.2f}"},
            {"Account Code": "2185-PROV-TAX-PAYABLE", "Account Description": f"Provincial Income Tax Withholding ({worker['Province']})", "Debit ($)": "-", "Credit ($)": f"${tax_results['Provincial_Tax']:,.2f}"},
            {"Account Code": "2190-CPP-QPP-PAYABLE", "Account Description": "Employee Pension Contribution (CRA/RQ)", "Debit ($)": "-", "Credit ($)": f"${tax_results['QPP'] if worker['Province'] == 'QC' else tax_results['CPP']:,.2f}"},
            {"Account Code": "2195-EI-QPIP-PAYABLE", "Account Description": "Employee EI & QPIP Withholdings", "Debit ($)": "-", "Credit ($)": f"${tax_results['EI'] + tax_results['QPIP']:,.2f}"},
            {"Account Code": "2100-NET-PAYROLL", "Account Description": "Net Direct Deposit Clearing Account", "Debit ($)": "-", "Credit ($)": f"${net_pay:,.2f}"}
        ]
        st.table(pd.DataFrame(gl_journal))
