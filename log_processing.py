#!/usr/bin/env python3
import sys
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from collections import defaultdict, Counter
from PyQt5 import QtCore # Only QtCore needed for QThread and signals
import zipfile
import gzip
import io
import os # For path basename
import pandas as pd

class LogLoaderThread(QtCore.QThread):
    progress_update = QtCore.pyqtSignal(str, str)  # status, detail
    progress_bar_config = QtCore.pyqtSignal(int, int)  # min, max
    progress_bar_update = QtCore.pyqtSignal(int)  # value
    finished_loading = QtCore.pyqtSignal(pd.DataFrame, list)  # log_entries_df, failed_files_summary
    error_occurred = QtCore.pyqtSignal(str)

    def __init__(self, file_path=None, archive_path=None, files_to_process=None):
        super().__init__()
        self.file_path = file_path
        self.archive_path = archive_path
        self.files_to_process = files_to_process
        self.should_stop = False
        self.encodings_to_try = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252']  # Common encodings
        self.datetime_format_for_parsing = '%Y-%m-%d %H:%M:%S'

    def run(self):
        all_log_entries = []
        failed_files_summary = []  # List of (filename, reason) tuples
        try:
            if self.archive_path:
                self.progress_update.emit("Processing archive...", os.path.basename(self.archive_path))
                all_log_entries, failed_files_summary = self._process_archive()
            elif self.file_path:
                self.progress_update.emit("Processing file...", os.path.basename(self.file_path))
                all_log_entries = self._process_single_file(self.file_path)  # Returns list of entries
            else:
                self.error_occurred.emit("No file or archive path specified.");
                return

            if self.should_stop:
                self.progress_update.emit("Loading cancelled.", "");
                return

            if all_log_entries:
                self.progress_update.emit("Sorting entries...", f"{len(all_log_entries)} total")

                # Sort by datetime_obj primarily, then by original datetime string for stability
                def sort_key(entry):
                    dt_obj = entry.get('datetime_obj')
                    # Handle cases where datetime_obj might be min (parse error) or None
                    if isinstance(dt_obj, datetime) and dt_obj != datetime.min: return dt_obj
                    try:  # Fallback to parsing the string again if obj is bad
                        return datetime.strptime(entry.get('datetime', ''), self.datetime_format_for_parsing)
                    except:  # If truly unparseable, sort to the end
                        return datetime.max  # Sort unparseable/invalid dates to the end

                all_log_entries.sort(key=sort_key)

            if not self.should_stop:
                df_log_entries = pd.DataFrame(all_log_entries)
                self.finished_loading.emit(df_log_entries, failed_files_summary)
        except Exception as e:
            self.error_occurred.emit(f"Unexpected error during loading: {str(e)}")

    def _process_archive(self):
        all_entries = []
        failed_files = []  # (filename, reason)
        try:
            with zipfile.ZipFile(self.archive_path, 'r') as zf:
                if self.files_to_process:
                    # If a specific list of files is provided, use it
                    members_to_process = [info for info in zf.infolist() if info.filename in self.files_to_process and not info.is_dir()]
                else:
                    # Fallback to original behavior: find all relevant log files
                    member_infos = [info for info in zf.infolist() if not info.is_dir()]
                    members_to_process = [info for info in member_infos
                                          if os.path.basename(info.filename).startswith(('app', 'error')) and \
                                          (info.filename.endswith('.log.gz') or info.filename.endswith('.log'))]

                if not members_to_process:
                    self.error_occurred.emit(f"No log files to process found in archive.")
                    return [], []

                total_files = len(members_to_process)
                self.progress_bar_config.emit(0, total_files)

                for i, member in enumerate(members_to_process):
                    if self.should_stop: break
                    try:
                        self.progress_update.emit(f"Processing {member.filename}...", f"File {i+1} of {total_files}")
                        with zf.open(member.filename, 'r') as file_in_zip:
                            file_iterator = None
                            # Check if the file is gzipped based on extension
                            if member.filename.endswith('.gz'):
                                self.progress_update.emit(f"Decompressing {member.filename}...", "")
                                file_iterator = gzip.open(file_in_zip, 'rt', encoding='utf-8', errors='replace')
                            else: # Plain text .log file
                                self.progress_update.emit(f"Reading {member.filename}...", "")
                                file_iterator = io.TextIOWrapper(file_in_zip, encoding='utf-8', errors='replace')

                            self.progress_update.emit(f"Parsing {member.filename}...", "")
                            entries = self._parse_log_from_iterator(file_iterator, source_name=member.filename)
                            all_entries.extend(entries)

                    except (gzip.BadGzipFile) as e:
                        failed_files.append((member.filename, f"Not a valid GZip file: {e}"))
                        continue
                    except Exception as e:
                        failed_files.append((member.filename, f"Error: {e}"))
                        continue
                    finally:
                        self.progress_bar_update.emit(i + 1)

        except zipfile.BadZipFile:
            self.error_occurred.emit(f"Error: The file '{os.path.basename(self.archive_path)}' is not a valid ZIP file.")
            self.error_occurred.emit(f"Invalid or corrupted ZIP: {e_bad_zip}");
            return [], []
        except Exception as e_zip_general:  # Other general zip errors
            self.error_occurred.emit(f"Error reading ZIP: {e_zip_general}");
            return [], []
        return all_entries, failed_files

    def _process_single_file(self, file_path_to_process):
        all_entries = []
        is_gz = file_path_to_process.endswith('.log.gz')  # More specific check
        self.progress_bar_config.emit(0, 0)  # Indeterminate for single file for now

        try:
            if is_gz:
                with open(file_path_to_process, 'rb') as f_gz_raw:  # Open raw gz file
                    with gzip.GzipFile(fileobj=f_gz_raw, mode='rb') as decompressed_file:
                        decompressed_bytes = decompressed_file.read()  # Read all bytes
                if not decompressed_bytes: return []  # Empty file

                found_encoding = False
                for enc in self.encodings_to_try:
                    if self.should_stop: break
                    try:
                        text_stream = io.TextIOWrapper(io.BytesIO(decompressed_bytes), encoding=enc, errors='strict')
                        text_stream.readline()  # Test read
                        text_stream.seek(0)  # Reset
                        all_entries = self._parse_log_from_iterator(text_stream,
                                                                    source_name=os.path.basename(file_path_to_process))
                        found_encoding = True;
                        break
                    except:
                        continue  # Try next encoding
                if not found_encoding and not self.should_stop:
                    raise IOError(f"GZ: Could not decode {os.path.basename(file_path_to_process)}")
            else:  # Plain text .log file
                detected_encoding = None
                for enc in self.encodings_to_try:
                    if self.should_stop: break
                    try:
                        with open(file_path_to_process, 'r', encoding=enc) as f_enc_test:
                            f_enc_test.readline()  # Try reading a line
                        detected_encoding = enc;
                        break
                    except:
                        continue  # Try next encoding
                if not detected_encoding: raise IOError(
                    f"TXT: Could not decode {os.path.basename(file_path_to_process)}")

                self.progress_update.emit(f"Parsing (Encoding: {detected_encoding})...", "")
                with open(file_path_to_process, 'r', encoding=detected_encoding) as final_f:
                    all_entries = self._parse_log_from_iterator(final_f,
                                                                source_name=os.path.basename(file_path_to_process))
        except Exception as e:  # Catch all errors from this file processing
            # Re-raise as a more specific exception or handle to pass to error_occurred
            raise Exception(f"Error processing file {os.path.basename(file_path_to_process)}: {e}")
        return all_entries

    def _parse_log_from_iterator(self, file_iterator, source_name=""):
        # Example: 2023-03-15 10:30:00 INFO [com.example.Logger] Message content
        entry_pattern = re.compile(
            r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+'  # Timestamp (Group 1)
            r'(INFO|WARN|ERROR|DEBUG)\s+'  # Log Level (Group 2)
            r'\[(.*?)\]\s+'  # Logger Name in brackets (Group 3)
            r'(.*)'  # Message (Group 4)
        )
        log_entries = []
        current_entry = None
        line_count = 0

        for line_text in file_iterator:
            if self.should_stop: break
            line_count += 1
            if line_count % 20000 == 0:  # Update progress periodically for large files
                self.progress_update.emit(f"Parsing {source_name}...", f"~{line_count // 1000}k lines")

            match = entry_pattern.match(line_text)
            if match:
                if current_entry: log_entries.append(current_entry)  # Save previous entry
                dt_str, lvl, lgr, msg_content = match.groups()
                parsed_dt = datetime.min  # Default for unparseable or error
                try:
                    parsed_dt = datetime.strptime(dt_str, self.datetime_format_for_parsing)
                except ValueError:
                    pass  # Keep parsed_dt as datetime.min if format error

                current_entry = {
                    'datetime': dt_str,
                    'datetime_obj': parsed_dt,
                    'log_level': lvl,
                    'logger_name': lgr,
                    'message_lines': [msg_content.strip()],  # Start with the first line of the message
                    'full_entry': line_text  # Store the raw line that started the entry
                }
            elif current_entry:  # This line is a continuation of the previous message
                current_entry['message_lines'].append(line_text.rstrip('\n'))  # Append and strip only trailing newline
                current_entry['full_entry'] += line_text  # Add to full entry

        if current_entry and not self.should_stop: log_entries.append(current_entry)  # Add the last entry

        # Post-process to join message lines
        for entry in log_entries:
            entry['message'] = '\n'.join(entry['message_lines'])
        return log_entries

    def stop(self):
        self.should_stop = True