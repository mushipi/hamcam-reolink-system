#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI座標校正ツール
RTSPストリームからの映像を使用してインタラクティブな4点校正を行う
"""

import os
import sys
# UTF-8エンコーディング強制設定
if sys.stdout.encoding != 'UTF-8':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

import cv2
import numpy as np
import argparse
import time
from typing import List, Tuple, Optional, Dict, Any
import logging
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# プロジェクトモジュール
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from phase3_hamster_tracking.utils.hamster_config import HamsterTrackingConfig, load_config
from phase3_hamster_tracking.hamster_tracking.coordinate_calibrator import CoordinateCalibrator
from rtsp_stream import RTSPStream

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 日本語表示用関数（既存のものを再利用）
def put_japanese_text(image, text, position, font_size=20, color=(255, 255, 255)):
    """OpenCV画像に日本語テキストを描画"""
    try:
        pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_image)
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", font_size)
        except:
            try:
                font = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", font_size)
            except:
                font = ImageFont.load_default()
        
        pil_color = (color[2], color[1], color[0])
        draw.text(position, text, font=font, fill=pil_color)
        
        return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    
    except Exception as e:
        fallback_text = text.encode('ascii', 'replace').decode('ascii')
        cv2.putText(image, fallback_text, position, cv2.FONT_HERSHEY_SIMPLEX, 
                   font_size/30, color, 1)
        return image

class CalibrationGUI:
    """GUI座標校正システム"""
    
    def __init__(self, config: HamsterTrackingConfig = None, stream_type: str = "sub"):
        """
        初期化
        
        Args:
            config: ハムスター管理システム設定
            stream_type: RTSPストリーム種別
        """
        self.config = config if config else load_config()
        self.stream_type = stream_type
        self.calibrator = CoordinateCalibrator(self.config)
        
        # GUI状態管理
        self.calibration_points: List[Tuple[int, int]] = []
        self.current_frame: Optional[np.ndarray] = None
        self.display_frame: Optional[np.ndarray] = None
        self.mouse_pos: Tuple[int, int] = (0, 0)
        self.is_calibrated: bool = False
        self.calibration_result = None
        
        # GUI設定
        self.window_name = "ハムスターケージ校正ツール"
        self.colors = {
            'point': (0, 255, 0),      # 緑（校正点）
            'current': (0, 255, 255),  # 黄（現在選択中）
            'line': (255, 0, 0),       # 青（境界線）
            'text': (255, 255, 255),   # 白（テキスト）
            'bg': (0, 0, 0),           # 黒（背景）
            'grid': (128, 128, 128)    # グレー（グリッド）
        }
        
        # ケージ情報
        self.cage_size = (self.config.cage.width, self.config.cage.height)
        
        logger.info(f"GUI校正ツール初期化完了 - ケージサイズ: {self.cage_size[0]}x{self.cage_size[1]}mm")
    
    def mouse_callback(self, event, x, y, flags, param):
        """マウスコールバック関数"""
        self.mouse_pos = (x, y)
        
        if event == cv2.EVENT_LBUTTONDOWN:
            if len(self.calibration_points) < 4:
                # 新しい校正点を追加
                self.calibration_points.append((x, y))
                logger.info(f"校正点{len(self.calibration_points)}を追加: ({x}, {y})")
                
                if len(self.calibration_points) == 4:
                    logger.info("4点の校正点が選択されました。校正を実行...")
                    self._perform_calibration()
        
        elif event == cv2.EVENT_RBUTTONDOWN:
            # 最後の点を削除
            if self.calibration_points:
                removed = self.calibration_points.pop()
                logger.info(f"校正点を削除: {removed}")
                self.is_calibrated = False
                self.calibration_result = None
    
    def _perform_calibration(self):
        """校正実行"""
        try:
            self.calibration_result = self.calibrator.calibrate_manual_4point(self.calibration_points)
            self.is_calibrated = True
            
            # 校正データ保存
            self.calibrator.save_calibration()
            
            # 校正精度検証
            validation = self.calibrator.validate_calibration()
            
            logger.info(f"校正完了! RMSE誤差: {self.calibration_result.rmse_error:.2f}mm")
            logger.info(f"校正検証: 距離誤差 {validation['distance_error_mm']:.2f}mm")
            
        except Exception as e:
            logger.error(f"校正エラー: {e}")
            self.is_calibrated = False
    
    def _draw_calibration_overlay(self, frame: np.ndarray) -> np.ndarray:
        """校正用オーバーレイ描画"""
        overlay = frame.copy()
        
        # 既存の校正点を描画
        point_labels = ["左上", "右上", "右下", "左下"]
        for i, (x, y) in enumerate(self.calibration_points):
            # 校正点の円
            cv2.circle(overlay, (x, y), 8, self.colors['point'], -1)
            cv2.circle(overlay, (x, y), 10, self.colors['text'], 2)
            
            # 点番号とラベル
            label = f"{i+1}: {point_labels[i]}"
            overlay = put_japanese_text(overlay, label, (x + 15, y - 10), 
                                      font_size=16, color=self.colors['text'])
        
        # ケージ境界線を描画（4点選択後）
        if len(self.calibration_points) == 4:
            points = np.array(self.calibration_points, np.int32)
            points = points.reshape((-1, 1, 2))
            cv2.polylines(overlay, [points], True, self.colors['line'], 2)
            
            # ケージ領域を半透明で塗りつぶし
            mask = np.zeros(frame.shape[:2], dtype=np.uint8)
            cv2.fillPoly(mask, [points], 255)
            colored_mask = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
            colored_mask[:, :, 0] = 0  # 青要素を削除
            overlay = cv2.addWeighted(overlay, 0.9, colored_mask, 0.1, 0)
        
        # 現在のマウス位置
        if len(self.calibration_points) < 4:
            cv2.circle(overlay, self.mouse_pos, 5, self.colors['current'], -1)
            
            # 次に選択すべき点のガイド
            next_point = len(self.calibration_points)
            guide_text = f"次の点: {point_labels[next_point]} をクリック"
            overlay = put_japanese_text(overlay, guide_text, (10, 30), 
                                      font_size=18, color=self.colors['current'])
        
        return overlay
    
    def _draw_calibration_info(self, frame: np.ndarray) -> np.ndarray:
        """校正情報表示"""
        info_frame = frame.copy()
        h, w = frame.shape[:2]
        
        # 情報パネル背景
        info_height = 120
        cv2.rectangle(info_frame, (0, h - info_height), (w, h), self.colors['bg'], -1)
        
        y_offset = h - info_height + 20
        
        # 基本情報
        cage_info = f"ケージサイズ: {self.cage_size[0]}×{self.cage_size[1]}mm"
        info_frame = put_japanese_text(info_frame, cage_info, (10, y_offset), 
                                     font_size=16, color=self.colors['text'])
        
        points_info = f"校正点: {len(self.calibration_points)}/4"
        info_frame = put_japanese_text(info_frame, points_info, (250, y_offset), 
                                     font_size=16, color=self.colors['text'])
        
        # 校正結果情報
        if self.is_calibrated and self.calibration_result:
            y_offset += 25
            accuracy_info = f"RMSE誤差: {self.calibration_result.rmse_error:.2f}mm"
            info_frame = put_japanese_text(info_frame, accuracy_info, (10, y_offset), 
                                         font_size=16, color=self.colors['point'])
            
            max_error_info = f"最大誤差: {self.calibration_result.max_error:.2f}mm"
            info_frame = put_japanese_text(info_frame, max_error_info, (250, y_offset), 
                                         font_size=16, color=self.colors['point'])
        
        # 操作ガイド
        y_offset += 25
        guide_text = "左クリック: 点選択 | 右クリック: 点削除 | 'r': リセット | 't': テスト | 'q': 終了"
        cv2.putText(info_frame, guide_text, (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 
                   0.5, self.colors['text'], 1)
        
        return info_frame
    
    def _draw_test_overlay(self, frame: np.ndarray) -> np.ndarray:
        """テストモード用オーバーレイ"""
        if not self.is_calibrated:
            return frame
        
        test_frame = frame.copy()
        
        # マウス位置での座標変換テスト
        try:
            mm_coord = self.calibrator.pixel_to_mm(self.mouse_pos)
            coord_text = f"Pixel: {self.mouse_pos[0]}, {self.mouse_pos[1]} | MM: {mm_coord[0]:.1f}, {mm_coord[1]:.1f}"
            
            # 座標テキスト背景
            (text_w, text_h), _ = cv2.getTextSize(coord_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(test_frame, (self.mouse_pos[0] - text_w//2 - 5, self.mouse_pos[1] - 35), 
                         (self.mouse_pos[0] + text_w//2 + 5, self.mouse_pos[1] - 10), 
                         self.colors['bg'], -1)
            
            # 座標テキスト
            cv2.putText(test_frame, coord_text, 
                       (self.mouse_pos[0] - text_w//2, self.mouse_pos[1] - 15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.colors['text'], 2)
            
            # マウス位置マーカー
            cv2.circle(test_frame, self.mouse_pos, 3, self.colors['current'], -1)
            cv2.circle(test_frame, self.mouse_pos, 6, self.colors['text'], 1)
            
            # ケージ内の場合は緑、外の場合は赤
            if 0 <= mm_coord[0] <= self.cage_size[0] and 0 <= mm_coord[1] <= self.cage_size[1]:
                cv2.circle(test_frame, self.mouse_pos, 10, self.colors['point'], 2)
            else:
                cv2.circle(test_frame, self.mouse_pos, 10, (0, 0, 255), 2)
            
        except Exception as e:
            # 校正領域外の場合
            error_text = "校正領域外"
            test_frame = put_japanese_text(test_frame, error_text, 
                                         (self.mouse_pos[0] + 10, self.mouse_pos[1] - 10),
                                         font_size=14, color=(0, 0, 255))
        
        return test_frame
    
    def run_calibration(self, duration: int = 0):
        """
        校正GUI実行
        
        Args:
            duration: 実行時間（秒）、0で無制限
        """
        print("=== GUI座標校正ツール開始 ===")
        print("操作方法:")
        print("  左クリック: 校正点選択（左上→右上→右下→左下の順）")
        print("  右クリック: 最後の校正点を削除")
        print("  'r': 校正リセット")
        print("  't': テストモード切り替え")
        print("  's': 校正データ保存")
        print("  'q' / ESC: 終了")
        print()
        
        try:
            # RTSPストリーム設定
            from utils.camera_config import get_camera_config
            camera_config = get_camera_config()
            camera_config.set_password("894890abc")
            
            with RTSPStream(self.stream_type, buffer_size=1) as stream:
                if not stream.start_stream():
                    logger.error("RTSPストリーム開始失敗")
                    return False
                
                logger.info("✅ RTSPストリーム開始成功")
                
                # OpenCVウィンドウ設定
                cv2.namedWindow(self.window_name, cv2.WINDOW_AUTOSIZE)
                cv2.setMouseCallback(self.window_name, self.mouse_callback)
                
                start_time = time.time()
                test_mode = False
                
                while True:
                    # 時間制限チェック
                    if duration > 0 and (time.time() - start_time) > duration:
                        logger.info(f"時間制限 ({duration}秒) に到達")
                        break
                    
                    # フレーム取得
                    result = stream.get_frame(timeout=1.0)
                    if not result or not result[0]:
                        continue
                    
                    success, frame = result
                    self.current_frame = frame.copy()
                    
                    # オーバーレイ描画
                    if test_mode and self.is_calibrated:
                        display_frame = self._draw_test_overlay(frame)
                    else:
                        display_frame = self._draw_calibration_overlay(frame)
                    
                    # 情報パネル描画
                    display_frame = self._draw_calibration_info(display_frame)
                    
                    # フレーム表示
                    cv2.imshow(self.window_name, display_frame)
                    
                    # キー入力処理
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q') or key == 27:  # 'q' or ESC
                        logger.info("ユーザーによる終了")
                        break
                    elif key == ord('r'):  # リセット
                        self.calibration_points.clear()
                        self.is_calibrated = False
                        self.calibration_result = None
                        logger.info("校正をリセットしました")
                    elif key == ord('t'):  # テストモード切り替え
                        if self.is_calibrated:
                            test_mode = not test_mode
                            mode_text = "テストモード" if test_mode else "校正モード"
                            logger.info(f"{mode_text}に切り替えました")
                        else:
                            logger.warning("校正が完了していません")
                    elif key == ord('s'):  # 保存
                        if self.is_calibrated:
                            try:
                                self.calibrator.save_calibration()
                                logger.info("✅ 校正データを保存しました")
                            except Exception as e:
                                logger.error(f"❌ 校正データ保存エラー: {e}")
                        else:
                            logger.warning("保存する校正データがありません")
                
                cv2.destroyAllWindows()
                
                # 最終結果表示
                if self.is_calibrated:
                    print("\n=== 校正完了 ===")
                    print(f"RMSE誤差: {self.calibration_result.rmse_error:.2f}mm")
                    print(f"最大誤差: {self.calibration_result.max_error:.2f}mm")
                    print(f"平均誤差: {self.calibration_result.mean_error:.2f}mm")
                    print(f"校正点数: {len(self.calibration_result.calibration_points)}")
                    
                    # 検証実行
                    try:
                        validation = self.calibrator.validate_calibration()
                        print(f"校正検証: {'✅ 合格' if validation['validation_passed'] else '❌ 不合格'}")
                        print(f"距離誤差: {validation['distance_error_mm']:.2f}mm ({validation['error_percentage']:.1f}%)")
                    except Exception as e:
                        print(f"検証エラー: {e}")
                else:
                    print("\n校正が完了していません")
                
                return self.is_calibrated
                
        except Exception as e:
            logger.error(f"GUI校正ツールエラー: {e}")
            return False

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='GUI座標校正ツール')
    parser.add_argument('--stream', choices=['main', 'sub'], default='sub',
                       help='RTSPストリーム種別')
    parser.add_argument('--duration', type=int, default=0,
                       help='実行時間（秒）、0で無制限')
    parser.add_argument('--config', type=str, default=None,
                       help='設定ファイルパス')
    
    args = parser.parse_args()
    
    # 設定読み込み
    config = load_config(args.config) if args.config else load_config()
    
    # GUI校正ツール実行
    gui = CalibrationGUI(config, args.stream)
    success = gui.run_calibration(args.duration)
    
    if success:
        print("\n🎉 GUI校正完了")
    else:
        print("\n❌ GUI校正失敗")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nGUI校正中断")
    except Exception as e:
        print(f"\nGUI校正エラー: {e}")
        import traceback
        traceback.print_exc()