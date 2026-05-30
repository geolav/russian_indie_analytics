# dashboard package
# dashboard package
from .app import main as run_dashboard
from .app_discovery import main as run_discovery

__all__ = ["run_dashboard", "run_discovery"]