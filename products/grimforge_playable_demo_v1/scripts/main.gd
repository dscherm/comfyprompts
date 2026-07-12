extends Node3D

# GrimForge playable demo — castle courtyard from castle_kit_grimforge_v1,
# bestiary characters, arrow-key knight. Root orchestrator: lighting, env,
# and CLI-driven screenshot support for headless-ish verification:
#   godot --path . -- --shot=name.png --shot-delay=1.5 --quit-after=3

const EnvBuilder := preload("res://scripts/env.gd")
const BestiaryBuilder := preload("res://scripts/bestiary.gd")
const InteriorBuilder := preload("res://scripts/interior.gd")
const TownBuilder := preload("res://scripts/town.gd")
const OccultBuilder := preload("res://scripts/occult_town.gd")
const PlayerScript := preload("res://scripts/player.gd")

const COURTYARD_START := Vector3(0.0, 0.1, 2.5)

# Per-world lighting mood (see _apply_world_lighting). Each world sets its own
# sun energy/pitch/colour + ambient + sky so it reads distinctly: the town is a
# warm living village, the occult town is dark and cursed (its emit atlases
# carry the glow), the keep is dim/torchlit, the courtyard is neutral daylight.
const _LIGHT_PROFILES := {
	"courtyard": {"sun": 1.3, "pitch": -50.0, "sun_col": Color(1.0, 0.97, 0.90),
		"amb": 0.80, "sky_top": Color(0.35, 0.42, 0.58), "sky_horiz": Color(0.62, 0.60, 0.58)},
	"town": {"sun": 1.9, "pitch": -62.0, "sun_col": Color(1.0, 0.94, 0.80),
		"amb": 1.35, "sky_top": Color(0.45, 0.60, 0.85), "sky_horiz": Color(0.92, 0.86, 0.74)},
	"interior": {"sun": 0.55, "pitch": -60.0, "sun_col": Color(1.0, 0.84, 0.62),
		"amb": 0.50, "sky_top": Color(0.10, 0.10, 0.14), "sky_horiz": Color(0.22, 0.17, 0.14)},
	"occult_town": {"sun": 1.05, "pitch": -52.0, "sun_col": Color(0.80, 0.82, 0.92),
		"amb": 0.60, "sky_top": Color(0.16, 0.17, 0.24), "sky_horiz": Color(0.34, 0.30, 0.34)},
}

var _overview_cam: Camera3D
var _sun: DirectionalLight3D
var _skymat: ProceduralSkyMaterial
var _env: Environment
var _world := "courtyard"
var _world_root: Node3D
var _player: CharacterBody3D
var _triggers: Array = []
var _cooldown := 0.0
var _no_player := false

func _ready() -> void:
	_setup_lighting()
	_setup_overview_camera()
	var args := OS.get_cmdline_user_args()
	_no_player = ("--flat" in args) or ("--topdown" in args) or ("--overview" in args)
	var start := "courtyard"
	if "--interior" in args:
		start = "interior"
	elif "--town" in args:
		start = "town"
	elif "--occult" in args:
		start = "occult_town"
	# Fresh game starts at full hp. reset() runs ONCE here on boot — never in
	# _build_world — so world transitions preserve the carried hp/death state.
	GameState.reset()
	_build_world(start, _default_spawn(start))
	_handle_cli()

func _process(delta: float) -> void:
	if _cooldown > 0.0:
		_cooldown -= delta
		return
	# Poll overlaps rather than rely on body_entered: the player can enter a
	# trigger during the post-spawn cooldown, which would swallow a one-shot
	# enter event. Polling re-checks every frame once the cooldown clears.
	if _player == null or not is_instance_valid(_player):
		return
	for area in _triggers:
		if is_instance_valid(area) and area.get_overlapping_bodies().has(_player):
			var ex: Dictionary = area.get_meta("exit")
			print("TRANSITION %s -> %s" % [_world, ex["to"]])
			_cooldown = 1e9   # freeze until the rebuild replaces this handler
			call_deferred("_build_world", ex["to"], ex["spawn"])
			return

func _default_spawn(world: String) -> Vector3:
	match world:
		"interior":
			return InteriorBuilder.entrance_point()
		"town":
			return TownBuilder.entrance_point()
		"occult_town":
			return OccultBuilder.entrance_point()
		_:
			return COURTYARD_START

# Exit zones per world: each is a trigger box that sends the player to another
# world at a spawn clear of that world's return trigger.
func _world_exits(world: String) -> Array:
	match world:
		"courtyard":
			return [
				{"pos": Vector3(0, 0, -3.4), "size": Vector3(1.8, 2.5, 1.2),
				 "to": "interior", "spawn": InteriorBuilder.entrance_point()},
				{"pos": Vector3(0, 0, 5.8), "size": Vector3(2.4, 2.5, 1.2),
				 "to": "town", "spawn": TownBuilder.entrance_point()},
			]
		"interior":
			var ez: float = InteriorBuilder.entrance_point().z + 1.0
			return [
				{"pos": Vector3(0, 0, ez), "size": Vector3(1.8, 2.5, 0.9),
				 "to": "courtyard", "spawn": Vector3(0.0, 0.1, -2.0)},
			]
		"town":
			var tz: float = TownBuilder.entrance_point().z - 0.7
			return [
				{"pos": Vector3(0, 0, tz), "size": Vector3(2.4, 2.5, 0.9),
				 "to": "courtyard", "spawn": Vector3(0.0, 0.1, 4.5)},
				# west edge of the town square -> into the cursed occult village
				{"pos": Vector3(-5.8, 0, 6.2), "size": Vector3(1.6, 2.5, 1.6),
				 "to": "occult_town", "spawn": OccultBuilder.entrance_point()},
			]
		"occult_town":
			var oz: float = OccultBuilder.entrance_point().z - 0.7
			return [
				{"pos": Vector3(0, 0, oz), "size": Vector3(2.4, 2.5, 0.9),
				 "to": "town", "spawn": Vector3(-4.0, 0.1, 5.5)},
			]
		_:
			return []

func _build_world(world: String, spawn: Vector3) -> void:
	_world = world
	_apply_world_lighting(world)
	if _world_root and is_instance_valid(_world_root):
		_world_root.queue_free()
	if _player and is_instance_valid(_player):
		_player.queue_free()
	_triggers.clear()

	var root := Node3D.new()
	root.name = "World_" + world
	add_child(root)
	_world_root = root

	var populate := not ("--flat" in OS.get_cmdline_user_args())
	match world:
		"interior":
			root.add_child(InteriorBuilder.build())
			if populate:
				root.add_child(BestiaryBuilder.build("interior"))
		"town":
			root.add_child(TownBuilder.build())
			if populate:
				root.add_child(BestiaryBuilder.build("town"))
		"occult_town":
			root.add_child(OccultBuilder.build())
			if populate:
				root.add_child(BestiaryBuilder.build("occult_town"))
		_:
			root.add_child(EnvBuilder.build())
			if populate:
				root.add_child(BestiaryBuilder.build("courtyard"))

	for ex in _world_exits(world):
		var area := _make_trigger(ex)
		root.add_child(area)
		_triggers.append(area)

	if not _no_player:
		_player = CharacterBody3D.new()
		_player.name = "Player"
		_player.set_script(PlayerScript)
		_player.position = spawn
		_player.set("world_name", world)   # names the world in the PLAYER_SPAWN log
		add_child(_player)
	_cooldown = 0.3   # brief settle so physics registers the new player before polling

func _make_trigger(ex: Dictionary) -> Area3D:
	var area := Area3D.new()
	area.position = ex["pos"]
	area.collision_mask = 1   # player is on layer 1
	area.set_meta("exit", ex)
	var cs := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = ex["size"]
	cs.shape = box
	area.add_child(cs)
	return area

func _setup_lighting() -> void:
	_sun = DirectionalLight3D.new()
	_sun.shadow_enabled = not ("--noshadow" in OS.get_cmdline_user_args())
	add_child(_sun)

	var wenv := WorldEnvironment.new()
	_env = Environment.new()
	var sky := Sky.new()
	_skymat = ProceduralSkyMaterial.new()
	_skymat.ground_bottom_color = Color(0.18, 0.16, 0.14)
	sky.sky_material = _skymat
	_env.background_mode = Environment.BG_SKY
	_env.sky = sky
	_env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	wenv.environment = _env
	add_child(wenv)
	_apply_world_lighting("courtyard")   # sane default before the first world build

# Set the sun + sky mood for a world from _LIGHT_PROFILES. Called by _build_world
# so each world feels distinct (warm village / cursed dark / torchlit hall).
func _apply_world_lighting(world: String) -> void:
	if _sun == null:
		return
	var p: Dictionary = _LIGHT_PROFILES.get(world, _LIGHT_PROFILES["courtyard"])
	_sun.rotation_degrees = Vector3(p["pitch"], -30.0, 0.0)
	_sun.light_energy = p["sun"]
	_sun.light_color = p["sun_col"]
	_env.ambient_light_energy = p["amb"]
	_skymat.sky_top_color = p["sky_top"]
	_skymat.sky_horizon_color = p["sky_horiz"]
	_skymat.ground_horizon_color = p["sky_horiz"]

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
