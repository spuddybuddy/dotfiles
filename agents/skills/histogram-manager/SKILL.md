---
name: histogram-manager
description: Identifies and extends expiring UMA histograms in Chromium XML files. Use when you need to audit histograms for specific features (e.g., Cast, MediaRouter) and extend their expiry by a year.
---

# Histogram Manager

This skill helps automate the tedious process of finding and extending expiring UMA histograms.

## Core Workflows

### 1. Identify Expiring Histograms
Use the `scripts/manage_histograms.py` script with the `--audit` flag to find histograms that have already expired or are expiring soon (within 90 days).

### 2. Extend Histograms
Use the `scripts/manage_histograms.py` script with the `--extend` flag to automatically update the `expires_after` attribute for a set of histograms.

## Usage Example

To audit "Cast" histograms:
```bash
python3 scripts/manage_histograms.py --audit --filter "Cast" --files tools/metrics/histograms/metadata/media/histograms.xml
```

To extend "MediaRouter" histograms in all metadata files:
```bash
python3 scripts/manage_histograms.py --extend --filter "MediaRouter" --files tools/metrics/histograms/metadata/media/histograms.xml tools/metrics/histograms/metadata/others/histograms.xml
```

## Best Practices
- **Verify before extend**: Always run an audit first to confirm which histograms will be affected.
- **Incremental commits**: Extend histograms in a separate commit from cleanup code.
- **Format after change**: Always run `git cl format` on the modified XML files.
