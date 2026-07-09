extends Node3D

# Lay out each building at rotation 0 with axis markers (RED=+X, BLUE=+Z) so the
# door-facing local direction can be read, then screenshot from two angles.
# Run windowed: godot --path . -- (this is set as a temporary main via CLI)
#   godot --path . --scene? — instead we drive it from a scene swap below.

const BUILDINGS := ["gatehouse", "keep", "great_hall", "chapel", "stable", "market_stall", "well", "tower_round", "tower_square"]
const EnvBuilder := preload("res://scripts/env.gd")

func _ready() -> void:
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50, -30, 0)
	sun.light_energy = 1.3
	add_child(sun)
	var amb := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.2, 0.22, 0.26)
	env.ambient_light_color = Color(0.6, 0.6, 0.6)
	env.ambient_light_energy = 0.8
	amb.environment = env
	add_child(amb)

	var n := BUILDINGS.size()
	for i in range(n):
		var scene: PackedScene = load("res://kit/%s.glb" % BUILDINGS[i])
		if scene == null:
			continue
		var inst: Node3D = scene.instantiate()
		var pivot := Node3D.new()
		add_child(pivot)
		pivot.position = Vector3((float(i) - (n - 1) / 2.0) * 3.0, 0, 0)
		pivot.add_child(inst)
		var ab := EnvBuilder._subtree_aabb(inst, Transform3D.IDENTITY)
		# RED marker at +Z face, BLUE at +X face
		_marker(pivot, Vector3(0, 0.3, ab.position.z + ab.size.z + 0.15), Color.RED)   # +Z (toward viewer front)
		_marker(pivot, Vector3(ab.position.x + ab.size.x + 0.15, 0.3, 0), Color.BLUE)   # +X
		var lbl := Label3D.new()
		lbl.text = BUILDINGS[i]
		lbl.font_size = 60
		lbl.pixel_size = 0.006
		lbl.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		lbl.position = Vector3(0, ab.size.y + 0.4, 0)
		pivot.add_child(lbl)

	var cam := Camera3D.new()
	add_child(cam)
	# look from -Z (front) so +Z faces (RED) point toward us
	cam.position = Vector3(0, 3.5, 12.0)
	cam.look_at(Vector3(0, 1.0, 0))
	cam.current = true
	_shot("buildings_front.png", 1.0)

func _marker(parent: Node3D, pos: Vector3, col: Color) -> void:
	var m := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = Vector3(0.2, 0.2, 0.2)
	m.mesh = box
	var mat := StandardMaterial3D.new()
	mat.albedo_color = col
	mat.emission_enabled = true
	mat.emission = col
	m.material_override = mat
	m.position = pos
	parent.add_child(m)

func _shot(name: String, delay: float) -> void:
	await get_tree().create_timer(delay).timeout
	var img := get_viewport().get_texture().get_image()
	var dir := ProjectSettings.globalize_path("res://_shots")
	DirAccess.make_dir_recursive_absolute(dir)
	img.save_png(dir.path_join(name))
	print("SHOT_SAVED ", name)
	get_tree().quit()
