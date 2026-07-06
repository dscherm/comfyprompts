extends Node3D

# Live bestiary gallery — polls res://models/*.glb every few seconds and HOT-ADDS
# any newly-appeared creature onto its own turntable, relaying out the row and
# reframing the camera. A background copier stages finished GLBs into models/ as
# the batch produces them, so this single window grows without a relaunch.

const MODELS_DIR := "res://models"
const TARGET_H := 2.0
const SPACING := 2.6
const POLL := 4.0

var _loaded: Dictionary = {}   # filename -> pivot Node3D
var _order: Array = []         # filenames, load order
var _cam: Camera3D
var _ground: MeshInstance3D
var _accum := 0.0

func _ready() -> void:
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50, -40, 0)
	sun.light_energy = 1.8
	sun.shadow_enabled = true
	add_child(sun)
	var fill := DirectionalLight3D.new()
	fill.rotation_degrees = Vector3(-15, 140, 0)
	fill.light_energy = 0.5
	add_child(fill)
	var we := WorldEnvironment.new()
	var e := Environment.new()
	e.background_mode = Environment.BG_COLOR
	e.background_color = Color(0.20, 0.21, 0.25)
	e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	e.ambient_light_color = Color(0.5, 0.5, 0.55)
	e.ambient_light_energy = 0.4
	we.environment = e
	add_child(we)

	_ground = MeshInstance3D.new()
	_ground.mesh = PlaneMesh.new()
	var gmat := StandardMaterial3D.new()
	gmat.albedo_color = Color(0.16, 0.16, 0.19)
	gmat.roughness = 1.0
	_ground.material_override = gmat
	add_child(_ground)

	_cam = Camera3D.new()
	add_child(_cam)
	_sync()

func _process(delta: float) -> void:
	for name in _order:
		(_loaded[name] as Node3D).rotate_y(delta * 0.6)
	_accum += delta
	if _accum >= POLL:
		_accum = 0.0
		_sync()

func _sync() -> void:
	var files: Array = []
	var d := DirAccess.open(MODELS_DIR)
	if d:
		d.list_dir_begin()
		var f := d.get_next()
		while f != "":
			if not d.current_is_dir() and f.to_lower().ends_with(".glb"):
				files.append(f)
			f = d.get_next()
		d.list_dir_end()
	files.sort()
	var added := false
	for fn in files:
		if _loaded.has(fn):
			continue
		var doc := GLTFDocument.new()
		var state := GLTFState.new()
		if doc.append_from_file("%s/%s" % [MODELS_DIR, fn], state) != OK:
			continue  # partial/mid-copy file — retry next poll
		var model := doc.generate_scene(state)
		var aabb := _subtree_aabb(model, Transform3D.IDENTITY)
		var h: float = maxf(aabb.size.y, 0.001)
		var s: float = TARGET_H / h
		model.scale = Vector3(s, s, s)
		var c := aabb.get_center()
		model.position = Vector3(-c.x, -aabb.position.y, -c.z) * s
		for mi in _find_meshes(model):
			var m: Mesh = mi.mesh
			for si in range(m.get_surface_count()):
				var existing: Material = m.surface_get_material(si)
				var textured: bool = existing is BaseMaterial3D and (existing as BaseMaterial3D).albedo_texture != null
				if not textured:
					var clay := StandardMaterial3D.new()
					clay.albedo_color = Color(0.62, 0.60, 0.57)
					clay.roughness = 0.85
					mi.set_surface_override_material(si, clay)
		var pivot := Node3D.new()
		add_child(pivot)
		pivot.add_child(model)
		var label := Label3D.new()
		label.text = fn.get_basename()
		label.font_size = 48
		label.pixel_size = 0.004
		label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		label.position = Vector3(0.0, -0.28, 0.0)
		label.modulate = Color(0.95, 0.88, 0.72)
		pivot.add_child(label)
		_loaded[fn] = pivot
		_order.append(fn)
		added = true
	if added:
		_relayout()

func _relayout() -> void:
	var n := _order.size()
	for i in range(n):
		(_loaded[_order[i]] as Node3D).position = Vector3((float(i) - (n - 1) / 2.0) * SPACING, 0.0, 0.0)
	(_ground.mesh as PlaneMesh).size = Vector2(maxf(n * SPACING + 4.0, 8.0), 8.0)
	var width: float = maxf(n * SPACING, TARGET_H * 2.0)
	_cam.position = Vector3(0, TARGET_H * 0.75, maxf(width * 0.75, TARGET_H * 2.6))
	_cam.look_at(Vector3(0, TARGET_H * 0.45, 0), Vector3.UP)

func _find_meshes(node: Node) -> Array:
	var out: Array = []
	if node is MeshInstance3D and (node as MeshInstance3D).mesh:
		out.append(node)
	for ch in node.get_children():
		out += _find_meshes(ch)
	return out

func _subtree_aabb(node: Node, xform: Transform3D) -> AABB:
	var out := AABB()
	var have := false
	if node is VisualInstance3D:
		out = xform * (node as VisualInstance3D).get_aabb()
		have = true
	for ch in node.get_children():
		var cx := xform
		if ch is Node3D:
			cx = xform * (ch as Node3D).transform
		var ca := _subtree_aabb(ch, cx)
		if ca.size != Vector3.ZERO:
			out = ca if not have else out.merge(ca)
			have = true
	return out
