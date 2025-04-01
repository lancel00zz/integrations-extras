import os
import json
import time
import logging
import socket
from datadog_checks.base import AgentCheck

try:
    from __about__ import __version__
except ImportError:
    __version__ = "unversioned"

class Helloworld2(AgentCheck):
    def check(self, instance):
        # Send heartbeat metric
        self.gauge('helloworld2.heartbeat', 1)

        # Send OK service check
        self.service_check('helloworld2.status', self.OK, message='Desktop status is cool ok')

        # Desktop path
        desktop_path = os.path.expanduser("~/Desktop")
        try:
            file_count = 0
            old_file_count = 0
            very_old_file_count = 0

            now = time.time()
            seven_days = 7 * 24 * 60 * 60
            thirty_days = 30 * 24 * 60 * 60

            for f in os.listdir(desktop_path):
                if f.startswith('.'):
                    continue  # Skip hidden files
                full_path = os.path.join(desktop_path, f)
                if os.path.isfile(full_path) or os.path.isdir(full_path):
                    file_count += 1
                    try:
                        modified_time = os.path.getmtime(full_path)
                        file_age = now - modified_time
                        if file_age > seven_days:
                            old_file_count += 1
                        if file_age > thirty_days:
                            very_old_file_count += 1
                    except Exception as e:
                        self.log.warning(f"Could not get age of {f}: {e}")
        except Exception as e:
            self.log.warning(f"Could not access Desktop: {e}")
            file_count = -1
            old_file_count = -1
            very_old_file_count = -1

        # Emit metrics
        self.gauge('helloworld2.desktop_file_count', file_count)
        self.gauge('helloworld2.desktop_file_count.old', old_file_count)

        host = socket.gethostname()

        # Logging setup
        logger = logging.getLogger('helloworld2')
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            log_file = '/opt/datadog-agent/logs/helloworld2.log'
            file_handler = logging.FileHandler(log_file)
            formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        # State tracking
        state_file = '/opt/datadog-agent/logs/helloworld2_state.json'
        log_this_run = False

        try:
            with open(state_file, 'r') as f:
                state = json.load(f)
            last_count = state.get("last_count")
            last_logged = state.get("last_logged", 0)
        except (FileNotFoundError, json.JSONDecodeError):
            last_count = None
            last_logged = 0

        # Decide whether to log
        if file_count != last_count:
            log_this_run = True
            log_reason = f"File count changed: {last_count} → {file_count} on {host}"
        elif now - last_logged > 43200:
            log_this_run = True
            log_reason = f"No change, but 12h passed since last log. {host} was alive."

        # Log based on file age distribution
        if log_this_run:
            logger.info(f"ℹ️ {log_reason}")

            young_file_count = max(file_count - old_file_count, 0)
            summary_message = f"{very_old_file_count} files older than 30 days. {old_file_count} files older than 7 days. {young_file_count} young files."

            if very_old_file_count > 0:
                logger.critical(summary_message)
            elif old_file_count > 0:
                logger.warning(summary_message)
            else:
                logger.info(summary_message)

            # Save updated state
            try:
                with open(state_file, 'w') as f:
                    json.dump({
                        "last_count": file_count,
                        "last_logged": int(time.time())
                    }, f)
            except Exception as e:
                self.log.warning(f"Could not write state file: {e}")

__version__ = __version__                