# app_logic.py
import sqlite3
import pandas as pd
from PyQt5 import QtCore  # Assurez-vous que QtCore est importé
from collections import Counter
from datetime import datetime
from ui_widgets import SortableTreeWidgetItem


class AppLogic(QtCore.QObject):
    def __init__(self, main_window):
        super().__init__()
        self.mw = main_window
        self.selected_log_levels = {'INFO': True, 'WARN': True, 'ERROR': True, 'DEBUG': True}
        self.message_types_data_for_list = pd.DataFrame(columns=['logger_name', 'count'])
        self.timeline_filter_active = False
        self.timeline_filter_start_time = None
        self.timeline_filter_end_time = None
        self.current_search_text = ""
        self.fts_db_conn = None


    # ... (reset_all_filters_and_view, update_log_summary_display, _rebuild_message_types_data_and_list)
    # ... (trigger_timeline_update_from_selection, on_granularity_changed, on_slider_value_changed)

    @QtCore.pyqtSlot(float, float)  # <--- DÉCORER COMME SLOT
    def update_timeline_sliders_range(self, min_num, max_num):
        self.mw._enter_batch_update()
        self.mw.timeline_min_num_full_range = min_num
        self.mw.timeline_max_num_full_range = max_num

        sliders_enabled = (self.mw.timeline_max_num_full_range > self.mw.timeline_min_num_full_range + 1e-9)
        if self.mw.pan_slider: self.mw.pan_slider.setEnabled(sliders_enabled)
        if self.mw.zoom_slider: self.mw.zoom_slider.setEnabled(sliders_enabled)

        if sliders_enabled:
            if self.mw.pan_slider:
                self.mw.pan_slider.setMinimum(0)
                self.mw.pan_slider.setMaximum(self.mw.slider_scale_factor)
                self.mw.pan_slider.setValue(0)
            if self.mw.zoom_slider:
                self.mw.zoom_slider.setMinimum(10)
                self.mw.zoom_slider.setMaximum(self.mw.slider_scale_factor)
                self.mw.zoom_slider.setValue(self.mw.slider_scale_factor)
        else:
            if self.mw.pan_slider:
                self.mw.pan_slider.setMinimum(0)
                self.mw.pan_slider.setMaximum(0)
            if self.mw.zoom_slider:
                self.mw.zoom_slider.setMinimum(10)
                self.mw.zoom_slider.setMaximum(self.mw.slider_scale_factor)
                self.mw.zoom_slider.setValue(self.mw.slider_scale_factor)
        self.mw._exit_batch_update()
        if not self.mw._is_batch_updating_ui: self.apply_sliders_to_timeline_view()

    # ... (le reste des méthodes de AppLogic)
    def reset_all_filters_and_view(self, initial_load=False):
        self.mw._enter_batch_update()
        try:
            # Reset filter states
            self.selected_log_levels = {'INFO': True, 'WARN': True, 'ERROR': True, 'DEBUG': True}
            self.timeline_filter_active = False
            self.timeline_filter_start_time = None
            self.timeline_filter_end_time = None
            self.current_search_text = ""

            # Update UI elements that reflect these states
            self.update_log_summary_display() # Reflects log level counts

            search_input = self.mw.message_type_search_input
            if search_input:
                search_input.blockSignals(True)
                search_input.clear()
                search_input.blockSignals(False)

            # This rebuilds the message type tree and selects all by default
            self._rebuild_message_types_data_and_list(select_all_visible=True)

            if self.mw.pan_slider and self.mw.zoom_slider:
                self.mw.pan_slider.setValue(0)
                self.mw.zoom_slider.setValue(self.mw.slider_scale_factor)

            if self.mw.granularity_combo:
                self.mw.granularity_combo.blockSignals(True)
                default_granularity = 'minute'
                if hasattr(self.mw, 'log_entries_full') and not self.mw.log_entries_full.empty and self.mw.loaded_source_type:
                    if self.mw.loaded_source_type == "archive":
                        default_granularity = 'day'
                    elif self.mw.loaded_source_type == "single_file":
                        default_granularity = 'hour'
                self.mw.granularity_combo.setCurrentText(default_granularity)
                self.mw.granularity_combo.blockSignals(False)

            if self.mw.search_widget: self.mw.search_widget.clear_search() # Clears UI
            # selected_messages_list will be updated by _apply_filters_and_update_views
            if self.mw.details_text: self.mw.details_text.clear()

        finally:
            self.mw._exit_batch_update()

        # Apply all (now reset) filters to update the main list and timeline
        self._apply_filters_and_update_views()
        
        # Update timeline display based on current (likely all) message types and granularity
        # This needs to happen *after* _apply_filters_and_update_views if that method doesn't already handle it
        # or if the timeline needs a specific update based on the full dataset view after reset.
        current_granularity = self.mw.granularity_combo.currentText() if self.mw.granularity_combo else 'minute'
        log_data_exists = hasattr(self.mw, 'log_entries_full') and not self.mw.log_entries_full.empty

        selected_types_for_timeline = set()
        if self.mw.message_types_tree:
            for i in range(self.mw.message_types_tree.topLevelItemCount()):
                item = self.mw.message_types_tree.topLevelItem(i)
                if item.checkState(0) == QtCore.Qt.Checked: # Should be all checked after reset
                    selected_types_for_timeline.add(item.text(0))
        
        if self.mw.timeline_canvas:
            self.mw.timeline_canvas.update_display_config(selected_types_for_timeline, current_granularity)

        if initial_load and not log_data_exists:
            self.update_timeline_sliders_range(0, 0)
        # If log_data_exists, the timeline range should be updated by update_display_config or a subsequent call
        # based on the full dataset. The sliders might need adjustment based on the full range of data.
        # This part might need refinement based on how update_timeline_sliders_range interacts with plot_timeline.

        if not initial_load and self.mw.statusBar():
            self.mw.statusBar().showMessage("Vue et filtres réinitialisés", 3000)

    def update_log_summary_display(self):
        if not self.mw.period_label or not self.mw.total_label or not self.mw.error_btn:
            return

        if self.mw.log_entries_full.empty:
            self.mw.period_label.setText("Pas de log chargé")
            self.mw.total_label.setText("0 entrées")
            self.mw.error_btn.setText("ERROR: 0")
            # Also reset other level buttons
            for level in ['INFO', 'WARN', 'DEBUG']:
                btn = getattr(self.mw, f"{level.lower()}_btn", None)
                if btn:
                    btn.setText(f"{level}: 0")
        else:
            total_entries = len(self.mw.log_entries_full)
            first_dt_obj = self.mw.log_entries_full['datetime_obj'].min()
            last_dt_obj = self.mw.log_entries_full['datetime_obj'].max()

            period_str = "N/A"
            if pd.notna(first_dt_obj) and pd.notna(last_dt_obj):
                duration = last_dt_obj - first_dt_obj
                period_str = (f"{first_dt_obj.strftime('%Y-%m-%d %H:%M:%S')} to "
                              f"{last_dt_obj.strftime('%Y-%m-%d %H:%M:%S')} "
                              f"(Duration: {str(duration).split('.')[0]})")

            self.mw.period_label.setText(period_str)
            self.mw.total_label.setText(f"{total_entries:,} entrées")
            
            level_counts = self.mw.log_entries_full['log_level'].value_counts()
            for level in ['INFO', 'WARN', 'ERROR', 'DEBUG']:
                btn = getattr(self.mw, f"{level.lower()}_btn", None)
                if btn:
                    count = level_counts.get(level, 0)
                    btn.setText(f"{level}: {count:,}")
                    btn.setChecked(self.selected_log_levels.get(level, False))

    def _rebuild_message_types_data_and_list(self, select_all_visible=False):
        if not hasattr(self.mw, 'log_entries_full') or self.mw.log_entries_full.empty:
            self.message_types_data_for_list = pd.DataFrame(columns=['logger_name', 'count'])
            if self.mw.message_types_tree:
                self.mw.message_types_tree.clear()
            return

        selected_levels = {level for level, is_selected in self.selected_log_levels.items() if is_selected}
        
        # Filter by selected log levels
        filtered_df = self.mw.log_entries_full[self.mw.log_entries_full['log_level'].isin(selected_levels)]
        
        if filtered_df.empty:
            self.message_types_data_for_list = pd.DataFrame(columns=['logger_name', 'count'])
        else:
            # Calculate logger counts
            logger_counts_series = filtered_df['logger_name'].value_counts()
            
            # Filter by search text if any
            search_text = self.mw.message_type_search_input.text().lower() if self.mw.message_type_search_input else ""
            if search_text:
                # Ensure index is string type before using .str accessor
                if not logger_counts_series.empty and pd.api.types.is_string_dtype(logger_counts_series.index.dtype):
                    logger_counts_series = logger_counts_series[logger_counts_series.index.str.lower().str.contains(search_text, regex=False)]
                elif not logger_counts_series.empty: # Handle non-string indices if they occur, though logger_name should be string
                    logger_counts_series = logger_counts_series[[str(idx).lower().find(search_text) != -1 for idx in logger_counts_series.index]]


            # Convert to DataFrame and store
            if logger_counts_series.empty:
                self.message_types_data_for_list = pd.DataFrame(columns=['logger_name', 'count'])
            else:
                self.message_types_data_for_list = logger_counts_series.reset_index()
                self.message_types_data_for_list.columns = ['logger_name', 'count']
                self.message_types_data_for_list['count'] = self.message_types_data_for_list['count'].astype(int)

        if self.mw.message_types_tree:
            tree = self.mw.message_types_tree
            tree.clear()
            tree.setSortingEnabled(False) # Disable sorting while populating
            
            items = []
            # Iterate over the DataFrame (value_counts sorts by count descending by default)
            for index, row in self.message_types_data_for_list.iterrows():
                logger_name = str(row['logger_name']) # Ensure logger_name is string for display
                count = int(row['count']) # Ensure count is int
                item = SortableTreeWidgetItem([logger_name, str(count)])
                item.setCheckState(0, QtCore.Qt.Unchecked) # Default to unchecked
                items.append(item)
            
            tree.addTopLevelItems(items)
            tree.setSortingEnabled(True) # Re-enable sorting
            
            if select_all_visible:
                self.set_check_state_for_visible_types(QtCore.Qt.Checked)

    def trigger_timeline_update_from_selection(self):
        if self.mw._is_batch_updating_ui or not self.mw.timeline_canvas: return
        selected_types = set()
        if self.mw.message_types_tree:
            for i in range(self.mw.message_types_tree.topLevelItemCount()):
                item = self.mw.message_types_tree.topLevelItem(i)
                if item.checkState(0) == QtCore.Qt.Checked:
                    selected_types.add(item.text(0))

        granularity = self.mw.granularity_combo.currentText() if self.mw.granularity_combo else 'minute'
        self.mw.timeline_canvas.update_display_config(selected_types, granularity)

    def on_granularity_changed(self):
        if self.mw._is_batch_updating_ui: return
        self.mw._enter_batch_update()
        if self.mw.pan_slider: self.mw.pan_slider.setValue(0)
        if self.mw.zoom_slider: self.mw.zoom_slider.setValue(self.mw.slider_scale_factor)
        self.mw._exit_batch_update()
        self.trigger_timeline_update_from_selection()
        if self.mw.statusBar(): self.mw.statusBar().showMessage(f"Granularité: {self.mw.granularity_combo.currentText()}", 2000)

    def on_slider_value_changed(self):
        if not self.mw._is_batch_updating_ui:
            self.apply_sliders_to_timeline_view()

    def apply_sliders_to_timeline_view(self):
        if self.mw._is_batch_updating_ui: return
        if self.mw.timeline_min_num_full_range is None or self.mw.timeline_max_num_full_range is None: return
        if not self.mw.timeline_canvas or not self.mw.pan_slider or not self.mw.zoom_slider: return

        if self.mw.timeline_max_num_full_range <= self.mw.timeline_min_num_full_range:
            center_point = self.mw.timeline_min_num_full_range
            tiny_width = 0.0001
            self.mw.timeline_canvas.set_time_window_from_sliders(center_point - tiny_width / 2, center_point + tiny_width / 2)
            return

        total_data_span = self.mw.timeline_max_num_full_range - self.mw.timeline_min_num_full_range
        zoom_value = max(self.mw.zoom_slider.value(), 1)
        zoom_ratio = zoom_value / self.mw.slider_scale_factor
        view_width = total_data_span * zoom_ratio
        min_view_width = max(total_data_span * (self.mw.zoom_slider.minimum() / self.mw.slider_scale_factor), 1e-5)
        view_width = max(view_width, min_view_width)

        pannable_range_num = total_data_span - view_width
        if pannable_range_num < 0: pannable_range_num = 0

        pan_ratio = self.mw.pan_slider.value() / self.mw.slider_scale_factor
        view_start_offset_from_min = pannable_range_num * pan_ratio
        view_start_num = self.mw.timeline_min_num_full_range + view_start_offset_from_min
        view_end_num = view_start_num + view_width

        view_start_num = max(view_start_num, self.mw.timeline_min_num_full_range)
        view_end_num = min(view_end_num, self.mw.timeline_max_num_full_range)

        if view_start_num + view_width > self.mw.timeline_max_num_full_range:
            view_start_num = self.mw.timeline_max_num_full_range - view_width
            view_start_num = max(view_start_num, self.mw.timeline_min_num_full_range)

        if view_start_num < view_end_num - 1e-9:
            self.mw.timeline_canvas.set_time_window_from_sliders(view_start_num, view_end_num)
        elif total_data_span > 1e-9:
            self.mw.timeline_canvas.set_time_window_from_sliders(self.mw.timeline_min_num_full_range, self.mw.timeline_max_num_full_range)

    def on_message_type_search_changed_debounced(self, text):
        if self.mw.message_type_search_timer:
            self.mw.message_type_search_timer.stop()
            self.mw.message_type_search_timer.start(300)
        if self.mw.statusBar():
            self.mw.statusBar().showMessage(f"Filtrage types: '{text}'" if text else "Filtre types effacé", 2000)

    def apply_message_type_filter(self):
        if not self.mw.message_types_tree or not self.mw.message_type_search_input: return
        search_text = self.mw.message_type_search_input.text().lower()
        for i in range(self.mw.message_types_tree.topLevelItemCount()):
            item = self.mw.message_types_tree.topLevelItem(i)
            item.setHidden(bool(search_text and search_text not in item.text(0).lower()))
        # The visibility of items in the tree has changed, which affects what _apply_filters_and_update_views considers.
        self._apply_filters_and_update_views()

    def on_message_type_item_changed(self, item, column):
        if not self.mw._is_batch_updating_ui:
            # A change in the message type tree selection is a filter change.
            self._apply_filters_and_update_views()
            
            # Also, the timeline needs to be updated based on the new selection of message types.
            selected_types_for_timeline = set()
            if self.mw.message_types_tree:
                for i in range(self.mw.message_types_tree.topLevelItemCount()):
                    tree_item = self.mw.message_types_tree.topLevelItem(i)
                    # Consider only items that are checked AND not hidden by the message type search filter
                    if tree_item.checkState(0) == QtCore.Qt.Checked and not tree_item.isHidden():
                        selected_types_for_timeline.add(tree_item.text(0))
            
            current_granularity = self.mw.granularity_combo.currentText() if self.mw.granularity_combo else 'minute'
            if self.mw.timeline_canvas:
                self.mw.timeline_canvas.update_display_config(selected_types_for_timeline, current_granularity)

    def on_search_changed(self, search_text):
        self.current_search_text = search_text.strip()
        # _apply_filters_and_update_views will handle empty log_entries_full or empty search_text
        self._apply_filters_and_update_views()
        
        # Status bar message is now handled by _apply_filters_and_update_views, 
        # but we can add a specific search status message here if desired, or let the generic one suffice.
        if self.mw.statusBar():
            if self.current_search_text:
                self.mw.statusBar().showMessage(f"Filtre de recherche appliqué: '{self.current_search_text}'", 2000)
            else:
                self.mw.statusBar().showMessage("Filtre de recherche effacé", 2000)

    def _apply_filters_and_update_views(self):
        if self.mw.log_entries_full.empty or self.mw._is_batch_updating_ui:
            if self.mw.selected_messages_list: self.mw.selected_messages_list.set_all_items_data([])
            # Potentially update status bar or other UI elements for empty/no results
            return

        # Start with a mask that includes all entries
        combined_mask = pd.Series([True] * len(self.mw.log_entries_full), index=self.mw.log_entries_full.index)

        # 1. Apply Log Level Filter
        active_levels = [level for level, active in self.selected_log_levels.items() if active]
        if len(active_levels) < len(self.selected_log_levels): # Only filter if not all levels are selected
            combined_mask &= self.mw.log_entries_full['log_level'].isin(active_levels)

        # 2. Apply Message Type Filter (from tree)
        tree_selected_types = set()
        if self.mw.message_types_tree:
            for i in range(self.mw.message_types_tree.topLevelItemCount()):
                item = self.mw.message_types_tree.topLevelItem(i)
                if item.checkState(0) == QtCore.Qt.Checked:
                    tree_selected_types.add(item.text(0))
        
        if tree_selected_types: # Only filter if some types are selected
            # Check if all types from the tree are selected. If so, no need to filter by type.
            all_possible_types_in_tree = set()
            if self.mw.message_types_tree:
                for i in range(self.mw.message_types_tree.topLevelItemCount()):
                    all_possible_types_in_tree.add(self.mw.message_types_tree.topLevelItem(i).text(0))
            
            if tree_selected_types != all_possible_types_in_tree:
                 combined_mask &= self.mw.log_entries_full['logger_name'].isin(tree_selected_types)

        # 3. Apply Timeline Time Filter
        if self.timeline_filter_active and self.timeline_filter_start_time and self.timeline_filter_end_time:
            combined_mask &= (self.mw.log_entries_full['datetime_obj'] >= self.timeline_filter_start_time) & \
                             (self.mw.log_entries_full['datetime_obj'] < self.timeline_filter_end_time)

        # 4. Apply Full-Text Search Filter
        if self.current_search_text and self.current_search_text.strip():
            matching_indices = self._search_fts_index(self.current_search_text)
            
            # Create a boolean mask based on FTS results.
            # If search_text was provided but FTS found no matches, fts_mask will be all False.
            # If FTS found matches, fts_mask will be True for those indices.
            # self.mw.log_entries_full.index should correspond to rowids in FTS.
            fts_mask = self.mw.log_entries_full.index.isin(list(matching_indices))
            combined_mask &= fts_mask
        # If current_search_text is empty or only whitespace, no FTS filtering is applied here.

        # Apply the combined mask
        filtered_df = self.mw.log_entries_full[combined_mask]
        filtered_entries_list = filtered_df.to_dict('records')

        if self.mw.selected_messages_list:
            self.mw.selected_messages_list.set_all_items_data(filtered_entries_list)
        
        if self.mw.statusBar():
            status_message = f"{len(filtered_entries_list)} messages affichés."
            if self.timeline_filter_active:
                status_message += f" (Intervalle: {self.timeline_filter_start_time.strftime('%H:%M:%S')} - {self.timeline_filter_end_time.strftime('%H:%M:%S')})"
            self.mw.statusBar().showMessage(status_message, 3000)

    def on_timeline_bar_clicked(self, time_start, time_end):
        if self.mw._is_batch_updating_ui: return
        
        self.timeline_filter_active = True
        self.timeline_filter_start_time = time_start
        self.timeline_filter_end_time = time_end
        
        self._apply_filters_and_update_views()

    def on_message_selected(self):
        if not self.mw.selected_messages_list or not self.mw.details_text: return
        selected_items = self.mw.selected_messages_list.selectedItems()
        if not selected_items: 
            self.mw.details_text.clear()
            return
        
        entry_data = selected_items[0].data(0, QtCore.Qt.UserRole)
        if entry_data and isinstance(entry_data, dict):
            # Reconstruct the full_entry string
            # 'datetime' column stores the original string representation of the timestamp
            dt_str = entry_data.get('datetime', '') 
            lvl = entry_data.get('log_level', '')
            lgr = entry_data.get('logger_name', '')
            # 'message' column stores the potentially multi-line message content
            msg = entry_data.get('message', '') 
            
            reconstructed_full_entry = f"{dt_str} {lvl} [{lgr}] {msg}"
            self.mw.details_text.setPlainText(reconstructed_full_entry)
        else:
            self.mw.details_text.clear()

    def _get_currently_visible_message_types_sorted_by_count(self):
        if not self.mw.message_types_tree: return []
        visible_types_with_counts = []
        for i in range(self.mw.message_types_tree.topLevelItemCount()):
            item = self.mw.message_types_tree.topLevelItem(i)
            if not item.isHidden():
                try:
                    count = int(item.text(1))
                    visible_types_with_counts.append((item.text(0), count))
                except (ValueError, TypeError):
                    continue
        visible_types_with_counts.sort(key=lambda x: (-x[1], x[0]))
        return [name for name, count in visible_types_with_counts]

    def _select_top_n_types_logic(self, top_n):
        if not self.mw.message_types_tree or self.mw.log_entries_full.empty:
            return

        # Get currently selected levels
        selected_levels = {level for level, is_selected in self.selected_log_levels.items() if is_selected}
        df = self.mw.log_entries_full[self.mw.log_entries_full['log_level'].isin(selected_levels)]

        if df.empty:
            return

        # Get top N logger names by frequency
        top_types = df['logger_name'].value_counts().nlargest(top_n).index.to_list()
        top_types_set = set(top_types)

        self.mw._enter_batch_update()
        try:
            tree = self.mw.message_types_tree
            for i in range(tree.topLevelItemCount()):
                item = tree.topLevelItem(i)
                logger_name = item.text(0)
                if logger_name in top_types_set:
                    item.setCheckState(0, QtCore.Qt.Checked)
                else:
                    item.setCheckState(0, QtCore.Qt.Unchecked)
        finally:
            self.mw._exit_batch_update()
        self.trigger_timeline_update_from_selection()

    def select_top5_message_types(self):
        self._select_top_n_types_logic(5)

    def select_top10_message_types(self):
        self._select_top_n_types_logic(10)

    def set_check_state_for_all_types(self, check_state):
        if self.mw._is_batch_updating_ui or not self.mw.message_types_tree: return
        self.mw._enter_batch_update()
        self.mw.message_types_tree.blockSignals(True)
        for i in range(self.mw.message_types_tree.topLevelItemCount()):
            item = self.mw.message_types_tree.topLevelItem(i)
            if item.checkState(0) != check_state:
                item.setCheckState(0, check_state)
        self.mw.message_types_tree.blockSignals(False)
        self.mw._exit_batch_update()
        self.trigger_timeline_update_from_selection()

    def set_check_state_for_visible_types(self, check_state):
        if self.mw._is_batch_updating_ui: return
        self.mw._enter_batch_update()
        self.mw.message_types_tree.blockSignals(True)
        for i in range(self.mw.message_types_tree.topLevelItemCount()):
            item = self.mw.message_types_tree.topLevelItem(i)
            if not item.isHidden():
                if item.checkState(0) != check_state:
                    item.setCheckState(0, check_state)
        self.mw.message_types_tree.blockSignals(False)
        self.mw._exit_batch_update()
        self.trigger_timeline_update_from_selection() # This will call _apply_filters_and_update_views indirectly

    def toggle_log_level_filter(self, level_name, is_checked):
        if level_name in self.selected_log_levels:
            self.selected_log_levels[level_name] = is_checked
            self._rebuild_message_types_data_and_list(select_all_visible=True)
            self._apply_filters_and_update_views()
            # MainWindow should have a method to update button text/style if counts are displayed on them
            self.update_log_summary_display() # This updates log level button texts with counts
            if self.mw.statusBar():
                active_levels = [lvl for lvl, active in self.selected_log_levels.items() if active]
                if not active_levels:
                    msg = "Aucun niveau de log sélectionné."
                elif len(active_levels) == len(self.selected_log_levels):
                    msg = "Tous les niveaux de log sélectionnés."
                else:
                    msg = f"Filtre de niveau de log mis à jour: {', '.join(active_levels)}"
                self.mw.statusBar().showMessage(msg, 3000)

    def filter_by_specific_level(self, level_name):
        # This method provides an exclusive filter for a given level.
        # Useful if triggered from a context menu or other UI element for quick isolation.
        if level_name in self.selected_log_levels:
            for lvl in self.selected_log_levels:
                self.selected_log_levels[lvl] = (lvl == level_name)
            
            self._rebuild_message_types_data_and_list(select_all_visible=True)
            self._apply_filters_and_update_views()
            # Update button states in UI (MainWindow needs a method for this)
            if hasattr(self.mw, 'update_log_level_button_states'): # Check if main window has this method
                self.mw.update_log_level_button_states(self.selected_log_levels)
            else: # Fallback to updating summary which also refreshes buttons if they show counts
                self.update_log_summary_display()

            if self.mw.statusBar():
                self.mw.statusBar().showMessage(f"Filtrage exclusif sur le niveau {level_name}", 3000)

    def apply_date_filter_to_timeline(self):
        date_range = getattr(self.mw, 'date_filter_range', None)
        
        if not date_range or self.mw.log_entries_full.empty:
            filtered_df = self.mw.log_entries_full
        else:
            start_qdate, end_qdate = date_range
            start_dt = datetime(start_qdate.year(), start_qdate.month(), start_qdate.day())
            end_dt = datetime(end_qdate.year(), end_qdate.month(), end_qdate.day(), 23, 59, 59, 999999)
            
            mask = (
                (self.mw.log_entries_full['datetime_obj'] >= start_dt) &
                (self.mw.log_entries_full['datetime_obj'] <= end_dt)
            )
            filtered_df = self.mw.log_entries_full[mask]

        if self.mw.timeline_canvas:
            self.mw.timeline_canvas.set_full_log_data(filtered_df)

    def set_granularity(self, granularity):
        # Update the timeline granularity and refresh the view
        if hasattr(self.mw, 'timeline_canvas') and self.mw.timeline_canvas:
            self.mw.timeline_canvas.current_time_granularity = granularity
            # Refresh the plot with selected types
            selected_types = set()
            if self.mw.message_types_tree:
                for i in range(self.mw.message_types_tree.topLevelItemCount()):
                    item = self.mw.message_types_tree.topLevelItem(i)
                    if item.checkState(0) == QtCore.Qt.Checked:
                        selected_types.add(item.text(0))
            self.mw.timeline_canvas.update_display_config(selected_types, granularity)

    def pan_timeline_left(self):
        self._pan_timeline(direction=-1)

    def pan_timeline_right(self):
        self._pan_timeline(direction=1)

    def _pan_timeline(self, direction):
        # direction: -1 for left, 1 for right
        canvas = getattr(self.mw, 'timeline_canvas', None)
        if not canvas or not hasattr(canvas, 'ax'):
            return
        # Get current xlim (matplotlib date numbers)
        xlim = canvas.ax.get_xlim()
        view_width = xlim[1] - xlim[0]
        if view_width <= 0:
            return
        # Determine pan step based on granularity
        gran = getattr(canvas, 'current_time_granularity', 'minute')
        if gran == 'minute':
            step = view_width  # Pan by one window
        elif gran == 'hour':
            step = view_width
        elif gran == 'day':
            step = view_width
        elif gran == 'week':
            step = view_width
        else:
            step = view_width
        # Pan
        new_min = xlim[0] + direction * step
        new_max = xlim[1] + direction * step
        # Clamp to data range if available
        min_num = getattr(canvas, 'full_time_min_num', None)
        max_num = getattr(canvas, 'full_time_max_num', None)
        if min_num is not None and max_num is not None:
            if new_min < min_num:
                new_min = min_num
                new_max = min_num + view_width
            if new_max > max_num:
                new_max = max_num
                new_min = max_num - view_width
        # Update the view
        if hasattr(canvas, 'plot_timeline'):
            canvas.plot_timeline(xlim_override=(new_min, new_max))

    def _build_fts_index(self, df):
        if self.fts_db_conn:
            try:
                self.fts_db_conn.close()
                self.fts_db_conn = None # Ensure it's None if closed
            except Exception as e:
                # Ideally, log this error
                print(f"Error closing existing FTS DB connection: {e}")
                self.fts_db_conn = None # Ensure it's None even if close fails
        
        if df.empty:
            # print("DataFrame is empty, skipping FTS index build.") # Optional: log or print
            return

        try:
            self.fts_db_conn = sqlite3.connect(':memory:')
            cursor = self.fts_db_conn.cursor()
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS log_index USING fts5(
                    message_content,
                    tokenize='porter unicode61'
                );
            """)

            if 'message' not in df.columns:
                print("Error: 'message' column not found in DataFrame for FTS indexing.")
                self.fts_db_conn.close()
                self.fts_db_conn = None
                return

            messages = df['message'].fillna('').astype(str)
            batch_size = 10000  # Process in batches
            
            for i in range(0, len(df), batch_size):
                batch_data = []
                # Use df.index directly for rowid if it's suitable (e.g., unique integers)
                # Or generate rowids if df.index is not simple integers
                for original_index, message_content in messages.iloc[i:i+batch_size].items():
                    batch_data.append((original_index, message_content))
                
                if batch_data:
                    cursor.executemany("INSERT INTO log_index (rowid, message_content) VALUES (?, ?)", batch_data)
            
            self.fts_db_conn.commit()
            # print(f"FTS index built successfully with {len(df)} entries.") # Optional: log or print
        except sqlite3.Error as e:
            print(f"SQLite error during FTS index build: {e}")
            if self.fts_db_conn:
                try:
                    self.fts_db_conn.close()
                except Exception as e_close:
                    print(f"Error closing FTS DB connection after build error: {e_close}")
            self.fts_db_conn = None
        except Exception as e:
            print(f"Unexpected error during FTS index build: {e}")
            if self.fts_db_conn:
                try:
                    self.fts_db_conn.close()
                except Exception as e_close:
                    print(f"Error closing FTS DB connection after unexpected build error: {e_close}")
            self.fts_db_conn = None

    def _search_fts_index(self, search_text):
        if not self.fts_db_conn or not search_text or search_text.strip() == "":
            return set()

        try:
            cursor = self.fts_db_conn.cursor()
            # FTS5 query syntax: wrap search_text in quotes for phrase search if needed,
            # or use NEAR, AND, OR, NOT operators. For simple term matching, this is okay.
            # To make it more robust, consider cleaning/preparing search_text.
            # Example: if search_text is "error X", FTS5 treats it as "error AND X".
            # If you want phrase "error X", it should be '"error X"'.
            # For now, simple matching.
            query = "SELECT rowid FROM log_index WHERE message_content MATCH ?"
            cursor.execute(query, (search_text,))
            
            matching_indices = {row[0] for row in cursor.fetchall()}
            return matching_indices
        except sqlite3.Error as e:
            print(f"SQLite error during FTS search for '{search_text}': {e}")
            return set()
        except Exception as e:
            print(f"Unexpected error during FTS search for '{search_text}': {e}")
            return set()