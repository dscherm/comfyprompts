extends Node3D

# Animated bestiary carousel — loads Godot-imported Unity FBX scenes (each carries a
# Skeleton3D + AnimationPlayer with a baked clip), stands each in a row, plays its clip
# looping, slow-rotates the row. Uses Godot's native ufbx FBX import (not Blender).

const CHARS := [
	{"name": "skeleton_warrior", "clip": "attack"},
	{"name": "ghoul", "clip": "celebrate"},
	{"name": "cultist", "clip": "wave"},
	{"name": "plague_zombie", "clip": "hit"},
	{"name": "bone_golem", "clip": "attack"},
	{"name": "skeleton_mage", "clip": "wave"},
	{"name": "necromancer", "clip": "celebrate"},
	{"name": "revenant_knight", "clip": "wave"},
	{"name": "lich_king", "clip": "celebrate"},
	{"name": "imp", "clip": "dodge"},
]
const TARGET_H := 2.0
const SPACING := 1.9

var _pivots: Array = []

func _ready() -> void:
	var n := CHARS.size()
	for i in range(n):
		var path := "res://chars/%s_anim.fbx" % CHARS[i].name
		var scene = load(path)
		if scene == null:
			push_warning("failed to load %s" % path)
			continue
		var inst: Node3D = scene.instantiate()

		var aabb := _subtree_aabb(inst, Transform3D.IDENTITY)
		var h: float = maxf(aabb.size.y, 0.01)
		var s: float = TARGET_H / h
		inst.scale = Vector3(s, s, s)
		var c := aabb.get_center()
		inst.position = Vector3(-c.x, -aabb.position.y, -c.z) * s

		# apply the bake albedo (meshes kept their bake UVs); clay fallback if missing
		var texpath := "res://tex/%s.png" % CHARS[i].name
		var albedo: Texture2D = null
		if ResourceLoader.exists(texpath):
			albedo = load(texpath)
		for mi in _find_meshes(inst):
			var m: Mesh = mi.mesh
			for si in range(m.get_surface_count()):
				var mat := StandardMaterial3D.new()
				if albedo != null:
					mat.albedo_texture = albedo
					mat.roughness = 0.9
				else:
					mat.albedo_color = Color(0.64, 0.62, 0.58)
					mat.roughness = 0.85
				mi.set_surface_override_material(si, mat)

		var pivot := Node3D.new()
		add_child(pivot)
		pivot.position = Vector3((float(i) - (n - 1) / 2.0) * SPACING, 0.0, 0.0)
		pivot.add_child(inst)
		_pivots.append(pivot)

		var ap := _find_anim_player(inst)
		if ap:
			var list := ap.get_animation_list()
			if list.size() > 0:
				var a := ap.get_animation(list[0])
				if a:
					a.loop_mode = Animation.LOOP_LINEAR
				ap.play(list[0])

		var label := Label3D.new()
		label.text = "%s\n%s" % [CHARS[i].name, CHARS[i].clip]
		label.font_size = 44
		label.pixel_size = 0.004
		label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		label.position = Vector3(0.0, -0.30, 0.0)
		label.modulate = Color(0.95, 0.88, 0.72)
		pivot.add_child(label)

	var ground := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(maxf(n * SPACING + 4.0, 8.0), 8.0)
	ground.mesh = pm
	var gmat := StandardMaterial3D.new()
	gmat.albedo_color = Color(0.16, 0.16, 0.19)
	gmat.roughness = 1.0
	ground.material_override = gmat
	add_child(ground)

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50, -40, 0)
	sun.light_energy = 1.8
	sun.shadow_enabled = true
	add_child(sun)
	var fill := DirectionalLight3D.new()
	fill.rotation_degrees = Vector3(-15, 140, 0)
	fill.light_energy = 0.5
	add_child(fill)
	var we := WorldEnvironment.new()
	var e := Environment.new()
	e.background_mode = Environment.BG_COLOR
	e.background_color = Color(0.20, 0.21, 0.25)
	e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	e.ambient_light_color = Color(0.5, 0.5, 0.55)
	e.ambient_light_energy = 0.4
	we.environment = e
	add_child(we)

	var half_extent: float = (n - 1) / 2.0 * SPACING + TARGET_H * 0.9
	var cam := Camera3D.new()
	add_child(cam)
	cam.fov = 70.0
	cam.position = Vector3(0, TARGET_H * 0.6, half_extent / 1.15)
	cam.look_at(Vector3(0, TARGET_H * 0.48, 0), Vector3.UP)

var _shot_done := false
var _elapsed := 0.0

func _process(delta: float) -> void:
	for p in _pivots:
		(p as Node3D).rotate_y(delta * 0.4)
	_elapsed += delta
	if not _shot_done and _elapsed > 2.5:
		_shot_done = true
		await RenderingServer.frame_post_draw
		var img := get_viewport().get_texture().get_image()
		img.save_png("C:/Users/scher/.claude/jobs/6d258183/tmp/carousel_shot.png")
		print("SHOT_SAVED")

func _find_anim_player(node: Node) -> AnimationPlayer:
	if node is AnimationPlayer:
		return node
	for ch in node.get_children():
		var r := _find_anim_player(ch)
		if r:
			return r
	return null

func _find_meshes(node: Node) -> Array:
	var out: Array = []
	if node is MeshInstance3D and (node as MeshInstance3D).mesh:
		out.append(node)
	for ch in node.get_children():
		out += _find_meshes(ch)
	return out

func _subtree_aabb(node: Node, xform: Transform3D) -> AABB:
	var out := AABB()
	var have := false
	if node is VisualInstance3D:
		out = xform * (node as VisualInstance3D).get_aabb()
		have = true
	for ch in node.get_children():
		var cx := xform
		if ch is Node3D:
			cx = xform * (ch as Node3D).transform
		var ca := _subtree_aabb(ch, cx)
		if ca.size != Vector3.ZERO:
			out = ca if not have else out.merge(ca)
			have = true
	return out
