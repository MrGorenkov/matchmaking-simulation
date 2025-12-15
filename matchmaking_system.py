"""
matchmaking_system.py (ИСПРАВЛЕННАЯ ВЕРСИЯ)
=============================================
ПОЛНАЯ МОДЕЛЬ СИСТЕМЫ ПОДБОРА МАТЧЕЙ - БЕЗ ЗАВИСАНИЙ
Оптимизирована для быстрого выполнения
"""

import random
import numpy as np
from typing import Dict, List
import csv

class Player:
    """Игрок в системе"""
    def __init__(self, player_id: int, arrival_time: float, region: str, mmr: int):
        self.player_id = player_id
        self.arrival_time = arrival_time
        self.region = region  # EU, NA, AS
        self.mmr = mmr  # 800-3000
        self.matched_time = None
        self.wait_time = 0

class Match:
    """Матч на сервере"""
    def __init__(self, match_id: int, server_id: int, match_size: int, start_time: float, service_time: float):
        self.match_id = match_id
        self.server_id = server_id
        self.players: List[Player] = []
        self.match_size = match_size
        self.start_time = start_time
        self.end_time = start_time + service_time
        self.mmr_spread = 0

    def add_player(self, player: Player):
        if len(self.players) < self.match_size:
            self.players.append(player)
            player.matched_time = self.start_time
            player.wait_time = max(0, self.start_time - player.arrival_time)

    def is_full(self) -> bool:
        return len(self.players) == self.match_size

    def finalize(self):
        if len(self.players) > 0:
            mmrs = [p.mmr for p in self.players]
            self.mmr_spread = max(mmrs) - min(mmrs)

class Server:
    """Игровой сервер по регионам"""
    def __init__(self, server_id: int, region: str, capacity: int = 50):
        self.server_id = server_id
        self.region = region
        self.capacity = capacity
        self.active_matches: List[Match] = []
        self.completed_matches: List[Match] = []

    def get_active_slots(self) -> int:
        return sum(len(m.players) for m in self.active_matches)

    def can_host_match(self) -> bool:
        return len(self.active_matches) < 100

    def utilization(self) -> float:
        if self.capacity == 0:
            return 0
        active_slots = self.get_active_slots()
        return min(100, (active_slots / self.capacity) * 100)

class MatchmakingSystem:
    """Основная система подбора матчей"""
    def __init__(self, params: Dict):
        self.lambda_rate = float(params.get('lambda_rate', 1.0))
        self.sim_time = float(params.get('sim_time', 120.0)) * 60  # в секунды
        self.max_queue = int(params.get('max_queue', 100))
        self.max_wait_time = float(params.get('max_wait_time', 60.0))
        self.match_size = int(params.get('match_size', 10))
        self.service_time = float(params.get('service_time', 20.0))  # Хранится в секундах!
        self.mmr_spread_max = int(params.get('mmr_spread_max', 500))

        # Инициализация серверов
        self.servers_eu = [Server(i, 'EU') for i in range(int(params.get('servers_eu', 3)))]
        self.servers_na = [Server(i+100, 'NA') for i in range(int(params.get('servers_na', 3)))]
        self.servers_as = [Server(i+200, 'AS') for i in range(int(params.get('servers_as', 3)))]
        self.all_servers = self.servers_eu + self.servers_na + self.servers_as

        # Очередь и статистика
        self.queue = []
        self.rejected_players = []
        self.matched_players = []
        self.player_counter = 0
        self.match_counter = 0
        self.stats = {
            'arrived': 0,
            'matched': 0,
            'rejected': 0,
            'matches_formed': 0,
            'total_wait_time': 0.0,
            'total_mmr_diff': 0.0
        }

    def run_simulation(self) -> Dict:
        """Запускаем симуляцию быстро и эффективно"""
        current_time = 0.0
        next_arrival_time = np.random.exponential(1.0 / self.lambda_rate)

        while current_time < self.sim_time:
            # Генерируем прибытия
            while next_arrival_time <= current_time and current_time < self.sim_time:
                region = random.choice(['EU', 'NA', 'AS'])
                mmr = random.randint(800, 3000)
                self.player_counter += 1
                player = Player(self.player_counter, current_time, region, mmr)
                self.stats['arrived'] += 1

                # Добавляем в очередь или отказываем
                if len(self.queue) < self.max_queue:
                    self.queue.append(player)
                else:
                    self.rejected_players.append(player)
                    self.stats['rejected'] += 1

                next_arrival_time += np.random.exponential(1.0 / self.lambda_rate)

            # Пытаемся создать матчи
            self._try_match_players(current_time)

            # Завершаем матчи
            self._complete_matches(current_time)

            # Отказываем по timeout
            self._timeout_players(current_time)

            # Переходим на следующий момент
            time_step = min(1.0, max(1.0, next_arrival_time - current_time) if next_arrival_time > current_time else 1.0)
            current_time += time_step

        # Завершаем оставшиеся матчи
        while any(s.active_matches for s in self.all_servers):
            current_time += 1
            self._complete_matches(current_time)

        return self._calculate_metrics()

    def _try_match_players(self, current_time: float):
        """Пытаемся найти матчи для игроков в очереди"""
        while len(self.queue) >= self.match_size:
            available_server = self._find_available_server()
            if available_server is None:
                break

            # Берем игроков из очереди
            selected = []
            temp_queue = self.queue.copy()

            if temp_queue:
                selected.append(temp_queue[0])
                self.queue.pop(0)

                for i in range(1, len(temp_queue)):
                    if len(selected) >= self.match_size:
                        break

                    candidate = temp_queue[i]
                    mmr_diff = abs(selected[0].mmr - candidate.mmr)

                    if mmr_diff <= self.mmr_spread_max:
                        selected.append(candidate)
                        self.queue.remove(candidate)

            if len(selected) == self.match_size:
                # Создаем матч
                self.match_counter += 1
                match = Match(
                    self.match_counter,
                    available_server.server_id,
                    self.match_size,
                    current_time,
                    self.service_time
                )

                for player in selected:
                    match.add_player(player)
                    self.matched_players.append(player)
                    self.stats['matched'] += 1
                    self.stats['total_wait_time'] += player.wait_time

                match.finalize()
                available_server.active_matches.append(match)
                self.stats['matches_formed'] += 1
                self.stats['total_mmr_diff'] += match.mmr_spread
            else:
                break

    def _find_available_server(self) -> Server:
        """Ищем доступный сервер"""
        for server in self.all_servers:
            if server.can_host_match():
                return server
        return None

    def _complete_matches(self, current_time: float):
        """Завершаем матчи по времени"""
        for server in self.all_servers:
            completed = [m for m in server.active_matches if m.end_time <= current_time]
            for match in completed:
                server.active_matches.remove(match)
                server.completed_matches.append(match)

    def _timeout_players(self, current_time: float):
        """Отказываем игрокам, слишком долго ждущим"""
        new_queue = []
        for player in self.queue:
            wait = current_time - player.arrival_time
            if wait > self.max_wait_time:
                self.rejected_players.append(player)
                self.stats['rejected'] += 1
            else:
                new_queue.append(player)
        self.queue = new_queue

    def _calculate_metrics(self) -> Dict:
        """
        🔧 ИСПРАВЛЕННЫЙ РАСЧЁТ МЕТРИК
        
        Загруженность (ρ) = (λ × T_service) / (C × 60)
        Где:
          λ = интенсивность (игроков в минуту)
          T_service = время матча (СЕКУНДЫ)
          C = количество серверов
          60 = конвертация в минуты
        """
        arrived = self.stats['arrived']
        matched = self.stats['matched']
        rejected = self.stats['rejected']
        matches = self.stats['matches_formed']
        
        rejection_rate = (rejected / arrived * 100) if arrived > 0 else 0.0
        avg_wait = (self.stats['total_wait_time'] / matched) if matched > 0 else 0.0
        
        # ✅ ПРАВИЛЬНЫЙ РАСЧЁТ ЗАГРУЖЕННОСТИ
        total_servers = len(self.all_servers)
        if total_servers > 0:
            # ρ = (λ игроков/мин × T_service сек) / (C серверов × 60 сек/мин)
            rho = (self.lambda_rate * self.service_time) / (total_servers * 60.0)
            avg_util = min(100.0, rho * 100.0)  # Конвертируем в проценты
        else:
            avg_util = 0.0
        
        avg_mmr_diff = (self.stats['total_mmr_diff'] / matches) if matches > 0 else 0.0

        return {
            'arrived': arrived,
            'matched': matched,
            'rejected': rejected,
            'rejection_rate': round(rejection_rate, 2),
            'matches_formed': matches,
            'avg_wait_time': round(avg_wait, 2),
            'avg_server_util': round(avg_util, 1),  # Теперь корректно!
            'avg_mmr_diff': round(avg_mmr_diff, 2)
        }


def run_experiments(params: Dict) -> Dict:
    """
    Запускаем серию экспериментов
    """
    runs = int(params.get('runs', 10))
    scenario_name = str(params.get('scenario_name', 'Custom'))

    experiments = []

    for run_num in range(1, runs + 1):
        system = MatchmakingSystem(params)
        metrics = system.run_simulation()

        experiment = {
            'run': run_num,
            'arrived': metrics['arrived'],
            'matched': metrics['matched'],
            'rejected': metrics['rejected'],
            'rejection_rate': metrics['rejection_rate'],
            'matches_formed': metrics['matches_formed'],
            'avg_wait_time': metrics['avg_wait_time'],
            'avg_server_util': metrics['avg_server_util'],
            'avg_mmr_diff': metrics['avg_mmr_diff']
        }

        experiments.append(experiment)

    # Агрегированные метрики
    aggregates = {
        'arrived_avg': round(np.mean([e['arrived'] for e in experiments]), 2),
        'matched_avg': round(np.mean([e['matched'] for e in experiments]), 2),
        'rejected_avg': round(np.mean([e['rejected'] for e in experiments]), 2),
        'rejection_rate_avg': round(np.mean([e['rejection_rate'] for e in experiments]), 2),
        'matches_formed_avg': round(np.mean([e['matches_formed'] for e in experiments]), 2),
        'avg_wait_time': round(np.mean([e['avg_wait_time'] for e in experiments]), 2),
        'avg_server_util': round(np.mean([e['avg_server_util'] for e in experiments]), 1),  # Теперь корректно!
        'avg_mmr_diff': round(np.mean([e['avg_mmr_diff'] for e in experiments]), 2)
    }

    return {
        'scenario': scenario_name,
        'runs': runs,
        'params': params,
        'experiments': experiments,
        'aggregates': aggregates
    }


if __name__ == '__main__':
    scenarios = {
        'Low Load': {
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
        'Balanced': {
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
        'High Load': {
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

    print("=" * 80)
    print("МОДЕЛИРОВАНИЕ СИСТЕМЫ ПОДБОРА МАТЧЕЙ")
    print("=" * 80)

    all_results = []

    for scenario_name, params in scenarios.items():
        print(f"\n▶ {scenario_name}...", end='', flush=True)
        result = run_experiments(params)
        all_results.append(result)
        print(f" ✓ (Ожидание: {result['aggregates']['avg_wait_time']}сек, Загрузка: {result['aggregates']['avg_server_util']}%)")

    print("\n💾 Сохраняю результаты...")

    with open('matchmaking_results_full.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Сценарий', 'Прогон', 'Прибыло', 'Обслужено', 'Отказов', '% Отказа',
                        'Матчей', 'Ожидание (сек)', 'Загрузка (%)', 'MMR Разброс'])

        for result in all_results:
            for exp in result['experiments']:
                writer.writerow([
                    result['scenario'],
                    exp['run'],
                    exp['arrived'],
                    exp['matched'],
                    exp['rejected'],
                    exp['rejection_rate'],
                    exp['matches_formed'],
                    exp['avg_wait_time'],
                    exp['avg_server_util'],
                    exp['avg_mmr_diff']
                ])

    print("✅ Готово! Файл: matchmaking_results_full.csv")
    print("=" * 80)
