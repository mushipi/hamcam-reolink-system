#!/usr/bin/env python3
"""
動作するAPI機能テスト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from reolinkapi import Camera
import json

def test_working_api():
    """動作するAPI機能テスト"""
    print("=== 動作するAPI機能テスト ===")
    
    camera_ip = "192.168.31.85"
    username = "admin"
    password = "894890abc"
    
    try:
        camera = Camera(camera_ip, username, password)
        
        if camera.login():
            print("✅ 認証成功\n")
            
            # 1. システム情報取得
            print("=== システム情報取得 ===")
            try:
                system_info = camera.get_general_system()
                if system_info:
                    print("✅ システム情報取得成功")
                    print(json.dumps(system_info, indent=2, ensure_ascii=False))
            except Exception as e:
                print(f"❌ システム情報取得エラー: {e}")
            
            # 2. デバイス情報取得
            print("\n=== デバイス情報取得 ===")
            try:
                device_info = camera.get_information()
                if device_info:
                    print("✅ デバイス情報取得成功")
                    print(json.dumps(device_info, indent=2, ensure_ascii=False))
            except Exception as e:
                print(f"❌ デバイス情報取得エラー: {e}")
            
            # 3. ネットワーク情報取得（詳細）
            print("\n=== ネットワーク情報取得 ===")
            try:
                network_info = camera.get_network_general()
                if network_info:
                    print("✅ ネットワーク情報取得成功")
                    print(json.dumps(network_info, indent=2, ensure_ascii=False))
            except Exception as e:
                print(f"❌ ネットワーク情報取得エラー: {e}")
            
            # 4. 録画エンコード設定
            print("\n=== 録画エンコード設定取得 ===")
            try:
                encoding_info = camera.get_recording_encoding()
                if encoding_info:
                    print("✅ エンコード設定取得成功")
                    print(json.dumps(encoding_info, indent=2, ensure_ascii=False))
            except Exception as e:
                print(f"❌ エンコード設定取得エラー: {e}")
            
            # 5. モーションアラーム設定
            print("\n=== モーションアラーム設定取得 ===")
            try:
                motion_info = camera.get_alarm_motion()
                if motion_info:
                    print("✅ モーション設定取得成功")
                    print(json.dumps(motion_info, indent=2, ensure_ascii=False))
            except Exception as e:
                print(f"❌ モーション設定取得エラー: {e}")
            
            # 6. OSD設定（画面表示）
            print("\n=== OSD設定取得 ===")
            try:
                osd_info = camera.get_osd()
                if osd_info:
                    print("✅ OSD設定取得成功")
                    print(json.dumps(osd_info, indent=2, ensure_ascii=False))
            except Exception as e:
                print(f"❌ OSD設定取得エラー: {e}")
            
            camera.logout()
            print("\n✅ API機能テスト完了")
            return True
            
        else:
            print("❌ 認証失敗")
            return False
            
    except Exception as e:
        print(f"❌ APIテストエラー: {e}")
        return False

if __name__ == "__main__":
    test_working_api()