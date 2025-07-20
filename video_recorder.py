#!/usr/bin/env python3
"""
映像録画機能
RTSPストリームからの映像を録画・保存
"""

import cv2
import time
import threading
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from rtsp_stream import RTSPStream
from utils.camera_config import get_camera_config, prompt_password_if_needed

class VideoRecorder:
    """映像録画クラス"""
    
    def __init__(self, stream_type: str = "main", 
                 duration: int = None,
                 segment_duration: int = None):
        """
        映像録画を初期化
        
        Args:
            stream_type: "main" または "sub"
            duration: 録画時間（秒）。Noneで無制限
            segment_duration: セグメント時間（秒）。Noneで分割なし
        """
        self.stream_type = stream_type
        self.duration = duration
        self.segment_duration = segment_duration
        self.config = get_camera_config()
        
        # ストリーム
        self.stream = RTSPStream(stream_type, buffer_size=2)
        
        # 録画状態
        self.is_recording = False
        self.should_stop = False
        self.current_writer = None
        self.recording_thread = None
        
        # ファイル管理
        self.output_dir = Path(self.config.output_dir) / self.config.recordings_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.current_filename = None
        self.segment_start_time = None
        
        # 統計情報
        self.total_frames = 0
        self.total_bytes = 0
        self.recording_start_time = None
        self.segments_created = 0
        
        # ログ設定
        self.logger = logging.getLogger("VideoRecorder")
    
    def start_recording(self, filename_prefix: str = "recording") -> bool:
        """録画開始"""
        if self.is_recording:
            self.logger.warning("既に録画中です")
            return False
        
        if not self.config.validate():
            prompt_password_if_needed()
        
        # ストリーム開始
        if not self.stream.start_stream():
            self.logger.error("ストリーム開始失敗")
            return False
        
        # 録画設定
        self.should_stop = False
        self.filename_prefix = filename_prefix
        self.recording_start_time = time.time()
        self.segment_start_time = time.time()
        
        # 最初のファイル作成
        if not self._create_new_segment():
            return False
        
        # 録画スレッド開始
        self.is_recording = True
        self.recording_thread = threading.Thread(target=self._recording_worker, daemon=True)
        self.recording_thread.start()
        
        self.logger.info(f"録画開始: {self.current_filename}")
        return True
    
    def stop_recording(self):
        """録画停止"""
        if not self.is_recording:
            return
        
        self.should_stop = True
        
        # 録画スレッド終了待ち
        if self.recording_thread:
            self.recording_thread.join(timeout=10)
        
        # リソースクリーンアップ
        self._cleanup_recording()
        
        # 統計出力
        duration = time.time() - self.recording_start_time
        self.logger.info(f"録画完了 - 時間: {duration:.1f}秒, フレーム数: {self.total_frames}, セグメント数: {self.segments_created}")
    
    def _recording_worker(self):
        """録画処理ワーカー"""
        try:
            while self.is_recording and not self.should_stop:
                # 録画時間制限チェック
                if self.duration and (time.time() - self.recording_start_time) >= self.duration:
                    self.logger.info("録画時間制限に達しました")
                    break
                
                # セグメント分割チェック
                if (self.segment_duration and 
                    (time.time() - self.segment_start_time) >= self.segment_duration):
                    self._create_new_segment()
                
                # フレーム取得・録画
                result = self.stream.get_frame(timeout=1.0)
                if result and result[0]:
                    _, frame = result
                    if self.current_writer and self.current_writer.isOpened():
                        self.current_writer.write(frame)
                        self.total_frames += 1
                        
                        # 統計更新（近似）
                        self.total_bytes += frame.nbytes
                else:
                    self.logger.warning("フレーム取得失敗")
                    time.sleep(0.1)
        
        except Exception as e:
            self.logger.error(f"録画エラー: {e}")
        finally:
            self._cleanup_recording()
    
    def _create_new_segment(self) -> bool:
        """新しいセグメントファイルを作成"""
        # 前のライターを閉じる
        if self.current_writer:
            self.current_writer.release()
            self.current_writer = None
        
        # 新しいファイル名生成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if self.segment_duration:
            filename = f"{self.filename_prefix}_{timestamp}_seg{self.segments_created:03d}.mp4"
        else:
            filename = f"{self.filename_prefix}_{timestamp}.mp4"
        
        self.current_filename = self.output_dir / filename
        
        # VideoWriter作成
        try:
            # フレーム取得して解像度確認
            result = self.stream.get_current_frame()
            if not result or not result[0]:
                self.logger.error("解像度確認用フレーム取得失敗")
                return False
            
            _, frame = result
            height, width = frame.shape[:2]
            
            # VideoWriter設定
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.current_writer = cv2.VideoWriter(
                str(self.current_filename), 
                fourcc, 
                float(self.config.target_fps), 
                (width, height)
            )
            
            if not self.current_writer.isOpened():
                self.logger.error("VideoWriter初期化失敗")
                return False
            
            self.segments_created += 1
            self.segment_start_time = time.time()
            
            if self.segments_created > 1:
                self.logger.info(f"新しいセグメント作成: {filename}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"セグメント作成エラー: {e}")
            return False
    
    def _cleanup_recording(self):
        """録画リソースクリーンアップ"""
        self.is_recording = False
        
        if self.current_writer:
            self.current_writer.release()
            self.current_writer = None
        
        self.stream.stop_stream()
    
    def get_recording_stats(self) -> dict:
        """録画統計情報を取得"""
        if self.recording_start_time:
            duration = time.time() - self.recording_start_time
            fps = self.total_frames / duration if duration > 0 else 0
        else:
            duration = 0
            fps = 0
        
        return {
            'is_recording': self.is_recording,
            'duration': duration,
            'total_frames': self.total_frames,
            'average_fps': fps,
            'total_bytes': self.total_bytes,
            'segments_created': self.segments_created,
            'current_file': str(self.current_filename) if self.current_filename else None,
            'stream_stats': self.stream.get_stats()
        }

class ScheduledRecorder:
    """スケジュール録画クラス"""
    
    def __init__(self, stream_type: str = "main"):
        self.recorder = VideoRecorder(stream_type)
        self.schedule = []
        self.is_running = False
        self.scheduler_thread = None
        self.logger = logging.getLogger("ScheduledRecorder")
    
    def add_schedule(self, start_time: str, duration: int, 
                    filename_prefix: str = "scheduled"):
        """
        録画スケジュールを追加
        
        Args:
            start_time: 開始時刻 (HH:MM形式)
            duration: 録画時間（秒）
            filename_prefix: ファイル名プレフィックス
        """
        try:
            hour, minute = map(int, start_time.split(':'))
            self.schedule.append({
                'hour': hour,
                'minute': minute,
                'duration': duration,
                'prefix': filename_prefix
            })
            self.logger.info(f"録画スケジュール追加: {start_time} ({duration}秒)")
        except ValueError:
            self.logger.error(f"無効な時刻形式: {start_time}")
    
    def start_scheduler(self):
        """スケジューラー開始"""
        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_worker, daemon=True)
        self.scheduler_thread.start()
        self.logger.info("スケジューラー開始")
    
    def stop_scheduler(self):
        """スケジューラー停止"""
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join()
        self.recorder.stop_recording()
        self.logger.info("スケジューラー停止")
    
    def _scheduler_worker(self):
        """スケジューラーワーカー"""
        while self.is_running:
            now = datetime.now()
            current_time = (now.hour, now.minute)
            
            for schedule in self.schedule:
                schedule_time = (schedule['hour'], schedule['minute'])
                
                if current_time == schedule_time and not self.recorder.is_recording:
                    self.logger.info(f"スケジュール録画開始: {schedule['prefix']}")
                    self.recorder = VideoRecorder(self.recorder.stream_type, duration=schedule['duration'])
                    self.recorder.start_recording(schedule['prefix'])
                    break
            
            time.sleep(30)  # 30秒間隔でチェック

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="Reolink Camera Video Recorder")
    parser.add_argument("-s", "--stream", choices=["main", "sub"], default="main",
                       help="ストリームタイプ (default: main)")
    parser.add_argument("-d", "--duration", type=int,
                       help="録画時間（秒）")
    parser.add_argument("-g", "--segment", type=int,
                       help="セグメント時間（秒）")
    parser.add_argument("-o", "--output", default="recording",
                       help="出力ファイル名プレフィックス")
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="詳細ログ出力")
    
    args = parser.parse_args()
    
    # ログ設定
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level,
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 録画開始
    recorder = VideoRecorder(args.stream, args.duration, args.segment)
    
    print(f"映像録画開始 ({args.stream}ストリーム)")
    if args.duration:
        print(f"録画時間: {args.duration}秒")
    if args.segment:
        print(f"セグメント時間: {args.segment}秒")
    print("Ctrl+Cで停止")
    
    try:
        if recorder.start_recording(args.output):
            # 統計情報表示
            while recorder.is_recording:
                stats = recorder.get_recording_stats()
                print(f"\r録画中 - 時間: {stats['duration']:.1f}s, "
                      f"フレーム: {stats['total_frames']}, "
                      f"FPS: {stats['average_fps']:.1f}", end="")
                time.sleep(1)
        else:
            print("録画開始失敗")
    
    except KeyboardInterrupt:
        print("\n録画停止中...")
    finally:
        recorder.stop_recording()
        print("\n録画完了")

if __name__ == "__main__":
    main()