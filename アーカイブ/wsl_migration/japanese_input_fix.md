# 日本語入力問題の解決方法

## 🚨 問題：WSL環境でWindows側のかな変換ボタンを押さないと日本語入力できない

### 解決方法1：VSCode設定による対処

1. **VSCodeの設定を開く**
   - `Ctrl + ,` で設定を開く
   - 検索バーで「input method」を検索

2. **Input Method設定を変更**
   ```json
   {
       "keyboard.dispatch": "keyCode",
       "terminal.integrated.allowChords": false,
       "terminal.integrated.commandsToSkipShell": [
           "language-status.show"
       ]
   }
   ```

3. **User Settings（settings.json）に追加**
   ```json
   {
       "terminal.integrated.detectLocale": "auto",
       "terminal.integrated.inheritEnv": true,
       "terminal.integrated.profiles.linux": {
           "bash": {
               "path": "bash",
               "args": [],
               "env": {
                   "LANG": "ja_JP.UTF-8",
                   "LC_ALL": "ja_JP.UTF-8"
               }
           }
       }
   }
   ```

### 解決方法2：WSL環境設定による対処

1. **WSL内で日本語ロケールを設定**
   ```bash
   sudo apt update
   sudo apt install language-pack-ja
   sudo locale-gen ja_JP.UTF-8
   export LANG=ja_JP.UTF-8
   export LC_ALL=ja_JP.UTF-8
   ```

2. **~/.bashrcに追加**
   ```bash
   echo 'export LANG=ja_JP.UTF-8' >> ~/.bashrc
   echo 'export LC_ALL=ja_JP.UTF-8' >> ~/.bashrc
   source ~/.bashrc
   ```

### 解決方法3：Windows Terminal設定による対処

1. **Windows Terminalの設定を開く**
   - `Ctrl + ,` で設定を開く
   - WSLプロファイルを選択

2. **コマンドライン設定を修正**
   ```json
   {
       "commandline": "wsl.exe -d Ubuntu",
       "fontFace": "MS Gothic",
       "fontSize": 12,
       "startingDirectory": "//wsl$/Ubuntu/home/trader"
   }
   ```

### 解決方法4：IME設定による対処

1. **Windows IME設定**
   - Windowsキー + X → 設定
   - 時刻と言語 → 言語
   - 日本語 → オプション
   - Microsoft IME → オプション

2. **詳細設定で「アプリごとに異なる入力方式を設定する」を無効化**

### 解決方法5：Claude Code固有の対処

1. **Claude Codeの設定ファイルを編集**
   ```bash
   mkdir -p ~/.claude
   cat > ~/.claude/terminal.json << 'EOF'
   {
       "terminal": {
           "shell": "/bin/bash",
           "env": {
               "LANG": "ja_JP.UTF-8",
               "LC_ALL": "ja_JP.UTF-8"
           }
       }
   }
   EOF
   ```

2. **Claude Code再起動**
   - 完全にClaude Codeを終了
   - WSL内で claude-code を再起動

## 🔧 即効性のある暫定対処法

### Windows側での対処
1. **Alt + `（半角/全角）キー** を試す
2. **Ctrl + Space** で入力方式切り替え
3. **Windows + Space** で入力方式切り替え

### WSL/Linux側での対処
1. **fcitx5のインストール**
   ```bash
   sudo apt install fcitx5 fcitx5-mozc
   ```

2. **環境変数の設定**
   ```bash
   export GTK_IM_MODULE=fcitx
   export QT_IM_MODULE=fcitx
   export XMODIFIERS=@im=fcitx
   ```

## 📋 推奨順序

1. **まず試す：** 解決方法1（VSCode設定）
2. **次に試す：** 解決方法4（IME設定）
3. **最後に試す：** 解決方法2（WSL環境設定）

## 🚀 自動化スクリプト

以下のスクリプトで自動設定：
```bash
./japanese_input_setup.sh
```