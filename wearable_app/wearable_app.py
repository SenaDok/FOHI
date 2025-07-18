from flask import Flask, request, render_template, redirect, url_for, send_from_directory
import os
import io
import csv
import json
from datetime import datetime, timedelta
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

app = Flask(__name__)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# store uploaded data in memory for simplicity
all_data = []  # list of (timestamp, heartrate)


def parse_csv(file_stream):
    data = []
    reader = csv.reader(io.StringIO(file_stream.read().decode('utf-8')))
    for row in reader:
        if len(row) < 2:
            continue
        ts_str, hr_str = row[0].strip(), row[1].strip()
        if ts_str.lower() in ['timestamp', 'time', '']:
            continue
        if not ts_str:
            continue
        try:
            ts = datetime.fromisoformat(ts_str)
        except ValueError:
            try:
                ts = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                continue
        hr = None
        if hr_str:
            try:
                hr = float(hr_str)
            except ValueError:
                pass
        data.append((ts, hr))
    return data


def parse_json(file_stream):
    parsed = json.load(file_stream)
    data = []
    # expect list of objects with heartRateValues
    for entry in parsed:
        values = entry.get('heartRateValues') or []
        for ts_ms, hr in values:
            ts = datetime.utcfromtimestamp(ts_ms / 1000)
            if hr is not None:
                data.append((ts, float(hr)))
    return data


def load_file(file):
    filename = file.filename.lower()
    if filename.endswith('.csv'):
        return parse_csv(file.stream)
    elif filename.endswith('.json'):
        return parse_json(file.stream)
    else:
        raise ValueError('Unsupported file type')


def find_intervals(data):
    """Find all 2h intervals with exact 2min steps"""
    if not data:
        return []
    # sort by timestamp
    data.sort()
    intervals = []
    start_index = 0
    while start_index < len(data):
        start_ts = data[start_index][0]
        end_ts = start_ts + timedelta(hours=2)
        expected_ts = start_ts
        points = []
        idx = start_index
        while idx < len(data) and data[idx][0] <= end_ts:
            ts, hr = data[idx]
            if ts != expected_ts:
                break
            points.append((ts, hr))
            expected_ts = expected_ts + timedelta(minutes=2)
            idx += 1
        if expected_ts - timedelta(minutes=2) == end_ts:
            intervals.append(points)
            start_index = idx
        else:
            start_index += 1
    return intervals


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file:
            return 'No file provided', 400
        try:
            data = load_file(file)
        except Exception as e:
            return f'Error parsing file: {e}', 400
        global all_data
        all_data = data
        return redirect(url_for('data_page'))
    return render_template('upload.html')


@app.route('/data')
def data_page():
    intervals = find_intervals(all_data)
    return render_template('data.html', intervals=intervals)


def plot_interval(interval):
    timestamps = [ts for ts, _ in interval]
    values = [hr for _, hr in interval]
    fig = Figure()
    ax = fig.subplots()
    ax.plot(timestamps, values)
    ax.set_xlabel('Time')
    ax.set_ylabel('Heartrate')
    ax.set_title('Heartrate over time')
    buf = io.BytesIO()
    fig.autofmt_xdate()
    fig.savefig(buf, format='png')
    buf.seek(0)
    return buf


@app.route('/')
def index():
    intervals = find_intervals(all_data)
    if not intervals:
        return 'No valid 2h interval found. Upload data first via /upload.'
    latest = intervals[-1]
    values = [hr for _, hr in latest]
    minimum = min(values)
    maximum = max(values)
    average = sum(values) / len(values)
    plot_buf = plot_interval(latest)
    img_path = os.path.join(UPLOAD_FOLDER, 'plot.png')
    with open(img_path, 'wb') as f:
        f.write(plot_buf.read())
    return render_template('summary.html', minimum=minimum, maximum=maximum, average=average)


@app.route('/plot.png')
def plot_png():
    return send_from_directory(UPLOAD_FOLDER, 'plot.png')


if __name__ == '__main__':
    app.run(debug=True)
