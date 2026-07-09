extends CharacterBody3D

# Wandering bestiary NPC. Picks random waypoints near its home spot, walks
# there (walk clip, speed-matched to scale like the player), then rests
# 2-5s playing its idle/flavor clip, and repeats. Collides with the castle
# (StaticBody3D colliders from env.gd) so it never enters a building.
# Bipeds merge their walk clip from <name>_walk.fbx (twin export of the
# <name>_anim.fbx rig); quads use walk/idle already in their _v2.glb.
# NPCs without a walk clip (lich_king, skeleton_mage) stay stationary idlers.

const EnvBuilder := preload("res://scripts/env.gd")

const WANDER_RADIUS := 3.0
const ARRIVE_DIST := 0.3
const ARENA := 6.4
const KNIGHT_SCALE := 0.486   # revenant_knight target_h/rig_height, for speed match
const KNIGHT_SPEED := 0.6     # tuned player MOVE_SPEED at that scale

# configuration set by bestiary.gd before add_child
var cfg := {}

var _rig: Node3D
var _ap: AnimationPlayer
var _walk_clip := ""
var _idle_clip := ""
var _move_speed := 0.4
var _anim_speed := 1.0
var _mobile := false

var _state := "rest"
var _rest_left := 0.0
var _target := Vector3.ZERO
var _walk_budget := 0.0
var _rng := RandomNumberGenerator.new()
var _log_accum := 0.0

func _ready() -> void:
	collision_layer = 2   # NPCs on their own layer
	collision_mask = 1    # collide with the environment (layer 1)
	# deterministic-but-distinct wander per NPC (stable across verification runs)
	_rng.seed = hash(cfg.get("name", "npc"))
	_build_visual()
	_setup_collision()
	_pick_rest(_rng.randf_range(0.3, 1.5))

func _build_visual() -> void:
	var kind: String = cfg.get("kind", "biped")
	var cname: String = cfg.get("name", "")
	if kind == "biped":
		var scene: PackedScene = load("res://chars/%s_anim.fbx" % cname)
		if scene == null:
			push_warning("npc: missing %s_anim.fbx" % cname)
			return
		_rig = scene.instantiate()
	else:
		var doc := GLTFDocument.new()
		var st := GLTFState.new()
		if doc.append_from_file("res://chars/%s_v2.glb" % cname, st) != OK:
			push_warning("npc: quad load fail %s" % cname)
			return
		_rig = doc.generate_scene(st)

	var aabb := EnvBuilder._subtree_aabb(_rig, Transform3D.IDENTITY)
	var s: float = cfg.get("target_h", 0.8) / maxf(aabb.size.y, 0.01)
	_rig.scale = Vector3(s, s, s)
	var c := aabb.get_center()
	_rig.position = Vector3(-c.x, -aabb.position.y, -c.z) * s
	add_child(_rig)

	_ap = _find_anim_player(_rig)
	if _ap == null:
		return

	if kind == "biped":
		_apply_albedo("res://chars/%s.png" % cname)
		var list := _ap.get_animation_list()
		_idle_clip = String(list[0]) if list.size() > 0 else ""
		if ResourceLoader.exists("res://chars/%s_walk.fbx" % cname):
			_merge_walk("res://chars/%s_walk.fbx" % cname)
		# stride scales with the character; match the knight's tuned feel
		_move_speed = KNIGHT_SPEED * (s / KNIGHT_SCALE)
		_anim_speed = 2.0
	else:
		if _ap.has_animation("walk"):
			_walk_clip = "walk"
		if _ap.has_animation("idle"):
			_idle_clip = "idle"
		elif _ap.get_animation_list().size() > 0:
			_idle_clip = String(_ap.get_animation_list()[0])
		_move_speed = 0.35 * (cfg.get("target_h", 0.4) / 0.4)
		_anim_speed = 1.0

	for cl in [_walk_clip, _idle_clip]:
		if cl != "" and _ap.has_animation(cl):
			_ap.get_animation(cl).loop_mode = Animation.LOOP_LINEAR

	_mobile = _walk_clip != ""

func _merge_walk(path: String) -> void:
	var scene: PackedScene = load(path)
	if scene == null:
		return
	var tmp: Node3D = scene.instantiate()
	var aps := _find_all(tmp, "AnimationPlayer")
	if aps.size() > 0 and (aps[0] as AnimationPlayer).has_animation("walk"):
		var wanim: Animation = (aps[0] as AnimationPlayer).get_animation("walk").duplicate(true)
		wanim.loop_mode = Animation.LOOP_LINEAR
		# The KD6 _walk.fbx was baked with the GameObject named <cname>, so its
		# tracks lead with "<cname>/root/...". The original _anim.fbx rig's
		# intermediate node is "<cname>_accurig/root/...". Rewrite the leading
		# path segment to the target rig's actual prefix so tracks resolve.
		var target_prefix := _rig_prefix(_rig)
		if target_prefix != "":
			_remap_track_prefix(wanim, target_prefix)
		var lib := AnimationLibrary.new()
		lib.add_animation("walk", wanim)
		_ap.add_animation_library("loco", lib)
		_walk_clip = "loco/walk"
	tmp.free()

# The name of the scene-root child that holds the Skeleton3D — the leading
# segment every skeleton track path is relative to.
func _rig_prefix(rig: Node) -> String:
	var sk := _find_skeleton(rig)
	if sk == null:
		return ""
	var n: Node = sk
	while n.get_parent() != null and n.get_parent() != rig:
		n = n.get_parent()
	return String(n.name)

func _remap_track_prefix(anim: Animation, target_prefix: String) -> void:
	for ti in range(anim.get_track_count()):
		var p := anim.track_get_path(ti)
		if p.get_name_count() == 0:
			continue
		var names := PackedStringArray()
		for i in range(p.get_name_count()):
			names.append(String(p.get_name(i)))
		names[0] = target_prefix
		var s := "/".join(names)
		if p.get_subname_count() > 0:
			var subs := PackedStringArray()
			for i in range(p.get_subname_count()):
				subs.append(String(p.get_subname(i)))
			s += ":" + ":".join(subs)
		anim.track_set_path(ti, NodePath(s))

func _find_skeleton(node: Node) -> Skeleton3D:
	var stack: Array = [node]
	while not stack.is_empty():
		var n: Node = stack.pop_back()
		if n is Skeleton3D:
			return n
		for c in n.get_children():
			stack.push_back(c)
	return null

func _setup_collision() -> void:
	var h: float = cfg.get("target_h", 0.8)
	var shape := CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.radius = clampf(h * 0.22, 0.1, 0.3)
	capsule.height = h
	shape.shape = capsule
	shape.position = Vector3(0.0, h * 0.5, 0.0)
	add_child(shape)

func _physics_process(delta: float) -> void:
	if _ap == null:
		return
	if not _mobile:
		velocity = Vector3.ZERO
		_play(_idle_clip, 1.0)
		return

	if _state == "rest":
		velocity = Vector3.ZERO
		_play(_idle_clip, 1.0)
		_rest_left -= delta
		if _rest_left <= 0.0:
			_pick_waypoint()
	else:
		var to := _target - global_position
		to.y = 0.0
		var dist := to.length()
		_walk_budget -= delta
		if dist < ARRIVE_DIST or _walk_budget <= 0.0:
			_pick_rest(_rng.randf_range(2.0, 5.0))
		else:
			var dir := to / dist
			velocity = dir * _move_speed
			move_and_slide()
			if _rig:
				var yaw := atan2(dir.x, dir.z)
				_rig.rotation.y = lerp_angle(_rig.rotation.y, yaw, minf(8.0 * delta, 1.0))
			_play(_walk_clip, _anim_speed)

	_log_accum += delta
	if _log_accum >= 0.5:
		_log_accum = 0.0
		print("NPC_POS %s %.2f,%.2f state=%s" % [cfg.get("name", "?"), global_position.x, global_position.z, _state])

func _pick_waypoint() -> void:
	var home: Vector2 = cfg.get("home", Vector2.ZERO)
	var ang := _rng.randf() * TAU
	var r := _rng.randf_range(1.0, WANDER_RADIUS)
	var p := home + Vector2(cos(ang), sin(ang)) * r
	p.x = clampf(p.x, -ARENA, ARENA)
	p.y = clampf(p.y, -ARENA, ARENA)
	_target = Vector3(p.x, global_position.y, p.y)
	_walk_budget = 6.0
	_state = "walk"

func _pick_rest(dur: float) -> void:
	_state = "rest"
	_rest_left = dur

func _play(clip: String, speed: float) -> void:
	if clip == "" or _ap == null:
		return
	if _ap.current_animation != clip:
		_ap.play(clip, 0.2, speed)

func _apply_albedo(texpath: String) -> void:
	var albedo: Texture2D = null
	if ResourceLoader.exists(texpath):
		albedo = load(texpath)
	for mi in _find_all(_rig, "MeshInstance3D"):
		var m: Mesh = (mi as MeshInstance3D).mesh
		if m == null:
			continue
		for si in range(m.get_surface_count()):
			var mat := StandardMaterial3D.new()
			if albedo != null:
				mat.albedo_texture = albedo
				mat.roughness = 0.9
			else:
				mat.albedo_color = Color(0.64, 0.62, 0.58)
				mat.roughness = 0.85
			(mi as MeshInstance3D).set_surface_override_material(si, mat)

func _find_all(node: Node, cls: String) -> Array:
	var out: Array = []
	var stack: Array = [node]
	while not stack.is_empty():
		var n: Node = stack.pop_back()
		if n.get_class() == cls:
			out.append(n)
		for c in n.get_children():
			stack.push_back(c)
	return out

func _find_anim_player(node: Node) -> AnimationPlayer:
	var stack: Array = [node]
	while not stack.is_empty():
		var n: Node = stack.pop_back()
		if n is AnimationPlayer:
			return n
		for c in n.get_children():
			stack.push_back(c)
	return null
