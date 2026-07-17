extends CharacterBody3D

# Wandering bestiary NPC. Picks random waypoints near its home spot, walks
# there (walk clip, speed-matched to scale like the player), then rests
# 2-5s playing its idle/flavor clip, and repeats. Collides with the castle
# (StaticBody3D colliders from env.gd) so it never enters a building.
# Bipeds merge their walk clip from <name>_walk.fbx (twin export of the
# <name>_anim.fbx rig); quads use walk/idle already in their _v2.glb.
# NPCs without a walk clip (lich_king, skeleton_mage) stay stationary idlers.

const EnvBuilder := preload("res://scripts/env.gd")
const ProjectileScript := preload("res://scripts/projectile.gd")

const WANDER_RADIUS := 3.0
const ARRIVE_DIST := 0.3
const ARENA := 6.4
const KNIGHT_SCALE := 0.486   # revenant_knight target_h/rig_height, for speed match
const KNIGHT_SPEED := 0.6     # tuned player MOVE_SPEED at that scale

# Shared CC_Base walk donor for bipeds whose OWN walk clip never baked. Unity's
# humanoid retarget rejected the lich_king / skeleton_mage AccuRIG avatars
# (isHuman=False) so KD6 produced no <name>_walk.fbx for them. But every bestiary
# biped is the SAME AccuRIG CC_Base skeleton — these two are a strict subset of
# the donor (they lack only finger bones, irrelevant to a walk, and the intermediate
# track path down to Skeleton3D is identical), so the donor's walk retargets onto
# them cleanly via the same first-segment prefix remap (_merge_walk). Verified with
# scripts/diag_mage_rigs.gd. This is the Godot-native fix for the 2 idlers that
# sidesteps the Unity 6 sourceAvatar CopyFromOther dead-end (CS0619).
const SHARED_WALK_DONOR := "res://chars/skeleton_warrior_walk.fbx"

# configuration set by bestiary.gd before add_child
var cfg := {}

var _rig: Node3D
var _ap: AnimationPlayer
var _walk_clip := ""
var _idle_clip := ""
var _move_speed := 0.4
var _anim_speed := 1.0
var _mobile := false
var _agent: NavigationAgent3D   # paths around building/wall footprints

var _state := "rest"
var _rest_left := 0.0
var _target := Vector3.ZERO
var _walk_budget := 0.0
var _rng := RandomNumberGenerator.new()
var _log_accum := 0.0

# Combat (bipeds with baked swipe+die become enemies)
const AGGRO_RANGE := 5.5
const ATTACK_RANGE := 1.05
const ATTACK_COOLDOWN := 2.0
const CHASE_MULT := 1.6
# HP/DMG now arrive via cfg from the EnemyDef resource (data/enemies/*.tres),
# injected by bestiary.gd. Defaults below (30 hp / 9 dmg) only apply if a def
# omits them.
const LUNGE_LEN := 0.8   # clip-less attack duration for creatures with no swipe
# Ranged casters (necromancer/skeleton_mage/lich_king): fire a spell orb from
# range instead of the melee lunge. They strike anywhere inside aggro range and
# hit slightly softer than melee since it's safer to attack from afar.
const CAST_RANGE := AGGRO_RANGE
const CAST_COOLDOWN := 2.2
const RANGED_DMG_MULT := 0.7
const KITE_RANGE := ATTACK_RANGE * 1.6   # back off if the knight closes to melee
var _ranged := false
var _is_enemy := false
var _fade_out := false   # death when no _die_clip: sink + shrink, then despawn
var max_hp := 30.0
var hp := 30.0
var _dmg := 9.0
var _swipe_clip := ""
var _die_clip := ""
var _dead := false
var _atk_cd := 0.0
var _swipe_timer := 0.0   # locked in the swipe anim
var _swipe_hit := -1.0    # seconds until this swipe lands its damage
var _despawn := -1.0
var _hpbar: Node3D
var _hpfill: MeshInstance3D
var _hpbar_w := 0.6
var _hpbar_show := 0.0

func _ready() -> void:
	collision_layer = 2   # NPCs on their own layer
	collision_mask = 1    # collide with the environment (layer 1)
	# deterministic-but-distinct wander per NPC (stable across verification runs)
	_rng.seed = hash(cfg.get("name", "npc"))
	_build_visual()
	_setup_collision()
	_setup_agent()
	# every creature is hostile; baked clips just decide the attack/death style
	_is_enemy = cfg.get("hostile", true)
	_ranged = cfg.get("ranged", false)
	if _is_enemy:
		add_to_group("enemy")
		max_hp = cfg.get("hp", 30.0)
		hp = max_hp
		_dmg = cfg.get("dmg", 9.0)
		_build_hpbar()
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
		elif ResourceLoader.exists(SHARED_WALK_DONOR):
			# no own walk clip (lich_king, skeleton_mage) -> retarget the shared
			# CC_Base donor walk so they wander + kite instead of standing frozen
			_merge_walk(SHARED_WALK_DONOR)
		# baked combat clips (if present) drive this enemy's attack/death;
		# creatures without them fall back to a lunge + fade (see _ready)
		if ResourceLoader.exists("res://chars/%s_swipe.fbx" % cname):
			_swipe_clip = _merge_named("res://chars/%s_swipe.fbx" % cname, "swipe", "atk", false)
			_die_clip = _merge_named("res://chars/%s_die.fbx" % cname, "die", "death", false)
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

# Merge any single clip into the rig's AnimationPlayer (track-prefix remapped),
# returning its play name "lib/clip" or "" on failure.
func _merge_named(path: String, clip: String, lib: String, loop: bool) -> String:
	var scene: PackedScene = load(path)
	if scene == null:
		return ""
	var tmp: Node3D = scene.instantiate()
	var aps := _find_all(tmp, "AnimationPlayer")
	var out := ""
	if aps.size() > 0 and (aps[0] as AnimationPlayer).has_animation(clip):
		var anim: Animation = (aps[0] as AnimationPlayer).get_animation(clip).duplicate(true)
		anim.loop_mode = Animation.LOOP_LINEAR if loop else Animation.LOOP_NONE
		var prefix := _rig_prefix(_rig)
		if prefix != "":
			_remap_track_prefix(anim, prefix)
		var alib := AnimationLibrary.new()
		alib.add_animation(clip, anim)
		_ap.add_animation_library(lib, alib)
		out = "%s/%s" % [lib, clip]
	tmp.free()
	return out

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

# --- combat ---

func _build_hpbar() -> void:
	var h: float = cfg.get("target_h", 0.8)
	_hpbar = Node3D.new()
	_hpbar.position = Vector3(0.0, h + 0.18, 0.0)
	_hpbar.visible = false
	add_child(_hpbar)
	_hpbar.add_child(_bar_quad(_hpbar_w, Color(0.05, 0.05, 0.05), 0.001))
	_hpfill = _bar_quad(_hpbar_w, Color(0.85, 0.15, 0.15), 0.002)
	_hpbar.add_child(_hpfill)

func _bar_quad(w: float, col: Color, z: float) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var q := QuadMesh.new()
	q.size = Vector2(w, 0.08)
	mi.mesh = q
	mi.position.z = z
	var mat := StandardMaterial3D.new()
	mat.albedo_color = col
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	mat.disable_receive_shadows = true
	mi.material_override = mat
	return mi

func _update_hpbar() -> void:
	if _hpfill == null:
		return
	var frac := clampf(hp / max_hp, 0.0, 1.0)
	_hpfill.scale.x = frac
	# keep the fill left-anchored as it shrinks (quad is centered)
	_hpfill.position.x = -_hpbar_w * (1.0 - frac) * 0.5

func take_damage(amount: float) -> void:
	if _dead:
		return
	hp = maxf(hp - amount, 0.0)
	_hpbar_show = 3.0
	if _hpbar:
		_hpbar.visible = true
	_update_hpbar()
	print("ENEMY_HURT %s -%.0f hp=%.0f" % [cfg.get("name", "?"), amount, hp])
	if hp <= 0.0:
		_die()

func _die() -> void:
	_dead = true
	velocity = Vector3.ZERO
	remove_from_group("enemy")
	collision_layer = 0
	if _hpbar:
		_hpbar.visible = false
	var die_len := 2.0
	if _die_clip != "" and _ap and _ap.has_animation(_die_clip):
		_ap.play(_die_clip, 0.1, 1.0)
		die_len = _ap.get_animation(_die_clip).length
	else:
		# no baked death: sink into the ground and shrink out (handled in _physics_process)
		_fade_out = true
		die_len = 1.0
	_despawn = die_len + 2.0
	print("ENEMY_DEAD %s" % cfg.get("name", "?"))

# Enemy behavior: chase the player when near, swipe when in range. Returns true
# if combat is driving this frame (so the wander logic is skipped).
func _combat_step(delta: float) -> bool:
	var player := get_tree().get_first_node_in_group("player")
	if player == null or not (player is Node3D):
		return false
	if "hp" in player and player.hp <= 0.0:
		return false   # player dead -> stand down
	# locked in an ongoing swipe
	if _swipe_timer > 0.0:
		velocity = Vector3.ZERO
		_face(player.global_position, delta)
		return true
	var to: Vector3 = player.global_position - global_position
	to.y = 0.0
	var dist := to.length()
	if dist > AGGRO_RANGE:
		return false
	if _ranged:
		return _ranged_step(player, dist, delta)
	if dist <= ATTACK_RANGE:
		velocity = Vector3.ZERO
		_face(player.global_position, delta)
		if _atk_cd <= 0.0:
			_start_swipe()
		else:
			_play(_idle_clip, 1.0)
		return true
	# chase — route around buildings/walls via the navmesh
	var dir := _nav_dir(player.global_position)
	velocity = dir * _move_speed * CHASE_MULT
	move_and_slide()
	_face(player.global_position, delta)
	_play(_walk_clip, _anim_speed)
	return true

func _start_swipe() -> void:
	_atk_cd = ATTACK_COOLDOWN
	var len := LUNGE_LEN
	if _swipe_clip != "" and _ap and _ap.has_animation(_swipe_clip):
		_ap.play(_swipe_clip, 0.08, 1.2)
		len = _ap.get_animation(_swipe_clip).length / 1.2
	else:
		# no baked swipe: a quick idle-posed lunge sells the bite/claw
		_play(_idle_clip, 1.8)
	_swipe_timer = len
	_swipe_hit = len * 0.45

# Ranged caster behavior: plant and fire the spell orb from anywhere inside
# aggro range, backing off a step if the knight closes to melee (only casters
# with a walk clip kite — statuesque idlers just hold their ground and cast).
# Reuses the swipe-timer/cooldown scaffolding so the cast gesture and pacing
# stay coherent with the melee path. Returns true (combat drives this frame).
func _ranged_step(player: Node3D, dist: float, delta: float) -> bool:
	velocity = Vector3.ZERO
	_face(player.global_position, delta)
	var kiting := false
	if _mobile and dist <= KITE_RANGE:
		var away: Vector3 = global_position - player.global_position
		away.y = 0.0
		if away.length() > 0.01:
			velocity = away.normalized() * _move_speed
			move_and_slide()
			_play(_walk_clip, _anim_speed)
			kiting = true
	if _atk_cd <= 0.0:
		_cast_projectile()
	elif not kiting:
		_play(_idle_clip, 1.0)
	return true

# Fire a spell orb toward the player. The gesture reuses the swipe clip (or the
# clip-less idle-pose beat) and the swipe-timer lock so casters pause on the
# cast, but no melee-contact damage is armed (_swipe_hit stays -1) — the orb
# carries the damage on impact instead.
func _cast_projectile() -> void:
	_atk_cd = CAST_COOLDOWN
	var len := LUNGE_LEN
	if _swipe_clip != "" and _ap and _ap.has_animation(_swipe_clip):
		_ap.play(_swipe_clip, 0.08, 1.2)
		len = _ap.get_animation(_swipe_clip).length / 1.2
	else:
		_play(_idle_clip, 1.8)   # clip-less cast beat
	_swipe_timer = len
	_spawn_projectile()
	print("ENEMY_CAST %s" % cfg.get("name", "?"))

func _spawn_projectile() -> void:
	var player := get_tree().get_first_node_in_group("player")
	if player == null or not (player is Node3D):
		return
	var h: float = cfg.get("target_h", 0.8)
	var origin := global_position + Vector3(0.0, h * 0.6, 0.0)
	var proj := Area3D.new()
	proj.set_script(ProjectileScript)
	var host: Node = get_tree().current_scene
	if host == null:
		host = get_parent()
	host.add_child(proj)
	proj.global_position = origin
	proj.setup(player, _dmg * RANGED_DMG_MULT, _cast_color())

func _cast_color() -> Color:
	match cfg.get("name", ""):
		"necromancer": return Color(0.4, 1.0, 0.35)   # sickly necrotic green
		"skeleton_mage": return Color(0.3, 0.9, 1.0)   # icy arcane cyan
		"lich_king": return Color(0.8, 0.4, 1.0)       # royal death-magic purple
	return Color(0.7, 0.5, 1.0)

func _deal_swipe_damage() -> void:
	var player := get_tree().get_first_node_in_group("player")
	if player == null or not (player is Node3D) or not player.has_method("take_damage"):
		return
	var to: Vector3 = player.global_position - global_position
	to.y = 0.0
	if to.length() <= ATTACK_RANGE + 0.4:
		player.take_damage(_dmg)

func _face(target: Vector3, delta: float) -> void:
	if _rig == null:
		return
	var to := target - global_position
	to.y = 0.0
	if to.length() < 0.01:
		return
	var yaw := atan2(to.x, to.z)
	_rig.rotation.y = lerp_angle(_rig.rotation.y, yaw, minf(8.0 * delta, 1.0))

func _setup_collision() -> void:
	var h: float = cfg.get("target_h", 0.8)
	var shape := CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.radius = clampf(h * 0.22, 0.1, 0.3)
	capsule.height = h
	shape.shape = capsule
	shape.position = Vector3(0.0, h * 0.5, 0.0)
	add_child(shape)

# NavigationAgent3D lets this NPC path around building/wall footprints (baked
# into the world's NavigationRegion3D at runtime) instead of sliding along them.
func _setup_agent() -> void:
	_agent = NavigationAgent3D.new()
	_agent.radius = 0.2                                  # matches the navmesh agent radius
	_agent.height = maxf(cfg.get("target_h", 0.8), 0.3)
	_agent.path_desired_distance = 0.3
	_agent.target_desired_distance = 0.25
	_agent.avoidance_enabled = false                     # capsule colliders handle NPC-vs-NPC
	add_child(_agent)

# Flat, normalized direction to move toward dest, routed around obstacles via the
# navmesh. During the brief post-bake window (map not yet synced) or when the
# target is directly reachable, this degrades to steering straight at the target —
# identical to the pre-nav behavior, so combat never stalls waiting on the bake.
func _nav_dir(dest: Vector3) -> Vector3:
	var flat := Vector3(dest.x, global_position.y, dest.z)
	if _agent == null:
		return _straight_dir(flat)
	_agent.target_position = flat
	var map := _agent.get_navigation_map()
	if not map.is_valid() or NavigationServer3D.map_get_iteration_id(map) == 0:
		return _straight_dir(flat)   # navmesh not baked/synced yet
	if _agent.is_navigation_finished():
		return _straight_dir(flat)
	var nxt := _agent.get_next_path_position()
	var d := nxt - global_position
	d.y = 0.0
	if d.length() < 0.001:
		return _straight_dir(flat)
	return d.normalized()

func _straight_dir(target: Vector3) -> Vector3:
	var d := target - global_position
	d.y = 0.0
	if d.length() < 0.001:
		return Vector3.ZERO
	return d.normalized()

func _physics_process(delta: float) -> void:
	if _ap == null:
		return
	# dead: play out the death clip (or sink+shrink), then despawn
	if _dead:
		velocity = Vector3.ZERO
		if _fade_out and _rig:
			_rig.scale *= maxf(1.0 - delta * 1.4, 0.0)
			position.y -= delta * 0.18
		if _despawn >= 0.0:
			_despawn -= delta
			if _despawn < 0.0:
				queue_free()
		return
	# combat timers
	if _atk_cd > 0.0:
		_atk_cd -= delta
	if _swipe_timer > 0.0:
		_swipe_timer -= delta
	if _swipe_hit >= 0.0:
		_swipe_hit -= delta
		if _swipe_hit < 0.0:
			_deal_swipe_damage()
	if _hpbar_show > 0.0:
		_hpbar_show -= delta
		if _hpbar and _hpbar_show <= 0.0:
			_hpbar.visible = false
	# enemy AI takes over when the player is near
	if _is_enemy and _combat_step(delta):
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
			var dir := _nav_dir(_target)
			velocity = dir * _move_speed
			move_and_slide()
			if _rig and dir.length() > 0.01:
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
	var arena: Vector2 = cfg.get("arena", Vector2(ARENA, ARENA))
	p.x = clampf(p.x, -arena.x, arena.x)
	p.y = clampf(p.y, -arena.y, arena.y)
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
