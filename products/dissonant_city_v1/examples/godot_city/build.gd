extends Node3D
# Reconstructs the DissonantCity from the kit GLBs (in-engine visual pass).
# Blender (X,Y, up=Z) -> Godot (X, up=Y, -Y->Z): place at (bx, 0, -by), rot_y = -deg.
var ROOT: Node3D

func place(n: String, bx: float, by: float, deg: float = 0.0) -> void:
	var ps := load("res://models/%s.glb" % n) as PackedScene
	if ps == null:
		return
	var inst := ps.instantiate()
	inst.position = Vector3(bx, 0, -by)
	inst.rotation_degrees = Vector3(0, -deg, 0)
	ROOT.add_child(inst); inst.owner = ROOT

func glow(bx: float, by: float, e: float, c: Color) -> void:
	var ol := OmniLight3D.new(); ol.position = Vector3(bx, 0.9, -by)
	ol.light_color = c; ol.light_energy = e; ol.omni_range = 6.0
	ROOT.add_child(ol); ol.owner = ROOT

func _ready() -> void:
	ROOT = Node3D.new(); ROOT.name = "DissonantCity"

	# environment: dusk purple + glow (so the neon emission blooms in-engine)
	var we := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.137, 0.063, 0.20)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.30, 0.22, 0.40); env.ambient_light_energy = 0.5
	env.glow_enabled = true
	env.glow_intensity = 0.9; env.glow_bloom = 0.25; env.glow_strength = 1.1
	we.environment = env
	ROOT.add_child(we); we.owner = ROOT

	var key := DirectionalLight3D.new()
	key.rotation_degrees = Vector3(-58, 35, 0); key.light_energy = 1.4
	key.light_color = Color(1.0, 0.82, 0.68)
	ROOT.add_child(key); key.owner = ROOT

	# ground: road grid + plaza tiles
	for x in range(-3, 4):
		for y in range(-3, 4):
			var gx := x * 2; var gy := y * 2
			if x == 0 or y == 0:
				if x == 0 and y == 0: place("road_junction", gx, gy)
				else: place("road_straight", gx, gy, 0 if x == 0 else 90)
			else:
				place("plaza_tile", gx, gy)

	# buildings
	place("tower_tall_cyan", -4, 4); place("tower_tall_purple", 4, 4)
	place("tower_cyl", -4, -4); place("arcology", 4, -4)
	place("dome_building", 0, 5); place("ziggurat", -5, 0)
	place("slab_shop_pink", 5, 0.5, 90); place("slab_shop_cyan", 0, -5)
	place("tower_short_pink", 5, 5)
	place("tower_spiral", -6.5, 2.5); place("tower_prism", 6.5, 2.5)
	# skybridge
	place("bridge_support", -1.4, 4); place("bridge_support", 1.4, 4); place("skybridge", 0, 4, 90)
	# props
	place("billboard", -2, 2, 30); place("billboard", 2, -2, -30); place("neon_arch", 0, 2)
	place("hover_car", -1.2, 0.6, 20); place("hover_car2", 1.4, -0.8, -40); place("hover_car", 0.4, 2.6, 70)
	place("antenna", -5, 5); place("holo_pylon", 3, 2); place("holo_pylon", -3, -2)
	place("fountain_pad", 0, 0)
	for p in [Vector2(-2, -3), Vector2(2, 3), Vector2(-3, 2), Vector2(3, -3)]:
		place("streetlight", p.x, p.y)
	for p in [Vector2(-5, -3), Vector2(5, -2), Vector2(-2, 5)]:
		place("crystals", p.x, p.y)
	place("palm_retro", -3, 3); place("palm_retro", 3, -2); place("barrier", 1, 4)

	# neon glow accents
	glow(0, 0, 8.0, Color(1.0, 0.1, 0.45))      # fountain pink
	glow(-4, 4, 6.0, Color(0.1, 0.78, 0.85))    # cyan tower
	glow(5, 0.5, 5.0, Color(1.0, 0.1, 0.45))    # pink shop
	glow(3, 2, 5.0, Color(0.1, 0.78, 0.85)); glow(-3, -2, 5.0, Color(0.1, 0.78, 0.85))

	add_child(ROOT)

	# camera for an immediate view on F6 / play
	var cam := Camera3D.new()
	cam.position = Vector3(16, 13, 16)
	cam.look_at_from_position(Vector3(16, 13, 16), Vector3(0, 1.5, 0), Vector3.UP)
	add_child(cam)
