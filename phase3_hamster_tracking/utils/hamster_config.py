#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ハムスター管理システム設定管理モジュール
YAML設定ファイルの読み込み・管理・検証を行う
"""

import os
import sys
# UTF-8エンコーディング強制設定
if sys.stdout.encoding != 'UTF-8':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

import yaml
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Union, Any, Tuple
from datetime import datetime
import numpy as np
import logging

# ログ設定
logger = logging.getLogger(__name__)

@dataclass
class CageConfig:
    """ケージ設定データクラス"""
    width: float = 380.0
    height: float = 280.0
    depth: float = 200.0
    material: str = "acrylic"
    corner_markers: bool = True
    reference_object_size: float = 50.0
    background_color: str = "white"
    camera_height_mm: float = 400.0
    lighting_type: str = "mixed"
    viewing_angle_degrees: float = 90.0
    
    def get_area_mm2(self) -> float:
        """ケージ面積を取得 (mm²)"""
        return self.width * self.height
        
    def get_aspect_ratio(self) -> float:
        """ケージのアスペクト比を取得"""
        return self.width / self.height
        
    def validate(self) -> Tuple[bool, List[str]]:
        """設定値の妥当性をチェック"""
        errors = []
        
        if self.width <= 0 or self.height <= 0 or self.depth <= 0:
            errors.append("ケージサイズは正の値である必要があります")
            
        if self.width < 100 or self.height < 100:
            errors.append("ケージサイズが小さすぎます (最小100mm)")
            
        if self.width > 1000 or self.height > 1000:
            errors.append("ケージサイズが大きすぎます (最大1000mm)")
            
        if self.reference_object_size <= 0:
            errors.append("基準物体サイズは正の値である必要があります")
            
        return len(errors) == 0, errors

@dataclass
class CalibrationConfig:
    """座標校正設定データクラス"""
    method: str = "manual"
    calibration_points: int = 4
    calibration_matrix_file: str = "calibration_matrix.yaml"
    backup_calibration_file: str = "calibration_backup.yaml"
    validation_enabled: bool = True
    reference_distance_mm: float = 100.0
    accuracy_threshold_mm: float = 5.0
    auto_validation: bool = True
    
    # 自動校正設定
    corner_detection_method: str = "contour"
    edge_threshold: int = 50
    min_area_ratio: float = 0.7
    gaussian_blur_kernel: int = 5
    
    def validate(self) -> Tuple[bool, List[str]]:
        """設定値の妥当性をチェック"""
        errors = []
        
        if self.method not in ["manual", "auto", "hybrid"]:
            errors.append("校正方法は manual, auto, hybrid のいずれかである必要があります")
            
        if self.calibration_points not in [4, 6, 8]:
            errors.append("校正点数は 4, 6, 8 のいずれかである必要があります")
            
        if self.accuracy_threshold_mm <= 0:
            errors.append("精度閾値は正の値である必要があります")
            
        if self.reference_distance_mm <= 0:
            errors.append("基準距離は正の値である必要があります")
            
        return len(errors) == 0, errors

@dataclass 
class DeepLabCutConfig:
    """DeepLabCut設定データクラス"""
    config_file: str = "deeplabcut/config.yaml"
    model_path: str = "deeplabcut/models/latest"
    confidence_threshold: float = 0.7
    inference_engine: str = "tensorflow"
    
    # 身体部位設定
    phase1_parts: List[str] = field(default_factory=lambda: ["nose", "back", "tail"])
    phase2_parts: List[str] = field(default_factory=lambda: ["nose", "head", "back", "hip", "tail"])
    phase3_parts: List[str] = field(default_factory=lambda: ["nose", "head", "left_ear", "right_ear", "back", "hip", "tail"])
    current_phase: str = "phase1"
    
    # 身体部位重み
    body_part_weights: Dict[str, float] = field(default_factory=lambda: {
        'nose': 0.2, 'head': 0.25, 'left_ear': 0.05, 'right_ear': 0.05,
        'back': 0.3, 'hip': 0.25, 'tail': 0.1
    })
    
    # 推論設定
    batch_size: int = 1
    input_resolution: List[int] = field(default_factory=lambda: [480, 640])
    preprocessing_enabled: bool = True
    postprocessing_enabled: bool = True
    
    def get_current_body_parts(self) -> List[str]:
        """現在のフェーズの身体部位を取得"""
        if self.current_phase == "phase1":
            return self.phase1_parts
        elif self.current_phase == "phase2":
            return self.phase2_parts
        elif self.current_phase == "phase3":
            return self.phase3_parts
        else:
            return self.phase1_parts
            
    def get_active_weights(self) -> Dict[str, float]:
        """現在の身体部位の重みを取得"""
        current_parts = self.get_current_body_parts()
        active_weights = {part: self.body_part_weights.get(part, 0.1) for part in current_parts}
        
        # 重みの正規化（合計を1.0にする）
        total_weight = sum(active_weights.values())
        if total_weight > 0:
            active_weights = {part: weight / total_weight for part, weight in active_weights.items()}
        
        return active_weights
        
    def validate(self) -> Tuple[bool, List[str]]:
        """設定値の妥当性をチェック"""
        errors = []
        
        if not 0.0 <= self.confidence_threshold <= 1.0:
            errors.append("信頼度閾値は0.0-1.0の範囲である必要があります")
            
        if self.current_phase not in ["phase1", "phase2", "phase3"]:
            errors.append("現在フェーズは phase1, phase2, phase3 のいずれかである必要があります")
            
        if self.batch_size < 1:
            errors.append("バッチサイズは1以上である必要があります")
            
        # 身体部位重みの合計確認
        total_weight = sum(self.get_active_weights().values())
        if abs(total_weight - 1.0) > 0.1:
            errors.append(f"身体部位重みの合計が1.0付近である必要があります (現在: {total_weight:.3f})")
            
        return len(errors) == 0, errors

@dataclass
class MovementTrackingConfig:
    """移動追跡設定データクラス"""
    # 物理的制約
    max_speed_mm_per_sec: float = 200.0
    max_acceleration_mm_per_sec2: float = 500.0
    min_movement_threshold_mm: float = 2.0
    max_jump_distance_mm: float = 50.0
    
    # フィルタリング設定
    kalman_filter_enabled: bool = True
    smoothing_window_size: int = 5
    outlier_detection_enabled: bool = True
    outlier_threshold_sigma: float = 2.5
    interpolation_max_frames: int = 3
    
    # 統計計算設定
    sampling_interval_sec: float = 1.0
    daily_summary_time: str = "23:59"
    activity_threshold_mm_per_min: float = 100.0
    rest_threshold_sec: int = 300
    
    def validate(self) -> Tuple[bool, List[str]]:
        """設定値の妥当性をチェック"""
        errors = []
        
        if self.max_speed_mm_per_sec <= 0:
            errors.append("最大速度は正の値である必要があります")
            
        if self.min_movement_threshold_mm < 0:
            errors.append("最小移動閾値は非負の値である必要があります")
            
        if self.smoothing_window_size < 1:
            errors.append("平滑化ウィンドウサイズは1以上である必要があります")
            
        if self.outlier_threshold_sigma <= 0:
            errors.append("異常値検出閾値は正の値である必要があります")
            
        if self.sampling_interval_sec <= 0:
            errors.append("サンプリング間隔は正の値である必要があります")
            
        return len(errors) == 0, errors

@dataclass
class MonitoringConfig:
    """システム監視設定データクラス"""
    # 性能監視
    target_fps: float = 2.0
    max_processing_time_ms: int = 500
    memory_limit_mb: int = 512
    cpu_limit_percent: int = 80
    
    # アラート設定
    no_movement_hours: int = 4
    system_error_threshold: int = 10
    low_confidence_ratio_threshold: float = 0.5
    high_memory_usage_threshold: float = 0.9
    
    # ログ設定
    log_level: str = "INFO"
    file_rotation_size_mb: int = 10
    max_log_files: int = 5
    console_output: bool = True
    
    def validate(self) -> Tuple[bool, List[str]]:
        """設定値の妥当性をチェック"""
        errors = []
        
        if self.target_fps <= 0:
            errors.append("目標FPSは正の値である必要があります")
            
        if self.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            errors.append("ログレベルは DEBUG, INFO, WARNING, ERROR のいずれかである必要があります")
            
        if not 0.0 <= self.low_confidence_ratio_threshold <= 1.0:
            errors.append("低信頼度閾値は0.0-1.0の範囲である必要があります")
            
        return len(errors) == 0, errors

@dataclass
class HamsterTrackingConfig:
    """ハムスター管理システム総合設定データクラス"""
    # 基本システム情報
    version: str = "3.0"
    name: str = "hamster_tracking_system"
    description: str = "Hamster tracking system configuration"
    
    # 各種設定
    cage: CageConfig = field(default_factory=CageConfig)
    calibration: CalibrationConfig = field(default_factory=CalibrationConfig)
    deeplabcut: DeepLabCutConfig = field(default_factory=DeepLabCutConfig)
    movement: MovementTrackingConfig = field(default_factory=MovementTrackingConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    
    # データ収集設定
    storage_base_dir: str = "./data"
    auto_quality_check: bool = True
    
    # ネットワーク設定
    rtsp_stream_type: str = "sub"
    rtsp_reconnect_attempts: int = 5
    rtsp_timeout_sec: int = 10
    
    # 開発設定
    debug_mode: bool = False
    test_mode: bool = False
    
    @classmethod
    def from_yaml(cls, file_path: str) -> 'HamsterTrackingConfig':
        """YAML設定ファイルから読み込み"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                yaml_data = yaml.safe_load(f)
                
            # YAML構造からデータクラスに変換
            config = cls()
            
            # システム設定
            if 'system' in yaml_data:
                system = yaml_data['system']
                config.version = system.get('version', config.version)
                config.name = system.get('name', config.name)
                config.description = system.get('description', config.description)
            
            # ケージ設定
            if 'cage' in yaml_data:
                cage_data = yaml_data['cage']
                dims = cage_data.get('dimensions', {})
                specs = cage_data.get('specifications', {})
                env = cage_data.get('environment', {})
                
                config.cage = CageConfig(
                    width=dims.get('width', config.cage.width),
                    height=dims.get('height', config.cage.height),
                    depth=dims.get('depth', config.cage.depth),
                    material=specs.get('material', config.cage.material),
                    corner_markers=specs.get('corner_markers', config.cage.corner_markers),
                    reference_object_size=specs.get('reference_object_size', config.cage.reference_object_size),
                    background_color=specs.get('background_color', config.cage.background_color),
                    camera_height_mm=env.get('camera_height_mm', config.cage.camera_height_mm),
                    lighting_type=env.get('lighting_type', config.cage.lighting_type),
                    viewing_angle_degrees=env.get('viewing_angle_degrees', config.cage.viewing_angle_degrees)
                )
            
            # 校正設定
            if 'coordinate_calibration' in yaml_data:
                cal_data = yaml_data['coordinate_calibration']
                val_data = cal_data.get('validation', {})
                auto_data = cal_data.get('auto_detection', {})
                
                config.calibration = CalibrationConfig(
                    method=cal_data.get('method', config.calibration.method),
                    calibration_points=cal_data.get('calibration_points', config.calibration.calibration_points),
                    calibration_matrix_file=cal_data.get('calibration_matrix_file', config.calibration.calibration_matrix_file),
                    validation_enabled=val_data.get('enabled', config.calibration.validation_enabled),
                    reference_distance_mm=val_data.get('reference_distance_mm', config.calibration.reference_distance_mm),
                    accuracy_threshold_mm=val_data.get('accuracy_threshold_mm', config.calibration.accuracy_threshold_mm),
                    corner_detection_method=auto_data.get('corner_detection_method', config.calibration.corner_detection_method),
                    edge_threshold=auto_data.get('edge_threshold', config.calibration.edge_threshold)
                )
            
            # DeepLabCut設定
            if 'deeplabcut' in yaml_data:
                dlc_data = yaml_data['deeplabcut']
                model_data = dlc_data.get('model', {})
                parts_data = dlc_data.get('body_parts', {})
                weights_data = dlc_data.get('body_part_weights', {})
                inf_data = dlc_data.get('inference', {})
                
                config.deeplabcut = DeepLabCutConfig(
                    config_file=model_data.get('config_file', config.deeplabcut.config_file),
                    model_path=model_data.get('model_path', config.deeplabcut.model_path),
                    confidence_threshold=model_data.get('confidence_threshold', config.deeplabcut.confidence_threshold),
                    current_phase=parts_data.get('current_phase', config.deeplabcut.current_phase),
                    body_part_weights=weights_data if weights_data else config.deeplabcut.body_part_weights,
                    batch_size=inf_data.get('batch_size', config.deeplabcut.batch_size),
                    input_resolution=inf_data.get('input_resolution', config.deeplabcut.input_resolution)
                )
            
            # 移動追跡設定
            if 'movement_tracking' in yaml_data:
                move_data = yaml_data['movement_tracking']
                const_data = move_data.get('constraints', {})
                filt_data = move_data.get('filtering', {})
                stat_data = move_data.get('statistics', {})
                
                config.movement = MovementTrackingConfig(
                    max_speed_mm_per_sec=const_data.get('max_speed_mm_per_sec', config.movement.max_speed_mm_per_sec),
                    max_acceleration_mm_per_sec2=const_data.get('max_acceleration_mm_per_sec2', config.movement.max_acceleration_mm_per_sec2),
                    min_movement_threshold_mm=const_data.get('min_movement_threshold_mm', config.movement.min_movement_threshold_mm),
                    kalman_filter_enabled=filt_data.get('kalman_filter_enabled', config.movement.kalman_filter_enabled),
                    smoothing_window_size=filt_data.get('smoothing_window_size', config.movement.smoothing_window_size),
                    activity_threshold_mm_per_min=stat_data.get('activity_threshold_mm_per_min', config.movement.activity_threshold_mm_per_min)
                )
            
            # 監視設定
            if 'monitoring' in yaml_data:
                mon_data = yaml_data['monitoring']
                perf_data = mon_data.get('performance', {})
                alert_data = mon_data.get('alerts', {})
                log_data = mon_data.get('logging', {})
                
                config.monitoring = MonitoringConfig(
                    target_fps=perf_data.get('target_fps', config.monitoring.target_fps),
                    max_processing_time_ms=perf_data.get('max_processing_time_ms', config.monitoring.max_processing_time_ms),
                    memory_limit_mb=perf_data.get('memory_limit_mb', config.monitoring.memory_limit_mb),
                    no_movement_hours=alert_data.get('no_movement_hours', config.monitoring.no_movement_hours),
                    log_level=log_data.get('level', config.monitoring.log_level)
                )
            
            # その他設定
            if 'development' in yaml_data:
                dev_data = yaml_data['development']
                config.debug_mode = dev_data.get('debug_mode', config.debug_mode)
                config.test_mode = dev_data.get('test_mode', config.test_mode)
                
            logger.info(f"設定ファイル '{file_path}' を正常に読み込みました")
            return config
            
        except FileNotFoundError:
            logger.error(f"設定ファイル '{file_path}' が見つかりません")
            raise
        except yaml.YAMLError as e:
            logger.error(f"YAML解析エラー: {e}")
            raise
        except Exception as e:
            logger.error(f"設定ファイル読み込みエラー: {e}")
            raise
    
    def to_yaml(self, file_path: str) -> None:
        """YAML設定ファイルに保存"""
        try:
            # データクラスをYAML構造に変換
            yaml_data = {
                'system': {
                    'version': self.version,
                    'name': self.name,
                    'description': self.description
                },
                'cage': {
                    'dimensions': {
                        'width': self.cage.width,
                        'height': self.cage.height,
                        'depth': self.cage.depth
                    },
                    'specifications': {
                        'material': self.cage.material,
                        'corner_markers': self.cage.corner_markers,
                        'reference_object_size': self.cage.reference_object_size,
                        'background_color': self.cage.background_color
                    },
                    'environment': {
                        'camera_height_mm': self.cage.camera_height_mm,
                        'lighting_type': self.cage.lighting_type,
                        'viewing_angle_degrees': self.cage.viewing_angle_degrees
                    }
                },
                'coordinate_calibration': {
                    'method': self.calibration.method,
                    'calibration_points': self.calibration.calibration_points,
                    'calibration_matrix_file': self.calibration.calibration_matrix_file,
                    'validation': {
                        'enabled': self.calibration.validation_enabled,
                        'reference_distance_mm': self.calibration.reference_distance_mm,
                        'accuracy_threshold_mm': self.calibration.accuracy_threshold_mm
                    }
                },
                'deeplabcut': {
                    'model': {
                        'config_file': self.deeplabcut.config_file,
                        'model_path': self.deeplabcut.model_path,
                        'confidence_threshold': self.deeplabcut.confidence_threshold
                    },
                    'body_parts': {
                        'current_phase': self.deeplabcut.current_phase
                    },
                    'body_part_weights': self.deeplabcut.body_part_weights
                },
                'movement_tracking': {
                    'constraints': {
                        'max_speed_mm_per_sec': self.movement.max_speed_mm_per_sec,
                        'min_movement_threshold_mm': self.movement.min_movement_threshold_mm
                    },
                    'filtering': {
                        'kalman_filter_enabled': self.movement.kalman_filter_enabled,
                        'smoothing_window_size': self.movement.smoothing_window_size
                    },
                    'statistics': {
                        'activity_threshold_mm_per_min': self.movement.activity_threshold_mm_per_min
                    }
                },
                'monitoring': {
                    'performance': {
                        'target_fps': self.monitoring.target_fps,
                        'max_processing_time_ms': self.monitoring.max_processing_time_ms
                    },
                    'logging': {
                        'level': self.monitoring.log_level
                    }
                },
                'development': {
                    'debug_mode': self.debug_mode,
                    'test_mode': self.test_mode
                },
                'metadata': {
                    'config_created': datetime.now().isoformat() + 'Z',
                    'config_version': '1.0',
                    'last_modified': datetime.now().isoformat() + 'Z'
                }
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(yaml_data, f, default_flow_style=False, 
                         allow_unicode=True, indent=2, sort_keys=False)
                         
            logger.info(f"設定ファイル '{file_path}' に保存しました")
            
        except Exception as e:
            logger.error(f"設定ファイル保存エラー: {e}")
            raise
    
    def validate_all(self) -> Tuple[bool, List[str]]:
        """全設定の妥当性をチェック"""
        all_errors = []
        
        # 各設定の検証
        cage_valid, cage_errors = self.cage.validate()
        cal_valid, cal_errors = self.calibration.validate()
        dlc_valid, dlc_errors = self.deeplabcut.validate()
        move_valid, move_errors = self.movement.validate()
        mon_valid, mon_errors = self.monitoring.validate()
        
        # エラー収集
        if not cage_valid:
            all_errors.extend([f"ケージ設定: {err}" for err in cage_errors])
        if not cal_valid:
            all_errors.extend([f"校正設定: {err}" for err in cal_errors])
        if not dlc_valid:
            all_errors.extend([f"DeepLabCut設定: {err}" for err in dlc_errors])
        if not move_valid:
            all_errors.extend([f"移動追跡設定: {err}" for err in move_errors])
        if not mon_valid:
            all_errors.extend([f"監視設定: {err}" for err in mon_errors])
        
        return len(all_errors) == 0, all_errors
    
    def update_cage_size(self, width: float, height: float, depth: float = None) -> None:
        """ケージサイズ更新"""
        self.cage.width = width
        self.cage.height = height
        if depth is not None:
            self.cage.depth = depth
            
        logger.info(f"ケージサイズを更新: {width}x{height}mm")
    
    def get_cage_corners_mm(self) -> List[Tuple[float, float]]:
        """ケージ四隅座標を取得 (mm単位)"""
        return [
            (0, 0),                           # 左上
            (self.cage.width, 0),             # 右上
            (self.cage.width, self.cage.height), # 右下
            (0, self.cage.height)             # 左下
        ]
    
    def summary(self) -> str:
        """設定サマリーを取得"""
        return f"""
=== ハムスター管理システム設定サマリー ===
システム: {self.name} v{self.version}
ケージサイズ: {self.cage.width}×{self.cage.height}×{self.cage.depth}mm
校正方法: {self.calibration.method}
DeepLabCutフェーズ: {self.deeplabcut.current_phase}
目標FPS: {self.monitoring.target_fps}
デバッグモード: {self.debug_mode}
"""

def load_config(file_path: str = None) -> HamsterTrackingConfig:
    """設定ファイルを読み込み（デフォルトパス対応）"""
    if file_path is None:
        # デフォルト設定ファイルパス
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(base_dir, 'config', 'hamster_config.yaml')
    
    if os.path.exists(file_path):
        return HamsterTrackingConfig.from_yaml(file_path)
    else:
        logger.warning(f"設定ファイル '{file_path}' が見つかりません。デフォルト設定を使用します。")
        return HamsterTrackingConfig()

if __name__ == "__main__":
    # 設定テスト
    try:
        # デフォルト設定作成
        config = HamsterTrackingConfig()
        print("=== デフォルト設定 ===")
        print(config.summary())
        
        # 妥当性チェック
        valid, errors = config.validate_all()
        print(f"\n設定妥当性: {'✅ 有効' if valid else '❌ 無効'}")
        if not valid:
            for error in errors:
                print(f"  - {error}")
        
        # YAML保存テスト
        test_file = "/tmp/test_config.yaml"
        config.to_yaml(test_file)
        print(f"\nテスト保存: {test_file}")
        
        # YAML読み込みテスト
        config2 = HamsterTrackingConfig.from_yaml(test_file)
        print("✅ YAML読み書きテスト成功")
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()