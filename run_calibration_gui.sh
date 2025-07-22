#!/bin/bash
# -*- coding: utf-8 -*-
#
# GUI座標校正ツール実行スクリプト
# ハムスターケージの座標校正を行うGUIツール
#
# 使用方法:
#   ./run_calibration_gui.sh              # メインストリーム使用
#   ./run_calibration_gui.sh sub          # サブストリーム使用
#   ./run_calibration_gui.sh main 300     # メインストリーム、5分間制限
#

# スクリプトディレクトリに移動
cd "$(dirname "$0")"

# Anaconda環境のパス設定
PYTHON_PATH="$HOME/anaconda3/bin/python"
GUI_SCRIPT="phase3_hamster_tracking/hamster_tracking/calibration_gui.py"

# 引数処理
STREAM_TYPE=${1:-"main"}        # デフォルトはメインストリーム
DURATION=${2:-0}                # デフォルトは無制限

# 実行前チェック
echo "=== GUI座標校正ツール 実行準備 ==="
echo "実行日時: $(date '+%Y-%m-%d %H:%M:%S')"
echo "ストリーム: $STREAM_TYPE"
if [ "$DURATION" -eq 0 ]; then
    echo "実行時間: 無制限"
else
    echo "実行時間: ${DURATION}秒"
fi
echo ""

# Anaconda環境確認
if [ ! -f "$PYTHON_PATH" ]; then
    echo "❌ エラー: Anaconda環境が見つかりません"
    echo "   パス: $PYTHON_PATH"
    echo "   Anacondaが正しくインストールされているか確認してください"
    exit 1
fi

# GUIスクリプト確認
if [ ! -f "$GUI_SCRIPT" ]; then
    echo "❌ エラー: GUI校正スクリプトが見つかりません"
    echo "   パス: $GUI_SCRIPT"
    echo "   Phase 3システムが正しくセットアップされているか確認してください"
    exit 1
fi

# 設定ファイル確認
CONFIG_FILE="phase3_hamster_tracking/config/hamster_config.yaml"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "⚠️  警告: 設定ファイルが見つかりません"
    echo "   パス: $CONFIG_FILE"
    echo "   デフォルト設定で実行します"
fi

# カメラ接続テスト（オプション）
echo "📹 カメラ接続テスト中..."
if ping -c 1 -W 3 192.168.31.85 > /dev/null 2>&1; then
    echo "✅ カメラ接続OK (192.168.31.85)"
else
    echo "⚠️  警告: カメラに接続できません (192.168.31.85)"
    echo "   ネットワーク接続とカメラの電源を確認してください"
    echo "   続行しますか？ (y/N): "
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "実行を中止しました"
        exit 1
    fi
fi

echo ""
echo "=== GUI校正ツール開始 ==="
echo "操作方法:"
echo "  🖱️  左クリック: ケージ四隅を左上→右上→右下→左下の順でクリック"
echo "  🖱️  右クリック: 最後の校正点を削除"
echo "  ⌨️  'r': 校正リセット"
echo "  ⌨️  't': テストモード切り替え（校正完了後）"
echo "  ⌨️  's': 校正データ手動保存"
echo "  ⌨️  'q'またはESC: 終了"
echo ""
echo "📋 校正手順:"
echo "  1. RTSPストリーム映像でケージ全体が見えることを確認"
echo "  2. ケージの四隅を正確にクリック選択"
echo "  3. 4点選択完了で自動校正実行"
echo "  4. 校正結果（RMSE誤差）を確認"
echo "  5. テストモードで座標変換精度を検証"
echo ""
echo "準備ができたら何かキーを押してください..."
read -r

# GUI校正ツール実行
echo "🚀 GUI校正ツール実行中..."
echo "コマンド: $PYTHON_PATH $GUI_SCRIPT --stream $STREAM_TYPE --duration $DURATION"
echo ""

# 実行時間計測開始
START_TIME=$(date +%s)

# GUI校正ツール実行
if [ "$DURATION" -eq 0 ]; then
    "$PYTHON_PATH" "$GUI_SCRIPT" --stream "$STREAM_TYPE"
else
    "$PYTHON_PATH" "$GUI_SCRIPT" --stream "$STREAM_TYPE" --duration "$DURATION"
fi

# 実行結果確認
EXIT_CODE=$?
END_TIME=$(date +%s)
ELAPSED_TIME=$((END_TIME - START_TIME))

echo ""
echo "=== 実行結果 ==="
echo "実行時間: ${ELAPSED_TIME}秒"
echo "終了コード: $EXIT_CODE"

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ GUI校正ツールが正常終了しました"
    
    # 校正結果確認
    CALIBRATION_FILE="phase3_hamster_tracking/config/calibration_matrix.yaml"
    if [ -f "$CALIBRATION_FILE" ]; then
        echo ""
        echo "📊 校正データが保存されました:"
        echo "   ファイル: $CALIBRATION_FILE"
        echo "   作成日時: $(stat -c '%y' "$CALIBRATION_FILE" 2>/dev/null || date)"
        
        # 校正精度情報抽出（簡易版）
        if command -v yq > /dev/null 2>&1; then
            echo "   校正精度情報:"
            yq eval '.accuracy_metrics.rmse_error_mm // "N/A"' "$CALIBRATION_FILE" 2>/dev/null | \
                sed 's/^/     RMSE誤差: /' || echo "     情報取得エラー"
        fi
    else
        echo "⚠️  校正データファイルが見つかりません"
        echo "   校正が完了していない可能性があります"
    fi
    
elif [ $EXIT_CODE -eq 130 ]; then
    echo "⚠️  ユーザーによって中断されました (Ctrl+C)"
else
    echo "❌ GUI校正ツールでエラーが発生しました"
    echo "   エラーコード: $EXIT_CODE"
    echo "   ログを確認して問題を解決してください"
fi

echo ""
echo "=== 次のステップ ==="
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ 校正完了後の推奨作業:"
    echo "   1. 座標変換テストで精度確認"
    echo "   2. 自動撮影システムでデータ収集開始"
    echo "   3. DeepLabCut学習用データの準備"
    echo ""
    echo "🔧 利用可能なツール:"
    echo "   - 座標校正テスト: ~/anaconda3/bin/python phase3_hamster_tracking/hamster_tracking/coordinate_calibrator.py"
    echo "   - 照明検出デモ: ~/anaconda3/bin/python lighting_detection_demo.py"
    echo "   - 設定確認: ~/anaconda3/bin/python phase3_hamster_tracking/utils/hamster_config.py"
else
    echo "🔧 トラブルシューティング:"
    echo "   - カメラ接続確認: ping 192.168.31.85"
    echo "   - RTSPストリームテスト: ~/anaconda3/bin/python rtsp_stream.py"
    echo "   - ログファイル確認: 最新のエラーメッセージを確認"
    echo "   - 設定ファイル確認: $CONFIG_FILE"
fi

echo ""
echo "実行完了: $(date '+%Y-%m-%d %H:%M:%S')"