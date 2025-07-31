#!/bin/bash
# PostToolUse Hook動作確認テスト
echo "$(date): Hook executed - Args: $*" >> /tmp/hook_test.log
echo "Environment variables:" >> /tmp/hook_test.log
env | grep -E "(CLAUDE|GEMINI|MCP)" >> /tmp/hook_test.log
echo "---" >> /tmp/hook_test.log
