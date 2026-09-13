// Quick manual sanity check for fft.wasm's math, without needing a browser.
// Run with: node webfft/selftest.mjs (after `make webfft/fft.wasm`)
//
// Feeds a synthetic 1kHz sine wave through fft() and checks the loudest bin
// lands where a 1kHz tone at 48kHz/1024-point FFT should: bin ~= 21.3.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here  = path.dirname(fileURLToPath(import.meta.url));
const bytes = fs.readFileSync(path.join(here, 'fft.wasm'));
const { instance } = await WebAssembly.instantiate(bytes, {});
const { memory, samples_ptr, magnitudes_ptr, fft } = instance.exports;

const SIZE = 1024, SR = 48000, FREQ = 1000;
const samples = new Float32Array(memory.buffer, samples_ptr(), SIZE);
for (let i = 0; i < SIZE; i++) samples[i] = Math.sin(2 * Math.PI * FREQ * i / SR);

fft(SIZE);

const mags = new Float32Array(memory.buffer, magnitudes_ptr(), SIZE / 2);
let peakBin = 0, peakVal = -1;
for (let i = 0; i < mags.length; i++) if (mags[i] > peakVal) { peakVal = mags[i]; peakBin = i; }

const expected = Math.round(FREQ / SR * SIZE);
console.log(`expected bin ~${expected}, got ${peakBin} (magnitude ${peakVal.toFixed(3)})`);
process.exit(Math.abs(peakBin - expected) <= 1 ? 0 : 1);
