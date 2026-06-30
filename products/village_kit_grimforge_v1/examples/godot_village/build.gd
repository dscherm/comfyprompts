extends Node3D
# Reconstructs the village from the kit GLBs and saves village.tscn.
# Blender (X,Y up=Z) -> Godot (X, up=Y, -Y->Z): place at (bx, 0, -by), rot_y = -deg.
var ROOT: Node3D

func place(n: String, bx: float, by: float, deg: float = 0.0) -> void:
	var ps := load("res://models/%s.glb" % n) as PackedScene
	if ps == null:
		return
	var inst := ps.instantiate()
	inst.position = Vector3(bx, 0, -by)
	inst.rotation_degrees = Vector3(0, -deg, 0)
	ROOT.add_child(inst); inst.owner = ROOT

func groundbox(sx: float, sz: float, y: float, col: Color) -> void:
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new(); bm.size = Vector3(sx, 0.2, sz); mi.mesh = bm
	var m := StandardMaterial3D.new(); m.albedo_color = col; m.roughness = 1.0
	mi.material_override = m; mi.position = Vector3(0, y, 0)
	ROOT.add_child(mi); mi.owner = ROOT

func glow(bx: float, by: float, e: float, c: Color) -> void:
	var ol := OmniLight3D.new(); ol.position = Vector3(bx, 0.9, -by)
	ol.light_color = c; ol.light_energy = e; ol.omni_range = 7.0
	ROOT.add_child(ol); ol.owner = ROOT

func _ready() -> void:
	ROOT = Node3D.new(); ROOT.name = "Village"
	groundbox(22, 22, -0.2, Color(0.24, 0.32, 0.15))   # grass
	groundbox(11, 11, -0.12, Color(0.30, 0.24, 0.16))  # dirt plaza

	for x in range(-4, 5): place("wall", x, 5, 0)
	for y in range(-4, 5):
		place("wall", -5, y, 90); place("wall", 5, y, 90)
	place("wall_corner", -5, 5, 0); place("wall_corner", 5, 5, 270)
	place("wall_gate", 0, -5, 0)
	for y in range(-4, 3): place("path_straight", 0, y, 0)

	place("cottage", -3.2, 2.6, 20); place("tavern", 3.0, 2.8, -25)
	place("church", -3.3, -1.2, 90); place("blacksmith", 3.4, -1.0, -90)
	place("house_tall", -3.4, 0.8, 95); place("house_small", 3.4, 1.0, -95)
	place("barn", 0, 3.6, 0)

	place("brazier", 0, 0, 0); place("well", -1.6, -0.6, 0); place("market_stall", 1.7, -0.4, 200)
	place("cart", 1.4, -2.2, 30); place("barrel", -0.9, -2.6, 0); place("crate", -1.3, -2.6, 0)
	place("haystack", 2.4, -2.6, 0)
	for t in [[-4.3, 4.2], [4.3, 4.2], [-4.4, -3.6], [4.4, -3.4]]: place("tree", t[0], t[1], 0)
	place("tree_dead", -2.4, -3.4, 0); place("gravestone", -4.0, -1.6, 0); place("gravestone", -3.6, -1.9, 0)
	place("lamppost", -1.0, -4.0, 0); place("lamppost", 1.0, -4.0, 0); place("signpost", 1.4, -4.2, 20)
	place("fence", -1, -4.6, 0); place("fence", 1, -4.6, 0)

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-46, 42, 0); sun.light_energy = 1.5
	sun.light_color = Color(1.0, 0.92, 0.84); sun.shadow_enabled = true
	ROOT.add_child(sun); sun.owner = ROOT
	var we := WorldEnvironment.new(); var env := Environment.new()
	env.background_mode = Environment.BG_COLOR; env.background_color = Color(0.11, 0.13, 0.18)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.46, 0.52, 0.62); env.ambient_light_energy = 0.55
	we.environment = env; ROOT.add_child(we); we.owner = ROOT
	glow(0, 0, 8.0, Color(1.0, 0.5, 0.16))
	glow(-3.2, 1.9, 3.0, Color(1.0, 0.6, 0.25)); glow(3.0, 2.0, 3.0, Color(1.0, 0.6, 0.25))

	var cam := Camera3D.new(); cam.projection = Camera3D.PROJECTION_ORTHOGONAL; cam.size = 15.0
	cam.look_at_from_position(Vector3(13, 12, 13), Vector3(0, 0.4, 0), Vector3.UP)
	ROOT.add_child(cam); cam.owner = ROOT

	var packed := PackedScene.new(); packed.pack(ROOT)
	ResourceSaver.save(packed, "res://village.tscn")
	print("SAVED village.tscn  children=", ROOT.get_child_count())
	get_tree().quit()
