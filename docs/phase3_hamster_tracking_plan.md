# ハムスター管理システム Phase 3 完全実装計画

## プロジェクト概要
- **目的**: 380×280mmケージ内ハムスターの24時間活動量測定
- **技術**: DeepLabCut + Phase2 RTSPシステム
- **対象**: 昼間カラー映像 + 夜間IR白黒映像
- **期間**: 3週間 + 準備期間

---

## Phase 3-0: 学習データ収集準備 (3-4日)

### Day 1: 自動撮影システム構築

#### タスク 1-1: 照明モード検出機能
```python
# 実装ファイル: utils/lighting_detector.py
class LightingModeDetector:
    def detect_mode(self, frame):
        """カラー/IR自動判定"""
        # RGB チャンネル分散計算
        # グレースケール変換
        # ヒストグラム分析
        return "color" | "ir"
    
    def get_lighting_quality(self, frame):
        """照明品質評価"""
        # コントラスト計算
        # 鮮明度評価
        # ノイズレベル測定
        return quality_score (0.0-1.0)
```

#### タスク 1-2: スケジュール撮影システム
```python
# 実装ファイル: data_collection/auto_capture.py
class ScheduledDataCollector:
    def __init__(self):
        self.schedule = {
            "regular_interval": 3600,  # 1時間毎
            "priority_times": [6, 12, 18, 0],  # 照明切替時
            "motion_triggered": True,
            "quality_threshold": 0.7
        }
    
    def start_collection(self):
        """24時間自動データ収集開始"""
        # スケジューラー起動
        # フレーム品質チェック
        # ファイル自動保存
        # メタデータ記録
```

#### タスク 1-3: データ品質管理
```python
# 実装ファイル: data_collection/quality_manager.py
class DataQualityManager:
    def evaluate_frame(self, frame, metadata):
        """フレーム品質評価"""
        # ハムスター検出サイズ
        # 画像鮮明度
        # 姿勢多様性
        # 重複除外
        return accept_reject_decision
    
    def organize_dataset(self):
        """データセット整理"""
        # 時間帯別分類
        # 照明条件別分類
        # 姿勢バリエーション確認
        # 学習用分割 (train/val/test)
```

### Day 2: データ収集開始・監視

#### タスク 2-1: 収集システム起動
- 自動撮影スケジュール開始
- 品質監視ダッシュボード
- エラー処理・ログ記録

#### タスク 2-2: 初期データ評価
- 12時間分データ品質チェック
- 照明モード判定精度確認
- 収集スケジュール調整

### Day 3-4: データ蓄積・ラベリング準備

#### タスク 3-1: 継続データ収集
- 48-72時間の連続データ収集
- 目標: 200-250枚の多様な画像

#### タスク 4-1: ラベリング環境準備
```bash
# DeepLabCutインストール・設定
conda activate hamcam
pip install deeplabcut[gui]

# プロジェクト作成
python -c "
import deeplabcut
deeplabcut.create_new_project('hamcam_tracking', 'researcher', 
                              ['/path/to/videos'], copy_videos=False)
"
```

---

## Phase 3-1: MVP実装 (Week 1: Day 5-11)

### Day 5: DeepLabCutプロジェクト設定

#### タスク 5-1: 身体部位定義
```python
# config.yaml編集
bodyparts:
- nose        # 鼻 (最重要参照点)
- back        # 背中 (重心計算用)
- tail        # 尻尾 (方向判定用)

# 最小構成で学習効率化
skeleton: []  # 初期は不要
```

#### タスク 5-2: 学習データ準備
```python
# 実装ファイル: deeplabcut/data_preparation.py
def prepare_training_data():
    """学習用データセット準備"""
    # 収集画像から100-120枚選定
    # カラー/IR 50:50比率
    # 姿勢多様性確保
    # 品質フィルタリング
    return selected_frames
```

### Day 6-7: ラベリング作業

#### タスク 6-1: 手動ラベリング
- DeepLabCut GUI使用
- 100-120枚の精密ラベリング
- 鼻・背中・尻尾の3点マーキング
- 品質チェック・修正

#### タスク 7-1: データ拡張準備
```python
# data_augmentation.py
def augment_training_data():
    """データ拡張処理"""
    # 輝度・コントラスト調整
    # カラー→グレースケール変換
    # ガウシアンノイズ付加
    # 水平反転 (ケージ対称性考慮)
```

### Day 8-9: DeepLabCut学習

#### タスク 8-1: 学習設定最適化
```yaml
# config.yaml 学習パラメータ
TrainingFraction: [0.8]
iteration: 0
default_net_type: mobilenet_v2_0.35  # 軽量化
multianimalproject: false
skeleton_color: black
pcutoff: 0.1
dotsize: 4
alphavalue: 0.7
```

#### タスク 8-2: モデル学習実行
```bash
# GPU使用学習 (メインPC)
python -c "
import deeplabcut
config_path = '/path/to/config.yaml'
deeplabcut.train_network(config_path, maxiters=50000)
"
```

#### タスク 9-1: 学習結果評価
```python
# モデル評価・検証
deeplabcut.evaluate_network(config_path, plotting=True)
# 目標: train error < 5px, test error < 8px
```

### Day 10-11: 推論システム実装

#### タスク 10-1: 推論エンジン構築
```python
# 実装ファイル: hamster_tracking/pose_estimator.py
class HamsterPoseEstimator:
    def __init__(self, model_path, config_path):
        """DeepLabCut推論エンジン初期化"""
        self.dlc_live = DLCLive(model_path)
        self.confidence_threshold = 0.7
        
    def predict_pose(self, frame):
        """単一フレーム姿勢推定"""
        # DeepLabCut推論実行
        # 信頼度フィルタリング
        # 座標正規化
        return pose_data
    
    def filter_low_confidence(self, pose_data):
        """低信頼度点の除外"""
        # 閾値未満の点を除外
        # 補間・平滑化処理
        return filtered_pose
```

#### タスク 11-1: 座標校正システム
```python
# 実装ファイル: hamster_tracking/coordinate_calibrator.py
class CoordinateCalibrator:
    def __init__(self, cage_size_mm=(380, 280)):
        """ケージサイズでの校正初期化"""
        self.cage_size = cage_size_mm
        self.calibration_matrix = None
        
    def calibrate_from_markers(self, corner_pixels):
        """四隅マーカーから校正行列算出"""
        # ピクセル座標→実寸変換行列
        # 歪み補正計算
        # 精度検証
        return calibration_success
    
    def pixel_to_mm(self, pixel_coords):
        """ピクセル→mm変換"""
        # 校正行列適用
        # 座標変換
        return mm_coords
```

---

## Phase 3-2: 精度向上・安定化 (Week 2: Day 12-18)

### Day 12-13: 身体部位拡張

#### タスク 12-1: 7点身体部位への拡張
```python
# config.yaml更新
bodyparts:
- nose      # 鼻
- head      # 頭頂部
- left_ear  # 左耳
- right_ear # 右耳  
- back      # 背中
- hip       # 腰
- tail      # 尻尾
```

#### タスク 12-2: 追加学習データ収集
```python
# 50-80枚追加ラベリング
# 詳細部位マーキング
# 困難姿勢（横向き、丸まり）対応
# 照明条件バリエーション増加
```

#### タスク 13-1: 再学習・評価
```bash
# 拡張データでの再学習
deeplabcut.train_network(config_path, maxiters=75000, 
                        displayiters=1000, saveiters=5000)
# 精度目標: test error < 5px
```

### Day 14-15: 移動量計算システム

#### タスク 14-1: 重心計算ロジック
```python
# 実装ファイル: hamster_tracking/movement_calculator.py
class MovementCalculator:
    def __init__(self):
        self.body_part_weights = {
            'nose': 0.2, 'head': 0.25, 'back': 0.3,
            'hip': 0.25, 'left_ear': 0.05, 'right_ear': 0.05,
            'tail': 0.1
        }
        
    def calculate_body_center(self, pose_data):
        """信頼度重み付き重心計算"""
        # 信頼度 × 部位重み × 座標
        # 重み付き平均
        # 中心点座標算出
        return center_point
    
    def calculate_movement_distance(self, prev_center, curr_center):
        """フレーム間移動距離"""
        # ユークリッド距離計算
        # 異常値検出・除外
        # 累積距離更新
        return distance_mm
```

#### タスク 15-1: 異常値除去・平滑化
```python
class MovementFilter:
    def __init__(self):
        self.kalman_filter = cv2.KalmanFilter(4, 2)
        self.max_jump_distance = 50  # mm
        
    def filter_movement(self, raw_positions):
        """カルマンフィルタ平滑化"""
        # 予測・更新ステップ
        # 異常値検出
        # 平滑化処理
        return filtered_positions
    
    def detect_outliers(self, movement_sequence):
        """異常な移動の検出"""
        # 統計的異常値検出
        # 物理的制約チェック
        # ノイズ除去
        return clean_sequence
```

### Day 16-17: 統計・可視化機能

#### タスク 16-1: 活動量統計
```python
# 実装ファイル: hamster_tracking/activity_analyzer.py
class ActivityAnalyzer:
    def __init__(self):
        self.daily_stats = {}
        self.hourly_breakdown = {}
        
    def calculate_daily_activity(self, movement_data):
        """日別活動量計算"""
        # 総移動距離
        # 平均移動速度
        # 活動時間割合
        # 最大連続活動時間
        return daily_metrics
    
    def analyze_circadian_pattern(self, multi_day_data):
        """概日リズム解析"""
        # 時間別活動量
        # 昼夜活動比率
        # ピーク活動時間
        return circadian_analysis
```

#### タスク 17-1: レポート生成機能
```python
class ReportGenerator:
    def generate_daily_report(self, date, activity_data):
        """日次レポート生成"""
        # 活動量サマリー
        # 時間別グラフ
        # 異常検知アラート
        # JSONファイル出力
        return report_data
    
    def create_visual_report(self, data):
        """可視化レポート"""
        # matplotlib活動グラフ
        # 移動軌跡プロット
        # 統計情報表示
        return visualization_files
```

### Day 18: システム統合テスト

#### タスク 18-1: エンドツーエンドテスト
```python
# integration_test.py
def test_full_pipeline():
    """全体パイプラインテスト"""
    # RTSP → 姿勢推定 → 移動計算 → 統計生成
    # 24時間分データでのテスト
    # 精度・性能評価
    # エラーハンドリング確認
```

---

## Phase 3-3: MINIPC最適化・運用化 (Week 3: Day 19-25)

### Day 19-20: MINIPC環境構築

#### タスク 19-1: 軽量環境セットアップ
```bash
# MINIPC (Intel N97) 環境構築
# Ubuntu Server LTS (最小構成)
# conda環境複製
# TensorFlow Lite環境

# 軽量パッケージインストール
pip install tensorflow-lite opencv-python-headless
pip install deeplabcut-live numpy scipy sqlite3
```

#### タスク 19-2: モデル軽量化・変換
```python
# model_optimization.py
def convert_to_tflite():
    """TensorFlow Lite変換"""
    # 量子化 (FP32 → INT8)
    # 最適化フラグ設定
    # 推論速度テスト
    # 精度維持確認
    return optimized_model

def benchmark_minipc_performance():
    """MINIPC性能ベンチマーク"""
    # FPS測定
    # CPU使用率監視
    # メモリ使用量測定
    # 発熱テスト
```

#### タスク 20-1: 推論システム移植
```python
# 実装ファイル: minipc/hamster_monitor.py
class MiniPCHamsterMonitor:
    def __init__(self):
        """MINIPC用監視システム"""
        self.pose_estimator = LightweightPoseEstimator()
        self.movement_calculator = MovementCalculator()
        self.data_logger = SQLiteLogger()
        
    def start_monitoring(self):
        """連続監視開始"""
        # RTSPストリーム接続
        # リアルタイム推論
        # データ記録
        # 統計更新
```

### Day 21-22: 自動化・監視機能

#### タスク 21-1: システム自動化
```python
# 実装ファイル: minipc/system_manager.py
class SystemManager:
    def __init__(self):
        """システム管理機能"""
        self.health_monitor = HealthMonitor()
        self.auto_recovery = AutoRecovery()
        
    def setup_autostart(self):
        """自動起動設定"""
        # systemdサービス作成
        # 起動順序設定
        # 依存関係管理
        
    def monitor_system_health(self):
        """システム監視"""
        # CPU/メモリ使用率
        # ディスク容量
        # ネットワーク接続
        # エラー率監視
```

#### タスク 21-2: エラー自動復旧
```python
class AutoRecovery:
    def handle_rtsp_disconnection(self):
        """RTSP切断時の自動復旧"""
        # 再接続リトライ
        # 指数バックオフ
        # アラート送信
        
    def handle_inference_errors(self):
        """推論エラー処理"""
        # モデル再読み込み
        # フレームスキップ
        # 品質劣化対応
```

#### タスク 22-1: アラート・通知機能
```python
class AlertSystem:
    def __init__(self):
        """アラートシステム"""
        self.alert_rules = {
            'no_movement_hours': 4,    # 4時間無動
            'system_error_count': 10,  # エラー閾値
            'low_confidence_ratio': 0.5  # 低信頼度比率
        }
        
    def check_alerts(self, current_data):
        """アラート条件チェック"""
        # ルールベース判定
        # 通知生成
        # ログ記録
```

### Day 23-24: UI・レポート機能

#### タスク 23-1: 軽量Web UI
```python
# 実装ファイル: minipc/web_interface.py
from flask import Flask, render_template, jsonify

class HamsterMonitorUI:
    def __init__(self):
        self.app = Flask(__name__)
        self.setup_routes()
        
    def setup_routes(self):
        """Webルート設定"""
        # /status - システム状態
        # /live - ライブ映像
        # /stats - 統計データ
        # /reports - レポート一覧
        
    def get_realtime_data(self):
        """リアルタイムデータAPI"""
        # 現在位置
        # 活動状態
        # システム状態
        return json_response
```

#### タスク 24-1: レポート自動生成
```python
class AutoReportGenerator:
    def __init__(self):
        """自動レポート生成"""
        self.schedule = {
            'daily': '23:59',   # 日次レポート
            'weekly': 'sun 23:59',  # 週次レポート
            'monthly': '1 00:00'    # 月次レポート
        }
        
    def generate_scheduled_reports(self):
        """スケジュールレポート生成"""
        # 活動量サマリー
        # グラフ生成
        # 異常検知結果
        # PDF出力
```

### Day 25: 最終統合・長期テスト

#### タスク 25-1: 最終システム統合
```python
# integration_final.py
def deploy_production_system():
    """本番システム配置"""
    # 全機能統合確認
    # パフォーマンステスト
    # セキュリティチェック
    # バックアップ設定
    
def start_long_term_test():
    """長期動作テスト開始"""
    # 7日間連続運用
    # 稼働率測定
    # データ整合性確認
    # 異常検知テスト
```

---

## ファイル構成

```
/home/mushipi/Scripts/hamcam_reolink/
├── phase3_hamster_tracking/
│   ├── data_collection/
│   │   ├── auto_capture.py           # 自動撮影システム
│   │   ├── quality_manager.py        # データ品質管理
│   │   └── lighting_detector.py      # 照明モード検出
│   ├── deeplabcut/
│   │   ├── data_preparation.py       # 学習データ準備
│   │   ├── training_config.yaml      # DeepLabCut設定
│   │   └── model_optimization.py     # モデル最適化
│   ├── hamster_tracking/
│   │   ├── pose_estimator.py         # 姿勢推定エンジン
│   │   ├── coordinate_calibrator.py  # 座標校正
│   │   ├── movement_calculator.py    # 移動量計算
│   │   └── activity_analyzer.py      # 活動量解析
│   ├── minipc/
│   │   ├── hamster_monitor.py        # MINIPC監視システム
│   │   ├── system_manager.py         # システム管理
│   │   ├── web_interface.py          # Web UI
│   │   └── auto_reports.py           # 自動レポート
│   ├── utils/
│   │   ├── lighting_detector.py      # 照明検出共通
│   │   ├── data_logger.py            # データ記録
│   │   └── config_manager.py         # 設定管理
│   └── tests/
│       ├── test_pose_estimation.py   # 姿勢推定テスト
│       ├── test_movement_calc.py     # 移動計算テスト
│       └── integration_test.py       # 統合テスト
```

## 成功指標・検証基準

### Phase 3-1 完了基準
- [ ] DeepLabCut 3点検出成功率: 80%+ (昼夜両方)
- [ ] 座標変換精度: ±10mm以内
- [ ] 基本移動距離計算動作確認
- [ ] MINIPC 1fps以上安定処理

### Phase 3-2 完了基準  
- [ ] 7点詳細検出成功率: 90%+ (昼夜両方)
- [ ] 座標変換精度: ±5mm以内
- [ ] 24時間連続データ収集成功
- [ ] 日次/時間別レポート自動生成

### Phase 3-3 完了基準
- [ ] MINIPC 2-3fps安定処理
- [ ] 7日間無人連続運用成功
- [ ] システム稼働率: 99%+
- [ ] 消費電力: 15W以下
- [ ] Web UI正常動作
- [ ] 自動アラート機能動作

## リスク管理

### 技術リスク
1. **DeepLabCut学習失敗**: 学習データ品質・量不足
   - 対策: 段階的データ収集、品質管理強化
2. **MINIPC性能不足**: 処理速度・精度劣化
   - 対策: モデル軽量化、処理頻度調整
3. **昼夜モード対応失敗**: 照明変化時の検出精度低下
   - 対策: 混合学習データ、照明適応処理

### 運用リスク
1. **長期稼働安定性**: メモリリーク、熱暴走
   - 対策: 監視機能、自動再起動
2. **データ欠損**: ストレージ不足、接続障害
   - 対策: ログローテーション、バックアップ

この詳細計画により、段階的かつ確実にハムスター管理システムを構築できます。