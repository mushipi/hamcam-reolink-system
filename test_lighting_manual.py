#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
照明検出機能の手動テスト
実際の画像で動作確認
"""

import sys
import os
# UTF-8エンコーディング強制設定
if sys.stdout.encoding != 'UTF-8':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np
from phase3_hamster_tracking.utils.lighting_detector import LightingModeDetector, SimpleLightingDetector

def test_ir_simulation():
    """IRシミュレーション画像テスト"""
    print("=== IRシミュレーション画像テスト ===")
    
    # グレースケール画像作成（IRシミュレーション）
    gray_value = 128
    ir_frame = np.full((480, 640, 3), gray_value, dtype=np.uint8)
    
    # 軽量版で確認
    simple_detector = SimpleLightingDetector(threshold=0.9)
    mode, confidence = simple_detector.detect_mode(ir_frame)
    
    print(f"軽量版: {mode} (信頼度: {confidence:.3f})")
    
    # 詳細版で確認
    detector = LightingModeDetector()
    mode, confidence, details = detector.detect_mode(ir_frame)
    
    print(f"詳細版: {mode} (信頼度: {confidence:.3f})")
    print(f"RGB相関: {details['rgb_correlation']:.3f}")
    print(f"処理時間: {details['processing_time_ms']:.1f}ms")

def test_color_simulation():
    """カラーシミュレーション画像テスト"""
    print("\n=== カラーシミュレーション画像テスト ===")
    
    # カラフルな画像作成
    color_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # グラデーション作成
    for y in range(480):
        for x in range(640):
            color_frame[y, x] = [
                int(255 * x / 640),      # B
                int(255 * y / 480),      # G  
                int(255 * (x + y) / (640 + 480))  # R
            ]
    
    # 軽量版で確認
    simple_detector = SimpleLightingDetector(threshold=0.9)
    mode, confidence = simple_detector.detect_mode(color_frame)
    
    print(f"軽量版: {mode} (信頼度: {confidence:.3f})")
    
    # 詳細版で確認
    detector = LightingModeDetector()
    mode, confidence, details = detector.detect_mode(color_frame)
    
    print(f"詳細版: {mode} (信頼度: {confidence:.3f})")
    print(f"RGB相関: {details['rgb_correlation']:.3f}")
    print(f"処理時間: {details['processing_time_ms']:.1f}ms")

def test_real_ir_characteristics():
    """本物のIR特性テスト"""
    print("\n=== 本物のIR特性テスト ===")
    
    # より現実的なIR画像（高コントラスト）
    ir_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # IRの特徴：明暗のはっきりした領域
    # 背景（暗い）
    ir_frame[:, :] = [30, 30, 30]
    
    # 明るい部分（反射・熱源）
    cv2.rectangle(ir_frame, (100, 100), (200, 200), (200, 200, 200), -1)
    cv2.rectangle(ir_frame, (300, 200), (400, 350), (180, 180, 180), -1)
    cv2.circle(ir_frame, (500, 300), 50, (220, 220, 220), -1)
    
    # ノイズ追加
    noise = np.random.normal(0, 5, ir_frame.shape).astype(np.int16)
    ir_frame = np.clip(ir_frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    
    detector = LightingModeDetector()
    mode, confidence, details = detector.detect_mode(ir_frame)
    
    print(f"リアルIR: {mode} (信頼度: {confidence:.3f})")
    print(f"RGB相関: {details['rgb_correlation']:.3f}")
    print(f"エッジ密度: {details['edge_density']:.3f}")

def test_camera_image_characteristics():
    """カメラ風画像の特性テスト"""
    print("\n=== カメラ風画像特性テスト ===")
    
    # カメラ風のカラー画像
    camera_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # 背景（青空風）
    camera_frame[:, :] = [180, 120, 60]  # 薄い青
    
    # オブジェクト（緑・茶色）
    cv2.rectangle(camera_frame, (50, 300), (200, 450), (40, 150, 40), -1)  # 緑
    cv2.rectangle(camera_frame, (400, 350), (550, 450), (60, 100, 140), -1)  # 茶色
    
    # テクスチャ追加
    noise = np.random.normal(0, 10, camera_frame.shape).astype(np.int16)
    camera_frame = np.clip(camera_frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    
    detector = LightingModeDetector()
    mode, confidence, details = detector.detect_mode(camera_frame)
    
    print(f"カメラ風: {mode} (信頼度: {confidence:.3f})")
    print(f"RGB相関: {details['rgb_correlation']:.3f}")
    print(f"色相多様性: {details['hue_diversity']:.3f}")

def test_rgb_correlation_manually():
    """RGB相関の手動計算確認"""
    print("\n=== RGB相関手動計算 ===")
    
    # 完全グレースケール
    gray_img = np.full((100, 100, 3), 128, dtype=np.uint8)
    b, g, r = cv2.split(gray_img)
    
    corr_bg = np.corrcoef(b.flatten(), g.flatten())[0, 1]
    corr_br = np.corrcoef(b.flatten(), r.flatten())[0, 1]
    corr_gr = np.corrcoef(g.flatten(), r.flatten())[0, 1]
    
    print(f"完全グレースケール相関: BG={corr_bg:.3f}, BR={corr_br:.3f}, GR={corr_gr:.3f}")
    
    # カラー画像
    color_img = np.zeros((100, 100, 3), dtype=np.uint8)
    color_img[:, :, 0] = 255  # 青
    color_img[:, :, 1] = 128  # 緑
    color_img[:, :, 2] = 64   # 赤
    
    b, g, r = cv2.split(color_img)
    
    try:
        corr_bg = np.corrcoef(b.flatten(), g.flatten())[0, 1]
        corr_br = np.corrcoef(b.flatten(), r.flatten())[0, 1]
        corr_gr = np.corrcoef(g.flatten(), r.flatten())[0, 1]
        
        print(f"単色カラー相関: BG={corr_bg:.3f}, BR={corr_br:.3f}, GR={corr_gr:.3f}")
    except:
        print("単色カラー: 相関計算不可（標準偏差0）")

if __name__ == "__main__":
    test_ir_simulation()
    test_color_simulation()
    test_real_ir_characteristics()
    test_camera_image_characteristics()
    test_rgb_correlation_manually()