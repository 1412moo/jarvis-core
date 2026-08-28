"use strict";

/**
 * Bounded seen-id set. Deliberately not a database or event log (design
 * scope: "과도한 event-log/DB 구현 금지") - just enough to stop a bridge
 * from re-processing the same relay event twice after a reconnect replay.
 */
class BoundedSeenSet {
  constructor(maxSize = 500) {
    this.maxSize = maxSize;
    this._set = new Set();
    this._order = [];
  }

  hasSeen(id) {
    return this._set.has(id);
  }

  markSeen(id) {
    if (this._set.has(id)) return;
    this._set.add(id);
    this._order.push(id);
    while (this._order.length > this.maxSize) {
      const oldest = this._order.shift();
      this._set.delete(oldest);
    }
  }
}

module.exports = { BoundedSeenSet };
