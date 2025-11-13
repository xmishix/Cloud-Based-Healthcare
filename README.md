# Multi-Disease Patient Readmission Prediction System

A machine learning-powered web application for predicting hospital readmission risk for patients with Diabetes and Heart Disease. This system provides clinical decision support through risk assessment, resource allocation recommendations, and automated follow-up care planning.

## Overview

This project uses Random Forest models to predict the likelihood of patient readmission within 30 days, combining ML predictions with clinical severity scoring to provide comprehensive risk assessments. The system generates professional PDF reports for physicians and includes staffing simulation capabilities for hospital resource planning.

## Features

- **Dual Disease Models**: Separate ML models for Diabetes and Heart Disease patients
- **Risk Stratification**: Three-tier risk classification (Low/Medium/High) with automated follow-up protocols
- **PDF Report Generation**: Professional clinical reports with patient details, risk assessment, and visualizations
- **Staffing Simulation**: Resource allocation recommendations (beds, nurses, doctors) based on predicted readmission risk
- **Follow-up Management**: Automated care planning with multiple communication channels (Phone, SMS, App, Portal)
- **Interactive Web Interface**: User-friendly form with dynamic disease-specific fields
- **Real-time Visualization**: Charts and graphs using Chart.js

## Technology Stack

### Backend
- **Framework**: Flask (Python)
- **ML Libraries**: scikit-learn, XGBoost
- **Data Processing**: pandas, numpy
- **Visualization**: matplotlib, seaborn
- **Report Generation**: ReportLab

### Frontend
- **HTML5** with responsive design
- **JavaScript** (vanilla JS)
- **CSS3** with UMKC branding
- **Chart.js** for data visualization

### Machine Learning
- **Algorithm**: Random Forest Classifier
- **Training**: Grid Search with cross-validation
- **Features**: 31 total (10 common + disease-specific)
- **Dataset**: 5,000 patient records

## Project Structure

```
Multi Disease Patient Readmission using ML/
├── backend/
│   ├── app.py                              # Main Flask application
│   ├── requirements.txt                    # Python dependencies
│   ├── readmission_diabetes_RandomForest.pkl      # Diabetes model (21MB)
│   ├── readmission_heart_disease_RandomForest.pkl # Heart Disease model (23MB)
│   ├── staffing_simulation_summary.csv     # Staffing data
│   ├── final_dataset_realistic.csv         # Dataset
│   └── frontend/
│       ├── index.html                      # Web interface
│       ├── script.js                       # Frontend logic
│       └── style.css                       # Styling
├── ML Model/
│   ├── Healthcare_ML_Model.ipynb           # Model training notebook
│   └── Output ML model/                    # Training results
├── data/
│   └── final_dataset_realistic.csv         # Original dataset
└── Outputs/                                # Sample reports and demos
```

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Setup Steps

1. **Clone the repository**
```bash
git clone <repository-url>
cd Multi-Disease-Patient-Readmission-Prediction-Using-ML-and-Cloud
```

2. **Navigate to the backend directory**
```bash
cd "Multi Disease Patient Readmission using ML/backend"
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

## Usage

### Running the Application

1. **Start the Flask server**
```bash
python app.py
```

2. **Access the web interface**
Open your browser and navigate to:
```
http://localhost:5000
```

The server runs on:
- Host: 0.0.0.0 (accessible from network)
- Port: 5000
- Debug: Disabled (production-ready)

### Using the Web Interface

1. **Select Disease Type**: Choose between Diabetes or Heart Disease
2. **Enter Patient Information**:
   - Demographics (Name, Age, Sex, Weight)
   - Clinical data (Blood Pressure, Cholesterol, Lab results)
   - Admission details (Date, Doctor, Hospital, etc.)
3. **Disease-Specific Fields**: Form dynamically shows relevant fields
4. **Submit Prediction**: View risk assessment, recommendations, and visualizations
5. **Generate Report**: Download professional PDF report for clinical records

## API Endpoints

### POST /api/predict
Predicts readmission risk for a patient.

**Request Body**: JSON with patient data
**Response**: Risk score, category, recommendations, follow-up schedule

### POST /api/simulate_staffing
Simulates resource allocation needs.

**Request Body**: Risk score, unit, date
**Response**: Recommended beds, nurses, doctors

### POST /api/report
Generates PDF clinical report.

**Request Body**: Patient data and prediction results
**Response**: PDF file download

### GET /api/followups
Retrieves pending follow-up appointments.

**Query Parameters**: unit (optional)
**Response**: List of scheduled follow-ups

### POST /api/followup/complete
Marks a follow-up as completed.

**Request Body**: Follow-up ID and completion notes
**Response**: Success confirmation

## Model Details

### Diabetes Model
- **Accuracy**: 64.66%
- **Features**: Age, Sex, Weight, Blood Pressure, Hemoglobin, WBC, Platelet Count, Urine Protein/Glucose, Environmental factors
- **File**: `readmission_diabetes_RandomForest.pkl`

### Heart Disease Model
- **Accuracy**: 66.20%
- **Features**: Age, Sex, Weight, Blood Pressure, Cholesterol, ECG Result, Pulse Rate, Platelets, Environmental factors
- **File**: `readmission_heart_disease_RandomForest.pkl`

### Risk Scoring
Final risk score combines:
- ML model probability (40% weight)
- Clinical severity score (60% weight)

Risk categories:
- **Low**: < 0.40
- **Medium**: 0.40 - 0.70
- **High**: > 0.70

## Dataset

The system uses a synthetic dataset with 5,000 patient records containing:
- **Demographics**: Age, Sex, Weight
- **Clinical Data**: Blood Pressure, Cholesterol, Lab Results
- **Disease-Specific**: Hemoglobin, ECG Results, Glucose levels
- **Environmental**: Weather, Air Quality, Social Events
- **Administrative**: Admission/Discharge dates, Doctor information
- **Target**: Binary readmission (Yes/No)

Location: `data/final_dataset_realistic.csv`

## Development

### Training New Models

To retrain the ML models:

1. Open the Jupyter notebook:
```bash
cd "Multi Disease Patient Readmission using ML/ML Model"
jupyter notebook Healthcare_ML_Model.ipynb
```

2. Run all cells to:
   - Load and preprocess data
   - Train Random Forest models with Grid Search
   - Evaluate performance (ROC curves, metrics)
   - Save models as .pkl files

3. Copy trained models to backend:
```bash
cp *.pkl ../backend/
```

### Model Training Outputs
- `training_summary.json`: Performance metrics
- `roc_curve.png`: ROC curve visualization
- `pr_curve.png`: Precision-Recall curve
- `feature_coefficients.csv`: Feature importance

## Configuration

### Environment Variables
The application uses default settings. For production deployment, consider:
- Setting `FLASK_ENV=production`
- Configuring `SECRET_KEY` for sessions
- Setting up proper CORS restrictions
- Using environment-specific configuration files

### CORS Configuration
Currently allows all origins (`*`). For production:
```python
CORS(app, resources={r"/api/*": {"origins": "https://yourdomain.com"}})
```

## AWS Deployment

This application is ready for AWS deployment with multiple options:

### Quick Deployment (Recommended)

**One-command deployment with Elastic Beanstalk:**
```bash
cd "Multi Disease Patient Readmission using ML/backend"
./deploy.sh
```

See **[QUICK_START_AWS.md](QUICK_START_AWS.md)** for step-by-step instructions.

### Deployment Options

| Method | Setup | Monthly Cost | Update Method | Guide |
|--------|-------|--------------|---------------|-------|
| **Elastic Beanstalk** ⭐ | 5 min | $33-78 | `eb deploy` | [Full Guide](AWS_DEPLOYMENT_GUIDE.md#option-1-aws-elastic-beanstalk) |
| **App Runner** 🚀 | 3 min | $5-50 | Git push | [Full Guide](AWS_DEPLOYMENT_GUIDE.md#option-2-aws-app-runner) |
| **ECS Fargate** ⚙️ | 30 min | $138+ | Docker push | [Full Guide](AWS_DEPLOYMENT_GUIDE.md#option-3-ecs-fargate) |
| **EC2 Auto Scaling** | 20 min | $48+ | CodeDeploy | [Full Guide](AWS_DEPLOYMENT_GUIDE.md#option-4-ec2-with-auto-scaling) |

### Easy Updates

**Elastic Beanstalk:**
```bash
# Make changes, then:
eb deploy
```

**App Runner (auto-deploy):**
```bash
git push origin main  # Automatically deploys
```

### Files Included for AWS Deployment

- `Dockerfile` - Container configuration
- `Procfile` - Process configuration
- `.ebextensions/python.config` - Elastic Beanstalk settings
- `deploy.sh` - One-command deployment script
- `requirements.txt` - Includes gunicorn for production

For complete deployment instructions, cost estimates, and best practices, see:
- **Quick Start**: [QUICK_START_AWS.md](QUICK_START_AWS.md)
- **Complete Guide**: [AWS_DEPLOYMENT_GUIDE.md](AWS_DEPLOYMENT_GUIDE.md)

## Security Considerations

**Current Implementation** (Development/Demo):
- CORS enabled without restrictions
- No authentication/authorization
- CSV-based follow-up storage
- No input validation/sanitization

**Production Recommendations**:
- Implement user authentication (OAuth2, JWT)
- Add API rate limiting
- Use proper database (PostgreSQL/MongoDB)
- Enable HTTPS/TLS
- Implement input validation and sanitization
- Add audit logging
- Restrict CORS to specific domains
- Follow HIPAA compliance guidelines for patient data

## Known Limitations

1. **Model Performance**: Accuracy ~64-66% (below clinical standard of 80%)
2. **Data Storage**: CSV files instead of database (not scalable)
3. **No Authentication**: Open API access (not production-ready)
4. **Missing Logo**: UMKC logo referenced but not included (gracefully handled)
5. **Static Staffing Data**: Uses historical CSV, not real-time data

## Future Enhancements

- Improve model accuracy through feature engineering and ensemble methods
- Implement database backend (PostgreSQL with SQLAlchemy)
- Add user authentication and role-based access control
- ✅ ~~Create Docker containers for easy deployment~~ (Completed)
- ✅ ~~Add cloud deployment scripts (AWS/Azure/GCP)~~ (AWS Completed)
- Implement real-time staffing integration
- Add automated testing (unit, integration, end-to-end)
- Create API documentation (Swagger/OpenAPI)
- Add model monitoring and retraining pipeline
- Implement A/B testing for model comparison
- Migrate to Azure/GCP deployment options

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/improvement`)
3. Commit changes (`git commit -am 'Add new feature'`)
4. Push to branch (`git push origin feature/improvement`)
5. Open a Pull Request

## License

This project is for educational and research purposes.

## Contact

For questions or support, please open an issue in the GitHub repository.

## Acknowledgments

- UMKC Hospital Analytics (branding)
- scikit-learn and Flask communities
- Healthcare data science research community
