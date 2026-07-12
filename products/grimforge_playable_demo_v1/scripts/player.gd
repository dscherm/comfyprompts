extends CharacterBody3D

# Arrow-key knight. Visual rig = revenant_knight_idle.fbx (Unity-baked,
# native ufbx); the walk clip is merged in at runtime from
# revenant_knight_walk.fbx — both FBXs are exports of the identical rig,
# so the walk Animation's track paths resolve against the idle scene.
# Movement is camera-relative (isometric yaw 45), body turns to face
# travel direction, walk/idle clips switch with motion.

const TARGET_H := 0.85       # miniature-world knight height (walls are 1.3m)
const WALK_SPEED := 0.74     # m/s — the retargeted forward walk's natural speed
const RUN_SPEED := 1.4       # m/s — hold Shift
const TURN_SPEED := 10.0     # rad/s toward travel direction
# No skate requires body_speed == clip foot-plant speed at its playback rate. The
# walk now uses revenant_knight_walk_rm (the Mixamo forward walk Humanoid-
# retargeted onto the knight, then baked IN PLACE — brisk + upright, no lean): its
# natural foot-plant speed is 0.74 m/s at 1.0x, so WALK_SPEED 0.74 @ 1.0x tracks.
# The run keeps its measured match: natural 1.454 m/s, so 1.4 @ 0.96x (see
# measure_loco.gd). Both play at their native cadence.
const WALK_ANIM_SPEED := 1.0
const RUN_ANIM_SPEED := 0.96
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
var _weapon_pos := Vector3(0.0, 0.02, 0.0)    # pivot offset from the hand bone
var _weapon_grip := Vector3(0.0, -0.06, 0.0)  # sword-local: move grip to pivot
var _weapon_rot := Vector3(120.0, 0.0, -35.0) # up-forward + angled outward (clears the body)
var _weapon_scale := 0.8

var _ap: AnimationPlayer
# Locomotion (idle/walk/run) is driven by an AnimationTree state machine.
# One-shot clips (attacks/hit/death) still play on the raw AnimationPlayer with
# the tree temporarily deactivated — see _play_oneshot / _set_anim_state.
var _tree: AnimationTree
var _sm: AnimationNodeStateMachinePlayback
var _has_walk := false
var _has_run := false
var _cam: Camera3D
var _rig: Node3D
var _state := "idle"
var _drive_left := 0.0       # seconds of simulated input remaining
var _drive_actions: PackedStringArray = ["move_up"]
var _force_run := false
var _log_accum := 0.0

# Attacks: physical keycode -> {anim, speed, dmg, len}. One-shot; while
# _attack_timer > 0 the attack clip plays and locomotion anim is suppressed.
var _attacks := {}
var _attack_timer := 0.0
var _fire_queue: Array = []   # simulated attack presses for headless testing
var _fire_timer := 0.0

# Combat
const MAX_HP := 100.0
const ATTACK_RANGE := 1.4     # reach of a swing (m)
const ATTACK_ARC := 130.0     # degrees, centered on facing
const HIT_IFRAMES := 0.6      # invulnerability after taking a hit
var hp := MAX_HP
var _dead := false
var _invuln := 0.0
var _damage_pending := -1.0   # >=0: seconds until the active swing lands
var _pending_dmg := 0.0
var _hurt_rate := 0.0         # --hurt=N : N dmg/sec self-damage for testing
var _autorevive := false
var _revive_timer := 0.0
var _hp_fill: ColorRect
var _hp_label: Label
# Set by main.gd before add_child so the spawn log names the world the player
# resumed into (courtyard/interior/town). hp persists across worlds via GameState.
var world_name := "courtyard"

func _ready() -> void:
	add_to_group("player")
	# Resume the carried hp/death state (GameState survives the world rebuild)
	# instead of always healing to MAX_HP — wounds follow the knight between worlds.
	hp = GameState.hp
	_dead = GameState.dead
	print("PLAYER_SPAWN hp=%d world=%s" % [int(hp), world_name])
	_build_rig()
	_build_camera()
	_build_hud()
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
		elif a.begins_with("--fire="):
			# simulate attack presses for headless verification: --fire=j,k,l,space
			for k in a.trim_prefix("--fire=").split(","):
				_fire_queue.append(k.strip_edges())
		elif a.begins_with("--hurt="):
			_hurt_rate = float(a.trim_prefix("--hurt="))   # dmg/sec self-damage (test)
		elif a == "--autorevive":
			_autorevive = true   # simulate an R press ~1.5s after death (test)

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
	# Walk = revenant_knight_walk_rm: the Mixamo forward walk retargeted onto the
	# knight and baked IN PLACE (brisk, upright, no lean). Run = the ActorCore run,
	# in-place. Both play at their native cadence; the body moves at the matched
	# WALK_SPEED / RUN_SPEED so the feet track the ground (no skate).
	var has_walk := _merge_clip("res://chars/revenant_knight_walk_rm.fbx", "walk", "loco", true)
	if not has_walk:
		has_walk = _merge_clip("res://chars/revenant_knight_walk.fbx", "walk", "loco", true)
	if has_walk:
		_retime_clip("loco/walk", WALK_ANIM_SPEED)
	var has_run := _merge_clip("res://chars/revenant_knight_run.fbx", "run", "run", true)
	if has_run:
		_retime_clip("run/run", RUN_ANIM_SPEED)
	print("PLAYER_CLIPS idle walk=%s run=%s" % [has_walk, has_run])
	# attacks (one-shot) + jump — see compare/PICKS.md
	_merge_attack(KEY_J, "res://chars/knight_slash.fbx", "slash", "j", 1.3, 15.0)
	_merge_attack(KEY_L, "res://chars/knight_ss_attack2.fbx", "ss_attack2", "l", 1.2, 20.0)
	_merge_attack(KEY_K, "res://chars/knight_ss_attack1.fbx", "ss_attack1", "k", 1.1, 25.0)
	_merge_attack(KEY_N, "res://chars/knight_ss_slash1.fbx", "ss_slash1", "n", 1.3, 15.0)
	_merge_attack(KEY_U, "res://chars/knight_ss_slash3.fbx", "ss_slash3", "u", 1.2, 8.0)
	_merge_attack(KEY_SPACE, "res://chars/knight_jump.fbx", "jump", "jmp", 1.2, 0.0)
	print("PLAYER_ATTACKS %d wired" % _attacks.size())
	_merge_clip("res://chars/knight_pl_death.fbx", "pl_death", "death", false)
	_merge_clip("res://chars/knight_pl_impact.fbx", "pl_impact", "hit", false)
	_apply_weapon_overrides()
	_attach_weapon()
	_build_anim_tree(has_walk, has_run)

func _build_hud() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	var bg := ColorRect.new()
	bg.color = Color(0, 0, 0, 0.55)
	bg.position = Vector2(24, 24)
	bg.size = Vector2(304, 34)
	layer.add_child(bg)
	_hp_fill = ColorRect.new()
	_hp_fill.color = Color(0.8, 0.15, 0.15)
	_hp_fill.position = Vector2(28, 28)
	_hp_fill.size = Vector2(296, 26)
	layer.add_child(_hp_fill)
	_hp_label = Label.new()
	_hp_label.position = Vector2(34, 30)
	_hp_label.add_theme_color_override("font_color", Color.WHITE)
	layer.add_child(_hp_label)
	_update_hud()

func _update_hud() -> void:
	if _hp_fill:
		var f := clampf(hp / MAX_HP, 0.0, 1.0)
		_hp_fill.size = Vector2(296.0 * f, 26.0)
		_hp_fill.color = Color(0.8, 0.15, 0.15) if f > 0.3 else Color(0.9, 0.4, 0.1)
	if _hp_label:
		_hp_label.text = "HP %d / %d%s" % [int(ceil(hp)), int(MAX_HP), "   — DEAD (press R)" if _dead else ""]

# Damage the player takes from a creature. Ignored during i-frames or death.
func take_damage(amount: float) -> void:
	if _dead or _invuln > 0.0:
		return
	hp = maxf(hp - amount, 0.0)
	_invuln = HIT_IFRAMES
	_sync_state()
	_update_hud()
	print("PLAYER_HURT -%.0f hp=%.0f" % [amount, hp])
	if hp <= 0.0:
		_die()
	elif _ap and _ap.has_animation("hit/pl_impact"):
		_attack_timer = 0.0
		_state = "hit"
		_play_oneshot("hit/pl_impact", 0.05, 1.4)

func _die() -> void:
	_dead = true
	_attack_timer = 0.0
	velocity = Vector3.ZERO
	_state = "dead"
	_sync_state()
	if _ap and _ap.has_animation("death/pl_death"):
		_play_oneshot("death/pl_death", 0.1, 1.0)
	_update_hud()
	print("PLAYER_DEAD")

func revive() -> void:
	_dead = false
	hp = MAX_HP
	_invuln = 0.0
	_state = "idle"
	_sync_state()
	if _sm:
		_tree.active = true
		_sm.start("idle")
	elif _ap:
		_ap.play("idle", 0.2)
	_update_hud()
	print("PLAYER_REVIVE hp=%.0f" % hp)

# Persist hp + death state so a rebuilt player (on world transition) resumes them.
func _sync_state() -> void:
	GameState.hp = hp
	GameState.dead = _dead

# Deal the active swing's damage to enemies in a forward arc.
func _deal_attack_damage() -> void:
	if _rig == null:
		return
	var facing := Vector3(sin(_rig.rotation.y), 0.0, cos(_rig.rotation.y))
	var half := deg_to_rad(ATTACK_ARC * 0.5)
	var hits := 0
	var nearest := 99.0
	for e in get_tree().get_nodes_in_group("enemy"):
		if not (e is Node3D) or not e.has_method("take_damage"):
			continue
		var to: Vector3 = (e as Node3D).global_position - global_position
		to.y = 0.0
		nearest = minf(nearest, to.length())
		if to.length() > ATTACK_RANGE:
			continue
		if to.length() > 0.01 and facing.angle_to(to.normalized()) <= half:
			e.take_damage(_pending_dmg)
			hits += 1
	print("PLAYER_HIT %d enemies dmg=%.0f (nearest=%.2f, range=%.2f)" % [hits, _pending_dmg, nearest, ATTACK_RANGE])

func _merge_attack(keycode: int, path: String, clip: String, lib: String, speed: float, dmg: float) -> void:
	if not _merge_clip(path, clip, lib, false):
		push_warning("player: attack merge failed %s" % clip)
		return
	var anim_name := "%s/%s" % [lib, clip]
	var length: float = _ap.get_animation(anim_name).length if _ap.has_animation(anim_name) else 1.0
	_attacks[keycode] = {"anim": anim_name, "speed": speed, "dmg": dmg, "len": length / maxf(speed, 0.01)}

# Merge a clip from a twin FBX export into the idle rig's AnimationPlayer.
# Remaps the clip's leading track-path segment to the target rig's prefix so
# tracks resolve even when the two FBXs were baked with different root names.
func _merge_clip(path: String, clip_name: String, lib_name: String, loop: bool) -> bool:
	var scene: PackedScene = load(path)
	if scene == null:
		return false
	var tmp: Node3D = scene.instantiate()
	var aps := _find_all(tmp, "AnimationPlayer")
	var ok := false
	if aps.size() > 0 and (aps[0] as AnimationPlayer).has_animation(clip_name):
		var anim: Animation = (aps[0] as AnimationPlayer).get_animation(clip_name).duplicate(true)
		anim.loop_mode = Animation.LOOP_LINEAR if loop else Animation.LOOP_NONE
		var prefix := _rig_prefix(_rig)
		if prefix != "":
			_remap_track_prefix(anim, prefix)
		var lib := AnimationLibrary.new()
		lib.add_animation(clip_name, anim)
		_ap.add_animation_library(lib_name, lib)
		ok = true
	tmp.free()
	return ok

# Bake a playback-speed multiplier into a merged loop clip by scaling every
# key time (and the clip length) by 1/factor — so playing it at the tree's
# native 1.0x reproduces the old _ap.play(clip, _, factor) look. The clips are
# in-place (no root motion), so this speed-match is what keeps feet on the
# ground. Scaling all keys by the same factor preserves their ordering.
func _retime_clip(anim_name: String, factor: float) -> void:
	if factor == 1.0 or _ap == null or not _ap.has_animation(anim_name):
		return
	var anim := _ap.get_animation(anim_name)
	for ti in range(anim.get_track_count()):
		for ki in range(anim.track_get_key_count(ti) - 1, -1, -1):
			anim.track_set_key_time(ti, ki, anim.track_get_key_time(ti, ki) / factor)
	anim.length = anim.length / factor

# Build the AnimationTree + idle/walk/run state machine in code. Falls back to
# the raw AnimationPlayer (idle) if the tree can't be built.
func _build_anim_tree(has_walk: bool, has_run: bool) -> void:
	if _ap == null:
		return
	var sm := AnimationNodeStateMachine.new()
	var states := [["idle", "idle"]]
	if has_walk:
		states.append(["walk", "loco/walk"])
	if has_run:
		states.append(["run", "run/run"])
	var i := 0
	for st in states:
		var na := AnimationNodeAnimation.new()
		na.animation = st[1]
		sm.add_node(st[0], na, Vector2(200 + i * 200, 100))
		i += 1
	# fully-connected immediate cross-fades (blend ~0.15s, matching the old plays)
	for a in states:
		for b in states:
			if a[0] == b[0]:
				continue
			var tr := AnimationNodeStateMachineTransition.new()
			tr.switch_mode = AnimationNodeStateMachineTransition.SWITCH_MODE_IMMEDIATE
			tr.xfade_time = 0.15
			sm.add_transition(a[0], b[0], tr)
	_tree = AnimationTree.new()
	add_child(_tree)
	_tree.anim_player = _tree.get_path_to(_ap)
	_tree.tree_root = sm
	_tree.active = true
	_sm = _tree.get("parameters/playback")
	_sm.start("idle")
	_state = "idle"
	_has_walk = has_walk
	_has_run = has_run

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

func _input(event: InputEvent) -> void:
	if not (event is InputEventKey):
		return
	var ev := event as InputEventKey
	if not ev.pressed or ev.echo:
		return
	if _dead:
		if ev.physical_keycode == KEY_R:
			revive()
		return
	if _attack_timer > 0.0:
		return
	if _attacks.has(ev.physical_keycode):
		_start_attack(ev.physical_keycode)

func _start_attack(keycode: int) -> void:
	var a: Dictionary = _attacks[keycode]
	_attack_timer = a["len"]
	_state = "attack"
	_play_oneshot(a["anim"], 0.08, a["speed"])
	# the swing lands ~40% into the clip (jump deals no damage)
	if a["dmg"] > 0.0:
		_damage_pending = a["len"] * 0.4
		_pending_dmg = a["dmg"]
	print("PLAYER_ATTACK %s" % a["anim"])

const FIRE_KEYS := {
	"j": KEY_J, "l": KEY_L, "k": KEY_K, "n": KEY_N, "u": KEY_U, "space": KEY_SPACE,
}

func _process(delta: float) -> void:
	# drive the simulated attack queue (headless verification)
	if _fire_queue.is_empty():
		return
	_fire_timer -= delta
	if _fire_timer <= 0.0 and _attack_timer <= 0.0:
		var key: String = _fire_queue.pop_front()
		if FIRE_KEYS.has(key) and _attacks.has(FIRE_KEYS[key]):
			_start_attack(FIRE_KEYS[key])
			_fire_timer = _attacks[FIRE_KEYS[key]]["len"] + 0.4

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
	if _invuln > 0.0:
		_invuln -= delta
	# test-only self damage to exercise death/revive (bypasses i-frames)
	if _hurt_rate > 0.0 and not _dead:
		hp = maxf(hp - _hurt_rate * delta, 0.0)
		_sync_state()
		_update_hud()
		if hp <= 0.0:
			_die()
	# active swing lands its damage partway through the clip
	if _damage_pending >= 0.0:
		_damage_pending -= delta
		if _damage_pending < 0.0:
			_deal_attack_damage()
	if _dead:
		velocity = Vector3.ZERO
		move_and_slide()
		_update_camera()
		if _autorevive:
			_revive_timer += delta
			if _revive_timer >= 1.5:
				_revive_timer = 0.0
				revive()
		return
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
	# attacks play one-shot and suppress the locomotion anim until they finish
	if _attack_timer > 0.0:
		_attack_timer -= delta
	else:
		_set_anim_state("run" if running else ("walk" if moving else "idle"))
	_update_camera()
	_log_accum += delta
	if _log_accum >= 0.5:
		_log_accum = 0.0
		print("PLAYER_POS %.2f,%.2f state=%s" % [global_position.x, global_position.z, _state])

# Drive locomotion through the AnimationTree state machine. _state stays the
# logical state (idle/walk/run) for the PLAYER_POS log even when a missing clip
# forces a visual fall-back to a lower gear.
func _set_anim_state(s: String) -> void:
	if _sm == null:
		# fallback: raw AnimationPlayer if the tree never built
		if s == _state or _ap == null:
			return
		_state = s
		var clip := "idle"
		if s == "run" and _ap.has_animation("run/run"):
			clip = "run/run"
		elif s != "idle" and _ap.has_animation("loco/walk"):
			clip = "loco/walk"
		_ap.play(clip, 0.2)
		return
	# re-arm the tree if a one-shot (attack/hit) deactivated it
	if not _tree.active:
		_tree.active = true
	if s == _state:
		return
	var target := s
	if target == "run" and not _has_run:
		target = "walk"
	if target == "walk" and not _has_walk:
		target = "idle"
	_state = s
	_sm.travel(target)

# Play a one-shot clip (attack/hit/death) on the raw AnimationPlayer,
# deactivating the tree so it doesn't fight for the skeleton. The tree is
# re-armed by the next _set_anim_state (locomotion) or by revive().
func _play_oneshot(anim: String, blend: float, speed: float) -> void:
	if _tree and _tree.active:
		_tree.active = false
	if _ap:
		_ap.play(anim, blend, speed)

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
