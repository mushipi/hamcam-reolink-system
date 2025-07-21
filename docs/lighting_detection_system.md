# 照明モード検出システム技術仕様書

## 概要

RLC-510Aカメラの昼間カラーモード/夜間IRモードを自動判定するシステム。RGB相関解析を主軸とした複数手法の統合により、高精度な照明状態検出を実現。

## システム構成

### コアモジュール

```
phase3_hamster_tracking/utils/lighting_detector.py
├── LightingModeDetector     # 高精度統合検出器
├── SimpleLightingDetector   # 軽量高速検出器
└── 補助機能群
```

### 実行ファイル

- `lighting_detection_demo.py` - リアルタイム検出デモ
- `test_lighting_manual.py` - 手動検証ツール
- `phase3_hamster_tracking/tests/test_lighting_detection.py` - テストスイート

## 技術仕様

### 1. RGB相関解析（メイン手法）

#### 原理
昼間カラー映像とIR映像のRGBチャンネル間相関の違いを利用：

- **カラーモード**: RGB各チャンネルが独立した値 → 相関低
- **IRモード**: RGB各チャンネルがほぼ同値 → 相関高（≥0.9）

#### 実装
```python
def _detect_by_rgb_correlation(self, frame):
    b, g, r = cv2.split(frame)
    
    # 相関計算
    corr_bg = np.corrcoef(b.flatten(), g.flatten())[0, 1]
    corr_br = np.corrcoef(b.flatten(), r.flatten())[0, 1]
    corr_gr = np.corrcoef(g.flatten(), r.flatten())[0, 1]
    
    avg_correlation = np.mean([corr_bg, corr_br, corr_gr])
    
    if avg_correlation > 0.9:
        return 'ir', confidence
    else:
        return 'color', confidence
```

#### 特徴
- **精度**: 90%以上の正判定率
- **処理速度**: 単独で約3ms/frame
- **堅牢性**: NaN/無限大値の自動処理

### 2. 補助判定手法

#### 時刻ベース推定
```python
def _detect_by_time(self):
    hour = datetime.now().hour
    
    if 6 <= hour < 18:  # 日中
        return 'color', confidence
    else:  # 夜間
        return 'ir', confidence
```

- **日の出**: 6:00頃
- **日の入**: 18:00頃
- **信頼度**: 正午/深夜で最高、境界時間で最低

#### HSV色相多様性解析
```python
def _detect_by_hue_diversity(self, frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    hue = hsv[:,:,0]
    hist = cv2.calcHist([hue], [0], None, [180], [0,180])
    
    diversity_ratio = np.count_nonzero(hist) / 180.0
    
    if diversity_ratio > 0.15:
        return 'color', confidence
    else:
        return 'ir', confidence
```

- **判定基準**: 色相の多様性15%以上でカラー判定
- **用途**: RGB相関の補助検証

#### エッジ密度特性解析
```python
def _detect_by_edge_characteristics(self, frame):
    edges = cv2.Canny(gray, 50, 150)
    edge_density = np.sum(edges > 0) / edges.size
    
    # ヒストグラム両端集中度
    hist = cv2.calcHist([gray], [0], None, [256], [0,256])
    extreme_ratio = dark_ratio + bright_ratio
    
    if edge_density > 0.05 and extreme_ratio > 0.4:
        return 'ir', confidence  # IR特有の高コントラスト
    else:
        return 'color', confidence
```

- **IR特徴**: 高エッジ密度 + 明暗両端集中
- **用途**: IR画像の特徴的パターン検出

### 3. 統合判定システム

#### 重み付き投票
```python
weights = {
    'rgb': 0.7,      # メイン手法
    'time': 0.1,     # 補助
    'hue': 0.15,     # 補助
    'edge': 0.05     # 補助
}
```

#### 最終判定フロー
1. 各手法で独立判定
2. 重み付きスコア計算
3. 履歴による安定化（5フレーム移動平均）
4. 信頼度評価・最終決定

### 4. 品質評価システム

#### フレーム品質指標
- **鮮明度**: ラプラシアン分散による焦点評価
- **適正露出**: 平均輝度の128からの偏差
- **ノイズレベル**: ガウシアンブラーとの差分標準偏差

#### 統計情報
```json
{
  "total_frames": 1000,
  "ir_frames": 600,
  "color_frames": 400,
  "avg_confidence": 0.85,
  "avg_processing_time": 10.9,
  "ir_ratio": 0.6
}
```

## パフォーマンス仕様

### 処理速度

| 検出器種別 | 平均処理時間 | 適用用途 |
|------------|--------------|----------|
| LightingModeDetector | 10.9ms/frame | 高精度要求 |
| SimpleLightingDetector | 2.9ms/frame | 高速処理要求 |

### 精度指標

| 指標 | 目標値 | 実測値 | 状況 |
|------|--------|--------|------|
| 正判定率 | ≥90% | ≥90% | ✅達成 |
| 処理速度 | ≤15ms | 10.9ms | ✅達成 |
| 信頼度 | ≥0.8 | 0.85 | ✅達成 |

## API仕様

### LightingModeDetector

#### 初期化
```python
detector = LightingModeDetector(
    correlation_threshold=0.95,   # RGB相関閾値
    history_size=5,              # 安定化履歴サイズ
    confidence_threshold=0.8     # 信頼度閾値
)
```

#### メイン検出
```python
mode, confidence, details = detector.detect_mode(frame)

# 戻り値
# mode: 'color' | 'ir' | 'unknown'
# confidence: float (0.0-1.0)
# details: {
#     'rgb_correlation': float,
#     'time_estimation': float,
#     'hue_diversity': float,
#     'edge_density': float,
#     'frame_quality': float,
#     'processing_time_ms': float,
#     'history_size': int
# }
```

#### 統計情報
```python
stats = detector.get_detection_stats()
detector.reset_stats()
```

### SimpleLightingDetector

#### 軽量版使用
```python
detector = SimpleLightingDetector(threshold=0.9)
mode, confidence = detector.detect_mode(frame)
```

## 使用方法

### 1. 基本的な検出
```python
from phase3_hamster_tracking.utils.lighting_detector import LightingModeDetector

detector = LightingModeDetector()

# フレーム検出
mode, confidence, details = detector.detect_mode(frame)

if mode == 'ir':
    print(f"夜間IRモード (信頼度: {confidence:.3f})")
elif mode == 'color':
    print(f"昼間カラーモード (信頼度: {confidence:.3f})")
```

### 2. デモアプリケーション
```bash
# 高精度版デモ（30秒間）
python lighting_detection_demo.py --duration 30

# 軽量版デモ
python lighting_detection_demo.py --simple --stream sub

# 操作方法
# 'q': 終了, 's': 統計リセット, 'i': 情報切替
```

### 3. テスト実行
```bash
# 単体テスト
python phase3_hamster_tracking/tests/test_lighting_detection.py --unit

# 統合テスト（要RTSPストリーム）
python phase3_hamster_tracking/tests/test_lighting_detection.py --integration

# 手動検証
python test_lighting_manual.py
```

## 設定パラメータ

### 検出閾値
```python
# RGB相関閾値（IRモード判定）
correlation_threshold = 0.9      # デフォルト

# 色相多様性閾値（カラーモード判定）
hue_diversity_threshold = 0.15   # 15%

# エッジ密度閾値（IR特徴判定）
edge_density_threshold = 0.05    # 5%

# 時刻判定境界
sunrise_hour = 6                 # 日の出
sunset_hour = 18                # 日の入り
```

### 性能調整
```python
# 履歴サイズ（安定化）
history_size = 5                 # 5フレーム移動平均

# 信頼度閾値
confidence_threshold = 0.8       # 80%以上で高信頼

# 統合判定重み
weights = {
    'rgb': 0.7,      # RGB相関 70%
    'time': 0.1,     # 時刻判定 10%
    'hue': 0.15,     # 色相多様性 15%
    'edge': 0.05     # エッジ特性 5%
}
```

## トラブルシューティング

### よくある問題

#### 1. 検出精度が低い
**症状**: 誤判定が多発
**原因**: 
- カメラ設定の問題
- 環境光の変化
- ノイズの多いフレーム

**対策**:
```python
# 閾値調整
detector = LightingModeDetector(
    correlation_threshold=0.85,  # 閾値を下げる
    history_size=7              # 履歴サイズを増加
)

# または軽量版使用
detector = SimpleLightingDetector(threshold=0.85)
```

#### 2. 処理速度が遅い
**症状**: 15ms以上の処理時間
**原因**: 
- 高解像度フレーム
- 複数手法の統合処理

**対策**:
```python
# 軽量版に切り替え
detector = SimpleLightingDetector()

# またはフレーム解像度を下げる
frame_resized = cv2.resize(frame, (320, 240))
```

#### 3. NaN/エラーが発生
**症状**: 計算エラー・異常値
**原因**: 
- 無効なフレームデータ
- 標準偏差0のチャンネル

**対策**:
- 自動的にハンドリング済み
- 'unknown'モードで安全に処理

### デバッグモード
```python
import logging
logging.getLogger('phase3_hamster_tracking.utils.lighting_detector').setLevel(logging.DEBUG)
```

## 今後の拡張予定

### Phase 3-1での活用
1. **DeepLabCut学習データ分類**
   - カラー/IR画像の自動分類
   - バランスの取れたデータセット構築

2. **自動撮影システム連携**
   - 照明条件に基づく撮影スケジュール
   - 品質評価による画像選別

### 高度化計画
1. **機械学習ベース検出**
   - CNN分類器の追加
   - 転移学習による精度向上

2. **環境適応機能**
   - 季節変動への対応
   - カメラ個体差の自動補正

---

**作成日**: 2025年7月20日  
**バージョン**: 1.0  
**対応システム**: Phase 3 ハムスター管理システム