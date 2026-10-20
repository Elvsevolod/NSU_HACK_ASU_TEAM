"""Documented ru_maxrss units; unsupported platforms retain raw measurements."""
import sys


def peak_rss(raw,system=None):
    system=sys.platform if system is None else system
    unit='bytes' if system=='darwin' else 'KiB' if system.startswith('linux') else None
    return {'peak_rss_raw':raw,'peak_rss_raw_unit':unit,
            'peak_rss_bytes':raw if unit=='bytes' else raw*1024 if unit=='KiB' else None}
