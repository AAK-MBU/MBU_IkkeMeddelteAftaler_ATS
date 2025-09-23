"""Module to get process arguments"""

import json
import sys


def get_procargs(argname="--procargs"):
    if argname[:2] != "--":
        raise ValueError("argname should being with '--'")
    argv = sys.argv
    try:
        data_index = argv.index(argname) + 1
        raw_data = argv[data_index]
        procargs = json.loads(raw_data)
    except (ValueError, IndexError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Failed to read dict from argv: {e}\n{argv = }") from e
    return procargs
