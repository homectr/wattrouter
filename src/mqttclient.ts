import mqtt from 'mqtt';
import * as ENV from './ENV';
import logger from './logger';

const log = logger.child({ module: 'mqttc' });

export const LWTtopic = `${ENV.config.mqtt?.client_id}/status`;

const options: mqtt.IClientOptions = {
  clientId: ENV.config.mqtt?.client_id,
  username: ENV.config.mqtt?.username,
  password: ENV.config.mqtt?.password,
  will: {
    topic: LWTtopic,
    payload: Buffer.from('OFF'),
    qos: 1,
    retain: true,
  },
};

log.info(`Connecting to MQTT host ${ENV.config.mqtt?.host}: clientId=${options.clientId} username=${options?.username ?? 'none'} password=${options?.password ? 'yes' : 'no'}`);
export const client = mqtt.connect(ENV.config.mqtt?.host, options);

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
  client.publish(LWTtopic, 'ON', { qos: 1, retain: true });
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
