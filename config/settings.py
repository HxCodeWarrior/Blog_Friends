# config/settings.py
# author:  ByteWyrm
# date: 2025.5.25 1:20
import os
import yaml

def load():
    # 获取项目根目录（Blog_Friends/）
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, 'config.yml')
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)