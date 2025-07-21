#!/usr/bin/env python3
"""
RLC-510A 照明モード情報の詳細調査
reolinkapi の全メソッドと直接APIコールでの詳細調査
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from reolinkapi import Camera
import json
import inspect

def explore_all_camera_methods():
    """Camera オブジェクトの全メソッド調査"""
    print("=== Camera オブジェクトの全メソッド調査 ===")
    
    camera_ip = "192.168.31.85"
    username = "admin"
    password = "894890abc"
    
    try:
        camera = Camera(camera_ip, username, password)
        
        if camera.login():
            print("✅ 認証成功\n")
            
            # Camera オブジェクトの全メソッド取得
            all_methods = [method for method in dir(camera) if callable(getattr(camera, method)) and not method.startswith('_')]
            
            print(f"📋 利用可能メソッド数: {len(all_methods)}")
            
            # IR・照明・画像関連のメソッドを探す
            relevant_keywords = ['ir', 'light', 'night', 'day', 'image', 'led', 'lamp', 'vision', 'mode', 'state', 'status']
            
            relevant_methods = []
            for method in all_methods:
                for keyword in relevant_keywords:
                    if keyword in method.lower():
                        relevant_methods.append(method)
                        break
            
            print(f"🔍 関連する可能性のあるメソッド: {len(relevant_methods)}")
            for method in relevant_methods:
                print(f"  - {method}")
            
            # 全メソッドを実行してみる（安全なもののみ）
            print("\n=== 全メソッド実行テスト ===")
            safe_get_methods = [method for method in all_methods if method.startswith('get_')]
            
            successful_methods = {}
            for method_name in safe_get_methods:
                try:
                    print(f"🔍 {method_name}() テスト中...")
                    method = getattr(camera, method_name)
                    
                    # メソッドシグネチャチェック
                    sig = inspect.signature(method)
                    if len(sig.parameters) == 0:  # パラメータなしのメソッドのみ
                        result = method()
                        if result:
                            successful_methods[method_name] = result
                            print(f"✅ {method_name}: 成功")
                            
                            # 結果の要約表示
                            if isinstance(result, dict):
                                keys = list(result.keys())[:5]  # 最初の5キーのみ
                                print(f"   📋 キー: {keys}")
                            elif isinstance(result, list) and result:
                                print(f"   📋 リスト長: {len(result)}")
                            else:
                                print(f"   📋 型: {type(result)}")
                        else:
                            print(f"❌ {method_name}: 結果なし")
                    else:
                        print(f"⚠️  {method_name}: パラメータ必要 {sig}")
                        
                except Exception as e:
                    print(f"❌ {method_name}: エラー ({e})")
            
            # 成功したメソッドの詳細表示
            print(f"\n✅ 成功したメソッド数: {len(successful_methods)}")
            for method_name, result in successful_methods.items():
                print(f"\n=== {method_name} 詳細結果 ===")
                print(json.dumps(result, indent=2, ensure_ascii=False))
            
            camera.logout()
            return successful_methods
            
        else:
            print("❌ 認証失敗")
            return {}
            
    except Exception as e:
        print(f"❌ 調査エラー: {e}")
        return {}

def test_reolink_api_commands():
    """Reolink API の既知コマンド調査"""
    print("\n=== Reolink API 既知コマンド調査 ===")
    
    camera_ip = "192.168.31.85"
    username = "admin"
    password = "894890abc"
    
    # 既知のReolink APIコマンド
    api_commands = [
        # 基本情報
        'GetDevInfo', 'GetSysVer', 'GetNetworkGeneral',
        
        # 画像・映像設定
        'GetImage', 'GetIsp', 'GetEnc', 'GetOsd', 'GetRec',
        
        # IR・照明関連
        'GetIrLights', 'GetWhiteLed', 'GetPowerLed', 'GetStatusLed',
        'GetNightVision', 'GetDayNightState', 'GetAutoNight',
        
        # AI・検知
        'GetAiState', 'GetAiCfg', 'GetMdState', 'GetMdAlarm',
        
        # その他
        'GetTime', 'GetPtzPreset', 'GetZoomFocus', 'GetAutoFocus',
        'GetImageAdjust', 'GetWhiteBalance', 'GetExposure',
        'GetUser', 'GetPerformance', 'GetAbility'
    ]
    
    try:
        camera = Camera(camera_ip, username, password)
        
        if camera.login():
            print("✅ 認証成功")
            
            # 認証トークン取得
            token = getattr(camera, 'token', None)
            print(f"🔑 トークン: {token}")
            
            import requests
            session = requests.Session()
            
            successful_commands = {}
            
            for cmd in api_commands:
                try:
                    # POST方式でのAPIコール
                    url = f"http://{camera_ip}/api.cgi"
                    
                    data = [{
                        "cmd": cmd,
                        "action": 0,
                        "param": {
                            "channel": 0
                        }
                    }]
                    
                    # 認証情報付きでリクエスト
                    headers = {
                        'Content-Type': 'application/json'
                    }
                    
                    # セッションCookieまたはトークンを使用
                    response = session.post(url, json=data, headers=headers, 
                                          auth=(username, password))
                    
                    print(f"🔍 {cmd}: ステータス {response.status_code}")
                    
                    if response.status_code == 200:
                        try:
                            result = response.json()
                            if result and len(result) > 0:
                                if result[0].get('code') == 0:  # 成功
                                    successful_commands[cmd] = result[0].get('value', result[0])
                                    print(f"✅ {cmd}: 成功")
                                    
                                    # IR・照明関連は詳細表示
                                    if any(keyword in cmd.lower() for keyword in ['ir', 'light', 'led', 'night', 'day']):
                                        print(f"   📋 詳細: {json.dumps(result[0], indent=4, ensure_ascii=False)}")
                                else:
                                    error_detail = result[0].get('error', {}).get('detail', 'Unknown error')
                                    print(f"❌ {cmd}: {error_detail}")
                            else:
                                print(f"❌ {cmd}: 空のレスポンス")
                        except json.JSONDecodeError:
                            print(f"❌ {cmd}: JSON解析エラー")
                            print(f"   レスポンス: {response.text[:100]}...")
                    else:
                        print(f"❌ {cmd}: HTTP {response.status_code}")
                        
                except Exception as e:
                    print(f"❌ {cmd}: 例外 ({e})")
            
            print(f"\n✅ 成功したAPIコマンド数: {len(successful_commands)}")
            print("成功したコマンド:", list(successful_commands.keys()))
            
            camera.logout()
            return successful_commands
            
        else:
            print("❌ 認証失敗")
            return {}
            
    except Exception as e:
        print(f"❌ API調査エラー: {e}")
        return {}

if __name__ == "__main__":
    try:
        # Camera メソッド調査
        methods_result = explore_all_camera_methods()
        
        # 直接APIコマンド調査  
        api_result = test_reolink_api_commands()
        
        # 結果まとめ
        print("\n" + "="*50)
        print("🎯 照明モード検出に関する調査結果まとめ")
        print("="*50)
        
        ir_related_found = False
        
        # メソッド結果から照明関連を探す
        for method, result in methods_result.items():
            if any(keyword in method.lower() for keyword in ['ir', 'light', 'night', 'day', 'led']):
                print(f"📍 メソッド発見: {method}")
                ir_related_found = True
        
        # APIコマンド結果から照明関連を探す
        for cmd, result in api_result.items():
            if any(keyword in cmd.lower() for keyword in ['ir', 'light', 'night', 'day', 'led']):
                print(f"📍 APIコマンド発見: {cmd}")
                ir_related_found = True
        
        if not ir_related_found:
            print("❌ 直接的な照明モード情報は見つかりませんでした")
            print("💡 推奨: 映像解析による照明モード検出を実装")
        
    except KeyboardInterrupt:
        print("\n調査中断")
    except Exception as e:
        print(f"\n調査エラー: {e}")