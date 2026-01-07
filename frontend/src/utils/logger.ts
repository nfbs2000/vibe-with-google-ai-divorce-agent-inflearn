/**
 * 구조화된 프론트엔드 로깅 시스템
 */

export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
  NONE = 99,
}

interface LogContext {
  [key: string]: unknown;
}

class Logger {
  private level: LogLevel;
  private enableTimestamp: boolean;
  private enableColors: boolean;

  constructor() {
    // 환경 변수에서 로그 레벨 읽기
    const envLevel = import.meta.env.VITE_LOG_LEVEL || 'INFO';
    this.level = LogLevel[envLevel as keyof typeof LogLevel] || LogLevel.INFO;
    this.enableTimestamp = true;
    this.enableColors = true;
  }

  private formatTimestamp(): string {
    const now = new Date();
    const hours = now.getHours().toString().padStart(2, '0');
    const minutes = now.getMinutes().toString().padStart(2, '0');
    const seconds = now.getSeconds().toString().padStart(2, '0');
    const ms = now.getMilliseconds().toString().padStart(3, '0');
    return `${hours}:${minutes}:${seconds}.${ms}`;
  }

  private formatMessage(level: string, message: string): string[] {
    const parts: string[] = [];

    if (this.enableTimestamp) {
      parts.push(`[${this.formatTimestamp()}]`);
    }

    parts.push(`[${level}]`);
    parts.push(message);

    return parts;
  }

  private shouldLog(level: LogLevel): boolean {
    return level >= this.level;
  }

  /**
   * DEBUG 레벨 로그
   */
  debug(message: string, context?: LogContext): void {
    if (!this.shouldLog(LogLevel.DEBUG)) return;

    const parts = this.formatMessage('DEBUG', message);

    if (this.enableColors) {
      console.log(
        `%c${parts[0]} %c${parts[1]} %c${parts[2]}`,
        'color: #999',          // timestamp
        'color: #00d4ff',       // level
        'color: inherit',       // message
        context || ''
      );
    } else {
      console.log(...parts, context || '');
    }
  }

  /**
   * INFO 레벨 로그
   */
  info(message: string, context?: LogContext): void {
    if (!this.shouldLog(LogLevel.INFO)) return;

    const parts = this.formatMessage('INFO ', message);

    if (this.enableColors) {
      console.log(
        `%c${parts[0]} %c${parts[1]} %c${parts[2]}`,
        'color: #999',
        'color: #00c853',
        'color: inherit',
        context || ''
      );
    } else {
      console.log(...parts, context || '');
    }
  }

  /**
   * WARN 레벨 로그
   */
  warn(message: string, context?: LogContext): void {
    if (!this.shouldLog(LogLevel.WARN)) return;

    const parts = this.formatMessage('WARN ', message);

    if (this.enableColors) {
      console.warn(
        `%c${parts[0]} %c${parts[1]} %c${parts[2]}`,
        'color: #999',
        'color: #ffa726',
        'color: inherit',
        context || ''
      );
    } else {
      console.warn(...parts, context || '');
    }
  }

  /**
   * ERROR 레벨 로그
   */
  error(message: string, error?: Error | unknown, context?: LogContext): void {
    if (!this.shouldLog(LogLevel.ERROR)) return;

    const parts = this.formatMessage('ERROR', message);

    if (this.enableColors) {
      console.error(
        `%c${parts[0]} %c${parts[1]} %c${parts[2]}`,
        'color: #999',
        'color: #f44336; font-weight: bold',
        'color: inherit',
        context || ''
      );
    } else {
      console.error(...parts, context || '');
    }

    if (error) {
      console.error(error);
    }
  }

  /**
   * API 요청 로그
   */
  apiRequest(method: string, url: string, data?: unknown): void {
    if (!this.shouldLog(LogLevel.DEBUG)) return;

    this.debug(`→ API Request: ${method} ${url}`, data ? { data } : undefined);
  }

  /**
   * API 응답 로그
   */
  apiResponse(
    method: string,
    url: string,
    status: number,
    duration: number,
    data?: unknown
  ): void {
    if (!this.shouldLog(LogLevel.DEBUG)) return;

    const context: LogContext = {
      status,
      duration: `${duration.toFixed(0)}ms`,
    };

    if (data) {
      context.data = data;
    }

    const statusColor =
      status >= 200 && status < 300
        ? '✓'
        : status >= 400
        ? '✗'
        : '⚠';

    this.debug(`← API Response: ${statusColor} ${method} ${url}`, context);
  }

  /**
   * API 에러 로그
   */
  apiError(method: string, url: string, error: Error | unknown): void {
    this.error(`✗ API Error: ${method} ${url}`, error);
  }

  /**
   * 컴포넌트 마운트 로그
   */
  mount(componentName: string, props?: LogContext): void {
    if (!this.shouldLog(LogLevel.DEBUG)) return;

    this.debug(`📦 Mount: ${componentName}`, props);
  }

  /**
   * 컴포넌트 언마운트 로그
   */
  unmount(componentName: string): void {
    if (!this.shouldLog(LogLevel.DEBUG)) return;

    this.debug(`📤 Unmount: ${componentName}`);
  }

  /**
   * 사용자 액션 로그
   */
  action(actionName: string, context?: LogContext): void {
    if (!this.shouldLog(LogLevel.INFO)) return;

    this.info(`🎯 Action: ${actionName}`, context);
  }

  /**
   * 네비게이션 로그
   */
  navigate(from: string, to: string): void {
    if (!this.shouldLog(LogLevel.INFO)) return;

    this.info(`🧭 Navigate: ${from} → ${to}`);
  }

  /**
   * 성능 측정 시작
   */
  timeStart(label: string): void {
    if (!this.shouldLog(LogLevel.DEBUG)) return;
    console.time(label);
  }

  /**
   * 성능 측정 종료
   */
  timeEnd(label: string): void {
    if (!this.shouldLog(LogLevel.DEBUG)) return;
    console.timeEnd(label);
  }

  /**
   * 그룹 로그 시작
   */
  group(label: string): void {
    if (!this.shouldLog(LogLevel.DEBUG)) return;
    console.group(label);
  }

  /**
   * 그룹 로그 종료
   */
  groupEnd(): void {
    if (!this.shouldLog(LogLevel.DEBUG)) return;
    console.groupEnd();
  }

  /**
   * 테이블 로그
   */
  table(data: unknown): void {
    if (!this.shouldLog(LogLevel.DEBUG)) return;
    console.table(data);
  }

  /**
   * 로그 레벨 설정
   */
  setLevel(level: LogLevel): void {
    this.level = level;
  }

  /**
   * 현재 로그 레벨 조회
   */
  getLevel(): LogLevel {
    return this.level;
  }
}

// 싱글톤 인스턴스
export const logger = new Logger();

// 개발 환경에서 전역으로 접근 가능하도록 설정
if (import.meta.env.DEV) {
  (window as typeof window & { logger?: Logger }).logger = logger;
}
