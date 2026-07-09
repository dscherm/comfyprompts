extends SceneTree

# Measures the walk clip's natural ground speed at the in-game scale:
# during stance the planted foot moves backward relative to the root at
# exactly the walking speed, so the median backward foot velocity while
# the foot is low = the no-skate ground speed at animation speed 1.0.
# Run: godot --headless --path . --script res://scripts/measure_walk.gd

const TARGET_H := 0.85  # must match player.gd

func _initialize() -> void:
	var scene: PackedScene = load("res://chars/revenant_knight_walk.fbx")
	var inst: Node3D = scene.instantiate()
	get_root().add_child(inst)
	var ap: AnimationPlayer = _find(inst, "AnimationPlayer")
	var sk: Skeleton3D = _find(inst, "Skeleton3D")
	if ap == null or sk == null or not ap.has_animation("walk"):
		print("MEASURE_FAIL missing ap/sk/walk")
		quit(1)
		return
	# in-game scale factor (same math as player.gd: AABB height -> TARGET_H)
	var aabb := _aabb(inst)
	var s := TARGET_H / maxf(aabb.size.y, 0.01)

	var feet: Array[int] = []
	for bi in range(sk.get_bone_count()):
		var bn := sk.get_bone_name(bi).to_lower()
		if bn.ends_with("foot") or bn.ends_with("_foot"):
			feet.append(bi)
	if feet.is_empty():
		for bi in range(sk.get_bone_count()):
			if "foot" in sk.get_bone_name(bi).to_lower():
				feet.append(bi)
	print("feet bones: ", feet.map(func(i): return sk.get_bone_name(i)))

	var clip := ap.get_animation("walk")
	clip.loop_mode = Animation.LOOP_LINEAR
	ap.play("walk")
	# seek() does not apply poses while the main loop is not iterating —
	# pump real frames instead and read the clip position back from the player
	var samples := []
	var elapsed := 0.0
	while elapsed < clip.length:
		await process_frame
		var t: float = ap.current_animation_position
		for f in feet:
			var p := sk.get_bone_global_pose(f).origin
			samples.append([t, f, p])
		elapsed = maxf(elapsed, t)
		if samples.size() > 4000:
			break
	# motion envelope sanity: distinguishes march-in-place from broken sampling
	for f in feet:
		var pts := samples.filter(func(e): return e[1] == f)
		var mn := Vector3.INF
		var mx := -Vector3.INF
		for e in pts:
			mn = mn.min(e[2])
			mx = mx.max(e[2])
		print("%s envelope=%s" % [sk.get_bone_name(f), mx - mn])
	# per-foot: collect horizontal speed while foot is in its lowest height band
	var speeds: Array[float] = []
	# the skeleton space is Z-up (whole-skeleton bbox is tallest on Z),
	# so stance = low Z, and travel speed lives in the XY plane
	for f in feet:
		var pts := samples.filter(func(e): return e[1] == f)
		var zs := pts.map(func(e): return e[2].z)
		zs.sort()
		var z_thresh: float = zs[int(zs.size() * 0.25)]
		for i in range(1, pts.size()):
			var dt: float = pts[i][0] - pts[i - 1][0]
			if dt <= 0.0001:
				continue  # loop wrap or duplicate frame
			var a: Vector3 = pts[i - 1][2]
			var b: Vector3 = pts[i][2]
			if a.z <= z_thresh and b.z <= z_thresh:
				var v := Vector2(b.x - a.x, b.y - a.y).length() / dt
				speeds.append(v)
	speeds.sort()
	if speeds.is_empty():
		print("MEASURE_FAIL no stance samples")
		quit(1)
		return
	var median: float = speeds[speeds.size() / 2]
	print("stance foot speed (skeleton space) median=%.3f m/s" % median)
	print("in-game scale s=%.3f -> natural ground speed at 1.0x = %.3f m/s" % [s, median * s])
	print("MEASURE_OK")
	quit(0)

func _find(node: Node, cls: String) -> Variant:
	if node.get_class() == cls:
		return node
	for c in node.get_children():
		var r: Variant = _find(c, cls)
		if r:
			return r
	return null

func _aabb(node: Node) -> AABB:
	var result := AABB()
	var first := true
	var stack: Array = [[node, Transform3D.IDENTITY]]
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
