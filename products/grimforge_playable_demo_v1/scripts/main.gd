extends Node3D

# GrimForge playable demo — castle courtyard from castle_kit_grimforge_v1,
# bestiary characters, arrow-key knight. Root orchestrator: lighting, env,
# and CLI-driven screenshot support for headless-ish verification:
#   godot --path . -- --shot=name.png --shot-delay=1.5 --quit-after=3

const EnvBuilder := preload("res://scripts/env.gd")
const BestiaryBuilder := preload("res://scripts/bestiary.gd")

var _overview_cam: Camera3D

func _ready() -> void:
	_setup_lighting()
	var env_root := EnvBuilder.build()
	add_child(env_root)
	var args := OS.get_cmdline_user_args()
	if not ("--flat" in args):
		add_child(BestiaryBuilder.build())
	_setup_overview_camera()
	if not ("--flat" in args) and not ("--topdown" in args) and not ("--overview" in args):
		var player := CharacterBody3D.new()
		player.name = "Player"
		player.set_script(load("res://scripts/player.gd"))
		player.position = Vector3(0.0, 0.1, 2.5)  # floor tile tops sit at ~0.1
		add_child(player)
	_handle_cli()

func _setup_lighting() -> void:
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-48.0, -30.0, 0.0)
	sun.light_energy = 1.2
	sun.shadow_enabled = not ("--noshadow" in OS.get_cmdline_user_args())
	add_child(sun)

	var wenv := WorldEnvironment.new()
	var env := Environment.new()
	var sky := Sky.new()
	var skymat := ProceduralSkyMaterial.new()
	skymat.sky_top_color = Color(0.35, 0.42, 0.58)
	skymat.sky_horizon_color = Color(0.62, 0.60, 0.58)
	skymat.ground_bottom_color = Color(0.18, 0.16, 0.14)
	skymat.ground_horizon_color = Color(0.62, 0.60, 0.58)
	sky.sky_material = skymat
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 0.7
	wenv.environment = env
	add_child(wenv)

func _setup_overview_camera() -> void:
	_overview_cam = Camera3D.new()
	add_child(_overview_cam)
	if "--topdown" in OS.get_cmdline_user_args():
		_overview_cam.position = Vector3(0.01, 20.0, 0.01)
		_overview_cam.look_at(Vector3.ZERO)
	else:
		# Isometric three-quarter view: orthographic, 35 deg down, 45 deg yaw.
		_overview_cam.projection = Camera3D.PROJECTION_ORTHOGONAL
		_overview_cam.size = 17.0
		for a in OS.get_cmdline_user_args():
			if a.begins_with("--zoom="):
				_overview_cam.size = float(a.trim_prefix("--zoom="))
		_overview_cam.rotation_degrees = Vector3(-35.0, 45.0, 0.0)
		_overview_cam.position = Vector3(14.0, 14.0 * tan(deg_to_rad(35.0)) * sqrt(2.0), 14.0)
	_overview_cam.current = true

func _handle_cli() -> void:
	var shots: Array = []      # entries: [name, delay]
	var shot_delay := 1.5
	var quit_after := 0.0
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--shot="):
			var spec := a.trim_prefix("--shot=")
			if ":" in spec:
				var parts := spec.rsplit(":", true, 1)
				shots.append([parts[0], float(parts[1])])
			else:
				shots.append([spec, -1.0])
		elif a.begins_with("--shot-delay="):
			shot_delay = float(a.trim_prefix("--shot-delay="))
		elif a.begins_with("--quit-after="):
			quit_after = float(a.trim_prefix("--quit-after="))
	for s in shots:
		_take_shot(s[0], s[1] if s[1] >= 0.0 else shot_delay)
	if quit_after > 0.0:
		get_tree().create_timer(quit_after).timeout.connect(func(): get_tree().quit())

func _take_shot(name: String, delay: float) -> void:
	await get_tree().create_timer(delay).timeout
	var img := get_viewport().get_texture().get_image()
	var dir := ProjectSettings.globalize_path("res://_shots")
	DirAccess.make_dir_recursive_absolute(dir)
	var path := dir.path_join(name)
	img.save_png(path)
	print("SHOT_SAVED ", path)
