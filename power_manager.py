import psutil
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional
import json
import os
from pathlib import Path

@dataclass
class PowerProfile:
    name: str
    description: str
    cpu_max: int  # Maximum CPU usage percentage
    screen_timeout: int  # Screen timeout in minutes
    sleep_timeout: int  # Sleep timeout in minutes
    performance_mode: bool  # True for high performance, False for power saving

class PowerManager:
    def __init__(self):
        self.profiles_dir = Path("power_profiles")
        self.profiles: Dict[str, PowerProfile] = {}
        self.current_profile = "balanced"
        
        # Create profiles directory if it doesn't exist
        self.profiles_dir.mkdir(exist_ok=True)
        
        # Load default profiles
        self._create_default_profiles()
        self.load_profiles()
        
    def _create_default_profiles(self):
        """Create default power profiles"""
        default_profiles = {
            "power_saver": PowerProfile(
                name="power_saver",
                description="Maximizes battery life",
                cpu_max=50,
                screen_timeout=5,
                sleep_timeout=15,
                performance_mode=False
            ),
            "balanced": PowerProfile(
                name="balanced",
                description="Balances performance and battery life",
                cpu_max=80,
                screen_timeout=10,
                sleep_timeout=30,
                performance_mode=False
            ),
            "performance": PowerProfile(
                name="performance",
                description="Maximizes performance",
                cpu_max=100,
                screen_timeout=30,
                sleep_timeout=60,
                performance_mode=True
            )
        }
        
        for profile in default_profiles.values():
            self.save_profile(profile)
    
    def load_profiles(self):
        """Load all power profiles"""
        for profile_file in self.profiles_dir.glob("*.json"):
            try:
                with open(profile_file, "r") as f:
                    data = json.load(f)
                    profile = PowerProfile(**data)
                    self.profiles[profile.name] = profile
            except Exception as e:
                logging.error(f"Error loading profile {profile_file}: {e}")
    
    def save_profile(self, profile: PowerProfile):
        """Save a power profile"""
        profile_path = self.profiles_dir / f"{profile.name}.json"
        try:
            with open(profile_path, "w") as f:
                json.dump(profile.__dict__, f, indent=4)
            self.profiles[profile.name] = profile
            logging.info(f"Saved power profile: {profile.name}")
        except Exception as e:
            logging.error(f"Error saving profile {profile.name}: {e}")
    
    def get_profile(self, profile_name: Optional[str] = None) -> PowerProfile:
        """Get a power profile by name"""
        if not profile_name:
            profile_name = self.current_profile
        return self.profiles.get(profile_name, self.profiles["balanced"])
    
    def set_profile(self, profile_name: str) -> bool:
        """Set the current power profile"""
        if profile_name in self.profiles:
            self.current_profile = profile_name
            self._apply_profile(self.profiles[profile_name])
            logging.info(f"Applied power profile: {profile_name}")
            return True
        logging.error(f"Profile not found: {profile_name}")
        return False
    
    def _apply_profile(self, profile: PowerProfile):
        """Apply power profile settings"""
        try:
            # Set CPU frequency scaling
            if hasattr(psutil, "cpu_freq"):
                current_freq = psutil.cpu_freq()
                if current_freq:
                    max_freq = current_freq.max * (profile.cpu_max / 100)
                    # Note: This might require elevated privileges
                    # Implementation depends on OS support
            
            # Set screen timeout
            # Implementation depends on OS
            
            # Set sleep timeout
            # Implementation depends on OS
            
            # Set performance mode
            # Implementation depends on OS
            
            logging.info(f"Applied power settings for profile: {profile.name}")
        except Exception as e:
            logging.error(f"Error applying power profile: {e}")
    
    def create_custom_profile(
        self,
        name: str,
        description: str,
        cpu_max: int = 80,
        screen_timeout: int = 10,
        sleep_timeout: int = 30,
        performance_mode: bool = False
    ) -> Optional[PowerProfile]:
        """Create a new custom power profile"""
        try:
            if name in ["power_saver", "balanced", "performance"]:
                raise ValueError("Cannot override default profiles")
            
            profile = PowerProfile(
                name=name,
                description=description,
                cpu_max=max(0, min(cpu_max, 100)),  # Clamp between 0-100
                screen_timeout=max(1, screen_timeout),  # Minimum 1 minute
                sleep_timeout=max(1, sleep_timeout),  # Minimum 1 minute
                performance_mode=performance_mode
            )
            
            self.save_profile(profile)
            return profile
        except Exception as e:
            logging.error(f"Error creating power profile: {e}")
            return None
    
    def delete_profile(self, profile_name: str) -> bool:
        """Delete a power profile"""
        if profile_name in ["power_saver", "balanced", "performance"]:
            raise ValueError("Cannot delete default profiles")
        
        profile_path = self.profiles_dir / f"{profile_name}.json"
        try:
            if profile_path.exists():
                profile_path.unlink()
                del self.profiles[profile_name]
                if self.current_profile == profile_name:
                    self.current_profile = "balanced"
                logging.info(f"Deleted power profile: {profile_name}")
                return True
            return False
        except Exception as e:
            logging.error(f"Error deleting profile {profile_name}: {e}")
            return False
    
    def get_battery_status(self) -> Dict:
        """Get current battery status"""
        try:
            battery = psutil.sensors_battery()
            if battery:
                return {
                    "percent": battery.percent,
                    "power_plugged": battery.power_plugged,
                    "time_left": battery.secsleft if battery.secsleft != -1 else None
                }
            return {
                "percent": None,
                "power_plugged": None,
                "time_left": None
            }
        except Exception as e:
            logging.error(f"Error getting battery status: {e}")
            return {
                "percent": None,
                "power_plugged": None,
                "time_left": None
            }
    
    def get_power_consumption(self) -> Dict:
        """Get current power consumption statistics"""
        try:
            return {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_io": psutil.disk_io_counters()._asdict() if hasattr(psutil, "disk_io_counters") else None,
                "network_io": psutil.net_io_counters()._asdict() if hasattr(psutil, "net_io_counters") else None
            }
        except Exception as e:
            logging.error(f"Error getting power consumption: {e}")
            return {}
    
    def get_all_profiles(self) -> List[str]:
        """Get list of all available power profiles"""
        return list(self.profiles.keys())
