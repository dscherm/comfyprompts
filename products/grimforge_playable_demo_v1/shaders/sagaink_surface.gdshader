shader_type spatial;

// Per-surface "sagaink" treatment for kit pieces whose textures we did NOT
// generate (the occult kits embed their own atlas in each GLB, in a palette the
// baked-atlas re-skin can't touch). Instead of swapping the albedo, this samples
// the piece's own embedded albedo and crushes it to high-contrast grayscale ink
// in-shader — EXCEPT saturated pixels (glowing runes, witchlight, candle flame),
// which survive as the one colour accent. Baked into the surface (not a
// full-screen pass), so the pieces still read sagaink standalone.

uniform sampler2D albedo_tex : source_color, filter_nearest_mipmap;
uniform float contrast : hint_range(1.0, 3.0) = 1.35;
uniform float black_point : hint_range(0.0, 0.5) = 0.04;
uniform float white_point : hint_range(0.5, 1.0) = 0.92;
uniform float accent_min_sat : hint_range(0.0, 1.0) = 0.30; // below this = desaturate
uniform float accent_min_val : hint_range(0.0, 1.0) = 0.42; // and must be bright (a glow, not dark foliage)
uniform float accent_boost : hint_range(1.0, 2.0) = 1.25;

float luma(vec3 c) {
	return dot(c, vec3(0.299, 0.587, 0.114));
}

float saturation(vec3 c) {
	float mx = max(c.r, max(c.g, c.b));
	float mn = min(c.r, min(c.g, c.b));
	return mx <= 0.0 ? 0.0 : (mx - mn) / mx;
}

void fragment() {
	vec4 tex = texture(albedo_tex, UV);
	float l = luma(tex.rgb);
	// carved high-contrast tonal base
	l = clamp((l - black_point) / max(white_point - black_point, 0.001), 0.0, 1.0);
	l = clamp((l - 0.5) * contrast + 0.5, 0.0, 1.0);
	vec3 gray = vec3(l);
	// only bright AND saturated pixels survive as the accent (a glowing rune or
	// flame), not dark incidental foliage — so the ground doesn't keep green flecks
	float mx = max(tex.r, max(tex.g, tex.b));
	float accent = smoothstep(accent_min_sat, accent_min_sat + 0.14, saturation(tex.rgb))
		* smoothstep(accent_min_val, accent_min_val + 0.14, mx);
	vec3 accent_col = clamp(tex.rgb * accent_boost, 0.0, 1.0);
	ALBEDO = mix(gray, accent_col, accent);
	ROUGHNESS = 0.95;
	METALLIC = 0.0;
}
