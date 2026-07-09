extends SceneTree

# KD1 validation: import both knight locomotion FBXs, seek mid-clip, and
# verify the skeleton bone bbox stays character-sized (a broken bind explodes it).
# Run: godot --headless --path . --script res://scripts/check_knight.gd

func _initialize() -> void:
	var fail := false
	for name in ["idle", "walk"]:
		var path := "res://chars/revenant_knight_%s.fbx" % name
		var scene: PackedScene = load(path)
		if scene == null:
			print("FAIL %s: load null" % name)
			fail = true
			continue
		var inst: Node3D = scene.instantiate()
		get_root().add_child(inst)
		var ap := _find(inst, "AnimationPlayer") as AnimationPlayer
		var sk := _find(inst, "Skeleton3D") as Skeleton3D
		if ap == null or sk == null:
			print("FAIL %s: ap=%s sk=%s" % [name, ap, sk])
			fail = true
			continue
		var anims := ap.get_animation_list()
		print(name, " clips=", anims)
		if anims.size() == 0:
			print("FAIL %s: no clips" % name)
			fail = true
			continue
		var clip := ap.get_animation(anims[0])
		ap.play(anims[0])
		ap.seek(clip.length * 0.5, true)
		var mn := Vector3.INF
		var mx := -Vector3.INF
		for bi in range(sk.get_bone_count()):
			var p := sk.get_bone_global_pose(bi).origin
			mn = mn.min(p)
			mx = mx.max(p)
		var ext := mx - mn
		print("%s: bones=%d len=%.2fs bbox_extent=%s" % [name, sk.get_bone_count(), clip.length, ext])
		if ext.length() > 3.0 or ext.length() < 0.1:
			print("FAIL %s: bbox extent out of range" % name)
			fail = true
		inst.queue_free()
	print("KNIGHT_CHECK ", "FAIL" if fail else "PASS")
	quit(1 if fail else 0)

func _find(node: Node, cls: String) -> Node:
	if node.get_class() == cls:
		return node
	for c in node.get_children():
		var r := _find(c, cls)
		if r:
			return r
	return null
