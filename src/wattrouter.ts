import logger from './logger';
import * as mqtt from './mqttclient';
import * as ENV from './ENV';
import axios from 'axios';
import parser from 'fast-xml-parser';

const log = logger.child({ module: 'wattmgr' });
let isRunning = true;

mqtt.client.on('connect', function () {
  if (mqtt.client.disconnecting) return;
  const topic = `${ENV.config.mqtt?.clientid ?? ''}/cmd`;
  log.info(`Subscribing to topic=${topic}`);
  mqtt.addHandler(topic, function (cmd): boolean {
    log.info(`Received command = ${cmd}`);
    return true;
  });
});

export function start() {
  log.info('Starting Wattrouter Bridge');
  isRunning = true;
  loop();
}

export function stop() {
  log.info('Stopping Wattrouter Bridge');

  setTimeout(() => {
    mqtt.client.end();
    isRunning = false;
  }, 1000);
}

export async function readWR() {
  try {
    const rt = ENV.config.mqtt.clientid;
    const url = `http://${ENV.config.wattrouter.host}/meas.xml`;
    log.debug(`Connecting to wattrouter host=${url}`);
    const { data } = await axios.get(url, {
      timeout: 1000,
      responseType: 'text',
    });
    const json = parser.parse(data);
    // process inputs
    for (let i = 1; i < 8; i++) {
      const itm = `I${i}`;
      if (itm in json.meas) {
        mqtt.client.publish(`${rt}/${itm}/P`, json.meas[itm].P.toFixed(2));
        log.debug(`Publish: ${itm}/P=${json.meas[itm].P.toFixed(2)}`);
      }
    }
    // process outputs
    for (let i = 1; i < 15; i++) {
      const itm = `O${i}`;
      if (itm in json.meas) {
        mqtt.client.publish(`${rt}/${itm}/P`, json.meas[itm].P.toFixed(2));
        mqtt.client.publish(`${rt}/${itm}/HN`, json.meas[itm].HN);
        mqtt.client.publish(`${rt}/${itm}/T`, json.meas[itm].T);
        log.debug(
          `Publish: ${itm} P=${json.meas[itm].P.toFixed(2)} HN=${json.meas[itm].HN} T=${
            json.meas[itm].T
          }`
        );
      }
    }

    // total power
    if ('PPS' in json.meas) {
      mqtt.client.publish(`${rt}/PPS`, json.meas.PPS.toFixed(2));
      log.info(`PPS=${json.meas.PPS}`);
    } else {
      log.error('PPS attribute not present.');
    }

    const s = [
      'DQ1',
      'DQ2',
      'DQ3',
      'DQ4', // temp sensors
      'VAC', // voltage
      'EL1', // L1 voltage error 1/0
      'ETS', // temperature sensor error 1/0
      'ILT', // low-tariff indicator 1/0
      'ICW', // combiwatt indicator 1/0
      'ITS', // test indicator 1/0
      'IDST', // daylight saving indicator 1/0
      'ISC', // SCGateway module indicator 1/0
      'SRT', // Sun rise time HH:MM
      'DW', // day of week 0(Mon)-6(Sun)
    ];

    for (const i in s) {
      if (i in json.meas) {
        log.debug(`Publish: ${i}=${json.meas[i]}`);
        mqtt.client.publish(`${rt}/${i}`, json.meas[i]);
      }
    }
  } catch (error) {
    console.error(error);
  }
}

let lastAlive = 0;
const aliveInterval = 1000 * 60 * 15;
let lastRead = 0;

function loop() {
  if (Date.now() - lastAlive > aliveInterval) {
    log.info('Wattrouter alive');
    lastAlive = Date.now();
  }

  if (Date.now() - lastRead > ENV.config.wattrouter.interval * 1000) {
    readWR();
    lastRead = Date.now();
  }

  // longer timeout results in longer wait before service restart
  if (isRunning) setTimeout(loop, 1000);
}
