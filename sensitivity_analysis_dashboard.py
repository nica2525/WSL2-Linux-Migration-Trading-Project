#!/usr/bin/env python3
"""
感度分析結果ダッシュボード・エクスポートシステム
Claude Code 設計 → GitHub Copilot 実装協働プロジェクト

設計仕様:
1. JSON結果ファイルの自動読み込み・解析
2. インタラクティブダッシュボード (Streamlit)
3. 複数形式エクスポート (CSV, Excel, PDF)
4. パフォーマンス指標の可視化
5. 戦略比較レポート生成

アーキテクチャ:
- DataProcessor: JSON解析・データ正規化
- Visualizer: グラフ・チャート生成
- Exporter: 複数形式出力
- Dashboard: Streamlit UI統合
"""

import json
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import matplotlib.pyplot as plt
import seaborn as sns

class SensitivityAnalysisProcessor:
    """感度分析結果処理クラス（Claude Code設計）"""
    
    def __init__(self, results_file: str = "sensitivity_analysis_results.json"):
        self.results_file = results_file
        self.raw_data = None
        self.processed_data = None
        
    def load_results(self) -> bool:
        """結果ファイル読み込み"""
        try:
            if not Path(self.results_file).exists():
                st.error(f"結果ファイルが見つかりません: {self.results_file}")
                return False
            
            with open(self.results_file, 'r', encoding='utf-8') as f:
                self.raw_data = json.load(f)
            
            # データ構造検証
            if 'sensitivity_analysis' not in self.raw_data:
                st.error("不正なデータ形式: 'sensitivity_analysis'キーが見つかりません")
                return False
            
            st.success(f"✅ 結果ファイル読み込み完了: {len(self.raw_data['sensitivity_analysis'])}シナリオ")
            return True
            
        except json.JSONDecodeError as e:
            st.error(f"JSON解析エラー: {e}")
            return False
        except Exception as e:
            st.error(f"ファイル読み込みエラー: {e}")
            return False
    
    def extract_performance_metrics(self) -> pd.DataFrame:
        """パフォーマンス指標抽出"""
        if self.raw_data is None:
            return pd.DataFrame()
        
        metrics_data = []
        
        for scenario in self.raw_data['sensitivity_analysis']:
            scenario_name = scenario['scenario']
            cost_params = scenario['cost_params']
            
            # WFA結果から指標を抽出
            if 'wfa_results' in scenario:
                wfa_results = scenario['wfa_results']
                
                # 各フォールドの指標を平均化
                avg_metrics = {
                    'scenario': scenario_name,
                    'spread_pips': cost_params['spread_pips'],
                    'commission_pips': cost_params['commission_pips'],
                    'total_cost_pips': cost_params['spread_pips'] + cost_params['commission_pips'],
                    'avg_profit_factor': np.mean([r.get('profit_factor', 0) for r in wfa_results]),
                    'avg_return': np.mean([r.get('total_return', 0) for r in wfa_results]),
                    'avg_win_rate': np.mean([r.get('win_rate', 0) for r in wfa_results]),
                    'avg_trades': np.mean([r.get('trades', 0) for r in wfa_results]),
                    'profitable_folds': sum(1 for r in wfa_results if r.get('profit_factor', 0) > 1.0),
                    'total_folds': len(wfa_results),
                    'consistency_ratio': sum(1 for r in wfa_results if r.get('profit_factor', 0) > 1.0) / len(wfa_results) if wfa_results else 0,
                    'min_profit_factor': min([r.get('profit_factor', 0) for r in wfa_results]) if wfa_results else 0,
                    'max_profit_factor': max([r.get('profit_factor', 0) for r in wfa_results]) if wfa_results else 0,
                    'strategy_viable': sum(1 for r in wfa_results if r.get('profit_factor', 0) > 1.0) / len(wfa_results) >= 0.6 if wfa_results else False
                }
                
                metrics_data.append(avg_metrics)
        
        self.processed_data = pd.DataFrame(metrics_data)
        return self.processed_data
    
    def calculate_scenario_comparison(self) -> pd.DataFrame:
        """シナリオ間比較計算"""
        if self.processed_data is None or self.processed_data.empty:
            return pd.DataFrame()
        
        # ベースライン（最良シナリオ）との比較
        baseline = self.processed_data.loc[self.processed_data['avg_profit_factor'].idxmax()]
        
        comparison_data = []
        
        for _, row in self.processed_data.iterrows():
            comparison = {
                'scenario': row['scenario'],
                'cost_level': 'Low' if row['total_cost_pips'] <= 1.5 else 'High' if row['total_cost_pips'] >= 2.5 else 'Medium',
                'profit_factor_vs_baseline': row['avg_profit_factor'] - baseline['avg_profit_factor'],
                'return_vs_baseline': row['avg_return'] - baseline['avg_return'],
                'profit_factor_pct_change': ((row['avg_profit_factor'] - baseline['avg_profit_factor']) / baseline['avg_profit_factor'] * 100) if baseline['avg_profit_factor'] > 0 else 0,
                'cost_efficiency': row['avg_profit_factor'] / row['total_cost_pips'] if row['total_cost_pips'] > 0 else 0,
                'risk_score': (1 - row['consistency_ratio']) * row['total_cost_pips'],
                'overall_rating': row['avg_profit_factor'] * row['consistency_ratio'] / (row['total_cost_pips'] + 1)
            }
            comparison_data.append(comparison)
        
        return pd.DataFrame(comparison_data)

class SensitivityVisualizer:
    """可視化クラス（Claude Code設計）"""
    
    def __init__(self, processor: SensitivityAnalysisProcessor):
        self.processor = processor
        
    def create_performance_comparison_chart(self) -> go.Figure:
        """パフォーマンス比較チャート"""
        df = self.processor.processed_data
        if df is None or df.empty:
            return go.Figure()
        
        fig = go.Figure()
        
        # プロフィットファクター
        fig.add_trace(go.Bar(
            name='プロフィットファクター',
            x=df['scenario'],
            y=df['avg_profit_factor'],
            marker_color='lightblue',
            yaxis='y',
            text=[f'{pf:.2f}' for pf in df['avg_profit_factor']],
            textposition='auto'
        ))
        
        # 一貫性比率（第2軸）
        fig.add_trace(go.Scatter(
            name='一貫性比率',
            x=df['scenario'],
            y=df['consistency_ratio'],
            mode='markers+lines',
            marker=dict(size=10, color='red'),
            line=dict(color='red', width=2),
            yaxis='y2'
        ))
        
        fig.update_layout(
            title='シナリオ別パフォーマンス比較',
            xaxis_title='コスト環境',
            yaxis=dict(title='プロフィットファクター', side='left'),
            yaxis2=dict(title='一貫性比率', side='right', overlaying='y', range=[0, 1]),
            legend=dict(x=0.7, y=1),
            height=500
        )
        
        return fig
    
    def create_cost_impact_heatmap(self) -> go.Figure:
        """コスト影響ヒートマップ"""
        df = self.processor.processed_data
        if df is None or df.empty:
            return go.Figure()
        
        # スプレッドとコミッションの組み合わせマトリックス作成
        pivot_pf = df.pivot_table(
            values='avg_profit_factor',
            index='spread_pips',
            columns='commission_pips',
            fill_value=0
        )
        
        fig = go.Figure(data=go.Heatmap(
            z=pivot_pf.values,
            x=[f'{col:.1f}' for col in pivot_pf.columns],
            y=[f'{idx:.1f}' for idx in pivot_pf.index],
            colorscale='RdYlGn',
            text=pivot_pf.values,
            texttemplate='%{text:.2f}',
            textfont={'size': 12},
            colorbar=dict(title='プロフィットファクター')
        ))
        
        fig.update_layout(
            title='コスト影響ヒートマップ（プロフィットファクター）',
            xaxis_title='コミッション (pips)',
            yaxis_title='スプレッド (pips)',
            height=400
        )
        
        return fig
    
    def create_scenario_survival_plot(self) -> go.Figure:
        """シナリオ生存プロット"""
        # TODO: Copilot実装 - 散布図・生存境界線
        pass

class SensitivityExporter:
    """エクスポートクラス（Claude Code設計）"""
    
    def __init__(self, processor: SensitivityAnalysisProcessor):
        self.processor = processor
        
    def export_to_csv(self, output_dir: str = "exports") -> str:
        """CSV形式エクスポート"""
        Path(output_dir).mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sensitivity_analysis_{timestamp}.csv"
        filepath = Path(output_dir) / filename
        
        df = self.processor.processed_data
        if df is not None and not df.empty:
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            return str(filepath)
        else:
            raise ValueError("エクスポートするデータがありません")
    
    def export_to_excel(self, output_dir: str = "exports") -> str:
        """Excel形式エクスポート（複数シート）"""
        Path(output_dir).mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sensitivity_analysis_{timestamp}.xlsx"
        filepath = Path(output_dir) / filename
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # メイン指標
            if self.processor.processed_data is not None:
                self.processor.processed_data.to_excel(writer, sheet_name='パフォーマンス指標', index=False)
            
            # シナリオ比較
            comparison_df = self.processor.calculate_scenario_comparison()
            if not comparison_df.empty:
                comparison_df.to_excel(writer, sheet_name='シナリオ比較', index=False)
            
            # 生データ（要約）
            if self.processor.raw_data:
                summary_data = []
                for scenario in self.processor.raw_data['sensitivity_analysis']:
                    summary_data.append({
                        'scenario': scenario['scenario'],
                        'total_folds': len(scenario.get('wfa_results', [])),
                        'spread_pips': scenario['cost_params']['spread_pips'],
                        'commission_pips': scenario['cost_params']['commission_pips']
                    })
                pd.DataFrame(summary_data).to_excel(writer, sheet_name='概要', index=False)
        
        return str(filepath)
    
    def generate_pdf_report(self, output_dir: str = "exports") -> str:
        """PDF戦略レポート生成"""
        # TODO: Copilot実装 - matplotlib → PDF変換
        pass

class SensitivityDashboard:
    """Streamlitダッシュボード（Claude Code設計）"""
    
    def __init__(self):
        self.processor = SensitivityAnalysisProcessor()
        self.visualizer = SensitivityVisualizer(self.processor)
        self.exporter = SensitivityExporter(self.processor)
        
    def setup_sidebar(self):
        """サイドバー設定"""
        # TODO: Copilot実装 - ファイル選択・フィルター設定
        pass
    
    def display_summary_metrics(self):
        """サマリー指標表示"""
        # TODO: Copilot実装 - st.metrics使用
        pass
    
    def display_interactive_charts(self):
        """インタラクティブチャート表示"""
        # TODO: Copilot実装 - Plotlyチャート埋め込み
        pass
    
    def display_export_section(self):
        """エクスポートセクション"""
        # TODO: Copilot実装 - ダウンロードボタン・形式選択
        pass

def main():
    """メイン実行関数（Claude Code設計 + Copilot実装）"""
    st.set_page_config(
        page_title="コスト耐性戦略 感度分析ダッシュボード",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("🎯 コスト耐性ブレイクアウト戦略 感度分析結果")
    st.markdown("---")
    
    # ダッシュボード初期化
    dashboard = SensitivityDashboard()
    
    # データ読み込み
    if dashboard.processor.load_results():
        # データ処理
        df = dashboard.processor.extract_performance_metrics()
        
        if not df.empty:
            # サマリー指標表示
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("シナリオ数", len(df))
            with col2:
                viable_scenarios = df[df['strategy_viable']].shape[0]
                st.metric("生存可能シナリオ", viable_scenarios)
            with col3:
                best_pf = df['avg_profit_factor'].max()
                st.metric("最高PF", f"{best_pf:.2f}")
            with col4:
                avg_consistency = df['consistency_ratio'].mean()
                st.metric("平均一貫性", f"{avg_consistency:.1%}")
            
            st.markdown("---")
            
            # チャート表示
            col1, col2 = st.columns(2)
            
            with col1:
                st.plotly_chart(dashboard.visualizer.create_performance_comparison_chart(), use_container_width=True)
            
            with col2:
                st.plotly_chart(dashboard.visualizer.create_cost_impact_heatmap(), use_container_width=True)
            
            # データテーブル
            st.subheader("📈 詳細データ")
            st.dataframe(df, use_container_width=True)
            
            # エクスポートセクション
            st.subheader("💾 エクスポート")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📄 CSVエクスポート"):
                    try:
                        filepath = dashboard.exporter.export_to_csv()
                        st.success(f"✅ CSVエクスポート完了: {filepath}")
                    except Exception as e:
                        st.error(f"❌ CSVエクスポートエラー: {e}")
            
            with col2:
                if st.button("📊 Excelエクスポート"):
                    try:
                        filepath = dashboard.exporter.export_to_excel()
                        st.success(f"✅ Excelエクスポート完了: {filepath}")
                    except Exception as e:
                        st.error(f"❌ Excelエクスポートエラー: {e}")
        else:
            st.error("データ処理エラー: 有効な指標が抽出できませんでした")

if __name__ == "__main__":
    main()