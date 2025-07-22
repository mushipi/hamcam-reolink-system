#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
照明モード検出デモアプリケーション
リアルタイムでの照明モード表示と統計情報
"""

import os
import sys
# UTF-8エンコーディング強制設定
if sys.stdout.encoding != 'UTF-8':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np
import time
from datetime import datetime
import argparse
from PIL import Image, ImageDraw, ImageFont

# 必要なモジュールのインポート
from phase3_hamster_tracking.utils.lighting_detector import LightingModeDetector, SimpleLightingDetector
from rtsp_stream import RTSPStream
from utils.camera_config import get_camera_config

def put_japanese_text(image, text, position, font_size=20, color=(255, 255, 255)):
    """
    OpenCV画像に日本語テキストを描画
    
    Args:
        image: OpenCV画像 (BGR)
        text: 描画する日本語テキスト
        position: 描画位置 (x, y)
        font_size: フォントサイズ
        color: 文字色 (B, G, R)
    
    Returns:
        描画後の画像
    """
    try:
        # OpenCV BGR -> PIL RGB
        pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_image)
        
        # 日本語フォント使用
        try:
            font = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", font_size)
        except:
            try:
                # フォールバック1: 別のCJKフォント
                font = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", font_size)
            except:
                # フォールバック2: デフォルト
                font = ImageFont.load_default()
        
        # PIL色形式に変換 (RGB)
        pil_color = (color[2], color[1], color[0])
        
        # テキスト描画
        draw.text(position, text, font=font, fill=pil_color)
        
        # PIL RGB -> OpenCV BGR
        return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    
    except Exception as e:
        # エラー時は英語でフォールバック
        fallback_text = text.encode('ascii', 'replace').decode('ascii')
        cv2.putText(image, fallback_text, position, cv2.FONT_HERSHEY_SIMPLEX, 
                   font_size/30, color, 1)
        return image

class LightingDetectionDemo:
    """照明検出デモクラス"""
    
    def __init__(self, use_simple: bool = False, stream_type: str = "sub"):
        """
        初期化
        
        Args:
            use_simple: 軽量版検出器使用フラグ
            stream_type: RTSPストリーム種別 ("main" or "sub")
        """
        # 検出器初期化
        if use_simple:
            self.detector = SimpleLightingDetector()
            self.detector_name = "SimpleLightingDetector"
        else:
            self.detector = LightingModeDetector()
            self.detector_name = "LightingModeDetector"
        
        # RTSP設定
        self.stream_type = stream_type
        self.config = get_camera_config()
        self.config.set_password("894890abc")
        
        # 統計情報
        self.stats = {
            'total_frames': 0,
            'ir_frames': 0,
            'color_frames': 0,
            'unknown_frames': 0,
            'avg_confidence': 0.0,
            'avg_processing_time': 0.0,
            'start_time': time.time()
        }
        
        # 表示設定
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale = 0.7
        self.thickness = 2
        
        # 色設定
        self.colors = {
            'ir': (0, 100, 255),      # オレンジ（IR）
            'color': (0, 255, 0),     # 緑（カラー）
            'unknown': (128, 128, 128), # グレー（不明）
            'text': (255, 255, 255),   # 白（テキスト）
            'background': (0, 0, 0)    # 黒（背景）
        }
        
        print(f"🎯 照明検出デモ初期化完了")
        print(f"   検出器: {self.detector_name}")
        print(f"   ストリーム: {stream_type}")
    
    def run_demo(self, duration: int = 300):
        """
        デモ実行
        
        Args:
            duration: 実行時間（秒）、0で無制限
        """
        print(f"=== 照明検出デモ開始 ({duration}秒間) ===")
        print("操作方法:")
        print("  'q' / ESC: 終了")
        print("  's': 統計リセット")
        print("  'i': 情報表示切り替え")
        print("  'h': ヘルプ表示")
        
        try:
            with RTSPStream(self.stream_type, buffer_size=1) as stream:
                if not stream.start_stream():
                    print("❌ RTSPストリーム開始失敗")
                    return False
                
                print("✅ RTSPストリーム開始成功")
                
                # OpenCVウィンドウ設定
                window_name = "照明モード検出デモ"
                cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
                
                start_time = time.time()
                show_info = True
                
                while True:
                    # 時間制限チェック
                    if duration > 0 and (time.time() - start_time) > duration:
                        print(f"⏰ 時間制限 ({duration}秒) に到達")
                        break
                    
                    # フレーム取得
                    result = stream.get_frame(timeout=1.0)
                    if not result or not result[0]:
                        continue
                    
                    success, frame = result
                    self.stats['total_frames'] += 1
                    
                    # 照明モード検出
                    detection_start = time.time()
                    if isinstance(self.detector, LightingModeDetector):
                        mode, confidence, details = self.detector.detect_mode(frame)
                        processing_time = details['processing_time_ms']
                    else:
                        mode, confidence = self.detector.detect_mode(frame)
                        processing_time = (time.time() - detection_start) * 1000
                        details = {}
                    
                    # 統計更新
                    self._update_stats(mode, confidence, processing_time)
                    
                    # フレームに情報描画
                    display_frame = self._draw_info_on_frame(
                        frame, mode, confidence, details, show_info
                    )
                    
                    # フレーム表示
                    cv2.imshow(window_name, display_frame)
                    
                    # キー入力処理
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q') or key == 27:  # 'q' or ESC
                        print("ユーザーによる終了")
                        break
                    elif key == ord('s'):
                        self._reset_stats()
                        print("📊 統計情報をリセットしました")
                    elif key == ord('i'):
                        show_info = not show_info
                        print(f"ℹ️ 情報表示: {'ON' if show_info else 'OFF'}")
                    elif key == ord('h'):
                        self._show_help()
                
                cv2.destroyAllWindows()
                
                # 最終統計表示
                self._show_final_stats()
                
                return True
                
        except Exception as e:
            print(f"❌ デモ実行エラー: {e}")
            return False
    
    def _draw_info_on_frame(self, frame: np.ndarray, mode: str, confidence: float,
                           details: dict, show_info: bool = True) -> np.ndarray:
        """
        フレームに情報を描画
        
        Args:
            frame: 元フレーム
            mode: 検出モード
            confidence: 信頼度
            details: 詳細情報
            show_info: 詳細情報表示フラグ
            
        Returns:
            描画済みフレーム
        """
        display_frame = frame.copy()
        h, w = frame.shape[:2]
        
        # モード表示（大きく中央上部）
        mode_text = f"モード: {mode.upper()}"
        mode_color = self.colors.get(mode, self.colors['unknown'])
        
        # テキストサイズ計算
        (text_w, text_h), baseline = cv2.getTextSize(
            mode_text, self.font, self.font_scale * 1.5, self.thickness
        )
        
        # 背景矩形
        cv2.rectangle(display_frame, 
                     (w//2 - text_w//2 - 10, 10),
                     (w//2 + text_w//2 + 10, 10 + text_h + baseline + 20),
                     self.colors['background'], -1)
        
        # モードテキスト（日本語対応）
        display_frame = put_japanese_text(display_frame, mode_text,
                                        (w//2 - text_w//2, 10 + text_h + 10),
                                        font_size=int(self.font_scale * 30), color=mode_color)
        
        # 信頼度バー
        bar_width = 200
        bar_height = 20
        bar_x = w//2 - bar_width//2
        bar_y = 60
        
        # バー背景
        cv2.rectangle(display_frame,
                     (bar_x, bar_y),
                     (bar_x + bar_width, bar_y + bar_height),
                     (50, 50, 50), -1)
        
        # 信頼度バー
        filled_width = int(bar_width * confidence)
        cv2.rectangle(display_frame,
                     (bar_x, bar_y),
                     (bar_x + filled_width, bar_y + bar_height),
                     mode_color, -1)
        
        # 信頼度テキスト（日本語対応）
        conf_text = f"信頼度: {confidence:.3f}"
        display_frame = put_japanese_text(display_frame, conf_text,
                                        (bar_x, bar_y + bar_height + 20),
                                        font_size=int(self.font_scale * 20), color=self.colors['text'])
        
        if show_info and details:
            self._draw_detailed_info(display_frame, details)
        
        # 統計情報（右下）
        self._draw_stats_info(display_frame)
        
        # 現在時刻（左上）
        current_time = datetime.now().strftime("%H:%M:%S")
        cv2.putText(display_frame, current_time,
                   (10, 30), self.font, self.font_scale, 
                   self.colors['text'], 1)
        
        # 操作ヘルプ（左下）
        help_text = "q:終了 s:統計リセット i:情報切替 h:ヘルプ"
        cv2.putText(display_frame, help_text,
                   (10, h - 10), self.font, 0.5, 
                   self.colors['text'], 1)
        
        return display_frame
    
    def _draw_detailed_info(self, frame: np.ndarray, details: dict):
        """詳細情報描画"""
        h, w = frame.shape[:2]
        info_x = 10
        info_y = 80
        line_height = 25
        
        # 詳細情報リスト
        info_lines = [
            f"RGB相関: {details.get('rgb_correlation', 0):.3f}",
            f"時刻推定: {details.get('time_estimation', 0):.3f}",
            f"色相多様性: {details.get('hue_diversity', 0):.3f}",
            f"エッジ密度: {details.get('edge_density', 0):.3f}",
            f"品質スコア: {details.get('frame_quality', 0):.3f}",
            f"処理時間: {details.get('processing_time_ms', 0):.1f}ms",
            f"履歴サイズ: {details.get('history_size', 0)}"
        ]
        
        # 背景矩形
        max_width = max([cv2.getTextSize(line, self.font, 0.5, 1)[0][0] for line in info_lines])
        cv2.rectangle(frame,
                     (info_x - 5, info_y - 5),
                     (info_x + max_width + 10, info_y + len(info_lines) * line_height + 5),
                     (0, 0, 0, 128), -1)
        
        # 詳細情報描画
        for i, line in enumerate(info_lines):
            cv2.putText(frame, line,
                       (info_x, info_y + i * line_height),
                       self.font, 0.5, self.colors['text'], 1)
    
    def _draw_stats_info(self, frame: np.ndarray):
        """統計情報描画"""
        h, w = frame.shape[:2]
        stats_x = w - 200
        stats_y = h - 150
        line_height = 20
        
        elapsed_time = time.time() - self.stats['start_time']
        fps = self.stats['total_frames'] / max(elapsed_time, 1)
        
        # 統計情報
        stats_lines = [
            f"総フレーム: {self.stats['total_frames']}",
            f"FPS: {fps:.1f}",
            f"IR: {self.stats['ir_frames']}",
            f"カラー: {self.stats['color_frames']}",
            f"平均信頼度: {self.stats['avg_confidence']:.3f}",
            f"平均処理時間: {self.stats['avg_processing_time']:.1f}ms"
        ]
        
        # 背景矩形
        cv2.rectangle(frame,
                     (stats_x - 5, stats_y - 5),
                     (w - 5, stats_y + len(stats_lines) * line_height + 5),
                     (0, 0, 0, 128), -1)
        
        # 統計情報描画
        for i, line in enumerate(stats_lines):
            cv2.putText(frame, line,
                       (stats_x, stats_y + i * line_height),
                       self.font, 0.5, self.colors['text'], 1)
    
    def _update_stats(self, mode: str, confidence: float, processing_time: float):
        """統計情報更新"""
        if mode == 'ir':
            self.stats['ir_frames'] += 1
        elif mode == 'color':
            self.stats['color_frames'] += 1
        else:
            self.stats['unknown_frames'] += 1
        
        # 移動平均更新
        alpha = 0.1
        self.stats['avg_confidence'] = (
            alpha * confidence + (1 - alpha) * self.stats['avg_confidence']
        )
        self.stats['avg_processing_time'] = (
            alpha * processing_time + (1 - alpha) * self.stats['avg_processing_time']
        )
    
    def _reset_stats(self):
        """統計情報リセット"""
        self.stats = {
            'total_frames': 0,
            'ir_frames': 0,
            'color_frames': 0,
            'unknown_frames': 0,
            'avg_confidence': 0.0,
            'avg_processing_time': 0.0,
            'start_time': time.time()
        }
        
        if hasattr(self.detector, 'reset_stats'):
            self.detector.reset_stats()
    
    def _show_help(self):
        """ヘルプ表示"""
        print("\n=== 操作ヘルプ ===")
        print("  'q' または ESC: デモ終了")
        print("  's': 統計情報リセット")
        print("  'i': 詳細情報表示切り替え")
        print("  'h': このヘルプ表示")
        print("")
    
    def _show_final_stats(self):
        """最終統計表示"""
        print("\n=== 最終統計情報 ===")
        
        total = self.stats['total_frames']
        if total == 0:
            print("処理フレームなし")
            return
        
        elapsed = time.time() - self.stats['start_time']
        
        print(f"実行時間: {elapsed:.1f}秒")
        print(f"総フレーム: {total}")
        print(f"平均FPS: {total/elapsed:.1f}")
        print(f"")
        print(f"検出結果:")
        print(f"  IR判定: {self.stats['ir_frames']} ({self.stats['ir_frames']/total:.1%})")
        print(f"  カラー判定: {self.stats['color_frames']} ({self.stats['color_frames']/total:.1%})")
        print(f"  不明判定: {self.stats['unknown_frames']} ({self.stats['unknown_frames']/total:.1%})")
        print(f"")
        print(f"性能指標:")
        print(f"  平均信頼度: {self.stats['avg_confidence']:.3f}")
        print(f"  平均処理時間: {self.stats['avg_processing_time']:.1f}ms")
        
        # 検出器の統計があれば表示
        if hasattr(self.detector, 'get_detection_stats'):
            detector_stats = self.detector.get_detection_stats()
            print(f"\n検出器統計:")
            for key, value in detector_stats.items():
                if isinstance(value, float):
                    print(f"  {key}: {value:.3f}")
                else:
                    print(f"  {key}: {value}")

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='照明モード検出デモ')
    parser.add_argument('--simple', action='store_true', 
                       help='軽量版検出器を使用')
    parser.add_argument('--stream', choices=['main', 'sub'], default='sub',
                       help='RTSPストリーム種別')
    parser.add_argument('--duration', type=int, default=0,
                       help='実行時間（秒）、0で無制限')
    
    args = parser.parse_args()
    
    # デモ実行
    demo = LightingDetectionDemo(
        use_simple=args.simple,
        stream_type=args.stream
    )
    
    success = demo.run_demo(duration=args.duration)
    
    if success:
        print("\n🎉 デモ完了")
    else:
        print("\n❌ デモ失敗")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nデモ中断")
    except Exception as e:
        print(f"\nデモエラー: {e}")
        import traceback
        traceback.print_exc()