#!/usr/bin/env python3
"""
ライブ映像表示デモ
シンプルな映像表示アプリケーション
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from video_viewer import VideoViewer
import logging

def main():
    """ライブ映像表示デモ"""
    print("=== RLC-510A ライブ映像表示デモ ===")
    print("このデモでは、カメラからのライブ映像を表示します")
    print()
    
    # ログ設定
    logging.basicConfig(level=logging.INFO)
    
    # ストリーム選択
    print("ストリームを選択してください:")
    print("1. メインストリーム (高解像度・高品質)")
    print("2. サブストリーム (低解像度・軽量)")
    
    while True:
        choice = input("選択 (1-2): ").strip()
        if choice == "1":
            stream_type = "main"
            break
        elif choice == "2":
            stream_type = "sub"
            break
        else:
            print("無効な選択です。1または2を入力してください。")
    
    print(f"\n{stream_type}ストリームで映像表示を開始します...")
    print()
    print("操作方法:")
    print("  'q' or ESC : 終了")
    print("  'i'        : 情報表示切り替え")
    print("  's'        : 統計表示切り替え")
    print("  'f'        : フルスクリーン切り替え")
    print("  'r'        : ストリームリセット")
    print()
    
    # 映像表示開始
    viewer = VideoViewer(stream_type, f"Reolink RLC-510A - {stream_type.upper()}")
    viewer.start_display()

if __name__ == "__main__":
    main()