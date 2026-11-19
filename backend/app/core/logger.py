import logging
import re
import sys

class SensitiveDataRedactionFilter(logging.Filter):
    """
    Redacts credentials, tokens, bearer authorizations, and secrets
    from structured and unstructured log records.
    """
    PATTERNS = [
        (re.compile(r'(password["\']?\s*[:=]\s*["\'])([^"\']+)(")', re.IGNORECASE), r'\1[REDACTED]\3'),
        (re.compile(r'(token["\']?\s*[:=]\s*["\'])([^"\']+)(")', re.IGNORECASE), r'\1[REDACTED]\3'),
        (re.compile(r'(secret["\']?\s*[:=]\s*["\'])([^"\']+)(")', re.IGNORECASE), r'\1[REDACTED]\3'),
        (re.compile(r'(authorization["\']?\s*[:=]\s*["\'])([^"\']+)(")', re.IGNORECASE), r'\1[REDACTED]\3'),
        (re.compile(r'Bearer\s+[A-Za-z0-9\-_.]{10,}', re.IGNORECASE), 'Bearer [REDACTED]'),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            msg = record.msg
            for pattern, repl in self.PATTERNS:
                msg = pattern.sub(repl, msg)
            record.msg = msg
        return True

def setup_logger():
    logger = logging.getLogger("dirs")
    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s"
    )
    
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(SensitiveDataRedactionFilter())
    
    if not logger.handlers:
        logger.addHandler(stream_handler)
        
    return logger

logger = setup_logger()
