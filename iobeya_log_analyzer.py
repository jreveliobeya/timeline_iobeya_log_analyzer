#!/usr/bin/env python3
import sys
import re
import os
from datetime import datetime, timedelta, timezone
from collections import defaultdict, Counter
from PyQt5 import QtWidgets, QtGui, QtCore
import pandas as pd
import zipfile

# Local imports
from timeline_canvas import TimelineCanvas
from log_processing import LogLoaderThread
from ui_widgets import SortableTreeWidgetItem, LoadingDialog, VirtualTreeWidget, SearchWidget, WelcomeWidget, AboutDialog
from statistics_dialog import StatsDialog
from app_logic import AppLogic
from date_selection_dialog import DateSelectionDialog

class LogAnalyzerApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.app_version = "4.1.0"
        self.setWindowTitle(f"iObeya Timeline Log Analyzer v{self.app_version}")
        self.resize(1600, 1000)
        self.log_entries_full = pd.DataFrame() # Initialize as DataFrame
        self.message_types_data_for_list = {}
        self.selected_log_levels = {'INFO': False, 'WARN': False, 'ERROR': False, 'DEBUG': False}
        # self.top_loggers_for_selection_buttons = [] # This will be dynamically generated now
        self.stats_dialog = None
        self.timeline_min_num_full_range = 0
        self.timeline_max_num_full_range = 100
        self.slider_scale_factor = 10000
        self._is_batch_updating_ui = False
        self.loading_dialog = None
        self.loader_thread = None
        self.current_loaded_source_name = "No file loaded"
        self.loaded_source_type = None

        self.app_logic = AppLogic(self) # Initialize AppLogic first

        self.message_type_search_timer = QtCore.QTimer()
        self.message_type_search_timer.setSingleShot(True)
        # NOW self.app_logic exists for the connection
        self.message_type_search_timer.timeout.connect(self.app_logic.apply_message_type_filter) 

        self.setup_ui() 

    def _enter_batch_update(self):
        self._is_batch_updating_ui = True

    def _exit_batch_update(self):
        self._is_batch_updating_ui = False

    def setup_ui(self):
        # Create the main application layout (but don't show it yet)
        self.main_app_widget = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout(self.main_app_widget)

        self.create_toolbar()

        main_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        timeline_section_widget = self.create_timeline_section_with_sliders()
        main_splitter.addWidget(timeline_section_widget)

        bottom_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        message_types_panel = self.create_message_types_panel()
        bottom_splitter.addWidget(message_types_panel)
        right_panel = self.create_right_panel()
        bottom_splitter.addWidget(right_panel)
        bottom_splitter.setStretchFactor(0, 1)
        bottom_splitter.setStretchFactor(1, 2)

        main_splitter.addWidget(bottom_splitter)
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 1)

        main_layout.addWidget(main_splitter)

        # Setup Welcome Widget as initial view
        self.welcome_widget = WelcomeWidget(version=self.app_version)
        self.welcome_widget.load_file_requested.connect(self.load_log_file)
        self.welcome_widget.load_archive_requested.connect(self.load_log_archive)
        self.setCentralWidget(self.welcome_widget)

    def get_app_version(self):
        # Helper to get version; consistent with main()
        return self.app_version 

    def show_about_dialog(self):
        """Shows the 'About' dialog."""
        dialog = AboutDialog(version=self.app_version, parent=self)
        dialog.exec_()

    def show_main_ui(self):
        """Switches the central widget to the main application UI."""
        self.setCentralWidget(self.main_app_widget)
        # Now that the main UI is visible, perform initial data population/reset
        self.app_logic.reset_all_filters_and_view(initial_load=True)

    def create_toolbar(self):
        toolbar = self.addToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setIconSize(QtCore.QSize(16, 16)) # Optional: for icon consistency

        # Load File Action
        load_file_action = QtWidgets.QAction(self.style().standardIcon(QtWidgets.QStyle.SP_DialogOpenButton), "Load File", self)
        load_file_action.triggered.connect(self.load_log_file)
        load_file_action.setShortcut(QtGui.QKeySequence.Open)
        toolbar.addAction(load_file_action)

        # Load Archive Action
        load_archive_action = QtWidgets.QAction(self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon), "Load Archive", self)  # SP_DriveArchiveIcon was unavailable
        load_archive_action.triggered.connect(self.load_log_archive)
        toolbar.addAction(load_archive_action)

        toolbar.addSeparator()

        # Reset View Action
        reset_view_action = QtWidgets.QAction(self.style().standardIcon(QtWidgets.QStyle.SP_DialogResetButton), "Reset View", self)
        reset_view_action.setToolTip("Reset all filters and timeline zoom")
        reset_view_action.triggered.connect(lambda: self.app_logic.reset_all_filters_and_view(initial_load=False))
        toolbar.addAction(reset_view_action)

        toolbar.addSeparator()

        # Search Widget (Main Search Bar)
        self.search_widget = SearchWidget(placeholder_text="Search all log messages (full-text)...")
        self.search_widget.search_changed.connect(self.app_logic.on_search_changed)
        self.search_widget.setMinimumWidth(300) # Give it some decent width
        toolbar.addWidget(self.search_widget)

        toolbar.addSeparator()

        # Log Level Filter Buttons
        level_button_styles = {
            "ERROR": {"text": "ERR", "tooltip": "Filter by ERROR level", "bg": "#D9534F", "checked_bg": "#C9302C", "hover": "#B94A48"},
            "WARN":  {"text": "WRN", "tooltip": "Filter by WARN level",  "bg": "#F0AD4E", "checked_bg": "#EC971F", "hover": "#D68F3E"},
            "INFO":  {"text": "INF", "tooltip": "Filter by INFO level",  "bg": "#5BC0DE", "checked_bg": "#31B0D5", "hover": "#2CA8C6"},
            "DEBUG": {"text": "DBG", "tooltip": "Filter by DEBUG level", "bg": "#777777", "checked_bg": "#5E5E5E", "hover": "#4F4F4F"}
        }

        common_button_style_parts = "color: white; border: 1px solid #333; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 10pt;"

        for level_name, styles in level_button_styles.items():
            btn = QtWidgets.QPushButton(styles["text"])
            btn.setToolTip(styles["tooltip"])
            btn.setCheckable(True)
            btn.setChecked(self.app_logic.selected_log_levels.get(level_name, True))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {styles['bg']};
                    {common_button_style_parts}
                }}
                QPushButton:checked {{
                    background-color: {styles['checked_bg']};
                    border: 1px solid black; /* Darker border when checked */
                }}
                QPushButton:hover:!checked {{
                    background-color: {styles['hover']};
                }}
            """)
            btn.clicked.connect(lambda checked, name=level_name: self.app_logic.toggle_log_level_filter(name, checked))
            toolbar.addWidget(btn)
            # Store button as instance attribute
            setattr(self, f"{level_name.lower()}_btn", btn)
        
        toolbar.addSeparator()

        # Summary Information Widget (Period, Stats, Total)
        # This will be a QWidget with QHBoxLayout to group these labels and button
        summary_info_widget = QtWidgets.QWidget()
        summary_info_layout = QtWidgets.QHBoxLayout(summary_info_widget)
        summary_info_layout.setContentsMargins(5, 0, 5, 0) # Minimal margins
        summary_info_layout.setSpacing(8)

        summary_info_layout.addWidget(QtWidgets.QLabel("📅"))
        self.period_label = QtWidgets.QLabel("No log loaded")
        self.period_label.setToolTip("Date range of loaded logs")
        self.period_label.setStyleSheet("QLabel { padding: 2px 4px; border-radius: 3px; background-color: #E8F5E9; font-family: monospace; font-size: 10px; }")
        summary_info_layout.addWidget(self.period_label)

        summary_info_layout.addSpacing(10)

        self.stats_button = QtWidgets.QPushButton("📊")
        self.stats_button.setToolTip("Show Global Statistics")
        self.stats_button.setFixedSize(QtCore.QSize(22, 22))
        self.stats_button.setStyleSheet("QPushButton { font-size: 14px; border: none; padding: 0px; } QPushButton:hover { background-color: #e0e0e0; }")
        self.stats_button.clicked.connect(self.show_stats_panel)
        summary_info_layout.addWidget(self.stats_button)

        summary_info_layout.addSpacing(10)

        self.total_label = QtWidgets.QLabel("0 entries")
        self.total_label.setToolTip("Total log entries loaded")
        self.total_label.setStyleSheet("QLabel { padding: 2px 4px; border-radius: 3px; background-color: #E3F2FD; font-weight: bold; font-size: 10px; }")
        summary_info_layout.addWidget(self.total_label)
        
        summary_info_widget.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        toolbar.addWidget(summary_info_widget)

        # Spacer to push About button to the right
        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        toolbar.addWidget(spacer)

        # About Action
        about_action = QtWidgets.QAction(self.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxInformation), "About", self)
        about_action.setToolTip("Show application information")
        about_action.triggered.connect(self.show_about_dialog)
        toolbar.addAction(about_action)

    def update_log_level_button_states(self, selected_levels):
        """Updates the checked state of log level filter buttons."""
        if hasattr(self, 'error_btn'): self.error_btn.setChecked(selected_levels.get('ERROR', False))
        if hasattr(self, 'warn_btn'):  self.warn_btn.setChecked(selected_levels.get('WARN', False))
        if hasattr(self, 'info_btn'):  self.info_btn.setChecked(selected_levels.get('INFO', False))
        if hasattr(self, 'debug_btn'): self.debug_btn.setChecked(selected_levels.get('DEBUG', False))

    def create_timeline_section_with_sliders(self):
        timeline_section_widget = QtWidgets.QWidget()
        section_layout = QtWidgets.QVBoxLayout(timeline_section_widget)
        section_layout.setContentsMargins(0, 0, 0, 0);
        section_layout.setSpacing(2)

        controls_widget = QtWidgets.QWidget()
        controls_layout = QtWidgets.QHBoxLayout(controls_widget)
        controls_layout.setContentsMargins(5, 2, 5, 2)
        controls_layout.addWidget(QtWidgets.QLabel("Time Granularity:"))
        self.granularity_combo = QtWidgets.QComboBox()
        self.granularity_combo.addItems(['minute', 'hour', 'day'])
        self.granularity_combo.setCurrentText('minute')
        self.granularity_combo.currentTextChanged.connect(self.on_granularity_changed)
        controls_layout.addWidget(self.granularity_combo)
        controls_layout.addStretch()
        section_layout.addWidget(controls_widget)

        self.timeline_canvas = TimelineCanvas()
        self.timeline_canvas.bar_clicked.connect(self.app_logic.on_timeline_bar_clicked)
        self.timeline_canvas.time_range_updated.connect(self.update_timeline_sliders_range)
        section_layout.addWidget(self.timeline_canvas)

        slider_widget = QtWidgets.QWidget()
        slider_layout = QtWidgets.QGridLayout(slider_widget)
        slider_layout.setContentsMargins(5, 0, 5, 5);
        slider_layout.setSpacing(5)

        self.pan_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.pan_slider.setMinimum(0);
        self.pan_slider.setMaximum(self.slider_scale_factor)
        self.pan_slider.setPageStep(int(self.slider_scale_factor * 0.1))
        self.pan_slider.valueChanged.connect(self.on_slider_value_changed)
        self.pan_slider.setToolTip("Pan Timeline")

        self.zoom_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.zoom_slider.setMinimum(10);
        self.zoom_slider.setMaximum(self.slider_scale_factor)
        self.zoom_slider.setValue(self.slider_scale_factor)
        self.zoom_slider.setPageStep(int(self.slider_scale_factor * 0.1))
        self.zoom_slider.valueChanged.connect(self.on_slider_value_changed)
        self.zoom_slider.setToolTip("Zoom Timeline")

        slider_layout.addWidget(QtWidgets.QLabel("Pan:"), 0, 0);
        slider_layout.addWidget(self.pan_slider, 0, 1)
        slider_layout.addWidget(QtWidgets.QLabel("Zoom:"), 1, 0);
        slider_layout.addWidget(self.zoom_slider, 1, 1)
        section_layout.addWidget(slider_widget)
        return timeline_section_widget

    def create_message_types_panel(self):
        panel = QtWidgets.QWidget();
        layout = QtWidgets.QVBoxLayout(panel)

        search_layout = QtWidgets.QHBoxLayout()
        search_layout.addWidget(QtWidgets.QLabel("🔍"))
        self.message_type_search_input = QtWidgets.QLineEdit()
        self.message_type_search_input.setPlaceholderText("Search message types...")
        self.message_type_search_input.textChanged.connect(self.app_logic.on_message_type_search_changed_debounced)
        search_layout.addWidget(self.message_type_search_input)
        self.message_type_search_clear_btn = QtWidgets.QPushButton("✕")
        self.message_type_search_clear_btn.setFixedSize(24,24)
        self.message_type_search_clear_btn.setToolTip("Clear message type search")
        self.message_type_search_clear_btn.clicked.connect(self.message_type_search_input.clear)
        search_layout.addWidget(self.message_type_search_clear_btn)
        layout.addLayout(search_layout)


        title_layout = QtWidgets.QHBoxLayout();
        title_layout.addWidget(QtWidgets.QLabel("<b>Message Types</b>"));
        title_layout.addStretch()
        self.select_top5_btn = QtWidgets.QPushButton("Top 5");
        self.select_top5_btn.clicked.connect(self.app_logic.select_top5_message_types)
        self.select_top10_btn = QtWidgets.QPushButton("Top 10");
        self.select_top10_btn.clicked.connect(self.app_logic.select_top10_message_types)
        self.select_all_visible_types_btn = QtWidgets.QPushButton("Sel. All Vis.");
        self.select_all_visible_types_btn.setToolTip("Select all currently visible (non-hidden) message types")
        self.select_all_visible_types_btn.clicked.connect(
            lambda: self.app_logic.set_check_state_for_visible_types(QtCore.Qt.Checked))
        self.deselect_all_visible_types_btn = QtWidgets.QPushButton("Desel. All"); 
        self.deselect_all_visible_types_btn.setToolTip("Deselect all message types") 
        self.deselect_all_visible_types_btn.clicked.connect(
            lambda: self.app_logic.set_check_state_for_all_types(QtCore.Qt.Unchecked))
        for btn in [self.select_top5_btn, self.select_top10_btn, self.select_all_visible_types_btn,
                    self.deselect_all_visible_types_btn]: title_layout.addWidget(btn)
        layout.addLayout(title_layout)

        self.message_types_tree = QtWidgets.QTreeWidget()
        self.message_types_tree.setHeaderLabels(['Message Type', 'Count']);
        self.message_types_tree.setSortingEnabled(True)
        self.message_types_tree.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection)
        self.message_types_tree.itemChanged.connect(self.app_logic.on_message_type_item_changed)
        header = self.message_types_tree.header();
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch);
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        self.message_types_tree.sortByColumn(1, QtCore.Qt.DescendingOrder)
        layout.addWidget(self.message_types_tree)
        return panel

    def create_right_panel(self):
        right_widget = QtWidgets.QWidget();
        layout = QtWidgets.QVBoxLayout(right_widget)

        self.search_widget = SearchWidget();
        self.search_widget.search_changed.connect(self.on_search_changed)
        layout.addWidget(self.search_widget)

        layout.addWidget(QtWidgets.QLabel("<b>Messages in Selected Time Interval</b>"))
        self.selected_messages_list = VirtualTreeWidget()
        self.selected_messages_list.setHeaderLabels(['Time', 'Level', 'Logger', 'Message'])
        self.selected_messages_list.itemSelectionChanged.connect(self.on_message_selected)
        self.selected_messages_list.current_sort_column = 0;
        self.selected_messages_list.current_sort_order = QtCore.Qt.AscendingOrder
        self.selected_messages_list.header().setSortIndicator(0, QtCore.Qt.AscendingOrder)
        layout.addWidget(self.selected_messages_list)

        layout.addWidget(QtWidgets.QLabel("<b>Message Details</b>"))
        self.details_text = QtWidgets.QTextEdit();
        self.details_text.setReadOnly(True)
        self.details_text.setFontFamily("monospace");
        layout.addWidget(self.details_text)
        return right_widget

    def _initiate_loading_process(self, file_path=None, archive_path=None, files_to_process=None):
        if self.loader_thread and self.loader_thread.isRunning():
            QtWidgets.QMessageBox.warning(self, "Loading in Progress", "A file or archive is already being loaded.")
            return

        if archive_path:
            self.current_loaded_source_name = os.path.basename(archive_path)
            self.loaded_source_type = "archive"
        elif file_path:
            self.current_loaded_source_name = os.path.basename(file_path)
            self.loaded_source_type = "single_file"
        else:
            self.current_loaded_source_name = "Unknown Source"
            self.loaded_source_type = None

        self.loading_dialog = LoadingDialog(self)
        self.loader_thread = LogLoaderThread(file_path=file_path, archive_path=archive_path, files_to_process=files_to_process)

        self.loader_thread.progress_update.connect(self.loading_dialog.set_status)
        self.loader_thread.progress_update.connect(
            lambda status_text, detail_text: self.loading_dialog.set_detail(detail_text))
        self.loader_thread.progress_bar_config.connect(self.loading_dialog.set_progress_range)
        self.loader_thread.progress_bar_update.connect(self.loading_dialog.set_progress_value)
        self.loader_thread.finished_loading.connect(self.on_log_data_loaded)
        self.loader_thread.error_occurred.connect(self.on_load_error)
        self.loader_thread.finished.connect(self.on_load_finished)

        self.loading_dialog.show()
        self.loader_thread.start()

    def on_search_changed(self, search_text):
        if hasattr(self.selected_messages_list, 'apply_search_filter'):
            self.selected_messages_list.apply_search_filter(search_text)

    def on_message_type_search_changed_debounced(self, text):
        self.message_type_search_timer.stop()
        self.message_type_search_timer.start(300)

    def _apply_message_type_filter(self):
        search_text = self.message_type_search_input.text().lower()
        for i in range(self.message_types_tree.topLevelItemCount()):
            item = self.message_types_tree.topLevelItem(i)
            logger_name = item.text(0).lower()
            if not search_text:
                item.setHidden(False)
            else:
                item.setHidden(search_text not in logger_name)
        # After filtering, top N buttons might need to be re-evaluated based on new visible set
        # However, top_n logic is triggered by button click, so it will use current visible items.

    @QtCore.pyqtSlot(float, float)
    def update_timeline_sliders_range(self, min_num, max_num):
        self._enter_batch_update()
        self.timeline_min_num_full_range = min_num;
        self.timeline_max_num_full_range = max_num

        sliders_enabled = (
                    self.timeline_max_num_full_range > self.timeline_min_num_full_range + 1e-9)
        self.pan_slider.setEnabled(sliders_enabled);
        self.zoom_slider.setEnabled(sliders_enabled)

        if sliders_enabled:
            self.pan_slider.setMinimum(0);
            self.pan_slider.setMaximum(self.slider_scale_factor);
            self.pan_slider.setValue(0)
            self.zoom_slider.setMinimum(10);
            self.zoom_slider.setMaximum(self.slider_scale_factor);
            self.zoom_slider.setValue(self.slider_scale_factor)
        else:
            self.pan_slider.setMinimum(0);
            self.pan_slider.setMaximum(0)
            self.zoom_slider.setMinimum(10);
            self.zoom_slider.setMaximum(self.slider_scale_factor);
            self.zoom_slider.setValue(self.slider_scale_factor)
        self._exit_batch_update()
        if not self._is_batch_updating_ui: self._apply_sliders_to_timeline_view()

    def on_slider_value_changed(self):
        if not self._is_batch_updating_ui:
            self._apply_sliders_to_timeline_view()

    def _apply_sliders_to_timeline_view(self):
        if self._is_batch_updating_ui: return
        if self.timeline_min_num_full_range is None or self.timeline_max_num_full_range is None: return

        if self.timeline_max_num_full_range <= self.timeline_min_num_full_range:
            center_point = self.timeline_min_num_full_range;
            tiny_width = 0.0001
            self.timeline_canvas.set_time_window_from_sliders(center_point - tiny_width / 2,
                                                              center_point + tiny_width / 2)
            return

        total_data_span = self.timeline_max_num_full_range - self.timeline_min_num_full_range
        zoom_value = max(self.zoom_slider.value(), 1)
        zoom_ratio = zoom_value / self.slider_scale_factor
        view_width = total_data_span * zoom_ratio
        min_view_width = max(total_data_span * (self.zoom_slider.minimum() / self.slider_scale_factor),
                             1e-5)
        view_width = max(view_width, min_view_width)

        pannable_range_num = total_data_span - view_width
        if pannable_range_num < 0: pannable_range_num = 0

        pan_ratio = self.pan_slider.value() / self.slider_scale_factor
        view_start_offset_from_min = pannable_range_num * pan_ratio
        view_start_num = self.timeline_min_num_full_range + view_start_offset_from_min
        view_end_num = view_start_num + view_width

        view_start_num = max(view_start_num, self.timeline_min_num_full_range)
        view_end_num = min(view_end_num, self.timeline_max_num_full_range)

        if view_start_num + view_width > self.timeline_max_num_full_range:
            view_start_num = self.timeline_max_num_full_range - view_width
            view_start_num = max(view_start_num, self.timeline_min_num_full_range)

        if view_start_num < view_end_num - 1e-9:
            self.timeline_canvas.set_time_window_from_sliders(view_start_num, view_end_num)
        elif total_data_span > 1e-9:
            self.timeline_canvas.set_time_window_from_sliders(self.timeline_min_num_full_range,
                                                              self.timeline_max_num_full_range)

    def load_log_file(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open Log File", "", "Log Files (*.log *.log.gz);;All Files (*)")
        if not file_path: return
        self._initiate_loading_process(file_path=file_path)

    def load_log_archive(self):
        archive_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open Log Archive", "", "ZIP Archives (*.zip);;All Files (*)")
        if not archive_path:
            return

        try:
            with zipfile.ZipFile(archive_path, 'r') as zf:
                file_list = zf.namelist()
        except zipfile.BadZipFile:
            QtWidgets.QMessageBox.critical(self, "Error", "Failed to open the archive. It may be corrupt or not a valid ZIP file.")
            return

        dialog = DateSelectionDialog(file_list, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            files_to_process = dialog.get_selected_files()
            if not files_to_process:
                QtWidgets.QMessageBox.information(self, "No Files Selected", "No log files were found for the selected date range.")
                return
            self._initiate_loading_process(archive_path=archive_path, files_to_process=files_to_process)

    def on_log_data_loaded(self, log_entries_df, failed_files_summary):
        if self.centralWidget() == self.welcome_widget and not log_entries_df.empty:
            self.show_main_ui()
        if self.loading_dialog:
            self.loading_dialog.update_status("Finalizing...", "Displaying results.")
            self.loading_dialog.accept()
        self.log_entries_full = log_entries_df
        self.current_loaded_source_name = self.loader_thread.get_source_name() if self.loader_thread else "Unknown Source" # Make sure this is set before using in title
        self.setWindowTitle(f"iObeya Timeline Log Analyzer - {self.current_loaded_source_name}")

        # Build FTS index using AppLogic
        if self.app_logic:
            if not self.log_entries_full.empty:
                self.app_logic._build_fts_index(self.log_entries_full)
            else:
                # If logs are empty, ensure any previous FTS index is cleared/reset
                self.app_logic._build_fts_index(pd.DataFrame())

        if hasattr(self.selected_messages_list, 'set_all_items_data'):
            self.selected_messages_list.set_all_items_data([])
        self.details_text.clear()

        if self.stats_dialog and self.stats_dialog.isVisible():
            self.stats_dialog.close();
            self.stats_dialog = None

        self.timeline_canvas.set_full_log_data(self.log_entries_full)
        self.app_logic.reset_all_filters_and_view(initial_load=True) # Call on app_logic
        self.loading_dialog.accept() # Close the loading dialog

        if not self.log_entries_full.empty and not self._is_batch_updating_ui:
             self._trigger_timeline_update_from_selection()


        if failed_files_summary:
            error_details = "\n".join(
                [f"- {fname}: {reason}" for fname, reason in failed_files_summary[:15]])
            if len(failed_files_summary) > 15: error_details += f"\n...and {len(failed_files_summary) - 15} more."
            QtWidgets.QMessageBox.warning(self, "Archive Loading Issues",
                                          f"Some files within the archive could not be processed:\n{error_details}")

        if self.log_entries_full.empty: 
            if not self._is_batch_updating_ui:
                self.timeline_canvas.plot_timeline()
                self.update_timeline_sliders_range(0, 0)
            QtWidgets.QMessageBox.information(self, "No Data Loaded",
                                          "No log entries were found or loaded from the source.")

    def on_load_error(self, error_message: str):
        """Handles errors emitted from the LogLoaderThread."""
        self.reset_app_state_after_error(error_message)

    def reset_app_state_after_error(self, error_message: str):
        """Resets the application state and UI after a loading error."""
        if self.loading_dialog and self.loading_dialog.isVisible():
            self.loading_dialog.reject() # Close if still open

        if self.loader_thread and self.loader_thread.isRunning():
            self.loader_thread.stop() # Request thread to stop
            if not self.loader_thread.wait(1000): # Wait a bit for graceful exit
                self.loader_thread.terminate() # Force terminate if not stopping
        
        QtWidgets.QMessageBox.critical(self, "Loading Error", str(error_message))

        self.log_entries_full = pd.DataFrame() # Clear any partial data
        self.current_loaded_source_name = "Error during load"
        self.setWindowTitle("Timeline Log Analyzer - Error")

        # Reset UI elements via AppLogic
        if hasattr(self, 'app_logic') and self.app_logic:
            self.app_logic.reset_all_filters_and_view(initial_load=True)
        else: # Fallback if app_logic somehow not initialized (should not happen)
            if hasattr(self.selected_messages_list, 'set_all_items_data'):
                 self.selected_messages_list.set_all_items_data([])
            if hasattr(self, 'details_text'): self.details_text.clear()
            if hasattr(self, 'timeline_canvas'): self.timeline_canvas.clear_plot()
            if hasattr(self, 'message_types_tree'): self.message_types_tree.clear()
            # Add other direct UI resets if necessary as a fallback

    def on_load_finished(self):
        """Called when the LogLoaderThread finishes, regardless of success or error."""
        if self.loading_dialog and self.loading_dialog.isVisible():
            self.loading_dialog.accept() # Ensure dialog is closed
        # Further cleanup if loader_thread instance needs to be cleared, etc.
        # For now, just ensure dialog is closed.

    def update_log_summary(self):
        if self.log_entries_full.empty:
            self.period_label.setText("No log loaded");
            self.period_label.setToolTip("No log file has been loaded.");
            self.total_label.setText("0 entries")
            self.error_btn.setText("ERROR: 0");
            self.warn_btn.setText("WARN: 0")
            self.info_btn.setText("INFO: 0");
            self.debug_btn.setText("DEBUG: 0")
        else:
            level_counts = self.log_entries_full['log_level'].value_counts().to_dict()
            for level in ['ERROR', 'WARN', 'INFO', 'DEBUG']:
                count = level_counts.get(level, 0)
                self.log_level_buttons[level].setText(f"{level} ({count})")
                self.log_level_buttons[level].setChecked(self.selected_log_levels[level])

            start_time = self.log_entries_full['datetime_obj'].min()
            end_time = self.log_entries_full['datetime_obj'].max()
            # Ensure datetime objects are actual datetimes before formatting
            if pd.notna(start_time) and pd.notna(end_time) and \
               isinstance(start_time, datetime) and isinstance(end_time, datetime) and \
               start_time != datetime.min and end_time != datetime.min:
                self.period_label.setText(
                f"{start_time.strftime('%y-%m-%d %H:%M')}→{end_time.strftime('%y-%m-%d %H:%M')}")
                self.period_label.setToolTip(f"Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\nEnd:   {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            elif not self.log_entries_full.empty and 'datetime' in self.log_entries_full.columns:
                 # This branch might be hit if datetime_obj parsing failed or was partial
                 min_dt_str = str(self.log_entries_full['datetime'].min())
                 max_dt_str = str(self.log_entries_full['datetime'].max())
                 self.period_label.setText(f"{min_dt_str} → {max_dt_str}")
                 self.period_label.setToolTip(f"Start: {min_dt_str}\nEnd:   {max_dt_str} (raw string)")
            else:
                self.period_label.setText("N/A → N/A")
                self.period_label.setToolTip("Date range not available")

            total_entries = len(self.log_entries_full);
            self.total_label.setText(f"{total_entries:,} entries")

    def _rebuild_message_types_data_and_list(self, select_all_visible=False):
        if self.log_entries_full.empty: return

        # Filter by selected log levels first
        selected_levels = [level for level, is_selected in self.selected_log_levels.items() if is_selected]
        if not selected_levels: return

        filtered_df = self.log_entries_full[self.log_entries_full['log_level'].isin(selected_levels)]
        if filtered_df.empty: return

        # Get counts of logger_name
        logger_counts = filtered_df['logger_name'].value_counts()

        # Sort by count descending
        sorted_loggers = logger_counts.sort_values(ascending=False).index.tolist()

        current_checked_texts = set()
        if not select_all_visible:
            for i in range(self.message_types_tree.topLevelItemCount()):
                item = self.message_types_tree.topLevelItem(i)
                if item.checkState(0) == QtCore.Qt.Checked:
                    current_checked_texts.add(item.text(0))

        self.message_types_tree.blockSignals(True);
        self.message_types_tree.clear();
        items_to_add = []
        for logger_name, data in self.message_types_data_for_list.items():
            if data['count'] > 0:
                item = SortableTreeWidgetItem([logger_name, str(data['count'])])
                item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
                item.setCheckState(0, QtCore.Qt.Checked if (
                            select_all_visible or logger_name in current_checked_texts) else QtCore.Qt.Unchecked)
                items_to_add.append(item)
        if items_to_add: self.message_types_tree.addTopLevelItems(items_to_add)

        current_sort_col = self.message_types_tree.sortColumn()
        current_sort_order = self.message_types_tree.header().sortIndicatorOrder()
        self.message_types_tree.sortItems(current_sort_col if current_sort_col != -1 else 1,
                                          current_sort_order if current_sort_col != -1 else QtCore.Qt.DescendingOrder)
        self.message_types_tree.blockSignals(False)
        self._apply_message_type_filter()

    def on_message_type_item_changed(self, item, column):
        if not self._is_batch_updating_ui:
            self._trigger_timeline_update_from_selection()

    # Changed: New method to set check state for ALL types (hidden or not)
    def set_check_state_for_all_types(self, check_state):
        if self._is_batch_updating_ui: return
        self._enter_batch_update()
        self.message_types_tree.blockSignals(True)
        for i in range(self.message_types_tree.topLevelItemCount()):
            item = self.message_types_tree.topLevelItem(i)
            # Operates on all items, regardless of hidden status
            if item.checkState(0) != check_state:
                item.setCheckState(0, check_state)
        self.message_types_tree.blockSignals(False)
        self._exit_batch_update()
        self._trigger_timeline_update_from_selection()

    # Changed: Renamed and modified to only act on VISIBLE (non-hidden) types
    def set_check_state_for_visible_types(self, check_state):
        if self._is_batch_updating_ui: return
        self._enter_batch_update()
        self.message_types_tree.blockSignals(True)
        for i in range(self.message_types_tree.topLevelItemCount()):
            item = self.message_types_tree.topLevelItem(i)
            if not item.isHidden(): # Only operate on non-hidden items
                if item.checkState(0) != check_state: item.setCheckState(0, check_state)
        self.message_types_tree.blockSignals(False)
        self._exit_batch_update()
        self._trigger_timeline_update_from_selection()

    def _trigger_timeline_update_from_selection(self):
        if self._is_batch_updating_ui: return
        selected_types = set()
        for i in range(self.message_types_tree.topLevelItemCount()):
            item = self.message_types_tree.topLevelItem(i)
            if item.checkState(0) == QtCore.Qt.Checked:
                 selected_types.add(item.text(0))

        self.timeline_canvas.update_display_config(selected_types, self.granularity_combo.currentText())

    def on_granularity_changed(self):
        if self._is_batch_updating_ui: return
        self._enter_batch_update()
        self.pan_slider.setValue(0);
        self.zoom_slider.setValue(self.slider_scale_factor)
        self._exit_batch_update()
        self._trigger_timeline_update_from_selection()

    def reset_all_filters_and_view(self, initial_load=False):
        self._enter_batch_update()
        try:
            self.selected_log_levels = {'INFO': True, 'WARN': True, 'ERROR': True, 'DEBUG': True}
            self.update_log_summary()

            if hasattr(self, 'message_type_search_input'):
                self.message_type_search_input.blockSignals(True)
                self.message_type_search_input.clear()
                self.message_type_search_input.blockSignals(False)

            self._rebuild_message_types_data_and_list(select_all_visible=True)

            if hasattr(self, 'pan_slider') and hasattr(self, 'zoom_slider'):
                self.pan_slider.setValue(0);
                self.zoom_slider.setValue(self.slider_scale_factor)

            if hasattr(self, 'granularity_combo'):
                self.granularity_combo.blockSignals(True)
                default_granularity = 'minute'
                if self.log_entries_full and self.loaded_source_type:
                    if self.loaded_source_type == "archive":
                        default_granularity = 'day'
                    elif self.loaded_source_type == "single_file":
                        default_granularity = 'hour'
                self.granularity_combo.setCurrentText(default_granularity)
                self.granularity_combo.blockSignals(False)

            if hasattr(self, 'search_widget'): self.search_widget.clear_search()
            if hasattr(self.selected_messages_list,
                       'set_all_items_data'): self.selected_messages_list.set_all_items_data([])
            if hasattr(self, 'details_text'): self.details_text.clear()
        finally:
            self._exit_batch_update()

        if initial_load and self.log_entries_full.empty:
            current_granularity = self.granularity_combo.currentText() if hasattr(self, 'granularity_combo') else 'minute'
            self.timeline_canvas.update_display_config(set(), current_granularity)
            self.update_timeline_sliders_range(0, 0)
        elif not self.log_entries_full.empty:
            self._trigger_timeline_update_from_selection()
        else:
            current_granularity = self.granularity_combo.currentText() if hasattr(self, 'granularity_combo') else 'minute'
            self.timeline_canvas.update_display_config(set(), current_granularity)
            self.update_timeline_sliders_range(0, 0)



    def on_message_selected(self):
        selected_items = self.selected_messages_list.selectedItems()
        if not selected_items: self.details_text.clear(); return
        entry_data = selected_items[0].data(0, QtCore.Qt.UserRole)
        if entry_data and isinstance(entry_data, dict):
            # Reconstruct the full entry for display, as it's no longer stored to save memory
            full_entry_text = f"{entry_data.get('datetime', '')} {entry_data.get('log_level', '')} [{entry_data.get('logger_name', '')}] {entry_data.get('message', '')}"
            self.details_text.setPlainText(full_entry_text)
        else:
            self.details_text.clear()

    def show_stats_panel(self):
        if self.log_entries_full.empty:
            QtWidgets.QMessageBox.information(self, "No Data", "Please load a log file first.")
            return
        if self.stats_dialog is None or not self.stats_dialog.isVisible():
            self.stats_dialog = StatsDialog(self.log_entries_full, self)
            self.stats_dialog.show()
        else:
            self.stats_dialog.activateWindow()

    def closeEvent(self, event):
        if self.loader_thread and self.loader_thread.isRunning():
            self.loader_thread.stop()
            if not self.loader_thread.wait(1500):
                self.loader_thread.terminate()
        if self.loading_dialog and self.loading_dialog.isVisible(): self.loading_dialog.reject()
        if self.stats_dialog and self.stats_dialog.isVisible(): self.stats_dialog.close()
        super().closeEvent(event)


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("iObeya Timeline Log Analyzer")
    app.setApplicationVersion("4.1.0") # Version bump
    app.setOrganizationName("LogAnalyzer")
    try:
        app.setStyle(QtWidgets.QStyleFactory.create('Fusion'))
    except:
        pass
    window = LogAnalyzerApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()