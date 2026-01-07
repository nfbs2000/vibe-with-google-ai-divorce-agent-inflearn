"""
구조화된 로깅 설정
"""
import logging
import sys
from datetime import datetime
from typing import Optional

# ANSI 컬러 코드
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # 레벨별 컬러
    DEBUG = "\033[36m"      # Cyan
    INFO = "\033[32m"       # Green
    WARNING = "\033[33m"    # Yellow
    ERROR = "\033[31m"      # Red
    CRITICAL = "\033[35m"   # Magenta

    # 컴포넌트별 컬러
    TIMESTAMP = "\033[90m"  # Gray
    MODULE = "\033[94m"     # Blue
    REQUEST = "\033[96m"    # Light Cyan


class ColoredFormatter(logging.Formatter):
    """컬러와 구조화된 포맷을 가진 로그 포매터"""

    LEVEL_COLORS = {
        logging.DEBUG: Colors.DEBUG,
        logging.INFO: Colors.INFO,
        logging.WARNING: Colors.WARNING,
        logging.ERROR: Colors.ERROR,
        logging.CRITICAL: Colors.CRITICAL,
    }

    LEVEL_NAMES = {
        logging.DEBUG: "DEBUG",
        logging.INFO: "INFO ",
        logging.WARNING: "WARN ",
        logging.ERROR: "ERROR",
        logging.CRITICAL: "CRIT ",
    }

    def format(self, record: logging.LogRecord) -> str:
        # 타임스탬프
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S.%f")[:-3]
        timestamp_str = f"{Colors.TIMESTAMP}[{timestamp}]{Colors.RESET}"

        # 로그 레벨
        level_color = self.LEVEL_COLORS.get(record.levelno, "")
        level_name = self.LEVEL_NAMES.get(record.levelno, record.levelname)
        level_str = f"{level_color}{Colors.BOLD}[{level_name}]{Colors.RESET}"

        # 모듈명
        module_name = record.name.split('.')[-1][:20]
        module_str = f"{Colors.MODULE}[{module_name:>20}]{Colors.RESET}"

        # 메시지
        message = record.getMessage()

        # 기본 포맷
        log_line = f"{timestamp_str} {level_str} {module_str} {message}"

        # 예외 정보가 있으면 추가
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            log_line += f"\n{Colors.ERROR}{exc_text}{Colors.RESET}"

        return log_line


class RequestLogFormatter(logging.Formatter):
    """API 요청/응답 로그 전용 포매터"""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S.%f")[:-3]

        # 요청 정보 추출
        method = getattr(record, 'method', 'N/A')
        path = getattr(record, 'path', 'N/A')
        status = getattr(record, 'status_code', 'N/A')
        duration = getattr(record, 'duration_ms', 0)

        # 상태 코드별 컬러
        if isinstance(status, int):
            if 200 <= status < 300:
                status_color = Colors.INFO
            elif 300 <= status < 400:
                status_color = Colors.WARNING
            else:
                status_color = Colors.ERROR
        else:
            status_color = Colors.RESET

        return (
            f"{Colors.TIMESTAMP}[{timestamp}]{Colors.RESET} "
            f"{Colors.REQUEST}[API]{Colors.RESET} "
            f"{Colors.BOLD}{method:>6}{Colors.RESET} "
            f"{path:50} "
            f"{status_color}{status:>3}{Colors.RESET} "
            f"{Colors.DIM}{duration:>6.0f}ms{Colors.RESET}"
        )


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    enable_colors: bool = True
) -> None:
    """
    애플리케이션 로깅 설정

    Args:
        level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 로그 파일 경로 (None이면 파일 로깅 비활성화)
        enable_colors: 컬러 출력 활성화 여부
    """
    # 로그 레벨 설정
    log_level = getattr(logging, level.upper(), logging.INFO)

    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    if enable_colors and sys.stdout.isatty():
        console_handler.setFormatter(ColoredFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
                datefmt="%H:%M:%S"
            )
        )

    root_logger.addHandler(console_handler)

    # 파일 핸들러 (옵션)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        )
        root_logger.addHandler(file_handler)

    # Uvicorn 로거 설정
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.setLevel(logging.INFO)

    # 외부 라이브러리 로그 레벨 조정
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    logging.info(f"Logging initialized - Level: {level}, Colors: {enable_colors}")


def get_api_logger() -> logging.Logger:
    """API 요청/응답 로깅용 로거 반환"""
    logger = logging.getLogger("api_requests")

    # API 로거용 별도 핸들러
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(RequestLogFormatter())
        logger.addHandler(handler)
        logger.propagate = False

    return logger
