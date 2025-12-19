# Network Uptime Monitor

A Python tool for monitoring network connectivity with detailed logging.

## What it does

- Pings multiple DNS servers (Google, Cloudflare, OpenDNS) every 2 seconds
- Logs all connectivity checks with timestamps
- Tracks outages with exact start/end times
- Generates a detailed report when stopped

## Usage
```bash
python Downtime-v2.py
```

Press `Ctrl+C` to stop monitoring and generate the report.

## Output

Creates a `network_logs/` directory with:
- Text log file with all events
- CSV file for data analysis
- Final report with uptime statistics

## Requirements

- Python 3.6+
- No external dependencies (uses standard library only)

## Configuration

Edit these variables at the top of the script:
- `CHECK_INTERVAL` - seconds between checks (default: 2)
- `PING_TIMEOUT` - timeout for ping responses (default: 3)
- `FAILURE_THRESHOLD` - consecutive failures before declaring outage (default: 3)
