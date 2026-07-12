extends Object

# A small village built from village_kit_grimforge_v1 pieces, reached by
# leaving the courtyard's south gate. A north-south road spine (the player
# arrives at its north end) leads past cottages/houses/tavern/blacksmith to a
# cobbled square with a well + market, with the church prominent at the far
# end. Doors face the road/square (village door convention = local +Z at yaw
# 0, same as the castle kit). Town-local placement: village GLBs embed their
# own atlas, so keep their materials — only rebuild per-face normals (the kit
# ships smoothed normals that pillow-shade) and add box colliders.

const EnvBuilder := preload("res://scripts/env.gd")

const GX := 15   # ground tiles across (x)
const GZ := 19   # ground tiles deep (z)
const NON_SOLID := ["ground_grass", "ground_dirt", "ground_cobble", "ground_flagstone",
	"road_straight", "road_corner", "road_cross", "road_tee", "path_straight"]

# Timber-clad dwellings: their grey-stone wall swatch (atlas cell 0,7) is
# repainted with the kit's own brown timber in atlas_color_wood.png so they read
# as wooden houses. The church keeps its stone (masonry suits a church).
const WOOD_BUILDINGS := ["cottage", "house_small", "house_tall", "tavern", "blacksmith"]

static var _flat_cache := {}

# Where the player arrives from the courtyard — on the open road, a few tiles
# in from the north edge so the return trigger (just north) is easy to reach.
static func entrance_point() -> Vector3:
	return Vector3(0.0, 0.1, -(float(GZ) * 0.5 - 0.5) + 3.0)

static func build() -> Node3D:
	var root := EnvBuilder._make_nav_region()
	root.name = "Town"
	var pitch := 1.0
	var hx := float(GX) * pitch * 0.5 - pitch * 0.5
	var hz := float(GZ) * pitch * 0.5 - pitch * 0.5
	var cx := int(GX / 2)   # center column index (x = 0)

	# --- ground: grass field, road spine at x=0, cobbled square near the south ---
	for gx in range(GX):
		for gz in range(GZ):
			var x := float(gx) * pitch - hx
			var z := float(gz) * pitch - hz
			var kind := "ground_grass"
			var in_square: bool = absf(x) <= 3.0 and z >= 3.0 and z <= 7.0
			if gx == cx and z < 3.5:
				kind = "road_straight"         # road spine (north -> square)
			elif in_square:
				kind = "ground_cobble"         # town square
			_place(root, kind, Vector3(x, 0.0, z), 0.0)

	# --- buildings: doors face the road/square ---
	# west row (x=-4.5), doors face +X (yaw 90)
	_place(root, "cottage", Vector3(-4.5, 0.0, -5.0), 90.0)
	_place(root, "house_small", Vector3(-4.5, 0.0, -1.0), 90.0)
	_place(root, "blacksmith", Vector3(-4.5, 0.0, 2.5), 90.0)
	# east row (x=+4.5), doors face -X (yaw 270)
	_place(root, "house_tall", Vector3(4.5, 0.0, -5.0), 270.0)
	_place(root, "tavern", Vector3(4.7, 0.0, -1.0), 270.0)
	_place(root, "house_small", Vector3(4.5, 0.0, 2.5), 270.0)
	# church at the far (south) end, facing north into the square
	_place(root, "church", Vector3(0.0, 0.0, hz - 1.4), 180.0)

	# --- square dressing ---
	_place(root, "well", Vector3(-2.0, 0.0, 5.0), 0.0)
	_place(root, "market_stall", Vector3(2.0, 0.0, 5.0), 180.0)

	# --- road furniture ---
	_place(root, "signpost", Vector3(1.8, 0.0, -hz + 2.5), 0.0)
	for z in [-6.0, -3.0, 0.0, 3.0]:
		_place(root, "lamppost", Vector3(1.0 if int(z) % 2 == 0 else -1.0, 0.0, z), 0.0)

	# --- fences lining the road frontage ---
	for z in [-6.5, -2.5, 1.5]:
		_place(root, "fence", Vector3(-2.5, 0.0, z), 0.0)
		_place(root, "fence", Vector3(2.5, 0.0, z), 0.0)

	# --- trees + props ---
	_place(root, "tree", Vector3(-6.0, 0.0, -7.0), 0.0)
	_place(root, "tree", Vector3(6.0, 0.0, -7.0), 0.0)
	_place(root, "tree", Vector3(-6.0, 0.0, 6.0), 0.0)
	_place(root, "tree", Vector3(6.0, 0.0, 6.5), 0.0)
	_place(root, "haystack", Vector3(-6.0, 0.0, 2.0), 0.0)
	_place(root, "barrel", Vector3(-3.0, 0.0, 3.4), 0.0)
	_place(root, "crate", Vector3(3.2, 0.0, 3.6), 0.0)
	_place(root, "cart", Vector3(6.0, 0.0, 1.0), 0.0)
	# graveyard beside the church
	_place(root, "gravestone", Vector3(-2.5, 0.0, hz - 1.0), 0.0)
	_place(root, "gravestone", Vector3(-3.2, 0.0, hz - 2.0), 20.0)
	_place(root, "brazier", Vector3(-1.5, 0.0, 3.2), 0.0)
	_place(root, "brazier", Vector3(1.5, 0.0, 3.2), 0.0)

	return root

static func _place(parent: Node3D, model: String, pos: Vector3, yaw: float) -> Node3D:
	var scene: PackedScene = load("res://town/%s.glb" % model)
	if scene == null:
		push_warning("town: missing %s" % model)
		return null
	var inst: Node3D = scene.instantiate()
	inst.position = pos
	inst.rotation_degrees = Vector3(0.0, yaw, 0.0)
	_flatten_normals(inst, model in WOOD_BUILDINGS)
	parent.add_child(inst)
	if not (model in NON_SOLID):
		_add_collision(inst)
	return inst

static func _add_collision(inst: Node3D) -> void:
	var aabb := EnvBuilder._subtree_aabb(inst, inst.transform.affine_inverse())
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

# Village GLBs embed their own atlas; keep the material, only harden normals.
static func _flatten_normals(node: Node, wood: bool = false) -> void:
	var stack: Array = [node]
	while not stack.is_empty():
		var n: Node = stack.pop_back()
		if n is MeshInstance3D and (n as MeshInstance3D).mesh:
			var mi := n as MeshInstance3D
			var key := "%d_%s" % [mi.mesh.get_instance_id(), wood]
			if not _flat_cache.has(key):
				_flat_cache[key] = _flat_mesh(mi.mesh, wood)
			mi.mesh = _flat_cache[key]
		for c in n.get_children():
			stack.push_back(c)

static func _flat_mesh(src: Mesh, wood: bool = false) -> ArrayMesh:
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
		out.surface_set_material(out.get_surface_count() - 1, _fixed_material(src.surface_get_material(si), wood))
	return out

# The village atlas ships baked gradients in the ground swatches (grass tiles
# into stripes). atlas_color_fixed.png row-normalizes those; swap it into every
# village material (all pieces share one atlas).
static var _mat_cache := {}

static func _fixed_material(src: Material, wood: bool = false) -> Material:
	if src == null:
		return null
	var key := "%d_%s" % [src.get_instance_id(), wood]
	if _mat_cache.has(key):
		return _mat_cache[key]
	var atlas := "res://town/atlas_color_wood.png" if wood else "res://town/atlas_color_fixed.png"
	var fixed := src
	if src is BaseMaterial3D and ResourceLoader.exists(atlas):
		fixed = (src as BaseMaterial3D).duplicate()
		(fixed as BaseMaterial3D).albedo_texture = load(atlas)
		(fixed as BaseMaterial3D).texture_filter = BaseMaterial3D.TEXTURE_FILTER_NEAREST_WITH_MIPMAPS
	_mat_cache[key] = fixed
	return fixed
