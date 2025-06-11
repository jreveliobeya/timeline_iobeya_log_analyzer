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

        # Distribution Chart Tab (replaces Level Distribution)
        dist_chart_tab = QtWidgets.QWidget();
        dist_chart_layout = QtWidgets.QVBoxLayout(dist_chart_tab)

        # Radio buttons for chart type selection
        self.chart_type_groupbox = QtWidgets.QGroupBox("Chart Data Type")
        chart_type_layout = QtWidgets.QHBoxLayout()
        self.radio_level = QtWidgets.QRadioButton("By Log Level")
        self.radio_message_type = QtWidgets.QRadioButton("By Message Type")
        self.radio_level.setChecked(True) # Default
        chart_type_layout.addWidget(self.radio_level)
        chart_type_layout.addWidget(self.radio_message_type)
        self.chart_type_groupbox.setLayout(chart_type_layout)
        dist_chart_layout.addWidget(self.chart_type_groupbox)

        self.dist_canvas = FigureCanvas(Figure(figsize=(5, 4))); # Renamed from level_dist_canvas
        dist_chart_layout.addWidget(self.dist_canvas)
        tab_widget.addTab(dist_chart_tab, "Distribution Chart"); # Renamed tab

        self.radio_level.toggled.connect(self._update_distribution_chart_type)
        # No need to connect radio_message_type explicitly if radio_level's toggle handles both states

        self._plot_distribution_chart() # Initial plot

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

    def _update_distribution_chart_type(self):
        # This method is called when a radio button is toggled.
        # We only need to replot if the new state is 'checked'.
        # However, the toggled signal fires for both check and uncheck.
        # We can simplify by just replotting, or check which button is now active.
        self._plot_distribution_chart()

    def _plot_distribution_chart(self): # Renamed from plot_level_distribution
        if self.all_log_entries.empty: 
            fig = self.dist_canvas.figure
            fig.clear()
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, "No log entries loaded.", ha='center', va='center')
            fig.suptitle("Distribution Chart", fontsize=12)
            self.dist_canvas.draw()
            return
        
        fig = self.dist_canvas.figure
        fig.clear()
        ax = fig.add_subplot(111)
        
        chart_title = "Distribution Chart"
        labels = []
        sizes = []
        pie_colors = None # Let Matplotlib decide for message types, specify for levels

        if self.radio_level.isChecked():
            chart_title = "Log Level Distribution"
            level_counts = self.all_log_entries['log_level'].value_counts()
            if not level_counts.empty:
                ordered_labels = ['ERROR', 'WARN', 'INFO', 'DEBUG']
                # Filter and order the counts based on ordered_labels, include 0 for levels not present
                plot_data = level_counts.reindex(ordered_labels, fill_value=0)
                # Remove levels with 0 count for cleaner pie chart
                plot_data = plot_data[plot_data > 0]

                if not plot_data.empty:
                    labels = plot_data.index.tolist()
                    sizes = plot_data.values.tolist()
                    colors_map = {'ERROR': '#D32F2F', 'WARN': '#F57C00', 'INFO': '#1976D2', 'DEBUG': '#7B1FA2'}
                    pie_colors = [colors_map.get(label, '#AAAAAA') for label in labels]

        elif self.radio_message_type.isChecked():
            chart_title = "Message Type Distribution"
            logger_counts = self.all_log_entries['logger_name'].value_counts()
            if not logger_counts.empty:
                total_logs = len(self.all_log_entries) # Use total from all_log_entries for percentage calculation
                threshold_percentage = 2.0  # Group types constituting less than this percentage

                df_counts = logger_counts.reset_index()
                df_counts.columns = ['logger', 'count']
                df_counts['percentage'] = (df_counts['count'] / total_logs) * 100
                
                main_types = df_counts[df_counts['percentage'] >= threshold_percentage]
                other_types = df_counts[df_counts['percentage'] < threshold_percentage]
                
                current_labels = main_types['logger'].tolist()
                current_sizes = main_types['count'].tolist()
                
                if not other_types.empty:
                    others_sum = other_types['count'].sum()
                    if others_sum > 0: 
                        current_labels.append(f"Others ({len(other_types)} types < {threshold_percentage}% each)")
                        current_sizes.append(others_sum)
                
                labels = current_labels
                sizes = current_sizes
                # pie_colors will be None, Matplotlib will use default color cycle

        if not labels or not sizes:
            ax.text(0.5, 0.5, "No data to display for this selection.", ha='center', va='center', fontsize=10)
        else:
            # Ensure autopct doesn't display for tiny slices if sizes are not normalized (they are counts here)
            # Or, pass normalized data to pie if you want percentages of the displayed pie, not of total logs.
            # For now, autopct shows percentage of the current pie's total.
            wedges, texts, autotexts = ax.pie(sizes, labels=None, autopct='%1.1f%%', startangle=90, colors=pie_colors,
                                              wedgeprops={'edgecolor': 'white'})
            ax.axis('equal')

            # Create a legend for pie charts, especially useful for message types
            # Filter labels and sizes for legend to avoid issues if a slice is too small for autopct
            # legend_labels = [f'{l} ({s})' for l, s in zip(labels, sizes)]
            # Use a more readable format for legend, especially if labels are long
            legend_labels = []
            for l, s in zip(labels, sizes):
                percentage = (s / sum(sizes)) * 100 if sum(sizes) > 0 else 0
                legend_labels.append(f'{l}: {s} ({percentage:.1f}%)')

            ax.legend(wedges, legend_labels, title=chart_title, loc="center left", bbox_to_anchor=(1, 0, 0.5, 1), fontsize='small')
            
        fig.suptitle(chart_title, fontsize=14, y=0.98) # Adjusted y for suptitle with legend
        fig.tight_layout(rect=[0, 0, 0.85, 0.96]) # Adjust rect to make space for legend
        self.dist_canvas.draw()