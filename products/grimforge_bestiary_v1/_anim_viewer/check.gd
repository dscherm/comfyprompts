extends SceneTree

func _initialize() -> void:
	for name in ["ghoul", "cultist", "bone_golem", "imp"]:
		var scn = load("res://chars/%s_anim.fbx" % name)
		if scn == null:
			print("CHECK %s LOAD_FAIL" % name); continue
		var inst = scn.instantiate()
		get_root().add_child(inst)
		var skel: Skeleton3D = _find(inst, "Skeleton3D")
		var ap: AnimationPlayer = _find(inst, "AnimationPlayer")
		var mi: MeshInstance3D = _find(inst, "MeshInstance3D")
		var anim_name := ""
		var flen := 0.0
		if ap:
			var l := ap.get_animation_list()
			if l.size() > 0:
				anim_name = l[0]
				var a := ap.get_animation(anim_name)
				flen = a.length if a else 0.0
				ap.play(anim_name)
				ap.seek(flen * 0.5, true)
		var bones := 0
		var size := Vector3.ZERO
		if skel:
			bones = skel.get_bone_count()
			var mn := Vector3(1e9, 1e9, 1e9)
			var mx := -mn
			for b in range(bones):
				var p: Vector3 = (skel.global_transform * skel.get_bone_global_pose(b)).origin
				mn = mn.min(p); mx = mx.max(p)
			size = mx - mn
		var has_skin := mi != null and mi.skin != null
		# ratio = largest / smallest nonzero dim; a clean humanoid ~1.5-4, a scramble is huge
		var dims: Array = [size.x, size.y, size.z]
		dims.sort()
		var ratio: float = 999.0
		if float(dims[0]) > 0.001:
			ratio = float(dims[2]) / float(dims[0])
		print("CHECK %s bones=%d anim=%s len=%.2f bbox=(%.2f,%.2f,%.2f) ratio=%.1f hasSkin=%s" %
			[name, bones, anim_name, flen, size.x, size.y, size.z, ratio, has_skin])
		inst.queue_free()
	quit()

func _find(n: Node, cls: String) -> Node:
	if n.get_class() == cls:
		return n
	for c in n.get_children():
		var r := _find(c, cls)
		if r:
			return r
	return null
