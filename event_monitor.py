#!/usr/bin/env python3
"""
イベント監視システム
モーション検知・AI検知イベントの監視と記録
"""

import time
import json
import threading
import logging
from datetime import datetime, timedelta
from pathlib import Path
from reolinkapi import Camera
from utils.camera_config import get_camera_config, prompt_password_if_needed

class EventMonitor:
    """イベント監視クラス"""
    
    def __init__(self, poll_interval: int = 5):
        """
        イベント監視を初期化
        
        Args:
            poll_interval: ポーリング間隔（秒）
        """
        self.poll_interval = poll_interval
        self.config = get_camera_config()
        
        # API接続
        self.camera = None
        
        # 監視状態
        self.is_monitoring = False
        self.monitor_thread = None
        
        # イベント管理
        self.event_history = []
        self.last_event_time = {}
        self.event_counts = {
            'motion': 0,
            'ai_person': 0,
            'ai_vehicle': 0,
            'ai_animal': 0
        }
        
        # 出力設定
        self.logs_dir = Path(self.config.output_dir) / self.config.logs_dir
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # コールバック
        self.event_callbacks = {}
        
        # ログ設定
        self.logger = logging.getLogger("EventMonitor")
    
    def initialize(self) -> bool:
        """監視システム初期化"""
        if not self.config.validate():
            prompt_password_if_needed()
        
        try:
            self.camera = Camera(self.config.ip, self.config.username, self.config.password)
            if self.camera.login():
                self.logger.info("イベント監視初期化成功")
                return True
            else:
                self.logger.error("API認証失敗")
                return False
        except Exception as e:
            self.logger.error(f"初期化エラー: {e}")
            return False
    
    def start_monitoring(self):
        """監視開始"""
        if self.is_monitoring:
            self.logger.warning("既に監視中です")
            return
        
        if not self.camera:
            if not self.initialize():
                return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitoring_worker, daemon=True)
        self.monitor_thread.start()
        
        self.logger.info(f"イベント監視開始 (間隔: {self.poll_interval}秒)")
    
    def stop_monitoring(self):
        """監視停止"""
        self.is_monitoring = False
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)
        
        if self.camera:
            self.camera.logout()
        
        self.logger.info("イベント監視停止")
    
    def _monitoring_worker(self):
        """監視処理ワーカー"""
        while self.is_monitoring:
            try:
                # モーション検知イベント確認
                self._check_motion_events()
                
                # AI検知イベント確認
                self._check_ai_events()
                
                # イベント履歴の保存
                self._save_event_log()
                
                time.sleep(self.poll_interval)
                
            except Exception as e:
                self.logger.error(f"監視処理エラー: {e}")
                time.sleep(self.poll_interval)
    
    def _check_motion_events(self):
        """モーション検知イベント確認"""
        try:
            # モーション検知状態取得
            motion_state = self.camera.get_motion_detection()
            
            if motion_state and motion_state.get('enable'):
                # 現在時刻でのモーション状態を確認
                # 注意: この部分は実際のAPIレスポンスに応じて調整が必要
                current_time = datetime.now()
                
                # 簡易的なモーション検知 - 実際の実装では適切なAPIを使用
                if self._should_trigger_motion_event():
                    event = {
                        'type': 'motion',
                        'timestamp': current_time.isoformat(),
                        'details': {
                            'sensitivity': motion_state.get('sensitivity', 0)
                        }
                    }
                    self._process_event(event)
                    
        except Exception as e:
            self.logger.debug(f"モーション検知確認エラー: {e}")
    
    def _check_ai_events(self):
        """AI検知イベント確認"""
        try:
            # AI設定取得
            ai_config = self.camera.get_ai_config()
            
            if not ai_config:
                return
            
            current_time = datetime.now()
            
            # 人間検知
            if ai_config.get('people', {}).get('enabled'):
                if self._should_trigger_ai_event('person'):
                    event = {
                        'type': 'ai_person',
                        'timestamp': current_time.isoformat(),
                        'details': {
                            'confidence': 0.85  # 仮の値
                        }
                    }
                    self._process_event(event)
            
            # 車両検知
            if ai_config.get('vehicle', {}).get('enabled'):
                if self._should_trigger_ai_event('vehicle'):
                    event = {
                        'type': 'ai_vehicle',
                        'timestamp': current_time.isoformat(),
                        'details': {
                            'confidence': 0.80
                        }
                    }
                    self._process_event(event)
            
            # 動物検知
            if ai_config.get('dog_cat', {}).get('enabled'):
                if self._should_trigger_ai_event('animal'):
                    event = {
                        'type': 'ai_animal',
                        'timestamp': current_time.isoformat(),
                        'details': {
                            'confidence': 0.75
                        }
                    }
                    self._process_event(event)
                    
        except Exception as e:
            self.logger.debug(f"AI検知確認エラー: {e}")
    
    def _should_trigger_motion_event(self) -> bool:
        """モーション検知イベントトリガー判定（仮実装）"""
        # 実際の実装では、カメラからのリアルタイムモーション情報を使用
        # ここでは最後のイベントから一定時間経過した場合にランダムで発生させる
        last_motion = self.last_event_time.get('motion', 0)
        if time.time() - last_motion > 30:  # 30秒間隔
            import random
            if random.random() < 0.1:  # 10%の確率
                return True
        return False
    
    def _should_trigger_ai_event(self, event_type: str) -> bool:
        """AI検知イベントトリガー判定（仮実装）"""
        # 実際の実装では、カメラからのリアルタイムAI検知情報を使用
        last_event = self.last_event_time.get(f'ai_{event_type}', 0)
        if time.time() - last_event > 60:  # 60秒間隔
            import random
            if random.random() < 0.05:  # 5%の確率
                return True
        return False
    
    def _process_event(self, event: dict):
        """イベント処理"""
        # イベント履歴に追加
        self.event_history.append(event)
        
        # 統計更新
        event_type = event['type']
        if event_type in self.event_counts:
            self.event_counts[event_type] += 1
        
        # 最終イベント時刻更新
        self.last_event_time[event_type] = time.time()
        
        # ログ出力
        self.logger.info(f"イベント検知: {event_type} - {event['timestamp']}")
        
        # コールバック実行
        if event_type in self.event_callbacks:
            try:
                self.event_callbacks[event_type](event)
            except Exception as e:
                self.logger.error(f"イベントコールバックエラー: {e}")
        
        # 履歴制限（最新1000件）
        if len(self.event_history) > 1000:
            self.event_history = self.event_history[-1000:]
    
    def _save_event_log(self):
        """イベントログ保存"""
        try:
            # 日別ログファイル
            today = datetime.now().strftime("%Y%m%d")
            log_file = self.logs_dir / f"events_{today}.json"
            
            # 今日のイベントを抽出
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_events = [
                event for event in self.event_history
                if datetime.fromisoformat(event['timestamp']) >= today_start
            ]
            
            # ログファイル書き込み
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'date': today,
                    'events': today_events,
                    'summary': {
                        'total_events': len(today_events),
                        'counts': self.event_counts.copy()
                    }
                }, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            self.logger.error(f"ログ保存エラー: {e}")
    
    def set_event_callback(self, event_type: str, callback):
        """イベントコールバック設定"""
        self.event_callbacks[event_type] = callback
        self.logger.info(f"イベントコールバック設定: {event_type}")
    
    def get_recent_events(self, hours: int = 24) -> list:
        """最近のイベントを取得"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_events = [
            event for event in self.event_history
            if datetime.fromisoformat(event['timestamp']) >= cutoff_time
        ]
        
        return recent_events
    
    def get_event_stats(self) -> dict:
        """イベント統計情報取得"""
        recent_events = self.get_recent_events(24)
        
        return {
            'is_monitoring': self.is_monitoring,
            'total_events': len(self.event_history),
            'recent_events_24h': len(recent_events),
            'event_counts': self.event_counts.copy(),
            'last_event_times': self.last_event_time.copy(),
            'poll_interval': self.poll_interval
        }
    
    def get_motion_detection_config(self) -> dict:
        """モーション検知設定取得"""
        try:
            if self.camera:
                return self.camera.get_motion_detection()
            return {}
        except Exception as e:
            self.logger.error(f"モーション検知設定取得エラー: {e}")
            return {}
    
    def get_ai_detection_config(self) -> dict:
        """AI検知設定取得"""
        try:
            if self.camera:
                return self.camera.get_ai_config()
            return {}
        except Exception as e:
            self.logger.error(f"AI検知設定取得エラー: {e}")
            return {}

class EventAlertSystem:
    """イベント通知システム"""
    
    def __init__(self, monitor: EventMonitor):
        self.monitor = monitor
        self.alert_rules = []
        self.logger = logging.getLogger("EventAlertSystem")
    
    def add_alert_rule(self, event_type: str, threshold: int = 1, 
                      time_window: int = 300):
        """
        アラートルール追加
        
        Args:
            event_type: イベントタイプ
            threshold: 閾値（件数）
            time_window: 時間窓（秒）
        """
        rule = {
            'event_type': event_type,
            'threshold': threshold,
            'time_window': time_window
        }
        self.alert_rules.append(rule)
        
        # コールバック設定
        self.monitor.set_event_callback(event_type, self._check_alert_rules)
        
        self.logger.info(f"アラートルール追加: {event_type} - {threshold}件/{time_window}秒")
    
    def _check_alert_rules(self, event: dict):
        """アラートルールチェック"""
        event_type = event['type']
        event_time = datetime.fromisoformat(event['timestamp'])
        
        for rule in self.alert_rules:
            if rule['event_type'] == event_type:
                # 時間窓内のイベント数をカウント
                window_start = event_time - timedelta(seconds=rule['time_window'])
                
                count = sum(1 for e in self.monitor.event_history
                           if (e['type'] == event_type and 
                               datetime.fromisoformat(e['timestamp']) >= window_start))
                
                if count >= rule['threshold']:
                    self._trigger_alert(rule, count, event)
    
    def _trigger_alert(self, rule: dict, count: int, event: dict):
        """アラート発動"""
        alert_msg = (f"アラート発動: {rule['event_type']} - "
                    f"{count}件/{rule['time_window']}秒 "
                    f"(閾値: {rule['threshold']}件)")
        
        self.logger.warning(alert_msg)
        print(f"🚨 {alert_msg}")

def main():
    """メイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Reolink Camera Event Monitor")
    parser.add_argument("-i", "--interval", type=int, default=5,
                       help="ポーリング間隔（秒, default: 5）")
    parser.add_argument("-a", "--alerts", action="store_true",
                       help="アラートシステム有効化")
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="詳細ログ出力")
    
    args = parser.parse_args()
    
    # ログ設定
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level,
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # イベント監視開始
    monitor = EventMonitor(args.interval)
    
    if not monitor.initialize():
        print("初期化失敗")
        return
    
    # アラートシステム設定
    if args.alerts:
        alert_system = EventAlertSystem(monitor)
        alert_system.add_alert_rule('motion', threshold=5, time_window=300)
        alert_system.add_alert_rule('ai_person', threshold=3, time_window=600)
        print("アラートシステム有効")
    
    print("イベント監視開始")
    print("Ctrl+Cで停止")
    
    try:
        monitor.start_monitoring()
        
        # 統計情報表示
        while monitor.is_monitoring:
            time.sleep(30)
            stats = monitor.get_event_stats()
            print(f"\n=== イベント統計 ===")
            print(f"総イベント数: {stats['total_events']}")
            print(f"24時間以内: {stats['recent_events_24h']}")
            print(f"イベント別: {stats['event_counts']}")
    
    except KeyboardInterrupt:
        print("\n監視停止中...")
    finally:
        monitor.stop_monitoring()
        print("監視完了")

if __name__ == "__main__":
    main()