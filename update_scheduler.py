import schedule
import threading
import time
from datetime import datetime, timedelta
import logging
from typing import Optional, List, Tuple

class UpdateScheduler:
    def __init__(self, update_manager):
        self.update_manager = update_manager
        self.quiet_hours: List[Tuple[datetime, datetime]] = []
        self.auto_install_delay = 0  # Delay in hours before auto-installing updates
        self.running = False
        self.scheduler_thread = None
        self.setup_logging()

    def setup_logging(self):
        """Setup logging for the scheduler"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            filename='scheduler.log'
        )
        self.logger = logging.getLogger('UpdateScheduler')

    def set_quiet_hours(self, start_time: str, end_time: str):
        """Set quiet hours when updates should not be installed
        
        Args:
            start_time: Start time in 24-hour format (HH:MM)
            end_time: End time in 24-hour format (HH:MM)
        """
        try:
            start = datetime.strptime(start_time, "%H:%M").time()
            end = datetime.strptime(end_time, "%H:%M").time()
            self.quiet_hours = [(start, end)]
            self.logger.info(f"Quiet hours set: {start_time} - {end_time}")
        except ValueError as e:
            self.logger.error(f"Invalid time format: {e}")

    def is_quiet_hours(self) -> bool:
        """Check if current time is within quiet hours"""
        if not self.quiet_hours:
            return False

        current_time = datetime.now().time()
        for start, end in self.quiet_hours:
            if start <= current_time <= end:
                return True
        return False

    def set_auto_install_delay(self, hours: int):
        """Set delay before automatically installing updates
        
        Args:
            hours: Number of hours to wait before installing updates
        """
        self.auto_install_delay = max(0, hours)
        self.logger.info(f"Auto-install delay set to {hours} hours")

    def schedule_update_check(self, time: str):
        """Schedule daily update check at specified time
        
        Args:
            time: Time in 24-hour format (HH:MM)
        """
        schedule.every().day.at(time).do(self._check_and_install_updates)
        self.logger.info(f"Scheduled daily update check at {time}")

    def _check_and_install_updates(self):
        """Check for updates and install if conditions are met"""
        if self.is_quiet_hours():
            self.logger.info("Skipping update check during quiet hours")
            return

        try:
            update_available = self.update_manager.check_for_updates()
            if update_available:
                self.logger.info("Update available")
                if self.auto_install_delay > 0:
                    # Schedule installation after delay
                    install_time = datetime.now() + timedelta(hours=self.auto_install_delay)
                    schedule.every().day.at(install_time.strftime("%H:%M")).do(
                        self._install_update_if_not_quiet
                    ).tag('pending_install')
                    self.logger.info(f"Scheduled update installation for {install_time}")
                else:
                    self._install_update_if_not_quiet()
        except Exception as e:
            self.logger.error(f"Error during update check: {e}")

    def _install_update_if_not_quiet(self):
        """Install update if not in quiet hours"""
        if self.is_quiet_hours():
            self.logger.info("Skipping update installation during quiet hours")
            return False

        try:
            success = self.update_manager.install_pending_update()
            if success:
                self.logger.info("Update installed successfully")
                # Clear any pending installation jobs
                schedule.clear('pending_install')
            return success
        except Exception as e:
            self.logger.error(f"Error during update installation: {e}")
            return False

    def _run_scheduler(self):
        """Run the scheduler loop"""
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

    def start(self):
        """Start the scheduler"""
        if not self.running:
            self.running = True
            self.scheduler_thread = threading.Thread(target=self._run_scheduler)
            self.scheduler_thread.daemon = True
            self.scheduler_thread.start()
            self.logger.info("Scheduler started")

    def stop(self):
        """Stop the scheduler"""
        if self.running:
            self.running = False
            if self.scheduler_thread:
                self.scheduler_thread.join()
            self.logger.info("Scheduler stopped")
