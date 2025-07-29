#!/usr/bin/env python3
"""
簡易ダッシュボード - WebSocket問題の緊急回避版
MT5データを直接JSON APIで提供
"""

import json
import time
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, jsonify

app = Flask(__name__)

def read_mt5_data():
    """MT5データ読み込み"""
    try:
        data_file = Path("/tmp/mt5_data/positions.json")
        if data_file.exists():
            with open(data_file, 'r') as f:
                return json.load(f)
        return None
    except Exception as e:
        print(f"データ読み込みエラー: {e}")
        return None

@app.route('/')
def dashboard():
    """メインダッシュボード"""
    return '''
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JamesORB Trading Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #1e1e1e;
            color: #ffffff;
            padding: 20px;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            color: #4CAF50;
            margin-bottom: 10px;
        }
        .status {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 15px;
            font-size: 14px;
            font-weight: bold;
            background-color: #4CAF50;
            color: white;
        }
        .account-summary {
            background-color: #2d2d2d;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 30px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }
        .metric {
            text-align: center;
        }
        .metric h3 {
            color: #888;
            font-size: 14px;
            margin-bottom: 10px;
        }
        .metric .value {
            font-size: 24px;
            font-weight: bold;
        }
        .profit { color: #4CAF50; }
        .loss { color: #f44336; }
        .positions-table {
            background-color: #2d2d2d;
            border-radius: 10px;
            padding: 20px;
            overflow-x: auto;
        }
        .positions-table h2 {
            color: #4CAF50;
            margin-bottom: 20px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #444;
        }
        th {
            color: #4CAF50;
            font-weight: bold;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            color: #888;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>JamesORB Trading Dashboard</h1>
        <span class="status">稼働中</span>
    </div>

    <div class="account-summary">
        <div class="metric">
            <h3>残高</h3>
            <div class="value" id="balance">---</div>
        </div>
        <div class="metric">
            <h3>有効証拠金</h3>
            <div class="value" id="equity">---</div>
        </div>
        <div class="metric">
            <h3>合計損益</h3>
            <div class="value" id="profit">---</div>
        </div>
    </div>

    <div class="positions-table">
        <h2>オープンポジション</h2>
        <table>
            <thead>
                <tr>
                    <th>通貨ペア</th>
                    <th>タイプ</th>
                    <th>ロット</th>
                    <th>損益</th>
                    <th>オープン価格</th>
                    <th>現在価格</th>
                    <th>オープン時刻</th>
                </tr>
            </thead>
            <tbody id="positions-tbody">
                <tr><td colspan="7">データを読み込み中...</td></tr>
            </tbody>
        </table>
    </div>

    <div class="footer">
        最終更新: <span id="last-update">---</span>
    </div>

    <script>
        function updateData() {
            fetch('/api/data')
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        console.error('API Error:', data.error);
                        return;
                    }
                    
                    // 口座情報更新
                    document.getElementById('balance').textContent = '$' + data.account.balance.toLocaleString();
                    document.getElementById('equity').textContent = '$' + data.account.equity.toLocaleString();
                    
                    const profit = data.account.profit;
                    const profitElement = document.getElementById('profit');
                    profitElement.textContent = '$' + profit.toLocaleString();
                    profitElement.className = 'value ' + (profit >= 0 ? 'profit' : 'loss');
                    
                    // ポジション更新
                    const tbody = document.getElementById('positions-tbody');
                    if (data.positions.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="7">ポジションなし</td></tr>';
                    } else {
                        tbody.innerHTML = data.positions.map(pos => `
                            <tr>
                                <td>${pos.symbol}</td>
                                <td>${pos.type.toUpperCase()}</td>
                                <td>${pos.volume}</td>
                                <td class="${pos.profit >= 0 ? 'profit' : 'loss'}">$${pos.profit.toFixed(2)}</td>
                                <td>${pos.open_price}</td>
                                <td>${pos.current_price}</td>
                                <td>${pos.open_time ? pos.open_time.substring(11, 19) : '---'}</td>
                            </tr>
                        `).join('');
                    }
                    
                    // 最終更新時刻
                    document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
                })
                .catch(error => {
                    console.error('Fetch error:', error);
                });
        }
        
        // 初回ロード
        updateData();
        
        // 5秒ごとに更新
        setInterval(updateData, 5000);
    </script>
</body>
</html>
    '''

@app.route('/api/data')
def api_data():
    """MT5データAPI"""
    data = read_mt5_data()
    if data:
        return jsonify(data)
    else:
        return jsonify({"error": "MT5データ読み込み失敗"})

if __name__ == '__main__':
    print("=== 簡易JamesORBダッシュボード ===")
    print("URL: http://localhost:5000")
    print("WebSocket不使用・JSON API方式")
    app.run(host='0.0.0.0', port=5000, debug=False)