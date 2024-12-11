import os
import json
import shutil
import hashlib
import logging
import sqlite3
from typing import Dict, List, Optional
from datetime import datetime

class Package:
    def __init__(self, name: str, version: str, description: str, dependencies: List[str]):
        self.name = name
        self.version = version
        self.description = description
        self.dependencies = dependencies
        self.installed_date = None
        self.status = "not_installed"

class PackageManager:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.packages_dir = os.path.join(base_dir, "packages")
        self.db_path = os.path.join(base_dir, "packages.db")
        self.setup_directories()
        self.setup_database()
        self.setup_logging()

    def setup_logging(self):
        """Setup logging for package manager"""
        log_dir = os.path.join(self.base_dir, "logs")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        logging.basicConfig(
            filename=os.path.join(log_dir, 'package_manager.log'),
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def setup_directories(self):
        """Create necessary directories"""
        os.makedirs(self.packages_dir, exist_ok=True)

    def setup_database(self):
        """Initialize SQLite database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS packages (
                    name TEXT PRIMARY KEY,
                    version TEXT,
                    description TEXT,
                    dependencies TEXT,
                    installed_date TEXT,
                    status TEXT
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS restore_points (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    description TEXT,
                    packages TEXT
                )
            ''')
            conn.commit()

    def create_restore_point(self, description: str) -> int:
        """Create a system restore point"""
        try:
            installed_packages = self.list_installed_packages()
            packages_json = json.dumps([{
                'name': pkg.name,
                'version': pkg.version,
                'dependencies': pkg.dependencies
            } for pkg in installed_packages])

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO restore_points (date, description, packages)
                    VALUES (?, ?, ?)
                ''', (datetime.now().isoformat(), description, packages_json))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logging.error(f"Error creating restore point: {e}")
            return -1

    def restore_from_point(self, point_id: int) -> bool:
        """Restore system to a previous restore point"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT packages FROM restore_points WHERE id = ?', (point_id,))
                result = cursor.fetchone()
                
                if not result:
                    logging.error(f"Restore point {point_id} not found")
                    return False
                
                packages = json.loads(result[0])
                
                # Uninstall packages not in restore point
                current_packages = self.list_installed_packages()
                for pkg in current_packages:
                    if not any(p['name'] == pkg.name for p in packages):
                        self.uninstall_package(pkg.name)
                
                # Install/downgrade packages from restore point
                for pkg_data in packages:
                    self.install_package(
                        pkg_data['name'],
                        pkg_data['version'],
                        pkg_data['dependencies']
                    )
                
                return True
        except Exception as e:
            logging.error(f"Error restoring from point {point_id}: {e}")
            return False

    def install_package(self, name: str, version: str, dependencies: List[str]) -> bool:
        """Install a package"""
        try:
            # Check dependencies
            for dep in dependencies:
                if not self.is_package_installed(dep):
                    logging.error(f"Missing dependency: {dep}")
                    return False

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO packages
                    (name, version, dependencies, installed_date, status)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    name,
                    version,
                    json.dumps(dependencies),
                    datetime.now().isoformat(),
                    "installed"
                ))
                conn.commit()
            
            logging.info(f"Successfully installed package: {name} v{version}")
            return True
        except Exception as e:
            logging.error(f"Error installing package {name}: {e}")
            return False

    def uninstall_package(self, name: str) -> bool:
        """Uninstall a package"""
        try:
            # Check if any other packages depend on this one
            dependent_packages = self.get_dependent_packages(name)
            if dependent_packages:
                logging.error(f"Cannot uninstall {name}: required by {dependent_packages}")
                return False

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM packages WHERE name = ?', (name,))
                conn.commit()
            
            logging.info(f"Successfully uninstalled package: {name}")
            return True
        except Exception as e:
            logging.error(f"Error uninstalling package {name}: {e}")
            return False

    def get_dependent_packages(self, package_name: str) -> List[str]:
        """Get list of packages that depend on the given package"""
        dependent_packages = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT name, dependencies FROM packages')
                for name, deps_json in cursor.fetchall():
                    deps = json.loads(deps_json)
                    if package_name in deps:
                        dependent_packages.append(name)
        except Exception as e:
            logging.error(f"Error checking dependencies for {package_name}: {e}")
        
        return dependent_packages

    def is_package_installed(self, name: str) -> bool:
        """Check if a package is installed"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT status FROM packages WHERE name = ?
                ''', (name,))
                result = cursor.fetchone()
                return result is not None and result[0] == "installed"
        except Exception as e:
            logging.error(f"Error checking package status: {e}")
            return False

    def list_installed_packages(self) -> List[Package]:
        """Get list of installed packages"""
        packages = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT name, version, description, dependencies, installed_date, status
                    FROM packages WHERE status = 'installed'
                ''')
                for row in cursor.fetchall():
                    pkg = Package(row[0], row[1], row[2], json.loads(row[3]))
                    pkg.installed_date = row[4]
                    pkg.status = row[5]
                    packages.append(pkg)
        except Exception as e:
            logging.error(f"Error listing packages: {e}")
        
        return packages

    def list_restore_points(self) -> List[Dict]:
        """Get list of available restore points"""
        restore_points = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id, date, description FROM restore_points')
                for row in cursor.fetchall():
                    restore_points.append({
                        'id': row[0],
                        'date': row[1],
                        'description': row[2]
                    })
        except Exception as e:
            logging.error(f"Error listing restore points: {e}")
        
        return restore_points

    def verify_package_integrity(self, package_name: str) -> bool:
        """Verify package files integrity"""
        try:
            package_dir = os.path.join(self.packages_dir, package_name)
            if not os.path.exists(package_dir):
                return False

            checksum_file = os.path.join(package_dir, 'checksum.json')
            if not os.path.exists(checksum_file):
                return False

            with open(checksum_file, 'r') as f:
                checksums = json.load(f)

            for file_path, expected_hash in checksums.items():
                full_path = os.path.join(package_dir, file_path)
                if not os.path.exists(full_path):
                    return False
                
                with open(full_path, 'rb') as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                    if file_hash != expected_hash:
                        return False

            return True
        except Exception as e:
            logging.error(f"Error verifying package {package_name}: {e}")
            return False
