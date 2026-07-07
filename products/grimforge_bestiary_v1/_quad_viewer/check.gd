extends SceneTree
func _initialize() -> void:
	for name in ["hell_hound","bone_hound","grave_boar","dire_rat"]:
		var doc := GLTFDocument.new(); var st := GLTFState.new()
		if doc.append_from_file("res://quads/%s_walk.glb" % name, st) != OK:
			print("CHECK %s LOAD_FAIL" % name); continue
		var inst = doc.generate_scene(st)
		get_root().add_child(inst)
		var ap: AnimationPlayer = _f(inst,"AnimationPlayer")
		var sk: Skeleton3D = _f(inst,"Skeleton3D")
		var an := ""; var ln := 0.0
		if ap:
			var l := ap.get_animation_list()
			if l.size()>0:
				an=l[0]; var a:=ap.get_animation(an); ln=a.length if a else 0.0
				ap.play(an); ap.seek(ln*0.5,true)
		var size := Vector3.ZERO; var bones := 0
		if sk:
			bones=sk.get_bone_count()
			var mn := Vector3(1e9,1e9,1e9); var mx := -mn
			for b in range(bones):
				var p: Vector3 = (sk.global_transform * sk.get_bone_global_pose(b)).origin
				mn=mn.min(p); mx=mx.max(p)
			size=mx-mn
		var dims := [size.x,size.y,size.z]; dims.sort()
		var ratio: float = 999.0
		if float(dims[0])>0.001: ratio=float(dims[2])/float(dims[0])
		print("CHECK %s anim=%s len=%.2f bones=%d posed_bbox=(%.2f,%.2f,%.2f) ratio=%.1f" % [name,an,ln,bones,size.x,size.y,size.z,ratio])
		inst.queue_free()
	quit()
func _f(n:Node,c:String)->Node:
	if n.get_class()==c: return n
	for ch in n.get_children():
		var r:=_f(ch,c)
		if r: return r
	return null
