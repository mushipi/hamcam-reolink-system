#!/usr/bin/env python3
"""
録画機能デモ
映像録画の基本的な使用方法を示すデモ
"""

import sys
import os
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from video_recorder import VideoRecorder
import logging

def demo_basic_recording():
    """基本録画デモ"""
    print("\n=== 基本録画デモ ===")
    
    # 録画設定
    duration = 30  # 30秒録画
    recorder = VideoRecorder("sub", duration=duration)
    
    print(f"サブストリームで{duration}秒間録画します...")
    
    if recorder.start_recording("basic_demo"):
        print("録画開始！")
        
        # 進捗表示
        start_time = time.time()
        while recorder.is_recording:
            elapsed = time.time() - start_time
            remaining = duration - elapsed
            
            if remaining <= 0:
                break
                
            print(f"\r録画中... 残り時間: {remaining:.0f}秒", end="")
            time.sleep(1)
        
        print("\n録画完了！")
        
        # 統計表示
        stats = recorder.get_recording_stats()
        print(f"録画ファイル: {stats['current_file']}")
        print(f"フレーム数: {stats['total_frames']}")
        print(f"平均FPS: {stats['average_fps']:.1f}")
    else:
        print("録画開始失敗")

def demo_segment_recording():
    """セグメント録画デモ"""
    print("\n=== セグメント録画デモ ===")
    
    # セグメント録画設定（10秒セグメント、30秒録画）
    duration = 30
    segment_duration = 10
    recorder = VideoRecorder("sub", duration=duration, segment_duration=segment_duration)
    
    print(f"セグメント録画（{segment_duration}秒毎に分割、計{duration}秒）...")
    
    if recorder.start_recording("segment_demo"):
        print("録画開始！")
        
        start_time = time.time()
        while recorder.is_recording:
            elapsed = time.time() - start_time
            remaining = duration - elapsed
            
            if remaining <= 0:
                break
                
            stats = recorder.get_recording_stats()
            print(f"\r録画中... セグメント: {stats['segments_created']}, "
                  f"残り: {remaining:.0f}秒", end="")
            time.sleep(1)
        
        print("\nセグメント録画完了！")
        
        stats = recorder.get_recording_stats()
        print(f"作成セグメント数: {stats['segments_created']}")
    else:
        print("録画開始失敗")

def demo_interactive_recording():
    """インタラクティブ録画デモ"""
    print("\n=== インタラクティブ録画デモ ===")
    print("手動で録画開始・停止を制御できます")
    
    recorder = VideoRecorder("sub")
    
    print("\nコマンド:")
    print("  's' : 録画開始")
    print("  't' : 録画停止")
    print("  'q' : 終了")
    
    try:
        while True:
            command = input("\nコマンドを入力: ").strip().lower()
            
            if command == 's':
                if not recorder.is_recording:
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    if recorder.start_recording(f"interactive_{timestamp}"):
                        print("録画開始！")
                    else:
                        print("録画開始失敗")
                else:
                    print("既に録画中です")
            
            elif command == 't':
                if recorder.is_recording:
                    recorder.stop_recording()
                    print("録画停止")
                else:
                    print("録画していません")
            
            elif command == 'q':
                break
            
            else:
                print("無効なコマンドです")
            
            # 録画状態表示
            if recorder.is_recording:
                stats = recorder.get_recording_stats()
                print(f"録画状態: 時間{stats['duration']:.1f}s, "
                      f"フレーム{stats['total_frames']}")
    
    except KeyboardInterrupt:
        print("\n中断されました")
    
    finally:
        if recorder.is_recording:
            recorder.stop_recording()
            print("録画を停止しました")

def main():
    """録画デモメイン"""
    print("=== RLC-510A 録画機能デモ ===")
    print("このデモでは、様々な録画機能を試すことができます")
    print()
    
    # ログ設定
    logging.basicConfig(level=logging.INFO)
    
    # デモ選択
    print("デモを選択してください:")
    print("1. 基本録画デモ (30秒自動録画)")
    print("2. セグメント録画デモ (10秒毎分割)")
    print("3. インタラクティブ録画デモ (手動制御)")
    print("4. 全てのデモを順番に実行")
    
    while True:
        choice = input("選択 (1-4): ").strip()
        if choice in ["1", "2", "3", "4"]:
            break
        print("無効な選択です。1-4を入力してください。")
    
    try:
        if choice == "1":
            demo_basic_recording()
        elif choice == "2":
            demo_segment_recording()
        elif choice == "3":
            demo_interactive_recording()
        elif choice == "4":
            demo_basic_recording()
            input("\n次のデモに進むにはEnterを押してください...")
            demo_segment_recording()
            input("\n次のデモに進むにはEnterを押してください...")
            demo_interactive_recording()
        
        print("\n録画デモ完了！")
        print("録画ファイルは 'output/recordings' フォルダに保存されています。")
    
    except KeyboardInterrupt:
        print("\nデモが中断されました")

if __name__ == "__main__":
    main()