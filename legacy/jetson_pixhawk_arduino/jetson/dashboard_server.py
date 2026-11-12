# dashboard_server.py – Simple Flask dashboard for mission monitoring
from flask import Flask, render_template_string, jsonify
import pandas as pd
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template_string("""
    <h2>Drone Sawit Dashboard</h2>
    <ul>
        <li><a href='/coverage'>Spray Coverage</a></li>
        <li><a href='/log'>Log Output</a></li>
    </ul>
    """)

@app.route('/coverage')
def coverage():
    if not os.path.exists('spray_log.csv'):
        return 'No spray log found.'
    df = pd.read_csv('spray_log.csv')
    return df.to_html()

@app.route('/log')
def log():
    if not os.path.exists('drone_sawit.log'):
        return 'No log file found.'
    with open('drone_sawit.log') as f:
        lines = f.readlines()[-100:]
    return '<pre>' + ''.join(lines) + '</pre>'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
