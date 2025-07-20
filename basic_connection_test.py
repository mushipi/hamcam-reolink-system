#!/usr/bin/env python3
"""
RLC-510A カメラ基本接続テストスクリプト
"""

from reolinkapi import Camera
import sys
import traceback

def test_camera_connection():
    """カメラへの基本接続をテストする"""
    
    # カメラ設定
    camera_ip = "192.168.31.85"
    username = "admin"
    
    # パスワード入力（実際の運用では環境変数から取得推奨）
    password = input(f"カメラ {camera_ip} のパスワードを入力してください: ")
    
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
                device_info = camera.get_device_info()
                print(f"デバイス名: {device_info.get('name', 'N/A')}")
                print(f"モデル: {device_info.get('model', 'N/A')}")
                print(f"ファームウェア: {device_info.get('firmVer', 'N/A')}")
                print(f"ハードウェア: {device_info.get('hardVer', 'N/A')}")
                print(f"UID: {device_info.get('uid', 'N/A')}")
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
    
    camera_ip = "192.168.31.85"
    
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