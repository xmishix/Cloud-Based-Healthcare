const apiBase = "http://127.0.0.1:5000";
let patients = [];
let staffingChart = null;
let riskPieChart = null;
let lastPrediction = null;

// ====================== Initialization ======================
document.addEventListener("DOMContentLoaded", () => {
  setupEventListeners();
});

function setupEventListeners() {
  // Toggle disease-specific fields
  document.getElementById("problem_type").addEventListener("change", toggleDiseaseFields);
  
  // Form submission
  document.getElementById("predictionForm").addEventListener("submit", handlePredictionSubmit);
  
  // Download PDF button
  document.getElementById("downloadPdfBtn").addEventListener("click", downloadReport);
  
  // Staffing simulation button
  document.getElementById("simulateBtn").addEventListener("click", runStaffingSimulation);
}

// ====================== Field Toggle ======================
function toggleDiseaseFields(e) {
  const diseaseType = e.target.value;
  const diabetesFields = document.getElementById("diabetes-fields");
  const hfFields = document.getElementById("hf-fields");
  
  diabetesFields.classList.toggle("hidden", diseaseType !== "diabetes");
  hfFields.classList.toggle("hidden", diseaseType !== "heart_failure");
}

// ====================== Prediction Form ======================
async function handlePredictionSubmit(e) {
  e.preventDefault();
  
  const resultBox = document.getElementById("result");
  const downloadBtn = document.getElementById("downloadPdfBtn");
  
  // Show loading state
  resultBox.innerHTML = '<p style="text-align: center;">⏳ Generating prediction...</p>';
  downloadBtn.disabled = true;
  
  try {
    // Collect meta information
    const meta = {
      admission_id: document.getElementById("admission_id").value,
      patient_name: document.getElementById("patient_name").value,
      doctor_name: document.getElementById("doctor_name").value,
      hospital_name: document.getElementById("hospital_name").value,
      admission_date: document.getElementById("admission_date").value,
      discharge_date: document.getElementById("discharge_date").value
    };
    
    // Collect features
    const problemType = document.getElementById("problem_type").value;
    if (!problemType) {
      throw new Error("Please select a condition type");
    }
    
    const features = {
      "Age": parseFloat(document.getElementById("Age").value),
      "Sex": document.getElementById("Sex").value,
      "Weight": parseFloat(document.getElementById("Weight").value),
      "Blood Pressure": document.getElementById("Blood_Pressure").value,
      "Cholesterol": parseFloat(document.getElementById("Cholesterol").value),
      "Insulin": parseFloat(document.getElementById("Insulin").value),
      "Platelets": parseFloat(document.getElementById("Platelets").value),
      "Diabetics": document.getElementById("Diabetics").value,
      "air_quality_index": document.getElementById("air_quality_index").value ? parseFloat(document.getElementById("air_quality_index").value) : 0,
      "social_event_count": document.getElementById("social_event_count").value ? parseFloat(document.getElementById("social_event_count").value) : 0
    };
    
    // Add disease-specific features
    if (problemType === "diabetes") {
      features["Hemoglobin (g/dL)"] = parseFloat(document.getElementById("Hemoglobin").value) || 0;
      features["WBC Count (10^9/L)"] = parseFloat(document.getElementById("WBC").value) || 0;
      features["Platelet Count (10^9/L)"] = parseFloat(document.getElementById("Platelet_Count").value) || 0;
      features["Urine Protein (mg/dL)"] = parseFloat(document.getElementById("Urine_Protein").value) || 0;
      features["Urine Glucose (mg/dL)"] = parseFloat(document.getElementById("Urine_Glucose").value) || 0;
    } else if (problemType === "heart_failure") {
      features["ECG Result"] = parseFloat(document.getElementById("ECG_Result").value) || 0;
      features["Pulse Rate (bpm)"] = parseFloat(document.getElementById("Pulse_Rate").value) || 0;
    }
    
    // Send prediction request
    const response = await fetch(`${apiBase}/api/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ problem_type: problemType, meta, features })
    });
    
    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.error || "Prediction failed");
    }
    
    // Store prediction for PDF download
    lastPrediction = data;
    
    // Display result
    displayPredictionResult(data, meta);
    
    // Add to follow-up table
    addToFollowupTable(data, meta);
    
    // Update staffing dashboard
    patients.push({
      admission_id: meta.admission_id,
      patient_name: meta.patient_name,
      problem_type: problemType,
      risk_level: data.risk_level,
      probability: data.probability,
      follow_up: data.follow_up
    });
    
    // Update risk pie chart
    updateRiskPieChart();
    
    downloadBtn.disabled = false;
    
  } catch (error) {
    resultBox.innerHTML = `<div class="error">❌ Error: ${error.message}</div>`;
    downloadBtn.disabled = true;
  }
}

// ====================== Display Results ======================
function displayPredictionResult(data, meta) {
  const resultBox = document.getElementById("result");
  const riskClass = `risk-${data.risk_level.toLowerCase()}`;
  const probability = (data.probability * 100).toFixed(1);
  
  resultBox.className = "result-box";
  resultBox.innerHTML = `
    <h3 style="color: var(--primary); margin-top: 0;">✅ Prediction Complete</h3>
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--spacing-lg);">
      <div>
        <p><strong>Patient ID:</strong> ${meta.admission_id}</p>
        <p><strong>Patient Name:</strong> ${meta.patient_name}</p>
        <p><strong>Condition:</strong> ${data.problem_type_label}</p>
      </div>
      <div>
        <p><strong>Readmission Probability:</strong> <span style="font-size: 1.25rem; color: var(--primary);">${probability}%</span></p>
        <p><strong>Risk Level:</strong> <span class="${riskClass}">${data.risk_level}</span></p>
        <p><strong>Follow-up:</strong> ${data.follow_up.timing} via ${data.follow_up.method}</p>
      </div>
    </div>
  `;
}

function addToFollowupTable(data, meta) {
  const tbody = document.querySelector("#followupTable tbody");
  
  // Remove placeholder row if it exists
  if (tbody && tbody.children.length === 1 && tbody.firstChild && tbody.firstChild.cells && tbody.firstChild.cells.length === 1) {
    tbody.innerHTML = "";
  }
  
  if (!tbody) {
    console.error("Follow-up table body not found");
    return;
  }
  
  const row = document.createElement("tr");
  const probability = (data.probability * 100).toFixed(1);
  const riskClass = `risk-${data.risk_level.toLowerCase()}`;
  
  row.innerHTML = `
    <td>${tbody.children.length + 1}</td>
    <td>${meta.admission_id}</td>
    <td>${meta.patient_name}</td>
    <td><span class="${riskClass}">${data.risk_level}</span></td>
    <td>${probability}%</td>
    <td>${data.follow_up.method}</td>
    <td>${data.follow_up.timing}</td>
  `;
  
  tbody.appendChild(row);
}

// ====================== Staffing Simulation ======================
async function runStaffingSimulation() {
  const summaryDiv = document.getElementById("staffingSummary");
  const simDate = document.getElementById("simulation_date").value;
  const unit = document.getElementById("hospital_unit").value;
  
  if (patients.length === 0) {
    summaryDiv.innerHTML = '<div class="error">❌ Please add at least one patient prediction first</div>';
    return;
  }
  
  try {
    summaryDiv.innerHTML = '<p style="text-align: center;">⏳ Running simulation...</p>';
    
    const response = await fetch(`${apiBase}/api/staffing_simulation`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        simulation_date: simDate || new Date().toISOString().split('T')[0],
        hospital_unit: unit || "General Unit",
        patients: patients.map(p => ({
          risk_level: p.risk_level,
          problem_type: p.problem_type
        }))
      })
    });
    
    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.error || "Simulation failed");
    }
    
    displayStaffingResults(data);
    renderStaffingChart(data);
    
  } catch (error) {
    summaryDiv.innerHTML = `<div class="error">❌ Error: ${error.message}</div>`;
  }
}

// ====================== Risk Pie Chart ======================
function updateRiskPieChart() {
  const high = patients.filter(p => p.risk_level === "HIGH").length;
  const medium = patients.filter(p => p.risk_level === "MEDIUM").length;
  const low = patients.filter(p => p.risk_level === "LOW").length;
  const total = high + medium + low;
  
  if (total === 0) {
    // Clear chart if no data
    if (riskPieChart) {
      riskPieChart.destroy();
      riskPieChart = null;
    }
    return;
  }
  
  const ctx = document.getElementById("riskPieChart");
  if (!ctx) return;
  
  const canvasContext = ctx.getContext("2d");
  
  if (riskPieChart) {
    riskPieChart.destroy();
  }
  
  riskPieChart = new Chart(canvasContext, {
    type: "doughnut",
    data: {
      labels: ["High Risk", "Medium Risk", "Low Risk"],
      datasets: [{
        data: [high, medium, low],
        backgroundColor: [
          "rgba(239, 68, 68, 0.8)",    // red for high
          "rgba(245, 158, 11, 0.8)",   // orange for medium
          "rgba(16, 185, 129, 0.8)"    // green for low
        ],
        borderColor: [
          "rgba(239, 68, 68, 1)",
          "rgba(245, 158, 11, 1)",
          "rgba(16, 185, 129, 1)"
        ],
        borderWidth: 2,
        hoverOffset: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            padding: 15,
            font: { size: 12 },
            usePointStyle: true
          }
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              const percentage = ((context.parsed / total) * 100).toFixed(1);
              return `${context.label}: ${context.parsed} (${percentage}%)`;
            }
          }
        }
      }
    }
  });
}

function displayStaffingResults(data) {
  const summaryDiv = document.getElementById("staffingSummary");
  const { risk_counts, expected_readmissions, required_doctors, required_nurses, required_beds } = data;
  
  summaryDiv.className = "result-box";
  summaryDiv.innerHTML = `
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--spacing-lg);">
      <div>
        <p><strong>Total Patients Analyzed:</strong> ${data.total_patients}</p>
        <p><strong>High Risk:</strong> ${risk_counts?.High || 0}</p>
        <p><strong>Medium Risk:</strong> ${risk_counts?.Medium || 0}</p>
        <p><strong>Low Risk:</strong> ${risk_counts?.Low || 0}</p>
      </div>
      <div>
        <p><strong>Expected Readmissions:</strong> <span style="color: var(--danger); font-weight: 700;">${expected_readmissions}</span></p>
        <p><strong>Required Doctors:</strong> ${required_doctors}</p>
        <p><strong>Required Nurses:</strong> ${required_nurses}</p>
        <p><strong>Required Beds:</strong> ${required_beds}</p>
      </div>
    </div>
    <p style="color: var(--gray-600); font-size: 0.9rem; margin-top: var(--spacing-md);">💡 ${data.message || 'Staffing recommendation based on patient risk profile.'}</p>
  `;
}

function renderStaffingChart(data) {
  const ctx = document.getElementById("staffingChart").getContext("2d");
  const { risk_counts, required_doctors, required_nurses, required_beds } = data;
  
  const labels = ["High Risk", "Medium Risk", "Low Risk", "Doctors", "Nurses", "Beds"];
  const values = [
    risk_counts?.High || 0,
    risk_counts?.Medium || 0,
    risk_counts?.Low || 0,
    required_doctors,
    required_nurses,
    required_beds
  ];
  
  if (staffingChart) {
    staffingChart.destroy();
  }
  
  staffingChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [{
        label: "Count",
        data: values,
        backgroundColor: [
          "rgba(239, 68, 68, 0.7)",    // red for high
          "rgba(245, 158, 11, 0.7)",   // orange for medium
          "rgba(16, 185, 129, 0.7)",   // green for low
          "rgba(37, 99, 235, 0.7)",    // blue for doctors
          "rgba(168, 85, 247, 0.7)",   // purple for nurses
          "rgba(06, 182, 212, 0.7)"    // cyan for beds
        ],
        borderRadius: 6,
        borderSkipped: false
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        y: { beginAtZero: true, ticks: { stepSize: 1 } }
      }
    }
  });
}

// ====================== PDF Download ======================
async function downloadReport() {
  if (!lastPrediction) {
    alert("No prediction available");
    return;
  }
  
  try {
    const response = await fetch(`${apiBase}/api/report/pdf`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(lastPrediction)
    });
    
    if (!response.ok) {
      throw new Error("Failed to generate PDF");
    }
    
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `Readmission_Report_${lastPrediction.meta.admission_id}.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
    
  } catch (error) {
    alert(`Error downloading PDF: ${error.message}`);
  }
}
