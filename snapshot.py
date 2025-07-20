#!/usr/bin/env python3
"""
スナップショット機能
RTSPストリームまたはAPI経由で静止画を取得・保存
"""

import cv2
import time
import threading
import logging
import argparse
from datetime import datetime
from pathlib import Path
from reolinkapi import Camera
from rtsp_stream import RTSPStream
from utils.camera_config import get_camera_config, prompt_password_if_needed

class SnapshotCapture:
    """スナップショット撮影クラス"""
    
    def __init__(self, method: str = "rtsp", stream_type: str = "main"):
        """
        スナップショット機能を初期化
        
        Args:
            method: "rtsp" または "api"
            stream_type: "main" または "sub" (RTSPの場合のみ)
        """
        self.method = method
        self.stream_type = stream_type
        self.config = get_camera_config()
        
        # 撮影方法によってセットアップ
        if method == "rtsp":
            self.stream = RTSPStream(stream_type, buffer_size=1)
            self.camera = None
        else:  # api
            self.stream = None
            self.camera = None
        
        # 出力設定
        self.output_dir = Path(self.config.output_dir) / self.config.snapshots_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 統計情報
        self.total_snapshots = 0
        self.successful_snapshots = 0
        
        # ログ設定
        self.logger = logging.getLogger("SnapshotCapture")
    
    def initialize(self) -> bool:
        """撮影システム初期化"""
        if not self.config.validate():
            prompt_password_if_needed()
        
        if self.method == "rtsp":
            return self._initialize_rtsp()
        else:
            return self._initialize_api()
    
    def _initialize_rtsp(self) -> bool:
        """RTSPストリーム初期化"""
        try:
            if self.stream.start_stream():
                self.logger.info(f"RTSPストリーム初期化成功 ({self.stream_type})")
                return True
            else:
                self.logger.error("RTSPストリーム初期化失敗")
                return False
        except Exception as e:
            self.logger.error(f"RTSPストリーム初期化エラー: {e}")
            return False
    
    def _initialize_api(self) -> bool:
        """API接続初期化"""
        try:
            self.camera = Camera(self.config.ip, self.config.username, self.config.password)
            if self.camera.login():
                self.logger.info("API接続初期化成功")
                return True
            else:
                self.logger.error("API認証失敗")
                return False
        except Exception as e:
            self.logger.error(f"API初期化エラー: {e}")
            return False
    
    def capture_snapshot(self, filename: str = None, quality: int = 95) -> str:
        """
        スナップショット撮影
        
        Args:
            filename: 保存ファイル名（Noneで自動生成）
            quality: JPEG品質（1-100）
        
        Returns:
            保存されたファイルパス、失敗時はNone
        """
        try:
            self.total_snapshots += 1
            
            if self.method == "rtsp":
                return self._capture_from_rtsp(filename, quality)
            else:
                return self._capture_from_api(filename, quality)
        
        except Exception as e:
            self.logger.error(f"スナップショット撮影エラー: {e}")
            return None
    
    def _capture_from_rtsp(self, filename: str, quality: int) -> str:
        """RTSPストリームからスナップショット撮影"""
        if not self.stream or not self.stream.is_running:
            self.logger.error("RTSPストリームが開始されていません")
            return None
        
        # フレーム取得
        result = self.stream.get_current_frame()
        if not result or not result[0]:
            self.logger.error("RTSPフレーム取得失敗")
            return None
        
        _, frame = result
        
        # ファイル名生成
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # ミリ秒まで
            filename = f"snapshot_rtsp_{self.stream_type}_{timestamp}.jpg"
        
        filepath = self.output_dir / filename
        
        # 画像保存
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
        success = cv2.imwrite(str(filepath), frame, encode_params)
        
        if success:
            self.successful_snapshots += 1
            self.logger.info(f"スナップショット保存: {filepath}")
            return str(filepath)
        else:
            self.logger.error(f"画像保存失敗: {filepath}")
            return None
    
    def _capture_from_api(self, filename: str, quality: int) -> str:
        """API経由でスナップショット撮影"""
        if not self.camera:
            self.logger.error("API接続が初期化されていません")
            return None
        
        try:
            # API経由でスナップショット取得
            snapshot_data = self.camera.get_snap()
            
            if not snapshot_data:
                self.logger.error("APIスナップショット取得失敗")
                return None
            
            # ファイル名生成
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                filename = f"snapshot_api_{timestamp}.jpg"
            
            filepath = self.output_dir / filename
            
            # バイナリデータを保存
            with open(filepath, 'wb') as f:
                f.write(snapshot_data)
            
            self.successful_snapshots += 1
            self.logger.info(f"APIスナップショット保存: {filepath}")
            return str(filepath)
        
        except Exception as e:
            self.logger.error(f"APIスナップショット撮影エラー: {e}")
            return None
    
    def capture_burst(self, count: int, interval: float = 0.5, 
                     filename_prefix: str = "burst") -> list:
        """
        連続スナップショット撮影
        
        Args:
            count: 撮影枚数
            interval: 撮影間隔（秒）
            filename_prefix: ファイル名プレフィックス
        
        Returns:
            保存されたファイルパスのリスト
        """
        results = []
        self.logger.info(f"連続撮影開始: {count}枚, 間隔{interval}秒")
        
        for i in range(count):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            filename = f"{filename_prefix}_{timestamp}_{i+1:03d}.jpg"
            
            filepath = self.capture_snapshot(filename)
            if filepath:
                results.append(filepath)
            
            if i < count - 1:  # 最後以外は待機
                time.sleep(interval)
        
        self.logger.info(f"連続撮影完了: {len(results)}/{count}枚成功")
        return results
    
    def capture_timelapse(self, duration: int, interval: int, 
                         filename_prefix: str = "timelapse") -> list:
        """
        タイムラプス撮影
        
        Args:
            duration: 撮影時間（秒）
            interval: 撮影間隔（秒）
            filename_prefix: ファイル名プレフィックス
        
        Returns:
            保存されたファイルパスのリスト
        """
        results = []
        start_time = time.time()
        shot_count = 0
        
        self.logger.info(f"タイムラプス撮影開始: {duration}秒間, {interval}秒間隔")
        
        while (time.time() - start_time) < duration:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{filename_prefix}_{timestamp}_{shot_count:04d}.jpg"
            
            filepath = self.capture_snapshot(filename)
            if filepath:
                results.append(filepath)
                shot_count += 1
            
            time.sleep(interval)
        
        self.logger.info(f"タイムラプス撮影完了: {len(results)}枚撮影")
        return results
    
    def get_stats(self) -> dict:
        """撮影統計情報を取得"""
        success_rate = (self.successful_snapshots / self.total_snapshots * 100 
                       if self.total_snapshots > 0 else 0)
        
        return {
            'method': self.method,
            'stream_type': self.stream_type if self.method == "rtsp" else None,
            'total_snapshots': self.total_snapshots,
            'successful_snapshots': self.successful_snapshots,
            'success_rate': success_rate,
            'output_directory': str(self.output_dir)
        }
    
    def cleanup(self):
        """リソースクリーンアップ"""
        if self.stream:
            self.stream.stop_stream()
        
        if self.camera:
            self.camera.logout()
        
        self.logger.info("スナップショット機能クリーンアップ完了")

class AutoSnapshotScheduler:
    """自動スナップショット撮影スケジューラー"""
    
    def __init__(self, capture: SnapshotCapture):
        self.capture = capture
        self.is_running = False
        self.scheduler_thread = None
        self.schedule_list = []
        self.logger = logging.getLogger("AutoSnapshotScheduler")
    
    def add_interval_schedule(self, interval: int, 
                            filename_prefix: str = "auto"):
        """定期撮影スケジュールを追加"""
        self.schedule_list.append({
            'type': 'interval',
            'interval': interval,
            'prefix': filename_prefix,
            'last_shot': 0
        })
        self.logger.info(f"定期撮影スケジュール追加: {interval}秒間隔")
    
    def start_scheduler(self):
        """スケジューラー開始"""
        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_worker, daemon=True)
        self.scheduler_thread.start()
        self.logger.info("自動撮影スケジューラー開始")
    
    def stop_scheduler(self):
        """スケジューラー停止"""
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join()
        self.logger.info("自動撮影スケジューラー停止")
    
    def _scheduler_worker(self):
        """スケジューラーワーカー"""
        while self.is_running:
            current_time = time.time()
            
            for schedule in self.schedule_list:
                if schedule['type'] == 'interval':
                    if (current_time - schedule['last_shot']) >= schedule['interval']:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"{schedule['prefix']}_{timestamp}.jpg"
                        
                        filepath = self.capture.capture_snapshot(filename)
                        if filepath:
                            schedule['last_shot'] = current_time
                            self.logger.debug(f"定期撮影実行: {filepath}")
            
            time.sleep(1)

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="Reolink Camera Snapshot Tool")
    parser.add_argument("-m", "--method", choices=["rtsp", "api"], default="rtsp",
                       help="撮影方法 (default: rtsp)")
    parser.add_argument("-s", "--stream", choices=["main", "sub"], default="main",
                       help="ストリームタイプ (RTSPのみ, default: main)")
    parser.add_argument("-o", "--output", 
                       help="出力ファイル名")
    parser.add_argument("-q", "--quality", type=int, default=95,
                       help="JPEG品質 (1-100, default: 95)")
    parser.add_argument("-c", "--count", type=int, default=1,
                       help="撮影枚数")
    parser.add_argument("-i", "--interval", type=float, default=1.0,
                       help="撮影間隔（秒）")
    parser.add_argument("-t", "--timelapse", type=int,
                       help="タイムラプス撮影時間（秒）")
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="詳細ログ出力")
    
    args = parser.parse_args()
    
    # ログ設定
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level,
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # スナップショット撮影
    capture = SnapshotCapture(args.method, args.stream)
    
    try:
        if not capture.initialize():
            print("初期化失敗")
            return
        
        print(f"スナップショット撮影開始 ({args.method}方式)")
        
        if args.timelapse:
            # タイムラプス撮影
            print(f"タイムラプス撮影: {args.timelapse}秒間, {args.interval}秒間隔")
            results = capture.capture_timelapse(args.timelapse, int(args.interval))
            print(f"撮影完了: {len(results)}枚")
        
        elif args.count > 1:
            # 連続撮影
            print(f"連続撮影: {args.count}枚, {args.interval}秒間隔")
            results = capture.capture_burst(args.count, args.interval)
            print(f"撮影完了: {len(results)}枚")
        
        else:
            # 単発撮影
            filepath = capture.capture_snapshot(args.output, args.quality)
            if filepath:
                print(f"撮影完了: {filepath}")
            else:
                print("撮影失敗")
        
        # 統計表示
        stats = capture.get_stats()
        print(f"統計: {stats['successful_snapshots']}/{stats['total_snapshots']}枚成功 "
              f"({stats['success_rate']:.1f}%)")
    
    except KeyboardInterrupt:
        print("\n中断されました")
    finally:
        capture.cleanup()

if __name__ == "__main__":
    main()