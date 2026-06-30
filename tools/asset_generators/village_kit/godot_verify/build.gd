extends Node3D
# GrimForge kit Godot import-verify + showcase builder.
#
# Discovers every GLB under res://models/, lays them out on an adaptive grid,
# applies a named AESTHETIC lighting profile (medieval | occult), frames an
# ortho camera to the set, and saves village.tscn. Running this proves the
# exported kit imports and renders in Godot, and produces a showcase scene.
#
# The aesthetic is read from res://aesthetic.txt (one word); defaults to
# "medieval". Profiles here mirror kit_pipeline.py's catalog PROFILES so the
# Blender catalog and the in-engine showcase share one look.
#
# Blender (Z-up) -> Godot (Y-up): place at (bx, 0, -by), rot_y = -deg.
var ROOT: Node3D

const PROFILES := {
	"medieval": {
		"ground": Color(0.22, 0.24, 0.17), "spacing": 2.6,
		"sun_energy": 2.2, "sun_color": Color(1.0, 0.93, 0.84), "sun_rot": Vector3(-48, 40, 0),
		"fill_energy": 0.0, "fill_color": Color(1, 1, 1), "fill_rot": Vector3(0, 0, 0),
		"bg": Color(0.16, 0.18, 0.22), "amb": Color(0.54, 0.58, 0.68), "amb_e": 0.95,
		"fog": false, "fog_color": Color(0, 0, 0), "fog_density": 0.0,
		"cam_scale": 1.0, "cam_h": 0.92, "warm_glow": Color(1.0, 0.6, 0.25),
	},
	"occult": {
		"ground": Color(0.07, 0.08, 0.10), "spacing": 4.6,
		"sun_energy": 1.7, "sun_color": Color(1.0, 0.80, 0.58), "sun_rot": Vector3(-38, 32, 0),
		"fill_energy": 0.5, "fill_color": Color(0.40, 0.55, 0.85), "fill_rot": Vector3(-20, -150, 0),
		"bg": Color(0.04, 0.05, 0.08), "amb": Color(0.20, 0.26, 0.40), "amb_e": 0.45,
		"fog": true, "fog_color": Color(0.12, 0.16, 0.24), "fog_density": 0.02,
		"cam_scale": 0.78, "cam_h": 0.6, "warm_glow": Color(1.0, 0.45, 0.15),
	},
}

func read_aesthetic() -> String:
	if FileAccess.file_exists("res://aesthetic.txt"):
		var a := FileAccess.get_file_as_string("res://aesthetic.txt").strip_edges()
		if PROFILES.has(a):
			return a
	return "medieval"

func place(n: String, bx: float, by: float, deg: float = 0.0) -> bool:
	var ps := load("res://models/%s.glb" % n) as PackedScene
	if ps == null:
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

func glow(bx: float, by: float, h: float, e: float, rng: float, c: Color) -> void:
	var ol := OmniLight3D.new(); ol.position = Vector3(bx, h, -by)
	ol.light_color = c; ol.light_energy = e; ol.omni_range = rng
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
	ROOT = Node3D.new(); ROOT.name = "KitShowcase"
	var p: Dictionary = PROFILES[read_aesthetic()]
	var models := discover_models()
	var n := models.size()
	var cols := int(ceil(sqrt(float(max(n, 1)))))
	var rows := int(ceil(float(max(n, 1)) / cols))
	var spacing: float = p["spacing"]

	var gw := cols * spacing + spacing
	var gd := rows * spacing + spacing
	groundbox(gw, gd, -0.2, p["ground"])

	for i in n:
		var col := i % cols
		var row := i / cols
		var bx := (col - (cols - 1) / 2.0) * spacing
		var by := ((rows - 1) / 2.0 - row) * spacing
		place(models[i], bx, by)
		var nm := String(models[i])
		# warm local glow pools for emissive pieces
		if nm.contains("barn") or nm.contains("forge"):
			glow(bx, by - 1.0, 1.0, 7.0, 11.0, p["warm_glow"])
		elif nm.contains("torch") or nm.contains("fountain") or nm.contains("brazier"):
			glow(bx, by, 0.9, 4.0, 7.0, p["warm_glow"])
		elif nm.contains("scarecrow"):
			glow(bx, by, 1.3, 2.0, 4.0, Color(1.0, 0.72, 0.25))

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = p["sun_rot"]; sun.light_energy = p["sun_energy"]
	sun.light_color = p["sun_color"]; sun.shadow_enabled = true
	ROOT.add_child(sun); sun.owner = ROOT
	if p["fill_energy"] > 0.0:
		var fill := DirectionalLight3D.new()
		fill.rotation_degrees = p["fill_rot"]; fill.light_energy = p["fill_energy"]
		fill.light_color = p["fill_color"]; fill.shadow_enabled = false
		ROOT.add_child(fill); fill.owner = ROOT
	var we := WorldEnvironment.new(); var env := Environment.new()
	env.background_mode = Environment.BG_COLOR; env.background_color = p["bg"]
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = p["amb"]; env.ambient_light_energy = p["amb_e"]
	if p["fog"]:
		env.fog_enabled = true
		env.fog_light_color = p["fog_color"]; env.fog_density = p["fog_density"]
	we.environment = env; ROOT.add_child(we); we.owner = ROOT

	var extent: float = max(gw, gd)
	var cam := Camera3D.new(); cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.size = extent * float(p["cam_scale"])
	var dist: float = extent
	cam.look_at_from_position(Vector3(dist, dist * float(p["cam_h"]), dist),
		Vector3(0, 0.7, 0), Vector3.UP)
	ROOT.add_child(cam); cam.owner = ROOT

	var packed := PackedScene.new(); packed.pack(ROOT)
	ResourceSaver.save(packed, "res://village.tscn")
	print("SAVED village.tscn  aesthetic=", read_aesthetic(), "  models=", n,
		"  grid=", cols, "x", rows, "  children=", ROOT.get_child_count())
	get_tree().quit()
