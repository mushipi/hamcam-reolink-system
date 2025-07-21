#!/usr/bin/env python3
"""
照明モード検出モジュール
RGB相関解析による昼間カラー/夜間IRモード判定
"""

import cv2
import numpy as np
import time
from datetime import datetime, timedelta
from typing import Tuple, Dict, List, Optional
import logging
from collections import deque

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LightingModeDetector:
    """
    照明モード検出器
    RGB相関解析をメインとした昼夜判定システム
    """
    
    def __init__(self, 
                 correlation_threshold: float = 0.95,
                 history_size: int = 5,
                 confidence_threshold: float = 0.8):
        """
        初期化
        
        Args:
            correlation_threshold: IR判定のRGB相関閾値
            history_size: 安定化のための履歴サイズ
            confidence_threshold: 最終判定の信頼度閾値
        """
        self.correlation_threshold = correlation_threshold
        self.history_size = history_size
        self.confidence_threshold = confidence_threshold
        
        # 履歴管理
        self.mode_history = deque(maxlen=history_size)
        self.confidence_history = deque(maxlen=history_size)
        
        # 統計情報
        self.detection_stats = {
            'total_frames': 0,
            'ir_frames': 0,
            'color_frames': 0,
            'low_confidence_frames': 0,
            'avg_processing_time': 0.0
        }
        
        # 時刻ベース判定用（補助）
        self.sunrise_hour = 6  # 6時頃日の出
        self.sunset_hour = 18  # 18時頃日の入り
        
        logger.info(f"LightingModeDetector 初期化完了 (閾値: {correlation_threshold})")
    
    def detect_mode(self, frame: np.ndarray) -> Tuple[str, float, Dict]:
        """
        フレームから照明モードを検出
        
        Args:
            frame: 入力画像フレーム (BGR)
            
        Returns:
            (mode, confidence, details)
            mode: 'color' または 'ir'
            confidence: 信頼度 (0.0-1.0)
            details: 詳細情報
        """
        start_time = time.time()
        
        # 入力検証
        if frame is None or frame.size == 0:
            return 'unknown', 0.0, {'error': 'Invalid frame'}
        
        # RGB相関解析（メイン手法）
        rgb_mode, rgb_confidence = self._detect_by_rgb_correlation(frame)
        
        # 時刻ベース判定（補助）
        time_mode, time_confidence = self._detect_by_time()
        
        # HSV色相解析（補助）
        hue_mode, hue_confidence = self._detect_by_hue_diversity(frame)
        
        # エッジ密度解析（補助）
        edge_mode, edge_confidence = self._detect_by_edge_characteristics(frame)
        
        # 品質評価
        quality_score = self._evaluate_frame_quality(frame, rgb_mode)
        
        # 統合判定（重み付き）
        final_mode, final_confidence = self._integrate_decisions(
            rgb_mode, rgb_confidence,
            time_mode, time_confidence,
            hue_mode, hue_confidence,
            edge_mode, edge_confidence
        )
        
        # 履歴による安定化
        stable_mode, stable_confidence = self._stabilize_with_history(
            final_mode, final_confidence
        )
        
        # 処理時間計算
        processing_time = time.time() - start_time
        
        # 統計更新
        self._update_stats(stable_mode, stable_confidence, processing_time)
        
        # 詳細情報
        details = {
            'rgb_correlation': rgb_confidence,
            'time_estimation': time_confidence,
            'hue_diversity': hue_confidence,
            'edge_density': edge_confidence,
            'frame_quality': quality_score,
            'processing_time_ms': processing_time * 1000,
            'history_size': len(self.mode_history),
            'method_weights': {
                'rgb': 0.5, 'time': 0.2, 'hue': 0.2, 'edge': 0.1
            }
        }
        
        return stable_mode, stable_confidence, details
    
    def _detect_by_rgb_correlation(self, frame: np.ndarray) -> Tuple[str, float]:
        """
        RGB相関解析による判定（メイン手法）
        
        Args:
            frame: 入力フレーム
            
        Returns:
            (mode, confidence)
        """
        try:
            # BGRチャンネル分離
            b, g, r = cv2.split(frame)
            
            # フラット化（計算効率化）
            b_flat = b.flatten().astype(np.float64)
            g_flat = g.flatten().astype(np.float64)
            r_flat = r.flatten().astype(np.float64)
            
            # 標準偏差チェック（すべて同じ値の場合の対策）
            if np.std(b_flat) < 1e-6 or np.std(g_flat) < 1e-6 or np.std(r_flat) < 1e-6:
                # 標準偏差がほぼ0 = 単色画像 = IRの可能性高
                return 'ir', 0.9
            
            # チャンネル間相関計算
            corr_bg = np.corrcoef(b_flat, g_flat)[0, 1]
            corr_br = np.corrcoef(b_flat, r_flat)[0, 1]
            corr_gr = np.corrcoef(g_flat, r_flat)[0, 1]
            
            # NaN処理
            correlations = [corr_bg, corr_br, corr_gr]
            correlations = [c for c in correlations if not np.isnan(c) and not np.isinf(c)]
            
            if not correlations:
                return 'unknown', 0.0
            
            # 平均相関
            avg_correlation = np.mean(correlations)
            
            # IR判定（閾値を少し下げる）
            if avg_correlation > 0.9:  # 0.95 → 0.9
                # 高相関 = グレースケール = IRモード
                confidence = min(1.0, avg_correlation + 0.1)
                return 'ir', confidence
            else:
                # 低相関 = カラー情報有り = カラーモード
                confidence = max(0.5, 1.0 - avg_correlation)
                return 'color', confidence
                
        except Exception as e:
            logger.warning(f"RGB相関解析エラー: {e}")
            return 'unknown', 0.0
    
    def _detect_by_time(self) -> Tuple[str, float]:
        """
        時刻ベース判定（補助手法）
        
        Returns:
            (mode, confidence)
        """
        try:
            current_time = datetime.now()
            hour = current_time.hour
            
            # 日中時間帯（6-18時）
            if self.sunrise_hour <= hour < self.sunset_hour:
                # 日中 = カラーモード可能性高
                # 正午に近いほど信頼度高
                distance_from_noon = abs(hour - 12)
                confidence = max(0.5, 1.0 - distance_from_noon / 6.0)
                return 'color', confidence
            else:
                # 夜間 = IRモード可能性高
                # 深夜に近いほど信頼度高
                if hour >= self.sunset_hour:
                    distance_from_midnight = min(hour - self.sunset_hour, 24 - hour)
                else:
                    distance_from_midnight = self.sunrise_hour - hour
                confidence = max(0.5, 1.0 - distance_from_midnight / 6.0)
                return 'ir', confidence
                
        except Exception as e:
            logger.warning(f"時刻ベース判定エラー: {e}")
            return 'unknown', 0.5
    
    def _detect_by_hue_diversity(self, frame: np.ndarray) -> Tuple[str, float]:
        """
        HSV色相多様性による判定（補助手法）
        
        Args:
            frame: 入力フレーム
            
        Returns:
            (mode, confidence)
        """
        try:
            # HSV変換
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            hue = hsv[:, :, 0]
            
            # 色相ヒストグラム
            hist = cv2.calcHist([hue], [0], None, [180], [0, 180])
            
            # 非ゼロビン数（色の多様性）
            non_zero_bins = np.count_nonzero(hist)
            
            # 正規化（最大180色相）
            diversity_ratio = non_zero_bins / 180.0
            
            # 判定閾値
            diversity_threshold = 0.15  # 15%以上の色相多様性でカラー
            
            if diversity_ratio > diversity_threshold:
                # 高多様性 = カラーモード
                confidence = min(1.0, diversity_ratio * 2)  # 正規化
                return 'color', confidence
            else:
                # 低多様性 = IRモード
                confidence = 1.0 - diversity_ratio / diversity_threshold
                return 'ir', confidence
                
        except Exception as e:
            logger.warning(f"色相多様性判定エラー: {e}")
            return 'unknown', 0.5
    
    def _detect_by_edge_characteristics(self, frame: np.ndarray) -> Tuple[str, float]:
        """
        エッジ特性による判定（補助手法）
        
        Args:
            frame: 入力フレーム
            
        Returns:
            (mode, confidence)
        """
        try:
            # グレースケール変換
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # エッジ検出
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / edges.size
            
            # ヒストグラム分析
            hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
            hist = hist.flatten() / np.sum(hist)  # 正規化
            
            # 両端集中度（IRの特徴）
            dark_ratio = np.sum(hist[0:50])
            bright_ratio = np.sum(hist[200:256])
            extreme_ratio = dark_ratio + bright_ratio
            
            # IR特徴判定
            # 高エッジ密度 + 両端集中 = IR
            edge_threshold = 0.05
            extreme_threshold = 0.4
            
            ir_score = 0.0
            if edge_density > edge_threshold:
                ir_score += 0.5
            if extreme_ratio > extreme_threshold:
                ir_score += 0.5
            
            if ir_score > 0.5:
                return 'ir', ir_score
            else:
                return 'color', 1.0 - ir_score
                
        except Exception as e:
            logger.warning(f"エッジ特性判定エラー: {e}")
            return 'unknown', 0.5
    
    def _integrate_decisions(self, 
                           rgb_mode: str, rgb_conf: float,
                           time_mode: str, time_conf: float,
                           hue_mode: str, hue_conf: float,
                           edge_mode: str, edge_conf: float) -> Tuple[str, float]:
        """
        複数判定結果の統合
        
        Returns:
            (integrated_mode, integrated_confidence)
        """
        # 重み設定（RGB相関を最重要視）
        weights = {
            'rgb': 0.7,  # RGB相関の重みを上げる
            'time': 0.1,
            'hue': 0.15,
            'edge': 0.05
        }
        
        # スコア計算
        ir_score = 0.0
        color_score = 0.0
        
        methods = [
            (rgb_mode, rgb_conf, 'rgb'),
            (time_mode, time_conf, 'time'),
            (hue_mode, hue_conf, 'hue'),
            (edge_mode, edge_conf, 'edge')
        ]
        
        for mode, confidence, method in methods:
            if mode == 'unknown':
                continue
                
            weighted_conf = confidence * weights[method]
            
            if mode == 'ir':
                ir_score += weighted_conf
            else:  # color
                color_score += weighted_conf
        
        # 最終判定
        if ir_score > color_score:
            final_mode = 'ir'
            final_confidence = ir_score / sum(weights.values())
        else:
            final_mode = 'color'
            final_confidence = color_score / sum(weights.values())
        
        return final_mode, final_confidence
    
    def _stabilize_with_history(self, mode: str, confidence: float) -> Tuple[str, float]:
        """
        履歴による判定安定化
        
        Args:
            mode: 現在の判定結果
            confidence: 現在の信頼度
            
        Returns:
            (stable_mode, stable_confidence)
        """
        # 履歴に追加
        self.mode_history.append(mode)
        self.confidence_history.append(confidence)
        
        # 十分な履歴が無い場合は現在値返却
        if len(self.mode_history) < 3:
            return mode, confidence
        
        # 過半数判定
        ir_count = list(self.mode_history).count('ir')
        color_count = list(self.mode_history).count('color')
        
        if ir_count > color_count:
            stable_mode = 'ir'
        else:
            stable_mode = 'color'
        
        # 信頼度は履歴平均
        stable_confidence = np.mean(list(self.confidence_history))
        
        return stable_mode, stable_confidence
    
    def _evaluate_frame_quality(self, frame: np.ndarray, mode: str) -> float:
        """
        フレーム品質評価
        
        Args:
            frame: 入力フレーム
            mode: 検出されたモード
            
        Returns:
            quality_score: 品質スコア (0.0-1.0)
        """
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # 鮮明度（ラプラシアン分散）
            sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
            sharpness_score = min(1.0, sharpness / 1000.0)  # 正規化
            
            # 適正露出
            mean_brightness = np.mean(gray)
            brightness_score = 1.0 - abs(mean_brightness - 128) / 128
            
            # ノイズレベル
            noise = np.std(gray - cv2.GaussianBlur(gray, (5, 5), 0))
            noise_score = max(0.0, 1.0 - noise / 50.0)
            
            # 統合品質スコア
            quality = (sharpness_score * 0.4 + 
                      brightness_score * 0.4 + 
                      noise_score * 0.2)
            
            return min(1.0, max(0.0, quality))
            
        except Exception as e:
            logger.warning(f"品質評価エラー: {e}")
            return 0.5
    
    def _update_stats(self, mode: str, confidence: float, processing_time: float):
        """統計情報更新"""
        self.detection_stats['total_frames'] += 1
        
        if mode == 'ir':
            self.detection_stats['ir_frames'] += 1
        elif mode == 'color':
            self.detection_stats['color_frames'] += 1
        
        if confidence < self.confidence_threshold:
            self.detection_stats['low_confidence_frames'] += 1
        
        # 移動平均で処理時間更新
        alpha = 0.1  # 平滑化係数
        self.detection_stats['avg_processing_time'] = (
            alpha * processing_time + 
            (1 - alpha) * self.detection_stats['avg_processing_time']
        )
    
    def get_detection_stats(self) -> Dict:
        """統計情報取得"""
        if self.detection_stats['total_frames'] == 0:
            return self.detection_stats
        
        stats = self.detection_stats.copy()
        stats['ir_ratio'] = stats['ir_frames'] / stats['total_frames']
        stats['color_ratio'] = stats['color_frames'] / stats['total_frames']
        stats['low_confidence_ratio'] = stats['low_confidence_frames'] / stats['total_frames']
        
        return stats
    
    def reset_stats(self):
        """統計情報リセット"""
        self.detection_stats = {
            'total_frames': 0,
            'ir_frames': 0,
            'color_frames': 0,
            'low_confidence_frames': 0,
            'avg_processing_time': 0.0
        }
        self.mode_history.clear()
        self.confidence_history.clear()
        
        logger.info("統計情報をリセットしました")

class SimpleLightingDetector:
    """
    軽量版照明モード検出器
    RGB相関のみの高速判定
    """
    
    def __init__(self, threshold: float = 0.95):
        self.threshold = threshold
    
    def detect_mode(self, frame: np.ndarray) -> Tuple[str, float]:
        """
        シンプルなRGB相関による判定
        
        Args:
            frame: 入力フレーム
            
        Returns:
            (mode, confidence)
        """
        try:
            b, g, r = cv2.split(frame)
            
            # 相関計算
            corr_bg = np.corrcoef(b.flatten(), g.flatten())[0, 1]
            corr_br = np.corrcoef(b.flatten(), r.flatten())[0, 1] 
            corr_gr = np.corrcoef(g.flatten(), r.flatten())[0, 1]
            
            # 平均相関
            avg_correlation = np.mean([corr_bg, corr_br, corr_gr])
            
            if np.isnan(avg_correlation):
                return 'unknown', 0.0
            
            # 判定
            if avg_correlation > self.threshold:
                return 'ir', avg_correlation
            else:
                return 'color', 1.0 - avg_correlation
                
        except Exception:
            return 'unknown', 0.0