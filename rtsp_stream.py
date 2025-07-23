#!/usr/bin/env python3
"""
RTSPストリーム基本クラス
Reolink RLC-510Aからの映像ストリーミング機能を提供
"""

import cv2
import time
import threading
import queue
import logging
from typing import Optional, Callable
from utils.camera_config import get_camera_config, prompt_password_if_needed

class RTSPStream:
    """RTSPストリーム管理クラス"""
    
    def __init__(self, stream_type: str = "main", buffer_size: int = 1):
        """
        RTSPストリームを初期化
        
        Args:
            stream_type: "main" または "sub"
            buffer_size: フレームバッファサイズ
        """
        self.config = get_camera_config()
        self.stream_type = stream_type
        self.buffer_size = buffer_size
        
        # ストリーム状態
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_running = False
        self.is_connected = False
        
        # フレームバッファ
        self.frame_queue = queue.Queue(maxsize=buffer_size)
        self.current_frame = None
        self.frame_lock = threading.Lock()
        
        # 統計情報
        self.frame_count = 0
        self.dropped_frames = 0
        self.last_fps_time = time.time()
        self.current_fps = 0
        
        # コールバック
        self.on_frame_callback: Optional[Callable] = None
        self.on_error_callback: Optional[Callable] = None
        
        # ログ設定
        self.logger = logging.getLogger(f"RTSPStream-{stream_type}")
        
    def connect(self) -> bool:
        """RTSPストリームに接続"""
        try:
            if not self.config.validate():
                prompt_password_if_needed()
                
            rtsp_url = self.config.get_rtsp_url(self.stream_type)
            self.logger.info(f"RTSP接続開始: {rtsp_url}")
            
            # VideoCapture設定
            self.cap = cv2.VideoCapture(rtsp_url)
            
            # OpenCV設定
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, self.buffer_size)
            self.cap.set(cv2.CAP_PROP_FPS, self.config.target_fps)
            
            # 接続テスト
            ret, frame = self.cap.read()
            if ret and frame is not None:
                self.is_connected = True
                self.current_frame = frame
                self.logger.info(f"RTSP接続成功 - 解像度: {frame.shape[:2]}")
                return True
            else:
                self.logger.error("RTSPストリームからフレーム取得失敗")
                self._cleanup()
                return False
                
        except Exception as e:
            self.logger.error(f"RTSP接続エラー: {e}")
            self._cleanup()
            return False
    
    def start_stream(self) -> bool:
        """ストリーミング開始"""
        if not self.is_connected:
            if not self.connect():
                return False
        
        self.is_running = True
        self.stream_thread = threading.Thread(target=self._stream_worker, daemon=True)
        self.stream_thread.start()
        
        self.logger.info("ストリーミング開始")
        return True
    
    def stop_stream(self):
        """ストリーミング停止"""
        self.is_running = False
        
        if hasattr(self, 'stream_thread'):
            self.stream_thread.join(timeout=5)
        
        self._cleanup()
        self.logger.info("ストリーミング停止")
    
    def _stream_worker(self):
        """ストリーミング処理ワーカー"""
        retry_count = 0
        max_retries = 5
        
        while self.is_running:
            try:
                if not self.cap or not self.cap.isOpened():
                    if retry_count >= max_retries:
                        self.logger.error("最大再試行回数に達しました")
                        break
                    
                    self.logger.warning(f"再接続試行 {retry_count + 1}/{max_retries}")
                    if not self.connect():
                        retry_count += 1
                        time.sleep(1)
                        continue
                
                ret, frame = self.cap.read()
                
                if ret and frame is not None:
                    retry_count = 0  # 成功時にリセット
                    self._update_frame(frame)
                    self._update_statistics()
                    
                    # コールバック実行
                    if self.on_frame_callback:
                        try:
                            self.on_frame_callback(frame.copy())
                        except Exception as e:
                            self.logger.error(f"フレームコールバックエラー: {e}")
                
                else:
                    self.logger.warning("フレーム読み取り失敗")
                    retry_count += 1
                    time.sleep(0.1)
                    
            except Exception as e:
                self.logger.error(f"ストリーム処理エラー: {e}")
                if self.on_error_callback:
                    self.on_error_callback(e)
                retry_count += 1
                time.sleep(1)
    
    def _update_frame(self, frame):
        """フレーム更新"""
        with self.frame_lock:
            self.current_frame = frame
            
        # フレームバッファ更新
        try:
            self.frame_queue.put_nowait(frame)
        except queue.Full:
            try:
                self.frame_queue.get_nowait()  # 古いフレームを削除
                self.frame_queue.put_nowait(frame)
                self.dropped_frames += 1
            except queue.Empty:
                pass
    
    def _update_statistics(self):
        """統計情報更新"""
        self.frame_count += 1
        
        # FPS計算（1秒間隔）
        current_time = time.time()
        if current_time - self.last_fps_time >= 1.0:
            self.current_fps = self.frame_count / (current_time - self.last_fps_time)
            self.frame_count = 0
            self.last_fps_time = current_time
    
    def get_frame(self, timeout: float = 1.0) -> Optional[tuple]:
        """
        最新フレームを取得
        
        Returns:
            (success, frame) または None
        """
        if not self.is_running:
            return None
            
        try:
            frame = self.frame_queue.get(timeout=timeout)
            return (True, frame)
        except queue.Empty:
            with self.frame_lock:
                if self.current_frame is not None:
                    return (True, self.current_frame.copy())
            return (False, None)
    
    def get_current_frame(self) -> Optional[tuple]:
        """
        現在のフレームを取得（非ブロッキング）
        
        Returns:
            (success, frame) または None
        """
        with self.frame_lock:
            if self.current_frame is not None:
                return (True, self.current_frame.copy())
        return (False, None)
    
    def get_stats(self) -> dict:
        """統計情報を取得"""
        return {
            'is_connected': self.is_connected,
            'is_running': self.is_running,
            'current_fps': self.current_fps,
            'dropped_frames': self.dropped_frames,
            'stream_type': self.stream_type,
            'resolution': self.config.get_resolution(self.stream_type)
        }
    
    def set_frame_callback(self, callback: Callable):
        """フレーム受信コールバックを設定"""
        self.on_frame_callback = callback
    
    def set_error_callback(self, callback: Callable):
        """エラーコールバックを設定"""
        self.on_error_callback = callback
    
    def _cleanup(self):
        """リソースクリーンアップ"""
        self.is_connected = False
        
        if self.cap:
            self.cap.release()
            self.cap = None
        
        # キューをクリア
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                break
    
    def __enter__(self):
        """コンテキストマネージャー対応"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャー対応"""
        self.stop_stream()

if __name__ == "__main__":
    # ログ設定
    logging.basicConfig(level=logging.INFO)
    
    # パスワードを事前設定
    config = get_camera_config()
    if not config.password:
        config.set_password("894890abc")
    
    # RTSPストリームテスト
    print("=== RTSPストリーム基本テスト ===")
    
    try:
        with RTSPStream("sub") as stream:  # サブストリームでテスト
            if stream.start_stream():
                print("ストリーミング開始成功")
                
                # 10秒間テスト
                for i in range(100):
                    result = stream.get_frame(timeout=0.5)
                    if result and result[0]:
                        _, frame = result
                        print(f"フレーム {i+1}: {frame.shape} - FPS: {stream.current_fps:.1f}")
                    else:
                        print(f"フレーム {i+1}: 取得失敗")
                    
                    time.sleep(0.1)
                
                print(f"\n統計情報: {stream.get_stats()}")
            else:
                print("ストリーミング開始失敗")
                
    except KeyboardInterrupt:
        print("\n中断されました")
    except Exception as e:
        print(f"エラー: {e}")