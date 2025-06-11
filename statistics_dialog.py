#!/usr/bin/env python3
from PyQt5 import QtWidgets, QtGui, QtCore
from collections import Counter
import pandas as pd
from datetime import datetime # For summary text
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
from matplotlib.ticker import PercentFormatter


class StatsDialog(QtWidgets.QDialog):
    def __init__(self, all_log_entries, parent=None):
        super().__init__(parent);
        self.all_log_entries = all_log_entries
        self.setWindowTitle("Global Log Statistics");
        self.setMinimumSize(800, 600)
        layout = QtWidgets.QVBoxLayout(self);
        tab_widget = QtWidgets.QTabWidget();
        layout.addWidget(tab_widget)

        # Summary Tab
        summary_tab = QtWidgets.QWidget();
        summary_layout = QtWidgets.QVBoxLayout(summary_tab)
        self.summary_text_edit = QtWidgets.QTextEdit();
        self.summary_text_edit.setReadOnly(True)
        self.summary_text_edit.setFontFamily("monospace");
        summary_layout.addWidget(self.summary_text_edit)
        tab_widget.addTab(summary_tab, "Overall Summary");
        self.populate_summary_text()

        # Pareto Chart Tab
        pareto_tab = QtWidgets.QWidget();
        pareto_layout = QtWidgets.QVBoxLayout(pareto_tab)
        self.pareto_canvas = FigureCanvas(Figure(figsize=(7, 5)));
        pareto_layout.addWidget(self.pareto_canvas)
        tab_widget.addTab(pareto_tab, "Message Type Pareto");
        self.plot_pareto_chart()

        # Level Distribution Tab
        level_dist_tab = QtWidgets.QWidget();
        level_dist_layout = QtWidgets.QVBoxLayout(level_dist_tab)
        self.level_dist_canvas = FigureCanvas(Figure(figsize=(5, 4)));
        level_dist_layout.addWidget(self.level_dist_canvas)
        tab_widget.addTab(level_dist_tab, "Log Level Distribution");
        self.plot_level_distribution()

    def populate_summary_text(self):
        if self.all_log_entries.empty: 
            self.summary_text_edit.setText("No log entries loaded.")
            return

        total_entries = len(self.all_log_entries)
        first_dt_obj = self.all_log_entries['datetime_obj'].min()
        last_dt_obj = self.all_log_entries['datetime_obj'].max()

        period_str = f"{first_dt_obj.strftime('%Y-%m-%d %H:%M:%S')} to {last_dt_obj.strftime('%Y-%m-%d %H:%M:%S')}"
        if pd.notna(first_dt_obj) and pd.notna(last_dt_obj):
            duration = last_dt_obj - first_dt_obj
            period_str += f" (Duration: {str(duration).split('.')[0]})"

        level_counts = self.all_log_entries['log_level'].value_counts()
        logger_counts = self.all_log_entries['logger_name'].value_counts()

        summary = [
            f"Global Log Statistics\n{'=' * 40}\n",
            f"Time Period: {period_str}",
            f"Total Entries: {total_entries:,}",
            f"Unique Message Types (Loggers): {len(logger_counts):,}\n",
            "Entries by Log Level:"
        ]

        for level in ['ERROR', 'WARN', 'INFO', 'DEBUG']:
            count = level_counts.get(level, 0)
            summary.append(f"  - {level:<8}: {count:>10,} ({count / total_entries * 100:.2f}%)")
        
        summary.append("\nTop 10 Most Frequent Message Types:")
        for logger, count in logger_counts.nlargest(10).items():
            summary.append(f"  - {logger:<50}: {count:>10,}")
        
        self.summary_text_edit.setText("\n".join(summary))

    def plot_pareto_chart(self):
        if self.all_log_entries.empty: return
        
        logger_counts = self.all_log_entries['logger_name'].value_counts()
        if logger_counts.empty: return

        top_20_counts = logger_counts.nlargest(20)
        loggers = top_20_counts.index.tolist()
        counts = top_20_counts.values
        
        cumulative_sum = np.cumsum(counts)
        overall_total_sum = len(self.all_log_entries)
        percentages = cumulative_sum / overall_total_sum * 100

        fig = self.pareto_canvas.figure;
        fig.clear();
        ax1 = fig.add_subplot(111)
        x_indices = np.arange(len(loggers));
        ax1.bar(x_indices, counts, color='C0', alpha=0.7)
        ax1.set_xticks(x_indices);
        ax1.set_xticklabels(loggers, rotation=45, ha="right", fontsize=8)
        ax1.set_xlabel("Message Type (Logger)");
        ax1.set_ylabel("Frequency (Count)", color='C0')
        ax1.tick_params(axis='y', labelcolor='C0');

        ax2 = ax1.twinx()  # Create a second y-axis for percentage
        ax2.plot(x_indices, percentages, color='C1', marker='o', ms=5)
        ax2.yaxis.set_major_formatter(PercentFormatter())
        ax2.set_ylabel("Cumulative Percentage", color='C1');
        ax2.tick_params(axis='y', labelcolor='C1')
        ax2.set_ylim(0, 105);  # Slight margin above 100%

        fig.suptitle(f"Pareto Chart of Message Types (Top {len(top_20_counts)})", fontsize=12)
        fig.tight_layout(rect=[0, 0.05, 1, 0.95]);
        self.pareto_canvas.draw()

    def plot_level_distribution(self):
        if self.all_log_entries.empty: return
        
        level_counts = self.all_log_entries['log_level'].value_counts()
        if level_counts.empty: return

        ordered_labels = ['ERROR', 'WARN', 'INFO', 'DEBUG']
        # Filter and order the counts based on ordered_labels
        plot_data = level_counts[level_counts.index.isin(ordered_labels)].reindex(ordered_labels).dropna()

        labels = plot_data.index.tolist()
        sizes = plot_data.values.tolist()

        fig = self.level_dist_canvas.figure;
        fig.clear();
        ax = fig.add_subplot(111)
        # Define colors for standard levels
        colors_map = {'ERROR': '#D32F2F', 'WARN': '#F57C00', 'INFO': '#1976D2', 'DEBUG': '#7B1FA2', 'OTHER': '#AAAAAA'}
        pie_colors = [colors_map.get(label, '#AAAAAA') for label in labels]  # Fallback for non-standard

        ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=pie_colors,
               wedgeprops={'edgecolor': 'white'})  # Add edge color for separation
        ax.axis('equal');
        fig.suptitle("Log Level Distribution", fontsize=12);
        fig.tight_layout();
        self.level_dist_canvas.draw()