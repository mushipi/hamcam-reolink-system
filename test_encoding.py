#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os

# UTF-8エンコーディング強制設定
os.environ['PYTHONIOENCODING'] = 'utf-8'

print("=== エンコーディングテスト ===")
print(f"システムエンコーディング: {sys.stdout.encoding}")
print(f"PYTHONIOENCODING: {os.environ.get('PYTHONIOENCODING', 'なし')}")
print("")
print("日本語テスト:")
print("🎯 照明検出デモ初期化完了")
print("✅ RTSPストリーム開始成功")
print("📊 統計情報をリセットしました")
print("ℹ️ 情報表示: ON")
print("❌ デモ実行エラー")
print("⚠️ 中程度の検出精度")
print("")
print("漢字・ひらがな・カタカナテスト:")
print("照明モード検出デモアプリケーション")
print("リアルタイムでの照明モード表示と統計情報")
print("処理時間: 10.9ms/frame")