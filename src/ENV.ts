import fs from 'fs';
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
    /** mqtt client id **/
    client_id: string;
    /** mqtt host address **/
    host: string;
    username?: string;
    password?: string;
  };
  wattrouter: {
    /** wattrouter host address **/
    host: string;
    /** interval in seconds to poll wattrouter **/
    interval: number;
  };
}

const defaultConfig: FileConfig = {
  mqtt: {
    client_id: 'wattrouter',
    host: 'tcp://localhost',
  },
  wattrouter: {
    host: 'http://localhost',
    interval: 5,
  },
};

export const config = readConfig(argv.config);

export function readConfig(cfgFileName: string): FileConfig {
  let cfg: FileConfig = defaultConfig; 
  if (!fs.existsSync(cfgFileName)) {
    console.error(`Configuration file ${cfgFileName} not found. If you are running in a container, you may need to check the configuration file in mounted location.`);
    process.exit(1);
  }
  try {
    const data = fs.readFileSync(cfgFileName, { encoding: 'utf8', flag: 'r' });
    console.log('Reading configuration from %s', cfgFileName); 
    cfg = JSON.parse(data);
  } catch (err) {
    console.error(`Error reading configuration from ${cfgFileName} err=${err}`);
  }

  return { ...defaultConfig, ...cfg };
}
