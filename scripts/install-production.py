"""Compatibility wrapper for the portable setup command."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from spire.setup import main
if __name__ == "__main__":
    args = sys.argv[1:]
    command = "uninstall" if "--uninstall" in args else "setup"
    sys.argv = [sys.argv[0], command] + [a for a in args if a != "--uninstall"]
    main()
