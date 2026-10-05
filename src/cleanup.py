"""Sweep orphaned temp PNGs; run periodically by the mcp-rendering-sweep timer."""
import logging

import config
from renderer import cleanup_orphans

if __name__ == "__main__":
    logging.basicConfig(level=config.LOG_LEVEL, format="%(levelname)s - %(message)s")
    for removed in cleanup_orphans():
        print(f"removed {removed}")
