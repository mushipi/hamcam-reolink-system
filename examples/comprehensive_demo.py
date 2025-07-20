#!/usr/bin/env python3
"""
総合デモアプリケーション
Phase 2で実装した全機能を統合したデモ
"""

import sys
import os
import time
import threading
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from video_viewer import AdvancedVideoViewer
from video_recorder import VideoRecorder  
from snapshot import SnapshotCapture
from event_monitor import EventMonitor
from rtsp_stream import RTSPStream
import logging

class ComprehensiveDemo:
    """総合デモクラス"""
    
    def __init__(self):
        self.is_running = False
        self.logger = logging.getLogger("ComprehensiveDemo")
        
        # 各機能のインスタンス
        self.recorder = None
        self.snapshot = None
        self.event_monitor = None
        self.stream = None
    
    def run_feature_showcase(self):
        """機能ショーケース"""
        print("=== RLC-510A カメラシステム 機能ショーケース ===")
        print()
        
        features = [
            self.demo_rtsp_stream,
            self.demo_snapshot_capture,
            self.demo_video_recording,
            self.demo_event_monitoring
        ]
        
        for i, feature_demo in enumerate(features, 1):
            print(f"\n【機能 {i}/{len(features)}】")
            try:
                feature_demo()
                input("\n次の機能デモに進むにはEnterキーを押してください...")
            except KeyboardInterrupt:
                print("\nデモが中断されました")
                return
            except Exception as e:
                print(f"エラーが発生しました: {e}")
                input("続行するにはEnterキーを押してください...")
        
        print("\n🎉 全機能のデモが完了しました！")
    
    def demo_rtsp_stream(self):
        """RTSPストリームデモ"""
        print("RTSPストリーム接続デモ")
        print("- リアルタイム映像ストリーミング")
        print("- フレーム取得とバッファリング")
        
        self.stream = RTSPStream("sub", buffer_size=2)
        
        if self.stream.start_stream():
            print("✅ ストリーム開始成功")
            
            # 10秒間のフレーム取得テスト
            print("10秒間のフレーム取得テスト...")
            start_time = time.time()
            frame_count = 0
            
            while (time.time() - start_time) < 10:
                result = self.stream.get_frame(timeout=0.5)
                if result and result[0]:
                    frame_count += 1
                    if frame_count % 10 == 0:
                        stats = self.stream.get_stats()
                        print(f"フレーム数: {frame_count}, FPS: {stats['current_fps']:.1f}")
                time.sleep(0.1)
            
            print(f"✅ 合計 {frame_count} フレーム取得")
            self.stream.stop_stream()
        else:
            print("❌ ストリーム開始失敗")
    
    def demo_snapshot_capture(self):
        """スナップショット撮影デモ"""
        print("スナップショット機能デモ")
        print("- RTSP方式とAPI方式での撮影")
        print("- 連続撮影機能")
        
        # RTSP方式
        print("\n1. RTSP方式で撮影...")
        snapshot_rtsp = SnapshotCapture("rtsp", "main")
        if snapshot_rtsp.initialize():
            filepath = snapshot_rtsp.capture_snapshot("demo_comprehensive_rtsp.jpg")
            if filepath:
                print(f"✅ RTSP撮影成功: {os.path.basename(filepath)}")
            else:
                print("❌ RTSP撮影失敗")
            snapshot_rtsp.cleanup()
        
        # API方式
        print("\n2. API方式で撮影...")
        snapshot_api = SnapshotCapture("api")
        if snapshot_api.initialize():
            filepath = snapshot_api.capture_snapshot("demo_comprehensive_api.jpg")
            if filepath:
                print(f"✅ API撮影成功: {os.path.basename(filepath)}")
            else:
                print("❌ API撮影失敗")
            snapshot_api.cleanup()
        
        # 連続撮影
        print("\n3. 連続撮影（3枚）...")
        snapshot_burst = SnapshotCapture("rtsp", "sub")
        if snapshot_burst.initialize():
            results = snapshot_burst.capture_burst(3, 1.0, "demo_comprehensive_burst")
            print(f"✅ 連続撮影完了: {len(results)}/3枚成功")
            snapshot_burst.cleanup()
    
    def demo_video_recording(self):
        """映像録画デモ"""
        print("映像録画機能デモ")
        print("- 基本録画機能")
        print("- セグメント分割録画")
        
        # 基本録画（15秒）
        print("\n1. 基本録画（15秒）...")
        recorder = VideoRecorder("sub", duration=15)
        
        if recorder.start_recording("demo_comprehensive"):
            print("録画開始...")
            
            # 進捗表示
            start_time = time.time()
            while recorder.is_recording:
                elapsed = time.time() - start_time
                print(f"\r録画中... {elapsed:.1f}秒", end="")
                time.sleep(0.5)
            
            stats = recorder.get_recording_stats()
            print(f"\n✅ 録画完了: {stats['total_frames']}フレーム, {stats['average_fps']:.1f}FPS")
        else:
            print("❌ 録画開始失敗")
        
        # セグメント録画（20秒、5秒毎分割）
        print("\n2. セグメント録画（20秒、5秒毎分割）...")
        recorder_seg = VideoRecorder("sub", duration=20, segment_duration=5)
        
        if recorder_seg.start_recording("demo_comprehensive_seg"):
            start_time = time.time()
            while recorder_seg.is_recording:
                elapsed = time.time() - start_time
                stats = recorder_seg.get_recording_stats()
                print(f"\r録画中... {elapsed:.1f}秒, セグメント: {stats['segments_created']}", end="")
                time.sleep(0.5)
            
            stats = recorder_seg.get_recording_stats()
            print(f"\n✅ セグメント録画完了: {stats['segments_created']}セグメント作成")
        else:
            print("❌ セグメント録画開始失敗")
    
    def demo_event_monitoring(self):
        """イベント監視デモ"""
        print("イベント監視機能デモ")
        print("- モーション検知監視")
        print("- AI検知イベント監視")
        print("- イベント履歴記録")
        
        # イベント監視（30秒間）
        monitor = EventMonitor(poll_interval=2)
        
        if monitor.initialize():
            print("✅ イベント監視初期化成功")
            
            # 検知設定確認
            motion_config = monitor.get_motion_detection_config()
            ai_config = monitor.get_ai_detection_config()
            
            print(f"モーション検知: {'有効' if motion_config.get('enable') else '無効'}")
            print(f"AI検知設定取得: {'成功' if ai_config else '失敗'}")
            
            # 30秒間監視
            print("\n30秒間のイベント監視...")
            monitor.start_monitoring()
            
            start_time = time.time()
            last_stats_time = 0
            
            while (time.time() - start_time) < 30:
                current_time = time.time()
                
                # 5秒毎に統計表示
                if (current_time - last_stats_time) >= 5:
                    stats = monitor.get_event_stats()
                    elapsed = current_time - start_time
                    print(f"\r監視中... {elapsed:.0f}秒, イベント数: {stats['total_events']}", end="")
                    last_stats_time = current_time
                
                time.sleep(0.5)
            
            monitor.stop_monitoring()
            
            # 最終統計
            stats = monitor.get_event_stats()
            print(f"\n✅ 監視完了")
            print(f"総イベント数: {stats['total_events']}")
            print(f"イベント内訳: {stats['event_counts']}")
        else:
            print("❌ イベント監視初期化失敗")
    
    def run_interactive_mode(self):
        """インタラクティブモード"""
        print("=== インタラクティブモード ===")
        print("各機能を個別に試すことができます")
        print()
        
        while True:
            print("\n利用可能な機能:")
            print("1. ライブ映像表示")
            print("2. スナップショット撮影")
            print("3. 映像録画")
            print("4. イベント監視")
            print("5. 機能ショーケース")
            print("6. 終了")
            
            choice = input("\n機能を選択 (1-6): ").strip()
            
            try:
                if choice == "1":
                    self.interactive_live_view()
                elif choice == "2":
                    self.interactive_snapshot()
                elif choice == "3":
                    self.interactive_recording()
                elif choice == "4":
                    self.interactive_monitoring()
                elif choice == "5":
                    self.run_feature_showcase()
                elif choice == "6":
                    break
                else:
                    print("無効な選択です")
            
            except KeyboardInterrupt:
                print("\n操作が中断されました")
            except Exception as e:
                print(f"エラーが発生しました: {e}")
    
    def interactive_live_view(self):
        """インタラクティブライブ表示"""
        print("\nライブ映像表示を開始します...")
        print("ウィンドウが開いたら、'q'キーで終了してください")
        
        viewer = AdvancedVideoViewer("sub", enable_recording=True)
        viewer.start_display()
    
    def interactive_snapshot(self):
        """インタラクティブスナップショット"""
        method = input("撮影方式を選択 (rtsp/api): ").strip().lower()
        if method not in ["rtsp", "api"]:
            method = "rtsp"
        
        stream_type = "main"
        if method == "rtsp":
            stream_type = input("ストリーム (main/sub): ").strip().lower()
            if stream_type not in ["main", "sub"]:
                stream_type = "main"
        
        capture = SnapshotCapture(method, stream_type)
        if capture.initialize():
            filepath = capture.capture_snapshot()
            if filepath:
                print(f"撮影成功: {os.path.basename(filepath)}")
            else:
                print("撮影失敗")
            capture.cleanup()
        else:
            print("初期化失敗")
    
    def interactive_recording(self):
        """インタラクティブ録画"""
        try:
            duration = int(input("録画時間（秒）: ").strip())
        except ValueError:
            duration = 30
        
        stream_type = input("ストリーム (main/sub): ").strip().lower()
        if stream_type not in ["main", "sub"]:
            stream_type = "sub"
        
        recorder = VideoRecorder(stream_type, duration=duration)
        
        if recorder.start_recording("interactive"):
            print(f"{duration}秒間録画中...")
            
            start_time = time.time()
            while recorder.is_recording:
                elapsed = time.time() - start_time
                print(f"\r録画中... {elapsed:.1f}/{duration}秒", end="")
                time.sleep(0.5)
            
            print("\n録画完了")
        else:
            print("録画開始失敗")
    
    def interactive_monitoring(self):
        """インタラクティブ監視"""
        try:
            duration = int(input("監視時間（秒）: ").strip())
        except ValueError:
            duration = 60
        
        monitor = EventMonitor(poll_interval=3)
        
        if monitor.initialize():
            print(f"{duration}秒間監視中...")
            monitor.start_monitoring()
            
            start_time = time.time()
            while (time.time() - start_time) < duration:
                elapsed = time.time() - start_time
                stats = monitor.get_event_stats()
                print(f"\r監視中... {elapsed:.0f}/{duration}秒, イベント: {stats['total_events']}", end="")
                time.sleep(1)
            
            monitor.stop_monitoring()
            
            stats = monitor.get_event_stats()
            print(f"\n監視完了 - 総イベント数: {stats['total_events']}")
        else:
            print("監視初期化失敗")

def main():
    """メイン関数"""
    print("=== RLC-510A カメラシステム 総合デモ ===")
    print()
    print("このデモでは、Phase 2で実装した全機能を試すことができます:")
    print("• RTSPストリーム映像取得")
    print("• ライブ映像表示・録画")  
    print("• スナップショット撮影")
    print("• イベント監視・検知")
    print()
    
    # ログ設定
    logging.basicConfig(level=logging.INFO,
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    demo = ComprehensiveDemo()
    
    # 動作モード選択
    print("動作モードを選択してください:")
    print("1. 機能ショーケース（全機能を順番にデモ）")
    print("2. インタラクティブモード（個別機能を自由に試用）")
    
    while True:
        choice = input("選択 (1-2): ").strip()
        if choice in ["1", "2"]:
            break
        print("1または2を入力してください")
    
    try:
        if choice == "1":
            demo.run_feature_showcase()
        else:
            demo.run_interactive_mode()
        
        print("\n総合デモ終了")
        print("生成されたファイルは 'output' フォルダ内に保存されています")
    
    except KeyboardInterrupt:
        print("\n\nデモが中断されました")
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")

if __name__ == "__main__":
    main()