extends Node3D

# Render great_hall + chapel at 0/90/180/270 so the door-facing side is clear.
# Each row = one building, 4 columns = 4 yaw rotations. RED marker = the face
# pointing toward the camera (-Z, i.e. viewer) for each.

const EnvBuilder := preload("res://scripts/env.gd")
const ITEMS := ["great_hall", "chapel"]
const YAWS := [0, 180]

func _ready() -> void:
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-45, -25, 0)
	sun.light_energy = 1.3
	add_child(sun)
	var we := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.2, 0.22, 0.26)
	env.ambient_light_color = Color(0.7, 0.7, 0.7)
	env.ambient_light_energy = 0.9
	we.environment = env
	add_child(we)

	for r in range(ITEMS.size()):
		for c in range(YAWS.size()):
			var scene: PackedScene = load("res://kit/%s.glb" % ITEMS[r])
			var inst: Node3D = scene.instantiate()
			var pivot := Node3D.new()
			add_child(pivot)
			pivot.position = Vector3((float(c) - 0.5) * 4.5, 0, (float(r) - 0.5) * 4.5)
			pivot.rotation_degrees = Vector3(0, YAWS[c], 0)
			pivot.add_child(inst)
			var lbl := Label3D.new()
			lbl.text = "%s %d" % [ITEMS[r], YAWS[c]]
			lbl.font_size = 48
			lbl.pixel_size = 0.005
			lbl.billboard = BaseMaterial3D.BILLBOARD_ENABLED
			lbl.position = Vector3(0, 2.4, 0)
			pivot.add_child(lbl)

	var cam := Camera3D.new()
	add_child(cam)
	cam.position = Vector3(0, 2.2, 9.5)
	cam.look_at(Vector3(0, 0.8, 0))
	cam.current = true
	await get_tree().create_timer(1.0).timeout
	var img := get_viewport().get_texture().get_image()
	var dir := ProjectSettings.globalize_path("res://_shots")
	DirAccess.make_dir_recursive_absolute(dir)
	img.save_png(dir.path_join("doors_grid.png"))
	print("SHOT_SAVED doors_grid.png")
	get_tree().quit()
