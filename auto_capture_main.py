#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自動撮影システム メインスクリプト
DeepLabCut学習用データ収集のための統合自動撮影システム

使用方法:
  python auto_capture_main.py                    # デフォルト設定で開始
  python auto_capture_main.py --duration 3600    # 1時間限定で実行
  python auto_capture_main.py --config custom.yaml  # カスタム設定ファイル使用
  python auto_capture_main.py --test             # テストモード
"""

import os
import sys
import time
import argparse
import signal
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path
import threading
import json

# プロジェクトパスを追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# プロジェクトモジュール
from phase3_hamster_tracking.utils.hamster_config import HamsterTrackingConfig, load_config
from phase3_hamster_tracking.data_collection.auto_capture_system import AutoCaptureSystem, CaptureResult
from phase3_hamster_tracking.data_collection.motion_detector import MotionDetector, MotionEvent
from phase3_hamster_tracking.data_collection.data_quality import DataQualityAssessor, QualityMetrics
from rtsp_stream import RTSPStream

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('auto_capture.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class IntegratedCaptureSystem:
    """統合自動撮影システム"""
    
    def __init__(self, config: HamsterTrackingConfig, test_mode: bool = False):
        """
        統合システムを初期化
        
        Args:
            config: システム設定
            test_mode: テストモード（短時間実行用）
        """
        self.config = config
        self.test_mode = test_mode
        self.is_running = False
        
        # システムコンポーネント
        self.capture_system: Optional[AutoCaptureSystem] = None
        self.motion_detector: Optional[MotionDetector] = None
        self.quality_assessor: Optional[DataQualityAssessor] = None
        
        # 統計情報
        self.session_stats = {
            'session_start': datetime.now(),
            'total_captures': 0,
            'successful_captures': 0,
            'high_quality_captures': 0,
            'motion_detections': 0,
            'session_duration': 0,
            'average_capture_interval': 0,
            'data_size_mb': 0
        }
        
        # シャットダウン処理用
        self._shutdown_requested = False
        self._setup_signal_handlers()
        
        logger.info(f"統合撮影システム初期化完了 {'(テストモード)' if test_mode else ''}")
    
    def _setup_signal_handlers(self):
        """シグナルハンドラ設定"""
        def signal_handler(signum, frame):
            logger.info(f"終了シグナルを受信 (シグナル: {signum})")
            self.request_shutdown()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def initialize_components(self):
        """システムコンポーネントを初期化"""
        try:
            logger.info("システムコンポーネントを初期化中...")
            
            # 自動撮影システム初期化
            self.capture_system = AutoCaptureSystem(self.config)
            
            # 動作検出器初期化
            self.motion_detector = MotionDetector(self.config)
            
            # 品質評価器初期化
            self.quality_assessor = DataQualityAssessor(self.config)
            
            # コールバック設定
            self._setup_callbacks()
            
            logger.info("✅ システムコンポーネント初期化完了")
            return True
            
        except Exception as e:
            logger.error(f"❌ システムコンポーネント初期化エラー: {e}")
            return False
    
    def _setup_callbacks(self):
        """コールバック関数を設定"""
        # 撮影完了時のコールバック
        def on_capture_complete(result: CaptureResult):
            self.session_stats['total_captures'] += 1
            
            if result.success:
                self.session_stats['successful_captures'] += 1
                
                # 品質評価実行
                try:
                    if os.path.exists(result.file_path):
                        import cv2
                        image = cv2.imread(result.file_path)
                        if image is not None:
                            quality_metrics = self.quality_assessor.evaluate_image_quality(
                                image, result.file_path
                            )
                            
                            # 高品質画像の統計
                            if quality_metrics.overall_score >= 0.7:
                                self.session_stats['high_quality_captures'] += 1
                            
                            logger.info(f"撮影完了: {result.filename} "
                                      f"(品質: {quality_metrics.quality_level.value}, "
                                      f"スコア: {quality_metrics.overall_score:.2f})")
                            
                            # 品質が低い場合は警告
                            if quality_metrics.overall_score < 0.5:
                                logger.warning(f"低品質画像: {result.filename} - {quality_metrics.notes}")
                        
                        # ファイルサイズ統計
                        file_size_mb = os.path.getsize(result.file_path) / (1024 * 1024)
                        self.session_stats['data_size_mb'] += file_size_mb
                        
                except Exception as e:
                    logger.error(f"品質評価エラー: {e}")
            else:
                logger.error(f"撮影失敗: {result.error_message}")
        
        # 動作検出時のコールバック
        def on_motion_detected(event: MotionEvent):
            self.session_stats['motion_detections'] += 1
            logger.debug(f"動作検出: {event.motion_type} at {event.center}, "
                        f"速度: {event.velocity_mm:.1f}mm/s, 信頼度: {event.confidence:.2f}")
        
        # 活動状態変化時のコールバック
        def on_activity_change(state: str):
            logger.info(f"ハムスター活動状態変化: {state}")
            
            # 活動状態に応じて撮影頻度を調整（オプション）
            if state == "active" and not self.test_mode:
                # 活動中は撮影頻度を上げる
                logger.info("活動中のため撮影頻度を上げます")
                self.capture_system.trigger_capture("activity", {"activity_state": state})
        
        # コールバック設定
        if self.capture_system:
            self.capture_system.on_capture_callback = on_capture_complete
        
        if self.motion_detector:
            self.motion_detector.on_motion_detected = on_motion_detected
            self.motion_detector.on_activity_change = on_activity_change
    
    def start(self, duration: Optional[int] = None):
        """
        統合システム開始
        
        Args:
            duration: 実行時間（秒）、Noneで無制限
        """
        if self.is_running:
            logger.warning("システムは既に稼働中です")
            return
        
        logger.info("=== 統合自動撮影システム開始 ===")
        
        # システム情報表示
        self._display_system_info(duration)
        
        try:
            # 自動撮影システム開始
            self.capture_system.start()
            
            # 実行時間制限がある場合
            end_time = None
            if duration:
                end_time = datetime.now() + timedelta(seconds=duration)
                logger.info(f"実行制限時間: {duration}秒 (終了予定: {end_time.strftime('%H:%M:%S')})")
            
            self.is_running = True
            
            # メインループ
            self._main_loop(end_time)
            
        except Exception as e:
            logger.error(f"システム実行エラー: {e}")
        finally:
            self.stop()
    
    def _display_system_info(self, duration: Optional[int]):
        """システム情報を表示"""
        logger.info(f"設定情報:")
        logger.info(f"  ケージサイズ: {self.config.cage.width}×{self.config.cage.height}mm")
        logger.info(f"  撮影間隔: 60分")  # デフォルト値
        logger.info(f"  動作検出: 有効")  # デフォルト値
        logger.info(f"  品質評価: 有効")  # デフォルト値
        logger.info(f"  データ保存: {getattr(self.config, 'storage_base_dir', './data')}")
        logger.info(f"  実行時間: {'無制限' if duration is None else f'{duration}秒'}")
        logger.info(f"  テストモード: {'有効' if self.test_mode else '無効'}")
    
    def _main_loop(self, end_time: Optional[datetime]):
        """メインループ"""
        last_stats_time = datetime.now()
        stats_interval = 300  # 5分間隔で統計表示
        
        # RTSPストリーム（動作検出用）
        stream_type = 'sub'  # デフォルト値
        stream = RTSPStream(stream_type=stream_type, buffer_size=1)
        
        try:
            if not stream.start_stream():
                raise RuntimeError("RTSPストリーム開始失敗（動作検出用）")
            
            logger.info("✅ 動作検出用RTSPストリーム開始")
            
            while self.is_running and not self._shutdown_requested:
                # 時間制限チェック
                if end_time and datetime.now() >= end_time:
                    logger.info("実行時間制限に到達")
                    break
                
                # 動作検出実行
                self._perform_motion_detection(stream)
                
                # 定期統計表示
                now = datetime.now()
                if (now - last_stats_time).total_seconds() >= stats_interval:
                    self._display_periodic_stats()
                    last_stats_time = now
                
                # ファイルクリーンアップ（1時間間隔）
                if not self.test_mode and now.minute == 0 and now.second < 30:
                    self.capture_system.cleanup_old_files()
                
                # 短時間待機
                time.sleep(1.0)
        
        finally:
            if stream:
                stream.stop_stream()
    
    def _perform_motion_detection(self, stream: RTSPStream):
        """動作検出を実行"""
        try:
            result = stream.get_frame(timeout=2.0)
            if result and result[0]:
                success, frame = result
                
                # 動作検出実行
                motion_events = self.motion_detector.detect_motion(frame)
                
                # テストモード時は検出結果を可視化
                if self.test_mode and motion_events:
                    import cv2
                    vis_frame = self.motion_detector.visualize_detection(frame, motion_events)
                    cv2.imshow('Motion Detection (Test Mode)', vis_frame)
                    cv2.waitKey(1)
        
        except Exception as e:
            logger.debug(f"動作検出エラー: {e}")
    
    def _display_periodic_stats(self):
        """定期統計表示"""
        # セッション統計更新
        session_duration = (datetime.now() - self.session_stats['session_start']).total_seconds()
        self.session_stats['session_duration'] = session_duration
        
        # 撮影統計
        capture_stats = self.capture_system.get_stats() if self.capture_system else {}
        motion_stats = self.motion_detector.get_stats() if self.motion_detector else {}
        quality_stats = self.quality_assessor.get_stats() if self.quality_assessor else {}
        
        logger.info("=== 定期統計レポート ===")
        logger.info(f"稼働時間: {int(session_duration/60)}分")
        logger.info(f"撮影: 成功 {self.session_stats['successful_captures']}/{self.session_stats['total_captures']}")
        logger.info(f"高品質画像: {self.session_stats['high_quality_captures']}")
        logger.info(f"動作検出: {self.session_stats['motion_detections']}回")
        logger.info(f"データサイズ: {self.session_stats['data_size_mb']:.1f}MB")
        
        if motion_stats:
            logger.info(f"活動状態: {self.motion_detector.get_activity_state()}")
        
        if quality_stats.get('total_evaluated', 0) > 0:
            logger.info(f"平均品質スコア: {quality_stats['average_overall_score']:.2f}")
    
    def request_shutdown(self):
        """シャットダウン要求"""
        logger.info("システムシャットダウンを要求")
        self._shutdown_requested = True
    
    def stop(self):
        """システム停止"""
        logger.info("統合撮影システム停止中...")
        
        self.is_running = False
        
        # 各コンポーネント停止
        if self.capture_system:
            self.capture_system.stop()
        
        # 最終統計表示
        self._display_final_stats()
        
        # 最終レポート保存
        self._save_final_report()
        
        # OpenCVウィンドウ閉じる（テストモード時）
        if self.test_mode:
            import cv2
            cv2.destroyAllWindows()
        
        logger.info("✅ 統合撮影システム停止完了")
    
    def _display_final_stats(self):
        """最終統計表示"""
        session_duration = (datetime.now() - self.session_stats['session_start']).total_seconds()
        
        logger.info("=== 最終セッション統計 ===")
        logger.info(f"稼働時間: {int(session_duration/60)}分{int(session_duration%60)}秒")
        logger.info(f"総撮影数: {self.session_stats['total_captures']}")
        logger.info(f"成功撮影: {self.session_stats['successful_captures']}")
        logger.info(f"高品質画像: {self.session_stats['high_quality_captures']}")
        logger.info(f"動作検出: {self.session_stats['motion_detections']}回")
        logger.info(f"総データサイズ: {self.session_stats['data_size_mb']:.2f}MB")
        
        # 効率性指標
        if session_duration > 0:
            capture_rate = self.session_stats['successful_captures'] / (session_duration / 3600)  # captures/hour
            logger.info(f"撮影効率: {capture_rate:.1f}枚/時間")
        
        if self.session_stats['successful_captures'] > 0:
            quality_ratio = self.session_stats['high_quality_captures'] / self.session_stats['successful_captures']
            logger.info(f"高品質率: {quality_ratio*100:.1f}%")
    
    def _save_final_report(self):
        """最終レポート保存"""
        try:
            report = {
                'session_summary': self.session_stats,
                'system_configuration': {
                    'cage_size_mm': [self.config.cage.width, self.config.cage.height],
                    'capture_interval_minutes': 60,  # デフォルト値
                    'motion_detection_enabled': True,  # デフォルト値
                    'quality_assessment_enabled': True,  # デフォルト値
                    'test_mode': self.test_mode
                },
                'component_stats': {}
            }
            
            # 各コンポーネントの統計情報を追加
            if self.capture_system:
                report['component_stats']['capture_system'] = self.capture_system.get_stats()
            
            if self.motion_detector:
                report['component_stats']['motion_detector'] = self.motion_detector.get_stats()
            
            if self.quality_assessor:
                report['component_stats']['quality_assessor'] = self.quality_assessor.get_stats()
            
            # レポートファイル保存
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_filename = f"session_report_{timestamp}.json"
            report_path = Path(getattr(self.config, 'storage_base_dir', './data')) / "reports" / report_filename
            
            report_path.parent.mkdir(parents=True, exist_ok=True)
            
            # datetimeオブジェクトを文字列に変換
            session_stats_clean = {}
            for key, value in self.session_stats.items():
                if isinstance(value, datetime):
                    session_stats_clean[key] = value.isoformat()
                else:
                    session_stats_clean[key] = value
            
            report['session_summary'] = session_stats_clean
            
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"最終レポートを保存: {report_path}")
            
        except Exception as e:
            logger.error(f"最終レポート保存エラー: {e}")

def parse_arguments():
    """コマンドライン引数解析"""
    parser = argparse.ArgumentParser(
        description='自動撮影システム - DeepLabCut学習用データ収集',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  %(prog)s                           # デフォルト設定で開始
  %(prog)s --duration 3600           # 1時間限定で実行
  %(prog)s --config custom.yaml      # カスタム設定ファイル使用
  %(prog)s --test --duration 300     # 5分間のテスト実行
  %(prog)s --manual-trigger          # 手動撮影テスト
        """
    )
    
    parser.add_argument(
        '--config', 
        type=str, 
        help='設定ファイルパス (デフォルト: hamster_config.yaml)'
    )
    
    parser.add_argument(
        '--duration', 
        type=int, 
        help='実行時間（秒）。指定しない場合は無制限'
    )
    
    parser.add_argument(
        '--test', 
        action='store_true', 
        help='テストモード（短時間実行、画面表示有効）'
    )
    
    parser.add_argument(
        '--manual-trigger', 
        action='store_true', 
        help='手動撮影テスト（システムを起動せずに1回撮影）'
    )
    
    parser.add_argument(
        '--verbose', 
        action='store_true', 
        help='詳細ログ出力'
    )
    
    parser.add_argument(
        '--log-file', 
        type=str, 
        default='auto_capture.log',
        help='ログファイル名 (デフォルト: auto_capture.log)'
    )
    
    return parser.parse_args()

def setup_logging(verbose: bool, log_file: str):
    """ログ設定"""
    log_level = logging.DEBUG if verbose else logging.INFO
    
    # 既存のハンドラを削除
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 新しいハンドラ設定
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # ファイルハンドラ
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # コンソールハンドラ
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    root_logger.setLevel(log_level)

def manual_capture_test(config: HamsterTrackingConfig):
    """手動撮影テスト"""
    logger.info("=== 手動撮影テスト ===")
    
    try:
        capture_system = AutoCaptureSystem(config)
        quality_assessor = DataQualityAssessor(config)
        
        capture_system.start()
        
        # 撮影実行
        logger.info("撮影を実行中...")
        capture_system.trigger_capture("manual", {"test": True})
        
        # 結果待機
        time.sleep(5)
        
        # 最新の撮影結果を取得
        recent_captures = capture_system.get_recent_captures(1)
        if recent_captures and recent_captures[0].success:
            result = recent_captures[0]
            logger.info(f"✅ 撮影成功: {result.filename}")
            logger.info(f"品質スコア: {result.quality_score:.2f}")
            logger.info(f"ファイルパス: {result.file_path}")
            
            # 詳細品質評価
            if os.path.exists(result.file_path):
                import cv2
                image = cv2.imread(result.file_path)
                if image is not None:
                    quality_metrics = quality_assessor.evaluate_image_quality(image, result.file_path)
                    logger.info(f"詳細品質評価: {quality_metrics.quality_level.value}")
                    logger.info(f"総合スコア: {quality_metrics.overall_score:.3f}")
                    logger.info(f"ブラー: {quality_metrics.blur_score:.3f}")
                    logger.info(f"輝度: {quality_metrics.brightness_score:.3f}")
                    logger.info(f"ハムスター可視性: {quality_metrics.hamster_visibility_score:.3f}")
        else:
            logger.error("❌ 撮影失敗")
        
        capture_system.stop()
        
    except Exception as e:
        logger.error(f"手動撮影テストエラー: {e}")
        import traceback
        traceback.print_exc()

def main():
    """メイン関数"""
    args = parse_arguments()
    
    # ログ設定
    setup_logging(args.verbose, args.log_file)
    
    logger.info("=== 自動撮影システム起動 ===")
    logger.info(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"引数: {vars(args)}")
    
    try:
        # 設定読み込み
        config = load_config(args.config) if args.config else load_config()
        logger.info(f"設定ファイル読み込み完了: {config.storage_base_dir}")
        
        # 手動撮影テストの場合
        if args.manual_trigger:
            manual_capture_test(config)
            return
        
        # 統合システム初期化
        system = IntegratedCaptureSystem(config, test_mode=args.test)
        
        if not system.initialize_components():
            logger.error("システム初期化失敗")
            return
        
        # テストモードの場合はデフォルト実行時間を短縮
        duration = args.duration
        if args.test and duration is None:
            duration = 600  # テストモードは10分制限
            logger.info("テストモード: 実行時間を10分に制限")
        
        # システム開始
        system.start(duration)
        
    except KeyboardInterrupt:
        logger.info("ユーザーによる中断")
    except Exception as e:
        logger.error(f"システムエラー: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logger.info("=== 自動撮影システム終了 ===")

if __name__ == "__main__":
    main()