#!/usr/bin/env python3
"""
カメラ接続テストスクリプト
実際のカメラとの接続をテストする
"""

import sys
import os
import getpass
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from reolinkapi import Camera
from utils.camera_config import get_camera_config
import time
import json

def test_camera_api_connection():
    """カメラAPI接続テスト"""
    print("=== カメラAPI接続テスト ===")
    
    config = get_camera_config()
    
    # パスワード入力
    if not config.password:
        print(f"カメラ {config.ip} への接続テストを行います")
        password = getpass.getpass("パスワードを入力してください: ")
        config.set_password(password)
    
    try:
        camera = Camera(config.ip, config.username, config.password)
        
        print("認証中...")
        if camera.login():
            print("✅ API認証成功")
            
            # 基本情報取得テスト
            try:
                device_info = camera.get_device_info()
                print("✅ デバイス情報取得成功")
                print(f"  デバイス名: {device_info.get('name', 'N/A')}")
                print(f"  モデル: {device_info.get('model', 'N/A')}")
                print(f"  ファームウェア: {device_info.get('firmVer', 'N/A')}")
                print(f"  UID: {device_info.get('uid', 'N/A')}")
            except Exception as e:
                print(f"⚠️  デバイス情報取得エラー: {e}")
            
            # ネットワーク情報取得テスト
            try:
                network_info = camera.get_network_general()
                print("✅ ネットワーク情報取得成功")
                print(f"  IP: {network_info.get('ip', 'N/A')}")
                print(f"  MAC: {network_info.get('mac', 'N/A')}")
                print(f"  DHCP: {'有効' if network_info.get('dhcp') else '無効'}")
            except Exception as e:
                print(f"⚠️  ネットワーク情報取得エラー: {e}")
            
            # エンコード設定取得テスト
            try:
                encoding_info = camera.get_encoding()
                print("✅ エンコード設定取得成功")
                if isinstance(encoding_info, list) and encoding_info:
                    main_stream = encoding_info[0].get('mainStream', {})
                    print(f"  メイン解像度: {main_stream.get('size', 'N/A')}")
                    print(f"  フレームレート: {main_stream.get('frameRate', 'N/A')} fps")
                    print(f"  ビットレート: {main_stream.get('bitRate', 'N/A')} kbps")
            except Exception as e:
                print(f"⚠️  エンコード設定取得エラー: {e}")
            
            camera.logout()
            return True
            
        else:
            print("❌ API認証失敗")
            return False
            
    except Exception as e:
        print(f"❌ 接続エラー: {e}")
        return False

def test_rtsp_stream_basic():
    """RTSPストリーム基本テスト"""
    print("\n=== RTSPストリーム基本テスト ===")
    
    config = get_camera_config()
    
    if not config.password:
        print("パスワードが設定されていません")
        return False
    
    try:
        from rtsp_stream import RTSPStream
        
        # サブストリームでテスト（軽量）
        print("サブストリームでの接続テスト...")
        
        with RTSPStream("sub", buffer_size=1) as stream:
            if stream.start_stream():
                print("✅ RTSPストリーム開始成功")
                
                # 5秒間のフレーム取得テスト
                print("5秒間のフレーム取得テスト...")
                start_time = time.time()
                frame_count = 0
                success_count = 0
                
                while (time.time() - start_time) < 5:
                    result = stream.get_frame(timeout=0.5)
                    frame_count += 1
                    
                    if result and result[0]:
                        success_count += 1
                        if success_count == 1:  # 最初のフレーム
                            _, frame = result
                            print(f"  フレームサイズ: {frame.shape}")
                    
                    time.sleep(0.2)
                
                stats = stream.get_stats()
                print(f"✅ フレーム取得テスト完了")
                print(f"  取得試行: {frame_count}回")
                print(f"  成功: {success_count}回")
                print(f"  成功率: {success_count/frame_count*100:.1f}%")
                print(f"  現在FPS: {stats['current_fps']:.1f}")
                print(f"  ドロップフレーム: {stats['dropped_frames']}")
                
                return success_count > 0
            else:
                print("❌ RTSPストリーム開始失敗")
                return False
                
    except Exception as e:
        print(f"❌ RTSPストリームテストエラー: {e}")
        return False

def test_snapshot_function():
    """スナップショット機能テスト"""
    print("\n=== スナップショット機能テスト ===")
    
    config = get_camera_config()
    
    if not config.password:
        print("パスワードが設定されていません")
        return False
    
    try:
        from snapshot import SnapshotCapture
        
        # API方式テスト
        print("1. API方式スナップショットテスト...")
        capture_api = SnapshotCapture("api")
        
        if capture_api.initialize():
            filepath = capture_api.capture_snapshot("test_api_snapshot.jpg")
            if filepath:
                print(f"✅ API方式撮影成功: {os.path.basename(filepath)}")
                
                # ファイルサイズ確認
                if os.path.exists(filepath):
                    size = os.path.getsize(filepath)
                    print(f"  ファイルサイズ: {size/1024:.1f} KB")
                
                api_success = True
            else:
                print("❌ API方式撮影失敗")
                api_success = False
            
            capture_api.cleanup()
        else:
            print("❌ API方式初期化失敗")
            api_success = False
        
        # RTSP方式テスト
        print("\n2. RTSP方式スナップショットテスト...")
        capture_rtsp = SnapshotCapture("rtsp", "sub")
        
        if capture_rtsp.initialize():
            time.sleep(2)  # ストリーム安定化待ち
            filepath = capture_rtsp.capture_snapshot("test_rtsp_snapshot.jpg")
            if filepath:
                print(f"✅ RTSP方式撮影成功: {os.path.basename(filepath)}")
                
                # ファイルサイズ確認
                if os.path.exists(filepath):
                    size = os.path.getsize(filepath)
                    print(f"  ファイルサイズ: {size/1024:.1f} KB")
                
                rtsp_success = True
            else:
                print("❌ RTSP方式撮影失敗")
                rtsp_success = False
            
            capture_rtsp.cleanup()
        else:
            print("❌ RTSP方式初期化失敗")
            rtsp_success = False
        
        return api_success or rtsp_success
        
    except Exception as e:
        print(f"❌ スナップショットテストエラー: {e}")
        return False

def save_test_results(results):
    """テスト結果保存"""
    try:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        results_file = f"output/logs/test_results_{timestamp}.json"
        
        os.makedirs(os.path.dirname(results_file), exist_ok=True)
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': timestamp,
                'results': results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\nテスト結果を保存しました: {results_file}")
        
    except Exception as e:
        print(f"結果保存エラー: {e}")

def main():
    """メイン関数"""
    print("=== RLC-510A カメラ接続機能テスト ===")
    print("実際のカメラとの接続をテストします\n")
    
    tests = [
        ("API接続", test_camera_api_connection),
        ("RTSPストリーム", test_rtsp_stream_basic),
        ("スナップショット", test_snapshot_function)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name}テスト {'='*20}")
        try:
            result = test_func()
            results[test_name] = {
                'success': result,
                'error': None
            }
            
            if result:
                print(f"✅ {test_name}テスト 成功")
            else:
                print(f"❌ {test_name}テスト 失敗")
                
        except Exception as e:
            results[test_name] = {
                'success': False,
                'error': str(e)
            }
            print(f"❌ {test_name}テスト エラー: {e}")
        
        time.sleep(2)
    
    # 結果サマリー
    print("\n" + "="*60)
    print("テスト結果サマリー")
    print("="*60)
    
    success_count = sum(1 for r in results.values() if r['success'])
    total_count = len(results)
    
    for test_name, result in results.items():
        status = "✅ 成功" if result['success'] else "❌ 失敗"
        print(f"{test_name:15}: {status}")
        if result['error']:
            print(f"                エラー: {result['error']}")
    
    print(f"\n合格: {success_count}/{total_count} テスト")
    
    if success_count == total_count:
        print("🎉 すべてのカメラ接続テストが成功しました！")
        print("システムは正常に動作しています。")
    elif success_count > 0:
        print("⚠️  一部のテストが失敗しましたが、基本機能は動作します")
    else:
        print("❌ すべてのテストが失敗しました")
        print("カメラの設定や接続を確認してください")
    
    # 結果保存
    save_test_results(results)
    
    return success_count > 0

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nテストが中断されました")
        sys.exit(1)