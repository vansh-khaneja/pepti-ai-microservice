"""
Server runtime information module
"""
from datetime import datetime
from typing import Optional

# Global variable to store server start time
_server_start_time: Optional[datetime] = None

def set_server_start_time():
    """Set the server start time to current time"""
    global _server_start_time
    _server_start_time = datetime.utcnow()

def get_server_start_time() -> Optional[datetime]:
    """Get the server start time"""
    return _server_start_time

def get_server_uptime() -> Optional[str]:
    """Get server uptime as a human-readable string"""
    if _server_start_time is None:
        return None
    
    uptime = datetime.utcnow() - _server_start_time
    
    # Convert to human-readable format
    total_seconds = int(uptime.total_seconds())
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m {seconds}s"
    elif hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"
