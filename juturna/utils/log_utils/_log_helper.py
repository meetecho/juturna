import logging

from juturna.utils.log_utils import _formatters


class _JuturnaLogger:
    def __init__(self):
        self._root_logger = logging.getLogger('jt')
        self._root_handler = logging.StreamHandler()
        self._root_formatter_name = 'full'

        self._root_handler.setFormatter(
            _formatters._FORMATTERS[self._root_formatter_name]
        )
        self._root_logger.addHandler(self._root_handler)
        self._root_logger.propagate = False

    def _logger(self, logger_name: str = '') -> logging.Logger:
        return (
            self._root_logger.getChild(logger_name)
            if logger_name
            else self._root_logger
        )

    def _formatters(self) -> list:
        return list(_formatters._FORMATTERS.keys())

    def _formatter(self, formatter_name: str = '') -> str | None:
        if formatter_name == '':
            return self._root_formatter_name

        self._root_formatter_name = formatter_name
        fmt = _formatters._FORMATTERS[formatter_name]

        for handler in self._root_logger.handlers:
            handler.setFormatter(fmt)


_JT_LOGGER = _JuturnaLogger()


def jt_logger(logger_name: str = '') -> logging.Logger:
    return _JT_LOGGER._logger(logger_name)


def formatters() -> list:
    return _JT_LOGGER._formatters()


def formatter(formatter_name: str = '') -> str | None:
    return _JT_LOGGER._formatter(formatter_name)


def add_handler(
    handler: logging.Handler, formatter: str | logging.Formatter = ''
):
    formatter = (
        _formatters._FORMATTERS[formatter or _JT_LOGGER._root_formatter_name]
        if isinstance(formatter, str)
        else formatter
    )

    handler.setFormatter(formatter)
    jt_logger().addHandler(handler)
