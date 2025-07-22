#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
動作検出システム
ハムスター特有の動きパターンを高精度で検出する専用モジュール
"""

import os
import sys
import cv2
import numpy as np
import time
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict, Callable
from dataclasses import dataclass, asdict
from collections import deque
import logging

# プロジェクトパスを追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from phase3_hamster_tracking.utils.hamster_config import HamsterTrackingConfig, load_config
from phase3_hamster_tracking.hamster_tracking.coordinate_calibrator import CoordinateCalibrator

# ログ設定
logger = logging.getLogger(__name__)

@dataclass
class MotionEvent:
    """動作イベントデータクラス"""
    timestamp: datetime
    center: Tuple[int, int]
    area: float
    velocity_pixel: float
    velocity_mm: float
    confidence: float
    motion_type: str  # "small", "medium", "large", "rapid", "slow"
    bounding_box: Tuple[int, int, int, int]  # x, y, width, height
    contours: List[np.ndarray]

@dataclass
class MotionStats:
    """動作統計データクラス"""
    total_detections: int = 0
    valid_detections: int = 0
    false_positives: int = 0
    average_velocity_mm_s: float = 0.0
    max_velocity_mm_s: float = 0.0
    active_periods: int = 0
    rest_periods: int = 0
    session_start: Optional[datetime] = None

class MotionDetector:
    """高精度動作検出システム"""
    
    def __init__(self, config: Optional[HamsterTrackingConfig] = None):
        """
        動作検出システムを初期化
        
        Args:
            config: ハムスター管理システム設定
        """
        self.config = config if config else load_config()
        
        # 座標校正器（mm変換用）
        try:
            self.calibrator = CoordinateCalibrator(self.config)
        except Exception as e:
            logger.warning(f"座標校正器初期化失敗: {e}")
            self.calibrator = None
        
        # 背景差分器設定
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            detectShadows=True,
            varThreshold=50,
            history=500
        )
        
        # フィルタ設定
        self.morphology_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        self.gaussian_kernel_size = 5
        
        # ハムスター検出パラメータ
        self.hamster_size_range = {
            'min_area_px': 300,    # 最小面積（ピクセル）
            'max_area_px': 8000,   # 最大面積（ピクセル）
            'min_aspect_ratio': 0.3,  # 最小アスペクト比
            'max_aspect_ratio': 3.0   # 最大アスペクト比
        }
        
        # 動作追跡
        self.motion_history: deque = deque(maxlen=30)  # 最大30フレーム分
        self.last_position: Optional[Tuple[int, int]] = None
        self.velocity_history: deque = deque(maxlen=10)
        
        # 統計情報
        self.stats = MotionStats(session_start=datetime.now())
        
        # コールバック
        self.on_motion_detected: Optional[Callable[[MotionEvent], None]] = None
        self.on_activity_change: Optional[Callable[[str], None]] = None  # "active" or "rest"
        
        # 状態管理
        self.current_activity_state = "unknown"
        self.last_activity_change = datetime.now()
        self.activity_threshold_mm_min = 100.0  # デフォルト値
        self.rest_threshold_sec = 300  # デフォルト値（5分）
        
        logger.info("動作検出システム初期化完了")
    
    def detect_motion(self, frame: np.ndarray, timestamp: Optional[datetime] = None) -> List[MotionEvent]:
        """
        フレームから動作を検出
        
        Args:
            frame: 入力フレーム
            timestamp: フレームのタイムスタンプ
            
        Returns:
            検出された動作イベントのリスト
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        try:
            # 前処理
            processed_frame = self._preprocess_frame(frame)
            
            # 背景差分
            fg_mask = self.bg_subtractor.apply(processed_frame)
            
            # ノイズ除去
            fg_mask = self._clean_mask(fg_mask)
            
            # 輪郭検出
            contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # ハムスター候補をフィルタリング
            hamster_contours = self._filter_hamster_contours(contours)
            
            # 動作イベント生成
            motion_events = []
            for contour in hamster_contours:
                event = self._create_motion_event(contour, timestamp, frame.shape)
                if event:
                    motion_events.append(event)
            
            # 統計更新
            self._update_stats(motion_events)
            
            # 活動状態評価
            self._evaluate_activity_state(motion_events, timestamp)
            
            # コールバック実行
            for event in motion_events:
                if self.on_motion_detected:
                    self.on_motion_detected(event)
            
            return motion_events
            
        except Exception as e:
            logger.error(f"動作検出エラー: {e}")
            return []
    
    def _preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """フレーム前処理"""
        # グレースケール変換
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame
        
        # ガウシアンブラー
        blurred = cv2.GaussianBlur(gray, (self.gaussian_kernel_size, self.gaussian_kernel_size), 0)
        
        return blurred
    
    def _clean_mask(self, mask: np.ndarray) -> np.ndarray:
        """マスクのノイズ除去"""
        # モルフォロジー演算でノイズ除去
        cleaned = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self.morphology_kernel)
        
        # 穴埋め
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, self.morphology_kernel)
        
        return cleaned
    
    def _filter_hamster_contours(self, contours: List[np.ndarray]) -> List[np.ndarray]:
        """ハムスター候補の輪郭をフィルタリング"""
        hamster_contours = []
        
        for contour in contours:
            # 面積フィルタ
            area = cv2.contourArea(contour)
            if not (self.hamster_size_range['min_area_px'] <= area <= self.hamster_size_range['max_area_px']):
                continue
            
            # バウンディングボックス取得
            x, y, w, h = cv2.boundingRect(contour)
            
            # アスペクト比フィルタ
            aspect_ratio = w / h if h > 0 else 0
            if not (self.hamster_size_range['min_aspect_ratio'] <= aspect_ratio <= self.hamster_size_range['max_aspect_ratio']):
                continue
            
            # 輪郭の充実度チェック（ハムスターらしい形状か）
            hull = cv2.convexHull(contour)
            hull_area = cv2.contourArea(hull)
            solidity = area / hull_area if hull_area > 0 else 0
            
            if solidity < 0.5:  # 充実度が低すぎる場合は除外
                continue
            
            hamster_contours.append(contour)
        
        return hamster_contours
    
    def _create_motion_event(self, contour: np.ndarray, timestamp: datetime, frame_shape: Tuple) -> Optional[MotionEvent]:
        """動作イベントを作成"""
        try:
            # 基本的な幾何学的情報
            area = cv2.contourArea(contour)
            moments = cv2.moments(contour)
            
            if moments['m00'] == 0:
                return None
            
            # 重心計算
            cx = int(moments['m10'] / moments['m00'])
            cy = int(moments['m01'] / moments['m00'])
            center = (cx, cy)
            
            # バウンディングボックス
            x, y, w, h = cv2.boundingRect(contour)
            bounding_box = (x, y, w, h)
            
            # 速度計算
            velocity_pixel = 0.0
            velocity_mm = 0.0
            
            if self.last_position is not None:
                # ピクセル単位の距離
                dx = cx - self.last_position[0]
                dy = cy - self.last_position[1]
                distance_pixel = np.sqrt(dx*dx + dy*dy)
                
                # FPS based velocity (assuming 30fps for now)
                velocity_pixel = distance_pixel * 30.0  # pixel/sec
                
                # mm単位の速度計算（座標校正が利用可能な場合）
                if self.calibrator:
                    try:
                        # 現在位置と前回位置をmm単位に変換
                        current_mm = self.calibrator.pixel_to_mm(center)
                        prev_mm = self.calibrator.pixel_to_mm(self.last_position)
                        
                        # mm単位の距離と速度
                        distance_mm = np.sqrt((current_mm[0] - prev_mm[0])**2 + (current_mm[1] - prev_mm[1])**2)
                        velocity_mm = distance_mm * 30.0  # mm/sec
                        
                    except Exception as e:
                        logger.debug(f"mm変換エラー: {e}")
                        velocity_mm = 0.0
            
            # 動作タイプの分類
            motion_type = self._classify_motion_type(area, velocity_pixel, velocity_mm)
            
            # 信頼度計算
            confidence = self._calculate_confidence(contour, area, velocity_pixel)
            
            # 動作イベント作成
            event = MotionEvent(
                timestamp=timestamp,
                center=center,
                area=area,
                velocity_pixel=velocity_pixel,
                velocity_mm=velocity_mm,
                confidence=confidence,
                motion_type=motion_type,
                bounding_box=bounding_box,
                contours=[contour]
            )
            
            # 位置と速度履歴を更新
            self.last_position = center
            if velocity_mm > 0:
                self.velocity_history.append(velocity_mm)
            
            return event
            
        except Exception as e:
            logger.error(f"動作イベント作成エラー: {e}")
            return None
    
    def _classify_motion_type(self, area: float, velocity_pixel: float, velocity_mm: float) -> str:
        """動作タイプを分類"""
        # 主に速度に基づく分類
        if velocity_mm > 0:  # mm単位の速度が利用可能
            if velocity_mm > 100:  # 100mm/sec以上
                return "rapid"
            elif velocity_mm > 50:  # 50-100mm/sec
                return "medium"
            else:  # 50mm/sec以下
                return "slow"
        else:  # ピクセル単位の速度を使用
            if velocity_pixel > 50:
                return "rapid"
            elif velocity_pixel > 20:
                return "medium"
            else:
                return "slow"
    
    def _calculate_confidence(self, contour: np.ndarray, area: float, velocity: float) -> float:
        """動作検出の信頼度を計算"""
        confidence = 0.0
        
        # 面積による信頼度（適切な面積範囲内かどうか）
        ideal_area = (self.hamster_size_range['min_area_px'] + self.hamster_size_range['max_area_px']) / 2
        area_score = 1.0 - abs(area - ideal_area) / ideal_area
        confidence += area_score * 0.4
        
        # 輪郭の滑らかさによる信頼度
        perimeter = cv2.arcLength(contour, True)
        if perimeter > 0:
            circularity = 4 * np.pi * area / (perimeter * perimeter)
            confidence += min(circularity * 2, 1.0) * 0.3
        
        # 速度による信頼度（適度な動きがあるか）
        if 1 <= velocity <= 200:  # 適切な速度範囲
            velocity_score = 1.0 - abs(velocity - 50) / 50  # 50を理想的な速度とする
            confidence += max(velocity_score, 0) * 0.3
        
        return max(0.0, min(1.0, confidence))
    
    def _update_stats(self, motion_events: List[MotionEvent]):
        """統計情報を更新"""
        valid_events = [e for e in motion_events if e.confidence > 0.5]
        
        self.stats.total_detections += len(motion_events)
        self.stats.valid_detections += len(valid_events)
        
        if valid_events:
            # 速度統計の更新
            velocities = [e.velocity_mm for e in valid_events if e.velocity_mm > 0]
            if velocities:
                avg_velocity = np.mean(velocities)
                max_velocity = max(velocities)
                
                # 移動平均で更新
                if self.stats.average_velocity_mm_s == 0:
                    self.stats.average_velocity_mm_s = avg_velocity
                else:
                    alpha = 0.1
                    self.stats.average_velocity_mm_s = (1 - alpha) * self.stats.average_velocity_mm_s + alpha * avg_velocity
                
                self.stats.max_velocity_mm_s = max(self.stats.max_velocity_mm_s, max_velocity)
        
        # 動作履歴に追加
        self.motion_history.append({
            'timestamp': datetime.now(),
            'event_count': len(valid_events),
            'max_velocity': max([e.velocity_mm for e in valid_events], default=0.0)
        })
    
    def _evaluate_activity_state(self, motion_events: List[MotionEvent], timestamp: datetime):
        """活動状態を評価"""
        # 現在の動作量を計算
        current_activity = len([e for e in motion_events if e.confidence > 0.5])
        
        # 過去の動作履歴から活動レベルを算出
        recent_history = [h for h in self.motion_history if (timestamp - h['timestamp']).total_seconds() <= 60]
        total_activity = sum(h['event_count'] for h in recent_history)
        
        # 活動状態の判定
        new_state = "rest"
        if total_activity > 10:  # 過去1分間で10回以上の動作
            new_state = "active"
        
        # 状態変化をチェック
        if new_state != self.current_activity_state:
            time_since_change = (timestamp - self.last_activity_change).total_seconds()
            
            # 最小時間経過後に状態変化を認定
            min_state_duration = 30  # 30秒
            if time_since_change >= min_state_duration:
                logger.info(f"活動状態変化: {self.current_activity_state} -> {new_state}")
                self.current_activity_state = new_state
                self.last_activity_change = timestamp
                
                # 統計更新
                if new_state == "active":
                    self.stats.active_periods += 1
                else:
                    self.stats.rest_periods += 1
                
                # コールバック実行
                if self.on_activity_change:
                    self.on_activity_change(new_state)
    
    def get_activity_state(self) -> str:
        """現在の活動状態を取得"""
        return self.current_activity_state
    
    def get_stats(self) -> Dict:
        """統計情報を取得"""
        return asdict(self.stats)
    
    def get_recent_motion_summary(self, minutes: int = 5) -> Dict:
        """最近の動作サマリーを取得"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_motions = [h for h in self.motion_history if h['timestamp'] >= cutoff_time]
        
        if not recent_motions:
            return {
                'period_minutes': minutes,
                'motion_events': 0,
                'average_velocity': 0.0,
                'max_velocity': 0.0,
                'activity_level': 'no_data'
            }
        
        total_events = sum(h['event_count'] for h in recent_motions)
        velocities = [h['max_velocity'] for h in recent_motions if h['max_velocity'] > 0]
        
        activity_level = "low"
        if total_events > 20:
            activity_level = "high"
        elif total_events > 5:
            activity_level = "medium"
        
        return {
            'period_minutes': minutes,
            'motion_events': total_events,
            'average_velocity': np.mean(velocities) if velocities else 0.0,
            'max_velocity': max(velocities) if velocities else 0.0,
            'activity_level': activity_level
        }
    
    def reset_background_model(self):
        """背景モデルをリセット"""
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            detectShadows=True,
            varThreshold=50,
            history=500
        )
        logger.info("背景モデルをリセットしました")
    
    def visualize_detection(self, frame: np.ndarray, motion_events: List[MotionEvent]) -> np.ndarray:
        """動作検出結果を可視化"""
        vis_frame = frame.copy()
        
        for event in motion_events:
            # 信頼度に応じて色を変更
            if event.confidence > 0.8:
                color = (0, 255, 0)  # 緑：高信頼度
            elif event.confidence > 0.5:
                color = (0, 255, 255)  # 黄：中信頼度
            else:
                color = (0, 0, 255)  # 赤：低信頼度
            
            # バウンディングボックス描画
            x, y, w, h = event.bounding_box
            cv2.rectangle(vis_frame, (x, y), (x + w, y + h), color, 2)
            
            # 中心点
            cv2.circle(vis_frame, event.center, 3, color, -1)
            
            # 情報テキスト
            info_text = f"{event.motion_type} ({event.confidence:.2f})"
            cv2.putText(vis_frame, info_text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            
            # 速度情報（mm単位が利用可能な場合）
            if event.velocity_mm > 0:
                vel_text = f"{event.velocity_mm:.1f}mm/s"
                cv2.putText(vis_frame, vel_text, (x, y + h + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            
            # 輪郭描画
            cv2.drawContours(vis_frame, event.contours, -1, color, 1)
        
        # 活動状態表示
        state_color = (0, 255, 0) if self.current_activity_state == "active" else (128, 128, 128)
        cv2.putText(vis_frame, f"State: {self.current_activity_state}", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, state_color, 2)
        
        return vis_frame

def main():
    """テスト用メイン関数"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    try:
        # 設定読み込み
        config = load_config()
        
        # 動作検出器初期化
        motion_detector = MotionDetector(config)
        
        # コールバック設定
        def on_motion(event: MotionEvent):
            print(f"動作検出: {event.motion_type} at {event.center}, "
                  f"信頼度: {event.confidence:.2f}, 速度: {event.velocity_mm:.1f}mm/s")
        
        def on_activity_change(state: str):
            print(f"活動状態変化: {state}")
        
        motion_detector.on_motion_detected = on_motion
        motion_detector.on_activity_change = on_activity_change
        
        # Webカメラでテスト（実際にはRTSPストリームを使用）
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("カメラが開けませんでした")
            return
        
        print("動作検出テスト開始... (ESCキーで終了)")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 動作検出
            motion_events = motion_detector.detect_motion(frame)
            
            # 結果の可視化
            vis_frame = motion_detector.visualize_detection(frame, motion_events)
            
            # 統計情報表示
            if len(motion_events) > 0:
                summary = motion_detector.get_recent_motion_summary()
                print(f"最近5分間: {summary['motion_events']}回の動作, "
                      f"活動レベル: {summary['activity_level']}")
            
            # 画面表示
            cv2.imshow('Motion Detection Test', vis_frame)
            
            # キー入力
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC
                break
            elif key == ord('r'):  # 背景モデルリセット
                motion_detector.reset_background_model()
                print("背景モデルをリセットしました")
        
        cap.release()
        cv2.destroyAllWindows()
        
        # 最終統計表示
        stats = motion_detector.get_stats()
        print(f"\n=== 動作検出統計 ===")
        print(f"総検出数: {stats['total_detections']}")
        print(f"有効検出数: {stats['valid_detections']}")
        print(f"平均速度: {stats['average_velocity_mm_s']:.2f} mm/s")
        print(f"最大速度: {stats['max_velocity_mm_s']:.2f} mm/s")
        print(f"活動期間: {stats['active_periods']}")
        print(f"休息期間: {stats['rest_periods']}")
    
    except Exception as e:
        logger.error(f"テストエラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()