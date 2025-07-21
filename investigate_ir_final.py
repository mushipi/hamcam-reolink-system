#!/usr/bin/env python3
"""
RLC-510A IR関連情報の最終調査
認証済みsessionでの直接APIコール
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from reolinkapi import Camera
import json
import requests

def final_ir_investigation():
    """認証済みsessionでのIR関連API最終調査"""
    print("=== RLC-510A IR関連情報の最終調査 ===")
    
    camera_ip = "192.168.31.85"
    username = "admin"
    password = "894890abc"
    
    try:
        camera = Camera(camera_ip, username, password)
        
        if camera.login():
            print("✅ 認証成功")
            
            # Camera オブジェクトのsessionを取得
            session = getattr(camera, '_Camera__session', None)
            token = getattr(camera, 'token', None)
            
            print(f"🔑 セッション情報:")
            print(f"   トークン: {token}")
            print(f"   セッション: {type(session)}")
            
            # 認証済みsessionでAPIコール
            if session:
                ir_commands = [
                    'GetIrLights', 'GetWhiteLed', 'GetPowerLed', 'GetStatusLed',
                    'GetNightVision', 'GetDayNightState', 'GetAutoNight',
                    'GetImage', 'GetIsp', 'GetImageAdjust', 'GetWhiteBalance', 
                    'GetExposure', 'GetAbility', 'GetAiCfg'
                ]
                
                successful_commands = {}
                
                for cmd in ir_commands:
                    try:
                        url = f"http://{camera_ip}/api.cgi"
                        
                        # 複数の認証方式を試す
                        payloads = [
                            # 方式1: channel指定
                            [{
                                "cmd": cmd,
                                "action": 0,
                                "param": {
                                    "channel": 0
                                }
                            }],
                            # 方式2: パラメータなし
                            [{
                                "cmd": cmd,
                                "action": 0
                            }],
                            # 方式3: 単純形式
                            [{
                                "cmd": cmd
                            }]
                        ]
                        
                        for i, payload in enumerate(payloads):
                            try:
                                response = session.post(url, json=payload, timeout=5)
                                
                                if response.status_code == 200:
                                    result = response.json()
                                    if result and len(result) > 0:
                                        if result[0].get('code') == 0:  # 成功
                                            successful_commands[cmd] = result[0].get('value', result[0])
                                            print(f"✅ {cmd} (方式{i+1}): 成功")
                                            print(f"   📋 結果: {json.dumps(result[0], indent=4, ensure_ascii=False)}")
                                            break
                                        else:
                                            error_detail = result[0].get('error', {}).get('detail', 'Unknown error')
                                            if i == len(payloads) - 1:  # 最後の試行
                                                print(f"❌ {cmd}: {error_detail}")
                                    else:
                                        if i == len(payloads) - 1:
                                            print(f"❌ {cmd}: 空のレスポンス")
                                else:
                                    if i == len(payloads) - 1:
                                        print(f"❌ {cmd}: HTTP {response.status_code}")
                                        
                            except requests.exceptions.Timeout:
                                if i == len(payloads) - 1:
                                    print(f"❌ {cmd}: タイムアウト")
                            except Exception as e:
                                if i == len(payloads) - 1:
                                    print(f"❌ {cmd}: 例外 ({e})")
                                    
                    except Exception as e:
                        print(f"❌ {cmd}: 全般エラー ({e})")
                
                print(f"\n✅ 成功したコマンド数: {len(successful_commands)}")
                print("成功したコマンド:", list(successful_commands.keys()))
                
                # 特に重要な結果の詳細表示
                important_commands = ['GetIrLights', 'GetNightVision', 'GetDayNightState', 'GetImage', 'GetAbility']
                for cmd in important_commands:
                    if cmd in successful_commands:
                        print(f"\n=== {cmd} 詳細結果 ===")
                        print(json.dumps(successful_commands[cmd], indent=2, ensure_ascii=False))
                
                camera.logout()
                return successful_commands
            else:
                print("❌ セッション取得失敗")
                camera.logout()
                return {}
                
        else:
            print("❌ 認証失敗")
            return {}
            
    except Exception as e:
        print(f"❌ 調査エラー: {e}")
        return {}

def analyze_existing_data():
    """既存データからIR判定手がかりを探す"""
    print("\n=== 既存データからのIR判定手がかり分析 ===")
    
    # 現在時刻（21:41）は夜間 = IR モードの可能性が高い
    print("🕘 現在時刻: 21:41 → 夜間時間帯")
    print("💡 現在の映像はIRモードの可能性が高い")
    
    # パフォーマンス情報から推測
    print("\n📊 パフォーマンス情報:")
    print("   CPU使用率: 52%")
    print("   エンコード率: 4797")
    print("   ネットワーク負荷: 3")
    
    # 推測アプローチ
    print("\n🔍 IRモード判定の代替アプローチ:")
    print("1. 時刻ベース判定 (日の出/日の入り時刻)")
    print("2. 映像解析による判定 (RGB相関・エッジ特性)")
    print("3. エンコード情報からの推測")
    print("4. 明るさセンサーシミュレーション")
    
    return {
        "current_time": "21:41",
        "likely_mode": "ir",
        "confidence": 0.8,
        "detection_method": "time_based"
    }

def create_lighting_detection_strategy():
    """照明検出戦略の策定"""
    print("\n=== 照明モード検出戦略 ===")
    
    strategy = {
        "primary_method": "image_analysis",
        "fallback_methods": ["time_based", "brightness_threshold"],
        "implementation_priority": [
            "RGB correlation analysis",
            "HSV hue diversity",
            "Edge density analysis",
            "Time-based estimation"
        ]
    }
    
    print("📋 推奨実装戦略:")
    print("1. 🎯 メイン手法: RGB相関解析")
    print("   - チャンネル間相関 > 0.95 → IR判定")
    print("   - 計算軽量、精度高い")
    
    print("2. 🔄 補助手法: 時刻ベース推定")
    print("   - 日の出前/日の入り後 → IR推定")
    print("   - APIから時刻情報取得可能")
    
    print("3. 📈 品質評価: エッジ密度解析")
    print("   - IR特有の高コントラスト検出")
    print("   - フレーム品質評価にも活用")
    
    return strategy

if __name__ == "__main__":
    try:
        # 最終API調査
        api_result = final_ir_investigation()
        
        # 既存データ分析
        existing_analysis = analyze_existing_data()
        
        # 戦略策定
        strategy = create_lighting_detection_strategy()
        
        # 総合結論
        print("\n" + "="*60)
        print("🎯 最終結論: RLC-510A照明モード検出について")
        print("="*60)
        
        if api_result:
            print("✅ 一部APIコマンドが成功しました")
            for cmd in api_result.keys():
                print(f"   - {cmd}")
        else:
            print("❌ 直接的なIR状態取得APIは利用不可")
        
        print("\n💡 推奨実装方針:")
        print("1. RGB相関解析による映像ベース判定を主軸")
        print("2. 時刻情報による補助判定")
        print("3. 学習データ収集時の品質管理強化")
        print("4. 段階的な精度向上アプローチ")
        
        print(f"\n📝 次のステップ:")
        print("   → 照明モード検出クラスの実装開始")
        print("   → RGB相関解析の実装・テスト")
        print("   → 自動撮影システムとの統合")
        
    except KeyboardInterrupt:
        print("\n調査中断")
    except Exception as e:
        print(f"\n最終調査エラー: {e}")