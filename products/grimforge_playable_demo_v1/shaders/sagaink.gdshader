shader_type canvas_item;

// "sagaink" post-process: turn the rendered frame into a stark, high-contrast,
// near-monochrome ink illustration where a single accent HUE keeps its colour
// (fire amber / rune blue / blood red) and everything else is crushed to
// grayscale with inked edges. Applied as a full-screen ColorRect on a CanvasLayer
// above the world (see main.gd --sagaink).

uniform sampler2D screen_tex : hint_screen_texture, filter_linear_mipmap;

uniform float gain : hint_range(1.0, 4.0) = 2.3;         // exposure lift (dark scenes -> full range)
uniform float desaturate : hint_range(0.0, 1.0) = 1.0;   // 1 = full grayscale base
uniform float contrast : hint_range(1.0, 3.0) = 1.3;     // tonal punch
uniform float black_point : hint_range(0.0, 0.5) = 0.03; // crush deep shadows to ink-black
uniform float white_point : hint_range(0.5, 1.0) = 0.9;  // lift highs to paper-white
uniform vec3 accent_rgb : source_color = vec3(1.0, 0.55, 0.12); // the one accent hue
uniform float accent_hue_tol : hint_range(0.0, 0.5) = 0.09;     // how close in hue to keep
uniform float accent_min_sat : hint_range(0.0, 1.0) = 0.22;     // ignore washed-out pixels
uniform float accent_boost : hint_range(1.0, 2.0) = 1.35;       // pop the accent
uniform float outline : hint_range(0.0, 1.0) = 0.7;            // inked edge strength

vec3 rgb2hsv(vec3 c) {
	vec4 K = vec4(0.0, -1.0 / 3.0, 2.0 / 3.0, -1.0);
	vec4 p = mix(vec4(c.bg, K.wz), vec4(c.gb, K.xy), step(c.b, c.g));
	vec4 q = mix(vec4(p.xyw, c.r), vec4(c.r, p.yzx), step(p.x, c.r));
	float d = q.x - min(q.w, q.y);
	float e = 1.0e-10;
	return vec3(abs(q.z + (q.w - q.y) / (6.0 * d + e)), d / (q.x + e), q.x);
}

float luma(vec3 c) {
	return dot(c, vec3(0.299, 0.587, 0.114));
}

void fragment() {
	vec2 px = SCREEN_PIXEL_SIZE;
	vec3 col = texture(screen_tex, SCREEN_UV).rgb;

	// --- inked tonal base: crush to high-contrast grayscale ---
	float l = luma(col);
	l = clamp((l - black_point) / max(white_point - black_point, 0.001), 0.0, 1.0);
	l = clamp((l - 0.5) * contrast + 0.5, 0.0, 1.0);
	vec3 gray = vec3(l);

	// --- one accent hue survives ---
	vec3 hsv = rgb2hsv(col);
	vec3 ahsv = rgb2hsv(accent_rgb);
	float hue_d = abs(hsv.x - ahsv.x);
	hue_d = min(hue_d, 1.0 - hue_d);
	float accent = smoothstep(accent_hue_tol, accent_hue_tol * 0.4, hue_d) * smoothstep(accent_min_sat, accent_min_sat + 0.12, hsv.y);
	vec3 accent_col = clamp(col * accent_boost, 0.0, 1.0);
	vec3 base = mix(gray, accent_col, accent);

	// --- inked outline: luminance Sobel on the screen ---
	float lx =
		luma(texture(screen_tex, SCREEN_UV + vec2(-px.x, 0.0)).rgb) -
		luma(texture(screen_tex, SCREEN_UV + vec2(px.x, 0.0)).rgb);
	float ly =
		luma(texture(screen_tex, SCREEN_UV + vec2(0.0, -px.y)).rgb) -
		luma(texture(screen_tex, SCREEN_UV + vec2(0.0, px.y)).rgb);
	float edge = clamp((abs(lx) + abs(ly)) * 3.0, 0.0, 1.0);
	edge = smoothstep(0.25, 0.6, edge) * outline;

	COLOR = vec4(base * (1.0 - edge), 1.0);
}
