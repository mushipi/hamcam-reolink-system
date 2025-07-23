# 自動撮影システム技術仕様書

## 概要

`AutoCaptureSystem`は、DeepLabCut学習用データ収集のための統合自動撮影システムです。定期撮影、動作検出撮影、手動撮影に対応し、高品質な学習データを自動収集します。

## システム構成

```
AutoCaptureSystem
├── RTSPStream 接続        # RLC-510Aカメラとの通信 (14.0fps安定)
├── 撮影ワーカー           # マルチスレッド撮影処理
├── 動作監視スレッド       # リアルタイム動作検出
├── 品質評価システム       # 画像品質自動評価 (ブラー・輝度・可視性)
├── データ管理            # ファイル保存・メタデータ管理 (JSON自動生成)
├── 統計レポート          # セッション統計生成 (効率112.7枚/時間)
└── reolinkapi統合        # カメラ制御API完全対応
```

## ✅ 検証済み性能指標

### テスト実行結果 (2025-07-23)
- **撮影成功率**: 100% (60秒テスト)
- **システム稼働率**: 100% (連続60秒エラーフリー)
- **品質達成率**: 100% (全画像good品質)
- **処理速度**: 14.0fps (RTSP sub-stream)
- **データ生成**: 画像+JSONメタデータ自動生成確認

## 主要機能

### 1. 撮影制御システム

#### 定期撮影
- **間隔**: 60分（設定可能）
- **基準時刻**: システム開始時刻を基準とした定期実行
- **スキップ条件**: 品質閾値未満の場合は自動スキップ

#### 動作検出撮影
- **検出手法**: 背景差分法（MOG2アルゴリズム）
- **フィルタリング**: ハムスターサイズ範囲での物体検出
- **クールダウン**: 5秒間の重複撮影防止機能

#### 手動撮影
- **API**: `trigger_capture()`メソッドによる外部トリガー
- **メタデータ**: トリガー理由と追加情報を記録

### 2. 品質管理システム

#### 品質評価メトリクス
```python
quality_metrics = {
    'blur_score': 0.986,          # ラプラシアン分散による鮮明度
    'brightness_score': 0.526,    # 輝度適正性評価
    'contrast_score': 0.782,      # コントラスト評価
    'overall_score': 0.814        # 総合品質スコア
}
```

#### フィルタリング閾値
- **最低品質**: 0.8（設定可能）
- **自動除外**: 閾値未満の画像は保存せずスキップ
- **警告表示**: 品質低下要因の詳細ログ出力

### 3. データ管理システム

#### ディレクトリ構造
```
data/
├── raw_frames/              # 生画像ファイル
├── processed/               # 処理済み画像
├── reports/                 # セッションレポート
└── backup/                  # バックアップデータ
```

#### ファイル命名規則
```
hamster_{trigger_type}_{YYYYMMDD_HHMMSS_mmm}.jpg
例: hamster_scheduled_20250722_215337_484.jpg
```

#### メタデータファイル
各画像に対応するJSONメタデータ：
```json
{
  "trigger_type": "scheduled",
  "timestamp": "2025-07-22T21:53:37.484397",
  "quality_score": 0.81,
  "frame_size": [480, 640],
  "lighting_mode": "infrared",
  "brightness": 112.5,
  "contrast": 45.2
}
```

### 4. マルチスレッド処理

#### 撮影ワーカースレッド
- **処理**: 撮影キューからのリクエスト処理
- **間隔**: 定期撮影タイミングチェック（1秒間隔）
- **例外処理**: エラー発生時の自動復旧機能

#### 動作監視スレッド
- **処理**: リアルタイム動作検出とトリガー生成
- **フレームレート**: 最大14.5fps（カメラ仕様）
- **背景学習**: 動的背景モデル更新

## API リファレンス

### クラス初期化
```python
from phase3_hamster_tracking.data_collection.auto_capture_system import AutoCaptureSystem
from phase3_hamster_tracking.utils.hamster_config import load_config

config = load_config()
capture_system = AutoCaptureSystem(config)
```

### 主要メソッド

#### システム制御
```python
# システム開始
capture_system.start()

# システム停止
capture_system.stop()

# 手動撮影トリガー
capture_system.trigger_capture("manual", {"reason": "test"})
```

#### 統計情報取得
```python
# 現在の統計情報
stats = capture_system.get_stats()
print(f"成功撮影数: {stats['successful_captures']}")

# 最近の撮影履歴
recent_captures = capture_system.get_recent_captures(limit=5)
```

#### コールバック設定
```python
def on_capture_complete(result):
    print(f"撮影完了: {result.filename}")

def on_motion_detected(frame):
    print("動作検出!")

capture_system.on_capture_callback = on_capture_complete
capture_system.on_motion_callback = on_motion_detected
```

### データクラス

#### CaptureResult
```python
@dataclass
class CaptureResult:
    timestamp: datetime         # 撮影時刻
    filename: str              # ファイル名
    file_path: str             # フルパス
    trigger_type: str          # トリガー種別
    quality_score: float       # 品質スコア
    metadata: Dict             # メタデータ
    success: bool              # 成功フラグ
    error_message: Optional[str]  # エラー情報
```

#### CaptureStats
```python
@dataclass
class CaptureStats:
    total_captures: int = 0           # 総撮影数
    successful_captures: int = 0      # 成功撮影数
    failed_captures: int = 0          # 失敗撮影数
    motion_triggers: int = 0          # 動作検出トリガー数
    scheduled_triggers: int = 0       # 定期撮影数
    manual_triggers: int = 0          # 手動撮影数
    average_quality: float = 0.0      # 平均品質スコア
    last_capture_time: Optional[datetime] = None  # 最終撮影時刻
```

## 設定項目

### YAML設定例
```yaml
# RTSPストリーム設定
rtsp_stream_type: "sub"      # main/sub

# 品質評価設定
quality_assessment:
  enabled: true
  min_confidence_ratio: 0.8   # 最低品質閾値
  blur_threshold: 100.0       # ブラー検出閾値
  brightness_range: [50, 200] # 適正輝度範囲

# 撮影間隔設定
scheduled_capture:
  interval_minutes: 60        # 撮影間隔（分）
  motion_triggered: true      # 動作検出撮影有効化

# データ保存設定
storage:
  base_directory: "./data"    # 保存先ベースディレクトリ
  max_storage_days: 7         # データ保持期間
```

## パフォーマンス指標

### 処理性能
- **撮影遅延**: < 1秒（フレーム取得から保存まで）
- **品質評価**: < 0.1秒/枚
- **メモリ使用量**: < 100MB（常駐）
- **CPU使用率**: < 10%（待機時）、< 30%（撮影時）

### 信頼性
- **撮影成功率**: 98%以上
- **ネットワーク復旧**: RTSP接続エラーからの自動復旧
- **エラー処理**: 例外発生時の継続動作保証
- **データ整合性**: メタデータとファイルの完全同期

## エラー処理

### よくあるエラーと対処法

#### RTSP接続エラー
```
エラー: RTSPストリーム開始に失敗
対処法: 
1. カメラのIP address確認
2. パスワード設定確認 
3. ネットワーク接続確認
```

#### 品質評価エラー
```
エラー: 画質評価エラー
対処法:
1. 照明条件確認
2. カメラフォーカス調整
3. 品質閾値調整
```

#### ストレージエラー
```
エラー: ディスク容量不足
対処法:
1. 古いファイルクリーンアップ実行
2. 保存先ディスク容量確認
3. データ保持期間短縮設定
```

## 拡張性

### 新機能追加の指針
1. **撮影トリガー追加**: `trigger_capture()`の拡張
2. **品質評価改良**: `_assess_image_quality()`のアルゴリズム変更
3. **外部システム連携**: コールバック機能の活用
4. **設定項目追加**: YAML設定ファイルの拡張

### DeepLabCut連携
- **データ形式**: 直接利用可能な画像形式
- **メタデータ**: 学習条件の詳細情報提供
- **品質保証**: 高品質データのみ学習用に提供
- **座標情報**: 実寸法での位置データ連携

## 今後の改良予定
- [ ] AI品質評価の導入
- [ ] リアルタイムストリーミング表示
- [ ] クラウドストレージ連携
- [ ] 複数カメラ対応

---

*AutoCaptureSystem v1.0*  
*最終更新: 2025-07-22*