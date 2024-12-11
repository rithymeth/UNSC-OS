import json
import os
import logging
from pathlib import Path

class ThemeManager:
    def __init__(self):
        self.themes_dir = Path("themes")
        self.themes = {}
        self.current_theme = "default"
        
        # Create themes directory if it doesn't exist
        self.themes_dir.mkdir(exist_ok=True)
        
        # Default theme definition
        self.default_theme = {
            "name": "default",
            "dark_mode": False,
            "colors": {
                "background": "#ffffff",
                "text": "#000000",
                "primary": "#007acc",
                "secondary": "#e0e0e0",
                "accent": "#0066cc",
                "error": "#ff0000",
                "success": "#00ff00",
                "warning": "#ffff00"
            },
            "fonts": {
                "main": ("Segoe UI", 10),
                "title": ("Segoe UI", 12, "bold"),
                "monospace": ("Consolas", 10)
            }
        }
        
        # Dark theme definition
        self.dark_theme = {
            "name": "dark",
            "dark_mode": True,
            "colors": {
                "background": "#1e1e1e",
                "text": "#ffffff",
                "primary": "#007acc",
                "secondary": "#2d2d2d",
                "accent": "#0066cc",
                "error": "#ff0000",
                "success": "#00ff00",
                "warning": "#ffff00"
            },
            "fonts": {
                "main": ("Segoe UI", 10),
                "title": ("Segoe UI", 12, "bold"),
                "monospace": ("Consolas", 10)
            }
        }
        
        # High contrast theme definition
        self.high_contrast_theme = {
            "name": "high_contrast",
            "dark_mode": True,
            "colors": {
                "background": "#000000",
                "text": "#ffffff",
                "primary": "#ffff00",
                "secondary": "#1a1a1a",
                "accent": "#00ff00",
                "error": "#ff0000",
                "success": "#00ff00",
                "warning": "#ffff00"
            },
            "fonts": {
                "main": ("Segoe UI", 10),
                "title": ("Segoe UI", 12, "bold"),
                "monospace": ("Consolas", 10)
            }
        }
        
        # Load built-in themes
        self.save_theme(self.default_theme)
        self.save_theme(self.dark_theme)
        self.save_theme(self.high_contrast_theme)
        
        # Load all themes
        self.load_themes()

    def load_themes(self):
        """Load all themes from the themes directory"""
        for theme_file in self.themes_dir.glob("*.json"):
            try:
                with open(theme_file, "r") as f:
                    theme = json.load(f)
                    self.themes[theme["name"]] = theme
            except Exception as e:
                logging.error(f"Error loading theme {theme_file}: {e}")

    def save_theme(self, theme):
        """Save a theme to file"""
        theme_path = self.themes_dir / f"{theme['name']}.json"
        try:
            with open(theme_path, "w") as f:
                json.dump(theme, f, indent=4)
            self.themes[theme["name"]] = theme
            logging.info(f"Saved theme: {theme['name']}")
        except Exception as e:
            logging.error(f"Error saving theme {theme['name']}: {e}")

    def delete_theme(self, theme_name):
        """Delete a theme"""
        if theme_name in ["default", "dark", "high_contrast"]:
            raise ValueError("Cannot delete built-in themes")
        
        theme_path = self.themes_dir / f"{theme_name}.json"
        if theme_path.exists():
            theme_path.unlink()
            del self.themes[theme_name]
            if self.current_theme == theme_name:
                self.current_theme = "default"
            logging.info(f"Deleted theme: {theme_name}")

    def get_theme(self, theme_name=None):
        """Get a theme by name, returns default theme if not found"""
        if not theme_name:
            theme_name = self.current_theme
        return self.themes.get(theme_name, self.default_theme)

    def set_theme(self, theme_name):
        """Set the current theme"""
        if theme_name in self.themes:
            self.current_theme = theme_name
            logging.info(f"Applied theme: {theme_name}")
            return True
        logging.error(f"Theme not found: {theme_name}")
        return False

    def create_custom_theme(self, name, colors=None, fonts=None, dark_mode=False):
        """Create a new custom theme"""
        if name in ["default", "dark", "high_contrast"]:
            raise ValueError("Cannot override built-in themes")
        
        theme = {
            "name": name,
            "dark_mode": dark_mode,
            "colors": colors or self.default_theme["colors"].copy(),
            "fonts": fonts or self.default_theme["fonts"].copy()
        }
        
        self.save_theme(theme)
        return theme

    def get_all_themes(self):
        """Get list of all available themes"""
        return list(self.themes.keys())
