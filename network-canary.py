#!/usr/bin/env python3
"""
Network Canary - Monitor network connectivity and report downtime to Discord
"""

import subprocess
import time
import requests
from datetime import datetime, timedelta, timezone
import sys
import platform

# Configuration
PING_TARGET = "1.1.1.1"
PING_INTERVAL = 5  # seconds between pings when network is up
PING_TIMEOUT = 3  # seconds to wait for ping response
WEBHOOK_FILE = "webhook-secret"


def load_webhook_url():
	# load webhook url
	try:
		with open(WEBHOOK_FILE, 'r') as f:
			url = f.read().strip()
			if url and not url.startswith("http"):
				print(f"Error: Invalid webhook URL in {WEBHOOK_FILE}")
				sys.exit(1)
			return url
	except FileNotFoundError:
		print(f"Error: {WEBHOOK_FILE} not found")
		sys.exit(1)


def ping(host, timeout):
	# ping a host and return True if reachable, False otherwise
	try:
		system = platform.system().lower()
		
		if system == "windows":
			# Windows: ping -n <count> -w <timeout_ms> <host>
			command = ['ping', '-n', '1', '-w', str(timeout * 1000), host]
		else:
			# macOS and Linux: ping -c <count> -W <timeout_sec> <host>
			# Note: macOS uses -W in milliseconds, Linux uses seconds
			if system == "darwin":  # macOS
				command = ['ping', '-c', '1', '-W', str(timeout * 1000), host]
			else:  # Linux and other Unix-like systems
				command = ['ping', '-c', '1', '-W', str(timeout), host]
		
		result = subprocess.run(
			command,
			stdout=subprocess.DEVNULL,
			stderr=subprocess.DEVNULL,
			timeout=timeout + 1
		)
		return result.returncode == 0
	except subprocess.TimeoutExpired:
		return False
	except Exception as e:
		print(f" !! Ping error: {e}")
		return False


def format_duration(duration):
	total_seconds = int(duration.total_seconds())
	
	hours = total_seconds // 3600
	minutes = (total_seconds % 3600) // 60
	seconds = total_seconds % 60
	
	parts = []
	if hours > 0:
		parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
	if minutes > 0:
		parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
	if seconds > 0 or not parts:
		parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
	
	return ", ".join(parts)


def send_discord_notification(webhook_url, downtime_start, downtime_end, duration):
	duration_str = format_duration(duration)
	
	message = {
		"embeds": [{
			"title": "🌐 Network Restored",
			"description": f"Network connectivity has been restored after being down for **{duration_str}**.",
			"color": 3066993,
			"fields": [
				{
					"name": "Downtime Started",
					"value": downtime_start.strftime("%Y-%m-%d %H:%M:%S"),
					"inline": True
				},
				{
					"name": "Network Restored",
					"value": downtime_end.strftime("%Y-%m-%d %H:%M:%S"),
					"inline": True
				},
				{
					"name": "Total Downtime",
					"value": duration_str,
					"inline": False
				}
			],
			"timestamp": datetime.now(timezone.utc).isoformat()
		}]
	}
	
	try:
		response = requests.post(webhook_url, json=message, timeout=10)
		if response.status_code == 204:
			print(f" ++ Discord notification sent successfully")
			return True
		else:
			print(f" !! Discord notification failed: {response.status_code}")
			return False
	except Exception as e:
		print(f" !! Error sending Discord notification: {e}")
		return False


def monitor_network():
	webhook_url = load_webhook_url()
	
	print(f" ")
	print(f" 🕊️  Network Canary starting...")
	print(f" ")
	print(f" ++ Platform: {platform.system()} {platform.release()}")
	print(f" ++ Monitoring connectivity to {PING_TARGET}")
	print(f" ++ Ping interval: {PING_INTERVAL} seconds")
	print(f" ++ Discord webhook configured")
	print(f" ")
	print("-" * 20)
	print("-" * 20)
	print(f" ")
	
	
	network_is_up = True
	downtime_start = None
	
	while True:
		try:
			is_reachable = ping(PING_TARGET, PING_TIMEOUT)
			current_time = datetime.now()
			
			if is_reachable:
				if not network_is_up:
					# Network just came back up
					downtime_end = current_time
					duration = downtime_end - downtime_start
					
					print(f"\n ++ Network restored at {current_time.strftime('%H:%M:%S')}")
					print(f" ++ Downtime duration: {format_duration(duration)}")
					
					# Send Discord notification
					send_discord_notification(webhook_url, downtime_start, downtime_end, duration)
					
					network_is_up = True
					downtime_start = None
					print("-" * 50)
				else:
					# Network is still up
					print(f" ++ {current_time.strftime('%H:%M:%S')} - Network OK", end='\r')
			else:
				if network_is_up:
					# Network just went down
					network_is_up = False
					downtime_start = current_time
					print(f"\n ++ Network down detected at {current_time.strftime('%H:%M:%S')}")
					print(f" ++ Monitoring downtime...", end='')
				else:
					# Network is still down
					elapsed = current_time - downtime_start
					print(f"\r ++ Network down for: {format_duration(elapsed)}", end='')
			
			time.sleep(PING_INTERVAL)
			
		except KeyboardInterrupt:
			sys.exit(0)
		except Exception as e:
			print(f"\n !! Unexpected error: {e}")
			time.sleep(PING_INTERVAL)


if __name__ == "__main__":
	monitor_network()
