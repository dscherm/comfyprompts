extends CharacterBody3D

# Arrow-key knight. Visual rig = revenant_knight_idle.fbx (Unity-baked,
# native ufbx); the walk clip is merged in at runtime from
# revenant_knight_walk.fbx — both FBXs are exports of the identical rig,
# so the walk Animation's track paths resolve against the idle scene.
# Movement is camera-relative (isometric yaw 45), body turns to face
# travel direction, walk/idle clips switch with motion.

const TARGET_H := 0.85       # miniature-world knight height (walls are 1.3m)
const WALK_SPEED := 0.6      # m/s — matched to the walk clip (measure_walk.gd)
const RUN_SPEED := 1.4       # m/s — hold Shift
const TURN_SPEED := 10.0     # rad/s toward travel direction
# measure_walk.gd: the ActorCore relaxed-walk covers ~0.18-0.31 m/s of ground
# at 1.0x at knight scale; 0.6 m/s at 2.0x playback sits on the stride-envelope
# estimate (0.30), so feet track the ground instead of skating.
const WALK_ANIM_SPEED := 2.0
const RUN_ANIM_SPEED := 1.5
const CAM_YAW := 45.0
const CAM_PITCH := -35.0
const CAM_SIZE := 6.0
const ARENA_CLAMP := 7.5     # failsafe only — wall colliders are the real bounds

# Sword grip (arsenal_kit sword.glb -> CC_Base_R_Hand). Tunable at runtime via
# --wpos=x,y,z --wrot=x,y,z --wscale=s for iteration.
const WEAPON_BONE := "CC_Base_R_Hand"
# The sword pivots around a grip node seated in the fist: _weapon_grip slides
# the mesh so its handle (not its pommel) sits at the pivot, then _weapon_rot
# aims it up-and-forward. All CLI-tunable: --wpos --wrot --wscale --wgrip.
var _weapon_pos := Vector3(0.0, 0.02, 0.0)   # pivot offset from the hand bone
var _weapon_grip := Vector3(0.0, -0.06, 0.0) # sword-local: move grip to pivot
var _weapon_rot := Vector3(120.0, 0.0, 0.0)  # up-and-forward
var _weapon_scale := 0.8

var _ap: AnimationPlayer
var _cam: Camera3D
var _rig: Node3D
var _state := "idle"
var _drive_left := 0.0       # seconds of simulated input remaining
var _drive_actions: PackedStringArray = ["move_up"]
var _force_run := false
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
		elif a == "--run":
			_force_run = true

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
	var has_walk := _merge_clip("res://chars/revenant_knight_walk.fbx", "walk", "loco")
	var has_run := _merge_clip("res://chars/revenant_knight_run.fbx", "run", "run")
	print("PLAYER_CLIPS idle walk=%s run=%s" % [has_walk, has_run])
	_apply_weapon_overrides()
	_attach_weapon()
	_ap.play("idle")

# Merge a clip from a twin FBX export into the idle rig's AnimationPlayer.
# Remaps the clip's leading track-path segment to the target rig's prefix so
# tracks resolve even when the two FBXs were baked with different root names.
func _merge_clip(path: String, clip_name: String, lib_name: String) -> bool:
	var scene: PackedScene = load(path)
	if scene == null:
		return false
	var tmp: Node3D = scene.instantiate()
	var aps := _find_all(tmp, "AnimationPlayer")
	var ok := false
	if aps.size() > 0 and (aps[0] as AnimationPlayer).has_animation(clip_name):
		var anim: Animation = (aps[0] as AnimationPlayer).get_animation(clip_name).duplicate(true)
		anim.loop_mode = Animation.LOOP_LINEAR
		var prefix := _rig_prefix(_rig)
		if prefix != "":
			_remap_track_prefix(anim, prefix)
		var lib := AnimationLibrary.new()
		lib.add_animation(clip_name, anim)
		_ap.add_animation_library(lib_name, lib)
		ok = true
	tmp.free()
	return ok

func _apply_weapon_overrides() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--wpos="):
			_weapon_pos = _parse_vec3(a.trim_prefix("--wpos="))
		elif a.begins_with("--wrot="):
			_weapon_rot = _parse_vec3(a.trim_prefix("--wrot="))
		elif a.begins_with("--wscale="):
			_weapon_scale = float(a.trim_prefix("--wscale="))
		elif a.begins_with("--wgrip="):
			_weapon_grip = _parse_vec3(a.trim_prefix("--wgrip="))

func _attach_weapon() -> void:
	var skels := _find_all(_rig, "Skeleton3D")
	if skels.is_empty():
		push_warning("player: no skeleton for weapon")
		return
	var skel := skels[0] as Skeleton3D
	if skel.find_bone(WEAPON_BONE) < 0:
		push_warning("player: no bone %s" % WEAPON_BONE)
		return
	var sword_scene: PackedScene = load("res://weapons/sword.glb")
	if sword_scene == null:
		push_warning("player: sword.glb missing")
		return
	var ba := BoneAttachment3D.new()
	ba.bone_name = WEAPON_BONE
	skel.add_child(ba)
	# pivot at the fist: rotation/scale here so the sword turns about its grip
	var pivot := Node3D.new()
	ba.add_child(pivot)
	pivot.position = _weapon_pos
	pivot.rotation_degrees = _weapon_rot
	pivot.scale = Vector3.ONE * _weapon_scale
	var sword: Node3D = sword_scene.instantiate()
	pivot.add_child(sword)
	sword.position = _weapon_grip  # slide handle onto the pivot (the fist)
	print("PLAYER_WEAPON sword pos=%s grip=%s rot=%s scale=%.2f" % [_weapon_pos, _weapon_grip, _weapon_rot, _weapon_scale])

func _parse_vec3(s: String) -> Vector3:
	var p := s.split(",")
	if p.size() != 3:
		return Vector3.ZERO
	return Vector3(float(p[0]), float(p[1]), float(p[2]))

func _rig_prefix(rig: Node) -> String:
	var sk := _find_all(rig, "Skeleton3D")
	if sk.is_empty():
		return ""
	var n: Node = sk[0]
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
	var moving := dir3.length() > 0.01
	var running := moving and (_force_run or Input.is_physical_key_pressed(KEY_SHIFT))
	velocity = dir3 * (RUN_SPEED if running else WALK_SPEED)
	move_and_slide()
	global_position.x = clampf(global_position.x, -ARENA_CLAMP, ARENA_CLAMP)
	global_position.z = clampf(global_position.z, -ARENA_CLAMP, ARENA_CLAMP)
	if moving and _rig:
		var target_yaw := atan2(dir3.x, dir3.z)
		_rig.rotation.y = lerp_angle(_rig.rotation.y, target_yaw, minf(TURN_SPEED * delta, 1.0))
	_set_anim_state("run" if running else ("walk" if moving else "idle"))
	_update_camera()
	_log_accum += delta
	if _log_accum >= 0.5:
		_log_accum = 0.0
		print("PLAYER_POS %.2f,%.2f state=%s" % [global_position.x, global_position.z, _state])

func _set_anim_state(s: String) -> void:
	if s == _state or _ap == null:
		return
	_state = s
	match s:
		"run":
			if _ap.has_animation("run/run"):
				_ap.play("run/run", 0.15, RUN_ANIM_SPEED)
			elif _ap.has_animation("loco/walk"):
				_ap.play("loco/walk", 0.15, WALK_ANIM_SPEED)
		"walk":
			if _ap.has_animation("loco/walk"):
				_ap.play("loco/walk", 0.2, WALK_ANIM_SPEED)
			else:
				_ap.play("idle", 0.2)
		_:
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
