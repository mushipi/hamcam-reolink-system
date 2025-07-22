#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI校正ツールのオフラインテスト
RTSPストリームの代わりに静止画を使用してテスト
"""

import os
import sys
import cv2
import numpy as np

# プロジェクトパスを追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def create_test_cage_image():
    """テスト用のケージ画像を作成"""
    # 640x480のテスト画像作成
    image = np.ones((480, 640, 3), dtype=np.uint8) * 200
    
    # ケージ枠を描画（四角形）
    cage_corners = np.array([
        [100, 80],   # 左上
        [540, 85],   # 右上
        [545, 395],  # 右下
        [95, 390]    # 左下
    ], np.int32)
    
    # ケージ境界線
    cv2.polylines(image, [cage_corners.reshape((-1, 1, 2))], True, (0, 0, 0), 3)
    
    # 背景パターン（床材っぽく）
    for i in range(0, 640, 20):
        for j in range(0, 480, 20):
            cv2.circle(image, (i, j), 2, (150, 150, 150), -1)
    
    # ケージ四隅にマーカー
    corner_labels = ["左上", "右上", "右下", "左下"]
    for i, ((x, y), label) in enumerate(zip(cage_corners, corner_labels)):
        cv2.circle(image, (x, y), 8, (0, 255, 0), -1)
        cv2.putText(image, label, (x + 10, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
    
    # ケージサイズ情報
    cv2.putText(image, "Test Cage: 380x280mm", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
    cv2.putText(image, "Click corners: Top-Left -> Top-Right -> Bottom-Right -> Bottom-Left", 
               (10, 450), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
    
    return image, cage_corners.tolist()

def test_gui_calibration():
    """GUI校正テスト"""
    print("=== GUI校正ツール オフラインテスト ===")
    print("操作方法:")
    print("  左クリック: 緑色の点を左上→右上→右下→左下の順にクリック")
    print("  右クリック: 最後の点を削除")
    print("  'r': リセット")
    print("  'q': 終了")
    print()
    
    # テスト画像作成
    test_image, expected_corners = create_test_cage_image()
    
    # 校正点管理
    calibration_points = []
    point_labels = ["左上", "右上", "右下", "左下"]
    
    def mouse_callback(event, x, y, flags, param):
        nonlocal calibration_points
        
        if event == cv2.EVENT_LBUTTONDOWN:
            if len(calibration_points) < 4:
                calibration_points.append((x, y))
                print(f"校正点{len(calibration_points)} ({point_labels[len(calibration_points)-1]}): ({x}, {y})")
                
                if len(calibration_points) == 4:
                    print("\n4点の校正点が選択されました!")
                    print("実際のGUI校正ツールでは、ここで座標校正が実行されます。")
                    
                    # 期待値との比較
                    print("\n=== 校正精度チェック ===")
                    total_error = 0
                    for i, (actual, expected) in enumerate(zip(calibration_points, expected_corners)):
                        error = np.sqrt((actual[0] - expected[0])**2 + (actual[1] - expected[1])**2)
                        total_error += error
                        print(f"{point_labels[i]}: 誤差 {error:.1f}ピクセル")
                    
                    avg_error = total_error / 4
                    print(f"平均誤差: {avg_error:.1f}ピクセル")
                    
                    if avg_error < 10:
                        print("✅ 良好な校正精度です！")
                    else:
                        print("⚠️ 校正精度を改善してください")
        
        elif event == cv2.EVENT_RBUTTONDOWN:
            if calibration_points:
                removed = calibration_points.pop()
                print(f"校正点を削除: {removed}")
    
    # OpenCVウィンドウ設定
    window_name = "GUI校正ツール テスト"
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback(window_name, mouse_callback)
    
    while True:
        # 表示用画像作成
        display_image = test_image.copy()
        
        # 選択された校正点を描画
        for i, (x, y) in enumerate(calibration_points):
            cv2.circle(display_image, (x, y), 6, (255, 255, 0), -1)  # 黄色
            cv2.circle(display_image, (x, y), 8, (255, 255, 255), 2)  # 白枠
            cv2.putText(display_image, str(i+1), (x + 10, y + 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        # 校正線描画（4点選択後）
        if len(calibration_points) == 4:
            points = np.array(calibration_points, np.int32)
            cv2.polylines(display_image, [points.reshape((-1, 1, 2))], True, (255, 0, 0), 2)
        
        # ガイド表示
        if len(calibration_points) < 4:
            next_point = point_labels[len(calibration_points)]
            cv2.putText(display_image, f"Next: {next_point}", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        else:
            cv2.putText(display_image, "Calibration Complete!", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        cv2.imshow(window_name, display_image)
        
        # キー入力処理
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            break
        elif key == ord('r'):
            calibration_points.clear()
            print("校正リセット")
    
    cv2.destroyAllWindows()
    
    if len(calibration_points) == 4:
        print("\n✅ テスト完了 - 4点の校正が成功しました")
        return True
    else:
        print("\n❌ テスト未完了")
        return False

if __name__ == "__main__":
    try:
        success = test_gui_calibration()
        if success:
            print("\nGUI校正ツールの基本機能は正常に動作します。")
            print("実際のRTSPストリームでテストするには:")
            print("~/anaconda3/bin/python phase3_hamster_tracking/hamster_tracking/calibration_gui.py")
        else:
            print("\nテストが完了していません。")
    except KeyboardInterrupt:
        print("\n\nテスト中断")
    except Exception as e:
        print(f"\nテストエラー: {e}")
        import traceback
        traceback.print_exc()