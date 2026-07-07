extends Node3D
# Quad carousel v2 — each UniRig-rigged quad plays a different clip (idle/walk/run/
# attack) from its multi-clip GLB, on a slow turntable. Runtime GLTFDocument load.
const CHARS := [
	{"name": "hell_hound", "clip": "run"},
	{"name": "bone_hound", "clip": "walk"},
	{"name": "grave_boar", "clip": "attack"},
	{"name": "dire_rat", "clip": "idle"},
]
const TARGET_H := 1.5
const SPACING := 2.1
var _pivots: Array = []
var _shot := false
var _elapsed := 0.0

func _ready() -> void:
	var n := CHARS.size()
	for i in range(n):
		var doc := GLTFDocument.new(); var st := GLTFState.new()
		if doc.append_from_file("res://quads/%s_v2.glb" % CHARS[i].name, st) != OK:
			push_warning("load fail %s" % CHARS[i].name); continue
		var model: Node3D = doc.generate_scene(st)
		var aabb := _subtree_aabb(model, Transform3D.IDENTITY)
		var s: float = TARGET_H / maxf(aabb.size.y, 0.01)
		model.scale = Vector3(s, s, s)
		var c := aabb.get_center()
		model.position = Vector3(-c.x, -aabb.position.y, -c.z) * s
		var pivot := Node3D.new(); add_child(pivot)
		pivot.position = Vector3((float(i) - (n - 1) / 2.0) * SPACING, 0.0, 0.0)
		pivot.add_child(model); _pivots.append(pivot)
		var ap := _find_anim(model)
		if ap:
			var clip: String = CHARS[i].clip
			if not ap.has_animation(clip):
				var l := ap.get_animation_list()
				clip = l[0] if l.size() > 0 else ""
			if clip != "":
				var a := ap.get_animation(clip)
				if a: a.loop_mode = Animation.LOOP_LINEAR
				ap.play(clip)
		var lab := Label3D.new()
		lab.text = "%s\n%s" % [CHARS[i].name, CHARS[i].clip]
		lab.font_size = 38; lab.pixel_size = 0.004
		lab.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		lab.position = Vector3(0, -0.28, 0); lab.modulate = Color(0.95, 0.88, 0.72)
		pivot.add_child(lab)
	var ground := MeshInstance3D.new(); var pm := PlaneMesh.new()
	pm.size = Vector2(maxf(n*SPACING+4, 8), 8); ground.mesh = pm
	var gm := StandardMaterial3D.new(); gm.albedo_color = Color(0.16,0.16,0.19); gm.roughness = 1.0
	ground.material_override = gm; add_child(ground)
	var sun := DirectionalLight3D.new(); sun.rotation_degrees = Vector3(-50,-40,0); sun.light_energy = 1.9; sun.shadow_enabled = true; add_child(sun)
	var fill := DirectionalLight3D.new(); fill.rotation_degrees = Vector3(-15,140,0); fill.light_energy = 0.5; add_child(fill)
	var we := WorldEnvironment.new(); var e := Environment.new()
	e.background_mode = Environment.BG_COLOR; e.background_color = Color(0.20,0.21,0.25)
	e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR; e.ambient_light_color = Color(0.5,0.5,0.55); e.ambient_light_energy = 0.4
	we.environment = e; add_child(we)
	var half: float = (n-1)/2.0*SPACING + TARGET_H*0.9
	var cam := Camera3D.new(); add_child(cam); cam.fov = 68
	cam.position = Vector3(0, TARGET_H*0.55, half/1.05); cam.look_at(Vector3(0, TARGET_H*0.4, 0), Vector3.UP)

func _process(delta: float) -> void:
	for p in _pivots: (p as Node3D).rotate_y(delta * 0.35)
	_elapsed += delta
	if not _shot and _elapsed > 2.5:
		_shot = true
		await RenderingServer.frame_post_draw
		get_viewport().get_texture().get_image().save_png("C:/Users/scher/.claude/jobs/6d258183/tmp/quad_carousel_v2.png")

func _find_anim(node: Node) -> AnimationPlayer:
	if node is AnimationPlayer: return node
	for c in node.get_children():
		var r := _find_anim(c)
		if r: return r
	return null

func _subtree_aabb(node: Node, xform: Transform3D) -> AABB:
	var out := AABB(); var have := false
	if node is VisualInstance3D:
		out = xform * (node as VisualInstance3D).get_aabb(); have = true
	for c in node.get_children():
		var cx := xform
		if c is Node3D: cx = xform * (c as Node3D).transform
		var ca := _subtree_aabb(c, cx)
		if ca.size != Vector3.ZERO:
			out = ca if not have else out.merge(ca); have = true
	return out
