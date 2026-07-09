extends CharacterBody3D

# Arrow-key knight. Visual rig = revenant_knight_idle.fbx (Unity-baked,
# native ufbx); the walk clip is merged in at runtime from
# revenant_knight_walk.fbx — both FBXs are exports of the identical rig,
# so the walk Animation's track paths resolve against the idle scene.
# Movement is camera-relative (isometric yaw 45), body turns to face
# travel direction, walk/idle clips switch with motion.

const TARGET_H := 0.85       # miniature-world knight height (walls are 1.3m)
const MOVE_SPEED := 0.6      # m/s — matched to the walk clip, see below
const TURN_SPEED := 10.0     # rad/s toward travel direction
# measure_walk.gd: the ActorCore relaxed-walk covers ~0.18-0.31 m/s of ground
# at 1.0x at knight scale; 0.6 m/s at 2.0x playback sits on the stride-envelope
# estimate (0.30), so feet track the ground instead of skating.
const WALK_ANIM_SPEED := 2.0
const CAM_YAW := 45.0
const CAM_PITCH := -35.0
const CAM_SIZE := 6.0
const ARENA_CLAMP := 7.5     # failsafe only — wall colliders are the real bounds

var _ap: AnimationPlayer
var _cam: Camera3D
var _rig: Node3D
var _state := "idle"
var _drive_left := 0.0       # seconds of simulated input remaining
var _drive_actions: PackedStringArray = ["move_up"]
var _log_accum := 0.0

func _ready() -> void:
	_build_rig()
	_build_camera()
	var shape := CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.radius = 0.15
	capsule.height = TARGET_H
	shape.shape = capsule
	shape.position = Vector3(0.0, TARGET_H * 0.5, 0.0)
	add_child(shape)
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--drive="):
			# --drive=2.5  or  --drive=up+left:12
			var spec := a.trim_prefix("--drive=")
			if ":" in spec:
				var parts := spec.split(":")
				_drive_actions.clear()
				for d in parts[0].split("+"):
					_drive_actions.append("move_%s" % d)
				_drive_left = float(parts[1])
			else:
				_drive_left = float(spec)

func _build_rig() -> void:
	var idle_scene: PackedScene = load("res://chars/revenant_knight_idle.fbx")
	if idle_scene == null:
		push_warning("player: idle fbx missing")
		return
	_rig = idle_scene.instantiate()
	# scale to knight height, feet on y=0
	var aabb := _subtree_aabb(_rig, Transform3D.IDENTITY)
	var s := TARGET_H / maxf(aabb.size.y, 0.01)
	_rig.scale = Vector3(s, s, s)
	var c := aabb.get_center()
	_rig.position = Vector3(-c.x, -aabb.position.y, -c.z) * s
	add_child(_rig)
	# albedo does not survive the Unity FBX export — re-apply
	var albedo: Texture2D = load("res://chars/revenant_knight.png")
	for mi in _find_all(_rig, "MeshInstance3D"):
		var m: Mesh = (mi as MeshInstance3D).mesh
		if m == null:
			continue
		for si in range(m.get_surface_count()):
			var mat := StandardMaterial3D.new()
			mat.albedo_texture = albedo
			mat.roughness = 0.9
			(mi as MeshInstance3D).set_surface_override_material(si, mat)
	# animations: idle ships in this scene; merge walk from the twin export
	_ap = _find_all(_rig, "AnimationPlayer")[0] if _find_all(_rig, "AnimationPlayer").size() > 0 else null
	if _ap == null:
		push_warning("player: no AnimationPlayer in idle fbx")
		return
	_set_loop(_ap, "idle")
	var walk_scene: PackedScene = load("res://chars/revenant_knight_walk.fbx")
	if walk_scene:
		var tmp: Node3D = walk_scene.instantiate()
		var aps := _find_all(tmp, "AnimationPlayer")
		if aps.size() > 0:
			var wap := aps[0] as AnimationPlayer
			if wap.has_animation("walk"):
				var walk_anim: Animation = wap.get_animation("walk").duplicate(true)
				walk_anim.loop_mode = Animation.LOOP_LINEAR
				var lib := AnimationLibrary.new()
				lib.add_animation("walk", walk_anim)
				_ap.add_animation_library("loco", lib)
		tmp.free()
	if _ap.has_animation("loco/walk"):
		print("PLAYER_CLIPS idle+walk ready")
	else:
		push_warning("player: walk clip merge failed")
	_ap.play("idle")

func _build_camera() -> void:
	_cam = Camera3D.new()
	_cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	_cam.size = CAM_SIZE
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--camsize="):
			_cam.size = float(a.trim_prefix("--camsize="))
	add_child(_cam)
	_cam.rotation_degrees = Vector3(CAM_PITCH, CAM_YAW, 0.0)
	_update_camera()
	_cam.current = true

func _update_camera() -> void:
	var back := Basis.from_euler(Vector3(deg_to_rad(CAM_PITCH), deg_to_rad(CAM_YAW), 0.0)) * Vector3(0, 0, 1)
	_cam.global_position = global_position + Vector3(0, TARGET_H * 0.6, 0) + back * 12.0

func _physics_process(delta: float) -> void:
	if _drive_left > 0.0:
		_drive_left -= delta
		for act in _drive_actions:
			Input.action_press(act)
		if _drive_left <= 0.0:
			for act in _drive_actions:
				Input.action_release(act)
	var iv := Input.get_vector("move_left", "move_right", "move_up", "move_down")
	# camera-relative: rotate screen input by the camera yaw
	var dir3 := Vector3(iv.x, 0.0, iv.y).rotated(Vector3.UP, deg_to_rad(CAM_YAW))
	velocity = dir3 * MOVE_SPEED
	move_and_slide()
	global_position.x = clampf(global_position.x, -ARENA_CLAMP, ARENA_CLAMP)
	global_position.z = clampf(global_position.z, -ARENA_CLAMP, ARENA_CLAMP)
	if dir3.length() > 0.01 and _rig:
		var target_yaw := atan2(dir3.x, dir3.z)
		_rig.rotation.y = lerp_angle(_rig.rotation.y, target_yaw, minf(TURN_SPEED * delta, 1.0))
	_set_anim_state("walk" if dir3.length() > 0.01 else "idle")
	_update_camera()
	_log_accum += delta
	if _log_accum >= 0.5:
		_log_accum = 0.0
		print("PLAYER_POS %.2f,%.2f state=%s" % [global_position.x, global_position.z, _state])

func _set_anim_state(s: String) -> void:
	if s == _state or _ap == null:
		return
	_state = s
	if s == "walk" and _ap.has_animation("loco/walk"):
		_ap.play("loco/walk", 0.2, WALK_ANIM_SPEED)
	else:
		_ap.play("idle", 0.2)

func _set_loop(ap: AnimationPlayer, name: String) -> void:
	if ap.has_animation(name):
		var a := ap.get_animation(name)
		a.loop_mode = Animation.LOOP_LINEAR

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

func _subtree_aabb(node: Node, xform: Transform3D) -> AABB:
	var result := AABB()
	var first := true
	var stack: Array = [[node, xform]]
	while not stack.is_empty():
		var top: Array = stack.pop_back()
		var n: Node = top[0]
		var xf: Transform3D = top[1]
		if n is Node3D:
			xf = xf * (n as Node3D).transform
		if n is MeshInstance3D and (n as MeshInstance3D).mesh:
			var ab := xf * (n as MeshInstance3D).mesh.get_aabb()
			result = ab if first else result.merge(ab)
			first = false
		for c in n.get_children():
			stack.push_back([c, xf])
	return result
