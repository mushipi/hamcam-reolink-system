#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データ品質評価システム
DeepLabCut学習用画像の品質を自動評価・フィルタリングするモジュール
"""

import os
import sys
import cv2
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from pathlib import Path

# プロジェクトパスを追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from phase3_hamster_tracking.utils.hamster_config import HamsterTrackingConfig, load_config

# ログ設定
logger = logging.getLogger(__name__)

class QualityLevel(Enum):
    """品質レベル列挙型"""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    REJECT = "reject"

@dataclass
class QualityMetrics:
    """品質評価指標データクラス"""
    # 基本的な画像品質
    blur_score: float                # ブラー検出スコア（高いほど鮮明）
    brightness_score: float          # 輝度スコア（0-1、0.5が理想）
    contrast_score: float            # コントラストスコア（高いほど良い）
    noise_score: float              # ノイズスコア（低いほど良い）
    saturation_score: float         # 彩度スコア（適度な彩度が理想）
    
    # ハムスター検出関連
    hamster_visibility_score: float  # ハムスター可視性スコア
    hamster_size_score: float       # ハムスターサイズ適正スコア
    pose_clarity_score: float       # 姿勢の明瞭性スコア
    
    # 背景・環境
    background_stability_score: float  # 背景安定性スコア
    lighting_consistency_score: float # 照明一貫性スコア
    shadow_interference_score: float  # 影の干渉スコア
    
    # 総合評価
    overall_score: float             # 総合品質スコア（0-1）
    quality_level: QualityLevel     # 品質レベル
    
    # メタデータ
    evaluation_timestamp: datetime
    frame_resolution: Tuple[int, int]
    file_size_bytes: Optional[int] = None
    notes: List[str] = None

@dataclass 
class QualityStats:
    """品質評価統計データクラス"""
    total_evaluated: int = 0
    excellent_count: int = 0
    good_count: int = 0
    acceptable_count: int = 0
    poor_count: int = 0
    rejected_count: int = 0
    average_overall_score: float = 0.0
    average_blur_score: float = 0.0
    average_brightness_score: float = 0.0
    average_contrast_score: float = 0.0

class DataQualityAssessor:
    """データ品質評価システム"""
    
    def __init__(self, config: Optional[HamsterTrackingConfig] = None):
        """
        データ品質評価システムを初期化
        
        Args:
            config: ハムスター管理システム設定
        """
        self.config = config if config else load_config()
        
        # 品質閾値設定（デフォルト値使用）
        self.quality_thresholds = {
            'blur_threshold': 100.0,  # デフォルト値
            'brightness_range': [50, 200],  # デフォルト値
            'contrast_threshold': 0.3,  # デフォルト値
            'min_hamster_area_ratio': 0.01,  # フレーム面積に対する最小ハムスター面積比
            'max_hamster_area_ratio': 0.15,  # フレーム面積に対する最大ハムスター面積比
            'noise_variance_threshold': 100.0,  # ノイズ分散閾値
            'saturation_optimal_range': (0.3, 0.8)  # 最適彩度範囲
        }
        
        # 品質レベル閾値
        self.level_thresholds = {
            QualityLevel.EXCELLENT: 0.8,
            QualityLevel.GOOD: 0.65,
            QualityLevel.ACCEPTABLE: 0.5,
            QualityLevel.POOR: 0.3,
            QualityLevel.REJECT: 0.0
        }
        
        # 統計情報
        self.stats = QualityStats()
        
        # 背景モデル（背景安定性評価用）
        self.background_model = None
        self.background_frames = []
        self.max_background_frames = 10
        
        logger.info("データ品質評価システム初期化完了")
    
    def evaluate_image_quality(
        self, 
        image: np.ndarray, 
        file_path: Optional[str] = None,
        detect_hamster: bool = True
    ) -> QualityMetrics:
        """
        画像の品質を総合評価
        
        Args:
            image: 評価対象画像
            file_path: ファイルパス（ファイルサイズ取得用）
            detect_hamster: ハムスター検出を行うかどうか
            
        Returns:
            品質評価結果
        """
        try:
            # 基本品質指標の評価
            blur_score = self._evaluate_blur(image)
            brightness_score = self._evaluate_brightness(image)
            contrast_score = self._evaluate_contrast(image)
            noise_score = self._evaluate_noise(image)
            saturation_score = self._evaluate_saturation(image)
            
            # ハムスター関連評価
            hamster_visibility = 0.5  # デフォルト値
            hamster_size = 0.5
            pose_clarity = 0.5
            
            if detect_hamster:
                hamster_metrics = self._evaluate_hamster_visibility(image)
                hamster_visibility = hamster_metrics['visibility_score']
                hamster_size = hamster_metrics['size_score']
                pose_clarity = hamster_metrics['pose_clarity']
            
            # 背景・環境評価
            background_stability = self._evaluate_background_stability(image)
            lighting_consistency = self._evaluate_lighting_consistency(image)
            shadow_interference = self._evaluate_shadow_interference(image)
            
            # 総合スコア計算（重み付き平均）
            weights = {
                'blur': 0.2,
                'brightness': 0.1,
                'contrast': 0.1,
                'noise': 0.1,
                'saturation': 0.05,
                'hamster_visibility': 0.25,
                'hamster_size': 0.1,
                'pose_clarity': 0.15,
                'background': 0.03,
                'lighting': 0.05,
                'shadow': 0.02
            }
            
            overall_score = (
                blur_score * weights['blur'] +
                brightness_score * weights['brightness'] +
                contrast_score * weights['contrast'] +
                (1.0 - noise_score) * weights['noise'] +  # ノイズは低いほど良い
                saturation_score * weights['saturation'] +
                hamster_visibility * weights['hamster_visibility'] +
                hamster_size * weights['hamster_size'] +
                pose_clarity * weights['pose_clarity'] +
                background_stability * weights['background'] +
                lighting_consistency * weights['lighting'] +
                (1.0 - shadow_interference) * weights['shadow']  # 影は少ないほど良い
            )
            
            # 品質レベル判定
            quality_level = self._determine_quality_level(overall_score)
            
            # ファイルサイズ取得
            file_size = None
            if file_path and os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
            
            # 評価結果作成
            metrics = QualityMetrics(
                blur_score=blur_score,
                brightness_score=brightness_score,
                contrast_score=contrast_score,
                noise_score=noise_score,
                saturation_score=saturation_score,
                hamster_visibility_score=hamster_visibility,
                hamster_size_score=hamster_size,
                pose_clarity_score=pose_clarity,
                background_stability_score=background_stability,
                lighting_consistency_score=lighting_consistency,
                shadow_interference_score=shadow_interference,
                overall_score=overall_score,
                quality_level=quality_level,
                evaluation_timestamp=datetime.now(),
                frame_resolution=(image.shape[1], image.shape[0]),
                file_size_bytes=file_size,
                notes=self._generate_quality_notes(locals())
            )
            
            # 統計更新
            self._update_stats(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"画像品質評価エラー: {e}")
            # エラー時のデフォルト評価
            return QualityMetrics(
                blur_score=0.0, brightness_score=0.0, contrast_score=0.0,
                noise_score=1.0, saturation_score=0.0,
                hamster_visibility_score=0.0, hamster_size_score=0.0, pose_clarity_score=0.0,
                background_stability_score=0.0, lighting_consistency_score=0.0,
                shadow_interference_score=1.0,
                overall_score=0.0, quality_level=QualityLevel.REJECT,
                evaluation_timestamp=datetime.now(),
                frame_resolution=(0, 0),
                notes=[f"評価エラー: {str(e)}"]
            )
    
    def _evaluate_blur(self, image: np.ndarray) -> float:
        """ブラー検出評価"""
        try:
            # グレースケール変換
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            
            # ラプラシアン分散によるブラー検出
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # Sobelオペレータによる追加検証
            sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            sobel_magnitude = np.sqrt(sobel_x**2 + sobel_y**2).mean()
            
            # 両方の値を正規化して組み合わせ
            threshold = self.quality_thresholds['blur_threshold']
            laplacian_score = min(laplacian_var / threshold, 1.0)
            sobel_score = min(sobel_magnitude / 50.0, 1.0)  # 50は経験的な値
            
            return (laplacian_score * 0.7 + sobel_score * 0.3)
            
        except Exception as e:
            logger.error(f"ブラー評価エラー: {e}")
            return 0.0
    
    def _evaluate_brightness(self, image: np.ndarray) -> float:
        """輝度評価"""
        try:
            # グレースケール変換
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            
            # 平均輝度
            mean_brightness = np.mean(gray)
            
            # 理想的な輝度範囲
            brightness_range = self.quality_thresholds['brightness_range']
            optimal_brightness = np.mean(brightness_range)
            
            # 理想値からの偏差を評価（0-1スケール）
            deviation = abs(mean_brightness - optimal_brightness) / 127.5
            score = max(0.0, 1.0 - deviation)
            
            return score
            
        except Exception as e:
            logger.error(f"輝度評価エラー: {e}")
            return 0.0
    
    def _evaluate_contrast(self, image: np.ndarray) -> float:
        """コントラスト評価"""
        try:
            # グレースケール変換
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            
            # 標準偏差によるコントラスト測定
            contrast = np.std(gray)
            
            # RMS（Root Mean Square）コントラストも計算
            rms_contrast = np.sqrt(np.mean((gray - np.mean(gray))**2))
            
            # 閾値との比較
            threshold = self.quality_thresholds['contrast_threshold'] * 255
            
            std_score = min(contrast / threshold, 1.0)
            rms_score = min(rms_contrast / threshold, 1.0)
            
            return (std_score * 0.6 + rms_score * 0.4)
            
        except Exception as e:
            logger.error(f"コントラスト評価エラー: {e}")
            return 0.0
    
    def _evaluate_noise(self, image: np.ndarray) -> float:
        """ノイズ評価"""
        try:
            # グレースケール変換
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            
            # ガウシアンフィルタ適用
            filtered = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # 差分からノイズレベルを推定
            noise = gray.astype(np.float32) - filtered.astype(np.float32)
            noise_variance = np.var(noise)
            
            # 正規化（低いほど良い、返り値は高いほど良い形式に変換）
            threshold = self.quality_thresholds['noise_variance_threshold']
            noise_score = max(0.0, min(noise_variance / threshold, 1.0))
            
            return noise_score  # 呼び出し側で1.0から引く
            
        except Exception as e:
            logger.error(f"ノイズ評価エラー: {e}")
            return 1.0  # エラー時は最大ノイズとして扱う
    
    def _evaluate_saturation(self, image: np.ndarray) -> float:
        """彩度評価"""
        try:
            if len(image.shape) != 3:
                return 0.5  # グレースケールの場合は中間値
            
            # HSVに変換
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            
            # 彩度（Saturation）チャンネル
            saturation = hsv[:, :, 1] / 255.0
            mean_saturation = np.mean(saturation)
            
            # 理想的な彩度範囲
            optimal_range = self.quality_thresholds['saturation_optimal_range']
            
            if optimal_range[0] <= mean_saturation <= optimal_range[1]:
                # 理想範囲内の場合
                center = np.mean(optimal_range)
                score = 1.0 - abs(mean_saturation - center) / (optimal_range[1] - center)
            else:
                # 理想範囲外の場合
                if mean_saturation < optimal_range[0]:
                    score = mean_saturation / optimal_range[0]
                else:
                    score = 1.0 - (mean_saturation - optimal_range[1]) / (1.0 - optimal_range[1])
            
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            logger.error(f"彩度評価エラー: {e}")
            return 0.5
    
    def _evaluate_hamster_visibility(self, image: np.ndarray) -> Dict[str, float]:
        """ハムスター可視性評価"""
        try:
            # 簡単なハムスター検出（色とサイズに基づく）
            # より高度な検出はMotionDetectorクラスを使用可能
            
            # HSV色空間でハムスターらしい色を検出
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            
            # ハムスターの一般的な色範囲（茶色系）
            # これは品種によって調整が必要
            lower_hamster = np.array([5, 50, 50])
            upper_hamster = np.array([25, 255, 255])
            
            mask = cv2.inRange(hsv, lower_hamster, upper_hamster)
            
            # ノイズ除去
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            
            # 輪郭検出
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return {
                    'visibility_score': 0.1,
                    'size_score': 0.0,
                    'pose_clarity': 0.0
                }
            
            # 最大の輪郭を選択
            largest_contour = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest_contour)
            
            # フレーム面積に対する比率
            frame_area = image.shape[0] * image.shape[1]
            area_ratio = area / frame_area
            
            # サイズ評価
            size_range = (
                self.quality_thresholds['min_hamster_area_ratio'],
                self.quality_thresholds['max_hamster_area_ratio']
            )
            
            if size_range[0] <= area_ratio <= size_range[1]:
                # 適切なサイズ範囲内
                optimal_ratio = np.mean(size_range)
                size_score = 1.0 - abs(area_ratio - optimal_ratio) / optimal_ratio
            else:
                # 範囲外
                if area_ratio < size_range[0]:
                    size_score = area_ratio / size_range[0]
                else:
                    size_score = size_range[1] / area_ratio
            
            # 可視性スコア（検出された面積に基づく）
            visibility_score = min(1.0, area_ratio * 10)  # 10は調整可能な係数
            
            # 姿勢明瞭性（輪郭の複雑さから推定）
            perimeter = cv2.arcLength(largest_contour, True)
            if perimeter > 0 and area > 0:
                compactness = 4 * np.pi * area / (perimeter * perimeter)
                pose_clarity = min(1.0, compactness * 2)  # ある程度コンパクトな方が良い
            else:
                pose_clarity = 0.0
            
            return {
                'visibility_score': max(0.0, min(1.0, visibility_score)),
                'size_score': max(0.0, min(1.0, size_score)),
                'pose_clarity': max(0.0, min(1.0, pose_clarity))
            }
            
        except Exception as e:
            logger.error(f"ハムスター可視性評価エラー: {e}")
            return {
                'visibility_score': 0.0,
                'size_score': 0.0,
                'pose_clarity': 0.0
            }
    
    def _evaluate_background_stability(self, image: np.ndarray) -> float:
        """背景安定性評価"""
        try:
            # 背景フレームを蓄積
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            
            if len(self.background_frames) < self.max_background_frames:
                self.background_frames.append(gray)
                return 0.5  # 初期段階は中間値
            else:
                # 古いフレームを削除して新しいフレームを追加
                self.background_frames.pop(0)
                self.background_frames.append(gray)
            
            # 背景モデル更新
            self.background_model = np.mean(self.background_frames, axis=0).astype(np.uint8)
            
            # 現在のフレームと背景モデルの差分
            diff = cv2.absdiff(gray, self.background_model)
            
            # 変化の度合いを評価
            change_ratio = np.sum(diff > 30) / diff.size  # 30は閾値
            
            # 安定性スコア（変化が少ないほど高い）
            stability_score = 1.0 - min(change_ratio * 5, 1.0)  # 5は調整係数
            
            return stability_score
            
        except Exception as e:
            logger.error(f"背景安定性評価エラー: {e}")
            return 0.5
    
    def _evaluate_lighting_consistency(self, image: np.ndarray) -> float:
        """照明一貫性評価"""
        try:
            # グレースケール変換
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            
            # 画像をグリッドに分割して局所的な輝度を分析
            h, w = gray.shape
            grid_size = 4  # 4x4グリッド
            cell_h, cell_w = h // grid_size, w // grid_size
            
            local_means = []
            for i in range(grid_size):
                for j in range(grid_size):
                    y1, y2 = i * cell_h, min((i + 1) * cell_h, h)
                    x1, x2 = j * cell_w, min((j + 1) * cell_w, w)
                    cell_mean = np.mean(gray[y1:y2, x1:x2])
                    local_means.append(cell_mean)
            
            # 局所輝度の分散を計算
            mean_variance = np.var(local_means)
            
            # 一貫性スコア（分散が小さいほど一貫性が高い）
            consistency_score = 1.0 / (1.0 + mean_variance / 100.0)  # 100は正規化係数
            
            return min(1.0, consistency_score)
            
        except Exception as e:
            logger.error(f"照明一貫性評価エラー: {e}")
            return 0.5
    
    def _evaluate_shadow_interference(self, image: np.ndarray) -> float:
        """影の干渉評価"""
        try:
            # LAB色空間に変換
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l_channel = lab[:, :, 0]
            
            # 極端に暗い領域を検出（影の可能性）
            dark_threshold = 50  # L*値が50以下
            dark_mask = l_channel < dark_threshold
            
            # 影の面積比率
            shadow_ratio = np.sum(dark_mask) / dark_mask.size
            
            # 影の干渉スコア（高いほど影が多い）
            interference_score = min(shadow_ratio * 3, 1.0)  # 3は調整係数
            
            return interference_score  # 呼び出し側で1.0から引く
            
        except Exception as e:
            logger.error(f"影干渉評価エラー: {e}")
            return 0.0
    
    def _determine_quality_level(self, overall_score: float) -> QualityLevel:
        """総合スコアから品質レベルを判定"""
        if overall_score >= self.level_thresholds[QualityLevel.EXCELLENT]:
            return QualityLevel.EXCELLENT
        elif overall_score >= self.level_thresholds[QualityLevel.GOOD]:
            return QualityLevel.GOOD
        elif overall_score >= self.level_thresholds[QualityLevel.ACCEPTABLE]:
            return QualityLevel.ACCEPTABLE
        elif overall_score >= self.level_thresholds[QualityLevel.POOR]:
            return QualityLevel.POOR
        else:
            return QualityLevel.REJECT
    
    def _generate_quality_notes(self, eval_vars: Dict) -> List[str]:
        """品質評価に基づく注意事項を生成"""
        notes = []
        
        # 各指標に基づく注意事項
        if eval_vars.get('blur_score', 0) < 0.5:
            notes.append("画像がぼやけています")
        
        if eval_vars.get('brightness_score', 0) < 0.5:
            notes.append("輝度が不適切です")
        
        if eval_vars.get('contrast_score', 0) < 0.5:
            notes.append("コントラストが不足しています")
        
        if eval_vars.get('noise_score', 0) > 0.7:
            notes.append("ノイズが多く含まれています")
        
        if eval_vars.get('hamster_visibility', 0) < 0.3:
            notes.append("ハムスターの可視性が低いです")
        
        if eval_vars.get('shadow_interference', 0) > 0.5:
            notes.append("影の干渉が検出されました")
        
        return notes
    
    def _update_stats(self, metrics: QualityMetrics):
        """統計情報を更新"""
        self.stats.total_evaluated += 1
        
        # 品質レベル別カウント
        if metrics.quality_level == QualityLevel.EXCELLENT:
            self.stats.excellent_count += 1
        elif metrics.quality_level == QualityLevel.GOOD:
            self.stats.good_count += 1
        elif metrics.quality_level == QualityLevel.ACCEPTABLE:
            self.stats.acceptable_count += 1
        elif metrics.quality_level == QualityLevel.POOR:
            self.stats.poor_count += 1
        else:
            self.stats.rejected_count += 1
        
        # 移動平均で各スコアを更新
        alpha = 0.1  # 学習率
        
        if self.stats.total_evaluated == 1:
            # 初回
            self.stats.average_overall_score = metrics.overall_score
            self.stats.average_blur_score = metrics.blur_score
            self.stats.average_brightness_score = metrics.brightness_score
            self.stats.average_contrast_score = metrics.contrast_score
        else:
            # 移動平均更新
            self.stats.average_overall_score = (1 - alpha) * self.stats.average_overall_score + alpha * metrics.overall_score
            self.stats.average_blur_score = (1 - alpha) * self.stats.average_blur_score + alpha * metrics.blur_score
            self.stats.average_brightness_score = (1 - alpha) * self.stats.average_brightness_score + alpha * metrics.brightness_score
            self.stats.average_contrast_score = (1 - alpha) * self.stats.average_contrast_score + alpha * metrics.contrast_score
    
    def filter_by_quality(
        self, 
        image_paths: List[str], 
        min_quality_level: QualityLevel = QualityLevel.ACCEPTABLE
    ) -> Dict[str, List[str]]:
        """
        品質レベルに基づいて画像をフィルタリング
        
        Args:
            image_paths: 画像ファイルパスのリスト
            min_quality_level: 最小品質レベル
            
        Returns:
            品質レベル別の画像パスディクショナリ
        """
        filtered_results = {
            'excellent': [],
            'good': [],
            'acceptable': [],
            'poor': [],
            'rejected': []
        }
        
        min_score = self.level_thresholds[min_quality_level]
        
        for image_path in image_paths:
            try:
                # 画像読み込み
                image = cv2.imread(image_path)
                if image is None:
                    logger.warning(f"画像読み込み失敗: {image_path}")
                    filtered_results['rejected'].append(image_path)
                    continue
                
                # 品質評価
                metrics = self.evaluate_image_quality(image, image_path)
                
                # 品質レベル別に分類
                level_key = metrics.quality_level.value
                filtered_results[level_key].append(image_path)
                
                logger.debug(f"画像評価完了: {image_path} -> {metrics.quality_level.value} "
                           f"(スコア: {metrics.overall_score:.2f})")
                
            except Exception as e:
                logger.error(f"画像フィルタリングエラー: {image_path} - {e}")
                filtered_results['rejected'].append(image_path)
        
        return filtered_results
    
    def get_stats(self) -> Dict:
        """統計情報を取得"""
        return asdict(self.stats)
    
    def export_quality_report(self, output_path: str, image_paths: List[str] = None):
        """品質評価レポートをエクスポート"""
        try:
            report = {
                'timestamp': datetime.now().isoformat(),
                'statistics': asdict(self.stats),
                'configuration': {
                    'blur_threshold': self.quality_thresholds['blur_threshold'],
                    'brightness_range': self.quality_thresholds['brightness_range'],
                    'contrast_threshold': self.quality_thresholds['contrast_threshold']
                }
            }
            
            # 個別画像の評価結果を含める場合
            if image_paths:
                individual_results = []
                for image_path in image_paths:
                    try:
                        image = cv2.imread(image_path)
                        if image is not None:
                            metrics = self.evaluate_image_quality(image, image_path)
                            individual_results.append({
                                'file_path': image_path,
                                'quality_level': metrics.quality_level.value,
                                'overall_score': metrics.overall_score,
                                'blur_score': metrics.blur_score,
                                'hamster_visibility': metrics.hamster_visibility_score,
                                'notes': metrics.notes
                            })
                    except Exception as e:
                        logger.error(f"個別評価エラー: {image_path} - {e}")
                
                report['individual_evaluations'] = individual_results
            
            # JSONファイルとして保存
            import json
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"品質評価レポートを保存: {output_path}")
            
        except Exception as e:
            logger.error(f"レポートエクスポートエラー: {e}")

def main():
    """テスト用メイン関数"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    try:
        # 設定読み込み
        config = load_config()
        
        # データ品質評価器初期化
        quality_assessor = DataQualityAssessor(config)
        
        # Webカメラでテスト
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("カメラが開けませんでした")
            return
        
        print("データ品質評価テスト開始... (ESCキーで終了)")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 品質評価実行
            metrics = quality_assessor.evaluate_image_quality(frame)
            
            # 結果表示
            print(f"\n=== 品質評価結果 ===")
            print(f"品質レベル: {metrics.quality_level.value}")
            print(f"総合スコア: {metrics.overall_score:.3f}")
            print(f"ブラー: {metrics.blur_score:.3f}")
            print(f"輝度: {metrics.brightness_score:.3f}")
            print(f"コントラスト: {metrics.contrast_score:.3f}")
            print(f"ハムスター可視性: {metrics.hamster_visibility_score:.3f}")
            
            if metrics.notes:
                print(f"注意事項: {', '.join(metrics.notes)}")
            
            # 品質レベルに応じた色で枠を描画
            color_map = {
                QualityLevel.EXCELLENT: (0, 255, 0),      # 緑
                QualityLevel.GOOD: (0, 255, 255),         # 黄
                QualityLevel.ACCEPTABLE: (0, 165, 255),   # オレンジ
                QualityLevel.POOR: (0, 0, 255),           # 赤
                QualityLevel.REJECT: (128, 0, 128)        # 紫
            }
            
            color = color_map[metrics.quality_level]
            cv2.rectangle(frame, (10, 10), (frame.shape[1] - 10, frame.shape[0] - 10), color, 5)
            
            # テキスト情報をオーバーレイ
            cv2.putText(frame, f"Quality: {metrics.quality_level.value}", 
                       (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            cv2.putText(frame, f"Score: {metrics.overall_score:.2f}", 
                       (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            
            # 画面表示
            cv2.imshow('Data Quality Assessment Test', frame)
            
            # キー入力
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC
                break
        
        cap.release()
        cv2.destroyAllWindows()
        
        # 最終統計表示
        stats = quality_assessor.get_stats()
        print(f"\n=== 評価統計 ===")
        print(f"総評価数: {stats['total_evaluated']}")
        print(f"優秀: {stats['excellent_count']}")
        print(f"良好: {stats['good_count']}")
        print(f"合格: {stats['acceptable_count']}")
        print(f"不良: {stats['poor_count']}")
        print(f"却下: {stats['rejected_count']}")
        print(f"平均総合スコア: {stats['average_overall_score']:.3f}")
    
    except Exception as e:
        logger.error(f"テストエラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()