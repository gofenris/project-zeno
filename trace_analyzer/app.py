from flask import Flask, render_template, jsonify, request
from datetime import datetime, timedelta
import os
from pathlib import Path

from trace_fetcher import TraceFetcher
from trace_analyzer import TraceAnalyzer
from config import Config

app = Flask(__name__)
config = Config()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/fetch_traces', methods=['POST'])
def fetch_traces():
    """Fetch traces for the last N days"""
    data = request.get_json()
    days = data.get('days', 5)
    environment = data.get('environment', 'default')
    
    fetcher = TraceFetcher(config)
    try:
        results = fetcher.fetch_last_n_days(days, environment)
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/analysis/<analysis_type>')
def get_analysis(analysis_type):
    """Get pre-computed analysis results"""
    analyzer = TraceAnalyzer(config)
    
    try:
        if analysis_type == 'basic_summary':
            result = analyzer.get_basic_summary()
        elif analysis_type == 'datasets':
            result = analyzer.get_dataset_analysis()
        elif analysis_type == 'tools':
            result = analyzer.get_tool_analysis()
        else:
            return jsonify({'error': 'Unknown analysis type'})
            
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
