/* In-page MQTT broker + WebSocket stub.
   The app still speaks real MQTT 3.1.1 bytes, so its codec is exercised for real. */
(() => {
  const top = window.top;
  if (!top.__rcvBroker) {
    top.__rcvBroker = {
      clients: [],
      retained: {},        // topic -> payload string
      log: [],
      enc: {},
    };
  }
  const B = top.__rcvBroker;

  const encLen = n => { const o = []; do { let b = n % 128; n = Math.floor(n / 128); if (n > 0) b |= 0x80; o.push(b); } while (n > 0); return o; };
  const encStr = s => { const b = new TextEncoder().encode(s); return [b.length >> 8, b.length & 0xff, ...b]; };
  const pk = (t, f, rest) => new Uint8Array([((t & 15) << 4) | (f & 15), ...encLen(rest.length), ...rest]);
  const match = (filter, topic) => {
    const f = filter.split('/'), t = topic.split('/');
    for (let i = 0; i < f.length; i++) { if (f[i] === '#') return true; if (f[i] !== '+' && f[i] !== t[i]) return false; }
    return f.length === t.length;
  };

  class FakeWS {
    constructor(url) {
      this.url = url; this.readyState = 0; this.subs = [];
      this.binaryType = 'arraybuffer';
      this.onopen = this.onmessage = this.onclose = this.onerror = null;
      B.clients.push(this);
      setTimeout(() => { this.readyState = 1; this.onopen && this.onopen({}); }, 1);
    }
    deliver(bytes) {
      if (this.readyState !== 1) return;
      const ab = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
      setTimeout(() => this.onmessage && this.onmessage({ data: ab }), 0);
    }
    send(data) {
      let buf = data instanceof Uint8Array ? data : new Uint8Array(data);
      let i = 0;
      while (i < buf.length) {
        const header = buf[i]; i++;
        let mult = 1, len = 0, b;
        do { b = buf[i]; i++; len += (b & 127) * mult; mult *= 128; } while (b & 128);
        const p = buf.slice(i, i + len); i += len;
        const type = header >> 4;
        if (type === 1) {                                        // CONNECT
          this.deliver(pk(2, 0, [0, 0]));                         // CONNACK ok
        } else if (type === 8) {                                  // SUBSCRIBE
          const pid = (p[0] << 8) | p[1];
          let j = 2; const added = [];
          while (j < p.length) {
            const l = (p[j] << 8) | p[j + 1]; j += 2;
            const f = new TextDecoder().decode(p.slice(j, j + l)); j += l + 1;
            this.subs.push(f); added.push(f);
          }
          this.deliver(pk(9, 0, [pid >> 8, pid & 0xff, 0]));      // SUBACK
          for (const f of added)                                  // retained delivery
            for (const t in B.retained)
              if (match(f, t) && B.retained[t] !== '')
                this.deliver(pk(3, 1, [...encStr(t), ...new TextEncoder().encode(B.retained[t])]));
        } else if (type === 3) {                                  // PUBLISH
          const tl = (p[0] << 8) | p[1];
          const topic = new TextDecoder().decode(p.slice(2, 2 + tl));
          const body = new TextDecoder().decode(p.slice(2 + tl));
          const retain = (header & 1) === 1;
          B.log.push({ topic, body, retain });
          if (retain) { if (body === '') delete B.retained[topic]; else B.retained[topic] = body; }
          for (const c of B.clients)
            if (c !== this || true) for (const f of c.subs) if (match(f, topic)) { c.deliver(pk(3, 0, [...encStr(topic), ...new TextEncoder().encode(body)])); break; }
        } else if (type === 12) {                                 // PINGREQ
          this.deliver(pk(13, 0, []));
        }
      }
    }
    close() { this.readyState = 3; const i = B.clients.indexOf(this); if (i >= 0) B.clients.splice(i, 1); this.onclose && this.onclose({}); }
  }
  FakeWS.prototype.CONNECTING = 0; FakeWS.prototype.OPEN = 1; FakeWS.prototype.CLOSING = 2; FakeWS.prototype.CLOSED = 3;
  window.WebSocket = FakeWS;

  // AudioContext để NGUYÊN BẢN THẬT: bộ trộn tiếng cần createMediaStreamDestination.
  // Kiểm thử chạy Chrome với --mute-audio nên vẫn im lặng.
})();
