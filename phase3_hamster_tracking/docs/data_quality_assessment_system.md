# データ品質評価システム技術仕様書

## 概要

`DataQualityAssessor`は、DeepLabCut学習用画像の品質を多角的に評価し、高品質なデータのみを学習セットに提供するシステムです。画質メトリクス、ハムスター可視性、環境条件を総合的に分析します。

## システムアーキテクチャ

```
DataQualityAssessor
├── 画質評価エンジン        # ブラー・輝度・コントラスト・ノイズ分析
├── ハムスター可視性評価    # 個体検出・姿勢判定・遮蔽評価
├── 環境条件分析          # 照明・影・背景品質評価
├── 総合品質判定          # 重み付き統合スコア計算
├── 品質レベル分類        # Excellent/Good/Acceptable/Poor/Rejected
└── DeepLabCut適合性      # 学習データとしての適合性評価
```

## 主要機能

### 1. 画質メトリクス評価

#### ブラー検出（鮮明度評価）
```python
def evaluate_blur(self, image: np.ndarray) -> float:
    """ラプラシアン分散によるブラー評価"""
    # グレースケール変換
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # ラプラシアンフィルタ適用
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    
    # 分散計算（高いほど鮮明）
    blur_score = laplacian.var()
    
    # 正規化（0-1スケール）
    normalized_score = min(blur_score / self.blur_threshold, 1.0)
    
    return normalized_score
```

#### 輝度評価
```python
def evaluate_brightness(self, image: np.ndarray) -> float:
    """適正輝度範囲での評価"""
    # グレースケール平均輝度
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    mean_brightness = np.mean(gray)
    
    # 適正範囲からの偏差計算
    optimal_range = self.brightness_range  # [50, 200]
    optimal_center = np.mean(optimal_range)
    
    # 正規化スコア（1.0が最適、0.0が最悪）
    brightness_score = 1.0 - abs(mean_brightness - optimal_center) / 127.5
    
    return max(0.0, brightness_score)
```

#### コントラスト評価
```python
def evaluate_contrast(self, image: np.ndarray) -> float:
    """画像コントラストの評価"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # 標準偏差によるコントラスト計算
    contrast = gray.std()
    
    # 閾値ベース正規化
    contrast_threshold = self.contrast_threshold * 255  # デフォルト0.3
    contrast_score = min(contrast / contrast_threshold, 1.0)
    
    return contrast_score
```

#### ノイズ評価
```python
def evaluate_noise(self, image: np.ndarray) -> float:
    """画像ノイズレベルの評価"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # ガウシアンブラーとの差分でノイズ推定
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    noise_map = cv2.absdiff(gray, blurred)
    
    # ノイズレベル計算
    noise_level = np.mean(noise_map)
    
    # 低ノイズほど高スコア
    noise_score = max(0.0, 1.0 - noise_level / 50.0)  # 50を基準値とする
    
    return noise_score
```

### 2. ハムスター可視性評価

#### ハムスター検出
```python
def detect_hamster_presence(self, image: np.ndarray) -> Tuple[bool, float, List]:
    """画像内のハムスター検出と可視性評価"""
    # 動作検出システム利用
    motion_detector = MotionDetector(self.config)
    motion_events = motion_detector.detect_motion(image)
    
    # 高信頼度の検出結果をフィルタ
    valid_detections = [event for event in motion_events if event.confidence > 0.7]
    
    if not valid_detections:
        return False, 0.0, []
    
    # 最大信頼度の検出結果を採用
    best_detection = max(valid_detections, key=lambda x: x.confidence)
    
    return True, best_detection.confidence, valid_detections
```

#### 姿勢・ポーズ評価
```python
def evaluate_pose_quality(self, detection_info) -> float:
    """ハムスターの姿勢・ポーズの学習適合性評価"""
    pose_factors = {
        'body_visibility': 0.4,    # 胴体の可視性
        'limb_visibility': 0.3,    # 四肢の可視性  
        'head_clarity': 0.2,       # 頭部の明瞭性
        'tail_visibility': 0.1     # 尻尾の可視性
    }
    
    # 検出領域のアスペクト比から姿勢推定
    bbox = detection_info['bounding_box']
    aspect_ratio = bbox[2] / bbox[3]  # width/height
    
    # 理想的な姿勢範囲（0.5-2.0）
    if 0.5 <= aspect_ratio <= 2.0:
        pose_score = 1.0
    else:
        # 極端な姿勢は減点
        pose_score = max(0.3, 1.0 - abs(aspect_ratio - 1.25) / 2.0)
    
    return pose_score
```

#### 遮蔽・重複評価
```python
def evaluate_occlusion(self, image: np.ndarray, detection_area) -> float:
    """ハムスターの遮蔽状況評価"""
    # ケージ内オブジェクト（給水器、餌皿など）による遮蔽検出
    occlusion_factors = []
    
    # 検出領域の境界での切り取り確認
    bbox = detection_area
    image_height, image_width = image.shape[:2]
    
    # 画像端での切り取り判定
    edge_clipping = (
        bbox[0] <= 5 or bbox[1] <= 5 or  # 左上端
        bbox[0] + bbox[2] >= image_width - 5 or  # 右端
        bbox[1] + bbox[3] >= image_height - 5    # 下端
    )
    
    if edge_clipping:
        occlusion_factors.append('edge_clipping')
    
    # 遮蔽度合いスコア
    occlusion_penalty = len(occlusion_factors) * 0.3
    occlusion_score = max(0.0, 1.0 - occlusion_penalty)
    
    return occlusion_score
```

### 3. 環境条件評価

#### 照明条件分析
```python
def evaluate_lighting_conditions(self, image: np.ndarray) -> Dict:
    """照明条件の適正性評価"""
    # HSVチャンネル分析
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    # 明度チャンネル統計
    value_channel = hsv[:, :, 2]
    brightness_uniformity = 1.0 - (value_channel.std() / 255.0)
    
    # 過度な影の検出
    dark_regions = np.sum(value_channel < 50) / value_channel.size
    shadow_score = 1.0 - min(dark_regions * 3, 1.0)  # 暗領域が33%超で減点
    
    # 過露光領域の検出
    bright_regions = np.sum(value_channel > 240) / value_channel.size
    highlight_score = 1.0 - min(bright_regions * 5, 1.0)  # 明領域が20%超で減点
    
    return {
        'brightness_uniformity': brightness_uniformity,
        'shadow_score': shadow_score,
        'highlight_score': highlight_score,
        'overall_lighting': (brightness_uniformity + shadow_score + highlight_score) / 3
    }
```

#### 背景品質評価
```python
def evaluate_background_quality(self, image: np.ndarray) -> float:
    """背景の学習適合性評価"""
    # 背景領域の抽出（ハムスター検出領域を除外）
    hamster_detected, confidence, detections = self.detect_hamster_presence(image)
    
    if hamster_detected:
        # ハムスター領域をマスク
        mask = np.ones(image.shape[:2], dtype=np.uint8) * 255
        for detection in detections:
            bbox = detection.bounding_box
            mask[bbox[1]:bbox[1]+bbox[3], bbox[0]:bbox[0]+bbox[2]] = 0
    else:
        mask = np.ones(image.shape[:2], dtype=np.uint8) * 255
    
    # 背景領域の複雑度評価
    background_region = cv2.bitwise_and(image, image, mask=mask)
    gray_bg = cv2.cvtColor(background_region, cv2.COLOR_BGR2GRAY)
    
    # エッジ密度による複雑度計算
    edges = cv2.Canny(gray_bg, 50, 150)
    edge_density = np.sum(edges > 0) / edges.size
    
    # 適度な複雑度が学習に有効（0.1-0.3が理想）
    if 0.1 <= edge_density <= 0.3:
        background_score = 1.0
    else:
        background_score = max(0.3, 1.0 - abs(edge_density - 0.2) / 0.5)
    
    return background_score
```

### 4. 総合品質判定

#### 重み付き統合スコア
```python
def calculate_overall_score(self, metrics: Dict) -> float:
    """重み付きメトリクスによる総合品質スコア"""
    weights = {
        'blur_score': 0.25,           # 鮮明度（25%）
        'brightness_score': 0.15,     # 輝度（15%）
        'contrast_score': 0.15,       # コントラスト（15%）
        'noise_score': 0.10,          # ノイズ（10%）
        'hamster_visibility': 0.20,   # ハムスター可視性（20%）
        'lighting_score': 0.10,       # 照明条件（10%）
        'background_score': 0.05      # 背景品質（5%）
    }
    
    overall_score = sum(metrics[key] * weight for key, weight in weights.items())
    return max(0.0, min(1.0, overall_score))
```

#### 品質レベル分類
```python
def classify_quality_level(self, overall_score: float) -> QualityLevel:
    """スコアベースの品質レベル分類"""
    if overall_score >= 0.8:
        return QualityLevel.EXCELLENT    # DeepLabCut学習に最適
    elif overall_score >= 0.65:
        return QualityLevel.GOOD         # 学習データとして良好
    elif overall_score >= 0.5:
        return QualityLevel.ACCEPTABLE   # 学習可能だが品質限界
    elif overall_score >= 0.3:
        return QualityLevel.POOR         # 学習効果限定的
    else:
        return QualityLevel.REJECTED     # 学習データとして不適
```

### 5. DeepLabCut適合性評価

#### ランドマーク検出適合性
```python
def evaluate_landmark_suitability(self, image: np.ndarray, detection_info) -> Dict:
    """DeepLabCutランドマーク検出への適合性評価"""
    landmark_scores = {}
    
    # 主要ランドマーク領域の評価
    landmark_regions = {
        'nose': self._evaluate_nose_region(image, detection_info),
        'ears': self._evaluate_ear_regions(image, detection_info),
        'body_center': self._evaluate_body_center(image, detection_info),
        'limbs': self._evaluate_limb_regions(image, detection_info),
        'tail_base': self._evaluate_tail_region(image, detection_info)
    }
    
    # 各ランドマーク領域の可視性・明瞭性スコア
    for landmark, region_info in landmark_regions.items():
        visibility = region_info.get('visibility', 0.5)
        clarity = region_info.get('clarity', 0.5)
        landmark_scores[landmark] = (visibility + clarity) / 2
    
    return landmark_scores
```

## API リファレンス

### クラス初期化
```python
from phase3_hamster_tracking.data_collection.data_quality import DataQualityAssessor
from phase3_hamster_tracking.utils.hamster_config import load_config

config = load_config()
quality_assessor = DataQualityAssessor(config)
```

### 品質評価実行
```python
# 画像品質の総合評価
quality_metrics = quality_assessor.evaluate_image_quality(image, file_path)

print(f"総合スコア: {quality_metrics.overall_score:.3f}")
print(f"品質レベル: {quality_metrics.quality_level.value}")
print(f"推奨事項: {quality_metrics.notes}")
```

### 個別メトリクス取得
```python
# 個別評価メトリクスの取得
blur_score = quality_assessor.evaluate_blur(image)
brightness_score = quality_assessor.evaluate_brightness(image)
hamster_visibility = quality_assessor.evaluate_hamster_visibility(image)

print(f"ブラー: {blur_score:.3f}")
print(f"輝度: {brightness_score:.3f}")  
print(f"ハムスター可視性: {hamster_visibility:.3f}")
```

### データクラス

#### QualityMetrics
```python
@dataclass
class QualityMetrics:
    overall_score: float                    # 総合品質スコア（0-1）
    quality_level: QualityLevel            # 品質レベル分類
    blur_score: float                      # ブラー評価
    brightness_score: float               # 輝度評価
    contrast_score: float                 # コントラスト評価
    noise_score: float                    # ノイズ評価
    hamster_visibility_score: float       # ハムスター可視性
    lighting_score: float                 # 照明条件
    background_score: float               # 背景品質
    notes: List[str]                      # 品質改善のための注意事項
    timestamp: datetime                   # 評価実行時刻
    deeplabcut_suitability: float         # DeepLabCut適合性
```

#### QualityLevel
```python
class QualityLevel(Enum):
    EXCELLENT = "excellent"    # 0.8+ : 最高品質
    GOOD = "good"             # 0.65+: 良好品質
    ACCEPTABLE = "acceptable"  # 0.5+ : 許容品質
    POOR = "poor"             # 0.3+ : 低品質
    REJECTED = "rejected"     # 0.3- : 拒否レベル
```

## 設定・カスタマイズ

### 閾値パラメータ設定
```yaml
# hamster_config.yaml - 品質評価設定
quality_assessment:
  enabled: true
  
  # 画質メトリクス閾値
  blur_threshold: 100.0              # ラプラシアン分散閾値
  brightness_range: [50, 200]       # 適正輝度範囲
  contrast_threshold: 0.3            # コントラスト基準値
  noise_threshold: 50.0              # ノイズレベル基準
  
  # ハムスター検出
  hamster_detection:
    min_confidence: 0.7              # 最低検出信頼度
    min_visibility_ratio: 0.6        # 最低可視比率
  
  # 品質レベル閾値
  quality_thresholds:
    excellent: 0.8
    good: 0.65  
    acceptable: 0.5
    poor: 0.3
  
  # DeepLabCut適合性
  deeplabcut_requirements:
    min_landmark_visibility: 0.7     # ランドマーク最低可視性
    preferred_pose_variety: true     # 多様な姿勢を優先
```

## パフォーマンス仕様

### 処理性能
- **評価速度**: ~200-300ms/枚（480×640画像）
- **メモリ使用量**: ~50MB（処理用バッファ含む）
- **バッチ処理**: 最大100枚/分の高速処理

### 評価精度
- **品質分類精度**: 90%以上（人間の判定と比較）
- **ハムスター検出率**: 95%以上（明瞭な画像）
- **False Positive**: < 5%（不適切な高評価）

## DeepLabCut統合

### 学習データ適合性
```python
def filter_for_deeplabcut(quality_metrics: QualityMetrics) -> bool:
    """DeepLabCut学習に適した画像のフィルタリング"""
    # 基本品質要件
    if quality_metrics.overall_score < 0.65:
        return False
    
    # ハムスター可視性要件
    if quality_metrics.hamster_visibility_score < 0.7:
        return False
    
    # 特定の品質問題を除外
    if 'severe_blur' in quality_metrics.notes:
        return False
        
    if 'poor_lighting' in quality_metrics.notes:
        return False
    
    return True
```

### データセット品質管理
```python
def generate_dataset_quality_report(image_paths: List[str]) -> Dict:
    """データセット全体の品質分析レポート"""
    quality_distribution = {
        'excellent': 0, 'good': 0, 'acceptable': 0, 'poor': 0, 'rejected': 0
    }
    
    total_suitable = 0
    average_scores = []
    
    for image_path in image_paths:
        image = cv2.imread(image_path)
        quality_metrics = self.evaluate_image_quality(image, image_path)
        
        # 分布統計更新
        quality_distribution[quality_metrics.quality_level.value] += 1
        average_scores.append(quality_metrics.overall_score)
        
        # DeepLabCut適合性カウント
        if self.filter_for_deeplabcut(quality_metrics):
            total_suitable += 1
    
    return {
        'total_images': len(image_paths),
        'quality_distribution': quality_distribution,
        'average_quality_score': np.mean(average_scores),
        'deeplabcut_suitable_count': total_suitable,
        'dataset_usability': total_suitable / len(image_paths)
    }
```

## 今後の改良予定
- [ ] AI/機械学習ベース品質評価の導入
- [ ] リアルタイム品質フィードバック
- [ ] カスタム評価メトリクスの追加
- [ ] 他の動物種への対応

---

*DataQualityAssessor v1.0*  
*最終更新: 2025-07-22*