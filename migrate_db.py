#!/usr/bin/env python3
"""
Database Migration Management Script

This script provides commands for managing database migrations using Alembic.
"""

import subprocess
import sys
import argparse
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=".")
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print(f"❌ {description} failed:")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ Error during {description}: {e}")
        return False

def create_migration(message):
    """Create a new migration"""
    cmd = [sys.executable, "-m", "alembic", "revision", "--autogenerate", "-m", message]
    return run_command(cmd, f"Creating migration: {message}")

def upgrade_database(revision="head"):
    """Upgrade database to specified revision"""
    cmd = [sys.executable, "-m", "alembic", "upgrade", revision]
    return run_command(cmd, f"Upgrading database to {revision}")

def downgrade_database(revision):
    """Downgrade database to specified revision"""
    cmd = [sys.executable, "-m", "alembic", "downgrade", revision]
    return run_command(cmd, f"Downgrading database to {revision}")

def show_current_revision():
    """Show current database revision"""
    cmd = [sys.executable, "-m", "alembic", "current"]
    return run_command(cmd, "Showing current revision")

def show_migration_history():
    """Show migration history"""
    cmd = [sys.executable, "-m", "alembic", "history"]
    return run_command(cmd, "Showing migration history")

def main():
    parser = argparse.ArgumentParser(description="Database Migration Management")
    parser.add_argument("command", choices=[
        "create", "upgrade", "downgrade", "current", "history", "init"
    ], help="Migration command to run")
    parser.add_argument("-m", "--message", help="Migration message (for create command)")
    parser.add_argument("-r", "--revision", default="head", help="Target revision (for upgrade/downgrade)")
    
    args = parser.parse_args()
    
    if args.command == "create":
        if not args.message:
            print("❌ Migration message is required for create command")
            print("Usage: python migrate_db.py create -m 'Your migration message'")
            sys.exit(1)
        success = create_migration(args.message)
    elif args.command == "upgrade":
        success = upgrade_database(args.revision)
    elif args.command == "downgrade":
        if args.revision == "head":
            print("❌ Specific revision required for downgrade command")
            sys.exit(1)
        success = downgrade_database(args.revision)
    elif args.command == "current":
        success = show_current_revision()
    elif args.command == "history":
        success = show_migration_history()
    elif args.command == "init":
        print("🔄 Initializing database with migrations...")
        success = upgrade_database("head")
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
