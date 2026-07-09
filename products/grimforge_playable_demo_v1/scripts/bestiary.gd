extends Object

# Bestiary population — GrimForge bestiary characters placed around the
# castle courtyard. Bipeds are the Unity-baked single-clip FBXs from the
# bestiary anim carousel (albedo re-applied — textures do not survive the
# Unity FBX export); quadrupeds are the Blender-walk GLBs.
# Heights are miniature-world targets (kit walls are 1.3m).

const EnvBuilder := preload("res://scripts/env.gd")

# name, target height (m), position (x, z), y-rotation deg
const BIPEDS := [
	["skeleton_warrior", 0.80, Vector2(0.7, 5.0), 180.0],
	["ghoul", 0.75, Vector2(-4.2, 3.2), 120.0],
	["cultist", 0.80, Vector2(4.0, -1.0), -90.0],
	["plague_zombie", 0.78, Vector2(-2.5, 0.5), 60.0],
	["bone_golem", 1.10, Vector2(-3.0, -3.0), 135.0],
	["skeleton_mage", 0.80, Vector2(1.8, -4.2), -160.0],
	["necromancer", 0.85, Vector2(0.8, -3.4), 170.0],
	["lich_king", 0.95, Vector2(0.0, -4.6), 180.0],
	["imp", 0.50, Vector2(4.0, 3.4), -45.0],
]
const QUADS := [
	["dire_rat", 0.25, Vector2(-1.5, 3.4), 30.0],
	["bone_hound", 0.45, Vector2(2.2, 2.0), -60.0],
	["hell_hound", 0.50, Vector2(-3.8, -0.8), 100.0],
	["grave_boar", 0.45, Vector2(4.4, 1.2), -120.0],
]

static func build() -> Node3D:
	var root := Node3D.new()
	root.name = "Bestiary"
	for e in BIPEDS:
		var inst := _spawn(root, "res://chars/%s_anim.fbx" % e[0], e[1], e[2], e[3])
		if inst:
			_apply_albedo(inst, "res://chars/%s.png" % e[0])
			_loop_first_clip(inst)
	for e in QUADS:
		var inst := _spawn_quad(root, e[0], e[1], e[2], e[3])
		if inst:
			_loop_clip(inst, "walk")
	return root

# Quads load via runtime GLTFDocument from the multi-clip _v2.glb (the
# quad-carousel-proven path) and play the named walk cycle.
static func _spawn_quad(parent: Node3D, name: String, target_h: float, pos: Vector2, yrot: float) -> Node3D:
	var doc := GLTFDocument.new()
	var st := GLTFState.new()
	if doc.append_from_file("res://chars/%s_v2.glb" % name, st) != OK:
		push_warning("bestiary: quad load fail %s" % name)
		return null
	var model: Node3D = doc.generate_scene(st)
	var aabb := EnvBuilder._subtree_aabb(model, Transform3D.IDENTITY)
	var s := target_h / maxf(aabb.size.y, 0.01)
	var pivot := Node3D.new()
	parent.add_child(pivot)
	pivot.position = Vector3(pos.x, 0.0, pos.y)
	pivot.rotation_degrees = Vector3(0.0, yrot, 0.0)
	model.scale = Vector3(s, s, s)
	var c := aabb.get_center()
	model.position = Vector3(-c.x, -aabb.position.y, -c.z) * s
	pivot.add_child(model)
	return pivot

static func _spawn(parent: Node3D, path: String, target_h: float, pos: Vector2, yrot: float) -> Node3D:
	var scene: PackedScene = load(path)
	if scene == null:
		push_warning("bestiary: failed to load %s" % path)
		return null
	var inst: Node3D = scene.instantiate()
	var aabb := EnvBuilder._subtree_aabb(inst, Transform3D.IDENTITY)
	var h: float = maxf(aabb.size.y, 0.01)
	var s := target_h / h
	var pivot := Node3D.new()
	parent.add_child(pivot)
	pivot.position = Vector3(pos.x, 0.0, pos.y)
	pivot.rotation_degrees = Vector3(0.0, yrot, 0.0)
	inst.scale = Vector3(s, s, s)
	var c := aabb.get_center()
	inst.position = Vector3(-c.x, -aabb.position.y, -c.z) * s
	pivot.add_child(inst)
	return pivot

static func _apply_albedo(root: Node, texpath: String) -> void:
	var albedo: Texture2D = null
	if ResourceLoader.exists(texpath):
		albedo = load(texpath)
	for mi in _find_meshes(root):
		var m: Mesh = mi.mesh
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
			mi.set_surface_override_material(si, mat)

static func _loop_first_clip(root: Node) -> void:
	_loop_clip(root, "")

static func _loop_clip(root: Node, preferred: String) -> void:
	var ap := _find_anim_player(root)
	if ap == null:
		push_warning("bestiary: no AnimationPlayer under %s" % root.name)
		return
	var list := ap.get_animation_list()
	if list.size() == 0:
		return
	var clip := preferred if (preferred != "" and ap.has_animation(preferred)) else String(list[0])
	var a := ap.get_animation(clip)
	if a:
		a.loop_mode = Animation.LOOP_LINEAR
	ap.play(clip)

static func _find_meshes(node: Node) -> Array:
	var out: Array = []
	var stack: Array = [node]
	while not stack.is_empty():
		var n: Node = stack.pop_back()
		if n is MeshInstance3D:
			out.append(n)
		for c in n.get_children():
			stack.push_back(c)
	return out

static func _find_anim_player(node: Node) -> AnimationPlayer:
	var stack: Array = [node]
	while not stack.is_empty():
		var n: Node = stack.pop_back()
		if n is AnimationPlayer:
			return n
		for c in n.get_children():
			stack.push_back(c)
	return null
