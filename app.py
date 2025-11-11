import os
import io
import numpy as np
import pandas as pd
import joblib

from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# ========= CONFIG =========

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "patient_readmission_model.pkl")
DATASET_PATH = os.path.join(BASE_DIR, "data", "final_dataset.csv")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Meta fields (NOT used for ML features, used for report/dashboard)
META_FIELDS = [
    "admission_id",
    "patient_name",
    "admission_date",
    "discharge_date"
]

# Model input features (logical/semantic names we expect from frontend)
COMMON_FEATURES = [
    "Age",
    "Sex",
    "Weight",
    "Blood Pressure",
    "Cholesterol",
    "Insulin",
    "Platelets",
    "Diabetics",
    "air_quality_index",
    "social_event_count",
]

DIABETES_FEATURES = [
    "Hemoglobin (g/dL)",
    "WBC Count (10^9/L)",
    "Platelet Count (10^9/L)",
    "Urine Protein (mg/dL)",
    "Urine Glucose (mg/dL)",
]

HEART_FAILURE_FEATURES = [
    "ECG Result",
    "Pulse Rate (bpm)",
]

ALL_FEATURES = COMMON_FEATURES + DIABETES_FEATURES + HEART_FAILURE_FEATURES

# ========= APP INIT =========

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="/")
CORS(app)

# Load model
model = None
try:
    model = joblib.load(MODEL_PATH)
    print("[INFO] Model loaded successfully.")
except Exception as e:
    print(f"[WARN] Could not load pre-trained model: {e}")
    print("[INFO] Fallback: Using heuristic prediction system.")
    model = None

# Load dataset (for doctor/hospital/admission/discharge info)
if os.path.exists(DATASET_PATH):
    try:
        df_data = pd.read_csv(DATASET_PATH)
        print("[INFO] Dataset loaded for report enrichment.")
    except Exception as e:
        print(f"[WARN] Could not load dataset: {e}")
        df_data = None
else:
    df_data = None
    print("[WARN] Dataset file not found.")


# ========= HELPERS =========

def encode_categorical(feature_name, value):
    if feature_name == "Sex":
        if isinstance(value, str):
            return 1.0 if value.strip().lower().startswith("m") else 0.0
    if feature_name == "Diabetics":
        if isinstance(value, str):
            return 1.0 if value.strip().lower().startswith("y") else 0.0
    return value


def preprocess_input(problem_type, features_dict):
    """
    Build a single-row DataFrame for the model.

    Key points:
    - If the trained model has `feature_names_in_`, we honor that as the
      canonical column order and fill missing ones with 0.
    - Otherwise, we fall back to ALL_FEATURES.
    - For missing disease-specific features, fill with median/typical values.
    - Returns: pandas.DataFrame (NOT numpy array).
    """
    if model is not None and hasattr(model, "feature_names_in_"):
        cols = list(model.feature_names_in_)
    else:
        cols = list(ALL_FEATURES)

    row = {}

    for col in cols:
        raw_val = features_dict.get(col, None)

        # If feature not provided, use sensible defaults based on problem type
        if raw_val is None or raw_val == "" or raw_val == 0:
            if problem_type == "diabetes" and col in HEART_FAILURE_FEATURES:
                raw_val = 0  # Default ECG and Pulse for non-HF patients
            elif problem_type == "heart_failure" and col in DIABETES_FEATURES:
                raw_val = 0  # Default metabolic markers for non-Diabetes patients
            else:
                raw_val = 0

        val = encode_categorical(col, raw_val)

        try:
            val = float(val) if val is not None else 0.0
        except (TypeError, ValueError):
            val = 0.0

        row[col] = val

    X = pd.DataFrame([row], columns=cols)
    return X


def generate_fallback_prediction(problem_type, features_dict):
    """
    Generate a fallback prediction when model is not available.
    Uses heuristic rules based on medical knowledge and feature importance.
    
    Returns a probability score between 0.10 and 0.95.
    """
    import random
    
    # Extract key features for heuristic prediction
    age = float(features_dict.get("Age", 50))
    cholesterol = float(features_dict.get("Cholesterol", 200))
    blood_pressure = features_dict.get("Blood Pressure", "120/80")
    platelets = float(features_dict.get("Platelets", 200))
    weight = float(features_dict.get("Weight", 75))
    insulin = float(features_dict.get("Insulin", 16))
    diabetics = str(features_dict.get("Diabetics", "No")).lower()
    
    # Parse blood pressure
    try:
        systolic = int(blood_pressure.split('/')[0]) if '/' in str(blood_pressure) else 120
        diastolic = int(blood_pressure.split('/')[1]) if '/' in str(blood_pressure) else 80
    except:
        systolic = 120
        diastolic = 80
    
    # Start with base risk of 0.25 (25% baseline readmission rate in healthcare)
    risk_score = 0.25
    
    # Age-based risk (age is strongest predictor of readmission)
    if age > 75:
        risk_score += 0.20
    elif age > 65:
        risk_score += 0.15
    elif age > 55:
        risk_score += 0.08
    elif age < 30:
        risk_score -= 0.05
    
    # Blood pressure risk (hypertension comorbidity)
    if systolic > 160 or diastolic > 100:
        risk_score += 0.15
    elif systolic > 140 or diastolic > 90:
        risk_score += 0.10
    
    # Cholesterol risk
    if cholesterol > 240:
        risk_score += 0.12
    elif cholesterol > 200:
        risk_score += 0.05
    elif cholesterol < 120:
        risk_score -= 0.03
    
    # Platelet abnormalities (thrombocytopenia/thrombocytosis)
    if platelets < 150 or platelets > 400:
        risk_score += 0.08
    
    # Insulin resistance indicator
    if insulin > 50:
        risk_score += 0.10
    
    # Diabetes comorbidity
    is_diabetic = diabetics in ['yes', 'y', 'true', '1']
    
    # Disease-specific factors
    if problem_type == "diabetes":
        hemoglobin = float(features_dict.get("Hemoglobin (g/dL)", 7))
        urine_glucose = float(features_dict.get("Urine Glucose (mg/dL)", 0))
        wbc = float(features_dict.get("WBC Count (10^9/L)", 7))
        
        # Poor glycemic control (HbA1c proxy via hemoglobin)
        if hemoglobin > 8.0:
            risk_score += 0.18
        elif hemoglobin > 7.0:
            risk_score += 0.10
        
        # Glucose in urine
        if urine_glucose > 100:
            risk_score += 0.12
        elif urine_glucose > 50:
            risk_score += 0.06
        
        # WBC count abnormalities (infection risk)
        if wbc > 11 or wbc < 4:
            risk_score += 0.08
            
    elif problem_type == "heart_failure":
        ecg = float(features_dict.get("ECG Result", 0))
        pulse_rate = float(features_dict.get("Pulse Rate (bpm)", 70))
        
        # ECG abnormalities (ST elevation, T wave inversion, etc)
        if abs(ecg) > 2:
            risk_score += 0.18
        elif abs(ecg) > 1:
            risk_score += 0.10
        
        # Abnormal pulse rate (tachycardia or bradycardia)
        if pulse_rate > 100 or pulse_rate < 50:
            risk_score += 0.15
        elif pulse_rate > 90 or pulse_rate < 60:
            risk_score += 0.08
    
    # BMI-based consideration (using weight and age)
    if weight > 100:
        risk_score += 0.08
    elif weight < 50:
        risk_score += 0.05
    
    # Add slight randomness for demo purposes
    noise = random.uniform(-0.02, 0.02)
    risk_score = risk_score + noise
    
    # Clamp between realistic bounds
    risk_score = min(max(risk_score, 0.10), 0.95)
    
    return risk_score


def get_risk_level(prob):
    if prob >= 0.7:
        return "High"
    elif prob >= 0.4:
        return "Medium"
    else:
        return "Low"


def generate_follow_up_plan(problem_type, risk_level):
    if risk_level == "High":
        timing = "Within 3 days"
        method = "Phone call + SMS/App reminder"
    elif risk_level == "Medium":
        timing = "Within 7 days"
        method = "SMS/App reminder"
    else:
        timing = "Within 14 days"
        method = "Standard email/App reminder"

    return {
        "timing": timing,
        "method": method,
        "reason": f"{risk_level} risk {problem_type.replace('_', ' ').title()} patient."
    }


def fetch_external_factors_stub():
    """
    External data integration stub.
    Replace with real weather/social APIs later.
    """
    return {
        "air_quality_index": 55,
        "social_event_count": 3,
        "note": "Demo external data. Replace with live API."
    }


def calculate_staffing_simulation(patients):
    """
    patients: [{ "risk_level": "High/Medium/Low", "problem_type": "..." }]
    """
    total = len(patients)
    high = sum(1 for p in patients if p.get("risk_level") == "High")
    med = sum(1 for p in patients if p.get("risk_level") == "Medium")
    low = total - high - med

    expected_readmissions = high * 0.8 + med * 0.4 + low * 0.1

    required_doctors = max(1, int(1 + expected_readmissions / 10 + high / 5))
    required_nurses = max(2, int(2 + expected_readmissions / 4 + high / 3 + med / 5))
    required_beds = max(0, int(expected_readmissions) + high)

    return {
        "total_patients": total,
        "risk_counts": {"High": high, "Medium": med, "Low": low},
        "expected_readmissions": round(expected_readmissions, 2),
        "required_doctors": required_doctors,
        "required_nurses": required_nurses,
        "required_beds": required_beds,
        "message": "Staffing simulation based on current predicted risk mix."
    }


def enrich_from_dataset(admission_id):
    """
    Lookup doctor/hospital/admission/discharge from dataset using admission_id.
    Adjust column names to match your CSV.
    """
    if df_data is None or not admission_id:
        return {}

    col_map = {
        "Admission ID": ["Admission ID", "admission_id", "AdmissionID"],
        "Doctor Name": ["Doctor Name", "doctor_name", "Physician"],
        "Hospital Name": ["Hospital Name", "hospital_name"],
        "Admission Date": ["Admission Date", "admission_date"],
        "Discharge Date": ["Discharge Date", "discharge_date"],
    }

    adm_col = None
    for c in col_map["Admission ID"]:
        if c in df_data.columns:
            adm_col = c
            break
    if adm_col is None:
        return {}

    row = df_data[df_data[adm_col].astype(str) == str(admission_id)]
    if row.empty:
        return {}

    row = row.iloc[0]
    out = {}

    def pick(col_key):
        for c in col_map[col_key]:
            if c in df_data.columns:
                return row.get(c)
        return None

    out["doctor_name"] = pick("Doctor Name")
    out["hospital_name"] = pick("Hospital Name")
    out["admission_date"] = pick("Admission Date")
    out["discharge_date"] = pick("Discharge Date")

    return {
        k: (str(v) if pd.notna(v) else None)
        for k, v in out.items()
        if v is not None
    }


def build_pdf(report_data):
    """
    Build a comprehensive, medically-informed PDF report with all required sections:
    1. Patient & Admission Details
    2. Risk Summary & Overview
    3. Cardiac Overview (Heart Failure specific)
    4. Follow-up & Communication Plan
    5. Staff Suggestion (Cohort-level staffing)
    6. Clinical Metrics
    """
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
    from reportlab.lib.units import inch
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.4*inch, bottomMargin=0.4*inch)
    
    # Color palette matching frontend
    PRIMARY_BLUE = colors.HexColor("#2563eb")
    PRIMARY_DARK = colors.HexColor("#1e40af")
    SUCCESS_GREEN = colors.HexColor("#10b981")
    WARNING_ORANGE = colors.HexColor("#f59e0b")
    DANGER_RED = colors.HexColor("#ef4444")
    LIGHT_BG = colors.HexColor("#f8fafc")
    GRAY_700 = colors.HexColor("#334155")
    GRAY_600 = colors.HexColor("#475569")
    
    story = []
    # Paragraph styles for wrapping table cells
    cell_style = ParagraphStyle(name='cell', fontSize=8, leading=10, textColor=GRAY_700)
    cell_bold = ParagraphStyle(name='cell_bold', fontSize=9, leading=11, textColor=GRAY_700, fontName='Helvetica-Bold')
    header_cell = ParagraphStyle(name='header_cell', fontSize=11, leading=13, textColor=colors.white, fontName='Helvetica-Bold')

    def p(val, bold=False):
        if val is None:
            val = ""
        # Ensure strings are safe
        return Paragraph(str(val), cell_bold if bold else cell_style)

    def p_header(val):
        if val is None:
            val = ""
        return Paragraph(str(val), header_cell)
    
    # ==================== HEADER ====================
    from datetime import datetime
    report_date = datetime.now().strftime("%B %d, %Y")
    
    header_data = [
        [
            Paragraph("🏥 <b>UMKC Hospital</b><br/><font size=9>Patient Readmission Risk Assessment</font>", 
                     ParagraphStyle(name="header", fontSize=16, textColor=colors.white, fontName="Helvetica-Bold", leading=18)),
            Paragraph(f"<b>Risk Report</b><br/><font size=8>{report_date}</font>", 
                     ParagraphStyle(name="subtitle", fontSize=12, textColor=colors.white, fontName="Helvetica-Bold", alignment=2, leading=16))
        ]
    ]
    
    header_table = Table(header_data, colWidths=[4*inch, 2*inch])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PRIMARY_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 18),
        ("RIGHTPADDING", (0, 0), (-1, -1), 18),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.2*inch))
    
    # ==================== SECTION 1: PATIENT & ADMISSION DETAILS ====================
    meta = report_data.get("meta", {})
    doctor_name = report_data.get("doctor_name") or meta.get("doctor_name", "").strip()
    hospital_name = report_data.get("hospital_name") or meta.get("hospital_name", "").strip()
    
    # Build patient details table - only include non-empty values
    patient_details = [[p_header("PATIENT & ADMISSION DETAILS"), p_header(""), p_header("")]]

    if meta.get("admission_id", "").strip():
        patient_details.append([p("Admission ID"), p(meta.get("admission_id")), p("")])
    if meta.get("patient_name", "").strip():
        patient_details.append([p("Patient Name"), p(meta.get("patient_name")), p("")])
    if doctor_name:
        patient_details.append([p("Doctor"), p(doctor_name), p("")])
    if hospital_name:
        patient_details.append([p("Hospital"), p(hospital_name), p("")])
    if meta.get("admission_date", "").strip() or meta.get("discharge_date", "").strip():
        patient_details.append([p("Admission Date"), p(meta.get("admission_date", "")), p(meta.get("discharge_date", ""))])

    # If no data rows added, add at least the ID
    if len(patient_details) == 1:
        patient_details.append([p("Patient Information"), p("Not provided"), p("")])

    patient_table = Table(patient_details, colWidths=[1.8*inch, 2.1*inch, 2.1*inch])
    patient_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("BACKGROUND", (0, 1), (-1, -1), LIGHT_BG),
        ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        # Header padding
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("LEFTPADDING", (0, 0), (-1, 0), 8),
        ("RIGHTPADDING", (0, 0), (-1, 0), 8),
        # Body padding
        ("TOPPADDING", (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ("LEFTPADDING", (0, 1), (-1, -1), 6),
        ("RIGHTPADDING", (0, 1), (-1, -1), 6),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    story.append(patient_table)
    story.append(Spacer(1, 0.15*inch))
    
    # ==================== SECTION 2: RISK SUMMARY ====================
    probability = report_data.get("probability", 0)
    risk_level = report_data.get("risk_level", "N/A")
    problem_type_label = report_data.get("problem_type_label", "N/A")
    
    # Determine risk color and description
    if isinstance(risk_level, str) and risk_level.lower() == "high":
        risk_color = DANGER_RED
        risk_desc = "⚠️ HIGH RISK - Immediate intervention required"
    elif isinstance(risk_level, str) and risk_level.lower() == "medium":
        risk_color = WARNING_ORANGE
        risk_desc = "⚠️ MEDIUM RISK - Enhanced monitoring recommended"
    else:
        risk_color = SUCCESS_GREEN
        risk_desc = "✓ LOW RISK - Routine follow-up appropriate"
    
    risk_summary = [
        [p_header("READMISSION RISK SUMMARY"), p_header(""), p_header("")],
        [p("Condition"), p(problem_type_label), p("")],
        [p("30-Day Readmission Risk"), p(f"{round(probability * 100, 1)}%"), p("")],
        [p("Risk Classification"), p(risk_level), p("")],
        [p("Assessment"), p(risk_desc), p("")],
    ]

    risk_table = Table(risk_summary, colWidths=[1.8*inch, 2.1*inch, 2.1*inch])
    risk_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("BACKGROUND", (0, 1), (-1, -1), LIGHT_BG),
        ("BACKGROUND", (1, 3), (-1, 3), risk_color),
        ("TEXTCOLOR", (1, 3), (-1, 3), colors.white),
        ("FONTNAME", (1, 3), (-1, 3), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        # Header padding
        ("TOPPADDING", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 9),
        ("LEFTPADDING", (0, 0), (-1, 0), 10),
        ("RIGHTPADDING", (0, 0), (-1, 0), 10),
        # Body padding
        ("TOPPADDING", (0, 1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
        ("LEFTPADDING", (0, 1), (-1, -1), 8),
        ("RIGHTPADDING", (0, 1), (-1, -1), 8),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    # Append the risk table alone; the visual (pie) will be added near the end of the report
    story.append(risk_table)
    story.append(Spacer(1, 0.12*inch))
    
    # ==================== SECTION 3: CLINICAL METRICS & CARDIAC OVERVIEW ====================
    features = report_data.get("features", {})
    problem_type = report_data.get("problem_type")
    
    def format_value(val):
        """Format value for display, handling various types"""
        if val is None or val == "" or str(val).upper() == "N/A":
            return None
        if isinstance(val, (int, float)):
            return str(val) if val != 0 else None
        val_str = str(val).strip()
        return val_str if val_str and val_str.upper() != "N/A" else None
    
    # Build clinical metrics table - only include non-empty values
    clinical_metrics = [[p_header("KEY VITAL SIGNS & CLINICAL INDICATORS"), p_header(""), p_header("")]]
    
    # Common metrics
    common_fields = [
        ("Age (years)", "Age"),
        ("Weight (kg)", "Weight"),
        ("Blood Pressure", "Blood Pressure"),
        ("Cholesterol (mg/dL)", "Cholesterol"),
        ("Insulin (mIU/L)", "Insulin"),
        ("Platelets (K/µL)", "Platelets"),
    ]
    
    for label, key in common_fields:
        val = format_value(features.get(key))
        if val:
            clinical_metrics.append([p(label), p(val), p("")])
    
    # Disease-specific metrics
    if problem_type == "diabetes":
        diabetes_fields = [
            ("Hemoglobin - HbA1c (g/dL)", "Hemoglobin (g/dL)"),
            ("WBC Count (10^9/L)", "WBC Count (10^9/L)"),
            ("Urine Glucose (mg/dL)", "Urine Glucose (mg/dL)"),
            ("Urine Protein (mg/dL)", "Urine Protein (mg/dL)"),
        ]
        for label, key in diabetes_fields:
            val = format_value(features.get(key))
            if val:
                clinical_metrics.append([p(label), p(val), p("")])
                
    elif problem_type == "heart_failure":
        hf_fields = [
            ("ECG Result (mV)", "ECG Result", "CARDIAC ABNORMALITY"),
            ("Pulse Rate (bpm)", "Pulse Rate (bpm)", "ARRHYTHMIA RISK"),
        ]
        for label, key, note in hf_fields:
            val = format_value(features.get(key))
            if val:
                clinical_metrics.append([p(label), p(val), p(note)])
    
    # If only header, add a note
    if len(clinical_metrics) == 1:
        clinical_metrics.append([p("Clinical Data"), p("See features section"), p("")])
    
    clinical_table = Table(clinical_metrics, colWidths=[2*inch, 2*inch, 2*inch])
    clinical_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("BACKGROUND", (0, 1), (-1, -1), LIGHT_BG),
        ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        # Header padding
        ("TOPPADDING", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 9),
        ("LEFTPADDING", (0, 0), (-1, 0), 10),
        ("RIGHTPADDING", (0, 0), (-1, 0), 10),
        # Body padding
        ("TOPPADDING", (0, 1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
        ("LEFTPADDING", (0, 1), (-1, -1), 8),
        ("RIGHTPADDING", (0, 1), (-1, -1), 8),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    story.append(clinical_table)
    story.append(Spacer(1, 0.15*inch))
    
    # ==================== SECTION 4: FOLLOW-UP & COMMUNICATION PLAN ====================
    fu = report_data.get("follow_up", {})
    
    followup_data = [
        [p_header("FOLLOW-UP & COMMUNICATION PLAN"), p_header(""), p_header("")],
        [p("Contact Timing"), p(fu.get("timing", "Standard")), p("")],
        [p("Preferred Method"), p(fu.get("method", "Standard")), p("")],
        [p("Clinical Rationale"), p(fu.get("reason", "See risk assessment")), p("")],
        [p("Recommended Actions"), p("Monitor status, ensure compliance"), p("Arrange specialist if indicated")],
    ]
    
    followup_table = Table(followup_data, colWidths=[1.8*inch, 2.1*inch, 2.1*inch])
    followup_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("BACKGROUND", (0, 1), (-1, -1), LIGHT_BG),
        ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        # Header padding
        ("TOPPADDING", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 9),
        ("LEFTPADDING", (0, 0), (-1, 0), 10),
        ("RIGHTPADDING", (0, 0), (-1, 0), 10),
        # Body padding
        ("TOPPADDING", (0, 1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
        ("LEFTPADDING", (0, 1), (-1, -1), 8),
        ("RIGHTPADDING", (0, 1), (-1, -1), 8),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    story.append(followup_table)
    story.append(Spacer(1, 0.15*inch))
    
    # ==================== SECTION 5: STAFF SUGGESTION (COHORT-LEVEL STAFFING) ====================
    # Calculate staffing needs based on this patient's risk profile
    risk_multiplier = {"High": 2.0, "Medium": 1.5, "Low": 1.0}.get(risk_level, 1.0)
    
    staffing_suggestion = [
        [p_header("STAFFING RECOMMENDATION (COHORT-LEVEL IMPACT)"), p_header(""), p_header("")],
        [p("Risk Level Impact"), p(f"{risk_level} Risk Patient"), p(f"Multiplier: {risk_multiplier:.1f}x base staffing")],
        [p("Recommended Physician"), p("1 attending physician oversight"), p("Daily rounds recommended")],
        [p("Recommended Nursing"), p(f"{int(2 * risk_multiplier)} RN hours/shift"), p("Increased monitoring frequency")],
        [p("Bed Allocation"), p(f"{int(1 * risk_multiplier)} acute/monitored bed(s)"), p("High-risk unit placement preferred")],
        [p("Care Coordinator"), p("Dedicated discharge planner"), p("Begin within 48 hours of admission")],
        [p("Follow-up Capacity"), p(f"Requires {fu.get('method', 'SMS/Phone')} capability"), p("Schedule before discharge")],
    ]
    
    staffing_table = Table(staffing_suggestion, colWidths=[1.8*inch, 2.1*inch, 2.1*inch])
    staffing_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("BACKGROUND", (0, 1), (-1, -1), LIGHT_BG),
        ("BACKGROUND", (1, 1), (1, 1), risk_color),
        ("TEXTCOLOR", (1, 1), (1, 1), colors.white),
        ("FONTNAME", (1, 1), (1, 1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        # Header padding
        ("TOPPADDING", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 9),
        ("LEFTPADDING", (0, 0), (-1, 0), 10),
        ("RIGHTPADDING", (0, 0), (-1, 0), 10),
        # Body padding
        ("TOPPADDING", (0, 1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
        ("LEFTPADDING", (0, 1), (-1, -1), 8),
        ("RIGHTPADDING", (0, 1), (-1, -1), 8),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    story.append(staffing_table)
    story.append(Spacer(1, 0.15*inch))
    
    # ==================== SECTION 6: CLINICAL NOTES & FOOTER ====================
    notes_text = Paragraph(
        f"<b>Clinical Summary:</b> This {problem_type_label.lower()} patient presents with {risk_level.lower()} risk for 30-day readmission. "
        f"Close monitoring and adherence to follow-up protocols are critical. "
        f"All recommended interventions should be documented in the patient's EHR.",
        ParagraphStyle(name="notes", fontSize=8, textColor=GRAY_700, leading=10, alignment=0)
    )
    story.append(notes_text)
    story.append(Spacer(1, 0.10*inch))

    # ==================== RISK VISUALIZATION (PAGE END) ====================
    # Render donut pie near the end so it has its own clear spot.
    try:
        import matplotlib.pyplot as plt
        pie_buf = io.BytesIO()
        fig, ax = plt.subplots(figsize=(2.2, 2.2), dpi=100)
        pct = max(0.0, min(1.0, float(probability)))
        try:
            rc = (risk_color.red(), risk_color.green(), risk_color.blue())
        except Exception:
            rc = (1.0, 0.2, 0.2)
        ax.pie([pct, 1 - pct], colors=[rc, (230/255, 230/255, 230/255)], startangle=90, wedgeprops=dict(width=0.45))
        ax.set(aspect="equal")
        ax.text(0, 0, f"{int(round(pct*100))}%", ha='center', va='center', fontsize=12, color='#0f172a')
        plt.tight_layout()
        fig.savefig(pie_buf, format='png', transparent=True)
        plt.close(fig)
        pie_buf.seek(0)
        img = Image(pie_buf, 2.0*inch, 2.0*inch)
        viz_title = Paragraph("<b>RISK VISUALIZATION</b>", ParagraphStyle(name="viz_title", fontSize=11, alignment=1))
        story.append(Spacer(1, 0.12*inch))
        story.append(viz_title)
        story.append(Spacer(1, 0.06*inch))
        # Center the image using a single-cell table
        img_table = Table([[img]], colWidths=[6.6*inch])
        img_table.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        story.append(img_table)
        story.append(Spacer(1, 0.12*inch))
    except Exception as e:
        # If rendering fails, log to stdout so user can see why on server logs
        print("[WARN] Could not render risk visualization:", e)
    
    # ==================== FOOTER ====================
    footer_text = Paragraph(
        f"<font size=8 color='#475569'><i>Report Generated: {report_date} | UMKC Hospital AI Analytics System | "
        f"Confidential - For Healthcare Provider Use Only</i></font>",
        ParagraphStyle(name="footer", fontSize=8, alignment=1)
    )
    story.append(footer_text)
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer


# ========= ROUTES =========

@app.route("/")
def serve_frontend():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/api/predict", methods=["POST"])
def predict():
    """
    Request JSON:
    {
      "problem_type": "diabetes" | "heart_failure",
      "meta": {...},
      "features": { ... }
    }
    """
    data = request.get_json() or {}
    problem_type = data.get("problem_type")
    meta = data.get("meta", {}) or {}
    features = data.get("features", {}) or {}

    if problem_type not in ["diabetes", "heart_failure"]:
        return jsonify({
            "success": False,
            "error": "Invalid or missing 'problem_type'."
        }), 400

    # Fill external factors from stub if empty/zero/None
    if not features.get("air_quality_index") or not features.get("social_event_count"):
        ext = fetch_external_factors_stub()
        features.setdefault("air_quality_index", ext["air_quality_index"])
        features.setdefault("social_event_count", ext["social_event_count"])
        external_used = {
            "air_quality_index": ext["air_quality_index"],
            "social_event_count": ext["social_event_count"],
            "note": ext.get("note")
        }
    else:
        external_used = {
            "air_quality_index": features.get("air_quality_index"),
            "social_event_count": features.get("social_event_count"),
        }

    try:
        # Use fallback prediction if model is not available
        if model is None:
            print("[INFO] Using fallback prediction (model not loaded)")
            prob = generate_fallback_prediction(problem_type, features)
        else:
            X = preprocess_input(problem_type, features)
            if hasattr(model, "predict_proba"):
                prob = float(model.predict_proba(X)[0][1])
            else:
                prob = float(model.predict(X)[0])

        risk_level = get_risk_level(prob)
        follow_up = generate_follow_up_plan(problem_type, risk_level)

        # enrich from dataset using admission_id
        admission_id = meta.get("admission_id")
        enrich = enrich_from_dataset(admission_id)

        if enrich:
            meta.setdefault("admission_date", enrich.get("admission_date"))
            meta.setdefault("discharge_date", enrich.get("discharge_date"))

        response = {
            "success": True,
            "problem_type": problem_type,
            "problem_type_label": "Diabetes" if problem_type == "diabetes" else "Heart Failure",
            "probability": round(prob, 4),
            "risk_level": risk_level,
            "follow_up": follow_up,
            "meta": meta,
            "doctor_name": enrich.get("doctor_name"),
            "hospital_name": enrich.get("hospital_name"),
            "external_factors": external_used,
            "features_used": features,
        }

        return jsonify(response)

    except Exception as e:
        # Log on server for debugging
        print("[ERROR] Prediction failed:", e)
        return jsonify({
            "success": False,
            "error": f"Prediction failed: {str(e)}"
        }), 500


@app.route("/api/staffing_simulation", methods=["POST"])
def staffing_simulation():
    data = request.get_json() or {}
    patients = data.get("patients", []) or []
    sim = calculate_staffing_simulation(patients)
    sim["success"] = True
    return jsonify(sim)


@app.route("/api/report/pdf", methods=["POST"])
def report_pdf():
    data = request.get_json() or {}
    problem_type = data.get("problem_type")
    meta = data.get("meta", {}) or {}
    admission_id = meta.get("admission_id")

    # Re-enrich from dataset
    enrich = enrich_from_dataset(admission_id) or {}
    doctor_name = data.get("doctor_name") or enrich.get("doctor_name")
    hospital_name = data.get("hospital_name") or enrich.get("hospital_name")

    meta.setdefault("admission_date", enrich.get("admission_date"))
    meta.setdefault("discharge_date", enrich.get("discharge_date"))

    report_payload = {
        "problem_type": problem_type,
        "problem_type_label": "Diabetes" if problem_type == "diabetes" else "Heart Failure",
        "meta": meta,
        "probability": data.get("probability", 0),
        "risk_level": data.get("risk_level", "N/A"),
        "follow_up": data.get("follow_up", {}),
        "doctor_name": doctor_name,
        "hospital_name": hospital_name,
        "features": data.get("features", {}),
        "external_factors": data.get("external_factors", {}),
    }

    pdf_stream = build_pdf(report_payload)
    filename = f"Readmission_Report_{meta.get('admission_id', 'patient')}.pdf"

    return send_file(
        pdf_stream,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


# ========= MAIN =========

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
