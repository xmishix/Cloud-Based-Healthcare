const apiBase = "http://127.0.0.1:5000"; // same origin
let patients = [];
let staffingChart = null;
let lastReportData = null;

// Toggle conditional disease fields
document.getElementById("problem_type").addEventListener("change", (e) => {
  const val = e.target.value;
  const diab = document.getElementById("diabetes-fields");
  const hf = document.getElementById("hf-fields");

  if (val === "diabetes") {
    diab.classList.remove("hidden");
    hf.classList.add("hidden");
  } else if (val === "heart_failure") {
    hf.classList.remove("hidden");
    diab.classList.add("hidden");
  } else {
    diab.classList.add("hidden");
    hf.classList.add("hidden");
  }
});

// Handle prediction form submission
document.getElementById("predictionForm").addEventListener("submit", async (e) => {
  e.preventDefault();

  const problemType = document.getElementById("problem_type").value;
  if (!problemType) {
    alert("Please select Problem Type.");
    return;
  }

  // Meta
  const meta = {
    admission_id: document.getElementById("admission_id").value,
    patient_name: document.getElementById("patient_name").value,
    admission_date: document.getElementById("admission_date").value,
    discharge_date: document.getElementById("discharge_date").value
  };

  // Common features
  const features = {
    "Age": document.getElementById("Age").value,
    "Sex": document.getElementById("Sex").value,
    "Weight": document.getElementById("Weight").value,
    "Blood Pressure": document.getElementById("Blood_Pressure").value,
    "Cholesterol": document.getElementById("Cholesterol").value,
    "Insulin": document.getElementById("Insulin").value,
    "Platelets": document.getElementById("Platelets").value,
    "Diabetics": document.getElementById("Diabetics").value,
    "air_quality_index": document.getElementById("air_quality_index").value,
    "social_event_count": document.getElementById("social_event_count").value
  };

  // Diabetes
  if (problemType === "diabetes") {
    features["Hemoglobin (g/dL)"] = document.getElementById("Hemoglobin").value;
    features["WBC Count (10^9/L)"] = document.getElementById("WBC").value;
    features["Platelet Count (10^9/L)"] = document.getElementById("Platelet_Count").value;
    features["Urine Protein (mg/dL)"] = document.getElementById("Urine_Protein").value;
    features["Urine Glucose (mg/dL)"] = document.getElementById("Urine_Glucose").value;
  }

  // Heart Failure
  if (problemType === "heart_failure") {
    features["ECG Result"] = document.getElementById("ECG_Result").value;
    features["Pulse Rate (bpm)"] = document.getElementById("Pulse_Rate").value;
  }

  try {
    const res = await fetch(`${apiBase}/api/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ problem_type: problemType, meta, features })
    });

    const data = await res.json();
    if (!data.success) {
      throw new Error(data.error || "Prediction failed");
    }

    // Update prediction UI
    renderPredictionResult(data);

    // Store for follow-up & staffing
    patients.push({
      admission_id: data.meta.admission_id,
      patient_name: data.meta.patient_name,
      problem_type: data.problem_type,
      risk_level: data.risk_level,
      follow_up: data.follow_up
    });

    renderFollowupTable();
    await updateStaffingDashboard();

    // Prepare data for PDF button
    lastReportData = {
      problem_type: data.problem_type,
      meta: data.meta,
      probability: data.probability,
      risk_level: data.risk_level,
      follow_up: data.follow_up,
      doctor_name: data.doctor_name,
      hospital_name: data.hospital_name,
      features: data.features_used,
      external_factors: data.external_factors
    };

    const pdfBtn = document.getElementById("downloadPdfBtn");
    pdfBtn.disabled = false;

  } catch (err) {
    console.error(err);
    document.getElementById("predictionResult").innerHTML =
      `<span style="color:#b91c1c;">Error: ${err.message}</span>`;
  }
});

function renderPredictionResult(data) {
  const box = document.getElementById("predictionResult");
  box.classList.remove("muted");

  const meta = data.meta || {};
  const hospital = data.hospital_name || "N/A";
  const doc = data.doctor_name || "N/A";

  box.innerHTML = `
    <div><strong>Admission ID:</strong> ${meta.admission_id || "-"}</div>
    <div><strong>Patient:</strong> ${meta.patient_name || "-"}</div>
    <div><strong>Hospital:</strong> ${hospital}</div>
    <div><strong>Doctor:</strong> ${doc}</div>
    <div><strong>Condition:</strong> ${data.problem_type_label}</div>
    <div><strong>Readmission Probability (30 days):</strong> ${(data.probability * 100).toFixed(2)}%</div>
    <div><strong>Risk Level:</strong> ${data.risk_level}</div>
    <div><strong>Follow-up:</strong> ${data.follow_up.timing} via ${data.follow_up.method}</div>
    <div style="color:#6b7280; font-size:11px;">${data.follow_up.reason}</div>
  `;
}

// Follow-up table
function renderFollowupTable() {
  const tbody = document.querySelector("#followupTable tbody");
  tbody.innerHTML = "";

  patients.forEach((p, i) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${i + 1}</td>
      <td>${p.admission_id || "-"}</td>
      <td>${p.patient_name || "-"}</td>
      <td>${prettyProblemType(p.problem_type)}</td>
      <td>${p.risk_level}</td>
      <td>${p.follow_up.timing}</td>
      <td>${p.follow_up.method}</td>
    `;
    tbody.appendChild(tr);
  });
}

// Staffing dashboard
async function updateStaffingDashboard() {
  const summaryDiv = document.getElementById("staffingSummary");
  if (patients.length === 0) {
    summaryDiv.textContent = "No patients yet.";
    return;
  }

  try {
    const res = await fetch(`${apiBase}/api/staffing_simulation`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        patients: patients.map(p => ({
          risk_level: p.risk_level,
          problem_type: p.problem_type
        }))
      })
    });

    const data = await res.json();
    if (!data.success) throw new Error("Staffing simulation failed");

    const { risk_counts, expected_readmissions,
      required_doctors, required_nurses, required_beds } = data;

    summaryDiv.classList.remove("muted");
    summaryDiv.innerHTML = `
      <div><strong>Total Patients:</strong> ${data.total_patients}</div>
      <div><strong>Risk Mix:</strong> High: ${risk_counts.High},
           Medium: ${risk_counts.Medium}, Low: ${risk_counts.Low}</div>
      <div><strong>Expected Readmissions:</strong> ${expected_readmissions}</div>
      <div><strong>Suggested Staffing:</strong>
        ${required_doctors} Doctors,
        ${required_nurses} Nurses,
        ${required_beds} Beds
      </div>
      <div style="color:#6b7280; font-size:11px;">${data.message}</div>
    `;

    renderStaffingChart(risk_counts, required_doctors, required_nurses, required_beds);

  } catch (err) {
    summaryDiv.innerHTML = `<span style="color:#b91c1c;">${err.message}</span>`;
  }
}

function renderStaffingChart(riskCounts, doctors, nurses, beds) {
  const ctx = document.getElementById("staffingChart").getContext("2d");
  const labels = ["High Risk", "Medium Risk", "Low Risk", "Doctors", "Nurses", "Beds"];
  const values = [
    riskCounts.High,
    riskCounts.Medium,
    riskCounts.Low,
    doctors,
    nurses,
    beds
  ];

  if (staffingChart) staffingChart.destroy();

  staffingChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Count",
        data: values
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false }
      },
      scales: {
        y: { beginAtZero: true }
      }
    }
  });
}

function prettyProblemType(pt) {
  if (pt === "diabetes") return "Diabetes";
  if (pt === "heart_failure") return "Heart Failure";
  return pt;
}

// Download PDF
document.getElementById("downloadPdfBtn").addEventListener("click", async () => {
  if (!lastReportData) return;

  try {
    const res = await fetch(`${apiBase}/api/report/pdf`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(lastReportData)
    });

    if (!res.ok) {
      throw new Error("Failed to generate PDF");
    }

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const adm = lastReportData.meta?.admission_id || "patient";
    a.download = `Readmission_Report_${adm}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    alert(err.message);
  }
});
