#!/usr/bin/env python3
"""
データキャッシュシステム
品質優先の5年データ生成と高速読み込み
"""

import os
import pickle
from datetime import datetime

from multi_timeframe_breakout_strategy import create_enhanced_sample_data


class DataCacheManager:
    """データキャッシュ管理クラス"""

    def __init__(self, cache_dir="data_cache"):
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(cache_dir, "full_market_data_5y.pkl")

        # キャッシュディレクトリ作成
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)

    def get_full_data(self, force_regenerate=False):
        """
        フルデータ取得（キャッシュ活用）

        Args:
            force_regenerate: 強制再生成フラグ

        Returns:
            list: 5年間のM5データ
        """

        if force_regenerate or not os.path.exists(self.cache_file):
            print("🔄 フルデータ生成中...")
            print("   予想時間: 3-5分（初回のみ）")

            # フルデータ生成
            start_time = datetime.now()
            data = create_enhanced_sample_data()
            generation_time = (datetime.now() - start_time).total_seconds()

            print(f"   生成完了: {len(data)}バー ({generation_time:.1f}秒)")

            # キャッシュ保存
            print("💾 データキャッシュ保存中...")
            with open(self.cache_file, "wb") as f:
                pickle.dump(data, f)
            print(f"   保存先: {self.cache_file}")

            return data

        else:
            print("⚡ キャッシュデータ読み込み中...")
            start_time = datetime.now()

            with open(self.cache_file, "rb") as f:
                data = pickle.load(f)

            load_time = (datetime.now() - start_time).total_seconds()
            print(f"   読み込み完了: {len(data)}バー ({load_time:.1f}秒)")

            return data

    def get_cache_info(self):
        """キャッシュ情報取得"""
        if os.path.exists(self.cache_file):
            file_size = os.path.getsize(self.cache_file) / (1024 * 1024)  # MB
            mod_time = datetime.fromtimestamp(os.path.getmtime(self.cache_file))

            return {
                "exists": True,
                "file_size_mb": file_size,
                "modified": mod_time.strftime("%Y-%m-%d %H:%M:%S"),
                "path": self.cache_file,
            }
        else:
            return {
                "exists": False,
                "file_size_mb": 0,
                "modified": None,
                "path": self.cache_file,
            }

    def clear_cache(self):
        """キャッシュクリア"""
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)
            print(f"🗑️ キャッシュクリア完了: {self.cache_file}")
        else:
            print("ℹ️ クリア対象のキャッシュが存在しません")


def main():
    """テスト実行"""
    print("🚀 データキャッシュシステムテスト")

    cache_manager = DataCacheManager()

    # キャッシュ情報表示
    info = cache_manager.get_cache_info()
    print("📊 キャッシュ情報:")
    print(f"   存在: {info['exists']}")
    if info["exists"]:
        print(f"   サイズ: {info['file_size_mb']:.1f}MB")
        print(f"   更新日時: {info['modified']}")

    # データ取得テスト
    data = cache_manager.get_full_data()

    print("\n✅ データ取得成功")
    print(f"   データ数: {len(data)}バー")
    print(f"   期間: {data[0]['datetime']} to {data[-1]['datetime']}")

    return cache_manager, data


if __name__ == "__main__":
    cache_manager, data = main()
