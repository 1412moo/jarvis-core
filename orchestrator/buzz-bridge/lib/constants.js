"use strict";

/**
 * Single shared definition of the fixed channel name, so orchestrator.js
 * and bridge.js can never drift apart on which channel they mean (audit
 * HIGH#2: they used to each read their own BUZZ_CHANNEL_ID guess and
 * silently disagree).
 */
const CHANNEL_NAME = "jarvis-buzz-bridge-slice1";

module.exports = { CHANNEL_NAME };
