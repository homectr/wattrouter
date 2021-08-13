import EventEmitter from 'events';
import logger from './logger';

const log = logger.child({ module: 'output' });

export default class Output extends EventEmitter {
  id: string;
  priority: number;
  maxPower: number;
  currPower: number; // current output power - can be 0-maxPower
  dcIsLinear: boolean; // is duty cycle linear
  dcFn: [number, number][]; // duty-cycle function points [dc,power][]
  pwrDC: number; // pwm duty cycle
  dcEnabled: boolean; // management by duty cycle is enabled?
  isEnabled: boolean; // is output enabled?
  statsUpdatedAt: number; // when were stats udpdated

  constructor(props: {
    id: string;
    priority: number;
    power: number;
    dcEnabled?: boolean;
    dcFn?: [number, number][];
  }) {
    super();
    const { id, priority, power: maxPower, dcEnabled, dcFn } = props;

    this.id = id;
    this.priority = priority;
    this.maxPower = maxPower;
    this.currPower = 0.0;
    this.pwrDC = 0;
    this.dcEnabled = (dcEnabled ?? false) || dcFn !== null;
    this.isEnabled = true;
    this.dcFn = dcFn ?? [];
    this.dcIsLinear = dcFn == null && this.dcEnabled;

    this.statsUpdatedAt = 0;
  }

  public open() {
    this.emit('open');
    log.info(`Output opened o=${this.id}`);
  }

  public open100() {
    if (this.currPower == 0) this.open();
    this.currPower = this.maxPower;
    this.pwrDC = 100;
  }

  public close() {
    if (this.currPower == 0) return;
    this.currPower = 0;
    this.pwrDC = 0;
    this.emit('dc', 0);
    this.emit('close');
    log.info(`Output closed o=${this.id}`);
  }

  public disable() {
    if (!this.isEnabled) return;
    this.isEnabled = false;
    this.close();
    this.emit('disable');
    log.info(`Output disabled o=${this.id}`);
  }

  public enable() {
    if (this.isEnabled) return;
    this.isEnabled = true;
    this.emit('enable');
    log.info(`Output enabled o=${this.id}`);
  }

  public getDcFnByDc(dc: number): [number, number] {
    if (this.dcFn == null) throw 'No duty-cycle function defined';

    let pp = this.dcFn[0];
    let i = 0;

    while (i < this.dcFn.length && dc < this.dcFn[i][0]) i++;

    if (i < this.dcFn.length) pp = this.dcFn[i];
    else pp = this.dcFn[this.dcFn.length - 1];

    log.debug(`DC2DCFN fn=${pp}`);

    return pp;
  }

  public getDcFnByPower(pwr: number): [number, number] {
    if (this.dcFn == null) throw 'No duty-cycle function defined';
    let pp = this.dcFn[0];
    let i = 0;

    while (i < this.dcFn.length) {
      if (pwr > this.dcFn[i][1]) {
        pp = this.dcFn[i];
        i++;
      } else break;
    }

    if (i > this.dcFn.length) pp = this.dcFn[this.dcFn.length - 1];

    log.debug(`PWR2DCFN pwr=${pwr} fn=${pp}`);

    return pp;
  }

  public getPower() {
    return this.currPower;
  }

  public setPower(pwr: number): number {
    if (!this.isEnabled || pwr <= 0 || (!this.dcEnabled && pwr < this.maxPower)) {
      this.close();
      return 0;
    }

    let dc = 0;

    if (pwr >= this.maxPower) {
      pwr = this.maxPower;
      dc = 100;
    } else {
      if (this.dcIsLinear) {
        dc = Math.round((pwr * 100) / this.maxPower);
        log.debug(`PWR->PP dc=${dc} pwr=${pwr}`);
      } else {
        [dc, pwr] = this.getDcFnByPower(pwr);
        log.debug(`PWR->PP dc=${dc} pwr=${pwr}`);
      }
    }

    if (dc == 0) this.close();
    else {
      if (this.currPower == 0 && pwr > 0) this.open();

      this.currPower = pwr;
      this.pwrDC = dc;

      this.emit('dc', this.pwrDC);
    }

    return this.currPower;
  }

  public setDC(dc: number): number {
    if (!this.isEnabled) return 0;

    let pwr = 0;
    if (dc <= 0) {
      this.close();
      return 0;
    } else if (dc >= 100 || !this.dcEnabled) {
      this.open100();
      return 100;
    }

    if (this.dcIsLinear) {
      pwr = (this.maxPower * dc) / 100;
      log.debug(`DC->PP dc=${dc} pwr=${pwr.toFixed(2)}`);
    } else {
      [dc, pwr] = this.getDcFnByDc(dc);
      log.debug(`DC->PP dc=${dc} pwr=${pwr.toFixed(2)}`);
    }

    if (dc == 0) this.close();
    else {
      if (this.currPower == 0) this.open();
      this.pwrDC = dc;
      this.currPower = pwr;
    }

    this.emit('dc', this.pwrDC);

    return dc;
  }

  public getDC() {
    return this.pwrDC;
  }

  public processCmd(cmd: string, value: string): boolean {
    log.debug(`CMD o=${this.id} cmd=${cmd} val=${value}`);
    let h = false;
    if (cmd == 'toggle') {
      if (value == 'on') {
        this.open100();
        h = true;
      }
      if (value == 'off') {
        this.close();
        h = true;
      }
    }
    if (cmd == 'enabled') {
      if (value == 'off') {
        this.disable();
        h = true;
      }
      if (value == 'on') {
        this.enable();
        h = true;
      }
    }
    return h;
  }
}
