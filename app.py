"""
app.py - Flask сервер для системы подбора матчей
===================================================
ИСПРАВЛЕННАЯ ВЕРСИЯ БЕЗ ЗАВИСАНИЙ
"""

from flask import Flask, render_template_string, jsonify, request
from flask_cors import CORS
import json
import sys
import os

# Импортируем нашу модель
sys.path.insert(0, os.path.dirname(__file__))
from matchmaking_system import run_experiments

app = Flask(__name__)
CORS(app)

# Встроенные пресеты
PRESETS = {
    'low_load': {
        'name': 'Low Load (Низкая нагрузка)',
        'lambda_rate': 0.5,
        'sim_time': 120.0,
        'max_queue': 50,
        'max_wait_time': 60.0,
        'servers_eu': 2,
        'servers_na': 2,
        'servers_as': 2,
        'match_size': 10,
        'service_time': 20.0,
        'mmr_spread_max': 500,
        'runs': 10,
        'scenario_name': 'Low Load'
    },
    'balanced': {
        'name': 'Balanced (Сбалансированная)',
        'lambda_rate': 1.0,
        'sim_time': 120.0,
        'max_queue': 100,
        'max_wait_time': 60.0,
        'servers_eu': 3,
        'servers_na': 3,
        'servers_as': 3,
        'match_size': 10,
        'service_time': 20.0,
        'mmr_spread_max': 500,
        'runs': 10,
        'scenario_name': 'Balanced'
    },
    'high_load': {
        'name': 'High Load (Высокая нагрузка)',
        'lambda_rate': 2.0,
        'sim_time': 120.0,
        'max_queue': 150,
        'max_wait_time': 60.0,
        'servers_eu': 4,
        'servers_na': 4,
        'servers_as': 4,
        'match_size': 10,
        'service_time': 20.0,
        'mmr_spread_max': 500,
        'runs': 10,
        'scenario_name': 'High Load'
    }
}

@app.route('/')
def index():
    """Возвращает index.html"""
    return render_template_string(open('index.html', 'r', encoding='utf-8').read())

@app.route('/api/info')
def get_info():
    """Информация о приложении"""
    return jsonify({
        'name': 'Система подбора матчей',
        'version': '1.0',
        'description': 'Моделирование онлайн игровой системы',
        'institution': 'МГТУ им. Баумана',
        'course': 'Имитационное моделирование',
        'year': 2024
    })

@app.route('/api/presets', methods=['GET'])
def get_presets():
    """Возвращает доступные пресеты"""
    return jsonify({
        'presets': {
            'low_load': PRESETS['low_load'],
            'balanced': PRESETS['balanced'],
            'high_load': PRESETS['high_load']
        }
    })

@app.route('/api/simulate', methods=['POST'])
def simulate():
    """Запускаем моделирование"""
    try:
        data = request.json
        
        # Валидация параметров
        lambda_rate = float(data.get('lambda_rate', 1.0))
        if lambda_rate < 0.1 or lambda_rate > 10.0:
            return jsonify({'error': 'lambda_rate должен быть 0.1-10'}), 400
        
        sim_time = float(data.get('sim_time', 120.0))
        if sim_time < 10 or sim_time > 1440:
            return jsonify({'error': 'sim_time должен быть 10-1440 минут'}), 400
        
        max_queue = int(data.get('max_queue', 100))
        if max_queue < 10 or max_queue > 1000:
            return jsonify({'error': 'max_queue должен быть 10-1000'}), 400
        
        max_wait_time = float(data.get('max_wait_time', 60.0))
        if max_wait_time < 10 or max_wait_time > 600:
            return jsonify({'error': 'max_wait_time должен быть 10-600 сек'}), 400
        
        servers_eu = int(data.get('servers_eu', 3))
        servers_na = int(data.get('servers_na', 3))
        servers_as = int(data.get('servers_as', 3))
        if servers_eu < 1 or servers_eu > 20 or servers_na < 1 or servers_na > 20 or servers_as < 1 or servers_as > 20:
            return jsonify({'error': 'Серверы должны быть 1-20 на регион'}), 400
        
        match_size = int(data.get('match_size', 10))
        if match_size < 2 or match_size > 100:
            return jsonify({'error': 'match_size должен быть 2-100'}), 400
        
        service_time = float(data.get('service_time', 20.0))
        if service_time < 5 or service_time > 180:
            return jsonify({'error': 'service_time должен быть 5-180 минут'}), 400
        
        mmr_spread_max = int(data.get('mmr_spread_max', 500))
        if mmr_spread_max < 50 or mmr_spread_max > 2000:
            return jsonify({'error': 'mmr_spread_max должен быть 50-2000'}), 400
        
        runs = int(data.get('runs', 10))
        if runs < 1 or runs > 100:
            return jsonify({'error': 'runs должен быть 1-100'}), 400
        
        scenario_name = str(data.get('scenario_name', 'Custom'))
        
        # Подготавливаем параметры
        params = {
            'lambda_rate': lambda_rate,
            'sim_time': sim_time,
            'max_queue': max_queue,
            'max_wait_time': max_wait_time,
            'servers_eu': servers_eu,
            'servers_na': servers_na,
            'servers_as': servers_as,
            'match_size': match_size,
            'service_time': service_time,
            'mmr_spread_max': mmr_spread_max,
            'runs': runs,
            'scenario_name': scenario_name
        }
        
        print(f"\n▶ Начало моделирования: {scenario_name}")
        print(f"  λ={lambda_rate}, T={sim_time}мин, Serv_EU={servers_eu}, Serv_NA={servers_na}, Serv_AS={servers_as}")
        
        # Запускаем моделирование
        result = run_experiments(params)
        
        print(f"  ✓ Завершено! Ожидание: {result['aggregates']['avg_wait_time']}сек, Отказы: {result['aggregates']['rejection_rate_avg']}%")
        
        return jsonify(result), 200
        
    except Exception as e:
        error_msg = f"Ошибка при моделировании: {str(e)}"
        print(f"❌ {error_msg}")
        return jsonify({'error': error_msg}), 500

@app.route('/api/download_csv', methods=['POST'])
def download_csv():
    """Генерируем CSV для скачивания"""
    try:
        data = request.json
        experiments = data.get('experiments', [])
        aggregates = data.get('aggregates', {})
        scenario = data.get('scenario', 'results')
        
        csv_content = "Сценарий,Прогон,Прибыло,Обслужено,Отказов,% Отказа,Матчей,Ожидание (сек),Загрузка (%),MMR Разброс\n"
        
        for exp in experiments:
            csv_content += f"{scenario},{exp['run']},{exp['arrived']},{exp['matched']},{exp['rejected']},{exp['rejection_rate']},{exp['matches_formed']},{exp['avg_wait_time']},{exp['avg_server_util']},{exp['avg_mmr_diff']}\n"
        
        # Добавляем среднее
        csv_content += f"\nСРЕДНЕЕ ПО СЦЕНАРИЮ:\n"
        csv_content += f"Ожидание (сек),{aggregates.get('avg_wait_time', 0)}\n"
        csv_content += f"Отказы (%),{aggregates.get('rejection_rate_avg', 0)}\n"
        csv_content += f"Загрузка (%),{aggregates.get('avg_server_util', 0)}\n"
        csv_content += f"Матчей,{aggregates.get('matches_formed_avg', 0)}\n"
        csv_content += f"Прибыло,{aggregates.get('arrived_avg', 0)}\n"
        csv_content += f"Обслужено,{aggregates.get('matched_avg', 0)}\n"
        
        return csv_content, 200, {'Content-Disposition': f'attachment; filename=matchmaking_{scenario}.csv'}
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("\n" + "="*80)
    print("FLASK СЕРВЕР - СИСТЕМА ПОДБОРА МАТЧЕЙ")
    print("="*80)
    print("\n✓ Сервер запускается на http://127.0.0.1:5000")
    print("✓ API доступен по адресам:")
    print("  - POST  /api/simulate      - запуск моделирования")
    print("  - GET   /api/presets       - получить доступные пресеты")
    print("  - POST  /api/download_csv  - скачать результаты в CSV")
    print("  - GET   /api/info          - информация о приложении")
    print("\n💡 Откройте браузер: http://127.0.0.1:5000")
    print("="*80 + "\n")
    
    app.run(debug=True, host='127.0.0.1', port=5000)
