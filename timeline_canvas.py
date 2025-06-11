#!/usr/bin/env python3
import sys
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from collections import defaultdict, Counter
from PyQt5 import QtWidgets, QtGui, QtCore
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
import numpy as np
from matplotlib.ticker import PercentFormatter
import os # For path basename (though not directly used here, good to keep if future needs)
import pandas as pd


class TimelineCanvas(FigureCanvas):
    bar_clicked = QtCore.pyqtSignal(datetime, datetime)
    time_range_updated = QtCore.pyqtSignal(float, float)

    def __init__(self, parent=None):
        self.figure = Figure(figsize=(12, 4), dpi=90)
        super().__init__(self.figure)
        self.setParent(parent)
        self.ax = self.figure.add_subplot(111)
        self.log_data_cache = pd.DataFrame()
        self.time_groups_cache = None
        self.current_selected_message_types = set()
        self.current_time_granularity = 'minute'  # Default
        self.bars_render_data = []
        self.hover_annotation = None
        self.last_hovered_bar_info = None
        self.full_time_min_num = None
        self.full_time_max_num = None
        self.current_xlim_cache = None
        self.update_timer = QtCore.QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self._do_delayed_plot_update)
        self.pending_xlim_override = None

        self.mpl_connect('button_press_event', self.on_click)
        self.mpl_connect('motion_notify_event', self.on_hover)
        self.mpl_connect('axes_leave_event', self.on_leave_axes)

    def set_full_log_data(self, log_entries):
        self.log_data_cache = log_entries
        self.time_groups_cache = None

    def update_display_config(self, selected_message_types, time_granularity):
        config_changed = (self.current_selected_message_types != selected_message_types or
                          self.current_time_granularity != time_granularity)
        self.current_selected_message_types = selected_message_types
        self.current_time_granularity = time_granularity
        if config_changed:
            self.time_groups_cache = None
        self.plot_timeline(xlim_override=self.current_xlim_cache if not config_changed else None)

    def _get_or_prepare_time_groups(self):
        if self.time_groups_cache is not None:
            return self.time_groups_cache

        if self.log_data_cache.empty or not self.current_selected_message_types:
            self.time_groups_cache = {}
            return self.time_groups_cache

        # Filter entries based on selected message types
        filtered_df = self.log_data_cache[self.log_data_cache['logger_name'].isin(self.current_selected_message_types)]

        if filtered_df.empty:
            self.time_groups_cache = {}
            return self.time_groups_cache

        # Use a copy to avoid SettingWithCopyWarning
        df = filtered_df.copy()
        df.dropna(subset=['datetime_obj'], inplace=True)

        if df.empty:
            self.time_groups_cache = {}
            return self.time_groups_cache

        # Round the datetimes based on granularity
        dts = df['datetime_obj']
        if self.current_time_granularity == 'day':
            rounded_time_series = dts.dt.floor('D')
        elif self.current_time_granularity == 'hour':
            rounded_time_series = dts.dt.floor('h')
        else:  # 'minute'
            rounded_time_series = dts.dt.floor('T')
        
        # Group by the rounded time and logger name, then count occurrences
        grouped = df.groupby([rounded_time_series, 'logger_name']).size().unstack(fill_value=0)
        
        # Convert to the nested defaultdict structure expected by the rest of the code
        time_groups = defaultdict(lambda: defaultdict(int))
        for timestamp, row in grouped.iterrows():
            for logger_name, count in row.items():
                if count > 0:
                    time_groups[timestamp.to_pydatetime()][logger_name] = count
        
        self.time_groups_cache = time_groups
        return self.time_groups_cache

    def plot_timeline(self, xlim_override=None):
        if xlim_override is not None:
            self.pending_xlim_override = xlim_override
        else:
            self.pending_xlim_override = None

        self.update_timer.stop()
        self.update_timer.start(50)  # Debounce plot updates

    def _do_delayed_plot_update(self):
        xlim_override = self.pending_xlim_override
        time_groups = self._get_or_prepare_time_groups()

        self.ax.clear()
        self.bars_render_data = []  # Clear previous bar artist references

        if self.hover_annotation:  # Clean up old annotation
            try:
                self.hover_annotation.remove()
            except (ValueError, AttributeError):  # Catch if already removed or invalid
                pass
            finally:
                self.hover_annotation = None
        self.last_hovered_bar_info = None

        if not time_groups:
            self.draw_idle()
            if xlim_override is None:  # Only update range if it's a full plot, not a zoom/pan
                self.time_range_updated.emit(0, 0)
            self.current_xlim_cache = self.ax.get_xlim()
            return

        times = sorted(time_groups.keys())
        message_types_to_plot = list(self.current_selected_message_types)
        x_pos = mdates.date2num(times)

        is_full_data_or_config_update = (xlim_override is None)
        if is_full_data_or_config_update:  # Recalculate full time range only on new data/config
            if x_pos.size > 0:
                self.full_time_min_num = x_pos[0]
                # Calculate end of the last interval for max range
                last_time_end_obj = self.get_interval_end_time(times[-1])
                self.full_time_max_num = mdates.date2num(last_time_end_obj)
                self.time_range_updated.emit(self.full_time_min_num, self.full_time_max_num)
            else:
                self.full_time_min_num = None
                self.full_time_max_num = None
                self.time_range_updated.emit(0, 0)

        bar_width_factor = 0.7
        bar_width = self._calculate_bar_width(times, x_pos, bar_width_factor)

        # Generate bar data for rendering and hover/click detection
        temp_bars_data, _ = self._generate_timeline_bars(
            times, x_pos, time_groups, message_types_to_plot, bar_width
        )
        self.bars_render_data = list(reversed(temp_bars_data))  # Reversed for hover priority (topmost bar gets hover)

        self._configure_axes(xlim_override)  # Pass xlim_override to configure axes before drawing

        handles, labels = self.ax.get_legend_handles_labels()
        if handles and labels:
            self.ax.legend(handles, labels, bbox_to_anchor=(1.05, 1), loc='upper left', fontsize='small')

        self.ax.grid(True, alpha=0.3)
        try:
            self.figure.tight_layout(rect=[0, 0, 0.85, 1])  # Adjust for legend
        except (ValueError, RuntimeError):  # Catch potential layout errors
            try:
                self.figure.tight_layout()
            except (ValueError, RuntimeError):
                pass  # Give up on tight_layout if it fails twice
        self.current_xlim_cache = self.ax.get_xlim()  # Cache the new xlim
        self.draw_idle()

    def _calculate_bar_width(self, times, x_pos, bar_width_factor):
        bar_width = 0.001  # Default minimum
        if len(times) > 1:
            min_interval_width = np.min(np.diff(x_pos)) if len(x_pos) > 1 else 0.1  # Use np.diff
            bar_width = min_interval_width * bar_width_factor
        elif len(times) == 1:  # Single data point
            deltas = {'minute': timedelta(minutes=1),
                      'hour': timedelta(hours=1), 'day': timedelta(days=1)}
            delta_td = deltas.get(self.current_time_granularity, timedelta(minutes=1))  # Default to minute
            # Convert timedelta to matplotlib numeric width
            base_dt = datetime(2000, 1, 1)  # Arbitrary base for delta calculation
            granularity_width_num = mdates.date2num(base_dt + delta_td) - mdates.date2num(base_dt)
            bar_width = granularity_width_num * bar_width_factor
        return max(bar_width, 0.0001)  # Ensure a very small minimum to avoid zero width

    def _generate_timeline_bars(self, times, x_pos, time_groups, message_types_to_plot, bar_width):
        temp_bars_data = []
        bars_collections_for_legend = []  # To collect artists for the legend
        if not times: return temp_bars_data, bars_collections_for_legend

        if len(message_types_to_plot) > 10:  # Aggregate if too many types for clarity
            total_counts = [sum(time_groups[t].get(mt, 0) for mt in message_types_to_plot) for t in times]
            bars_collection = self.ax.bar(x_pos, total_counts, bar_width, color='steelblue', alpha=0.7,
                                          label=f'All Messages ({len(message_types_to_plot)} types)')
            bars_collections_for_legend.append(bars_collection)
            for bar_artist, t, count in zip(bars_collection, times, total_counts):
                if count > 0:
                    temp_bars_data.append({'bar': bar_artist, 'time_start': t,
                                           'time_end': self.get_interval_end_time(t),
                                           'message_type': f'All Selected ({len(message_types_to_plot)} types)',
                                           'count': count})
        else:  # Stacked bar chart for fewer types
            data_matrix = [[time_groups[t].get(mt, 0) for t in times] for mt in message_types_to_plot]
            bottom_values = np.zeros(len(times))
            num_plot_types = len(message_types_to_plot) if message_types_to_plot else 1  # Avoid div by zero if no types
            colors = plt.cm.Set3(np.linspace(0, 1, max(1, num_plot_types)))  # Use a colormap

            for i, (msg_type, counts_for_type) in enumerate(zip(message_types_to_plot, data_matrix)):
                color_idx = i % len(colors) if (colors.ndim > 0 and colors.size > 0) else 0
                current_color = colors[
                    color_idx] if colors.ndim > 1 else colors  # Handle single color case from colormap
                bars_collection = self.ax.bar(x_pos, counts_for_type, bar_width, bottom=bottom_values, label=msg_type,
                                              color=current_color, alpha=0.7)
                bars_collections_for_legend.append(bars_collection)
                bottom_values += np.array(counts_for_type)  # Ensure it's an array for addition
                for bar_artist, t, count_val in zip(bars_collection, times, counts_for_type):
                    if count_val > 0:
                        temp_bars_data.append({'bar': bar_artist, 'time_start': t,
                                               'time_end': self.get_interval_end_time(t),
                                               'message_type': msg_type, 'count': count_val})
        return temp_bars_data, bars_collections_for_legend

    def _configure_axes(self, xlim_override):
        # Set x-axis limits first, as they might influence formatter choice
        if xlim_override and self.full_time_min_num is not None and self.full_time_max_num is not None:
            eff_min = max(xlim_override[0], self.full_time_min_num)
            eff_max = min(xlim_override[1], self.full_time_max_num)
            if eff_min < eff_max:
                self.ax.set_xlim(eff_min, eff_max)
            elif self.full_time_min_num < self.full_time_max_num:  # Fallback to full range if override is invalid
                self.ax.set_xlim(self.full_time_min_num, self.full_time_max_num)
        elif self.full_time_min_num is not None and self.full_time_max_num is not None and \
                self.full_time_min_num < self.full_time_max_num:
            self.ax.set_xlim(self.full_time_min_num, self.full_time_max_num)
        # else: xlim will be auto-determined by matplotlib if no data/range set previously

        locator = mdates.AutoDateLocator(maxticks=12, minticks=4)
        self.ax.xaxis.set_major_locator(locator)

        view_min_num, view_max_num = self.ax.get_xlim()  # Get current, possibly just set, limits
        span_in_days = view_max_num - view_min_num

        if self.current_time_granularity == 'day':
            formatter = mdates.DateFormatter('%Y-%m-%d')
        elif self.current_time_granularity == 'hour':
            if span_in_days > 1.8:  # More than ~1.8 days visible
                formatter = mdates.DateFormatter('%b %d %H:%M')
            else:
                formatter = mdates.DateFormatter('%H:%M')
        elif self.current_time_granularity == 'minute':
            if span_in_days > 1.8:  # More than ~1.8 days visible
                formatter = mdates.DateFormatter('%b %d %H:%M')  # Date and time, no seconds
            # elif span_in_days > 0.1: # More than ~2.4 hours visible
            #     formatter = mdates.DateFormatter('%H:%M:%S')
            else:  # Less than ~1.8 days, show seconds
                formatter = mdates.DateFormatter('%H:%M:%S')
        else:  # Fallback (should not be 'second' anymore if UI restricts it)
            formatter = mdates.DateFormatter('%H:%M:%S')

        self.ax.xaxis.set_major_formatter(formatter)
        plt.setp(self.ax.get_xticklabels(), rotation=45, ha="right")
        self.ax.set_xlabel('Time');
        self.ax.set_ylabel('Message Count')
        self.ax.set_title('Log Messages Timeline')

    def set_time_window_from_sliders(self, view_min_num, view_max_num):
        if self.full_time_min_num is None or self.full_time_max_num is None: return

        # Ensure view window is within the full data range
        view_min_num = max(view_min_num, self.full_time_min_num)
        view_max_num = min(view_max_num, self.full_time_max_num)

        # Prevent excessively small zoom windows that might cause issues
        min_sensible_width_ratio = 0.0001  # e.g., 0.01% of total span
        min_absolute_width = (self.full_time_max_num - self.full_time_min_num) * min_sensible_width_ratio \
            if self.full_time_max_num > self.full_time_min_num else 0.00001  # A tiny default if span is zero

        if view_max_num - view_min_num < min_absolute_width:
            current_mid = (view_min_num + view_max_num) / 2
            view_min_num = current_mid - min_absolute_width / 2
            view_max_num = current_mid + min_absolute_width / 2
            # Re-clamp to full range after adjustment
            view_min_num = max(view_min_num, self.full_time_min_num)
            view_max_num = min(view_max_num, self.full_time_max_num)
            # If still too small (e.g. at the very edge of the range and min_absolute_width is large)
            if view_max_num - view_min_num < min_absolute_width:
                if view_min_num + min_absolute_width <= self.full_time_max_num:
                    view_max_num = view_min_num + min_absolute_width
                else:  # At the very end of the range
                    view_min_num = self.full_time_max_num - min_absolute_width
                    view_max_num = self.full_time_max_num

        current_xlim = self.ax.get_xlim()
        # Check if update is actually needed and window is valid
        if (view_min_num < view_max_num and
                (abs(current_xlim[0] - view_min_num) > 1e-9 or  # Use tolerance for float comparison
                 abs(current_xlim[1] - view_max_num) > 1e-9)):
            self.plot_timeline(xlim_override=(view_min_num, view_max_num))

    def get_interval_end_time(self, time_start):
        if not isinstance(time_start, datetime): return time_start + timedelta(minutes=1)  # Default fallback
        granularity_deltas = {'minute': timedelta(minutes=1),
                              'hour': timedelta(hours=1), 'day': timedelta(days=1)}
        return time_start + granularity_deltas.get(self.current_time_granularity, timedelta(minutes=1))

    def on_click(self, event):
        if event.inaxes != self.ax: return
        # Iterate in original order for stacked bars (bottom-most part of stack if clicked there)
        # self.bars_render_data is already reversed for hover (top-most).
        # For click, matplotlib's pick event or contains usually handles stacking okay if artists are distinct.
        # If self.bars_render_data was reversed for hover, we might need to iterate original or check more carefully.
        # Let's assume reversed (for hover) is fine for click too, as it checks top-most first.
        for bar_data in reversed(self.bars_render_data):  # Check top-most rendered bar first
            try:
                if bar_data['bar'].contains(event)[0]:
                    self.bar_clicked.emit(bar_data['time_start'], bar_data['time_end'])
                    return  # Process first match
            except (AttributeError, KeyError, RuntimeError):  # Bar might be invalid or removed
                continue

    def on_hover(self, event):
        if event.inaxes != self.ax:
            if self.hover_annotation and self.hover_annotation.get_visible():
                try:
                    self.hover_annotation.set_visible(False);
                    self.draw_idle()
                except (AttributeError, RuntimeError):
                    pass  # Annotation might be stale
            self.last_hovered_bar_info = None
            return

        hovered_bar_info = None
        # self.bars_render_data is already reversed for hover priority
        for b_info in self.bars_render_data:
            try:
                if b_info['bar'].contains(event)[0]:
                    hovered_bar_info = b_info;
                    break
            except (AttributeError, KeyError, RuntimeError):  # Bar might be invalid
                continue

        if hovered_bar_info:
            if hovered_bar_info == self.last_hovered_bar_info:  # Still on the same bar
                if self.hover_annotation and not self.hover_annotation.get_visible():
                    try:
                        self.hover_annotation.set_visible(True);
                        self.draw_idle()
                    except (AttributeError, RuntimeError):
                        pass
                return  # No change needed if already visible

            self.last_hovered_bar_info = hovered_bar_info  # New bar hovered

            if self.hover_annotation:  # Remove old annotation
                try:
                    self.hover_annotation.remove()
                except (ValueError, AttributeError, RuntimeError):
                    pass  # Catch if already removed

            try:
                time_start = hovered_bar_info['time_start']
                time_end_display = hovered_bar_info['time_end'] - timedelta(microseconds=1)

                # Format based on whether the time range spans across midnight
                if time_start.date() == time_end_display.date():
                    start_format = '%A, %Y-%m-%d %H:%M:%S'
                    end_format = '%H:%M:%S'
                    time_text = f"Time: {time_start.strftime(start_format)} - {time_end_display.strftime(end_format)}"
                else:
                    full_format = '%A, %Y-%m-%d %H:%M:%S'
                    time_text = f"Start: {time_start.strftime(full_format)}\nEnd:   {time_end_display.strftime(full_format)}"

                text = f"{hovered_bar_info['message_type']}\n{time_text}\nCount: {hovered_bar_info['count']}"

                bar_patch = hovered_bar_info['bar']
                x = bar_patch.get_x() + bar_patch.get_width() / 2
                y = bar_patch.get_y() + bar_patch.get_height()

                self.hover_annotation = self.ax.annotate(text, xy=(x, y), xytext=(0, 5), textcoords="offset points",
                                                         ha='center', va='bottom',
                                                         bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.85),
                                                         fontsize=9, zorder=10)  # High zorder
                self.hover_annotation.set_visible(True);
                self.draw_idle()
            except (AttributeError, KeyError, RuntimeError):  # If data is malformed
                self.hover_annotation = None;
                self.last_hovered_bar_info = None
        else:  # Not hovering over any known bar
            if self.hover_annotation and self.hover_annotation.get_visible():
                try:
                    self.hover_annotation.set_visible(False);
                    self.draw_idle()
                except (AttributeError, RuntimeError):
                    pass
            self.last_hovered_bar_info = None

    def on_leave_axes(self, event):
        if self.hover_annotation and self.hover_annotation.get_visible():
            try:
                self.hover_annotation.set_visible(False);
                self.draw_idle()
            except (AttributeError, RuntimeError):
                pass
        self.last_hovered_bar_info = None