# Data Analysis Application for Multiple Domains

A multi-domain Data Analysis Application built using FastAPI, Streamlit, and Groq LLM.
Designed to analyze Excel files from Retail, Manufacturing, and Education domains (generated using your multi-domain CSV generator).
The system automatically provides:
1. Data preview (for the first 20 rows of a selected sheet)
2. Statistical summaries
3. Visualizations using basic logic
4. AI-generated visualizations using Llama-3.1-8b-instant via Groq API
5. Session-based workflow

## Project Workflow
### Upload Excel File
User uploads an Excel file (.xlsx/.xls) for one of the three domains:
- Retail
- Manufacturing
- Education
The backend saves the file, extracts sheet names, creates a session ID and determines the domain type.

### Preview Sheets
For each sheet:
- First 20 rows are shown
- DataFrame displayed in Streamlit

### Statistical Summary
Backend calculates:
- Column data types
- Summary (min, max, mean…)
- Missing values table
- Unique counts
- Category frequencies

### Manual Visualizations
Basic logic generates default charts such as:
- Histogram
- Bar charts
- Line plots
- Scatter
For all sheets at once.

### AI-Generated Visualizations (Groq LLM)
Using llama-3.1-8b-instant
The AI analyzes:
- Sheet columns
- Data types
- Patterns
And returns:
- Suggested chart type
- X/Y mappings
- Description
- Base64-encoded rendered chart image

## Installation & Setup
1. Clone the repository
   git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
   cd DATA_ANALYSIS_APP
2. Create & activate a virtual environment
3. Install dependencies
   pip install -r requirements.txt
4. Run the code
   bash run_app.sh
