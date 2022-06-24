import fs from 'fs';
import logger from './logger';
const yargs = require('yargs');

export const DEBUG = 'mqttc';

export const argv = yargs
  .options({
    verbose: {
      alias: 'v',
      type: 'string',
      demandOption: true,
      description: 'log verbose level',
    },
    config: {
      alias: 'c',
      type: 'string',
      demandOption: true,
      description: 'configuration file name',
    },
    logfile: {
      alias: 'l',
      type: 'string',
      demandOption: true,
      description: 'log file name',
    },
    console: {
      alias: 'o',
      type: 'boolean',
      description: 'output log to console too',
    },
  })
  .boolean('console').argv;

interface FileConfig {
  mqtt: {
    clientid: string;
    host: string;
    username?: string;
    password?: string;
  };
  wattrouter: {
    host: string;
    interval: number;
  };
}

const defaultConfig: FileConfig = {
  mqtt: {
    clientid: 'wattrouter',
    host: 'tcp://localhost',
  },
  wattrouter: {
    host: 'http://localhost',
    interval: 5,
  },
};

const log = logger.child({ module: 'env' });

export const config = readConfig(argv.config);

export function readConfig(cfgFileName: string): FileConfig {
  const data = fs.readFileSync(cfgFileName, { encoding: 'utf8', flag: 'r' });
  log.debug('Reading configuration from %s', cfgFileName);
  let cfg: FileConfig = defaultConfig;
  try {
    cfg = JSON.parse(data);
    log.debug('Configuration=', JSON.stringify(cfg));
  } catch (err) {
    console.error(`Error reading configuration from ${cfgFileName} err=${err}`);
  }

  return { ...defaultConfig, ...cfg };
}
