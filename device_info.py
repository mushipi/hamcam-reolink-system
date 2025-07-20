#!/usr/bin/env python3
"""
RLC-510A カメラデバイス情報取得スクリプト
詳細なデバイス情報、設定、状態を取得・表示する
"""

from reolinkapi import Camera
import json
import sys
import traceback
from datetime import datetime

def get_detailed_device_info(camera):
    """詳細なデバイス情報を取得"""
    info = {}
    
    try:
        # 基本デバイス情報
        device_info = camera.get_device_info()
        info['device_info'] = device_info
        print("✅ デバイス基本情報取得成功")
    except Exception as e:
        print(f"❌ デバイス基本情報取得失敗: {e}")
        info['device_info'] = None
    
    try:
        # ネットワーク情報
        network_info = camera.get_network_general()
        info['network_info'] = network_info
        print("✅ ネットワーク情報取得成功")
    except Exception as e:
        print(f"❌ ネットワーク情報取得失敗: {e}")
        info['network_info'] = None
    
    try:
        # ストレージ情報
        storage_info = camera.get_hdd_info()
        info['storage_info'] = storage_info
        print("✅ ストレージ情報取得成功")
    except Exception as e:
        print(f"❌ ストレージ情報取得失敗: {e}")
        info['storage_info'] = None
    
    try:
        # エンコード設定
        encoding_info = camera.get_encoding()
        info['encoding_info'] = encoding_info
        print("✅ エンコード設定取得成功")
    except Exception as e:
        print(f"❌ エンコード設定取得失敗: {e}")
        info['encoding_info'] = None
    
    try:
        # AI検知設定
        ai_info = camera.get_ai_config()
        info['ai_config'] = ai_info
        print("✅ AI設定取得成功")
    except Exception as e:
        print(f"❌ AI設定取得失敗: {e}")
        info['ai_config'] = None
    
    try:
        # モーション検知設定
        motion_info = camera.get_motion_detection()
        info['motion_detection'] = motion_info
        print("✅ モーション検知設定取得成功")
    except Exception as e:
        print(f"❌ モーション検知設定取得失敗: {e}")
        info['motion_detection'] = None
    
    return info

def format_device_info(info):
    """デバイス情報を整理して表示"""
    print("\n" + "="*60)
    print("           RLC-510A デバイス情報詳細")
    print("="*60)
    
    # 基本情報
    if info.get('device_info'):
        device = info['device_info']
        print(f"\n📱 基本情報:")
        print(f"  デバイス名: {device.get('name', 'N/A')}")
        print(f"  モデル: {device.get('model', 'N/A')}")
        print(f"  UID: {device.get('uid', 'N/A')}")
        print(f"  ファームウェア: {device.get('firmVer', 'N/A')}")
        print(f"  ハードウェア: {device.get('hardVer', 'N/A')}")
        print(f"  製造番号: {device.get('serial', 'N/A')}")
        print(f"  チャンネル数: {device.get('channelNum', 'N/A')}")
    
    # ネットワーク情報
    if info.get('network_info'):
        network = info['network_info']
        print(f"\n🌐 ネットワーク情報:")
        print(f"  IPアドレス: {network.get('ip', 'N/A')}")
        print(f"  サブネットマスク: {network.get('mask', 'N/A')}")
        print(f"  ゲートウェイ: {network.get('gateway', 'N/A')}")
        print(f"  DNS: {network.get('dns1', 'N/A')}")
        print(f"  MAC: {network.get('mac', 'N/A')}")
        print(f"  DHCP: {'有効' if network.get('dhcp') else '無効'}")
    
    # ストレージ情報
    if info.get('storage_info'):
        storage = info['storage_info']
        print(f"\n💾 ストレージ情報:")
        if isinstance(storage, list) and storage:
            for i, hdd in enumerate(storage):
                print(f"  ドライブ {i+1}:")
                print(f"    容量: {hdd.get('capacity', 'N/A')} GB")
                print(f"    使用量: {hdd.get('size', 'N/A')} GB")
                print(f"    状態: {hdd.get('status', 'N/A')}")
                print(f"    フォーマット: {hdd.get('format', 'N/A')}")
        else:
            print("  ストレージ情報なし")
    
    # エンコード設定
    if info.get('encoding_info'):
        encoding = info['encoding_info']
        print(f"\n🎥 映像設定:")
        if isinstance(encoding, list):
            for i, stream in enumerate(encoding):
                print(f"  ストリーム {i+1}:")
                print(f"    解像度: {stream.get('mainStream', {}).get('size', 'N/A')}")
                print(f"    フレームレート: {stream.get('mainStream', {}).get('frameRate', 'N/A')} fps")
                print(f"    ビットレート: {stream.get('mainStream', {}).get('bitRate', 'N/A')} kbps")
    
    # AI設定
    if info.get('ai_config'):
        ai_config = info['ai_config']
        print(f"\n🤖 AI検知設定:")
        print(f"  人間検知: {'有効' if ai_config.get('dog_cat', {}).get('enabled') else '無効'}")
        print(f"  車両検知: {'有効' if ai_config.get('vehicle', {}).get('enabled') else '無効'}")
        print(f"  動物検知: {'有効' if ai_config.get('people', {}).get('enabled') else '無効'}")
    
    # モーション検知
    if info.get('motion_detection'):
        motion = info['motion_detection']
        print(f"\n🔍 モーション検知:")
        print(f"  状態: {'有効' if motion.get('enable') else '無効'}")
        print(f"  感度: {motion.get('sensitivity', 'N/A')}")

def save_info_to_file(info, filename=None):
    """デバイス情報をJSONファイルに保存"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"device_info_{timestamp}.json"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(info, f, ensure_ascii=False, indent=2)
        print(f"\n💾 デバイス情報を {filename} に保存しました")
        return filename
    except Exception as e:
        print(f"❌ ファイル保存エラー: {e}")
        return None

def main():
    """メイン処理"""
    camera_ip = "192.168.31.85"
    username = "admin"
    
    # パスワード入力
    password = input(f"カメラ {camera_ip} のパスワードを入力してください: ")
    
    try:
        print(f"\nカメラ {camera_ip} に接続中...")
        camera = Camera(camera_ip, username, password)
        
        # ログイン
        if not camera.login():
            print("❌ 認証失敗")
            return
        
        print("✅ 認証成功\n")
        print("デバイス情報を取得中...")
        
        # デバイス情報取得
        info = get_detailed_device_info(camera)
        
        # 情報表示
        format_device_info(info)
        
        # ファイル保存
        save_info_to_file(info)
        
        # ログアウト
        camera.logout()
        print("\n✅ 処理完了")
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        print(f"詳細: {traceback.format_exc()}")

if __name__ == "__main__":
    main()