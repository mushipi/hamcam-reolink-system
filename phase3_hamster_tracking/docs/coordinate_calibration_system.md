# 座標校正システム技術仕様書

## 概要

`CoordinateCalibrator`は、カメラ画像のピクセル座標を実世界の物理座標（mm単位）に変換するシステムです。4点校正による射影変換を使用し、ハムスターケージの正確な寸法マッピングを実現します。

## システムアーキテクチャ

```
CoordinateCalibrator
├── 4点校正システム        # 物理座標定義・マッピング
├── 射影変換エンジン        # OpenCV Perspective Transform
├── 双方向座標変換         # Pixel ↔ mm 変換
├── 校正精度検証          # 変換誤差計算・検証
├── YAML設定管理          # 校正データ永続化
└── GUI校正ツール連携      # 対話的校正インターフェース
```

## 主要機能

### 1. 4点校正システム

#### 校正点定義
```python
# ケージ4隅の物理座標（mm単位）
physical_corners = {
    'top_left': (0.0, 0.0),           # 左上角
    'top_right': (380.0, 0.0),        # 右上角（幅380mm）
    'bottom_left': (0.0, 280.0),      # 左下角（高さ280mm）
    'bottom_right': (380.0, 280.0)    # 右下角
}

# 対応するピクセル座標（校正時にユーザー指定）
pixel_corners = {
    'top_left': (x1, y1),
    'top_right': (x2, y2), 
    'bottom_left': (x3, y3),
    'bottom_right': (x4, y4)
}
```

#### 射影変換行列計算
```python
def calculate_transformation_matrix():
    """4点対応による射影変換行列を計算"""
    # 物理座標 → ピクセル座標変換行列
    pixel_to_mm_matrix = cv2.getPerspectiveTransform(
        src_points=pixel_corners_array,      # ピクセル座標
        dst_points=physical_corners_array    # 物理座標
    )
    
    # ピクセル座標 → 物理座標変換行列
    mm_to_pixel_matrix = cv2.getPerspectiveTransform(
        src_points=physical_corners_array,   # 物理座標
        dst_points=pixel_corners_array       # ピクセル座標
    )
    
    return pixel_to_mm_matrix, mm_to_pixel_matrix
```

### 2. 双方向座標変換

#### ピクセル → mm変換
```python
def pixel_to_mm(self, pixel_coord: Tuple[float, float]) -> Tuple[float, float]:
    """ピクセル座標を物理座標（mm）に変換"""
    if not self.is_calibrated:
        raise RuntimeError("座標校正が実行されていません")
    
    # 同次座標に変換
    pixel_homogeneous = np.array([pixel_coord[0], pixel_coord[1], 1.0], dtype=np.float32)
    
    # 射影変換適用
    mm_homogeneous = self.pixel_to_mm_matrix @ pixel_homogeneous
    
    # 同次座標を通常座標に変換
    mm_coord = (mm_homogeneous[0] / mm_homogeneous[2], 
                mm_homogeneous[1] / mm_homogeneous[2])
    
    return mm_coord
```

#### mm → ピクセル変換
```python
def mm_to_pixel(self, mm_coord: Tuple[float, float]) -> Tuple[float, float]:
    """物理座標（mm）をピクセル座標に変換"""
    if not self.is_calibrated:
        raise RuntimeError("座標校正が実行されていません")
    
    # 同次座標変換と射影変換適用
    mm_homogeneous = np.array([mm_coord[0], mm_coord[1], 1.0], dtype=np.float32)
    pixel_homogeneous = self.mm_to_pixel_matrix @ mm_homogeneous
    
    pixel_coord = (pixel_homogeneous[0] / pixel_homogeneous[2],
                   pixel_homogeneous[1] / pixel_homogeneous[2])
    
    return pixel_coord
```

### 3. 校正精度検証

#### 再投影誤差計算
```python
def calculate_calibration_error(self):
    """校正精度を計算（再投影誤差）"""
    total_error = 0.0
    error_points = []
    
    for original_pixel, expected_physical in zip(self.pixel_corners, self.physical_corners):
        # 順変換: pixel → mm
        calculated_physical = self.pixel_to_mm(original_pixel)
        
        # 逆変換: mm → pixel  
        back_projected_pixel = self.mm_to_pixel(calculated_physical)
        
        # 再投影誤差計算（ピクセル単位）
        error = np.sqrt((original_pixel[0] - back_projected_pixel[0])**2 + 
                       (original_pixel[1] - back_projected_pixel[1])**2)
        
        error_points.append(error)
        total_error += error
    
    average_error = total_error / len(self.pixel_corners)
    return average_error, error_points
```

#### 物理距離検証
```python
def validate_physical_distances(self):
    """実際の物理距離との整合性確認"""
    # 水平距離検証（期待値: 380mm）
    horizontal_distance = self.calculate_distance_mm(
        self.pixel_corners['top_left'], 
        self.pixel_corners['top_right']
    )
    
    # 垂直距離検証（期待値: 280mm）
    vertical_distance = self.calculate_distance_mm(
        self.pixel_corners['top_left'],
        self.pixel_corners['bottom_left']
    )
    
    horizontal_error = abs(horizontal_distance - 380.0)
    vertical_error = abs(vertical_distance - 280.0)
    
    return {
        'horizontal_distance': horizontal_distance,
        'vertical_distance': vertical_distance,
        'horizontal_error_mm': horizontal_error,
        'vertical_error_mm': vertical_error
    }
```

### 4. 距離・面積計算機能

#### 実測距離計算
```python
def calculate_distance_mm(self, pixel1: Tuple[float, float], pixel2: Tuple[float, float]) -> float:
    """2点間の実測距離（mm単位）を計算"""
    mm1 = self.pixel_to_mm(pixel1)
    mm2 = self.pixel_to_mm(pixel2)
    
    distance = np.sqrt((mm2[0] - mm1[0])**2 + (mm2[1] - mm1[1])**2)
    return distance
```

#### 実測面積計算
```python
def calculate_area_mm2(self, pixel_contour: np.ndarray) -> float:
    """輪郭の実測面積（mm²単位）を計算"""
    # 輪郭をmm座標に変換
    mm_contour = np.array([self.pixel_to_mm((pt[0], pt[1])) for pt in pixel_contour])
    
    # Shoelace公式で面積計算
    n = len(mm_contour)
    area = 0.5 * abs(sum(mm_contour[i][0] * mm_contour[(i + 1) % n][1] - 
                        mm_contour[(i + 1) % n][0] * mm_contour[i][1] 
                        for i in range(n)))
    return area
```

### 5. 設定管理システム

#### YAML形式での永続化
```yaml
# calibration_matrix.yaml
calibration_data:
  pixel_corners:
    top_left: [145, 95]
    top_right: [495, 95] 
    bottom_left: [145, 375]
    bottom_right: [495, 375]
  
  physical_corners:
    top_left: [0.0, 0.0]
    top_right: [380.0, 0.0]
    bottom_left: [0.0, 280.0] 
    bottom_right: [380.0, 280.0]
  
  transformation_matrices:
    pixel_to_mm: 
      - [1.0857, 0.0, -157.1429]
      - [0.0, 1.0857, -103.1429]
      - [0.0, 0.0, 1.0]
    mm_to_pixel:
      - [0.9211, 0.0, 144.7368]
      - [0.0, 0.9211, 95.0]
      - [0.0, 0.0, 1.0]
  
  calibration_metrics:
    average_reprojection_error: 0.0
    calibration_timestamp: "2025-07-22T21:46:54"
    cage_dimensions: [380.0, 280.0]
```

## API リファレンス

### クラス初期化
```python
from phase3_hamster_tracking.hamster_tracking.coordinate_calibrator import CoordinateCalibrator
from phase3_hamster_tracking.utils.hamster_config import load_config

config = load_config()
calibrator = CoordinateCalibrator(config)
```

### 校正実行
```python
# 4点校正実行
pixel_corners = {
    'top_left': (145, 95),
    'top_right': (495, 95),
    'bottom_left': (145, 375), 
    'bottom_right': (495, 375)
}

success = calibrator.calibrate(pixel_corners)
if success:
    print("校正完了")
    calibrator.save_calibration()
```

### 座標変換
```python
# 各種変換実行
mm_coord = calibrator.pixel_to_mm((320, 240))
pixel_coord = calibrator.mm_to_pixel((190, 140))

# 距離・面積計算
distance_mm = calibrator.calculate_distance_mm((x1, y1), (x2, y2))
area_mm2 = calibrator.calculate_area_mm2(contour_points)
```

### 校正状態確認
```python
# 校正状態とメトリクス確認
is_calibrated = calibrator.is_calibrated
error_info = calibrator.get_calibration_metrics()

print(f"校正済み: {is_calibrated}")
print(f"平均誤差: {error_info['average_error']:.3f}mm")
```

## GUI校正ツール連携

### 対話的校正プロセス
```python
# 校正GUIツールとの連携
def interactive_calibration():
    """対話的校正プロセス"""
    from phase3_hamster_tracking.gui.calibration_gui import CalibrationGUI
    
    # GUIツール起動
    gui = CalibrationGUI(calibrator)
    gui.run()
    
    # 校正結果の自動保存
    if gui.calibration_completed:
        calibrator.save_calibration()
        print("校正データを保存しました")
```

### 校正点可視化
```python
def visualize_calibration_points(self, frame):
    """校正点と変換結果を可視化"""
    vis_frame = frame.copy()
    
    # 校正点描画
    for point_name, pixel_coord in self.pixel_corners.items():
        cv2.circle(vis_frame, tuple(map(int, pixel_coord)), 5, (0, 255, 0), -1)
        cv2.putText(vis_frame, point_name, pixel_coord, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    # 校正領域の枠線描画
    corners = np.array(list(self.pixel_corners.values()), dtype=np.int32)
    cv2.polylines(vis_frame, [corners], True, (255, 0, 0), 2)
    
    return vis_frame
```

## エラー処理・トラブルシューティング

### よくある問題と対処法

#### 校正精度の低下
```python
# 問題: 再投影誤差が大きい（> 2.0pixel）
# 原因: 校正点の指定精度不足
# 対処: より正確な角点指定、画像解像度確認

if average_error > 2.0:
    logger.warning(f"校正精度が低下しています: {average_error:.2f}pixel")
    # 再校正推奨
```

#### 変換結果の異常
```python
# 問題: 負の座標や範囲外座標
# 原因: 射影変換行列の特異性
# 対処: 校正点の再設定、4点の適切な配置

def validate_transformation_result(self, result):
    if result[0] < -50 or result[0] > 450 or result[1] < -50 or result[1] > 350:
        raise ValueError("変換結果が期待範囲外です - 再校正が必要")
```

#### 校正データの破損
```python
# 問題: YAML読み込みエラー
# 原因: ファイル破損、形式不正
# 対処: バックアップからの復旧、再校正実行

try:
    self.load_calibration()
except (FileNotFoundError, yaml.YAMLError):
    logger.error("校正データ読み込み失敗 - 再校正が必要")
    self.is_calibrated = False
```

## パフォーマンス・最適化

### 計算効率
```python
# 最適化1: 行列演算のベクトル化
def batch_pixel_to_mm(self, pixel_coords_array):
    """複数点の一括変換（効率向上）"""
    coords_homogeneous = np.column_stack([pixel_coords_array, np.ones(len(pixel_coords_array))])
    mm_homogeneous = (self.pixel_to_mm_matrix @ coords_homogeneous.T).T
    mm_coords = mm_homogeneous[:, :2] / mm_homogeneous[:, 2:]
    return mm_coords
```

### メモリ使用量
- **校正データ**: < 1KB（変換行列とメタデータ）
- **実行時メモリ**: < 10MB（numpy配列）
- **処理速度**: ~0.1ms/点（単一座標変換）

## 精度仕様

### 校正精度目標
- **再投影誤差**: < 1.0pixel（理想）、< 2.0pixel（許容）
- **物理距離精度**: ±1mm（380mm距離で±0.26%）
- **面積計算精度**: ±2%（通常範囲での動物検出）

### 環境影響要因
- **カメラ設置角度**: 垂直から±5度以内推奨
- **レンズ歪み**: 魚眼効果による端部精度低下
- **照明条件**: 校正点認識に影響

## 今後の改良予定
- [ ] 自動角点検出による校正簡素化
- [ ] レンズ歪み補正の組み込み
- [ ] 複数解像度対応（メイン/サブストリーム）
- [ ] 校正精度の機械学習ベース改善

---

*CoordinateCalibrator v1.0*  
*最終更新: 2025-07-22*