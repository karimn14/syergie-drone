"""
report_generator.py
Automated PDF/HTML report generation after each mission.
"""
import pandas as pd
from fpdf import FPDF
import os

def generate_report(log_file='mission.log', output_file='mission_report.pdf'):
    if not os.path.exists(log_file):
        print(f"Log file {log_file} not found.")
        return
    df = pd.read_csv(log_file, sep=None, engine='python')
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'Drone Sawit Mission Report', 0, 1, 'C')
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 10, f'Log File: {log_file}', 0, 1)
    pdf.cell(0, 10, f'Total Events: {len(df)}', 0, 1)
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 10)
    for col in df.columns:
        pdf.cell(40, 8, col, 1)
    pdf.ln()
    pdf.set_font('Arial', '', 9)
    for _, row in df.iterrows():
        for item in row:
            pdf.cell(40, 8, str(item), 1)
        pdf.ln()
    pdf.output(output_file)
    print(f"Mission report saved to {output_file}")
