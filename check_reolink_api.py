#!/usr/bin/env python3
"""
Reolink API機能確認スクリプト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from reolinkapi import Camera

def check_api_methods():
    """APIメソッド確認"""
    print("=== Reolink API メソッド確認 ===")
    
    camera_ip = "192.168.31.85"
    username = "admin"
    password = "894890abc"
    
    try:
        camera = Camera(camera_ip, username, password)
        
        print("認証中...")
        if camera.login():
            print("✅ 認証成功")
            
            # 利用可能なメソッドを確認
            methods = [method for method in dir(camera) if not method.startswith('_')]
            print(f"\n利用可能なメソッド数: {len(methods)}")
            
            # 情報取得系メソッドをテスト
            info_methods = [
                'get_device_general', 'get_device_name', 'get_system_version',
                'get_network_general', 'get_system_general', 'get_hdd_info',
                'get_encoding', 'get_motion_detection', 'get_ai_config',
                'get_snap'
            ]
            
            print("\n=== 情報取得メソッドテスト ===")
            results = {}
            
            for method_name in info_methods:
                if hasattr(camera, method_name):
                    try:
                        method = getattr(camera, method_name)
                        result = method()
                        results[method_name] = result
                        print(f"✅ {method_name}: 成功")
                        
                        # 結果の一部を表示
                        if isinstance(result, dict):
                            if 'name' in result:
                                print(f"   name: {result['name']}")
                            if 'model' in result:
                                print(f"   model: {result['model']}")
                            if 'firmVer' in result:
                                print(f"   firmware: {result['firmVer']}")
                        elif isinstance(result, list) and result:
                            print(f"   type: list, length: {len(result)}")
                        elif isinstance(result, bytes):
                            print(f"   type: bytes, size: {len(result)} bytes")
                        
                    except Exception as e:
                        print(f"❌ {method_name}: エラー - {e}")
                        results[method_name] = None
                else:
                    print(f"⚠️  {method_name}: メソッド存在せず")
                    results[method_name] = None
            
            # デバイス情報取得
            print("\n=== デバイス基本情報 ===")
            try:
                device_general = camera.get_device_general()
                if device_general:
                    print(f"デバイス名: {device_general.get('name', 'N/A')}")
                    print(f"モデル: {device_general.get('model', 'N/A')}")
                    print(f"UID: {device_general.get('uid', 'N/A')}")
            except Exception as e:
                print(f"デバイス情報取得エラー: {e}")
            
            # システム情報取得
            try:
                system_version = camera.get_system_version()
                if system_version:
                    print(f"ファームウェア: {system_version.get('firmVer', 'N/A')}")
                    print(f"ハードウェア: {system_version.get('hardVer', 'N/A')}")
                    print(f"構築時間: {system_version.get('buildDay', 'N/A')}")
            except Exception as e:
                print(f"システム情報取得エラー: {e}")
            
            # スナップショット取得テスト
            print("\n=== スナップショット取得テスト ===")
            try:
                snap_data = camera.get_snap()
                if snap_data:
                    print(f"✅ スナップショット取得成功: {len(snap_data)} bytes")
                    
                    # ファイル保存テスト
                    filename = "api_test_snapshot.jpg"
                    with open(filename, 'wb') as f:
                        f.write(snap_data)
                    print(f"✅ ファイル保存成功: {filename}")
                else:
                    print("❌ スナップショット取得失敗（データなし）")
            except Exception as e:
                print(f"❌ スナップショット取得エラー: {e}")
            
            camera.logout()
            print("\n✅ API確認完了")
            return True
            
        else:
            print("❌ 認証失敗")
            return False
            
    except Exception as e:
        print(f"❌ API確認エラー: {e}")
        return False

if __name__ == "__main__":
    check_api_methods()