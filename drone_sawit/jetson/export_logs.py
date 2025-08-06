"""
export_logs.py
Exports mission logs to CSV and PDF using pandas and fpdf2.
"""

import pandas as pd
from fpdf import FPDF
import os
from log_utils import setup_logger

def export_logs(format='csv', log_file='mission.log', output_file=None, archived=False):
    # Optionally export from archived logs
    if archived:
        log_dir = os.path.dirname(log_file)
        logs = [f for f in os.listdir(log_dir) if f.startswith('mission.log')]
        for lf in logs:
            export_logs(format, os.path.join(log_dir, lf), output_file=None)
        return
    if not os.path.exists(log_file):
        print(f"Log file {log_file} not found.")
        return
    df = pd.read_csv(log_file, sep=None, engine='python')
    if not output_file:
        output_file = log_file.replace('.log', f'.{format}')
    if format == 'csv':
        df.to_csv(output_file, index=False)
        print(f"Exported logs to {output_file}")
    elif format == 'pdf':
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Arial', 'B', 12)
        for col in df.columns:
            pdf.cell(40, 10, col, 1)
        pdf.ln()
        pdf.set_font('Arial', '', 10)
        for _, row in df.iterrows():
            for item in row:
                pdf.cell(40, 10, str(item), 1)
            pdf.ln()
        pdf.output(output_file)
        print(f"Exported logs to {output_file}")
    else:
        print("Unsupported format. Use 'csv' or 'pdf'.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        export_logs('csv')
    else:
        format = sys.argv[1]
        log_file = sys.argv[2] if len(sys.argv) > 2 else 'mission.log'
        output_file = sys.argv[3] if len(sys.argv) > 3 else None
        archived = '--archived' in sys.argv
        export_logs(format, log_file, output_file, archived)
