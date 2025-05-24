import os
import yaml

def load():
    """
    加载配置文件
    :return: 配置字典
    """
    # 获取当前脚本所在目录
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, 'config.yml')
    
    # 检查配置文件是否存在
    if not os.path.exists(config_path):
        print(f"配置文件不存在: {config_path}")
        return {}
    
    # 读取配置文件
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print(f"读取配置文件失败: {e}")
        return {}