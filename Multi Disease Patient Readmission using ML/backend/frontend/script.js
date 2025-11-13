/* ========================================
   MODERN HEALTHCARE DASHBOARD - JS
   ======================================== */

let lastRequestPayload = null;
let riskChart = null;
let staffChart = null;

// DOM Content Loaded
document.addEventListener("DOMContentLoaded", () => {
  initializeApp();
});

function initializeApp() {
  const problemSelect = document.getElementById("problem_type");
  const diabetesFields = document.getElementById("diabetes-fields");
  const heartFields = document.getElementById("heart-fields");
  const form = document.getElementById("prediction-form");
  const resultCard = document.getElementById("result-card");
  const pdfBtn = document.getElementById("download-pdf");
  const simButton = document.getElementById("run-simulation");
  const simOutput = document.getElementById("simulation-output");
  const loadingOverlay = document.getElementById("loading-overlay");

  // Toggle Diabetes/Heart specific fields with smooth animation
  problemSelect.addEventListener("change", () => {
    if (problemSelect.value === "Diabetes") {
      diabetesFields.classList.remove("hidden");
      heartFields.classList.add("hidden");
      animateSection(diabetesFields);
    } else {
      heartFields.classList.remove("hidden");
      diabetesFields.classList.add("hidden");
      animateSection(heartFields);
    }
  });

  // === Predict Readmission ===
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    // Show loading overlay
    showLoading();

    const payload = buildPayload();
    lastRequestPayload = payload;

    try {
      const res = await fetch("/api/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();

      if (!res.ok) {
        hideLoading();
        showError(data.error || "Prediction failed");
        return;
      }

      // Hide loading and show results
      hideLoading();
      renderPredictionResult(data);

      // Show result card with animation
      resultCard.classList.remove("hidden");
      animateSection(resultCard);

      // Scroll to results
      resultCard.scrollIntoView({ behavior: "smooth", block: "nearest" });

      simOutput.classList.add("hidden");

      // Show success notification
      showSuccess("Prediction completed successfully!");
    } catch (err) {
      console.error(err);
      hideLoading();
      showError("Server error while predicting. Please try again.");
    }
  });

  // === Run Staffing Simulation ===
  simButton.addEventListener("click", async () => {
    if (!lastRequestPayload) {
      showError("Please run a prediction first.");
      return;
    }

    const simDate = document.getElementById("simulation_date").value;
    const unit = document.getElementById("hospital_unit").value;

    if (!simDate || !unit) {
      showError("Please select both Simulation Date and Hospital Unit.");
      return;
    }

    // Show loading on button
    simButton.disabled = true;
    simButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> <span>Running Simulation...</span>';

    lastRequestPayload["Simulation Date"] = simDate;
    lastRequestPayload["Hospital Unit"] = unit;

    try {
      const res = await fetch("/api/simulate_staffing", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(lastRequestPayload),
      });

      const data = await res.json();

      if (!res.ok) {
        simButton.disabled = false;
        simButton.innerHTML = '<i class="fas fa-cogs"></i> <span>Run Staffing Simulation</span>';
        showError(data.error || "Simulation failed");
        return;
      }

      const s = data.staffing;
      simOutput.classList.remove("hidden");
      simOutput.innerHTML = `
        <strong>Simulation Results:</strong><br>
        <strong>Date:</strong> ${data.simulation_date}<br>
        <strong>Hospital:</strong> ${data.hospital_unit}<br>
        <strong>Expected Readmissions:</strong> ${s.expected_readmissions}<br>
        <strong>Recommended Resources:</strong>
        ${s.suggested_beds} beds, ${s.suggested_nurses} nurses, ${s.suggested_doctors} doctors
      `;

      // Show staff chart
      const staffChartContainer = document.getElementById("staff-chart-container");
      staffChartContainer.classList.remove("hidden");
      drawStaffChart(s);

      // Reset button
      simButton.disabled = false;
      simButton.innerHTML = '<i class="fas fa-cogs"></i> <span>Run Staffing Simulation</span>';

      showSuccess("Staffing simulation completed!");
    } catch (err) {
      console.error(err);
      simButton.disabled = false;
      simButton.innerHTML = '<i class="fas fa-cogs"></i> <span>Run Staffing Simulation</span>';
      showError("Error running staffing simulation.");
    }
  });

  // === PDF Download ===
  pdfBtn.addEventListener("click", async () => {
    if (!lastRequestPayload) {
      showError("Please run a prediction first.");
      return;
    }

    // Show loading on button
    pdfBtn.disabled = true;
    pdfBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> <span>Generating PDF...</span>';

    try {
      const res = await fetch("/api/report", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(lastRequestPayload),
      });

      if (!res.ok) {
        const err = await res.json();
        pdfBtn.disabled = false;
        pdfBtn.innerHTML = '<i class="fas fa-file-pdf"></i> <span>Download Clinical Report</span>';
        showError(err.error || "Failed to generate report");
        return;
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `readmission_report_${new Date().getTime()}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

      // Reset button
      pdfBtn.disabled = false;
      pdfBtn.innerHTML = '<i class="fas fa-file-pdf"></i> <span>Download Clinical Report</span>';

      showSuccess("PDF report generated successfully!");
    } catch (err) {
      console.error(err);
      pdfBtn.disabled = false;
      pdfBtn.innerHTML = '<i class="fas fa-file-pdf"></i> <span>Download Clinical Report</span>';
      showError("Error generating PDF.");
    }
  });
}

// ===== Build Payload =====
function buildPayload() {
  const problem_type = document.getElementById("problem_type").value;

  const payload = {
    "Patient ID": document.getElementById("patient_id").value || "N/A",
    "Patient Name": document.getElementById("patient_name").value || "N/A",
    "Admission Date": document.getElementById("admission_date").value || "N/A",
    "Discharge Date": document.getElementById("discharge_date").value || "N/A",
    "Problem Type": problem_type,
    "Age": Number(document.getElementById("age").value),
    "Sex": document.getElementById("sex").value,
    "Weight": Number(document.getElementById("weight").value),
    "Blood Pressure": document.getElementById("bp").value,
    "Cholesterol": Number(document.getElementById("cholesterol").value),
    "Insulin": document.getElementById("insulin").value,
    "Diabetics": document.getElementById("diabetics").value,
    "air_quality_index": Number(document.getElementById("aqi").value),
    "social_event_count": Number(document.getElementById("events").value),
  };

  if (problem_type === "Diabetes") {
    payload["Hemoglobin (g/dL)"] = Number(document.getElementById("hb").value || 13.5);
    payload["WBC Count (10^9/L)"] = Number(document.getElementById("wbc").value || 7.0);
    payload["Platelet Count (10^9/L)"] = Number(document.getElementById("plt_count").value || 250);
    payload["Urine Protein (mg/dL)"] = Number(document.getElementById("urine_protein").value || 10);
    payload["Urine Glucose (mg/dL)"] = Number(document.getElementById("urine_glucose").value || 5);
  } else {
    payload["ECG Result"] = document.getElementById("ecg").value;
    payload["Pulse Rate (bpm)"] = Number(document.getElementById("pulse").value || 72);
  }

  return payload;
}

// ===== Render Prediction =====
function renderPredictionResult(data) {
  document.getElementById("out-disease").textContent = data.disease_type || "-";
  document.getElementById("out-prediction").textContent = data.prediction || "-";
  document.getElementById("out-score").textContent =
    data.readmission_probability !== undefined
      ? data.readmission_probability.toFixed(4)
      : "-";

  const riskLabel = data.risk_label || "-";
  document.getElementById("out-risk-label").textContent = riskLabel;

  // Update risk badge styling based on risk level
  const riskBadge = document.getElementById("risk-badge");
  riskBadge.className = "risk-badge"; // Reset classes

  if (riskLabel.toLowerCase().includes("high")) {
    riskBadge.classList.add("high-risk");
  } else if (riskLabel.toLowerCase().includes("medium")) {
    riskBadge.classList.add("medium-risk");
  } else if (riskLabel.toLowerCase().includes("low")) {
    riskBadge.classList.add("low-risk");
  }

  // Update follow-up plan
  if (data.followup_plan) {
    const f = data.followup_plan;
    document.getElementById("out-followup").innerHTML = `
      <strong><i class="fas fa-phone"></i> Contact Method:</strong> ${f.channel}<br>
      <strong><i class="fas fa-calendar"></i> Schedule:</strong> ${f.schedule.join(", ")}<br>
      <strong><i class="fas fa-info-circle"></i> Notes:</strong> ${f.note}
    `;
  }

  // Draw risk chart
  drawRiskChart(data.readmission_probability || 0, riskLabel);
}

// ===== Enhanced Risk Chart =====
function drawRiskChart(prob, riskLabel) {
  const ctx = document.getElementById("riskChart").getContext("2d");
  if (riskChart) riskChart.destroy();

  // Determine color based on risk level
  let color, borderColor;
  if (riskLabel.toLowerCase().includes("high")) {
    color = "rgba(250, 112, 154, 0.7)";
    borderColor = "rgba(250, 112, 154, 1)";
  } else if (riskLabel.toLowerCase().includes("medium")) {
    color = "rgba(251, 191, 36, 0.7)";
    borderColor = "rgba(251, 191, 36, 1)";
  } else {
    color = "rgba(52, 211, 153, 0.7)";
    borderColor = "rgba(52, 211, 153, 1)";
  }

  riskChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: ["Readmission Risk", "No Risk"],
      datasets: [{
        data: [prob * 100, (1 - prob) * 100],
        backgroundColor: [color, "rgba(226, 232, 240, 0.5)"],
        borderColor: [borderColor, "rgba(226, 232, 240, 1)"],
        borderWidth: 3
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            padding: 15,
            font: {
              size: 12,
              weight: '600'
            }
          }
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              return context.label + ': ' + context.parsed.toFixed(2) + '%';
            }
          }
        }
      }
    }
  });
}

// ===== Enhanced Staff Chart =====
function drawStaffChart(staffing) {
  const ctx = document.getElementById("staffChart").getContext("2d");
  if (staffChart) staffChart.destroy();
  if (!staffing) return;

  const gradient1 = ctx.createLinearGradient(0, 0, 0, 400);
  gradient1.addColorStop(0, 'rgba(102, 126, 234, 0.8)');
  gradient1.addColorStop(1, 'rgba(118, 75, 162, 0.8)');

  const gradient2 = ctx.createLinearGradient(0, 0, 0, 400);
  gradient2.addColorStop(0, 'rgba(79, 172, 254, 0.8)');
  gradient2.addColorStop(1, 'rgba(0, 242, 254, 0.8)');

  const gradient3 = ctx.createLinearGradient(0, 0, 0, 400);
  gradient3.addColorStop(0, 'rgba(240, 147, 251, 0.8)');
  gradient3.addColorStop(1, 'rgba(245, 87, 108, 0.8)');

  staffChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["Beds", "Nurses", "Doctors"],
      datasets: [{
        label: "Recommended Resources",
        data: [
          staffing.suggested_beds,
          staffing.suggested_nurses,
          staffing.suggested_doctors
        ],
        backgroundColor: [gradient1, gradient2, gradient3],
        borderColor: [
          'rgba(102, 126, 234, 1)',
          'rgba(79, 172, 254, 1)',
          'rgba(240, 147, 251, 1)'
        ],
        borderWidth: 2,
        borderRadius: 8
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          display: false
        },
        tooltip: {
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          padding: 12,
          cornerRadius: 8,
          titleFont: {
            size: 14,
            weight: 'bold'
          },
          bodyFont: {
            size: 13
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          grid: {
            color: 'rgba(0, 0, 0, 0.05)',
            drawBorder: false
          },
          ticks: {
            font: {
              size: 12,
              weight: '600'
            }
          }
        },
        x: {
          grid: {
            display: false
          },
          ticks: {
            font: {
              size: 12,
              weight: '600'
            }
          }
        }
      }
    }
  });
}

// ===== Utility Functions =====

function showLoading() {
  const overlay = document.getElementById("loading-overlay");
  overlay.classList.remove("hidden");
}

function hideLoading() {
  const overlay = document.getElementById("loading-overlay");
  overlay.classList.add("hidden");
}

function showError(message) {
  // Create toast notification
  const toast = document.createElement("div");
  toast.className = "toast toast-error";
  toast.innerHTML = `
    <i class="fas fa-exclamation-circle"></i>
    <span>${message}</span>
  `;
  toast.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
    color: white;
    padding: 1rem 1.5rem;
    border-radius: 12px;
    box-shadow: 0 10px 25px rgba(250, 112, 154, 0.3);
    z-index: 10000;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    font-weight: 600;
    animation: slideInRight 0.3s ease-out;
  `;

  document.body.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = "slideOutRight 0.3s ease-out";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

function showSuccess(message) {
  // Create toast notification
  const toast = document.createElement("div");
  toast.className = "toast toast-success";
  toast.innerHTML = `
    <i class="fas fa-check-circle"></i>
    <span>${message}</span>
  `;
  toast.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    color: white;
    padding: 1rem 1.5rem;
    border-radius: 12px;
    box-shadow: 0 10px 25px rgba(79, 172, 254, 0.3);
    z-index: 10000;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    font-weight: 600;
    animation: slideInRight 0.3s ease-out;
  `;

  document.body.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = "slideOutRight 0.3s ease-out";
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

function animateSection(element) {
  element.style.animation = "none";
  setTimeout(() => {
    element.style.animation = "scaleIn 0.4s ease-out";
  }, 10);
}

// Add CSS for toast animations
const style = document.createElement("style");
style.textContent = `
  @keyframes slideInRight {
    from {
      transform: translateX(400px);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }

  @keyframes slideOutRight {
    from {
      transform: translateX(0);
      opacity: 1;
    }
    to {
      transform: translateX(400px);
      opacity: 0;
    }
  }
`;
document.head.appendChild(style);
