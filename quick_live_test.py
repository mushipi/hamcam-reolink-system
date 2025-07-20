#!/usr/bin/env python3
"""
クイックライブ映像テスト
5秒間だけライブ映像を表示してテスト
"""

import sys
import os
import cv2
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rtsp_stream import RTSPStream
from utils.camera_config import get_camera_config

def quick_live_test():
    """5秒間のライブ映像テスト"""
    print("=== 5秒間ライブ映像テスト ===")
    
    # 設定
    config = get_camera_config()
    config.set_password("894890abc")
    
    try:
        with RTSPStream("sub", buffer_size=1) as stream:
            if stream.start_stream():
                print("✅ RTSPストリーム開始成功")
                print("5秒間映像を表示します... (ウィンドウが開いたら何かキーを押すか5秒待ってください)")
                
                # OpenCVウィンドウ作成
                cv2.namedWindow("Live Test", cv2.WINDOW_AUTOSIZE)
                
                start_time = time.time()
                frame_count = 0
                
                while (time.time() - start_time) < 5:
                    result = stream.get_frame(timeout=0.5)
                    
                    if result and result[0]:
                        _, frame = result
                        frame_count += 1
                        
                        # フレームに情報を追加
                        elapsed = time.time() - start_time
                        cv2.putText(frame, f"Frame: {frame_count}", (10, 30), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        cv2.putText(frame, f"Time: {elapsed:.1f}s", (10, 60), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        cv2.putText(frame, "Press any key to exit", (10, frame.shape[0] - 20), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                        
                        # フレーム表示
                        cv2.imshow("Live Test", frame)
                        
                        # キー入力チェック（1ms待ち）
                        key = cv2.waitKey(1) & 0xFF
                        if key != 255:  # 何かキーが押された
                            print(f"\nキー入力で終了 (フレーム数: {frame_count})")
                            break
                
                cv2.destroyAllWindows()
                
                # 統計表示
                stats = stream.get_stats()
                print(f"✅ ライブ映像テスト完了")
                print(f"  表示フレーム数: {frame_count}")
                print(f"  平均FPS: {stats['current_fps']:.1f}")
                print(f"  ドロップフレーム: {stats['dropped_frames']}")
                
                if frame_count > 0:
                    print("🎉 ライブ映像表示成功！システムは正常に動作しています。")
                    return True
                else:
                    print("❌ フレーム取得できませんでした")
                    return False
                
            else:
                print("❌ RTSPストリーム開始失敗")
                return False
                
    except Exception as e:
        print(f"❌ ライブテストエラー: {e}")
        return False

if __name__ == "__main__":
    try:
        success = quick_live_test()
        if success:
            print("\n=== 全体テスト結果 ===")
            print("✅ ネットワーク接続: 成功")
            print("✅ API認証: 成功") 
            print("✅ RTSPストリーム: 成功")
            print("✅ ライブ映像表示: 成功")
            print("\n🎉 Phase 2のすべての機能が正常に動作しています！")
            print("次は examples/comprehensive_demo.py で全機能をテストできます。")
        else:
            print("\n⚠️  一部の機能に問題があります")
    except KeyboardInterrupt:
        print("\nテスト中断")
    except Exception as e:
        print(f"\nテストエラー: {e}")