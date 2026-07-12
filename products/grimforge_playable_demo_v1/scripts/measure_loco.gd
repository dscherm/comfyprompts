extends SceneTree

# Measure BOTH walk and run clips' natural ground speed at 1.0x (median backward
# foot-plant speed during stance x in-game scale). For no skate:
#   body_speed  ==  natural_1x * playback_multiplier
# So this tells us whether WALK_SPEED/WALK_ANIM_SPEED and RUN_SPEED/RUN_ANIM_SPEED
# are matched, and what they SHOULD be. Run:
#   godot --headless --path . --script res://scripts/measure_loco.gd

const TARGET_H := 0.85  # must match player.gd

func _initialize() -> void:
	for entry in [["revenant_knight_walk", "walk"], ["revenant_knight_run", "run"]]:
		var scene: PackedScene = load("res://chars/%s.fbx" % entry[0])
		if scene == null:
			print("%s LOAD FAIL" % entry[0]); continue
		var inst: Node3D = scene.instantiate()
		get_root().add_child(inst)
		var ap: AnimationPlayer = _find(inst, "AnimationPlayer")
		var sk: Skeleton3D = _find(inst, "Skeleton3D")
		if ap == null or sk == null or not ap.has_animation(entry[1]):
			print("%s MEASURE_FAIL missing ap/sk/clip" % entry[1]); inst.queue_free(); continue
		var s := TARGET_H / maxf(_aabb(inst).size.y, 0.01)
		var feet: Array[int] = []
		for bi in range(sk.get_bone_count()):
			if sk.get_bone_name(bi).to_lower().ends_with("foot"):
				feet.append(bi)
		var clip := ap.get_animation(entry[1])
		clip.loop_mode = Animation.LOOP_LINEAR
		ap.play(entry[1])
		var samples := []
		var elapsed := 0.0
		while elapsed < clip.length and samples.size() < 4000:
			await process_frame
			var t: float = ap.current_animation_position
			for f in feet:
				samples.append([t, f, sk.get_bone_global_pose(f).origin])
			elapsed = maxf(elapsed, t)
		var speeds: Array[float] = []
		for f in feet:
			var pts := samples.filter(func(e): return e[1] == f)
			var zs := pts.map(func(e): return e[2].z)
			zs.sort()
			if zs.is_empty(): continue
			var z_thresh: float = zs[int(zs.size() * 0.25)]
			for i in range(1, pts.size()):
				var dt: float = pts[i][0] - pts[i - 1][0]
				if dt <= 0.0001: continue
				var a: Vector3 = pts[i - 1][2]; var b: Vector3 = pts[i][2]
				if a.z <= z_thresh and b.z <= z_thresh:
					speeds.append(Vector2(b.x - a.x, b.y - a.y).length() / dt)
		speeds.sort()
		if speeds.is_empty():
			print("%s MEASURE_FAIL no stance samples" % entry[1]); inst.queue_free(); continue
		var natural: float = speeds[speeds.size() / 2] * s
		print("LOCO %s clip_len=%.3f natural_1x=%.3f m/s" % [entry[1], clip.length, natural])
		inst.queue_free()
	print("MEASURE_OK")
	quit(0)

func _find(node: Node, cls: String) -> Variant:
	if node.get_class() == cls: return node
	for c in node.get_children():
		var r: Variant = _find(c, cls)
		if r: return r
	return null

func _aabb(node: Node) -> AABB:
	var result := AABB(); var first := true
	var stack: Array = [[node, Transform3D.IDENTITY]]
	while not stack.is_empty():
		var top: Array = stack.pop_back()
		var n: Node = top[0]; var xf: Transform3D = top[1]
		if n is Node3D: xf = xf * (n as Node3D).transform
		if n is MeshInstance3D and (n as MeshInstance3D).mesh:
			var ab := xf * (n as MeshInstance3D).mesh.get_aabb()
			result = ab if first else result.merge(ab); first = false
		for c in n.get_children(): stack.push_back([c, xf])
	return result
