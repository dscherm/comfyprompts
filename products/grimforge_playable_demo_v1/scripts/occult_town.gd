extends Object

# A cursed occult village — the 4th world, reached by leaving the town's square.
# Natural dark-fantasy houses (village_kit_grimforge_darkfantasy_v1) dressed with
# ritual props (village_kit_grimforge_occult_v1). A north-south road spine (the
# player arrives at its north end, passing a palisade gate) runs past
# cottages/hovel/blacksmith/tavern/stable to a central RITUAL PLAZA — a summoning
# circle + altar ringed by standing stones — capped at the far end by a
# desecrated chapel. A crypt + graveyard cluster and a witch's barn flank it;
# witchlight braziers/candle-shrines glow from the emit atlas.
#
# The two kits ship colliding atlas filenames, so each was copied self-contained
# into its own subfolder: darkfantasy -> res://occult/df/, occult -> res://occult/occ/.
# Both GLBs EMBED their atlas in the .glb buffer, so the pieces render in colour
# with no external texture dependency; we only rebuild per-face normals (the kits
# ship smoothed normals that pillow-shade flat surfaces) and force nearest
# filtering for the crisp low-poly look. Door convention = local +Z at yaw 0
# (same GrimForge village generator as town.gd / the castle kit).

const EnvBuilder := preload("res://scripts/env.gd")

const GX := 17   # ground tiles across (x)
const GZ := 23   # ground tiles deep (z)
const NON_SOLID := ["ground_moss", "ground_mud", "ground_gravel", "ground_cobble",
	"ground_flagstone", "road_straight", "road_corner", "road_cross", "road_tee",
	"path_cross", "path_tee", "path_end", "summoning_circle", "palisade_gate"]

# Base-field mix for the walkable grid (ground_mud excluded — see build()).
const GROUND_MIX := ["ground_moss", "ground_gravel", "ground_flagstone", "ground_moss"]

static var _flat_cache := {}
static var _mat_cache := {}

# Where the player arrives from the town — on the road spine, a few tiles in from
# the north edge so the return trigger (just north) is easy to reach.
static func entrance_point() -> Vector3:
	return Vector3(0.0, 0.1, -(float(GZ) * 0.5 - 0.5) + 3.5)

static func build() -> Node3D:
	var root := EnvBuilder._make_nav_region()
	root.name = "OccultTown"
	var pitch := 1.0
	var hx := float(GX) * pitch * 0.5 - pitch * 0.5
	var hz := float(GZ) * pitch * 0.5 - pitch * 0.5
	var cx := int(GX / 2)   # center column index (x = 0)

	# --- ground: mixed broken earth, road spine at x=0, cobbled ritual plaza ---
	# A side-by-side render of the 5 DF ground swatches showed ground_mud is
	# uniquely defective: it bakes a near-black low-poly puddle mound covering
	# half the tile — not a normals problem (flatten doesn't touch it) and not
	# a subtle AO vignette, an oversized dark blob. Tiled uniformly it read as
	# an obvious "blob grid" from directly overhead. The other four swatches
	# (moss/gravel/cobble/flagstone) are all clean, so the
	# base field mixes those instead — moss/gravel/flagstone chosen per-tile by
	# a seeded hash of the tile's own coord (deterministic for the gate) so the
	# ground reads as broken, uneven earth rather than one uniform texture.
	# moss/gravel ship bumpy ~37deg tops (vs the dead-flat cobble/flagstone/
	# road), which is fine for the navmesh (agent_max_slope=45) — verified the
	# bake still produces a healthy polygon count with them in the mix.
	# Each non-road tile also gets a seeded 0/90/180/270 yaw so any residual
	# per-swatch detail doesn't line up into a grid either.
	for gx in range(GX):
		for gz in range(GZ):
			var x := float(gx) * pitch - hx
			var z := float(gz) * pitch - hz
			var kind := "ground_moss"
			var in_plaza: bool = absf(x) <= 2.0 and z >= 2.5 and z <= 6.5
			var on_spine: bool = gx == cx and z < 2.5
			if on_spine:
				kind = "road_straight"         # spine: entrance -> plaza
			elif in_plaza:
				kind = "ground_cobble"         # ritual plaza floor
			else:
				kind = GROUND_MIX[absi(hash(Vector2i(gx, gz))) % GROUND_MIX.size()]
			var yaw := 0.0 if on_spine else _tile_yaw(gx, gz)
			_place_df(root, kind, Vector3(x, 0.0, z), yaw)

	# --- palisade gate the player passes through at the north entrance ---
	_place_df(root, "palisade_gate", Vector3(0.0, 0.0, -hz + 2.5), 0.0)
	_place_occ(root, "skull_totem", Vector3(1.5, 0.0, -hz + 2.2), 0.0)
	_place_occ(root, "skull_totem", Vector3(-1.5, 0.0, -hz + 2.2), 0.0)

	# --- houses: doors face the spine (west row +X/yaw90, east row -X/yaw270) ---
	_place_df(root, "cottage", Vector3(-5.5, 0.0, -6.5), 90.0)
	_place_df(root, "hovel", Vector3(-5.5, 0.0, -3.5), 90.0)
	_place_df(root, "blacksmith", Vector3(-5.5, 0.0, -0.3), 90.0)
	_place_df(root, "windmill", Vector3(-6.0, 0.0, 3.8), 90.0)
	_place_df(root, "watchtower", Vector3(5.7, 0.0, -6.5), 270.0)
	_place_df(root, "cottage", Vector3(5.5, 0.0, -3.5), 270.0)
	_place_df(root, "tavern", Vector3(5.6, 0.0, -0.2), 270.0)
	_place_df(root, "stable", Vector3(5.6, 0.0, 3.5), 270.0)

	# --- desecrated chapel caps the far (south) end, facing north into the plaza ---
	_place_df(root, "chapel", Vector3(0.0, 0.0, hz - 1.8), 180.0)

	# --- village well + abandoned stall near the entrance ---
	_place_df(root, "well", Vector3(2.2, 0.0, -5.0), 0.0)
	_place_df(root, "market_stall", Vector3(-2.5, 0.0, -5.0), 90.0)

	# --- central ritual plaza: circle + altar ringed by a horseshoe of stones ---
	_place_occ(root, "summoning_circle", Vector3(0.0, 0.05, 4.5), 0.0)
	_place_occ(root, "ritual_altar", Vector3(0.0, 0.0, 4.5), 180.0)
	for s in [Vector3(2.4, 0, 4.5), Vector3(-2.4, 0, 4.5), Vector3(1.9, 0, 6.2),
			Vector3(-1.9, 0, 6.2), Vector3(0.0, 0, 6.7)]:
		_place_occ(root, "standing_stone", s, 0.0)
	_place_occ(root, "iron_brazier", Vector3(1.3, 0.0, 3.0), 0.0)
	_place_occ(root, "iron_brazier", Vector3(-1.3, 0.0, 3.0), 0.0)
	_place_occ(root, "candle_shrine", Vector3(1.1, 0.0, 5.3), 0.0)
	_place_occ(root, "candle_shrine", Vector3(-1.1, 0.0, 5.3), 0.0)
	_place_occ(root, "cauldron", Vector3(-2.3, 0.0, 5.6), 0.0)

	# --- crypt + graveyard cluster (east of the chapel) ---
	_place_occ(root, "crypt_entrance", Vector3(5.5, 0.0, 8.5), 270.0)
	for g in [Vector3(3.4, 0, 7.5), Vector3(4.3, 0, 9.3), Vector3(3.1, 0, 9.1),
			Vector3(2.6, 0, 8.1)]:
		_place_occ(root, "grave_cross", g, 0.0)
	_place_occ(root, "bone_pile", Vector3(3.0, 0.0, 6.8), 0.0)
	_place_occ(root, "hanged_tree", Vector3(3.9, 0.0, 6.1), 0.0)
	_place_occ(root, "iron_brazier", Vector3(3.4, 0.0, 8.6), 0.0)

	# --- witch's barn + dead field (west of the chapel) ---
	_place_occ(root, "creepy_barn", Vector3(-5.8, 0.0, 8.0), 90.0)
	_place_occ(root, "dead_tree", Vector3(-3.4, 0.0, 7.2), 0.0)
	_place_occ(root, "dark_scarecrow", Vector3(-3.0, 0.0, 3.2), 0.0)

	# --- outlying dead trees framing the entrance ---
	_place_occ(root, "dead_tree", Vector3(-6.6, 0.0, -6.0), 0.0)
	_place_occ(root, "dead_tree", Vector3(6.6, 0.0, -2.5), 0.0)

	return root

# Deterministic pseudo-random yaw (0/90/180/270) seeded from the tile's own
# grid coord — same layout every run (gate stays reproducible) but breaks the
# ground swatches' baked-vignette alignment into an irregular pattern.
static func _tile_yaw(gx: int, gz: int) -> float:
	var h := absi(hash(Vector2i(gx, gz)))
	return float(h % 4) * 90.0

static func _place_df(parent: Node3D, model: String, pos: Vector3, yaw: float) -> Node3D:
	return _place(parent, "res://occult/df/%s.glb" % model, model, pos, yaw)

static func _place_occ(parent: Node3D, model: String, pos: Vector3, yaw: float) -> Node3D:
	return _place(parent, "res://occult/occ/%s.glb" % model, model, pos, yaw)

static func _place(parent: Node3D, path: String, model: String, pos: Vector3, yaw: float) -> Node3D:
	var scene: PackedScene = load(path)
	if scene == null:
		push_warning("occult_town: missing %s" % path)
		return null
	var inst: Node3D = scene.instantiate()
	inst.position = pos
	inst.rotation_degrees = Vector3(0.0, yaw, 0.0)
	_flatten_normals(inst)
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

# Both kits' GLBs embed their atlas; keep the material, only harden normals (the
# kits ship smoothed normals that pillow-shade the flat low-poly faces).
static func _flatten_normals(node: Node) -> void:
	var stack: Array = [node]
	while not stack.is_empty():
		var n: Node = stack.pop_back()
		if n is MeshInstance3D and (n as MeshInstance3D).mesh:
			var mi := n as MeshInstance3D
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

# Keep the GLB's embedded atlas albedo; only force nearest filtering so the
# baked palette reads crisp (mipmapped nearest also tames gradient banding at
# tiling distance — the kit-render "atlas fix" without a hand-authored atlas).
const SagainkShader := preload("res://shaders/sagaink_surface.gdshader")

static func _fixed_material(src: Material) -> Material:
	if src == null:
		return null
	var key := src.get_instance_id()
	if _mat_cache.has(key):
		return _mat_cache[key]
	var fixed := src
	if src is BaseMaterial3D:
		if EnvBuilder.sagaink_kit():
			# occult kits embed their own atlas per-GLB (palette we can't re-bake),
			# so desaturate-to-ink in a spatial shader that keeps their glows as accents
			var sm := ShaderMaterial.new()
			sm.shader = SagainkShader
			sm.set_shader_parameter("albedo_tex", (src as BaseMaterial3D).albedo_texture)
			fixed = sm
		else:
			fixed = (src as BaseMaterial3D).duplicate()
			(fixed as BaseMaterial3D).texture_filter = BaseMaterial3D.TEXTURE_FILTER_NEAREST_WITH_MIPMAPS
	_mat_cache[key] = fixed
	return fixed
