/*
 * Minimal, dependency-free radix-2 FFT for the mobile web UI.
 *
 * Compiled to a *standalone* wasm module (no Emscripten JS runtime) -- the
 * browser just does WebAssembly.instantiate() and pokes floats directly into
 * the module's linear memory. See mobile.js for the loader.
 *
 * Exposed ABI (all indices/sizes in float32 elements, memory is one big
 * float32 buffer starting at address 0):
 *
 *   samples_ptr()               -> byte offset of the input sample buffer
 *                                   (MAX_FFT_SIZE float32 samples, mono, [-1,1])
 *   magnitudes_ptr()             -> byte offset of the output magnitude buffer
 *                                   (MAX_FFT_SIZE/2 float32 bins)
 *   fft(size)                    -> runs a Hann-windowed real FFT over the
 *                                   first `size` samples (power of two, <=
 *                                   MAX_FFT_SIZE) and fills the magnitude
 *                                   buffer with size/2 bins, normalised to
 *                                   roughly [0, 1].
 */

#define MAX_FFT_SIZE 4096

static float samples[MAX_FFT_SIZE];
static float re[MAX_FFT_SIZE];
static float im[MAX_FFT_SIZE];
static float mags[MAX_FFT_SIZE / 2];

__attribute__((export_name("samples_ptr")))
float *samples_ptr(void) { return samples; }

__attribute__((export_name("magnitudes_ptr")))
float *magnitudes_ptr(void) { return mags; }

__attribute__((export_name("max_fft_size")))
int max_fft_size(void) { return MAX_FFT_SIZE; }

/* Tiny local math -- we're freestanding, no libm. */
static float my_sqrtf(float x) {
    if (x <= 0.0f) return 0.0f;
    float guess = x;
    for (int i = 0; i < 12; i++) guess = 0.5f * (guess + x / guess);
    return guess;
}

/* Cosine via a 6-term Taylor/minimax-ish series after range reduction to
 * [-pi, pi]; plenty accurate for windowing + twiddle factors. */
static const float PI = 3.14159265358979323846f;
static const float TWO_PI = 6.28318530717958647692f;

static float my_cosf(float x) {
    while (x >  PI) x -= TWO_PI;
    while (x < -PI) x += TWO_PI;
    float x2 = x * x;
    /* cos(x) ~= 1 - x^2/2 + x^4/24 - x^6/720 + x^8/40320 */
    return 1.0f + x2 * (-0.5f + x2 * (1.0f/24.0f + x2 * (-1.0f/720.0f + x2 * (1.0f/40320.0f))));
}

static float my_sinf(float x) {
    return my_cosf(x - PI * 0.5f);
}

static int is_pow2(int n) { return n > 0 && (n & (n - 1)) == 0; }

/* Fast approximate log2, via the classic bit-trick (Ian Stephenson / Laurent
 * de Soras). Accurate enough for a dB scale used purely for bar heights. */
static float my_log2f(float x) {
    union { float f; unsigned int i; } vx = { x };
    union { unsigned int i; float f; } mx = { (vx.i & 0x007FFFFFu) | 0x3f000000u };
    float y = (float)vx.i * 1.1920928955078125e-7f; /* vx.i / 2^23 */
    return y - 124.22551499f - 1.498030302f * mx.f - 1.72587999f / (0.3520887068f + mx.f);
}

__attribute__((export_name("fft")))
void fft(int size) {
    if (size < 2 || size > MAX_FFT_SIZE || !is_pow2(size)) return;

    /* Hann window + bit-reversal permutation straight into re[]/im[]. */
    int bits = 0;
    while ((1 << bits) < size) bits++;

    for (int i = 0; i < size; i++) {
        float w = 0.5f - 0.5f * my_cosf(TWO_PI * i / (size - 1));
        int rev = 0;
        for (int b = 0; b < bits; b++)
            if (i & (1 << b)) rev |= 1 << (bits - 1 - b);
        re[rev] = samples[i] * w;
        im[rev] = 0.0f;
    }

    /* Iterative Cooley-Tukey, decimation in time. */
    for (int len = 2; len <= size; len <<= 1) {
        float ang = -TWO_PI / len;
        float wr = my_cosf(ang), wi = my_sinf(ang);
        for (int i = 0; i < size; i += len) {
            float curr = 1.0f, curi = 0.0f;
            for (int j = 0; j < len / 2; j++) {
                float ur = re[i + j],           ui = im[i + j];
                float vr = re[i + j + len/2] * curr - im[i + j + len/2] * curi;
                float vi = re[i + j + len/2] * curi + im[i + j + len/2] * curr;
                re[i + j]           = ur + vr;
                im[i + j]           = ui + vi;
                re[i + j + len/2]   = ur - vr;
                im[i + j + len/2]   = ui - vi;
                float nr = curr * wr - curi * wi;
                float ni = curr * wi + curi * wr;
                curr = nr; curi = ni;
            }
        }
    }

    /* Magnitude, log-scaled and roughly normalised to [0, 1]. */
    float scale = 2.0f / size;
    for (int k = 0; k < size / 2; k++) {
        float mr = re[k] * scale, mi = im[k] * scale;
        float mag = my_sqrtf(mr * mr + mi * mi);
        /* map ~[0, 1.4] linear amplitude onto [0,1] with a log curve so quiet
         * content is still visible, matching the punchy look of the sketch. */
        float db = mag > 1e-6f ? 6.0205999f * my_log2f(mag) : -120.0f;
        float norm = (db + 60.0f) / 60.0f;
        if (norm < 0.0f) norm = 0.0f;
        if (norm > 1.0f) norm = 1.0f;
        mags[k] = norm;
    }
}
