import logging
import datetime


class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[36m',
        'INFO': '\033[32m',
        'WARNING': '\033[33m',
        'ERROR': '\033[31m',
        'CRITICAL': '\033[35m',
    }
    RESET = '\033[0m'
    BOLD = '\033[1m'

    def __init__(self, fmt=None, datefmt=None, style='%'):
        super().__init__(fmt, datefmt, style)

    def format(self, record):
        original_levelname = record.levelname

        if record.levelname in self.COLORS:
            # Pad levelname to 8 characters before coloring
            padded_level = f"{record.levelname:<8}"
            colored_levelname = \
                f'{self.COLORS[record.levelname]}{self.BOLD}{padded_level}{self.RESET}'
            record.levelname = colored_levelname

        formatted = super().format(record)
        record.levelname = original_levelname

        return formatted

    def formatMessage(self, record):
        """
        Formats the message part of the log record, stripping a redundant logger
        name prefix if present.
        """
        # First, let the base formatter handle standard message formatting
        # (e.g., string interpolation for %s, %d, etc.)
        formatted_message = super().formatMessage(record)

        # Extract the short name of the logger (last component of hierarchical name)
        logger_short_name = record.name.split('.')[-1]

        # Construct the expected redundant prefix with a trailing space
        prefix_to_check = f'{logger_short_name} '

        # Check if the message starts with this prefix and remove it if found
        if formatted_message.startswith(prefix_to_check):
            return formatted_message[len(prefix_to_check):]
        else:
            return formatted_message


class JsonFormatter(logging.Formatter):
    def format(self, record):
        import json

        log_obj = {
            'timestamp': datetime.datetime.fromtimestamp(
                record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_obj, default=str)


_FORMATTERS = {
    'simple': logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
    'colored': ColoredFormatter(
        '%(asctime)s | %(levelname)s | %(name)-23s | %(message)s'),
    'full': logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)-23s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'),
    'compact': logging.Formatter(
        '%(asctime)s | %(levelname).1s | %(name)-23s | %(message)s',
        datefmt='%H:%M:%S'),
    'development': ColoredFormatter(  # Use ColoredFormatter
        ('%(asctime)s | %(levelname)s |'  # Removed -8s padding
         '%(name)s:%(lineno)d | %(funcName)s() | %(message)s'),
        datefmt='%H:%M:%S'),
    'minimal': logging.Formatter('%(levelname)s: %(message)s'),
    'json': JsonFormatter(),
}