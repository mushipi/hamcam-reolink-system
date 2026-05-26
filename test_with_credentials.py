#!/usr/bin/env python3
"""
認証情報付きテストスクリプト
.env ファイルに以下を設定してください:
  CAMERA_IP, CAMERA_USER, CAMERA_PASSWORD
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from reolinkapi import Camera
from utils.camera_config import get_camera_config
import time

CAMERA_IP       = os.environ.get('CAMERA_IP', '192.168.x.x')
CAMERA_USER     = os.environ.get('CAMERA_USER', 'admin')
CAMERA_PASSWORD = os.environ.get('CAMERA_PASSWORD', '')

def test_direct_connection():
    print("=== 直接接続テスト ===")
    try:
        camera = Camera(CAMERA_IP, CAMERA_USER, CAMERA_PASSWORD)
        print("認証中...")
        if camera.login():
            print("✅ API認証成功")
            try:
                device_info = camera.get_device_info()
                print("✅ デバイス情報取得成功")
                print(f"  デバイス名: {device_info.get('name', 'N/A')}")
                print(f"  モデル: {device_info.get('model', 'N/A')}")
                print(f"  ファームウェア: {device_info.get('firmVer', 'N/A')}")
            except Exception as e:
                print(f"⚠️  デバイス情報取得エラー: {e}")
            camera.logout()
            return True
        else:
            print("❌ API認証失敗")
            return False
    except Exception as e:
        print(f"❌ 接続エラー: {e}")
        return False

def test_rtsp_with_credentials():
    print("\n=== RTSP接続テスト ===")
    try:
        from rtsp_stream import RTSPStream
        config = get_camera_config()
        config.set_password(CAMERA_PASSWORD)
        with RTSPStream("sub", buffer_size=1) as stream:
            if stream.start_stream():
                print("✅ RTSPストリーム開始成功")
                for i in range(10):
                    result = stream.get_frame(timeout=1.0)
                    if result and result[0]:
                        _, frame = result
                        print(f"フレーム {i+1}: {frame.shape}")
                        break
                    time.sleep(0.1)
                stats = stream.get_stats()
                print(f"統計: FPS={stats['current_fps']:.1f}, ドロップ={stats['dropped_frames']}")
                return True
            else:
                print("❌ RTSPストリーム開始失敗")
                return False
    except Exception as e:
        print(f"❌ RTSPテストエラー: {e}")
        return False

def test_snapshot_with_credentials():
    print("\n=== スナップショット接続テスト ===")
    try:
        from snapshot import SnapshotCapture
        config = get_camera_config()
        config.set_password(CAMERA_PASSWORD)
        capture = SnapshotCapture("api")
        if capture.initialize():
            filepath = capture.capture_snapshot("connection_test.jpg")
            if filepath:
                print(f"✅ スナップショット撮影成功: {os.path.basename(filepath)}")
                if os.path.exists(filepath):
                    print(f"  ファイルサイズ: {os.path.getsize(filepath)/1024:.1f} KB")
                capture.cleanup()
                return True
            else:
                print("❌ スナップショット撮影失敗")
                capture.cleanup()
                return False
        else:
            print("❌ スナップショット初期化失敗")
            return False
    except Exception as e:
        print(f"❌ スナップショットエラー: {e}")
        return False

def main():
    print("=== RLC-510A 接続テスト ===\n")
    if not CAMERA_PASSWORD:
        print("⚠️  CAMERA_PASSWORD が未設定です。.env を確認してください。")
        return

    tests = [
        ("直接API接続", test_direct_connection),
        ("RTSPストリーム", test_rtsp_with_credentials),
        ("スナップショット", test_snapshot_with_credentials)
    ]
    results = []
    for test_name, test_func in tests:
        print(f"{'='*50}")
        try:
            result = test_func()
            results.append(result)
            print(f"\n{test_name}: {'✅ 成功' if result else '❌ 失敗'}")
        except Exception as e:
            print(f"\n{test_name}: ❌ エラー - {e}")
            results.append(False)
        time.sleep(1)

    print(f"\n{'='*50}")
    print(f"成功: {sum(results)}/{len(results)} テスト")

if __name__ == "__main__":
    main()