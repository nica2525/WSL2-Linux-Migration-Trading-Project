#!/usr/bin/env python3
"""
JamesORB PWAアイコン生成スクリプト
"""

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("⚠️ PIL (Pillow) がインストールされていません。シンプルなアイコンファイルを作成します。")

import os

def create_simple_icon():
    """シンプルなSVGアイコンを作成"""
    svg_content = '''
<svg width="192" height="192" viewBox="0 0 192 192" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style="stop-color:#2196F3;stop-opacity:1" />
            <stop offset="100%" style="stop-color:#1976D2;stop-opacity:1" />
        </linearGradient>
    </defs>
    
    <!-- 背景 -->
    <rect width="192" height="192" rx="32" fill="url(#bg)"/>
    
    <!-- チャートアイコン -->
    <g transform="translate(48, 48)">
        <!-- 軸 -->
        <line x1="16" y1="80" x2="80" y2="80" stroke="white" stroke-width="3"/>
        <line x1="16" y1="16" x2="16" y2="80" stroke="white" stroke-width="3"/>
        
        <!-- 上昇チャート -->
        <polyline points="16,64 32,48 48,56 64,32 80,40" 
                  stroke="white" stroke-width="4" fill="none" stroke-linecap="round"/>
        
        <!-- ポイント -->
        <circle cx="32" cy="48" r="3" fill="white"/>
        <circle cx="48" cy="56" r="3" fill="white"/>
        <circle cx="64" cy="32" r="3" fill="white"/>
        <circle cx="80" cy="40" r="3" fill="white"/>
    </g>
    
    <!-- ロゴテキスト -->
    <text x="96" y="140" text-anchor="middle" fill="white" font-family="Arial, sans-serif" font-size="24" font-weight="bold">JamesORB</text>
    <text x="96" y="165" text-anchor="middle" fill="rgba(255,255,255,0.8)" font-family="Arial, sans-serif" font-size="12">監視</text>
</svg>
    '''.strip()
    
    return svg_content

def create_pil_icon():
    """PIL使用の高品質アイコンを作成"""
    # 192x192 アイコン作成
    img = Image.new('RGBA', (192, 192), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # グラデーション背景（簡易版）
    for y in range(192):
        alpha = y / 192
        color = (
            int(33 + (25 - 33) * alpha),    # R: 33 -> 25
            int(150 + (118 - 150) * alpha), # G: 150 -> 118  
            int(243 + (210 - 243) * alpha), # B: 243 -> 210
            255
        )
        draw.line([(0, y), (192, y)], fill=color)
    
    # 角丸四角形
    draw.rounded_rectangle([0, 0, 191, 191], radius=32, fill=None, outline=(255, 255, 255, 100), width=2)
    
    # チャートアイコン
    chart_points = [
        (48, 112), (64, 96), (80, 104), (96, 80), (112, 88), (128, 72)
    ]
    
    # チャートライン
    for i in range(len(chart_points) - 1):
        draw.line([chart_points[i], chart_points[i + 1]], fill=(255, 255, 255, 255), width=4)
    
    # チャートポイント
    for point in chart_points:
        draw.ellipse([point[0] - 4, point[1] - 4, point[0] + 4, point[1] + 4], fill=(255, 255, 255, 255))
    
    # 軸
    draw.line([(48, 144), (144, 144)], fill=(255, 255, 255, 255), width=3)  # X軸
    draw.line([(48, 48), (48, 144)], fill=(255, 255, 255, 255), width=3)     # Y軸
    
    try:
        # フォント読み込み（システムフォントを試行）
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # テキスト
    draw.text((96, 160), "JamesORB", fill=(255, 255, 255, 255), font=font_large, anchor="mm")
    draw.text((96, 175), "監視", fill=(255, 255, 255, 200), font=font_small, anchor="mm")
    
    return img

def main():
    icon_dir = "/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Dashboard/static/icons"
    
    global PIL_AVAILABLE
    if PIL_AVAILABLE:
        print("📱 PILを使用して高品質アイコンを作成中...")
        try:
            icon = create_pil_icon()
            icon.save(os.path.join(icon_dir, "icon-192x192.png"), "PNG")
            
            # 他のサイズも作成
            sizes = [72, 96, 128, 144, 152, 384, 512]
            for size in sizes:
                resized = icon.resize((size, size), Image.Resampling.LANCZOS)
                resized.save(os.path.join(icon_dir, f"icon-{size}x{size}.png"), "PNG")
            
            print("✅ PNG アイコンセット作成完了")
            
        except Exception as e:
            print(f"❌ PNG作成エラー: {e}")
            print("🔄 SVGアイコンにフォールバック...")
            PIL_AVAILABLE = False
    
    if not PIL_AVAILABLE:
        print("📱 SVGアイコンを作成中...")
        svg_content = create_simple_icon()
        
        with open(os.path.join(icon_dir, "icon.svg"), "w", encoding="utf-8") as f:
            f.write(svg_content)
        
        # 簡易PNG作成（base64エンコードされたSVG）
        import base64
        svg_b64 = base64.b64encode(svg_content.encode()).decode()
        
        print("✅ SVG アイコン作成完了")
        print("💡 より高品質なアイコンが必要な場合は 'pip install Pillow' を実行してください")

if __name__ == "__main__":
    main()