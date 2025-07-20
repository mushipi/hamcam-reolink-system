#!/usr/bin/env python3
"""
認証情報付きテストスクリプト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from reolinkapi import Camera
from utils.camera_config import get_camera_config
import time

def test_direct_connection():
    """直接接続テスト"""
    print("=== 直接接続テスト ===")
    
    # 直接認証情報を設定
    camera_ip = "192.168.31.85"
    username = "admin"
    password = "894890abc"
    
    try:
        camera = Camera(camera_ip, username, password)
        
        print("認証中...")
        if camera.login():
            print("✅ API認証成功")
            
            # デバイス情報取得
            try:
                device_info = camera.get_device_info()
                print("✅ デバイス情報取得成功")
                print(f"  デバイス名: {device_info.get('name', 'N/A')}")
                print(f"  モデル: {device_info.get('model', 'N/A')}")
                print(f"  ファームウェア: {device_info.get('firmVer', 'N/A')}")
                print(f"  UID: {device_info.get('uid', 'N/A')}")
                print(f"  ハードウェア: {device_info.get('hardVer', 'N/A')}")
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
    """認証情報付きRTSPテスト"""
    print("\n=== RTSP接続テスト ===")
    
    try:
        from rtsp_stream import RTSPStream
        
        # 設定に認証情報を設定
        config = get_camera_config()
        config.set_password("894890abc")
        
        print("RTSPストリーム接続テスト...")
        with RTSPStream("sub", buffer_size=1) as stream:
            if stream.start_stream():
                print("✅ RTSPストリーム開始成功")
                
                # フレーム取得テスト
                for i in range(10):
                    result = stream.get_frame(timeout=1.0)
                    if result and result[0]:
                        _, frame = result
                        print(f"フレーム {i+1}: {frame.shape}")
                        if i == 0:  # 最初のフレームの詳細
                            print(f"  データタイプ: {frame.dtype}")
                            print(f"  サイズ: {frame.nbytes} bytes")
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
    """認証情報付きスナップショットテスト"""
    print("\n=== スナップショット接続テスト ===")
    
    try:
        from snapshot import SnapshotCapture
        
        # 設定に認証情報を設定
        config = get_camera_config()
        config.set_password("894890abc")
        
        print("API方式スナップショットテスト...")
        capture = SnapshotCapture("api")
        
        if capture.initialize():
            filepath = capture.capture_snapshot("connection_test.jpg")
            if filepath:
                print(f"✅ スナップショット撮影成功: {os.path.basename(filepath)}")
                
                # ファイル情報
                if os.path.exists(filepath):
                    size = os.path.getsize(filepath)
                    print(f"  ファイルサイズ: {size/1024:.1f} KB")
                    print(f"  保存先: {filepath}")
                
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
        print(f"❌ スナップショットテストエラー: {e}")
        return False

def main():
    print("=== RLC-510A 認証情報付き接続テスト ===\n")
    
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
    print("テスト結果サマリー")
    print(f"{'='*50}")
    
    success_count = sum(results)
    total_count = len(results)
    
    print(f"成功: {success_count}/{total_count} テスト")
    
    if success_count == total_count:
        print("🎉 すべての接続テストが成功しました！")
        print("システムは正常に動作しています。")
    elif success_count > 0:
        print("⚠️  一部のテストが失敗しましたが、基本機能は動作します")
    else:
        print("❌ すべてのテストが失敗しました")
        print("カメラの設定や接続を確認してください")

if __name__ == "__main__":
    main()