extends Node3D

# Bestiary gallery — runtime-loads every res://models/*.glb (copied from the kit's
# models_glb/), stands each on its own turntable with a name label, frames the row.
# Runtime GLTFDocument load so COLOR_0 and baked albedo both show; no editor import.

const MODELS_DIR := "res://models"
const TARGET_H := 2.0        # normalise every creature to this height
const SPACING := 2.6         # gap between turntables

var _pivots: Array = []

func _ready() -> void:
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

	var n := files.size()
	if n == 0:
		push_error("no .glb in %s" % MODELS_DIR)
		get_tree().quit()
		return

	for i in range(n):
		var path := "%s/%s" % [MODELS_DIR, files[i]]
		var doc := GLTFDocument.new()
		var state := GLTFState.new()
		if doc.append_from_file(path, state) != OK:
			push_warning("skip (load failed): %s" % path)
			continue
		var model := doc.generate_scene(state)

		var aabb := _subtree_aabb(model, Transform3D.IDENTITY)
		var h: float = maxf(aabb.size.y, 0.001)
		var s: float = TARGET_H / h
		model.scale = Vector3(s, s, s)
		# base on the floor (y=0), centred horizontally over its pivot
		var c := aabb.get_center()
		model.position = Vector3(-c.x, -aabb.position.y, -c.z) * s

		# clay-render only untextured surfaces so geometry-only meshes still read
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
		pivot.position = Vector3((float(i) - (n - 1) / 2.0) * SPACING, 0.0, 0.0)
		pivot.add_child(model)
		_pivots.append(pivot)

		var label := Label3D.new()
		label.text = files[i].get_basename()
		label.font_size = 48
		label.pixel_size = 0.004
		label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		label.position = Vector3(0.0, -0.28, 0.0)
		label.modulate = Color(0.95, 0.88, 0.72)
		pivot.add_child(label)

	# ground
	var ground := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(maxf(n * SPACING + 4.0, 8.0), 8.0)
	ground.mesh = pm
	var gmat := StandardMaterial3D.new()
	gmat.albedo_color = Color(0.16, 0.16, 0.19)
	gmat.roughness = 1.0
	ground.material_override = gmat
	add_child(ground)

	# lights + environment
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

	# camera frames the whole row
	var width: float = maxf(n * SPACING, TARGET_H * 2.0)
	var cam := Camera3D.new()
	add_child(cam)
	cam.position = Vector3(0, TARGET_H * 0.75, maxf(width * 0.75, TARGET_H * 2.6))
	cam.look_at(Vector3(0, TARGET_H * 0.45, 0), Vector3.UP)

func _process(delta: float) -> void:
	for p in _pivots:
		(p as Node3D).rotate_y(delta * 0.6)

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
