#!/usr/bin/env python3
"""
RLC-510A カメラ基本接続テストスクリプト
"""

from reolinkapi import Camera
import sys
import traceback

def test_camera_connection():
    """カメラへの基本接続をテストする"""
    
    # カメラ設定を読み込み
    from utils.camera_config import get_camera_config
    config = get_camera_config()
    
    # パスワードが設定されていない場合のみ設定
    if not config.password:
        config.set_password("894890abc")
    
    camera_ip = config.ip
    username = config.username
    password = config.password
    
    try:
        print(f"カメラ {camera_ip} への接続を試行中...")
        
        # カメラ接続
        camera = Camera(camera_ip, username, password)
        
        # 接続テスト
        print("認証中...")
        login_result = camera.login()
        
        if login_result:
            print("✅ カメラ接続成功!")
            
            # 基本情報取得テスト
            print("\n基本情報を取得中...")
            try:
                device_info = camera.get_information()
                if isinstance(device_info, list) and len(device_info) > 0:
                    info = device_info[0].get('value', {})
                    info = info.get('DevInfo', info)
                elif isinstance(device_info, dict):
                    info = device_info.get('value', device_info)
                    info = info.get('DevInfo', info) if isinstance(info, dict) else {}
                else:
                    info = {}
                
                print(f"デバイス名: {info.get('name', 'N/A')}")
                print(f"モデル: {info.get('model', 'N/A')}")
                print(f"ファームウェア: {info.get('firmVer', 'N/A')}")
                print(f"ハードウェア: {info.get('hardVer', 'N/A')}")
                print(f"UID: {info.get('uid', 'N/A')}")
                print(f"シリアル: {info.get('serial', 'N/A')}")
            except Exception as e:
                print(f"⚠️  デバイス情報取得エラー: {e}")
            
            # ログアウト
            camera.logout()
            print("\n✅ 接続テスト完了")
            return True
            
        else:
            print("❌ 認証失敗")
            return False
            
    except Exception as e:
        print(f"❌ 接続エラー: {e}")
        print(f"詳細: {traceback.format_exc()}")
        return False

def test_network_connectivity():
    """ネットワーク接続状況を確認"""
    import subprocess
    
    from utils.camera_config import get_camera_config
    config = get_camera_config()
    camera_ip = config.ip
    
    print("=== ネットワーク接続確認 ===")
    
    # ping テスト
    try:
        result = subprocess.run(['ping', '-c', '3', camera_ip], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Ping成功")
        else:
            print("❌ Ping失敗")
            print(result.stderr)
    except Exception as e:
        print(f"❌ Pingテストエラー: {e}")
    
    # ポートテスト
    ports = [80, 554]  # 8000は接続拒否されることが確認済み
    for port in ports:
        try:
            result = subprocess.run(['nc', '-zv', camera_ip, str(port)], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"✅ ポート {port} 接続可能")
            else:
                print(f"❌ ポート {port} 接続失敗")
        except Exception as e:
            print(f"❌ ポート {port} テストエラー: {e}")

if __name__ == "__main__":
    print("=== RLC-510A カメラ接続テスト ===\n")
    
    # ネットワーク接続確認
    test_network_connectivity()
    
    print("\n" + "="*50 + "\n")
    
    # カメラAPI接続テスト
    success = test_camera_connection()
    
    if success:
        print("\n🎉 すべてのテストが成功しました!")
        sys.exit(0)
    else:
        print("\n💀 接続テストが失敗しました")
        sys.exit(1)