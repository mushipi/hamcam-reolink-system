#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自動撮影システム
DeepLabCut学習用データ収集のための統合撮影システム
"""

import os
import sys
import cv2
import numpy as np
import time
import threading
import queue
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Callable
from dataclasses import dataclass, asdict
import json
import yaml

# プロジェクトパスを追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from rtsp_stream import RTSPStream
from phase3_hamster_tracking.utils.hamster_config import HamsterTrackingConfig, load_config
from phase3_hamster_tracking.utils.lighting_detector import LightingModeDetector

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CaptureResult:
    """撮影結果データクラス"""
    timestamp: datetime
    filename: str
    file_path: str
    trigger_type: str  # "scheduled", "motion", "manual"
    quality_score: float
    metadata: Dict
    success: bool
    error_message: Optional[str] = None

@dataclass
class CaptureStats:
    """撮影統計データクラス"""
    total_captures: int = 0
    successful_captures: int = 0
    failed_captures: int = 0
    motion_triggers: int = 0
    scheduled_triggers: int = 0
    manual_triggers: int = 0
    average_quality: float = 0.0
    last_capture_time: Optional[datetime] = None

class AutoCaptureSystem:
    """自動撮影システムメインクラス"""
    
    def __init__(self, config: Optional[HamsterTrackingConfig] = None):
        """
        自動撮影システムを初期化
        
        Args:
            config: ハムスター管理システム設定
        """
        self.config = config if config else load_config()
        
        # システム状態
        self.is_running = False
        self.capture_thread: Optional[threading.Thread] = None
        self.motion_thread: Optional[threading.Thread] = None
        
        # 撮影制御
        self.capture_queue = queue.Queue()
        self.last_scheduled_capture: Optional[datetime] = None
        self.last_motion_capture: Optional[datetime] = None
        
        # 統計情報
        self.stats = CaptureStats()
        self.capture_history: List[CaptureResult] = []
        
        # コンポーネント初期化
        self.stream: Optional[RTSPStream] = None
        self.lighting_detector: Optional[LightingModeDetector] = None
        
        # データ保存設定
        self.setup_storage()
        
        # コールバック関数
        self.on_capture_callback: Optional[Callable[[CaptureResult], None]] = None
        self.on_motion_callback: Optional[Callable[[np.ndarray], None]] = None
        
        logger.info("自動撮影システム初期化完了")
    
    def setup_storage(self):
        """データ保存ディレクトリを設定"""
        base_dir = Path(getattr(self.config, 'storage_base_dir', './data'))
        
        # 必要なディレクトリを作成
        self.storage_paths = {
            'base': base_dir,
            'raw_frames': base_dir / 'raw_frames',
            'processed': base_dir / 'processed',
            'reports': base_dir / 'reports',
            'backup': base_dir / 'backup'
        }
        
        for path_name, path in self.storage_paths.items():
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"ストレージパス設定: {path_name} -> {path}")
    
    def start(self):
        """自動撮影システムを開始"""
        if self.is_running:
            logger.warning("自動撮影システムは既に稼働中です")
            return
        
        logger.info("自動撮影システム開始")
        
        try:
            # カメラパスワード設定
            from utils.camera_config import get_camera_config
            camera_config = get_camera_config()
            camera_config.set_password("894890abc")
            
            # RTSPストリーム初期化
            stream_type = getattr(self.config, 'rtsp_stream_type', 'sub')
            buffer_size = 1
            self.stream = RTSPStream(stream_type=stream_type, buffer_size=buffer_size)
            
            if not self.stream.start_stream():
                raise RuntimeError("RTSPストリーム開始に失敗")
            
            # 照明検出器初期化（オプション）
            try:
                self.lighting_detector = LightingModeDetector()
            except Exception as e:
                logger.warning(f"照明検出器初期化失敗: {e}")
                self.lighting_detector = None
            
            # ワーカースレッド開始
            self.is_running = True
            self.capture_thread = threading.Thread(target=self._capture_worker, daemon=True)
            self.motion_thread = threading.Thread(target=self._motion_monitor, daemon=True)
            
            self.capture_thread.start()
            self.motion_thread.start()
            
            logger.info("✅ 自動撮影システム開始成功")
            
        except Exception as e:
            logger.error(f"❌ 自動撮影システム開始エラー: {e}")
            self.stop()
            raise
    
    def stop(self):
        """自動撮影システムを停止"""
        logger.info("自動撮影システム停止中...")
        
        self.is_running = False
        
        # スレッド終了待機
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=5.0)
        
        if self.motion_thread and self.motion_thread.is_alive():
            self.motion_thread.join(timeout=5.0)
        
        # RTSPストリーム停止
        if self.stream:
            self.stream.stop_stream()
            self.stream = None
        
        # 統計レポート保存
        self._save_session_report()
        
        logger.info("✅ 自動撮影システム停止完了")
    
    def _capture_worker(self):
        """撮影ワーカースレッド"""
        logger.info("撮影ワーカースレッド開始")
        
        while self.is_running:
            try:
                # 定期撮影チェック
                self._check_scheduled_capture()
                
                # キューからの撮影リクエスト処理
                try:
                    capture_request = self.capture_queue.get(timeout=1.0)
                    self._process_capture_request(capture_request)
                    self.capture_queue.task_done()
                except queue.Empty:
                    continue
                    
            except Exception as e:
                logger.error(f"撮影ワーカーエラー: {e}")
                time.sleep(1.0)
        
        logger.info("撮影ワーカースレッド終了")
    
    def _motion_monitor(self):
        """動作監視スレッド"""
        motion_enabled = True  # デフォルトで動作検出を有効
        if not motion_enabled:
            logger.info("動作検出撮影は無効です")
            return
        
        logger.info("動作監視スレッド開始")
        
        # 背景差分器初期化
        bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            detectShadows=True, varThreshold=50, history=500
        )
        
        motion_cooldown = 5.0  # 動作検出後のクールダウン時間（秒）
        
        while self.is_running:
            try:
                if not self.stream:
                    time.sleep(1.0)
                    continue
                
                # フレーム取得
                result = self.stream.get_frame(timeout=2.0)
                if not result or not result[0]:
                    continue
                
                success, frame = result
                
                # 動作検出
                if self._detect_motion(frame, bg_subtractor):
                    # クールダウンチェック
                    now = datetime.now()
                    if (self.last_motion_capture is None or 
                        (now - self.last_motion_capture).total_seconds() > motion_cooldown):
                        
                        logger.info("動作を検出 - 撮影をトリガー")
                        self.trigger_capture("motion")
                        self.last_motion_capture = now
                        
                        if self.on_motion_callback:
                            self.on_motion_callback(frame)
                
            except Exception as e:
                logger.error(f"動作監視エラー: {e}")
                time.sleep(1.0)
        
        logger.info("動作監視スレッド終了")
    
    def _detect_motion(self, frame: np.ndarray, bg_subtractor) -> bool:
        """動作検出"""
        try:
            # グレースケール変換
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # ガウシアンブラー適用
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # 背景差分
            fg_mask = bg_subtractor.apply(blurred)
            
            # ノイズ除去
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
            
            # 輪郭検出
            contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # ハムスターサイズの物体をフィルタリング
            motion_detected = False
            for contour in contours:
                area = cv2.contourArea(contour)
                
                # ハムスターのおおよそのサイズ（ピクセル単位）
                min_area = 500  # 最小面積
                max_area = 5000  # 最大面積
                
                if min_area <= area <= max_area:
                    motion_detected = True
                    break
            
            return motion_detected
            
        except Exception as e:
            logger.error(f"動作検出エラー: {e}")
            return False
    
    def _check_scheduled_capture(self):
        """定期撮影チェック"""
        scheduled_enabled = True  # デフォルトで定期撮影を有効
        if not scheduled_enabled:
            return
        
        now = datetime.now()
        interval_minutes = 60  # デフォルト60分間隔
        
        # 最後の定期撮影からの経過時間をチェック
        if (self.last_scheduled_capture is None or 
            (now - self.last_scheduled_capture).total_seconds() >= interval_minutes * 60):
            
            logger.info("定期撮影時刻に到達")
            self.trigger_capture("scheduled")
            self.last_scheduled_capture = now
    
    def trigger_capture(self, trigger_type: str = "manual", metadata: Optional[Dict] = None):
        """撮影をトリガー"""
        capture_request = {
            'trigger_type': trigger_type,
            'timestamp': datetime.now(),
            'metadata': metadata or {}
        }
        
        try:
            self.capture_queue.put(capture_request, timeout=1.0)
            logger.debug(f"撮影リクエスト追加: {trigger_type}")
        except queue.Full:
            logger.warning("撮影キューが満杯です")
    
    def _process_capture_request(self, request: Dict):
        """撮影リクエストを処理"""
        try:
            trigger_type = request['trigger_type']
            timestamp = request['timestamp']
            metadata = request['metadata']
            
            logger.info(f"撮影実行: {trigger_type} @ {timestamp}")
            
            # フレーム取得
            if not self.stream:
                raise RuntimeError("RTSPストリームが利用できません")
            
            result = self.stream.get_frame(timeout=5.0)
            if not result or not result[0]:
                raise RuntimeError("フレーム取得に失敗")
            
            success, frame = result
            
            # 画質評価
            quality_score = self._assess_image_quality(frame)
            
            # 品質フィルタリング
            min_quality = getattr(getattr(self.config, 'data_collection', None), 'quality', {}).get('min_confidence_ratio', 0.8)
            if quality_score < min_quality:
                logger.warning(f"画質が低いため撮影をスキップ: {quality_score:.2f} < {min_quality:.2f}")
                self._update_stats(False, trigger_type)
                return
            
            # ファイル保存
            filename = self._generate_filename(timestamp, trigger_type)
            file_path = self.storage_paths['raw_frames'] / filename
            
            # メタデータ追加
            capture_metadata = {
                'trigger_type': trigger_type,
                'timestamp': timestamp.isoformat(),
                'quality_score': quality_score,
                'frame_size': frame.shape,
                'lighting_mode': None,
                **metadata
            }
            
            # 照明条件検出
            if self.lighting_detector:
                try:
                    lighting_result = self.lighting_detector.detect_lighting_mode(frame)
                    capture_metadata['lighting_mode'] = lighting_result['mode']
                    capture_metadata['lighting_confidence'] = lighting_result['confidence']
                except Exception as e:
                    logger.warning(f"照明検出エラー: {e}")
            
            # 画像保存
            cv2.imwrite(str(file_path), frame)
            
            # メタデータファイル保存
            metadata_path = file_path.with_suffix('.json')
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(capture_metadata, f, ensure_ascii=False, indent=2)
            
            # 結果記録
            capture_result = CaptureResult(
                timestamp=timestamp,
                filename=filename,
                file_path=str(file_path),
                trigger_type=trigger_type,
                quality_score=quality_score,
                metadata=capture_metadata,
                success=True
            )
            
            self.capture_history.append(capture_result)
            self._update_stats(True, trigger_type, quality_score)
            
            # コールバック実行
            if self.on_capture_callback:
                self.on_capture_callback(capture_result)
            
            logger.info(f"✅ 撮影成功: {filename} (品質: {quality_score:.2f})")
            
        except Exception as e:
            logger.error(f"❌ 撮影処理エラー: {e}")
            self._update_stats(False, trigger_type)
            
            # エラー結果記録
            error_result = CaptureResult(
                timestamp=request['timestamp'],
                filename="",
                file_path="",
                trigger_type=trigger_type,
                quality_score=0.0,
                metadata=metadata,
                success=False,
                error_message=str(e)
            )
            
            self.capture_history.append(error_result)
    
    def _assess_image_quality(self, frame: np.ndarray) -> float:
        """画像品質を評価"""
        try:
            # グレースケール変換
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # ブラー検出（ラプラシアン分散）
            blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # 輝度評価
            brightness = np.mean(gray)
            brightness_range = [50, 200]  # デフォルト値
            brightness_score = 1.0 - abs(brightness - np.mean(brightness_range)) / 127.5
            
            # コントラスト評価
            contrast = gray.std()
            contrast_threshold = 0.3 * 255  # デフォルト値
            contrast_score = min(contrast / contrast_threshold, 1.0)
            
            # 総合品質スコア（0.0-1.0）
            blur_threshold = 100.0  # デフォルト値
            blur_score_norm = min(blur_score / blur_threshold, 1.0)
            
            quality = (blur_score_norm * 0.5 + brightness_score * 0.3 + contrast_score * 0.2)
            
            return max(0.0, min(1.0, quality))
            
        except Exception as e:
            logger.error(f"画質評価エラー: {e}")
            return 0.5  # デフォルト値
    
    def _generate_filename(self, timestamp: datetime, trigger_type: str) -> str:
        """ファイル名を生成"""
        date_str = timestamp.strftime("%Y%m%d_%H%M%S_%f")[:-3]  # ミリ秒まで
        return f"hamster_{trigger_type}_{date_str}.jpg"
    
    def _update_stats(self, success: bool, trigger_type: str, quality_score: float = 0.0):
        """統計情報を更新"""
        self.stats.total_captures += 1
        
        if success:
            self.stats.successful_captures += 1
            self.stats.last_capture_time = datetime.now()
            
            # 移動平均で品質スコアを更新
            if self.stats.successful_captures == 1:
                self.stats.average_quality = quality_score
            else:
                alpha = 0.1  # 学習率
                self.stats.average_quality = (1 - alpha) * self.stats.average_quality + alpha * quality_score
        else:
            self.stats.failed_captures += 1
        
        # トリガータイプ別統計
        if trigger_type == "motion":
            self.stats.motion_triggers += 1
        elif trigger_type == "scheduled":
            self.stats.scheduled_triggers += 1
        elif trigger_type == "manual":
            self.stats.manual_triggers += 1
    
    def _save_session_report(self):
        """セッションレポートを保存"""
        try:
            # 統計情報のdatetimeオブジェクトを文字列に変換
            stats_dict = asdict(self.stats)
            if 'last_capture_time' in stats_dict and stats_dict['last_capture_time']:
                stats_dict['last_capture_time'] = stats_dict['last_capture_time'].isoformat()
            
            report = {
                'session_end_time': datetime.now().isoformat(),
                'statistics': stats_dict,
                'capture_history_count': len(self.capture_history),
                'configuration': {
                    'capture_interval_minutes': 60,  # デフォルト値
                    'motion_detection_enabled': True,  # デフォルト値
                    'quality_threshold': 0.8  # デフォルト値
                }
            }
            
            report_path = self.storage_paths['reports'] / f"session_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"セッションレポート保存: {report_path}")
            
        except Exception as e:
            logger.error(f"セッションレポート保存エラー: {e}")
    
    def get_stats(self) -> Dict:
        """統計情報を取得"""
        return asdict(self.stats)
    
    def get_recent_captures(self, limit: int = 10) -> List[CaptureResult]:
        """最近の撮影履歴を取得"""
        return self.capture_history[-limit:]
    
    def cleanup_old_files(self):
        """古いファイルをクリーンアップ"""
        try:
            now = datetime.now()
            max_days = 7  # デフォルト値
            cutoff_date = now - timedelta(days=max_days)
            
            raw_path = self.storage_paths['raw_frames']
            deleted_count = 0
            
            for file_path in raw_path.glob("hamster_*"):
                if file_path.stat().st_mtime < cutoff_date.timestamp():
                    try:
                        file_path.unlink()  # ファイル削除
                        
                        # 対応するメタデータファイルも削除
                        metadata_path = file_path.with_suffix('.json')
                        if metadata_path.exists():
                            metadata_path.unlink()
                        
                        deleted_count += 1
                    except Exception as e:
                        logger.warning(f"ファイル削除エラー: {file_path} - {e}")
            
            if deleted_count > 0:
                logger.info(f"古いファイルをクリーンアップ: {deleted_count}件削除")
            
        except Exception as e:
            logger.error(f"ファイルクリーンアップエラー: {e}")

def main():
    """テスト用メイン関数"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    try:
        # 設定読み込み
        config = load_config()
        
        # 自動撮影システム初期化
        capture_system = AutoCaptureSystem(config)
        
        # コールバック関数設定
        def on_capture(result: CaptureResult):
            print(f"撮影完了: {result.filename} (品質: {result.quality_score:.2f})")
        
        def on_motion(frame: np.ndarray):
            print(f"動作検出: フレームサイズ {frame.shape}")
        
        capture_system.on_capture_callback = on_capture
        capture_system.on_motion_callback = on_motion
        
        # システム開始
        capture_system.start()
        
        print("自動撮影システムが稼働中... (Ctrl+C で終了)")
        
        # 手動撮影テスト
        time.sleep(5)
        print("手動撮影テスト実行")
        capture_system.trigger_capture("manual", {"test": True})
        
        # メインループ
        try:
            while True:
                time.sleep(10)
                
                # 統計情報表示
                stats = capture_system.get_stats()
                print(f"撮影統計: 成功 {stats['successful_captures']}/{stats['total_captures']}, " +
                      f"平均品質 {stats['average_quality']:.2f}")
        
        except KeyboardInterrupt:
            print("\n終了シグナルを受信")
        
        finally:
            capture_system.stop()
            print("自動撮影システムを停止しました")
    
    except Exception as e:
        logger.error(f"システムエラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()