extends SceneTree
func _initialize() -> void:
	for name in ["hell_hound","bone_hound","grave_boar","dire_rat"]:
		var doc := GLTFDocument.new(); var st := GLTFState.new()
		if doc.append_from_file("res://quads/%s_v2.glb" % name, st) != OK:
			print("CHK %s FAIL" % name); continue
		var inst = doc.generate_scene(st); get_root().add_child(inst)
		var ap: AnimationPlayer = _f(inst,"AnimationPlayer")
		var clips := "none"
		if ap: clips = ", ".join(ap.get_animation_list())
		print("CHK %s clips=[%s]" % [name, clips])
		inst.queue_free()
	quit()
func _f(n:Node,c:String)->Node:
	if n.get_class()==c: return n
	for ch in n.get_children():
		var r:=_f(ch,c)
		if r: return r
	return null
