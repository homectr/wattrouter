import mqtt from 'mqtt';
import * as ENV from './ENV';
import logger from './logger';

const log = logger.child({ module: 'mqttc' });

log.info(`connecting to ${ENV.config.mqtt?.host}`);
export const client = mqtt.connect(ENV.config.mqtt?.host, {
  clientId: ENV.config.mqtt?.clientid,
  username: ENV.config.mqtt?.username,
  password: ENV.config.mqtt?.password,
});

export type mgs_handler_t = (message: string) => boolean;

const handlers: { topic: string; handler: mgs_handler_t }[] = [];

export function addHandler(topic: string, handler: mgs_handler_t) {
  handlers.push({ topic, handler });
  client.subscribe(topic, function (err) {
    if (err) log.error(`Error subscribing to topic=${topic} err=${err}`);
  });
}

client.on('connect', function () {
  log.debug('MQTT connected');
});

client.on('error', function (err) {
  log.debug(`MQTT error=${err}`);
});

client.on('message', function (topic, message) {
  // message is Buffer
  log.debug(`MQTT received topic=${topic} msg=${message.toString()}`);
  let handled = false;
  let i = 0;
  while (!handled && i < handlers.length) {
    if (handlers[i].topic === topic) handled = handlers[i].handler(message.toString());
    i++;
  }
  if (!handled) log.warn(`Message not handled. topic=${topic} msg=${message.toString()}`);
});

export default client;
