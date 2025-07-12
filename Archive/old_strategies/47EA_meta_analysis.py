#!/usr/bin/env python3
"""
47EA全体メタ分析スクリプト
過学習問題の定量的証明とDSR (Deflated Sharpe Ratio) 分析
"""

import math
import warnings
warnings.filterwarnings('ignore')

# 外部ライブラリの条件付きインポート
try:
    import numpy as np
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("⚠️ pandas/numpy not available. Using basic calculations.")

try:
    from scipy.stats import norm
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("⚠️ scipy not available. Using approximations.")

# matplotlib/seabornは可視化時のみインポート
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    PLOT_AVAILABLE = True
except ImportError:
    PLOT_AVAILABLE = False
    print("⚠️ matplotlib/seaborn not available. Skipping visualizations.")

# 基本統計関数（scipyなしでの代替）
def norm_ppf(p):
    """標準正規分布の逆累積分布関数の近似"""
    if SCIPY_AVAILABLE:
        return norm.ppf(p)
    else:
        # Beasley-Springer-Moro algorithm approximation
        if p <= 0 or p >= 1:
            return float('nan')
        if p == 0.5:
            return 0.0
        
        # 近似計算
        if p < 0.5:
            sign = -1
            p = 1 - p
        else:
            sign = 1
        
        t = math.sqrt(-2 * math.log(p))
        x = t - (2.30753 + 0.27061 * t) / (1 + 0.99229 * t + 0.04481 * t * t)
        return sign * x

def analyze_47ea_performance():
    """47EA全体のメタ分析実行"""
    
    print("=" * 60)
    print("🔬 47EA全体メタ分析：統計的概要")
    print("=" * 60)

    # データ準備：戦略モード包括テスト結果 (45EA)
    ea_data = {
        'strategy': [
            'BB+SR+MA標準', 'BB+SR+MA標準', 'BB+SR+MA標準',
            '4indicators包括', '4indicators包括', '4indicators包括', 
            'Channel重視', 'Channel重視', 'Channel重視',
            '動的調整', '動的調整', '動的調整',
            'MA標準', 'MA標準', 'MA標準'
        ] * 3,  # 3通貨ペア分
        'pair': ['USDJPY', 'EURUSD', 'GBPJPY'] * 15,  # 各戦略3通貨
        'timeframe': ['M5'] * 15 + ['M15'] * 15 + ['H1'] * 15,
        'pf': [
            # M5: 良好な成績
            1.78, 1.94, 1.32, 1.89, 2.07, 1.45, 2.16, 2.27, 1.58, 2.12, 2.44, 1.67, 1.76, 1.89, 1.41,
            # M15: 中程度の成績
            1.52, 1.71, 1.18, 1.63, 1.84, 1.29, 1.87, 1.95, 1.34, 1.78, 2.09, 1.42, 1.58, 1.72, 1.25,
            # H1: 問題の多い成績（損失含む）
            1.12, 1.28, 0.95, 1.18, 1.35, 1.04, 1.45, 1.62, 1.08, 1.34, 1.51, 1.11, 1.22, 1.39, 1.06
        ],
        'win_rate': [
            # M5
            62.5, 68.2, 51.3, 64.8, 71.4, 54.7, 51.5, 53.7, 48.2, 67.9, 77.8, 56.3, 59.1, 65.4, 52.8,
            # M15  
            58.7, 63.1, 47.9, 61.2, 66.8, 50.4, 48.3, 50.1, 44.6, 62.4, 71.2, 51.7, 55.3, 60.8, 48.1,
            # H1
            54.2, 57.8, 42.5, 56.7, 61.3, 45.8, 44.1, 45.9, 40.2, 57.1, 64.7, 46.3, 50.8, 55.4, 43.7
        ],
        'max_dd': [
            # M5: 低リスク
            8.45, 6.82, 12.34, 7.91, 4.58, 11.67, 10.80, 9.11, 13.24, 8.73, 7.71, 11.89, 9.34, 7.25, 12.56,
            # M15: 中リスク
            11.23, 9.47, 15.68, 10.84, 7.32, 14.91, 13.57, 12.38, 16.82, 11.95, 10.29, 15.34, 12.67, 9.81, 16.47,
            # H1: 高リスク
            15.89, 13.24, 19.73, 14.52, 11.18, 18.96, 17.43, 16.85, 21.30, 16.28, 14.67, 19.42, 17.91, 13.78, 20.15
        ],
        'total_trades': [
            # M5: 高頻度
            156, 190, 128, 174, 203, 142, 101, 115, 89, 167, 190, 134, 145, 178, 126,
            # M15: 中頻度
            89, 108, 73, 98, 116, 81, 58, 66, 51, 95, 108, 76, 83, 101, 72,
            # H1: 低頻度
            43, 52, 35, 47, 56, 39, 28, 32, 25, 46, 52, 37, 40, 49, 35
        ]
    }

    if PANDAS_AVAILABLE:
        df = pd.DataFrame(ea_data)
    else:
        # pandasなしでの基本実装
        class SimpleDataFrame:
            def __init__(self, data):
                self.data = data
                self.length = len(data[list(data.keys())[0]])
            
            def __len__(self):
                return self.length
            
            def mean(self, col):
                return sum(self.data[col]) / len(self.data[col])
            
            def get_column(self, col):
                return self.data[col]
        
        df = SimpleDataFrame(ea_data)

    # 基本統計
    print(f"\n📊 基本統計情報:")
    print(f"- 分析対象EA数: {len(df)}個")
    print(f"- 平均PF: {df['pf'].mean():.3f}")
    print(f"- 平均勝率: {df['win_rate'].mean():.1f}%")
    print(f"- 平均最大DD: {df['max_dd'].mean():.1f}%")

    # PF分布の分析
    print(f"\n🎯 プロフィットファクター (PF) 分布:")
    excellent = len(df[df['pf'] >= 1.5])
    good = len(df[(df['pf'] >= 1.2) & (df['pf'] < 1.5)])
    marginal = len(df[(df['pf'] >= 1.0) & (df['pf'] < 1.2)])
    loss = len(df[df['pf'] < 1.0])

    print(f"- 🏆 優秀群 (PF ≥ 1.5): {excellent}EA ({excellent/len(df)*100:.1f}%)")
    print(f"- 📊 良好群 (PF 1.2-1.5): {good}EA ({good/len(df)*100:.1f}%)")
    print(f"- ⚠️ 限界群 (PF 1.0-1.2): {marginal}EA ({marginal/len(df)*100:.1f}%)")
    print(f"- 🚨 損失群 (PF < 1.0): {loss}EA ({loss/len(df)*100:.1f}%)")

    # 時間足別分析
    print(f"\n⏰ 時間足別パフォーマンス:")
    for tf in ['M5', 'M15', 'H1']:
        tf_data = df[df['timeframe'] == tf]
        success_rate = len(tf_data[tf_data['pf'] >= 1.2]) / len(tf_data) * 100
        avg_pf = tf_data['pf'].mean()
        print(f"- {tf}: 平均PF {avg_pf:.3f}, 成功率 {success_rate:.1f}% ({len(tf_data[tf_data['pf'] >= 1.2])}/{len(tf_data)})")

    return df

def calculate_sharpe_ratios(df):
    """シャープレシオ推定計算"""
    print(f"\n📈 シャープレシオ推定（年率換算）:")

    # 簡易シャープレシオ計算
    # 仮定: 年250取引日、リスクフリーレート0.1%
    sharpe_ratios = []
    for idx, row in df.iterrows():
        # PFから期待リターンを推定
        if row['pf'] > 1.0:
            annual_return = (row['pf'] - 1) * 0.1  # 10%のリスク基準で推定
        else:
            annual_return = (row['pf'] - 1) * 0.1  # 負のリターン
        
        # 最大DDからボラティリティを推定
        volatility = row['max_dd'] / 100 * 3  # DDの3倍をボラティリティとして概算
        
        # シャープレシオ計算
        risk_free_rate = 0.001  # 0.1%
        sharpe = (annual_return - risk_free_rate) / volatility if volatility > 0 else 0
        sharpe_ratios.append(sharpe)

    df['sharpe_ratio'] = sharpe_ratios

    print(f"- 平均シャープレシオ: {df['sharpe_ratio'].mean():.3f}")
    print(f"- 最高シャープレシオ: {df['sharpe_ratio'].max():.3f}")
    print(f"- 最低シャープレシオ: {df['sharpe_ratio'].min():.3f}")
    
    return df

def calculate_dsr_analysis(df):
    """Deflated Sharpe Ratio (DSR) 分析"""
    print(f"\n🔬 DSR (Deflated Sharpe Ratio) 分析:")
    
    N = len(df)  # 試行回数 = 45EA
    max_sharpe = df['sharpe_ratio'].max()
    
    # 期待される最大SRを計算（de Prado公式）
    euler_gamma = 0.5772156649
    z_inv_N = norm.ppf(1 - 1/N)
    z_inv_Ne = norm.ppf(1 - 1/(N * np.e))
    expected_max_SR = (1 - euler_gamma) * z_inv_N + euler_gamma * z_inv_Ne
    
    print(f"- 試行回数 (N): {N}")
    print(f"- 観測最大SR: {max_sharpe:.3f}")
    print(f"- 期待最大SR (偶然): {expected_max_SR:.3f}")
    print(f"- SR超過度: {max_sharpe - expected_max_SR:.3f}")
    
    # DSR統計的判定
    if max_sharpe > expected_max_SR:
        print("✅ 観測SRが期待値を上回る - 統計的優位性の可能性")
        significance = "有意"
    else:
        print("⚠️ 観測SRが期待値以下 - 偶然の可能性が高い")
        significance = "非有意"
    
    # 過学習度の定量化
    overfitting_ratio = max_sharpe / expected_max_SR if expected_max_SR > 0 else 0
    print(f"- 過学習度指標: {overfitting_ratio:.3f}")
    
    if overfitting_ratio < 0.8:
        print("🚨 深刻な過学習状態：最良EAでも偶然期待値を大幅に下回る")
    elif overfitting_ratio < 1.0:
        print("⚠️ 過学習の疑い：期待値未達成")
    elif overfitting_ratio < 1.2:
        print("📊 適正範囲：わずかな優位性")
    else:
        print("🏆 優秀：明確な統計的優位性")
    
    return {
        'trials': N,
        'max_observed_sr': max_sharpe,
        'expected_max_sr': expected_max_SR,
        'excess_sr': max_sharpe - expected_max_SR,
        'overfitting_ratio': overfitting_ratio,
        'significance': significance
    }

def create_visualizations(df):
    """統計的可視化"""
    if not PLOT_AVAILABLE:
        print("📊 可視化ライブラリが利用できないため、スキップします。")
        return
    
    # 可視化設定
    plt.style.use('default')
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))

    # PF分布
    axes[0,0].hist(df['pf'], bins=20, alpha=0.7, edgecolor='black')
    axes[0,0].axvline(1.0, color='red', linestyle='--', label='損益分岐点')
    axes[0,0].axvline(df['pf'].mean(), color='blue', linestyle='-', label=f'平均: {df["pf"].mean():.3f}')
    axes[0,0].set_xlabel('プロフィットファクター (PF)')
    axes[0,0].set_ylabel('頻度')
    axes[0,0].set_title('47EA プロフィットファクター分布')
    axes[0,0].legend()
    axes[0,0].grid(True, alpha=0.3)

    # 勝率vs PF散布図
    colors = {'M5': 'blue', 'M15': 'green', 'H1': 'red'}
    for tf in ['M5', 'M15', 'H1']:
        tf_data = df[df['timeframe'] == tf]
        axes[0,1].scatter(tf_data['win_rate'], tf_data['pf'], 
                         label=tf, alpha=0.7, s=60, color=colors[tf])
    axes[0,1].set_xlabel('勝率 (%)')
    axes[0,1].set_ylabel('プロフィットファクター (PF)')
    axes[0,1].set_title('勝率 vs PF (時間足別)')
    axes[0,1].legend()
    axes[0,1].grid(True, alpha=0.3)

    # 最大DD分布
    axes[1,0].hist(df['max_dd'], bins=15, alpha=0.7, edgecolor='black', color='orange')
    axes[1,0].axvline(df['max_dd'].mean(), color='red', linestyle='-', 
                     label=f'平均: {df["max_dd"].mean():.1f}%')
    axes[1,0].set_xlabel('最大ドローダウン (%)')
    axes[1,0].set_ylabel('頻度')
    axes[1,0].set_title('47EA 最大ドローダウン分布')
    axes[1,0].legend()
    axes[1,0].grid(True, alpha=0.3)

    # シャープレシオ分布とDSR分析
    expected_max_SR = 2.0  # 概算値
    axes[1,1].hist(df['sharpe_ratio'], bins=20, alpha=0.7, edgecolor='black', color='green')
    axes[1,1].axvline(0, color='red', linestyle='--', label='ゼロライン')
    axes[1,1].axvline(df['sharpe_ratio'].mean(), color='blue', linestyle='-', 
                     label=f'平均: {df["sharpe_ratio"].mean():.3f}')
    axes[1,1].axvline(expected_max_SR, color='purple', linestyle=':', 
                     label=f'期待最大SR: {expected_max_SR:.3f}')
    axes[1,1].set_xlabel('シャープレシオ (推定)')
    axes[1,1].set_ylabel('頻度')
    axes[1,1].set_title('47EA シャープレシオ分布 (DSR分析)')
    axes[1,1].legend()
    axes[1,1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('47EA_meta_analysis_visualization.png', dpi=300, bbox_inches='tight')
    print("📊 可視化を '47EA_meta_analysis_visualization.png' に保存しました。")

def generate_strategy_summary(df):
    """戦略別統計要約"""
    print(f"\n📋 戦略別統計要約:")
    strategy_summary = df.groupby('strategy').agg({
        'pf': ['mean', 'std', 'min', 'max'],
        'win_rate': ['mean', 'std'],
        'max_dd': ['mean', 'std'],
        'sharpe_ratio': ['mean', 'std']
    }).round(3)
    
    print(strategy_summary)
    
    # 時間足別要約
    print(f"\n⏰ 時間足別統計要約:")
    timeframe_summary = df.groupby('timeframe').agg({
        'pf': ['mean', 'std', 'min', 'max', 'count'],
        'win_rate': ['mean', 'std'],
        'max_dd': ['mean', 'std'],
        'sharpe_ratio': ['mean', 'std']
    }).round(3)
    
    print(timeframe_summary)
    
    return strategy_summary, timeframe_summary

def main():
    """メイン実行関数"""
    # データ分析実行
    df = analyze_47ea_performance()
    df = calculate_sharpe_ratios(df)
    dsr_results = calculate_dsr_analysis(df)
    
    # 可視化
    create_visualizations(df)
    
    # 統計要約
    strategy_summary, timeframe_summary = generate_strategy_summary(df)
    
    # 最終結論
    print("\n" + "=" * 60)
    print("🎯 47EA メタ分析 結論")
    print("=" * 60)
    
    print(f"\n📊 統計的証明:")
    print(f"- 過学習度指標: {dsr_results['overfitting_ratio']:.3f}")
    print(f"- 統計的有意性: {dsr_results['significance']}")
    print(f"- 最高SR vs 期待SR: {dsr_results['max_observed_sr']:.3f} vs {dsr_results['expected_max_sr']:.3f}")
    
    if dsr_results['overfitting_ratio'] < 1.0:
        print(f"\n🚨 重要な発見:")
        print(f"47回の試行でも、偶然期待される水準を下回る結果。")
        print(f"これは戦略群全体の市場優位性欠如を示唆している。")
        print(f"根本的な戦略アプローチの見直しが必要。")
    
    # データ保存
    df.to_csv('47EA_meta_analysis_results.csv', index=False)
    print(f"\n💾 分析結果を '47EA_meta_analysis_results.csv' に保存しました。")
    
    return df, dsr_results

if __name__ == "__main__":
    df, dsr_results = main()