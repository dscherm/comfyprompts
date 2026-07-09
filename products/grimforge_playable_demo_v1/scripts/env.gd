extends Object

# Castle courtyard builder — instances castle_kit_grimforge_v1 GLBs from a
# layout table. Tile pitch is measured from the floor tile's AABB so the
# grid adapts if the kit's footprint changes.

const GRID := 14          # ground tiles per side
const WALL_INSET := 0.0   # walls sit on the outermost tile ring

static func build() -> Node3D:
	var root := Node3D.new()
	root.name = "Env"

	var tile_scene: PackedScene = load("res://kit/floor_cobble.glb")
	var ts := _footprint(tile_scene)
	var pitch: float = maxf(ts.x, 0.5)
	var half := float(GRID) * pitch * 0.5 - pitch * 0.5

	var flat := "--flat" in OS.get_cmdline_user_args()

	# --- ground: grass ring (2 tiles), flagstone cross paths, cobble court ---
	for gx in range(GRID):
		for gz in range(GRID):
			var kind := "floor_cobble"
			if not flat:
				if gx < 2 or gz < 2 or gx >= GRID - 2 or gz >= GRID - 2:
					kind = "floor_grass"
				elif gx == GRID / 2 or gx == GRID / 2 - 1 or gz == GRID / 2 or gz == GRID / 2 - 1:
					kind = "floor_flagstone"
			var pos := Vector3(float(gx) * pitch - half, 0.0, float(gz) * pitch - half)
			_place(root, kind, pos, 0.0)
	if flat:
		return root

	# --- perimeter walls on the grass ring edge ---
	var wall_scene: PackedScene = load("res://kit/wall.glb")
	var wl := _footprint(wall_scene)
	var wpitch: float = maxf(maxf(wl.x, wl.z), 0.5)
	var edge := half + pitch * 0.5
	var n := int(ceil((edge * 2.0) / wpitch)) - 1
	for i in range(1, n):
		var t := -edge + float(i) * wpitch
		_place(root, "wall", Vector3(t, 0.0, -edge), 0.0)
		# south row leaves a center gap for the gatehouse
		if absf(t) > wpitch * 1.4:
			_place(root, "wall", Vector3(t, 0.0, edge), 180.0)
		_place(root, "wall", Vector3(-edge, 0.0, t), 90.0)
		_place(root, "wall", Vector3(edge, 0.0, t), -90.0)
	for c in [Vector3(-edge, 0, -edge), Vector3(edge, 0, -edge), Vector3(-edge, 0, edge), Vector3(edge, 0, edge)]:
		_place(root, "wall_corner", c, 0.0)
	_place(root, "gatehouse", Vector3(0.0, 0.0, edge), 180.0)

	# --- buildings ---
	_place(root, "keep", Vector3(0.0, 0.0, -half + pitch * 1.2), 180.0)
	_place(root, "great_hall", Vector3(-half + pitch * 1.6, 0.0, -pitch * 1.0), 90.0)
	_place(root, "chapel", Vector3(half - pitch * 1.6, 0.0, -pitch * 1.0), -90.0)
	_place(root, "stable", Vector3(-half + pitch * 1.8, 0.0, half - pitch * 2.6), 90.0)
	_place(root, "market_stall", Vector3(half - pitch * 2.2, 0.0, half - pitch * 2.8), -120.0)
	_place(root, "well", Vector3(pitch * 1.5, 0.0, pitch * 1.2), 0.0)
	_place(root, "tower_round", Vector3(-half + pitch * 0.8, 0.0, -half + pitch * 0.8), 0.0)
	_place(root, "tower_square", Vector3(half - pitch * 0.8, 0.0, -half + pitch * 0.8), 0.0)

	# --- props ---
	_place(root, "cart", Vector3(-pitch * 1.8, 0.0, half - pitch * 3.2), 30.0)
	_place(root, "barrel", Vector3(-half + pitch * 2.6, 0.0, half - pitch * 2.2), 0.0)
	_place(root, "barrel", Vector3(-half + pitch * 2.9, 0.0, half - pitch * 2.4), 40.0)
	_place(root, "crate", Vector3(half - pitch * 2.8, 0.0, half - pitch * 2.2), 15.0)
	_place(root, "crate", Vector3(half - pitch * 3.1, 0.0, half - pitch * 2.5), 60.0)
	_place(root, "brazier", Vector3(-pitch * 1.2, 0.0, edge - pitch * 0.9), 0.0)
	_place(root, "brazier", Vector3(pitch * 1.2, 0.0, edge - pitch * 0.9), 0.0)
	_place(root, "statue", Vector3(0.0, 0.0, -half + pitch * 3.0), 180.0)
	_place(root, "banner_pole", Vector3(-pitch * 0.8, 0.0, -half + pitch * 3.6), 0.0)
	_place(root, "banner_pole", Vector3(pitch * 0.8, 0.0, -half + pitch * 3.6), 0.0)
	_place(root, "tree", Vector3(-half + pitch * 0.9, 0.0, pitch * 2.0), 0.0)
	_place(root, "tree", Vector3(half - pitch * 0.9, 0.0, pitch * 2.5), 70.0)
	_place(root, "stairs_stone", Vector3(pitch * 3.0, 0.0, -pitch * 2.5), -90.0)
	_place(root, "torch_wall", Vector3(0.0, 0.0, -half + pitch * 1.9), 180.0)

	return root

static var _flat_cache := {}

const NON_SOLID := ["floor_cobble", "floor_grass", "floor_flagstone", "floor_dirt", "torch_wall", "banner_pole"]

static func _place(parent: Node3D, model: String, pos: Vector3, yrot_deg: float) -> Node3D:
	var scene: PackedScene = load("res://kit/%s.glb" % model)
	if scene == null:
		push_warning("env: missing model %s" % model)
		return null
	var inst: Node3D = scene.instantiate()
	inst.position = pos
	inst.rotation_degrees = Vector3(0.0, yrot_deg, 0.0)
	_flatten_normals(inst)
	parent.add_child(inst)
	if not (model in NON_SOLID):
		_add_collision(inst)
	return inst

# Box collider from the model's AABB so the player cannot walk through
# buildings, walls, or props. Floors and thin decor stay non-solid.
static func _add_collision(inst: Node3D) -> void:
	# cancel inst's own transform — the body is parented under inst, so the
	# AABB must be in inst-local space or position/rotation apply twice
	var aabb := _subtree_aabb(inst, inst.transform.affine_inverse())
	if aabb.size.length() < 0.01:
		return
	var body := StaticBody3D.new()
	var shape := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = aabb.size
	shape.shape = box
	shape.position = aabb.get_center()
	body.add_child(shape)
	inst.add_child(body)

# The kit GLBs ship smoothed vertex normals that bend over hard box edges,
# pillow-shading every flat surface (worst on floor tiles). Rebuild each mesh
# non-indexed with per-face normals; cache per source mesh.
static func _flatten_normals(node: Node) -> void:
	var stack: Array = [node]
	while not stack.is_empty():
		var n: Node = stack.pop_back()
		if n is MeshInstance3D:
			var mi := n as MeshInstance3D
			if mi.mesh:
				var key := mi.mesh.get_instance_id()
				if not _flat_cache.has(key):
					_flat_cache[key] = _flat_mesh(mi.mesh)
				mi.mesh = _flat_cache[key]
		for c in n.get_children():
			stack.push_back(c)

static func _flat_mesh(src: Mesh) -> ArrayMesh:
	var out := ArrayMesh.new()
	for si in range(src.get_surface_count()):
		var arr := src.surface_get_arrays(si)
		var verts: PackedVector3Array = arr[Mesh.ARRAY_VERTEX]
		var old_normals: PackedVector3Array = arr[Mesh.ARRAY_NORMAL] if arr[Mesh.ARRAY_NORMAL] != null else PackedVector3Array()
		var uvs = arr[Mesh.ARRAY_TEX_UV]
		var idx: PackedInt32Array = arr[Mesh.ARRAY_INDEX] if arr[Mesh.ARRAY_INDEX] != null else PackedInt32Array()
		if idx.is_empty():
			idx = PackedInt32Array(range(verts.size()))
		var nv := PackedVector3Array()
		var nn := PackedVector3Array()
		var nu := PackedVector2Array()
		var has_uv: bool = uvs != null and (uvs as PackedVector2Array).size() == verts.size()
		for t in range(0, idx.size(), 3):
			var ia := idx[t]
			var ib := idx[t + 1]
			var ic := idx[t + 2]
			var fn := (verts[ib] - verts[ia]).cross(verts[ic] - verts[ia]).normalized()
			# orient against the source normals so winding conventions don't matter
			if old_normals.size() == verts.size():
				var avg := old_normals[ia] + old_normals[ib] + old_normals[ic]
				if fn.dot(avg) < 0.0:
					fn = -fn
			for j in [ia, ib, ic]:
				nv.append(verts[j])
				nn.append(fn)
				if has_uv:
					nu.append((uvs as PackedVector2Array)[j])
		var na := []
		na.resize(Mesh.ARRAY_MAX)
		na[Mesh.ARRAY_VERTEX] = nv
		na[Mesh.ARRAY_NORMAL] = nn
		if has_uv:
			na[Mesh.ARRAY_TEX_UV] = nu
		out.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, na)
		out.surface_set_material(out.get_surface_count() - 1, _fixed_material(src.surface_get_material(si)))
	return out

# The kit atlas ships baked vertical gradients in the floor swatches, which
# tile into visible stripes. atlas_color_fixed.png has those regions
# row-normalized; swap it into every kit material (all pieces share one atlas).
static var _mat_cache := {}

static func _fixed_material(src: Material) -> Material:
	if src == null:
		return null
	var key := src.get_instance_id()
	if _mat_cache.has(key):
		return _mat_cache[key]
	var fixed := src
	if src is BaseMaterial3D and ResourceLoader.exists("res://kit/atlas_color_fixed.png"):
		fixed = (src as BaseMaterial3D).duplicate()
		(fixed as BaseMaterial3D).albedo_texture = load("res://kit/atlas_color_fixed.png")
		(fixed as BaseMaterial3D).texture_filter = BaseMaterial3D.TEXTURE_FILTER_NEAREST_WITH_MIPMAPS
	_mat_cache[key] = fixed
	return fixed

static func _footprint(scene: PackedScene) -> Vector3:
	if scene == null:
		return Vector3.ONE
	var inst: Node3D = scene.instantiate()
	var aabb := _subtree_aabb(inst, Transform3D.IDENTITY)
	inst.free()
	return aabb.size

static func _subtree_aabb(node: Node, xform: Transform3D) -> AABB:
	var result := AABB()
	var first := true
	var stack: Array = [[node, xform]]
	while not stack.is_empty():
		var top: Array = stack.pop_back()
		var n: Node = top[0]
		var xf: Transform3D = top[1]
		if n is Node3D:
			xf = xf * (n as Node3D).transform
		if n is MeshInstance3D:
			var mi := n as MeshInstance3D
			if mi.mesh:
				var ab := xf * mi.mesh.get_aabb()
				if first:
					result = ab
					first = false
				else:
					result = result.merge(ab)
		for c in n.get_children():
			stack.push_back([c, xf])
	return result
