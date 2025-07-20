#!/usr/bin/env python3
"""
カメラ設定管理モジュール
設定情報を一元管理し、各スクリプトから参照可能にする
"""

import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class CameraConfig:
    """カメラ設定データクラス"""
    ip: str = "192.168.31.85"
    username: str = "admin"
    password: Optional[str] = None
    
    # RTSP設定
    rtsp_port: int = 554
    http_port: int = 80
    
    # ストリーム設定
    main_stream_path: str = "h264Preview_01_main"
    sub_stream_path: str = "h264Preview_01_sub"
    
    # 映像設定
    main_resolution: tuple = (2560, 1920)  # 5MP
    sub_resolution: tuple = (640, 480)     # VGA
    target_fps: int = 15
    
    # 録画設定
    video_codec: str = "mp4v"  # または "XVID"
    video_extension: str = ".mp4"
    image_extension: str = ".jpg"
    
    # 出力ディレクトリ
    output_dir: str = "output"
    snapshots_dir: str = "snapshots"
    recordings_dir: str = "recordings"
    logs_dir: str = "logs"
    
    def __post_init__(self):
        """初期化後処理"""
        # 出力ディレクトリの作成
        for directory in [self.output_dir, 
                         os.path.join(self.output_dir, self.snapshots_dir),
                         os.path.join(self.output_dir, self.recordings_dir),
                         os.path.join(self.output_dir, self.logs_dir)]:
            os.makedirs(directory, exist_ok=True)
    
    def get_rtsp_url(self, stream_type: str = "main") -> str:
        """RTSPストリームURLを取得"""
        if not self.password:
            raise ValueError("パスワードが設定されていません")
        
        if stream_type == "main":
            stream_path = self.main_stream_path
        elif stream_type == "sub":
            stream_path = self.sub_stream_path
        else:
            raise ValueError(f"無効なストリームタイプ: {stream_type}")
        
        return f"rtsp://{self.username}:{self.password}@{self.ip}:{self.rtsp_port}/{stream_path}"
    
    def get_resolution(self, stream_type: str = "main") -> tuple:
        """指定ストリームの解像度を取得"""
        if stream_type == "main":
            return self.main_resolution
        elif stream_type == "sub":
            return self.sub_resolution
        else:
            raise ValueError(f"無効なストリームタイプ: {stream_type}")
    
    def set_password(self, password: str):
        """パスワードを設定"""
        self.password = password
    
    @classmethod
    def from_env(cls) -> 'CameraConfig':
        """環境変数から設定を読み込み"""
        config = cls()
        
        # 環境変数から設定を上書き
        config.ip = os.getenv('CAMERA_IP', config.ip)
        config.username = os.getenv('CAMERA_USERNAME', config.username)
        config.password = os.getenv('CAMERA_PASSWORD', config.password)
        
        return config
    
    def validate(self) -> bool:
        """設定の妥当性をチェック"""
        if not self.password:
            return False
        
        if not self.ip or not self.username:
            return False
        
        return True

# グローバル設定インスタンス（環境変数から初期化）
camera_config = CameraConfig.from_env()

def get_camera_config() -> CameraConfig:
    """カメラ設定を取得"""
    return camera_config

def prompt_password_if_needed():
    """必要に応じてパスワードの入力を求める"""
    if not camera_config.password:
        camera_config.password = input(f"カメラ {camera_config.ip} のパスワードを入力してください: ")

if __name__ == "__main__":
    # 設定テスト
    config = get_camera_config()
    prompt_password_if_needed()
    
    print("=== カメラ設定 ===")
    print(f"IP: {config.ip}")
    print(f"ユーザー名: {config.username}")
    print(f"パスワード: {'*' * len(config.password) if config.password else '未設定'}")
    print(f"メインストリームURL: {config.get_rtsp_url('main') if config.password else '(パスワード未設定)'}")
    print(f"サブストリームURL: {config.get_rtsp_url('sub') if config.password else '(パスワード未設定)'}")
    print(f"設定有効: {config.validate()}")