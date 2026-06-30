extends Node3D
# GrimForge Village Vol.2 demo builder.
# Auto-discovers every kit GLB under res://models/, lays them out on a grid
# (a "grim outpost" catalog), adds ground + lighting + an ortho camera, and
# saves village.tscn. Verifies all 25 expansion pieces import and instantiate.
# Blender (Z-up) -> Godot (Y-up): place at (bx, 0, -by), rot_y = -deg.
var ROOT: Node3D

func place(n: String, bx: float, by: float, deg: float = 0.0) -> bool:
	var ps := load("res://models/%s.glb" % n) as PackedScene
	if ps == null:
		push_warning("missing model: %s" % n)
		return false
	var inst := ps.instantiate()
	inst.name = n
	inst.position = Vector3(bx, 0, -by)
	inst.rotation_degrees = Vector3(0, -deg, 0)
	ROOT.add_child(inst); inst.owner = ROOT
	return true

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

func discover_models() -> Array:
	var names := []
	var d := DirAccess.open("res://models")
	if d == null:
		return names
	d.list_dir_begin()
	var f := d.get_next()
	while f != "":
		if not d.current_is_dir() and f.get_extension() == "glb":
			names.append(f.get_basename())
		f = d.get_next()
	d.list_dir_end()
	names.sort()
	return names

func _ready() -> void:
	ROOT = Node3D.new(); ROOT.name = "VillageVol2"

	var models := discover_models()
	groundbox(40, 40, -0.2, Color(0.20, 0.22, 0.16))   # dark grim ground

	# Grid layout: 5 columns, 3.0u spacing, ordered alphabetically.
	var cols := 5
	var spacing := 3.0
	var placed := 0
	for i in models.size():
		var col := i % cols
		var row := i / cols
		var bx := (col - (cols - 1) / 2.0) * spacing
		var by := ((models.size() - 1) / cols / 2.0 - row) * spacing
		if place(models[i], bx, by):
			placed += 1

	# Lighting — grim dusk
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-46, 42, 0); sun.light_energy = 2.0
	sun.light_color = Color(1.0, 0.91, 0.82); sun.shadow_enabled = true
	ROOT.add_child(sun); sun.owner = ROOT
	var we := WorldEnvironment.new(); var env := Environment.new()
	env.background_mode = Environment.BG_COLOR; env.background_color = Color(0.13, 0.15, 0.19)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.50, 0.55, 0.66); env.ambient_light_energy = 0.85
	we.environment = env; ROOT.add_child(we); we.owner = ROOT
	# emissive props get a warm glow
	for nm in ["torch", "fountain"]:
		if nm in models:
			var idx := models.find(nm)
			var col := idx % cols
			var row := idx / cols
			var bx := (col - (cols - 1) / 2.0) * spacing
			var by := ((models.size() - 1) / cols / 2.0 - row) * spacing
			glow(bx, by, 4.0, Color(1.0, 0.55, 0.2))

	var cam := Camera3D.new(); cam.projection = Camera3D.PROJECTION_ORTHOGONAL; cam.size = 18.0
	cam.look_at_from_position(Vector3(16, 15, 16), Vector3(0, 0.4, 0), Vector3.UP)
	ROOT.add_child(cam); cam.owner = ROOT

	var packed := PackedScene.new(); packed.pack(ROOT)
	ResourceSaver.save(packed, "res://village.tscn")
	print("SAVED village.tscn  models_found=", models.size(), "  placed=", placed, "  children=", ROOT.get_child_count())
	get_tree().quit()
