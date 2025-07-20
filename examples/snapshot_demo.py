#!/usr/bin/env python3
"""
スナップショット機能デモ
静止画撮影の様々な方法を示すデモ
"""

import sys
import os
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from snapshot import SnapshotCapture
import logging

def demo_single_snapshot():
    """単発スナップショットデモ"""
    print("\n=== 単発スナップショットデモ ===")
    
    # RTSP方式でスナップショット
    capture = SnapshotCapture("rtsp", "main")
    
    if capture.initialize():
        print("メインストリーム（高解像度）でスナップショットを撮影します...")
        
        filepath = capture.capture_snapshot("demo_single.jpg", quality=95)
        if filepath:
            print(f"撮影成功: {filepath}")
        else:
            print("撮影失敗")
        
        capture.cleanup()
    else:
        print("初期化失敗")

def demo_api_snapshot():
    """API方式スナップショットデモ"""
    print("\n=== API方式スナップショットデモ ===")
    
    # API方式でスナップショット
    capture = SnapshotCapture("api")
    
    if capture.initialize():
        print("API経由でスナップショットを撮影します...")
        
        filepath = capture.capture_snapshot("demo_api.jpg")
        if filepath:
            print(f"撮影成功: {filepath}")
        else:
            print("撮影失敗")
        
        capture.cleanup()
    else:
        print("初期化失敗")

def demo_burst_snapshot():
    """連続スナップショットデモ"""
    print("\n=== 連続スナップショットデモ ===")
    
    capture = SnapshotCapture("rtsp", "sub")
    
    if capture.initialize():
        count = 5
        interval = 1.0
        print(f"サブストリームで{count}枚連続撮影（{interval}秒間隔）...")
        
        results = capture.capture_burst(count, interval, "demo_burst")
        print(f"撮影完了: {len(results)}/{count}枚成功")
        
        for i, filepath in enumerate(results, 1):
            print(f"  {i}: {os.path.basename(filepath)}")
        
        capture.cleanup()
    else:
        print("初期化失敗")

def demo_timelapse_snapshot():
    """タイムラプススナップショットデモ"""
    print("\n=== タイムラプススナップショットデモ ===")
    
    capture = SnapshotCapture("rtsp", "sub")
    
    if capture.initialize():
        duration = 30  # 30秒間
        interval = 5   # 5秒間隔
        print(f"タイムラプス撮影（{duration}秒間、{interval}秒間隔）...")
        
        results = capture.capture_timelapse(duration, interval, "demo_timelapse")
        print(f"タイムラプス撮影完了: {len(results)}枚")
        
        for i, filepath in enumerate(results, 1):
            print(f"  {i}: {os.path.basename(filepath)}")
        
        capture.cleanup()
    else:
        print("初期化失敗")

def demo_interactive_snapshot():
    """インタラクティブスナップショットデモ"""
    print("\n=== インタラクティブスナップショットデモ ===")
    print("手動でスナップショットを撮影できます")
    
    capture = SnapshotCapture("rtsp", "main")
    
    if not capture.initialize():
        print("初期化失敗")
        return
    
    print("\nコマンド:")
    print("  Enter : スナップショット撮影")
    print("  'q'   : 終了")
    
    shot_count = 0
    
    try:
        while True:
            command = input(f"\nスナップショット撮影 (撮影済み: {shot_count}枚) - Enterキーまたは'q': ").strip().lower()
            
            if command == 'q':
                break
            elif command == '' or command == 's':
                shot_count += 1
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"interactive_{timestamp}_{shot_count:03d}.jpg"
                
                print("撮影中...")
                filepath = capture.capture_snapshot(filename)
                if filepath:
                    print(f"撮影成功: {os.path.basename(filepath)}")
                else:
                    print("撮影失敗")
            else:
                print("Enterキーまたは'q'を入力してください")
        
        # 統計表示
        stats = capture.get_stats()
        print(f"\n撮影統計:")
        print(f"  総撮影数: {stats['total_snapshots']}")
        print(f"  成功数: {stats['successful_snapshots']}")
        print(f"  成功率: {stats['success_rate']:.1f}%")
    
    except KeyboardInterrupt:
        print("\n中断されました")
    
    finally:
        capture.cleanup()

def demo_quality_comparison():
    """画質比較デモ"""
    print("\n=== 画質比較デモ ===")
    
    capture = SnapshotCapture("rtsp", "main")
    
    if capture.initialize():
        qualities = [50, 75, 95]
        print(f"異なる品質設定で撮影します: {qualities}")
        
        for quality in qualities:
            print(f"品質{quality}で撮影中...")
            filename = f"demo_quality_{quality}.jpg"
            filepath = capture.capture_snapshot(filename, quality)
            if filepath:
                print(f"  撮影成功: {os.path.basename(filepath)}")
                
                # ファイルサイズ表示
                try:
                    size = os.path.getsize(filepath)
                    print(f"  ファイルサイズ: {size/1024:.1f} KB")
                except:
                    pass
            else:
                print(f"  撮影失敗")
            
            time.sleep(1)
        
        capture.cleanup()
    else:
        print("初期化失敗")

def main():
    """スナップショットデモメイン"""
    print("=== RLC-510A スナップショット機能デモ ===")
    print("このデモでは、様々なスナップショット撮影機能を試すことができます")
    print()
    
    # ログ設定
    logging.basicConfig(level=logging.INFO)
    
    # デモ選択
    print("デモを選択してください:")
    print("1. 単発スナップショット (RTSP方式)")
    print("2. API方式スナップショット")
    print("3. 連続スナップショット (5枚)")
    print("4. タイムラプススナップショット (30秒間)")
    print("5. インタラクティブスナップショット (手動撮影)")
    print("6. 画質比較デモ")
    print("7. 全てのデモを順番に実行")
    
    while True:
        choice = input("選択 (1-7): ").strip()
        if choice in ["1", "2", "3", "4", "5", "6", "7"]:
            break
        print("無効な選択です。1-7を入力してください。")
    
    try:
        if choice == "1":
            demo_single_snapshot()
        elif choice == "2":
            demo_api_snapshot()
        elif choice == "3":
            demo_burst_snapshot()
        elif choice == "4":
            demo_timelapse_snapshot()
        elif choice == "5":
            demo_interactive_snapshot()
        elif choice == "6":
            demo_quality_comparison()
        elif choice == "7":
            demo_single_snapshot()
            input("\n次のデモに進むにはEnterを押してください...")
            demo_api_snapshot()
            input("\n次のデモに進むにはEnterを押してください...")
            demo_burst_snapshot()
            input("\n次のデモに進むにはEnterを押してください...")
            demo_timelapse_snapshot()
            input("\n次のデモに進むにはEnterを押してください...")
            demo_quality_comparison()
            print("\nインタラクティブデモをスキップしました")
        
        print("\nスナップショットデモ完了！")
        print("撮影した画像は 'output/snapshots' フォルダに保存されています。")
    
    except KeyboardInterrupt:
        print("\nデモが中断されました")

if __name__ == "__main__":
    main()