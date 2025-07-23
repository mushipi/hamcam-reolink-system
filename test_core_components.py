#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 3 コアコンポーネント統合テスト
座標校正、動作検出、品質評価システムの基本動作確認
"""

import os
import sys
import cv2
import numpy as np
import time
import logging
from datetime import datetime

# プロジェクトパスを追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# プロジェクトモジュール
from phase3_hamster_tracking.utils.hamster_config import load_config
from phase3_hamster_tracking.hamster_tracking.coordinate_calibrator import CoordinateCalibrator
from phase3_hamster_tracking.data_collection.motion_detector import MotionDetector
from phase3_hamster_tracking.data_collection.data_quality import DataQualityAssessor
from rtsp_stream import RTSPStream

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_coordinate_calibration():
    """座標校正システムテスト"""
    print("=== 座標校正システムテスト ===")
    
    try:
        # 設定読み込み
        config = load_config()
        logger.info(f"設定読み込み完了: ケージサイズ {config.cage.width}x{config.cage.height}mm")
        
        # 座標校正器初期化
        calibrator = CoordinateCalibrator(config)
        logger.info("座標校正器初期化成功")
        
        # テスト用の校正点（仮想的な4点）
        test_corners = [
            (100, 80),   # 左上
            (540, 85),   # 右上  
            (545, 395),  # 右下
            (95, 390)    # 左下
        ]
        
        # 既に校正済みの場合はテストをスキップ
        if calibrator.is_calibrated:
            logger.info("✅ 既に校正済み - 座標変換テストを実行")
            
            # 変換テスト
            test_pixel = (320, 240)  # 画面中央
            world_pos = calibrator.pixel_to_mm(test_pixel)
            if world_pos:
                logger.info(f"座標変換テスト: {test_pixel} -> ({world_pos[0]:.2f}, {world_pos[1]:.2f})mm座標")
                
                # 逆変換テスト
                pixel_pos = calibrator.mm_to_pixel(world_pos)
                if pixel_pos:
                    error = np.sqrt((test_pixel[0] - pixel_pos[0])**2 + (test_pixel[1] - pixel_pos[1])**2)
                    logger.info(f"逆変換テスト: ({world_pos[0]:.2f}, {world_pos[1]:.2f})mm -> {pixel_pos}, 誤差: {error:.1f}px")
                    
                    if error < 5.0:
                        logger.info("✅ 座標変換精度良好")
                        return True
                    else:
                        logger.warning(f"⚠️ 座標変換精度要改善: 誤差{error:.1f}px")
                else:
                    logger.error("❌ 逆座標変換失敗")
            else:
                logger.error("❌ 座標変換失敗")
        else:
            # 新規校正テスト
            logger.info("新規校正テストを実行")
            try:
                calibration_result = calibrator.calibrate_manual_4point(test_corners)
                if calibration_result:
                    logger.info(f"✅ 座標校正成功 - RMSE誤差: {calibration_result.rmse_error:.2f}mm")
                    return True
                else:
                    logger.error("❌ 座標校正失敗")
            except Exception as calib_error:
                logger.error(f"❌ 校正実行エラー: {calib_error}")
                # 既存の校正を使用してテスト継続
                if calibrator.is_calibrated:
                    logger.info("既存の校正でテスト継続")
                    test_pixel = (320, 240)
                    world_pos = calibrator.pixel_to_mm(test_pixel)
                    if world_pos:
                        logger.info(f"座標変換テスト: {test_pixel} -> ({world_pos[0]:.2f}, {world_pos[1]:.2f})mm")
                        return True
            
    except Exception as e:
        logger.error(f"❌ 座標校正テストエラー: {e}")
        import traceback
        traceback.print_exc()
    
    return False

def test_motion_detection():
    """動作検出システムテスト"""
    print("\n=== 動作検出システムテスト ===")
    
    try:
        # 設定読み込み
        config = load_config()
        
        # 動作検出器初期化
        motion_detector = MotionDetector(config)
        logger.info("動作検出器初期化成功")
        
        # RTSPストリーム開始
        stream = RTSPStream("sub", buffer_size=1)
        
        # パスワード設定
        from utils.camera_config import get_camera_config
        camera_config = get_camera_config()
        if not camera_config.password:
            camera_config.set_password("894890abc")
        
        if not stream.start_stream():
            logger.error("❌ RTSPストリーム開始失敗")
            return False
        
        logger.info("✅ RTSPストリーム開始成功")
        
        # 動作検出テスト（30秒間）
        test_duration = 30
        start_time = time.time()
        frame_count = 0
        motion_count = 0
        
        logger.info(f"動作検出テスト開始 ({test_duration}秒間)")
        
        while time.time() - start_time < test_duration:
            result = stream.get_frame(timeout=2.0)
            if not result or not result[0]:
                continue
            
            success, frame = result
            frame_count += 1
            
            # 動作検出実行
            motion_events = motion_detector.detect_motion(frame)
            
            if motion_events:
                motion_count += len(motion_events)
                for event in motion_events:
                    logger.info(f"動作検出: {event.motion_type} @ {event.center}, "
                              f"速度: {event.velocity_mm:.1f}mm/s, 信頼度: {event.confidence:.2f}")
            
            time.sleep(0.1)
        
        stream.stop_stream()
        
        # 統計情報
        stats = motion_detector.get_stats()
        logger.info(f"テスト結果: {frame_count}フレーム処理, {motion_count}回動作検出")
        logger.info(f"統計: 総検出{stats['total_detections']}, 有効検出{stats['valid_detections']}")
        
        if frame_count > 0:
            logger.info("✅ 動作検出システム動作確認完了")
            return True
        else:
            logger.error("❌ フレーム処理なし")
            
    except Exception as e:
        logger.error(f"❌ 動作検出テストエラー: {e}")
        import traceback
        traceback.print_exc()
    
    return False

def test_data_quality_assessment():
    """品質評価システムテスト"""
    print("\n=== 品質評価システムテスト ===")
    
    try:
        # 設定読み込み
        config = load_config()
        
        # 品質評価器初期化
        quality_assessor = DataQualityAssessor(config)
        logger.info("品質評価器初期化成功")
        
        # 既存の撮影画像をテスト
        import glob
        from pathlib import Path
        
        image_dir = Path("./data/raw_frames")
        if not image_dir.exists():
            logger.warning("撮影画像ディレクトリが見つかりません。RTSPから直接テストします。")
            
            # RTSPストリームから直接テスト
            stream = RTSPStream("sub", buffer_size=1)
            
            # パスワード設定
            from utils.camera_config import get_camera_config
            camera_config = get_camera_config()
            if not camera_config.password:
                camera_config.set_password("894890abc")
            
            if not stream.start_stream():
                logger.error("❌ RTSPストリーム開始失敗")
                return False
            
            # フレーム取得してテスト
            for i in range(5):
                result = stream.get_frame(timeout=2.0)
                if result and result[0]:
                    success, frame = result
                    
                    # 品質評価実行
                    quality_metrics = quality_assessor.evaluate_image_quality(frame, f"test_frame_{i}")
                    
                    logger.info(f"フレーム{i+1} 品質評価:")
                    logger.info(f"  総合スコア: {quality_metrics.overall_score:.3f}")
                    logger.info(f"  品質レベル: {quality_metrics.quality_level.value}")
                    logger.info(f"  ブラー: {quality_metrics.blur_score:.3f}")
                    logger.info(f"  輝度: {quality_metrics.brightness_score:.3f}")
                    logger.info(f"  ハムスター可視性: {quality_metrics.hamster_visibility_score:.3f}")
                
                time.sleep(1)
            
            stream.stop_stream()
            
        else:
            # 既存画像ファイルでテスト
            image_files = list(image_dir.glob("*.jpg"))
            logger.info(f"テスト対象画像: {len(image_files)}枚")
            
            tested_count = 0
            for image_path in image_files[:3]:  # 最大3枚テスト
                try:
                    image = cv2.imread(str(image_path))
                    if image is not None:
                        quality_metrics = quality_assessor.evaluate_image_quality(image, str(image_path))
                        
                        logger.info(f"{image_path.name} 品質評価:")
                        logger.info(f"  総合スコア: {quality_metrics.overall_score:.3f}")
                        logger.info(f"  品質レベル: {quality_metrics.quality_level.value}")
                        logger.info(f"  ブラー: {quality_metrics.blur_score:.3f}")
                        logger.info(f"  輝度: {quality_metrics.brightness_score:.3f}")
                        logger.info(f"  ハムスター可視性: {quality_metrics.hamster_visibility_score:.3f}")
                        
                        tested_count += 1
                        
                except Exception as e:
                    logger.error(f"画像読み込みエラー {image_path}: {e}")
            
            if tested_count > 0:
                logger.info(f"✅ 品質評価システムテスト完了 ({tested_count}枚処理)")
                return True
        
        # 統計情報確認
        stats = quality_assessor.get_stats()
        if stats.get('total_evaluated', 0) > 0:
            logger.info(f"品質評価統計: 評価済み{stats['total_evaluated']}枚, "
                      f"平均スコア{stats['average_overall_score']:.2f}")
            logger.info("✅ 品質評価システム動作確認完了")
            return True
            
    except Exception as e:
        logger.error(f"❌ 品質評価テストエラー: {e}")
        import traceback
        traceback.print_exc()
    
    return False

def main():
    """メイン関数"""
    print("=== Phase 3 コアコンポーネント統合テスト ===")
    print(f"テスト開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # テスト結果
    results = {}
    
    try:
        # 1. 座標校正システムテスト
        results['coordinate_calibration'] = test_coordinate_calibration()
        
        # 2. 動作検出システムテスト
        results['motion_detection'] = test_motion_detection()
        
        # 3. 品質評価システムテスト
        results['quality_assessment'] = test_data_quality_assessment()
        
    except KeyboardInterrupt:
        logger.info("テスト中断（Ctrl+C）")
    except Exception as e:
        logger.error(f"テスト実行エラー: {e}")
        import traceback
        traceback.print_exc()
    
    # 結果サマリー
    print("\n" + "="*50)
    print("=== テスト結果サマリー ===")
    for component, success in results.items():
        status = "✅ 成功" if success else "❌ 失敗"
        print(f"{component}: {status}")
    
    success_count = sum(results.values())
    total_count = len(results)
    print(f"\n総合結果: {success_count}/{total_count} 成功")
    
    if success_count == total_count:
        print("🎉 全コンポーネントのテストが成功しました！")
        return True
    else:
        print("⚠️ 一部のテストが失敗しました。ログを確認してください。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)