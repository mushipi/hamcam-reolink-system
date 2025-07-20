#!/usr/bin/env python3
"""
映像表示アプリケーション
RTSPストリームからの映像をリアルタイム表示
"""

import cv2
import time
import logging
import argparse
from datetime import datetime
from rtsp_stream import RTSPStream
from utils.camera_config import get_camera_config, prompt_password_if_needed

class VideoViewer:
    """映像表示クラス"""
    
    def __init__(self, stream_type: str = "sub", window_name: str = "Reolink Camera"):
        """
        映像表示を初期化
        
        Args:
            stream_type: "main" または "sub"
            window_name: 表示ウィンドウ名
        """
        self.stream_type = stream_type
        self.window_name = window_name
        self.config = get_camera_config()
        
        # ストリーム
        self.stream = RTSPStream(stream_type)
        
        # 表示状態
        self.is_displaying = False
        self.show_info = True
        self.show_stats = False
        
        # 統計情報
        self.display_fps = 0
        self.last_display_time = time.time()
        self.display_frame_count = 0
        
        # ログ設定
        self.logger = logging.getLogger("VideoViewer")
    
    def start_display(self):
        """映像表示開始"""
        if not self.config.validate():
            prompt_password_if_needed()
        
        # ストリーム開始
        if not self.stream.start_stream():
            self.logger.error("ストリーム開始失敗")
            return False
        
        # OpenCVウィンドウ設定
        cv2.namedWindow(self.window_name, cv2.WINDOW_AUTOSIZE)
        
        self.is_displaying = True
        self.logger.info(f"映像表示開始: {self.stream_type}ストリーム")
        
        try:
            self._display_loop()
        except KeyboardInterrupt:
            self.logger.info("ユーザーによる中断")
        finally:
            self.stop_display()
        
        return True
    
    def stop_display(self):
        """映像表示停止"""
        self.is_displaying = False
        self.stream.stop_stream()
        cv2.destroyAllWindows()
        self.logger.info("映像表示停止")
    
    def _display_loop(self):
        """映像表示メインループ"""
        while self.is_displaying:
            # フレーム取得
            result = self.stream.get_frame(timeout=0.1)
            if not result or not result[0]:
                continue
            
            _, frame = result
            
            # 情報表示
            if self.show_info:
                frame = self._add_info_overlay(frame)
            
            # フレーム表示
            cv2.imshow(self.window_name, frame)
            
            # 統計更新
            self._update_display_stats()
            
            # キー入力処理
            key = cv2.waitKey(1) & 0xFF
            if not self._handle_key_input(key):
                break
    
    def _add_info_overlay(self, frame):
        """フレームに情報オーバーレイを追加"""
        overlay_frame = frame.copy()
        
        # 基本情報
        info_lines = [
            f"Stream: {self.stream_type.upper()}",
            f"Resolution: {frame.shape[1]}x{frame.shape[0]}",
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ]
        
        # 統計情報（オプション）
        if self.show_stats:
            stream_stats = self.stream.get_stats()
            info_lines.extend([
                f"Stream FPS: {stream_stats['current_fps']:.1f}",
                f"Display FPS: {self.display_fps:.1f}",
                f"Dropped: {stream_stats['dropped_frames']}"
            ])
        
        # テキスト描画
        y_offset = 30
        for line in info_lines:
            cv2.putText(overlay_frame, line, (10, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            y_offset += 25
        
        # 操作ヘルプ
        help_text = "Press: 'q'-Quit, 'i'-Info, 's'-Stats, 'f'-Fullscreen"
        cv2.putText(overlay_frame, help_text, (10, frame.shape[0] - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        return overlay_frame
    
    def _update_display_stats(self):
        """表示統計情報更新"""
        self.display_frame_count += 1
        current_time = time.time()
        
        if current_time - self.last_display_time >= 1.0:
            self.display_fps = self.display_frame_count / (current_time - self.last_display_time)
            self.display_frame_count = 0
            self.last_display_time = current_time
    
    def _handle_key_input(self, key) -> bool:
        """
        キー入力処理
        
        Returns:
            True: 継続, False: 終了
        """
        if key == ord('q') or key == 27:  # 'q' または ESC
            return False
        elif key == ord('i'):  # 情報表示切り替え
            self.show_info = not self.show_info
            self.logger.info(f"情報表示: {'ON' if self.show_info else 'OFF'}")
        elif key == ord('s'):  # 統計表示切り替え
            self.show_stats = not self.show_stats
            self.logger.info(f"統計表示: {'ON' if self.show_stats else 'OFF'}")
        elif key == ord('f'):  # フルスクリーン切り替え
            self._toggle_fullscreen()
        elif key == ord('r'):  # リセット
            self._reset_stream()
        
        return True
    
    def _toggle_fullscreen(self):
        """フルスクリーン表示切り替え"""
        # 現在のウィンドウプロパティを取得
        current_prop = cv2.getWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN)
        
        if current_prop == cv2.WINDOW_FULLSCREEN:
            cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_AUTOSIZE)
            self.logger.info("ウィンドウモード")
        else:
            cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            self.logger.info("フルスクリーンモード")
    
    def _reset_stream(self):
        """ストリームリセット"""
        self.logger.info("ストリームをリセット中...")
        self.stream.stop_stream()
        time.sleep(1)
        self.stream.start_stream()

class AdvancedVideoViewer(VideoViewer):
    """高機能映像表示クラス"""
    
    def __init__(self, stream_type: str = "sub", enable_recording: bool = False):
        super().__init__(stream_type)
        self.enable_recording = enable_recording
        self.is_recording = False
        self.video_writer = None
        self.recording_start_time = None
    
    def _handle_key_input(self, key) -> bool:
        """拡張キー入力処理"""
        # 基本処理
        if not super()._handle_key_input(key):
            return False
        
        # 録画機能
        if self.enable_recording:
            if key == ord('r') and not self.is_recording:
                self._start_recording()
            elif key == ord('t') and self.is_recording:
                self._stop_recording()
        
        return True
    
    def _start_recording(self):
        """録画開始"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.config.output_dir}/{self.config.recordings_dir}/recording_{timestamp}.mp4"
            
            # 解像度取得
            result = self.stream.get_current_frame()
            if not result or not result[0]:
                self.logger.error("録画用フレーム取得失敗")
                return
            
            _, frame = result
            height, width = frame.shape[:2]
            
            # VideoWriter設定
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.video_writer = cv2.VideoWriter(filename, fourcc, 15.0, (width, height))
            
            if self.video_writer.isOpened():
                self.is_recording = True
                self.recording_start_time = time.time()
                self.logger.info(f"録画開始: {filename}")
            else:
                self.logger.error("VideoWriter初期化失敗")
                
        except Exception as e:
            self.logger.error(f"録画開始エラー: {e}")
    
    def _stop_recording(self):
        """録画停止"""
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
            
            duration = time.time() - self.recording_start_time
            self.logger.info(f"録画停止 - 録画時間: {duration:.1f}秒")
        
        self.is_recording = False
        self.recording_start_time = None
    
    def _add_info_overlay(self, frame):
        """録画状態を含む情報オーバーレイ"""
        overlay_frame = super()._add_info_overlay(frame)
        
        # 録画状態表示
        if self.enable_recording:
            if self.is_recording:
                recording_time = time.time() - self.recording_start_time
                cv2.circle(overlay_frame, (frame.shape[1] - 30, 30), 10, (0, 0, 255), -1)
                cv2.putText(overlay_frame, f"REC {recording_time:.0f}s", 
                           (frame.shape[1] - 100, 35),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                
                # フレームを録画
                if self.video_writer:
                    self.video_writer.write(frame)
        
        return overlay_frame

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="Reolink Camera Video Viewer")
    parser.add_argument("-s", "--stream", choices=["main", "sub"], default="sub",
                       help="ストリームタイプ (default: sub)")
    parser.add_argument("-r", "--record", action="store_true",
                       help="録画機能を有効化")
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="詳細ログ出力")
    
    args = parser.parse_args()
    
    # ログ設定
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, 
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 映像表示開始
    if args.record:
        viewer = AdvancedVideoViewer(args.stream, enable_recording=True)
        print("録画機能有効 - 'r'キーで録画開始、't'キーで録画停止")
    else:
        viewer = VideoViewer(args.stream)
    
    print(f"映像表示開始 ({args.stream}ストリーム)")
    print("操作: 'q'-終了, 'i'-情報表示切替, 's'-統計表示切替, 'f'-フルスクリーン")
    
    viewer.start_display()

if __name__ == "__main__":
    main()