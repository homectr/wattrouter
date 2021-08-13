import winston from 'winston';
import { format } from 'logform';

import { argv } from './ENV';

const fmt = format.combine(
  format.timestamp(),
  format.printf((info) => `${info.timestamp} [${info.level}] (${info.module}) ${info.message}`)
);

export function createLogger(
  level: string,
  logName: string,
  opts?: { errorlog?: string; consolelog?: boolean }
): winston.Logger {
  const { errorlog, consolelog } = opts ?? {};
  const tr: winston.transport[] = [new winston.transports.File({ filename: logName })];

  if (errorlog) tr.push(new winston.transports.File({ filename: errorlog, level: 'error' }));
  if (consolelog) tr.push(new winston.transports.Console({ format: fmt, level: 'debug' }));

  const logger = winston.createLogger({ level: level, format: fmt, transports: tr });

  return logger;
}

const logger = createLogger(argv.verbose, argv.logfile, {
  consolelog: (argv.console ?? false) === true,
});

export default logger;
