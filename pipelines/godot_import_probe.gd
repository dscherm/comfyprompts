extends SceneTree
# Probe for pipelines/godot_import.py. Run by the stage, windowed (headless
# Godot cannot render the shot):
#   godot --path <project> --script <this file> -- --glb=res://... \
#       --collision=none|box|convex|trimesh --out-scene=res://....tscn \
#       --report=<abs json> --shot=<abs png> [--shot-delay=0.5] [--quit-after=20]
# It instances the imported GLB under a root Node3D, adds the collision the
# rules ask for, saves that as a scene next to the GLB, reloads the SAVED scene
# and measures it (collision shape classes, animation names, material slots,
# mesh extent), writes the measurements as JSON, then screenshots it.

var args := {}

func _initialize() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--") and "=" in a:
			var kv := a.trim_prefix("--").split("=", true, 1)
			args[kv[0]] = kv[1]
	_run()

func _run() -> void:
	var report := {"ok": false}
	var glb: String = args.get("glb", "")
	var ps := load(glb) as PackedScene
	if ps == null:
		report["error"] = "could not load %s (not imported?)" % glb
		_finish(report, null)
		return
	var wrapper := Node3D.new()
	wrapper.name = glb.get_file().get_basename()
	var inst := ps.instantiate()
	wrapper.add_child(inst)
	inst.owner = wrapper
	var kind: String = args.get("collision", "none")
	if kind != "none":
		var err := _add_collision(wrapper, inst, kind)
		if err != "":
			report["error"] = err
			_finish(report, null)
			return
	var packed := PackedScene.new()
	packed.pack(wrapper)
	var out_scene: String = args.get("out-scene", "")
	var save_err := ResourceSaver.save(packed, out_scene)
	wrapper.free()
	if save_err != OK:
		report["error"] = "could not save %s (error %d)" % [out_scene, save_err]
		_finish(report, null)
		return
	var saved := load(out_scene) as PackedScene
	var node := saved.instantiate() as Node3D
	root.add_child(node)
	report = _measure(node)
	report["ok"] = true
	report["scene"] = out_scene
	_finish(report, node)

func _add_collision(wrapper: Node3D, inst: Node, kind: String) -> String:
	var body := StaticBody3D.new()
	body.name = "Collision"
	wrapper.add_child(body)
	body.owner = wrapper
	var meshes := inst.find_children("*", "MeshInstance3D", true, false)
	if meshes.is_empty():
		return "no MeshInstance3D to build %s collision from" % kind
	if kind == "box":
		var box := AABB()
		var first := true
		for mi in meshes:
			var a: AABB = _to_root(mi as MeshInstance3D, inst) * (mi as MeshInstance3D).mesh.get_aabb()
			box = a if first else box.merge(a)
			first = false
		var cs := CollisionShape3D.new()
		var shape := BoxShape3D.new()
		shape.size = box.size
		cs.shape = shape
		cs.position = box.get_center()
		body.add_child(cs)
		cs.owner = wrapper
		return ""
	for mi in meshes:
		var m := mi as MeshInstance3D
		var cs := CollisionShape3D.new()
		if kind == "convex":
			cs.shape = m.mesh.create_convex_shape(true, false)
		elif kind == "trimesh":
			cs.shape = m.mesh.create_trimesh_shape()
		else:
			return "unknown collision kind '%s'" % kind
		cs.transform = _to_root(m, inst)
		body.add_child(cs)
		cs.owner = wrapper
	return ""

# Transform of `n` relative to `top` (works before the nodes are in the tree).
func _to_root(n: Node3D, top: Node) -> Transform3D:
	var t := n.transform
	var p := n.get_parent()
	while p != null and p != top.get_parent():
		if p is Node3D:
			t = (p as Node3D).transform * t
		p = p.get_parent()
	return t

func _measure(node: Node3D) -> Dictionary:
	var shapes: Array = []
	for cs in node.find_children("*", "CollisionShape3D", true, false):
		var s: Shape3D = (cs as CollisionShape3D).shape
		shapes.append(s.get_class() if s != null else "null")
	var anims: Array = []
	for ap in node.find_children("*", "AnimationPlayer", true, false):
		for n in (ap as AnimationPlayer).get_animation_list():
			anims.append(String(n))
	var slots := 0
	var extent := AABB()
	var first := true
	for mi in node.find_children("*", "MeshInstance3D", true, false):
		var m := mi as MeshInstance3D
		if m.mesh == null:
			continue
		slots += m.mesh.get_surface_count()
		var a: AABB = m.global_transform * m.mesh.get_aabb()
		extent = a if first else extent.merge(a)
		first = false
	return {"collision_shapes": shapes, "animations": anims, "material_slots": slots,
		"extent": [extent.size.x, extent.size.y, extent.size.z],
		"center": [extent.get_center().x, extent.get_center().y, extent.get_center().z]}

func _finish(report: Dictionary, node: Node3D) -> void:
	var f := FileAccess.open(args.get("report", ""), FileAccess.WRITE)
	if f != null:
		f.store_string(JSON.stringify(report))
		f.close()
	print("IMPORT_PROBE ", JSON.stringify(report))
	if node != null and args.has("shot"):
		await _shot(node)
	quit(0 if report.get("ok", false) else 1)

func _shot(node: Node3D) -> void:
	var rep: Dictionary = _measure(node)
	var size: float = max(0.1, Vector3(rep["extent"][0], rep["extent"][1], rep["extent"][2]).length())
	var center := Vector3(rep["center"][0], rep["center"][1], rep["center"][2])
	var cam := Camera3D.new()
	root.add_child(cam)
	cam.look_at_from_position(center + Vector3(1.0, 0.7, 1.0) * size, center)
	cam.current = true
	var sun := DirectionalLight3D.new()
	root.add_child(sun)
	sun.rotation_degrees = Vector3(-50, 30, 0)
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.6, 0.6, 0.65)
	root.add_child(env)
	await create_timer(float(args.get("shot-delay", "0.5"))).timeout
	await process_frame
	var img := root.get_texture().get_image()
	var path: String = args["shot"]
	DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	var err := img.save_png(path)
	print("IMPORT_SHOT ", path, " ", err)
