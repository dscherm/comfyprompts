extends Object

# Castle courtyard builder — instances castle_kit_grimforge_v1 GLBs from a
# layout table. Tile pitch is measured from the floor tile's AABB so the
# grid adapts if the kit's footprint changes.

const GRID := 14          # ground tiles per side
const WALL_INSET := 0.0   # walls sit on the outermost tile ring

const NavRegionScript := preload("res://scripts/nav_region.gd")

# A NavigationRegion3D configured for the miniature world scale, wired to bake
# its navmesh from child kit meshes at runtime (see nav_region.gd). All three
# world builders wrap their geometry in one so enemies can path around the
# building/wall colliders instead of sliding along them.
static func _make_nav_region() -> NavigationRegion3D:
	var region := NavigationRegion3D.new()
	region.set_script(NavRegionScript)
	var nm := NavigationMesh.new()
	# miniature scale: NPCs are 0.25-1.1m, walls ~1.3m; a ~0.2m agent radius
	# with a fine cell keeps paths tight around the small footprints
	nm.cell_size = 0.08
	nm.cell_height = 0.05
	nm.agent_radius = 0.2
	nm.agent_height = 0.3
	nm.agent_max_climb = 0.2
	nm.agent_max_slope = 45.0
	# parse the placed kit meshes: flat floor tiles read as walkable ground,
	# tall buildings/walls read as obstacles the radius erodes around
	nm.geometry_parsed_geometry_type = NavigationMesh.PARSED_GEOMETRY_MESH_INSTANCES
	nm.geometry_source_geometry_mode = NavigationMesh.SOURCE_GEOMETRY_ROOT_NODE_CHILDREN
	region.navigation_mesh = nm
	return region

static func build() -> Node3D:
	var root := _make_nav_region()
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

	# --- perimeter wall ring (seamless: step with slight overlap, no gaps) ---
	# Kit door/opening convention (verified via diag_buildings): the door faces
	# local +Z at rotation 0. So a wall panel at rot 0 faces +Z; the ring uses
	# 0/90/180/270 so each side's panels face outward and tile corner-to-corner.
	var wall_scene: PackedScene = load("res://kit/wall.glb")
	var wl := _footprint(wall_scene)
	var wpitch: float = maxf(wl.x, 0.5)
	var edge := half + pitch * 0.5
	var span := edge * 2.0
	var count := int(ceil(span / (wpitch * 0.97)))   # overlap ~3% so no seams
	var step := span / float(count)
	var gate_half := 1.3                              # south gap for the gatehouse
	for i in range(count + 1):
		var t := -edge + float(i) * step
		_place(root, "wall", Vector3(t, 0.0, -edge), 0.0)          # north side
		if absf(t) > gate_half:
			_place(root, "wall", Vector3(t, 0.0, edge), 180.0)    # south side (gap)
		_place(root, "wall", Vector3(-edge, 0.0, t), 90.0)         # west side
		_place(root, "wall", Vector3(edge, 0.0, t), 270.0)        # east side
	for c in [Vector3(-edge, 0, -edge), Vector3(edge, 0, -edge), Vector3(-edge, 0, edge), Vector3(edge, 0, edge)]:
		_place(root, "wall_corner", c, 0.0)
	# gatehouse fills the south gap, door facing -Z (into the courtyard)
	_place(root, "gatehouse", Vector3(0.0, 0.0, edge), 180.0)
	_place(root, "tower_round", Vector3(-edge, 0.0, -edge), 0.0)   # back corners
	_place(root, "tower_square", Vector3(edge, 0.0, -edge), 0.0)

	# --- buildings: grid-aligned, doors (+Z local) rotated to face the center ---
	# rot_y: 0 door->+Z, 90 door->+X, 180 door->-Z, 270 door->-X
	_place(root, "keep", Vector3(0.0, 0.0, -5.0), 0.0)            # north, faces path south
	_place(root, "great_hall", Vector3(-5.0, 0.0, -1.5), 90.0)   # west, faces +X inward
	_place(root, "stable", Vector3(-5.0, 0.0, 3.0), 90.0)        # west, faces +X inward
	_place(root, "chapel", Vector3(5.0, 0.0, -1.5), 270.0)       # east, faces -X inward
	_place(root, "market_stall", Vector3(5.0, 0.0, 3.0), 270.0)  # east, faces -X inward
	_place(root, "well", Vector3(2.0, 0.0, 2.0), 0.0)            # off the central cross

	# --- props: flank the gate, dress the courtyard, corners ---
	_place(root, "brazier", Vector3(-1.5, 0.0, edge - 1.0), 0.0)
	_place(root, "brazier", Vector3(1.5, 0.0, edge - 1.0), 0.0)
	_place(root, "statue", Vector3(-2.0, 0.0, -4.5), 0.0)
	_place(root, "banner_pole", Vector3(-1.2, 0.0, -3.6), 0.0)
	_place(root, "banner_pole", Vector3(1.2, 0.0, -3.6), 0.0)
	_place(root, "cart", Vector3(-3.0, 0.0, 4.5), 0.0)
	_place(root, "barrel", Vector3(-3.2, 0.0, 1.2), 0.0)
	_place(root, "barrel", Vector3(-2.7, 0.0, 1.4), 0.0)
	_place(root, "crate", Vector3(3.2, 0.0, 1.2), 0.0)
	_place(root, "crate", Vector3(2.7, 0.0, 1.5), 0.0)
	_place(root, "tree", Vector3(-5.5, 0.0, 5.5), 0.0)
	_place(root, "tree", Vector3(5.5, 0.0, 5.5), 0.0)
	_place(root, "torch_wall", Vector3(-3.0, 0.0, -5.0), 90.0)
	_place(root, "torch_wall", Vector3(3.0, 0.0, -5.0), 270.0)

	return root

static var _flat_cache := {}

const NON_SOLID := ["floor_cobble", "floor_grass", "floor_flagstone", "floor_dirt",
	"torch_wall", "banner_pole", "banner", "gate_arch", "door_arch", "arrow_loop"]

static func _place(parent: Node3D, model: String, pos: Vector3, yrot_deg: float) -> Node3D:
	var scene: PackedScene = load("res://kit/%s.glb" % model)
	if scene == null:
		push_warning("env: missing model %s" % model)
		return null
	var inst: Node3D = scene.instantiate()
	inst.position = pos
	inst.rotation_degrees = Vector3(0.0, yrot_deg, 0.0)
	_flatten_normals(inst)
	if sagaink_kit():
		apply_variant(inst, "res://kit/atlas_sagaink", pos)
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
		if sagaink_kit() and has_uv:
			# route through SurfaceTool to synthesize tangents (the sagaink normal
			# map needs them) while keeping our computed flat per-face normals
			var st := SurfaceTool.new()
			st.begin(Mesh.PRIMITIVE_TRIANGLES)
			for vi in range(nv.size()):
				st.set_normal(nn[vi])
				st.set_uv(nu[vi])
				st.add_vertex(nv[vi])
			st.generate_tangents()
			st.commit(out)
		else:
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
	if src is BaseMaterial3D:
		if sagaink_kit() and ResourceLoader.exists("res://kit/atlas_sagaink_color.png"):
			fixed = sagaink_material(src as BaseMaterial3D, "res://kit/atlas_sagaink")
		elif ResourceLoader.exists("res://kit/atlas_color_fixed.png"):
			fixed = (src as BaseMaterial3D).duplicate()
			(fixed as BaseMaterial3D).albedo_texture = load("res://kit/atlas_color_fixed.png")
			(fixed as BaseMaterial3D).texture_filter = BaseMaterial3D.TEXTURE_FILTER_NEAREST_WITH_MIPMAPS
	_mat_cache[key] = fixed
	return fixed

# --sagaink-kit swaps the whole kit onto the inked sagaink atlas set: grayscale
# carved-ink albedo + a derived normal map (plank seams / mortar / reeds catch
# light) + AO (recesses stay shaded). Normal/AO are loaded as raw ImageTextures
# so the import pipeline doesn't sRGB-mangle their linear data.
static func sagaink_kit() -> bool:
	return "--sagaink-kit" in OS.get_cmdline_user_args()

# Per-instance material variety: pick the base atlas or its rolled _v1 by hashing
# the piece position, so repeated walls/houses don't clone the identical brick or
# plank arrangement. Shared by env (courtyard) and town. No-op if _v1 isn't baked.
static var _variant_cache := {}

static func apply_variant(node: Node, base_prefix: String, pos: Vector3) -> void:
	if (hash(str(pos.snapped(Vector3.ONE * 0.05))) & 1) == 0:
		return  # this instance keeps the base (v0) atlas
	var prefix := base_prefix + "_v1"
	if not ResourceLoader.exists(prefix + "_color.png"):
		return
	var stack: Array = [node]
	while not stack.is_empty():
		var n: Node = stack.pop_back()
		if n is MeshInstance3D:
			var mi := n as MeshInstance3D
			if mi.mesh and mi.mesh.get_surface_count() > 0:
				var bm := mi.mesh.surface_get_material(0)
				if bm is BaseMaterial3D:
					var key := "%d_%s" % [bm.get_instance_id(), prefix]
					if not _variant_cache.has(key):
						_variant_cache[key] = sagaink_material(bm as BaseMaterial3D, prefix)
					mi.material_override = _variant_cache[key]
		for c in n.get_children():
			stack.push_back(c)

static var _raw_tex_cache := {}

static func _raw_tex(res_path: String) -> Texture2D:
	if _raw_tex_cache.has(res_path):
		return _raw_tex_cache[res_path]
	var img := Image.load_from_file(ProjectSettings.globalize_path(res_path))
	var tex: Texture2D = ImageTexture.create_from_image(img) if img else null
	_raw_tex_cache[res_path] = tex
	return tex

# Build a sagaink material from an atlas set given its prefix (e.g.
# "res://kit/atlas_sagaink" -> _color/_n/_ao). Shared by every world that uses the
# baked-atlas kit (courtyard via env, village via town.gd with its wood variant).
static func sagaink_material(src: BaseMaterial3D, prefix: String) -> BaseMaterial3D:
	var m := src.duplicate() as BaseMaterial3D
	m.albedo_texture = load(prefix + "_color.png")
	m.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
	m.roughness = 0.95
	m.metallic = 0.0
	if ResourceLoader.exists(prefix + "_n.png"):
		var nt := _raw_tex(prefix + "_n.png")
		if nt:
			m.normal_enabled = true
			m.normal_texture = nt
			m.normal_scale = 1.0
	if ResourceLoader.exists(prefix + "_ao.png"):
		var at := _raw_tex(prefix + "_ao.png")
		if at:
			m.ao_enabled = true
			m.ao_texture = at
			m.ao_texture_channel = BaseMaterial3D.TEXTURE_CHANNEL_RED
			m.ao_light_affect = 0.6
	return m

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
