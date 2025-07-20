#!/usr/bin/env python3
"""
基本機能テストスクリプト
パスワード入力なしで基本的な動作確認を行う
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.camera_config import get_camera_config
from rtsp_stream import RTSPStream
import subprocess
import time

def test_network_connectivity():
    """ネットワーク接続テスト"""
    print("=== ネットワーク接続テスト ===")
    
    camera_ip = "192.168.31.85"
    
    # Ping テスト
    try:
        result = subprocess.run(['ping', '-c', '3', camera_ip], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Ping成功")
            # RTT情報抽出
            lines = result.stdout.split('\n')
            for line in lines:
                if 'rtt' in line.lower():
                    print(f"  {line.strip()}")
        else:
            print("❌ Ping失敗")
            return False
    except Exception as e:
        print(f"❌ Pingテストエラー: {e}")
        return False
    
    # ポートテスト
    ports = [80, 554]
    for port in ports:
        try:
            result = subprocess.run(['nc', '-zv', camera_ip, str(port)], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"✅ ポート {port} 接続可能")
            else:
                print(f"❌ ポート {port} 接続失敗")
                return False
        except Exception as e:
            print(f"❌ ポート {port} テストエラー: {e}")
            return False
    
    return True

def test_config_system():
    """設定システムテスト"""
    print("\n=== 設定システムテスト ===")
    
    try:
        config = get_camera_config()
        print(f"✅ 設定読み込み成功")
        print(f"  IP: {config.ip}")
        print(f"  ユーザー名: {config.username}")
        print(f"  パスワード: {'設定済み' if config.password else '未設定'}")
        print(f"  メイン解像度: {config.main_resolution}")
        print(f"  サブ解像度: {config.sub_resolution}")
        print(f"  目標FPS: {config.target_fps}")
        
        # 出力ディレクトリ確認
        if os.path.exists(config.output_dir):
            print(f"✅ 出力ディレクトリ: {config.output_dir}")
        else:
            print(f"❌ 出力ディレクトリなし: {config.output_dir}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 設定システムエラー: {e}")
        return False

def test_rtsp_url_generation():
    """RTSP URL生成テスト"""
    print("\n=== RTSP URL生成テスト ===")
    
    try:
        config = get_camera_config()
        
        # テスト用パスワード設定
        config.set_password("test_password")
        
        main_url = config.get_rtsp_url("main")
        sub_url = config.get_rtsp_url("sub")
        
        print(f"✅ メインストリームURL生成成功")
        print(f"  形式: rtsp://username:password@ip:port/path")
        print(f"  実際: {main_url[:20]}...{main_url[-20:]}")  # 一部マスク
        
        print(f"✅ サブストリームURL生成成功")
        print(f"  実際: {sub_url[:20]}...{sub_url[-20:]}")  # 一部マスク
        
        # パスワードリセット
        config.set_password(None)
        
        return True
        
    except Exception as e:
        print(f"❌ RTSP URL生成エラー: {e}")
        return False

def test_module_imports():
    """モジュールインポートテスト"""
    print("\n=== モジュールインポートテスト ===")
    
    modules = [
        ('utils.camera_config', 'カメラ設定'),
        ('rtsp_stream', 'RTSPストリーム'),
        ('video_viewer', '映像表示'),
        ('video_recorder', '映像録画'),
        ('snapshot', 'スナップショット'),
        ('event_monitor', 'イベント監視')
    ]
    
    all_success = True
    
    for module_name, description in modules:
        try:
            __import__(module_name)
            print(f"✅ {description}モジュール インポート成功")
        except Exception as e:
            print(f"❌ {description}モジュール インポート失敗: {e}")
            all_success = False
    
    return all_success

def test_dependencies():
    """依存関係テスト"""
    print("\n=== 依存関係テスト ===")
    
    dependencies = [
        ('cv2', 'OpenCV'),
        ('reolinkapi', 'Reolink API'),
        ('numpy', 'NumPy')
    ]
    
    all_success = True
    
    for module_name, description in dependencies:
        try:
            module = __import__(module_name)
            if hasattr(module, '__version__'):
                version = module.__version__
            else:
                version = "バージョン不明"
            print(f"✅ {description}: {version}")
        except Exception as e:
            print(f"❌ {description} インポート失敗: {e}")
            all_success = False
    
    return all_success

def test_file_structure():
    """ファイル構造テスト"""
    print("\n=== ファイル構造テスト ===")
    
    required_files = [
        'basic_connection_test.py',
        'device_info.py',
        'rtsp_stream.py',
        'video_viewer.py',
        'video_recorder.py',
        'snapshot.py',
        'event_monitor.py',
        'utils/camera_config.py',
        'examples/comprehensive_demo.py'
    ]
    
    all_exist = True
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} が見つかりません")
            all_exist = False
    
    return all_exist

def run_basic_tests():
    """基本テスト実行"""
    print("=== RLC-510A システム基本動作テスト ===")
    print("パスワード入力なしで実行可能なテストを行います\n")
    
    tests = [
        test_file_structure,
        test_dependencies,
        test_module_imports,
        test_config_system,
        test_rtsp_url_generation,
        test_network_connectivity
    ]
    
    results = []
    
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ {test_func.__name__} でエラー: {e}")
            results.append(False)
        
        time.sleep(1)  # テスト間の待機
    
    # 結果サマリー
    print("\n" + "="*50)
    print("テスト結果サマリー")
    print("="*50)
    
    passed = sum(results)
    total = len(results)
    
    print(f"合格: {passed}/{total} テスト")
    
    if passed == total:
        print("🎉 すべてのテストが成功しました！")
        print("次のステップ: 実際のカメラパスワードを設定して機能テストを実行")
    else:
        print("⚠️  一部のテストが失敗しました")
        print("失敗した項目を確認して修正してください")
    
    return passed == total

if __name__ == "__main__":
    success = run_basic_tests()
    sys.exit(0 if success else 1)