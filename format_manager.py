class FormatManager:
    def __init__(self):
        # This format is specific to the log files being analyzed.
        # It includes milliseconds, which is important for chronological sorting.
        self.datetime_format = "%Y-%m-%d %H:%M:%S,%f"

    def get_format(self):
        """Returns the currently configured datetime format string."""
        return self.datetime_format
