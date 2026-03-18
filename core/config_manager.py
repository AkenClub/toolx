import os
import json

class ConfigManager:
    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.config = self.load_config()

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"配置文件读取失败: {e}")
                return self.default_config()
        return self.default_config()

    def default_config(self):
        return {
            "window_size": [900, 600],
            "pinned_plugins": ["quick_copy"],
            "theme": "light"
        }

    def save_config(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"配置文件保存失败: {e}")

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save_config()

    def add_pinned(self, plugin_id):
        pinned = self.get("pinned_plugins", [])
        if plugin_id not in pinned:
            pinned.append(plugin_id)
            self.set("pinned_plugins", pinned)

    def remove_pinned(self, plugin_id):
        pinned = self.get("pinned_plugins", [])
        if plugin_id in pinned:
            pinned.remove(plugin_id)
            self.set("pinned_plugins", pinned)
