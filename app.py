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
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")

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
try:
    model = joblib.load(MODEL_PATH)
    print("[INFO] Model loaded.")
except Exception as e:
    print(f"[ERROR] Failed to load model: {e}")
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
    - Disease-specific features for the other condition are zeroed.
    - Returns: pandas.DataFrame (NOT numpy array).
    """
    if model is not None and hasattr(model, "feature_names_in_"):
        cols = list(model.feature_names_in_)
    else:
        cols = list(ALL_FEATURES)

    row = {}

    for col in cols:
        raw_val = features_dict.get(col, 0)

        # zero-out features not relevant to selected problem_type
        if problem_type == "diabetes" and col in HEART_FAILURE_FEATURES:
            raw_val = 0
        if problem_type == "heart_failure" and col in DIABETES_FEATURES:
            raw_val = 0

        val = encode_categorical(col, raw_val)

        try:
            val = float(val)
        except (TypeError, ValueError):
            val = 0.0

        row[col] = val

    X = pd.DataFrame([row], columns=cols)
    return X


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
    Build PDF in memory and return BytesIO.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 40

    def line(txt, size=11, color=colors.black, bold=False):
        nonlocal y
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.setFillColor(color)
        c.drawString(40, y, txt)
        y -= 16

    # Header
    line("Hospital Readmission Risk Report", size=16, bold=True)
    y -= 6

    # Hospital & doctor
    hospital = report_data.get("hospital_name", "N/A")
    doctor = report_data.get("doctor_name", "N/A")
    line(f"Hospital: {hospital}", size=11)
    line(f"Responsible Doctor: {doctor}", size=11)
    y -= 4

    # Patient meta
    meta = report_data.get("meta", {})
    line("Patient Details:", bold=True)
    line(f"  Admission ID: {meta.get('admission_id', 'N/A')}")
    line(f"  Patient Name: {meta.get('patient_name', 'N/A')}")
    line(f"  Admission Date: {meta.get('admission_date', 'N/A')}")
    line(f"  Discharge Date: {meta.get('discharge_date', 'N/A')}")
    y -= 4

    # Prediction summary
    line("Prediction Summary:", bold=True)
    line(f"  Condition: {report_data.get('problem_type_label', 'N/A')}")
    line(
        f"  Readmission Probability (30 days): "
        f"{round(report_data.get('probability', 0) * 100, 2)}%"
    )
    line(f"  Risk Level: {report_data.get('risk_level', 'N/A')}")
    fu = report_data.get("follow_up", {})
    line(
        f"  Recommended Follow-up: "
        f"{fu.get('timing', 'N/A')} via {fu.get('method', 'N/A')}"
    )
    y -= 4

    # External factors
    ext = report_data.get("external_factors", {})
    if ext:
        line("External Factors:", bold=True)
        line(f"  Air Quality Index: {ext.get('air_quality_index', 'N/A')}")
        line(f"  Social Event Count: {ext.get('social_event_count', 'N/A')}")
        y -= 4

    # Lab / ECG visualization
    features = report_data.get("features", {})
    line("Clinical Snapshot (Key Values):", bold=True)

    chart_items = []
    problem_type = report_data.get("problem_type")

    if problem_type == "diabetes":
        chart_items = [
            ("Hemoglobin", float(features.get("Hemoglobin (g/dL)", 0))),
            ("WBC", float(features.get("WBC Count (10^9/L)", 0))),
            ("Urine Prot", float(features.get("Urine Protein (mg/dL)", 0))),
            ("Urine Gluc", float(features.get("Urine Glucose (mg/dL)", 0))),
        ]
    elif problem_type == "heart_failure":
        chart_items = [
            ("ECG", float(features.get("ECG Result", 0))),
            ("Pulse", float(features.get("Pulse Rate (bpm)", 0))),
        ]

    for label, val in chart_items:
        line(f"  {label}: {val}")

    if chart_items:
        y -= 4
        max_val = max(v for _, v in chart_items) or 1
        x0 = 60
        bar_max_width = 200
        for label, val in chart_items:
            bar_width = (val / max_val) * bar_max_width
            c.setFillColor(colors.lightblue)
            c.rect(x0, y - 6, bar_width, 6, fill=True, stroke=False)
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 8)
            c.drawString(x0 + bar_max_width + 10, y - 4, label)
            y -= 12

    c.showPage()
    c.save()
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
    if model is None:
        return jsonify({"success": False, "error": "Model not loaded on server."}), 500

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
