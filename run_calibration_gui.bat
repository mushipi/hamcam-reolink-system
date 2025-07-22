@echo off
chcp 65001 >nul
REM -*- coding: utf-8 -*-
REM
REM GUI座標校正ツール実行バッチファイル (Windows版)
REM ハムスターケージの座標校正を行うGUIツール
REM
REM 使用方法:
REM   run_calibration_gui.bat              # メインストリーム使用
REM   run_calibration_gui.bat sub          # サブストリーム使用  
REM   run_calibration_gui.bat main 300     # メインストリーム、5分間制限
REM

setlocal enabledelayedexpansion

REM スクリプトディレクトリに移動
cd /d "%~dp0"

REM Python環境のパス設定（Anaconda環境想定）
set PYTHON_PATH=%USERPROFILE%\anaconda3\python.exe
set GUI_SCRIPT=phase3_hamster_tracking\hamster_tracking\calibration_gui.py

REM 引数処理
set STREAM_TYPE=%1
if "%STREAM_TYPE%"=="" set STREAM_TYPE=main

set DURATION=%2
if "%DURATION%"=="" set DURATION=0

REM 実行前チェック
echo ========================================
echo GUI座標校正ツール 実行準備
echo ========================================
echo 実行日時: %date% %time%
echo ストリーム: %STREAM_TYPE%
if %DURATION%==0 (
    echo 実行時間: 無制限
) else (
    echo 実行時間: %DURATION%秒
)
echo.

REM Python環境確認
if not exist "%PYTHON_PATH%" (
    echo ❌ エラー: Python環境が見つかりません
    echo    パス: %PYTHON_PATH%
    echo    Anacondaが正しくインストールされているか確認してください
    pause
    exit /b 1
)

REM GUIスクリプト確認
if not exist "%GUI_SCRIPT%" (
    echo ❌ エラー: GUI校正スクリプトが見つかりません
    echo    パス: %GUI_SCRIPT%
    echo    Phase 3システムが正しくセットアップされているか確認してください
    pause
    exit /b 1
)

REM 設定ファイル確認
set CONFIG_FILE=phase3_hamster_tracking\config\hamster_config.yaml
if not exist "%CONFIG_FILE%" (
    echo ⚠️  警告: 設定ファイルが見つかりません
    echo    パス: %CONFIG_FILE%
    echo    デフォルト設定で実行します
)

REM カメラ接続テスト
echo 📹 カメラ接続テスト中...
ping -n 1 -w 3000 192.168.31.85 >nul 2>&1
if %errorlevel%==0 (
    echo ✅ カメラ接続OK ^(192.168.31.85^)
) else (
    echo ⚠️  警告: カメラに接続できません ^(192.168.31.85^)
    echo    ネットワーク接続とカメラの電源を確認してください
    echo    続行しますか？ ^(Y/N^): 
    set /p response=
    if /i not "!response!"=="y" (
        echo 実行を中止しました
        pause
        exit /b 1
    )
)

echo.
echo ========================================
echo GUI校正ツール開始
echo ========================================
echo 操作方法:
echo   🖱️  左クリック: ケージ四隅を左上→右上→右下→左下の順でクリック
echo   🖱️  右クリック: 最後の校正点を削除
echo   ⌨️  'r': 校正リセット
echo   ⌨️  't': テストモード切り替え（校正完了後）
echo   ⌨️  's': 校正データ手動保存
echo   ⌨️  'q'またはESC: 終了
echo.
echo 📋 校正手順:
echo   1. RTSPストリーム映像でケージ全体が見えることを確認
echo   2. ケージの四隅を正確にクリック選択
echo   3. 4点選択完了で自動校正実行
echo   4. 校正結果（RMSE誤差）を確認
echo   5. テストモードで座標変換精度を検証
echo.
echo 準備ができたら何かキーを押してください...
pause >nul

REM GUI校正ツール実行
echo 🚀 GUI校正ツール実行中...
echo コマンド: %PYTHON_PATH% %GUI_SCRIPT% --stream %STREAM_TYPE% --duration %DURATION%
echo.

REM 実行時間計測開始
set START_TIME=%time%

REM GUI校正ツール実行
if %DURATION%==0 (
    "%PYTHON_PATH%" "%GUI_SCRIPT%" --stream %STREAM_TYPE%
) else (
    "%PYTHON_PATH%" "%GUI_SCRIPT%" --stream %STREAM_TYPE% --duration %DURATION%
)

REM 実行結果確認
set EXIT_CODE=%errorlevel%
set END_TIME=%time%

echo.
echo ========================================
echo 実行結果
echo ========================================
echo 開始時間: %START_TIME%
echo 終了時間: %END_TIME%
echo 終了コード: %EXIT_CODE%

if %EXIT_CODE%==0 (
    echo ✅ GUI校正ツールが正常終了しました
    
    REM 校正結果確認
    set CALIBRATION_FILE=phase3_hamster_tracking\config\calibration_matrix.yaml
    if exist "!CALIBRATION_FILE!" (
        echo.
        echo 📊 校正データが保存されました:
        echo    ファイル: !CALIBRATION_FILE!
        for %%i in ("!CALIBRATION_FILE!") do echo    更新日時: %%~ti
    ) else (
        echo ⚠️  校正データファイルが見つかりません
        echo    校正が完了していない可能性があります
    )
) else (
    echo ❌ GUI校正ツールでエラーが発生しました
    echo    エラーコード: %EXIT_CODE%
    echo    ログを確認して問題を解決してください
)

echo.
echo ========================================
echo 次のステップ
echo ========================================
if %EXIT_CODE%==0 (
    echo ✅ 校正完了後の推奨作業:
    echo    1. 座標変換テストで精度確認
    echo    2. 自動撮影システムでデータ収集開始
    echo    3. DeepLabCut学習用データの準備
    echo.
    echo 🔧 利用可能なツール:
    echo    - 座標校正テスト: %PYTHON_PATH% phase3_hamster_tracking\hamster_tracking\coordinate_calibrator.py
    echo    - 照明検出デモ: %PYTHON_PATH% lighting_detection_demo.py
    echo    - 設定確認: %PYTHON_PATH% phase3_hamster_tracking\utils\hamster_config.py
) else (
    echo 🔧 トラブルシューティング:
    echo    - カメラ接続確認: ping 192.168.31.85
    echo    - RTSPストリームテスト: %PYTHON_PATH% rtsp_stream.py
    echo    - ログファイル確認: 最新のエラーメッセージを確認
    echo    - 設定ファイル確認: %CONFIG_FILE%
)

echo.
echo 実行完了: %date% %time%
echo バッチファイルを閉じるには何かキーを押してください...
pause >nul