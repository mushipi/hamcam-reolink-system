#!/usr/bin/env python3
"""
Reolink API実メソッド探索
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from reolinkapi import Camera

def explore_api_methods():
    """API実メソッド探索"""
    print("=== Reolink API 実メソッド探索 ===")
    
    camera_ip = "192.168.31.85"
    username = "admin"
    password = "894890abc"
    
    try:
        camera = Camera(camera_ip, username, password)
        
        if camera.login():
            print("✅ 認証成功\n")
            
            # 全メソッドリスト
            all_methods = [method for method in dir(camera) if not method.startswith('_')]
            print(f"全メソッド数: {len(all_methods)}\n")
            
            # getで始まるメソッドを探索
            get_methods = [method for method in all_methods if method.startswith('get')]
            print(f"=== GETメソッド一覧 ({len(get_methods)}個) ===")
            
            for method_name in sorted(get_methods):
                try:
                    method = getattr(camera, method_name)
                    # パラメータが不要そうなメソッドを試す
                    if method_name in ['get_network_general', 'get_hdd_info']:
                        result = method()
                        print(f"✅ {method_name}: 成功 - {type(result)}")
                        if isinstance(result, list) and result:
                            print(f"   内容例: {str(result[0])[:100]}...")
                        elif isinstance(result, dict):
                            keys = list(result.keys())[:5]
                            print(f"   キー例: {keys}")
                    else:
                        print(f"📋 {method_name}: 存在")
                except Exception as e:
                    print(f"❌ {method_name}: {str(e)[:50]}...")
            
            # 他の有用そうなメソッド
            print(f"\n=== その他の有用そうなメソッド ===")
            other_methods = [method for method in all_methods 
                           if any(keyword in method.lower() for keyword in 
                                ['device', 'info', 'status', 'version', 'motion', 'ai', 'snap', 'stream'])]
            
            for method_name in sorted(other_methods):
                if not method_name.startswith('get'):
                    print(f"📋 {method_name}")
            
            # ネットワーク情報詳細表示
            print(f"\n=== ネットワーク情報詳細 ===")
            try:
                network_info = camera.get_network_general()
                if network_info and isinstance(network_info, list):
                    net_data = network_info[0]
                    print(f"IP: {net_data.get('ip', 'N/A')}")
                    print(f"MAC: {net_data.get('mac', 'N/A')}")
                    print(f"DHCP: {net_data.get('dhcp', 'N/A')}")
                    print(f"ゲートウェイ: {net_data.get('gateway', 'N/A')}")
                    print(f"DNS: {net_data.get('dns1', 'N/A')}")
            except Exception as e:
                print(f"ネットワーク情報詳細エラー: {e}")
            
            # HDD情報詳細表示
            print(f"\n=== HDD情報詳細 ===")
            try:
                hdd_info = camera.get_hdd_info()
                if hdd_info and isinstance(hdd_info, list):
                    hdd_data = hdd_info[0]
                    print(f"容量: {hdd_data.get('capacity', 'N/A')} GB")
                    print(f"使用量: {hdd_data.get('size', 'N/A')} GB")
                    print(f"状態: {hdd_data.get('status', 'N/A')}")
                    print(f"フォーマット: {hdd_data.get('format', 'N/A')}")
            except Exception as e:
                print(f"HDD情報詳細エラー: {e}")
            
            camera.logout()
            return True
            
        else:
            print("❌ 認証失敗")
            return False
            
    except Exception as e:
        print(f"❌ 探索エラー: {e}")
        return False

if __name__ == "__main__":
    explore_api_methods()