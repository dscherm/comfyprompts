extends SceneTree

# Determine whether the walk/run clips carry usable ROOT MOTION — i.e. the
# root/hip bone translates across the cycle (net + envelope). ActorCore/Mixamo
# clips baked "in place" show near-zero root translation and cannot drive
# movement. Run:
#   godot --headless --path . --script res://scripts/diag_rootmotion.gd

const TARGET_H := 0.85  # must match player.gd

func _initialize() -> void:
	for entry in [["revenant_knight_walk", "walk"], ["revenant_knight_run", "run"]]:
		var fname: String = entry[0]
		var clip_name: String = entry[1]
		var scene: PackedScene = load("res://chars/%s.fbx" % fname)
		var inst: Node3D = scene.instantiate()
		get_root().add_child(inst)
		var ap := _find(inst, "AnimationPlayer") as AnimationPlayer
		var sk := _find(inst, "Skeleton3D") as Skeleton3D
		if ap == null or sk == null or not ap.has_animation(clip_name):
			print("ROOTMOTION %s FAIL missing ap/sk/clip" % fname)
			inst.queue_free()
			continue
		# root bone = the bone with no parent (skeleton root)
		var root_bone := -1
		for bi in range(sk.get_bone_count()):
			if sk.get_bone_parent(bi) == -1:
				root_bone = bi
				break
		var clip := ap.get_animation(clip_name)
		# find which tracks target the root bone position, and print all position
		# track paths so we can see whether the FBX authored a root-motion track
		print("--- %s (clip=%s len=%.3f) root_bone=%s ---" % [fname, clip_name, clip.length, sk.get_bone_name(root_bone)])
		for ti in range(clip.get_track_count()):
			if clip.track_get_type(ti) == Animation.TYPE_POSITION_3D:
				var p := clip.track_get_path(ti)
				var sub := String(p.get_concatenated_subnames())
				if sub.to_lower().find("hip") >= 0 or sub == sk.get_bone_name(root_bone) or ti < 2:
					print("  postrack[%d] %s keys=%d" % [ti, p, clip.track_get_key_count(ti)])
		# pump real frames and record the root bone LOCAL pose translation
		clip.loop_mode = Animation.LOOP_NONE
		ap.play(clip_name)
		var mn := Vector3.INF
		var mx := -Vector3.INF
		var first := Vector3.INF
		var last := Vector3.ZERO
		var elapsed := 0.0
		var guard := 0
		while elapsed < clip.length and guard < 4000:
			await process_frame
			guard += 1
			var t: float = ap.current_animation_position
			var pos := sk.get_bone_pose_position(root_bone)
			if first == Vector3.INF:
				first = pos
			last = pos
			mn = mn.min(pos)
			mx = mx.max(pos)
			elapsed = maxf(elapsed, t)
		var s := TARGET_H / maxf(_aabb(inst).size.y, 0.01)
		var envelope := mx - mn
		var net := last - first
		# skeleton space is Z-up: horizontal travel is X/Y. Report both raw and scaled.
		print("  root local first=%s last=%s" % [first, last])
		print("  root envelope(raw)=%s net(raw)=%s" % [envelope, net])
		print("  scale s=%.3f envelope*s=%s net*s=%s" % [s, envelope * s, net * s])
		var horiz_env := Vector2(envelope.x, envelope.y).length() * s
		var yes := horiz_env > 0.05
		print("ROOTMOTION %s=%s horiz_envelope_scaled=%.3f" % [clip_name, "yes" if yes else "no", horiz_env])
		inst.queue_free()
	quit(0)

func _find(node: Node, cls: String) -> Node:
	if node.get_class() == cls:
		return node
	for c in node.get_children():
		var r := _find(c, cls)
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
