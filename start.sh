#!/bin/bash
cd /home/agent/data/sites/analysis-prompts
export ANALION_PROMPTS_DIR="/home/agent/data/sites/analysis-prompts"
export ANALION_BACKEND="template"
exec python3 engine/main.py >> /home/agent/data/sites/analysis-prompts/backend.log 2>&1
