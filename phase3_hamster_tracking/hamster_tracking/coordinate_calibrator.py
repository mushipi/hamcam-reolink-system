#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
座標校正システム
ピクセル座標からmm座標への変換機能を提供
"""

import os
import sys
# UTF-8エンコーディング強制設定
if sys.stdout.encoding != 'UTF-8':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

import cv2
import numpy as np
import yaml
from typing import List, Tuple, Optional, Dict, Any
import logging
from datetime import datetime
from dataclasses import dataclass, asdict
import json

# プロジェクトモジュール
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from phase3_hamster_tracking.utils.hamster_config import HamsterTrackingConfig, load_config

# ログ設定
logger = logging.getLogger(__name__)

@dataclass
class CalibrationPoint:
    """校正点データクラス"""
    pixel_x: float
    pixel_y: float
    world_x: float  # mm
    world_y: float  # mm
    confidence: float = 1.0
    manually_adjusted: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CalibrationPoint':
        """辞書から復元"""
        return cls(**data)

@dataclass
class CalibrationResult:
    """校正結果データクラス"""
    homography_matrix: np.ndarray
    inverse_homography: np.ndarray
    calibration_points: List[CalibrationPoint]
    rmse_error: float
    max_error: float
    mean_error: float
    calibration_method: str
    timestamp: str
    cage_size_mm: Tuple[float, float]
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換（YAML保存用）"""
        return {
            'homography_matrix': self.homography_matrix.tolist(),
            'inverse_homography': self.inverse_homography.tolist(),
            'calibration_points': [cp.to_dict() for cp in self.calibration_points],
            'rmse_error': float(self.rmse_error),
            'max_error': float(self.max_error),
            'mean_error': float(self.mean_error),
            'calibration_method': self.calibration_method,
            'timestamp': self.timestamp,
            'cage_size_mm': self.cage_size_mm
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CalibrationResult':
        """辞書から復元"""
        return cls(
            homography_matrix=np.array(data['homography_matrix']),
            inverse_homography=np.array(data['inverse_homography']),
            calibration_points=[CalibrationPoint.from_dict(cp) for cp in data['calibration_points']],
            rmse_error=data['rmse_error'],
            max_error=data['max_error'],
            mean_error=data['mean_error'],
            calibration_method=data['calibration_method'],
            timestamp=data['timestamp'],
            cage_size_mm=tuple(data['cage_size_mm'])
        )

class CoordinateCalibrator:
    """座標校正システムメインクラス"""
    
    def __init__(self, config: HamsterTrackingConfig = None):
        """
        初期化
        
        Args:
            config: ハムスター管理システム設定
        """
        self.config = config if config else load_config()
        self.cage_size = (self.config.cage.width, self.config.cage.height)
        
        # 校正状態
        self.is_calibrated = False
        self.calibration_result: Optional[CalibrationResult] = None
        
        # 校正ファイルパス
        config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config')
        self.calibration_file = os.path.join(config_dir, self.config.calibration.calibration_matrix_file)
        
        logger.info(f"座標校正システム初期化完了 - ケージサイズ: {self.cage_size[0]}x{self.cage_size[1]}mm")
        
        # 既存の校正データを読み込み試行
        self.load_calibration()
    
    def calibrate_manual_4point(self, corner_pixels: List[Tuple[int, int]]) -> CalibrationResult:
        """
        手動4点校正
        
        Args:
            corner_pixels: ケージ四隅のピクセル座標 [左上, 右上, 右下, 左下]
            
        Returns:
            CalibrationResult: 校正結果
        """
        if len(corner_pixels) != 4:
            raise ValueError("4点の座標が必要です")
        
        logger.info("手動4点校正開始")
        
        # ケージ四隅の実世界座標 (mm)
        world_corners = [
            (0, 0),                           # 左上
            (self.cage_size[0], 0),           # 右上  
            (self.cage_size[0], self.cage_size[1]), # 右下
            (0, self.cage_size[1])            # 左下
        ]
        
        # 校正点データ作成
        calibration_points = []
        for i, (pixel_pos, world_pos) in enumerate(zip(corner_pixels, world_corners)):
            point = CalibrationPoint(
                pixel_x=float(pixel_pos[0]),
                pixel_y=float(pixel_pos[1]),
                world_x=float(world_pos[0]),
                world_y=float(world_pos[1]),
                confidence=1.0,
                manually_adjusted=True
            )
            calibration_points.append(point)
        
        # 座標変換行列計算
        pixel_points = np.array([[cp.pixel_x, cp.pixel_y] for cp in calibration_points], dtype=np.float32)
        world_points = np.array([[cp.world_x, cp.world_y] for cp in calibration_points], dtype=np.float32)
        
        # ホモグラフィ行列計算
        homography_matrix, _ = cv2.findHomography(pixel_points, world_points, cv2.RANSAC)
        
        if homography_matrix is None:
            raise RuntimeError("ホモグラフィ行列の計算に失敗しました")
        
        # 逆変換行列計算
        inverse_homography = np.linalg.inv(homography_matrix)
        
        # 校正精度評価
        rmse_error, max_error, mean_error = self._evaluate_calibration_accuracy(
            calibration_points, homography_matrix
        )
        
        # 校正結果作成
        self.calibration_result = CalibrationResult(
            homography_matrix=homography_matrix,
            inverse_homography=inverse_homography,
            calibration_points=calibration_points,
            rmse_error=rmse_error,
            max_error=max_error,
            mean_error=mean_error,
            calibration_method="manual_4point",
            timestamp=datetime.now().isoformat() + 'Z',
            cage_size_mm=self.cage_size
        )
        
        self.is_calibrated = True
        
        logger.info(f"手動4点校正完了 - RMSE誤差: {rmse_error:.2f}mm, 最大誤差: {max_error:.2f}mm")
        
        return self.calibration_result
    
    def _evaluate_calibration_accuracy(self, calibration_points: List[CalibrationPoint], 
                                     homography_matrix: np.ndarray) -> Tuple[float, float, float]:
        """
        校正精度評価
        
        Returns:
            Tuple[RMSE誤差, 最大誤差, 平均誤差] (mm単位)
        """
        errors = []
        
        for point in calibration_points:
            # ピクセル座標をmm座標に変換
            pixel_point = np.array([[point.pixel_x, point.pixel_y]], dtype=np.float32)
            pixel_point = np.array([pixel_point])  # shape: (1, 1, 2)
            
            converted_point = cv2.perspectiveTransform(pixel_point, homography_matrix)[0][0]
            
            # 誤差計算
            error_x = converted_point[0] - point.world_x
            error_y = converted_point[1] - point.world_y
            error_distance = np.sqrt(error_x**2 + error_y**2)
            errors.append(error_distance)
        
        rmse_error = np.sqrt(np.mean(np.array(errors)**2))
        max_error = np.max(errors)
        mean_error = np.mean(errors)
        
        return rmse_error, max_error, mean_error
    
    def pixel_to_mm(self, pixel_coord: Tuple[float, float]) -> Tuple[float, float]:
        """
        ピクセル座標をmm座標に変換
        
        Args:
            pixel_coord: ピクセル座標 (x, y)
            
        Returns:
            mm座標 (x, y)
        """
        if not self.is_calibrated or self.calibration_result is None:
            raise RuntimeError("校正が完了していません")
        
        # OpenCV用の座標変換
        pixel_point = np.array([[pixel_coord]], dtype=np.float32)
        mm_point = cv2.perspectiveTransform(pixel_point, self.calibration_result.homography_matrix)[0][0]
        
        return float(mm_point[0]), float(mm_point[1])
    
    def mm_to_pixel(self, mm_coord: Tuple[float, float]) -> Tuple[float, float]:
        """
        mm座標をピクセル座標に変換
        
        Args:
            mm_coord: mm座標 (x, y)
            
        Returns:
            ピクセル座標 (x, y)
        """
        if not self.is_calibrated or self.calibration_result is None:
            raise RuntimeError("校正が完了していません")
        
        # OpenCV用の座標変換
        mm_point = np.array([[mm_coord]], dtype=np.float32)
        pixel_point = cv2.perspectiveTransform(mm_point, self.calibration_result.inverse_homography)[0][0]
        
        return float(pixel_point[0]), float(pixel_point[1])
    
    def batch_pixel_to_mm(self, pixel_coords: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """
        複数のピクセル座標を一括でmm座標に変換
        
        Args:
            pixel_coords: ピクセル座標のリスト
            
        Returns:
            mm座標のリスト
        """
        if not self.is_calibrated or self.calibration_result is None:
            raise RuntimeError("校正が完了していません")
        
        if not pixel_coords:
            return []
        
        # バッチ変換
        pixel_points = np.array([list(coord) for coord in pixel_coords], dtype=np.float32)
        pixel_points = pixel_points.reshape(-1, 1, 2)  # OpenCV形式に変換
        
        mm_points = cv2.perspectiveTransform(pixel_points, self.calibration_result.homography_matrix)
        
        # 結果をタプルのリストに変換
        return [(float(point[0][0]), float(point[0][1])) for point in mm_points]
    
    def validate_calibration(self, test_distance_mm: float = None) -> Dict[str, Any]:
        """
        校正精度検証
        
        Args:
            test_distance_mm: テスト用既知距離（Noneの場合は設定値使用）
            
        Returns:
            検証結果辞書
        """
        if not self.is_calibrated or self.calibration_result is None:
            raise RuntimeError("校正が完了していません")
        
        if test_distance_mm is None:
            test_distance_mm = self.config.calibration.reference_distance_mm
        
        logger.info(f"校正精度検証開始 - テスト距離: {test_distance_mm}mm")
        
        # ケージ中央から基準距離の点を設定
        cage_center_mm = (self.cage_size[0] / 2, self.cage_size[1] / 2)
        test_point_mm = (cage_center_mm[0] + test_distance_mm, cage_center_mm[1])
        
        # mm → pixel → mm変換テスト
        center_pixel = self.mm_to_pixel(cage_center_mm)
        test_pixel = self.mm_to_pixel(test_point_mm)
        
        # ピクセル座標での距離計算
        pixel_distance = np.sqrt((test_pixel[0] - center_pixel[0])**2 + (test_pixel[1] - center_pixel[1])**2)
        
        # ピクセル座標をmm座標に逆変換
        center_mm_converted = self.pixel_to_mm(center_pixel)
        test_mm_converted = self.pixel_to_mm(test_pixel)
        
        # 変換後のmm距離計算
        converted_distance = np.sqrt((test_mm_converted[0] - center_mm_converted[0])**2 + 
                                   (test_mm_converted[1] - center_mm_converted[1])**2)
        
        # 誤差計算
        distance_error = abs(converted_distance - test_distance_mm)
        error_percentage = (distance_error / test_distance_mm) * 100
        
        # 校正品質評価
        accuracy_threshold = self.config.calibration.accuracy_threshold_mm
        is_accurate = distance_error <= accuracy_threshold
        
        validation_result = {
            'test_distance_mm': test_distance_mm,
            'measured_distance_mm': converted_distance,
            'distance_error_mm': distance_error,
            'error_percentage': error_percentage,
            'accuracy_threshold_mm': accuracy_threshold,
            'is_accurate': is_accurate,
            'pixel_distance': pixel_distance,
            'calibration_rmse': self.calibration_result.rmse_error,
            'calibration_max_error': self.calibration_result.max_error,
            'validation_passed': is_accurate and self.calibration_result.rmse_error <= accuracy_threshold
        }
        
        logger.info(f"校正精度検証完了 - 距離誤差: {distance_error:.2f}mm ({error_percentage:.1f}%)")
        
        return validation_result
    
    def save_calibration(self, file_path: str = None) -> None:
        """
        校正データをYAMLファイルに保存
        
        Args:
            file_path: 保存ファイルパス（Noneの場合はデフォルトパス使用）
        """
        if not self.is_calibrated or self.calibration_result is None:
            raise RuntimeError("保存する校正データがありません")
        
        if file_path is None:
            file_path = self.calibration_file
        
        # 校正データをYAML形式で準備
        calibration_data = {
            'calibration_info': {
                'status': 'calibrated',
                'created_at': self.calibration_result.timestamp,
                'last_updated': datetime.now().isoformat() + 'Z',
                'cage_size_mm': list(self.calibration_result.cage_size_mm),
                'method': self.calibration_result.calibration_method,
                'validation_error_mm': float(self.calibration_result.rmse_error),
                'operator': 'CoordinateCalibrator',
                'notes': f'Auto-generated calibration data with {self.calibration_result.calibration_method} method'
            },
            
            'transformation_matrix': {
                'homography': self.calibration_result.homography_matrix.tolist(),
                'inverse_homography': self.calibration_result.inverse_homography.tolist(),
                'statistics': {
                    'pixel_to_mm_ratio_x': float(self.cage_size[0] / 640),  # 概算値
                    'pixel_to_mm_ratio_y': float(self.cage_size[1] / 480),  # 概算値
                    'rmse_error_mm': float(self.calibration_result.rmse_error),
                    'max_error_mm': float(self.calibration_result.max_error),
                    'mean_error_mm': float(self.calibration_result.mean_error)
                }
            },
            
            'calibration_points': {
                'pixel_coordinates': [[cp.pixel_x, cp.pixel_y] for cp in self.calibration_result.calibration_points],
                'world_coordinates_mm': [[cp.world_x, cp.world_y] for cp in self.calibration_result.calibration_points],
                'point_quality': {
                    'detection_confidence': [cp.confidence for cp in self.calibration_result.calibration_points],
                    'manual_adjustment': [cp.manually_adjusted for cp in self.calibration_result.calibration_points]
                }
            },
            
            'accuracy_metrics': {
                'rmse_error_mm': float(self.calibration_result.rmse_error),
                'max_error_mm': float(self.calibration_result.max_error),
                'mean_error_mm': float(self.calibration_result.mean_error),
                'accuracy_threshold_mm': float(self.config.calibration.accuracy_threshold_mm),
                'meets_accuracy_requirement': bool(self.calibration_result.rmse_error <= self.config.calibration.accuracy_threshold_mm)
            },
            
            'quality_control': {
                'calibration_id': f"cal_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'validation_passed': bool(self.calibration_result.rmse_error <= self.config.calibration.accuracy_threshold_mm),
                'approval_status': 'approved' if self.calibration_result.rmse_error <= self.config.calibration.accuracy_threshold_mm else 'needs_review'
            }
        }
        
        try:
            # バックアップ作成
            if os.path.exists(file_path):
                backup_path = file_path + '.backup.' + datetime.now().strftime('%Y%m%d_%H%M%S')
                import shutil
                shutil.copy2(file_path, backup_path)
                logger.info(f"既存校正データをバックアップ: {backup_path}")
            
            # 新しい校正データ保存
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(calibration_data, f, default_flow_style=False, 
                         allow_unicode=True, indent=2, sort_keys=False)
            
            logger.info(f"校正データを保存しました: {file_path}")
            
        except Exception as e:
            logger.error(f"校正データ保存エラー: {e}")
            raise
    
    def load_calibration(self, file_path: str = None) -> bool:
        """
        校正データをYAMLファイルから読み込み
        
        Args:
            file_path: 読み込みファイルパス（Noneの場合はデフォルトパス使用）
            
        Returns:
            読み込み成功フラグ
        """
        if file_path is None:
            file_path = self.calibration_file
        
        if not os.path.exists(file_path):
            logger.info(f"校正ファイル '{file_path}' が見つかりません")
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                calibration_data = yaml.safe_load(f)
            
            # 校正データの有効性チェック
            if not calibration_data.get('calibration_info', {}).get('status') == 'calibrated':
                logger.warning("校正データが未完了状態です")
                return False
            
            # 変換行列の復元
            matrix_data = calibration_data.get('transformation_matrix', {})
            homography = matrix_data.get('homography')
            inverse_homography = matrix_data.get('inverse_homography')
            
            if homography is None or inverse_homography is None:
                logger.warning("変換行列データが見つかりません")
                return False
            
            # 校正点データの復元
            points_data = calibration_data.get('calibration_points', {})
            pixel_coords = points_data.get('pixel_coordinates', [])
            world_coords = points_data.get('world_coordinates_mm', [])
            confidences = points_data.get('point_quality', {}).get('detection_confidence', [1.0] * len(pixel_coords))
            manual_flags = points_data.get('point_quality', {}).get('manual_adjustment', [False] * len(pixel_coords))
            
            # 校正点オブジェクト作成
            calibration_points = []
            for i, (pixel, world) in enumerate(zip(pixel_coords, world_coords)):
                point = CalibrationPoint(
                    pixel_x=pixel[0], pixel_y=pixel[1],
                    world_x=world[0], world_y=world[1],
                    confidence=confidences[i] if i < len(confidences) else 1.0,
                    manually_adjusted=manual_flags[i] if i < len(manual_flags) else False
                )
                calibration_points.append(point)
            
            # 精度メトリクスの復元
            accuracy_data = calibration_data.get('accuracy_metrics', {})
            rmse_error = accuracy_data.get('rmse_error_mm', 0.0)
            max_error = accuracy_data.get('max_error_mm', 0.0)
            mean_error = accuracy_data.get('mean_error_mm', 0.0)
            
            # CalibrationResultオブジェクト作成
            self.calibration_result = CalibrationResult(
                homography_matrix=np.array(homography),
                inverse_homography=np.array(inverse_homography),
                calibration_points=calibration_points,
                rmse_error=rmse_error,
                max_error=max_error,
                mean_error=mean_error,
                calibration_method=calibration_data.get('calibration_info', {}).get('method', 'unknown'),
                timestamp=calibration_data.get('calibration_info', {}).get('created_at', ''),
                cage_size_mm=tuple(calibration_data.get('calibration_info', {}).get('cage_size_mm', self.cage_size))
            )
            
            self.is_calibrated = True
            
            logger.info(f"校正データを読み込みました: {file_path} (誤差: {rmse_error:.2f}mm)")
            return True
            
        except Exception as e:
            logger.error(f"校正データ読み込みエラー: {e}")
            return False
    
    def get_calibration_info(self) -> Dict[str, Any]:
        """校正情報を取得"""
        if not self.is_calibrated or self.calibration_result is None:
            return {
                'is_calibrated': False,
                'status': 'uncalibrated'
            }
        
        return {
            'is_calibrated': True,
            'status': 'calibrated',
            'method': self.calibration_result.calibration_method,
            'timestamp': self.calibration_result.timestamp,
            'cage_size_mm': self.calibration_result.cage_size_mm,
            'rmse_error_mm': self.calibration_result.rmse_error,
            'max_error_mm': self.calibration_result.max_error,
            'meets_accuracy_requirement': self.calibration_result.rmse_error <= self.config.calibration.accuracy_threshold_mm,
            'calibration_points_count': len(self.calibration_result.calibration_points)
        }
    
    def reset_calibration(self) -> None:
        """校正データをリセット"""
        self.is_calibrated = False
        self.calibration_result = None
        logger.info("校正データをリセットしました")

def demo_calibration():
    """校正システムのデモ"""
    print("=== 座標校正システムデモ ===")
    
    # 設定読み込み
    config = load_config()
    calibrator = CoordinateCalibrator(config)
    
    print(f"ケージサイズ: {calibrator.cage_size[0]}x{calibrator.cage_size[1]}mm")
    
    # 校正情報表示
    info = calibrator.get_calibration_info()
    print(f"校正状態: {info}")
    
    if not calibrator.is_calibrated:
        print("\n校正が必要です。サンプル4点校正を実行...")
        
        # サンプル校正点（実際のケージ撮影時に取得する座標）
        sample_corners = [
            (100, 80),    # 左上
            (540, 85),    # 右上
            (545, 395),   # 右下
            (95, 390)     # 左下
        ]
        
        try:
            # 校正実行
            result = calibrator.calibrate_manual_4point(sample_corners)
            print(f"校正完了 - RMSE誤差: {result.rmse_error:.2f}mm")
            
            # 校正保存
            calibrator.save_calibration()
            
            # 校正検証
            validation = calibrator.validate_calibration()
            print(f"校正検証: {validation['validation_passed']}")
            print(f"距離誤差: {validation['distance_error_mm']:.2f}mm ({validation['error_percentage']:.1f}%)")
            
        except Exception as e:
            print(f"校正エラー: {e}")
            return
    
    # 座標変換テスト
    print("\n=== 座標変換テスト ===")
    test_pixels = [
        (320, 240),  # 画面中央
        (100, 100),  # 左上付近
        (500, 350)   # 右下付近
    ]
    
    for pixel in test_pixels:
        try:
            mm_coord = calibrator.pixel_to_mm(pixel)
            pixel_back = calibrator.mm_to_pixel(mm_coord)
            print(f"Pixel {pixel} → MM {mm_coord[0]:.1f},{mm_coord[1]:.1f} → Pixel {pixel_back[0]:.1f},{pixel_back[1]:.1f}")
        except Exception as e:
            print(f"変換エラー ({pixel}): {e}")

if __name__ == "__main__":
    # デモ実行
    demo_calibration()