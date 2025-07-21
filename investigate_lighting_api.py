#!/usr/bin/env python3
"""
RLC-510A 照明モード・IR情報の調査
直接APIから照明状態を取得できるかを調査
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from reolinkapi import Camera
import json

def investigate_lighting_api():
    """照明・IR関連API情報の調査"""
    print("=== RLC-510A 照明モード・IR情報調査 ===")
    
    camera_ip = "192.168.31.85"
    username = "admin"
    password = "894890abc"
    
    try:
        camera = Camera(camera_ip, username, password)
        
        if camera.login():
            print("✅ 認証成功\n")
            
            # 1. 画像設定（ISP設定）
            print("=== 画像設定 (Image/ISP) ===")
            try:
                isp_info = camera.get_image_setting()
                if isp_info:
                    print("✅ 画像設定取得成功")
                    print(json.dumps(isp_info, indent=2, ensure_ascii=False))
                else:
                    print("❌ 画像設定取得失敗")
            except Exception as e:
                print(f"❌ 画像設定取得エラー: {e}")
            
            # 2. IRライト設定
            print("\n=== IRライト設定 ===")
            try:
                ir_info = camera.get_ir_lights()
                if ir_info:
                    print("✅ IRライト設定取得成功")
                    print(json.dumps(ir_info, indent=2, ensure_ascii=False))
                else:
                    print("❌ IRライト設定取得失敗")
            except Exception as e:
                print(f"❌ IRライト設定取得エラー: {e}")
            
            # 3. 夜間設定
            print("\n=== 夜間設定 ===")
            try:
                night_info = camera.get_night_vision()
                if night_info:
                    print("✅ 夜間設定取得成功")
                    print(json.dumps(night_info, indent=2, ensure_ascii=False))
                else:
                    print("❌ 夜間設定取得失敗")
            except Exception as e:
                print(f"❌ 夜間設定取得エラー: {e}")
            
            # 4. LED設定
            print("\n=== LED設定 ===")
            try:
                led_info = camera.get_led()
                if led_info:
                    print("✅ LED設定取得成功") 
                    print(json.dumps(led_info, indent=2, ensure_ascii=False))
                else:
                    print("❌ LED設定取得失敗")
            except Exception as e:
                print(f"❌ LED設定取得エラー: {e}")
            
            # 5. カメラ状態
            print("\n=== カメラ状態 ===")
            try:
                status_info = camera.get_status()
                if status_info:
                    print("✅ カメラ状態取得成功")
                    print(json.dumps(status_info, indent=2, ensure_ascii=False))
                else:
                    print("❌ カメラ状態取得失敗")
            except Exception as e:
                print(f"❌ カメラ状態取得エラー: {e}")
            
            # 6. 全API メソッド探索
            print("\n=== 利用可能APIメソッド探索 ===")
            api_methods = [
                # 基本情報
                'get_general_system', 'get_information', 'get_network_general',
                
                # 画像・映像設定
                'get_image_setting', 'get_recording_encoding', 'get_osd',
                
                # IR・照明関連
                'get_ir_lights', 'get_night_vision', 'get_led',
                
                # ステータス・状態
                'get_status', 'get_states', 'get_capabilities',
                
                # アラーム・検知
                'get_alarm_motion', 'get_ai_detection', 'get_ai_config',
                
                # その他設定
                'get_ptz_preset', 'get_zoom_focus', 'get_autofocus',
                'get_image_adjust', 'get_white_balance', 'get_exposure',
                
                # 時間・スケジュール  
                'get_time', 'get_schedule', 'get_daynight_state'
            ]
            
            available_methods = []
            for method_name in api_methods:
                if hasattr(camera, method_name):
                    try:
                        print(f"🔍 {method_name}() テスト中...")
                        method = getattr(camera, method_name)
                        result = method()
                        if result:
                            available_methods.append(method_name)
                            print(f"✅ {method_name}: 成功")
                            # 重要なものは詳細表示
                            if 'ir' in method_name.lower() or 'night' in method_name.lower() or 'led' in method_name.lower():
                                print(f"   📋 結果: {json.dumps(result, indent=4, ensure_ascii=False)}")
                        else:
                            print(f"❌ {method_name}: 結果なし")
                    except Exception as e:
                        print(f"❌ {method_name}: エラー ({e})")
                else:
                    print(f"⚠️  {method_name}: メソッド存在せず")
            
            print(f"\n✅ 利用可能メソッド数: {len(available_methods)}")
            print("利用可能メソッド一覧:", available_methods)
            
            camera.logout()
            return True
            
        else:
            print("❌ 認証失敗")
            return False
            
    except Exception as e:
        print(f"❌ 調査エラー: {e}")
        return False

def test_direct_api_calls():
    """直接APIコール調査"""
    print("\n=== 直接APIコール調査 ===")
    
    camera_ip = "192.168.31.85"
    username = "admin"
    password = "894890abc"
    
    import requests
    
    # APIエンドポイント候補
    api_endpoints = [
        '/api.cgi?cmd=GetIrLights',
        '/api.cgi?cmd=GetImage',
        '/api.cgi?cmd=GetNightVision', 
        '/api.cgi?cmd=GetLed',
        '/api.cgi?cmd=GetStatus',
        '/api.cgi?cmd=GetStates',
        '/api.cgi?cmd=GetDayNightState',
        '/api.cgi?cmd=GetImageAdjust',
        '/api.cgi?cmd=GetWhiteBalance'
    ]
    
    session = requests.Session()
    
    # 認証
    login_url = f"http://{camera_ip}/api.cgi?cmd=Login"
    login_data = {
        "cmd": "Login",
        "param": {
            "User": {
                "userName": username,
                "password": password
            }
        }
    }
    
    try:
        response = session.post(login_url, json=[login_data])
        if response.status_code == 200:
            print("✅ 直接API認証成功")
            
            for endpoint in api_endpoints:
                try:
                    url = f"http://{camera_ip}{endpoint}"
                    response = session.get(url)
                    print(f"\n🔍 {endpoint}:")
                    print(f"   ステータス: {response.status_code}")
                    if response.status_code == 200:
                        print(f"   レスポンス: {response.text[:200]}...")
                except Exception as e:
                    print(f"❌ {endpoint}: {e}")
        else:
            print("❌ 直接API認証失敗")
            
    except Exception as e:
        print(f"❌ 直接API調査エラー: {e}")

if __name__ == "__main__":
    try:
        investigate_lighting_api()
        test_direct_api_calls()
    except KeyboardInterrupt:
        print("\n調査中断")
    except Exception as e:
        print(f"\n調査エラー: {e}")