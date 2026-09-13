import streamlit as st
import pandas as pd
from datetime import datetime

# -------------------------------------------------------------
# 1. Page Configuration & Header
# -------------------------------------------------------------
st.set_page_config(
    page_title="Workday Multi-Union & Benefits HRIS Sandbox",
    page_icon="⚙️",
    layout="wide"
)

st.title("⚙️ Workday Multi-Union HRIS, Benefits & Bi-Weekly Payroll Sandbox")
st.caption("Enterprise Architecture: Multi-Jurisdiction Gross-to-Net Engine with Group Benefits (Extended Health, Dental, Life, Disability) & Real-Time CRA/RQ Taxes")

# -------------------------------------------------------------
# 2. Session State Initialization (Configuration Rules & Benefits)
# -------------------------------------------------------------
if "init" not in st.session_state:
    st.session_state.init = True
    
    # Unions
    st.session_state.unions = {
        "UNION_USW_2009": {"Name": "United Steelworkers Local 2009", "Site": "Ontario Concentrator Plant", "CA_ID": "CA_USW_ON", "Frequency": "Bi-Weekly (26 P/Y)"},
        "UNION_MET_9414": {"Name": "Syndicat des Métallos Local 9414", "Site": "Val-d'Or Underground Mine", "CA_ID": "CA_MET_QC", "Frequency": "Bi-Weekly (26 P/Y)"}
    }
    
    # Wage Grids
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
    
    # Time Tracking Rules
    st.session_state.callout_min = 4.0
    st.session_state.callout_mult = 2.0
    st.session_state.night_diff = 3.50
    st.session_state.underground_prem = 4.25
    st.session_state.anti_pyramiding = True
    
    # Dues & Pension
    st.session_state.usw_dues_pct = 1.85
    st.session_state.usw_dues_biweekly_flat = 2.50
    st.session_state.met_dues_hours_per_month = 2.0
    st.session_state.mepp_rate_usw = 2.50
    st.session_state.mepp_rate_met = 3.00

    # ---------------------------------------------------------
    # Group Benefits Configuration (Standard Bi-Weekly Rates)
    # ---------------------------------------------------------
    st.session_state.benefits = {
        "EXT_HEALTH": {"Name": "Extended Health Care", "Total_Premium": 120.00, "EE_Share": 0.00, "ER_Share": 1.00, "Taxable_Fed": False, "Taxable_QC": True},
        "DENTAL":     {"Name": "Comprehensive Dental", "Total_Premium": 60.00,  "EE_Share": 0.30, "ER_Share": 0.70, "Taxable_Fed": False, "Taxable_QC": True},
        "BASIC_LIFE": {"Name": "Basic Group Life (2x Salary)", "Total_Premium": 14.00,  "EE_Share": 0.00, "ER_Share": 1.00, "Taxable_Fed": True,  "Taxable_QC": True},
        "DEP_LIFE":   {"Name": "Dependent Life Insurance", "Total_Premium": 3.00,   "EE_Share": 0.00, "ER_Share": 1.00, "Taxable_Fed": True,  "Taxable_QC": True},
        "ADD":        {"Name": "Accidental Death & Dismemberment (AD&D)", "Total_Premium": 2.50, "EE_Share": 0.00, "ER_Share": 1.00, "Taxable_Fed": True,  "Taxable_QC": True},
        "STD":        {"Name": "Short-Term Disability (Wage Loss)", "Total_Premium": 18.00,  "EE_Share": 0.00, "ER_Share": 1.00, "Taxable_Fed": False, "Taxable_QC": False},
        "LTD":        {"Name": "Long-Term Disability (Tax-Free Plan)", "Total_Premium": 38.00,  "EE_Share": 1.00, "ER_Share": 0.00, "Taxable_Fed": False, "Taxable_QC": False}
    }

# -------------------------------------------------------------
# 3. Canadian Statutory Tax Calculation Engine (with Taxable Benefits)
# -------------------------------------------------------------
def calculate_canadian_statutory_taxes(gross_pay, union_dues, mepp_ded, fed_taxable_ben, qc_taxable_ben, province):
    """
    Computes Canadian statutory withholdings (CRA T4032 & Revenu Québec TP-1015.3).
    Incorporates pre-tax deductions and taxable benefit additions.
    """
    # Pre-tax deductions reduce taxable income (ITA 8(1)(i)(iv))
    base_taxable_gross = max(0.0, gross_pay - union_dues - mepp_ded)
    
    # Taxable Gross differs federally vs Quebec
    federal_taxable_income = base_taxable_gross + fed_taxable_ben
    provincial_taxable_income = (base_taxable_gross + qc_taxable_ben) if province == "QC" else federal_taxable_income
    
    # Pension Subject Earnings (Gross + Life/AD&D Taxable Benefits minus $134.61 bi-weekly basic exemption)
    pensionable_earnings = max(0.0, (gross_pay + fed_taxable_ben) - 134.61)
    
    if province == "QC":
        cpp = 0.0
        qpp = min(4160.0 / 26.0, pensionable_earnings * 0.064)  # QPP 6.40%
        ei = min(781.0 / 26.0, gross_pay * 0.0132)             # Reduced EI 1.32% (Taxable benefits non-insurable)
        qpip = min(460.0 / 26.0, (gross_pay + fed_taxable_ben) * 0.00494) # QPIP 0.494%
        er_health_tax = (gross_pay + qc_taxable_ben) * 0.0426  # QC HSF 4.26%
        er_wcb = (gross_pay / 100.0) * 3.95                    # CNESST Mining
    else:
        cpp = min(3867.50 / 26.0, pensionable_earnings * 0.0595) # CPP 5.95%
        qpp = 0.0
        ei = min(1049.12 / 26.0, gross_pay * 0.0166)           # Standard Federal EI 1.66%
        qpip = 0.0
        if province == "ON":
            er_health_tax = gross_pay * 0.0195                 # ON EHT 1.95%
            er_wcb = (gross_pay / 100.0) * 2.85                # WSIB Class D
        else: # BC
            er_health_tax = gross_pay * 0.0195                 # BC EHT 1.95%
            er_wcb = (gross_pay / 100.0) * 0.18                # WorkSafeBC

    er_cpp_qpp = qpp if province == "QC" else cpp
    er_ei = ei * 1.4
    er_qpip = qpip * 1.4

    # Federal Income Tax (Annualized Brackets)
    fed_annual = federal_taxable_income * 26.0
    if fed_annual <= 55867:
        fed_tax_annual = fed_annual * 0.15
    elif fed_annual <= 111733:
        fed_tax_annual = (55867 * 0.15) + ((fed_annual - 55867) * 0.205)
    elif fed_annual <= 173205:
        fed_tax_annual = (55867 * 0.15) + ((111733 - 55867) * 0.205) + ((fed_annual - 111733) * 0.26)
    else:
        fed_tax_annual = (55867 * 0.15) + ((111733 - 55867) * 0.205) + ((173205 - 111733) * 0.26) + ((fed_annual - 173205) * 0.29)
    
    fed_bpa_credit = 15705.0 * 0.15
    fed_tax_annual = max(0.0, fed_tax_annual - fed_bpa_credit)
    if province == "QC":
        fed_tax_annual = fed_tax_annual * (1.0 - 0.165) # 16.5% Quebec Abatement
    fed_tax_biweekly = fed_tax_annual / 26.0

    # Provincial Income Tax (Annualized Brackets)
    prov_annual = provincial_taxable_income * 26.0
    if province == "QC":
        if prov_annual <= 51780:
            qc_tax_annual = prov_annual * 0.14
        elif prov_annual <= 103545:
            qc_tax_annual = (51780 * 0.14) + ((prov_annual - 51780) * 0.19)
        else:
            qc_tax_annual = (51780 * 0.14) + ((103545 - 51780) * 0.19) + ((prov_annual - 103545) * 0.24)
        qc_bpa_credit = 18056.0 * 0.14
        prov_tax_biweekly = max(0.0, qc_tax_annual - qc_bpa_credit) / 26.0
    elif province == "ON":
        if prov_annual <= 51446:
            on_tax_annual = prov_annual * 0.0505
        elif prov_annual <= 102894:
            on_tax_annual = (51446 * 0.0505) + ((prov_annual - 51446) * 0.0915)
        else:
            on_tax_annual = (51446 * 0.0505) + ((102894 - 51446) * 0.0915) + ((prov_annual - 102894) * 0.1116)
        on_bpa_credit = 12399.0 * 0.0505
        prov_tax_biweekly = max(0.0, on_tax_annual - on_bpa_credit) / 26.0
    else: # BC
        if prov_annual <= 47937:
            bc_tax_annual = prov_annual * 0.0506
        elif prov_annual <= 95875:
            bc_tax_annual = (47937 * 0.0506) + ((prov_annual - 47937) * 0.0770)
        else:
            bc_tax_annual = (47937 * 0.0506) + ((95875 - 47937) * 0.0770) + ((prov_annual - 95875) * 0.1050)
        bc_bpa_credit = 12580.0 * 0.0506
        prov_tax_biweekly = max(0.0, bc_tax_annual - bc_bpa_credit) / 26.0

    return {
        "Fed_Taxable_Income": federal_taxable_income,
        "QC_Taxable_Income": provincial_taxable_income,
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
    "🏥 Tab 4: Benefits, Deductions & MEPP",
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
# TAB 4: Benefits, Deductions & MEPP
# =============================================================
with tab4:
    st.header("4. Group Benefits Architecture, Cost-Sharing & Union Deductions")
    st.markdown("""
    Configure the **7 Core Employee Benefits**, premium cost-sharing ratios, and Canadian taxable benefit treatments.
    """)
    st.write("---")

    st.subheader("🏥 Group Benefits Coverage & Cost-Share Schedule (Bi-Weekly Rates)")
    
    ben_table_data = []
    for code, b in st.session_state.benefits.items():
        ee_amt = b["Total_Premium"] * b["EE_Share"]
        er_amt = b["Total_Premium"] * b["ER_Share"]
        ben_table_data.append({
            "Plan Code": code,
            "Coverage Plan Name": b["Name"],
            "Bi-Weekly Premium": f"${b['Total_Premium']:.2f}",
            "EE Cost Share": f"{int(b['EE_Share']*100)}% (${ee_amt:.2f})",
            "ER Cost Share": f"{int(b['ER_Share']*100)}% (${er_amt:.2f})",
            "Fed Taxable (T4)": "Yes (Code 40)" if b["Taxable_Fed"] else "No",
            "QC Taxable (RL-1)": "Yes (Box A/J/L)" if b["Taxable_QC"] else "No"
        })
    st.table(pd.DataFrame(ben_table_data))

    st.info("""
    📘 **Canadian Compliance & Governance Notes:**
    * **Dental (30% EE / 70% ER):** Employee-paid dental premiums are eligible for the Medical Expense Tax Credit (METC). In Quebec, employer-paid dental is a taxable benefit on RL-1 Box J.
    * **LTD (100% Employee-Paid):** When employees fund 100% of Long-Term Disability premiums post-tax, any future disability benefit payouts are **completely tax-free**.
    * **Life & AD&D (100% Employer-Paid):** Employer contributions represent a taxable benefit for Federal Income Tax and CPP (T4 Box 14/26). In Quebec, it is taxable for QPP, QPIP, and income tax (RL-1 Box A/L).
    * **Extended Health (100% Employer-Paid):** Tax-free under Federal CRA rules, but **taxable on Quebec RL-1 Box J/A** for provincial tax.
    """)

    st.write("---")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.subheader("USW Local 2009 Union Deductions")
        st.session_state.usw_dues_pct = st.number_input("USW Dues Percentage of Gross (%)", value=st.session_state.usw_dues_pct, step=0.05)
        st.session_state.usw_dues_biweekly_flat = st.number_input("USW Flat Bi-Weekly Strike Fund ($)", value=st.session_state.usw_dues_biweekly_flat, step=0.50)
        st.session_state.mepp_rate_usw = st.number_input("Steelworkers Pension Trust (MEPP $/worked hr)", value=st.session_state.mepp_rate_usw, step=0.25)
    with col_d2:
        st.subheader("Métallos Local 9414 Union Deductions")
        st.session_state.met_dues_hours_per_month = st.number_input("Métallos Monthly Dues Standard (Hours of Base Pay)", value=st.session_state.met_dues_hours_per_month, step=0.5)
        st.session_state.mepp_rate_met = st.number_input("Fonds de retraite Métallos (MEPP $/worked hr)", value=st.session_state.mepp_rate_met, step=0.25)

# =============================================================
# TAB 5: Bi-Weekly Pay Run & Official Paystub
# =============================================================
with tab5:
    st.header("5. Bi-Weekly Pay Run, Benefits Evaluation & Official Paystub")
    st.markdown("Execute a full gross-to-net pay run incorporating all 7 group benefits, multi-jurisdiction taxable benefits, and CRA/RQ withholdings.")
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
    st.subheader("Bi-Weekly Attendance & Shift Inputs")

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

    if st.button("⚡ Execute Bi-Weekly Pay & Generate Master Paystub", type="primary"):
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

        # 2. Pre-Tax Union Dues & MEPP Pensions
        union_dues = 0.0
        mepp_pension = 0.0
        if worker["CA"] == "CA_USW_ON":
            union_dues = (total_biweekly_gross * (st.session_state.usw_dues_pct / 100.0)) + st.session_state.usw_dues_biweekly_flat
            mepp_pension = total_worked_hours * st.session_state.mepp_rate_usw
        elif worker["CA"] == "CA_MET_QC":
            union_dues = (base_hourly * st.session_state.met_dues_hours_per_month) / 2.0
            mepp_pension = total_worked_hours * st.session_state.mepp_rate_met

        # 3. Group Benefits Calculations (Employee Deductions & Employer Contributions)
        # Employee Deductions: Dental (30%), LTD (100%)
        ee_dental_ded = st.session_state.benefits["DENTAL"]["Total_Premium"] * st.session_state.benefits["DENTAL"]["EE_Share"] # $18.00
        ee_ltd_ded = st.session_state.benefits["LTD"]["Total_Premium"] * st.session_state.benefits["LTD"]["EE_Share"]          # $38.00
        total_ee_benefit_ded = ee_dental_ded + ee_ltd_ded # $56.00

        # Employer Contributions:
        er_ext_health = st.session_state.benefits["EXT_HEALTH"]["Total_Premium"] * st.session_state.benefits["EXT_HEALTH"]["ER_Share"] # $120.00
        er_dental     = st.session_state.benefits["DENTAL"]["Total_Premium"] * st.session_state.benefits["DENTAL"]["ER_Share"]         # $42.00
        er_life       = st.session_state.benefits["BASIC_LIFE"]["Total_Premium"] * st.session_state.benefits["BASIC_LIFE"]["ER_Share"] # $14.00
        er_dep_life   = st.session_state.benefits["DEP_LIFE"]["Total_Premium"] * st.session_state.benefits["DEP_LIFE"]["ER_Share"]     # $3.00
        er_add        = st.session_state.benefits["ADD"]["Total_Premium"] * st.session_state.benefits["ADD"]["ER_Share"]               # $2.50
        er_std        = st.session_state.benefits["STD"]["Total_Premium"] * st.session_state.benefits["STD"]["ER_Share"]               # $18.00
        total_er_benefits = er_ext_health + er_dental + er_life + er_dep_life + er_add + er_std # $199.50

        # Taxable Benefits:
        # Federal: Life + Dep Life + AD&D ($19.50)
        fed_taxable_benefits = er_life + er_dep_life + er_add
        # Quebec: Life + Dep Life + AD&D + ER Health + ER Dental ($181.50)
        qc_taxable_benefits = fed_taxable_benefits + er_ext_health + er_dental

        # 4. Canadian Statutory Tax Withholdings (CRA & Revenu Québec)
        tax_results = calculate_canadian_statutory_taxes(
            total_biweekly_gross, union_dues, mepp_pension,
            fed_taxable_benefits, qc_taxable_benefits, worker["Province"]
        )

        total_stat_taxes = tax_results["Total_Stat_Taxes"]
        total_employee_deductions = union_dues + mepp_pension + total_stat_taxes + total_ee_benefit_ded
        net_pay = total_biweekly_gross - total_employee_deductions

        ytd_mult = 18

        # -------------------------------------------------------------
        # 5. OFFICIAL ENTERPRISE PAYSTUB DISPLAY
        # -------------------------------------------------------------
        st.write("---")
        st.subheader("📄 Official Employee Earnings & Benefits Statement (Paystub)")

        paystub_container = st.container(border=True)
        with paystub_container:
            # Paystub Header
            h_col1, h_col2 = st.columns([3, 2])
            with h_col1:
                st.markdown("### **APEX MINING CORPORATION**")
                st.caption("Canadian Heavy Industry & Extraction Operations")
                st.markdown(f"**Employee Name:** {sel_worker_name.split(' (')[0]}")
                st.markdown(f"**Employee ID:** `{sel_worker_name.split('(')[1].replace(')', '')}` &nbsp;&nbsp;|&nbsp;&nbsp; **SIN:** `***-***-{worker['SIN'][-3:]}`")
                st.markdown(f"**Job Title:** {worker['Role']} &nbsp;&nbsp;|&nbsp;&nbsp; **Location:** {worker['Location']}")
            with h_col2:
                st.markdown("#### **BI-WEEKLY EARNINGS STATEMENT**")
                st.markdown("**Pay Period:** 2026-08-24 to 2026-09-06 (Cycle 18/26)")
                st.markdown("**Pay Date:** **2026-09-11**")
                st.markdown(f"**Bargaining Unit:** `{worker['CA']}`")
                st.markdown(f"**Jurisdiction:** `{worker['Province']} (Tax Authority: {'CRA + Revenu Québec' if worker['Province']=='QC' else 'CRA Sole Agency'})`")

            st.write("---")

            # Section 1: Gross Earnings
            st.markdown("##### **1. GROSS EARNINGS**")
            earnings_data = [
                {"Description": "Regular Base Wages", "Hours": f"{reg_hours_input:.1f}", "Rate": f"${base_hourly:.2f}", "Current Amount": f"${reg_gross:,.2f}", "YTD Amount": f"${reg_gross * ytd_mult:,.2f}"},
                {"Description": "Overtime 1.5x", "Hours": f"{ot15_hours_input:.1f}", "Rate": f"${base_hourly * 1.5:.2f}", "Current Amount": f"${ot15_gross:,.2f}", "YTD Amount": f"${ot15_gross * ytd_mult:,.2f}"},
                {"Description": "Emergency Call-Out 2.0x (Guaranteed)", "Hours": f"{credited_callout_hrs:.1f}", "Rate": f"${base_hourly * 2.0:.2f}", "Current Amount": f"${callout_gross:,.2f}", "YTD Amount": f"${callout_gross * ytd_mult:,.2f}"},
                {"Description": "Graveyard Shift Differential ($3.50/hr)", "Hours": f"{night_hours_input:.1f}", "Rate": f"${st.session_state.night_diff:.2f}", "Current Amount": f"${shift_prem_gross:,.2f}", "YTD Amount": f"${shift_prem_gross * ytd_mult:,.2f}"},
                {"Description": "Underground Mine Hazard ($4.25/hr)", "Hours": f"{ug_hours_input:.1f}", "Rate": f"${st.session_state.underground_prem:.2f}", "Current Amount": f"${hazard_prem_gross:,.2f}", "YTD Amount": f"${hazard_prem_gross * ytd_mult:,.2f}"}
            ]
            st.table(pd.DataFrame(earnings_data))

            # Section 2: Taxable Benefits Matrix
            st.markdown("##### **2. EMPLOYER-PAID TAXABLE BENEFITS (Added to Taxable Gross, Not Paid as Cash)**")
            taxable_ben_data = [
                {"Benefit Item": "Basic Life Insurance (100% ER Paid)", "Amount": f"${er_life:.2f}", "Federal Tax Status": "Taxable (T4 Code 40)", "Quebec RL-1 Status": "Taxable (Box A/L)"},
                {"Benefit Item": "Dependent Life Insurance (100% ER Paid)", "Amount": f"${er_dep_life:.2f}", "Federal Tax Status": "Taxable (T4 Code 40)", "Quebec RL-1 Status": "Taxable (Box A/L)"},
                {"Benefit Item": "AD&D Insurance (100% ER Paid)", "Amount": f"${er_add:.2f}", "Federal Tax Status": "Taxable (T4 Code 40)", "Quebec RL-1 Status": "Taxable (Box A/L)"},
                {"Benefit Item": "Extended Health Care (100% ER Paid)", "Amount": f"${er_ext_health:.2f}", "Federal Tax Status": "Non-Taxable", "Quebec RL-1 Status": "Taxable (Box A/J)" if worker['Province']=='QC' else "Non-Taxable"},
                {"Benefit Item": "Comprehensive Dental (70% ER Paid)", "Amount": f"${er_dental:.2f}", "Federal Tax Status": "Non-Taxable", "Quebec RL-1 Status": "Taxable (Box A/J)" if worker['Province']=='QC' else "Non-Taxable"}
            ]
            st.table(pd.DataFrame(taxable_ben_data))
            
            if worker["Province"] == "QC":
                st.caption(f"💡 **Quebec Dual-Tax Architecture:** Total Federal Taxable Benefits: **${fed_taxable_benefits:.2f}** | Total Quebec Provincial Taxable Benefits: **${qc_taxable_benefits:.2f}** *(includes employer-paid health & dental under RL-1 Box J)*.")
            else:
                st.caption(f"💡 **Federal CRA Compliance:** Total Taxable Benefits added to T4 Box 14/Code 40: **${fed_taxable_benefits:.2f}** *(Life + Dep Life + AD&D)*.")

            st.write("---")

            # Section 3: Deductions Grid (Pre-Tax, Statutory, Post-Tax Benefits)
            col_d1, col_d2, col_d3 = st.columns(3)
            with col_d1:
                st.markdown("##### **3A. PRE-TAX DEDUCTIONS**")
                pretax_data = [
                    {"Deduction": "Union Dues", "Amount": f"${union_dues:,.2f}"},
                    {"Deduction": "MEPP Pension Trust", "Amount": f"${mepp_pension:,.2f}"}
                ]
                st.table(pd.DataFrame(pretax_data))
                st.caption(f"**Taxable Base (Fed):** `${tax_results['Fed_Taxable_Income']:,.2f}`")

            with col_d2:
                st.markdown("##### **3B. STATUTORY TAXES**")
                stat_data = [
                    {"Tax": "Federal Income Tax", "Amount": f"${tax_results['Federal_Tax']:,.2f}"},
                    {"Tax": f"Provincial Tax ({worker['Province']})", "Amount": f"${tax_results['Provincial_Tax']:,.2f}"},
                    {"Tax": "QPP" if worker["Province"] == "QC" else "CPP", "Amount": f"${tax_results['QPP'] if worker['Province'] == 'QC' else tax_results['CPP']:,.2f}"},
                    {"Tax": "EI Premium", "Amount": f"${tax_results['EI']:,.2f}"}
                ]
                if worker["Province"] == "QC":
                    stat_data.append({"Tax": "QPIP (RQAP)", "Amount": f"${tax_results['QPIP']:,.2f}"})
                st.table(pd.DataFrame(stat_data))

            with col_d3:
                st.markdown("##### **3C. POST-TAX BENEFITS**")
                posttax_data = [
                    {"Plan": "Dental (30% EE)", "Amount": f"${ee_dental_ded:,.2f}"},
                    {"Plan": "LTD (100% EE)", "Amount": f"${ee_ltd_ded:,.2f}"}
                ]
                st.table(pd.DataFrame(posttax_data))
                st.caption("💡 *LTD is 100% EE post-tax to ensure future benefits are tax-free.*")

            st.write("---")

            # Section 4: Net Pay & Direct Deposit
            st.markdown("##### **4. NET PAY & DISTRIBUTION SUMMARY**")
            w1, w2, w3, w4 = st.columns(4)
            w1.metric("Gross Earnings", f"${total_biweekly_gross:,.2f}")
            w2.metric("Pre-Tax Deductions", f"-${union_dues + mepp_pension:,.2f}", "Dues + MEPP")
            w3.metric("Taxes & Benefits", f"-${total_stat_taxes + total_ee_benefit_ded:,.2f}", "CRA/RQ + Benefits")
            w4.metric("NET DIRECT DEPOSIT", f"${net_pay:,.2f}", delta="Period Net")

            st.info(f"**Direct Deposit Banking Routing:** Royal Bank of Canada | Transit: 04219 | Account: ****-8102 &nbsp;➔&nbsp; **Deposit Cleared:** `${net_pay:,.2f}` on September 11, 2026.")

            # Section 5: Employer Total Rewards & Health Levies
            st.write("---")
            st.markdown("##### **5. EMPLOYER-PAID CONTRIBUTIONS & TOTAL REWARDS (Not Deducted from Pay)**")
            er_rewards_data = [
                {"Category": "Group Insurance", "Item Description": "Extended Health Care (100% ER)", "Current Amount": f"${er_ext_health:.2f}", "YTD Amount": f"${er_ext_health * ytd_mult:,.2f}"},
                {"Category": "Group Insurance", "Item Description": "Comprehensive Dental (70% ER)", "Current Amount": f"${er_dental:.2f}", "YTD Amount": f"${er_dental * ytd_mult:,.2f}"},
                {"Category": "Group Insurance", "Item Description": "Basic Life Insurance (100% ER)", "Current Amount": f"${er_life:.2f}", "YTD Amount": f"${er_life * ytd_mult:,.2f}"},
                {"Category": "Group Insurance", "Item Description": "Dependent Life Insurance (100% ER)", "Current Amount": f"${er_dep_life:.2f}", "YTD Amount": f"${er_dep_life * ytd_mult:,.2f}"},
                {"Category": "Group Insurance", "Item Description": "AD&D Insurance (100% ER)", "Current Amount": f"${er_add:.2f}", "YTD Amount": f"${er_add * ytd_mult:,.2f}"},
                {"Category": "Group Insurance", "Item Description": "Short-Term Disability (100% ER)", "Current Amount": f"${er_std:.2f}", "YTD Amount": f"${er_std * ytd_mult:,.2f}"},
                {"Category": "Statutory Matching", "Item Description": "CPP / QPP Employer Matching", "Current Amount": f"${tax_results['ER_CPP_QPP']:,.2f}", "YTD Amount": f"${tax_results['ER_CPP_QPP'] * ytd_mult:,.2f}"},
                {"Category": "Statutory Matching", "Item Description": "Employment Insurance (1.4x ER Match)", "Current Amount": f"${tax_results['ER_EI']:,.2f}", "YTD Amount": f"${tax_results['ER_EI'] * ytd_mult:,.2f}"},
                {"Category": "Provincial Health Tax", "Item Description": f"Employer Health Tax ({'QC HSF @ 4.26%' if worker['Province'] == 'QC' else worker['Province'] + ' EHT @ 1.95%'})", "Current Amount": f"${tax_results['ER_Health_Tax']:,.2f}", "YTD Amount": f"${tax_results['ER_Health_Tax'] * ytd_mult:,.2f}"},
                {"Category": "Workers' Compensation", "Item Description": f"Workers' Compensation Board ({'CNESST Mining' if worker['Province'] == 'QC' else 'WSIB/WorkSafeBC'})", "Current Amount": f"${tax_results['ER_WCB']:,.2f}", "YTD Amount": f"${tax_results['ER_WCB'] * ytd_mult:,.2f}"}
            ]
            st.table(pd.DataFrame(er_rewards_data))

        # -------------------------------------------------------------
        # 6. BALANCED GENERAL LEDGER JOURNAL
        # -------------------------------------------------------------
        st.write("---")
        st.subheader("📑 Balanced General Ledger (GL) Interface Distribution")
        st.caption("Double-entry accounting journal lines mapping operational expenses against clearing liabilities (Debits strictly equal Credits).")

        total_carrier_remittance = total_ee_benefit_ded + total_er_benefits # $56.00 + $199.50 = $255.50

        gl_journal = [
            # Debits (Operational Expenses)
            {"Account Code": "5100-LABOUR-REG", "Account Description": "Direct Operational Labour Expense", "Debit ($)": f"${reg_gross + ot15_gross:,.2f}", "Credit ($)": "-"},
            {"Account Code": "5105-LABOUR-CALLOUT", "Account Description": "Emergency Call-Out Premium Expense", "Debit ($)": f"${callout_gross:,.2f}", "Credit ($)": "-"},
            {"Account Code": "5110-SHIFT-DIFF", "Account Description": "Shift Differentials & Mine Hazard", "Debit ($)": f"${shift_prem_gross + hazard_prem_gross:,.2f}", "Credit ($)": "-"},
            {"Account Code": "5120-BENEFITS-EXP", "Account Description": "Employer Group Benefits Expense (Health/Dental/Life/STD)", "Debit ($)": f"${total_er_benefits:,.2f}", "Credit ($)": "-"},
            
            # Credits (Balance Sheet Liabilities & Clearing)
            {"Account Code": "2150-DUES-PAYABLE", "Account Description": "Union Dues Third-Party Remittance", "Debit ($)": "-", "Credit ($)": f"${union_dues:,.2f}"},
            {"Account Code": "2160-MEPP-PAYABLE", "Account Description": "Multi-Employer Pension Trust Clearing", "Debit ($)": "-", "Credit ($)": f"${mepp_pension:,.2f}"},
            {"Account Code": "2170-INSURANCE-CLEARING", "Account Description": "Group Benefits Carrier Payable (Sun Life / Manulife)", "Debit ($)": "-", "Credit ($)": f"${total_carrier_remittance:,.2f}"},
            {"Account Code": "2180-FED-TAX-PAYABLE", "Account Description": "Federal Income Tax Withholding (CRA)", "Debit ($)": "-", "Credit ($)": f"${tax_results['Federal_Tax']:,.2f}"},
            {"Account Code": "2185-PROV-TAX-PAYABLE", "Account Description": f"Provincial Income Tax Withholding ({worker['Province']})", "Debit ($)": "-", "Credit ($)": f"${tax_results['Provincial_Tax']:,.2f}"},
            {"Account Code": "2190-CPP-QPP-PAYABLE", "Account Description": "Employee Pension Contribution (CRA/RQ)", "Debit ($)": "-", "Credit ($)": f"${tax_results['QPP'] if worker['Province'] == 'QC' else tax_results['CPP']:,.2f}"},
            {"Account Code": "2195-EI-QPIP-PAYABLE", "Account Description": "Employee EI & QPIP Withholdings", "Debit ($)": "-", "Credit ($)": f"${tax_results['EI'] + tax_results['QPIP']:,.2f}"},
            {"Account Code": "2100-NET-PAYROLL", "Account Description": "Net Direct Deposit Clearing Account", "Debit ($)": "-", "Credit ($)": f"${net_pay:,.2f}"}
        ]
        st.table(pd.DataFrame(gl_journal))
        st.caption(f"⚖️ **GL Balance Verification:** Total Debits = `${(reg_gross + ot15_gross + callout_gross + shift_prem_gross + hazard_prem_gross + total_er_benefits):,.2f}` | Total Credits = `${(union_dues + mepp_pension + total_carrier_remittance + tax_results['Federal_Tax'] + tax_results['Provincial_Tax'] + (tax_results['QPP'] if worker['Province']=='QC' else tax_results['CPP']) + (tax_results['EI'] + tax_results['QPIP']) + net_pay):,.2f}` *(Fully Balanced)*")
