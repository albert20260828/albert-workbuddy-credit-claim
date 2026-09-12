#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""macOS check-in engine for the launchd path.

This is a thin wrapper that delegates to the shared cross-platform claimer
(scripts/claim_api.py) so there is a single implementation to maintain.
The macOS launchd entry (checkin.sh) invokes this file.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "scripts"))

from claim_api import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
