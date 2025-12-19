#!/usr/bin/env python3

import subprocess
import platform
import time
import signal
import sys
from datetime import datetime, timedelta
from pathlib import Path
import csv
import socket


PING_TARGETS = [
    "8.8.8.8",
    "1.1.1.1",
    "208.67.222.222"
]

DNS_TEST_DOMAINS = [
    "google.com",
    "cloudflare.com",
    "amazon.com"
]

CHECK_INTERVAL = 2
PING_TIMEOUT = 3
FAILURE_THRESHOLD = 3

LOG_DIR = Path("network_logs")
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S %Z"


class NetworkMonitor:
    
    def __init__(self):
        self.start_time = datetime.now()
        self.is_online = True
        self.current_outage_start = None
        self.consecutive_failures = 0
        
        self.total_checks = 0
        self.successful_checks = 0
        self.failed_checks = 0
        self.outages = []
        self.response_times = []
        
        self.log_dir = LOG_DIR
        self.log_dir.mkdir(exist_ok=True)
        
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"monitor_{timestamp}.log"
        self.csv_file = self.log_dir / f"monitor_{timestamp}.csv"
        
        self._init_csv()
        self._log_event("MONITOR_START", "Network monitoring started")
    
    def _init_csv(self):
        with open(self.csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "Timestamp", "Status", "Target", "Response_Time_ms",
                "Test_Type", "Details"
            ])
    
    def _log_event(self, event_type, message, target="", response_time="", test_type=""):
        timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)
        
        with open(self.log_file, 'a') as f:
            f.write(f"[{timestamp}] {event_type}: {message}\n")
        
        with open(self.csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp, event_type, target, response_time, test_type, message
            ])
    
    def record_check(self, success, target, response_time=None, test_type="PING", details=""):
        self.total_checks += 1
        
        if success:
            self.successful_checks += 1
            self.consecutive_failures = 0
            if response_time is not None:
                self.response_times.append(response_time)
            
            if not self.is_online:
                self._transition_to_online()
            
            self._log_event("SUCCESS", details or "Connection successful", 
                          target, response_time or "", test_type)
        else:
            self.failed_checks += 1
            self.consecutive_failures += 1
            self._log_event("FAILURE", details or "Connection failed", 
                          target, "", test_type)
            
            if self.is_online and self.consecutive_failures >= FAILURE_THRESHOLD:
                self._transition_to_offline()
    
    def _transition_to_offline(self):
        self.is_online = False
        self.current_outage_start = datetime.now()
        self._log_event("OUTAGE_START", 
                       f"Network outage detected after {FAILURE_THRESHOLD} consecutive failures")
        print(f"\nOUTAGE DETECTED at {self.current_outage_start.strftime(TIMESTAMP_FORMAT)}")
    
    def _transition_to_online(self):
        self.is_online = True
        outage_end = datetime.now()
        duration = outage_end - self.current_outage_start
        
        self.outages.append({
            'start': self.current_outage_start,
            'end': outage_end,
            'duration': duration
        })
        
        self._log_event("OUTAGE_END", 
                       f"Network restored. Outage duration: {self._format_duration(duration)}")
        print(f"Connection restored at {outage_end.strftime(TIMESTAMP_FORMAT)}")
        print(f"Outage lasted: {self._format_duration(duration)}\n")
        
        self.current_outage_start = None
    
    @staticmethod
    def _format_duration(td):
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{seconds}s")
        
        return " ".join(parts)
    
    def generate_report(self):
        end_time = datetime.now()
        total_runtime = end_time - self.start_time
        
        if not self.is_online and self.current_outage_start:
            ongoing_duration = end_time - self.current_outage_start
            self.outages.append({
                'start': self.current_outage_start,
                'end': end_time,
                'duration': ongoing_duration,
                'ongoing': True
            })
        
        total_outage_time = sum((o['duration'] for o in self.outages), timedelta())
        total_uptime = total_runtime - total_outage_time
        uptime_percentage = (total_uptime.total_seconds() / total_runtime.total_seconds() * 100) if total_runtime.total_seconds() > 0 else 0
        
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        
        report = []
        report.append("=" * 80)
        report.append("NETWORK MONITORING REPORT")
        report.append("=" * 80)
        report.append("")
        report.append("MONITORING PERIOD")
        report.append(f"  Start Time:     {self.start_time.strftime(TIMESTAMP_FORMAT)}")
        report.append(f"  End Time:       {end_time.strftime(TIMESTAMP_FORMAT)}")
        report.append(f"  Total Duration: {self._format_duration(total_runtime)}")
        report.append("")
        report.append("CONNECTION SUMMARY")
        report.append(f"  Total Checks:       {self.total_checks:,}")
        report.append(f"  Successful Checks:  {self.successful_checks:,} ({self.successful_checks/self.total_checks*100:.2f}%)" if self.total_checks > 0 else "  Successful Checks:  0")
        report.append(f"  Failed Checks:      {self.failed_checks:,} ({self.failed_checks/self.total_checks*100:.2f}%)" if self.total_checks > 0 else "  Failed Checks:      0")
        report.append(f"  Avg Response Time:  {avg_response_time:.1f} ms")
        report.append("")
        report.append("UPTIME STATISTICS")
        report.append(f"  Total Uptime:       {self._format_duration(total_uptime)} ({uptime_percentage:.2f}%)")
        report.append(f"  Total Downtime:     {self._format_duration(total_outage_time)}")
        report.append(f"  Number of Outages:  {len(self.outages)}")
        report.append("")
        
        if self.outages:
            report.append("OUTAGE DETAILS")
            report.append("-" * 80)
            for i, outage in enumerate(self.outages, 1):
                ongoing_marker = " (ONGOING)" if outage.get('ongoing') else ""
                report.append(f"  Outage #{i}{ongoing_marker}")
                report.append(f"    Start:    {outage['start'].strftime(TIMESTAMP_FORMAT)}")
                report.append(f"    End:      {outage['end'].strftime(TIMESTAMP_FORMAT)}")
                report.append(f"    Duration: {self._format_duration(outage['duration'])}")
                report.append("")
            
            if len(self.outages) > 1:
                durations = [o['duration'].total_seconds() for o in self.outages]
                avg_outage = sum(durations) / len(durations)
                max_outage = max(durations)
                min_outage = min(durations)
                
                report.append("  Outage Statistics")
                report.append(f"    Average Duration: {self._format_duration(timedelta(seconds=avg_outage))}")
                report.append(f"    Longest Outage:   {self._format_duration(timedelta(seconds=max_outage))}")
                report.append(f"    Shortest Outage:  {self._format_duration(timedelta(seconds=min_outage))}")
                report.append("")
        
        report.append("=" * 80)
        report.append("LOG FILES")
        report.append(f"  Detailed Log: {self.log_file}")
        report.append(f"  CSV Data:     {self.csv_file}")
        report.append("=" * 80)
        
        report_text = "\n".join(report)
        
        report_file = self.log_dir / f"report_{end_time.strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w') as f:
            f.write(report_text)
        
        print("\n" + report_text)
        print(f"\nReport saved to: {report_file}")


def ping_host(host, timeout=PING_TIMEOUT):
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    timeout_param = '-w' if platform.system().lower() == 'windows' else '-W'
    size_param = '-l' if platform.system().lower() == 'windows' else '-s'
    
    command = ['ping', param, '1', size_param, '32', timeout_param, str(timeout), host]
    
    try:
        output = subprocess.check_output(
            command,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            timeout=timeout + 1
        )
        
        if platform.system().lower() == 'windows':
            if 'time=' in output or 'time<' in output:
                for line in output.split('\n'):
                    if 'time' in line.lower():
                        try:
                            time_str = line.split('time')[1].split()[0]
                            time_str = time_str.replace('=', '').replace('<', '').replace('ms', '')
                            return True, float(time_str)
                        except (IndexError, ValueError):
                            pass
        else:
            if 'time=' in output:
                for line in output.split('\n'):
                    if 'time=' in line:
                        try:
                            time_str = line.split('time=')[1].split()[0]
                            return True, float(time_str)
                        except (IndexError, ValueError):
                            pass
        return True, None
    
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False, None


def test_dns_resolution(domain, timeout=PING_TIMEOUT):
    try:
        socket.setdefaulttimeout(timeout)
        socket.gethostbyname(domain)
        return True
    except (socket.gaierror, socket.timeout):
        return False


def perform_connectivity_test(monitor):
    results = []
    for target in PING_TARGETS:
        success, response_time = ping_host(target)
        results.append(success)
        monitor.record_check(success, target, response_time, "ICMP_PING")
        
        if success:
            break
        time.sleep(0.5)
    
    if not any(results):
        for domain in DNS_TEST_DOMAINS[:2]:
            success = test_dns_resolution(domain)
            results.append(success)
            monitor.record_check(success, domain, test_type="DNS_RESOLUTION")
            
            if success:
                break
            time.sleep(0.5)
    
    return any(results)


def end_signal(signum, frame):
    print("\n\nMonitoring stopped by user")
    monitor.generate_report()
    sys.exit(0)


if __name__ == "__main__":
    print("=" * 80)
    print("NETWORK UPTIME MONITOR")
    print("=" * 80)
    print(f"Monitoring started at {datetime.now().strftime(TIMESTAMP_FORMAT)}")
    print(f"Check interval: {CHECK_INTERVAL} seconds")
    print(f"Test targets: {', '.join(PING_TARGETS)}")
    print(f"Logs directory: {LOG_DIR.absolute()}")
    print("\nPress Ctrl+C to stop monitoring and generate report")
    print("=" * 80)
    print()
    
    monitor = NetworkMonitor()
    
    signal.signal(signal.SIGINT, end_signal)
    
    try:
        while True:
            perform_connectivity_test(monitor)
            time.sleep(CHECK_INTERVAL)
    
    except KeyboardInterrupt:

        end_signal(None, None)
