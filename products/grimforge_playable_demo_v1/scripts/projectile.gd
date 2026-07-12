extends Area3D

# Caster spell orb (G5). Built entirely in code by npc.gd's _cast_projectile:
# a small emissive sphere + a colored point light that flies from the caster's
# chest toward the knight, lightly homing so it curves but is still dodgeable.
# On overlap with the player it deals its (reduced, ranged-fair) damage ONCE and
# frees itself; it also self-frees on its lifetime/max-range so nothing leaks.
#
# Collision: the player sits on layer 1, so the orb's mask is 1. Enemies are on
# layer 2 (npc.gd) and are never detected, so casters can't friendly-fire. The
# environment (walls/pillars) is ALSO on layer 1, but we IGNORE env bodies and
# pass through them — the great hall is an open aisle, so this keeps casts fair
# and reliable rather than letting a stray pillar edge eat the shot. The orb
# still despawns on its own timer/range, so nothing flies forever.

const SPEED := 3.0            # m/s in miniature-world scale (knight walks 0.6)
const HOMING := 1.6           # steer-toward-player rate; light so the orb is dodgeable
const LIFETIME := 4.0         # seconds before it fizzles
const MAX_RANGE := 8.0        # total travel cap (~AGGRO_RANGE + a little)
const HIT_Y := 0.4            # aim at the knight's chest, not his feet

var _target: Node3D
var _dmg := 6.0
var _dir := Vector3.FORWARD
var _life := LIFETIME
var _travelled := 0.0
var _spent := false

# Called by the caster right after add_child (so global_position is already set).
func setup(target: Node3D, dmg: float, color: Color) -> void:
	_target = target
	_dmg = dmg
	_dir = _aim()
	_build_visual(color)

func _ready() -> void:
	collision_layer = 0    # nothing needs to detect the orb itself
	collision_mask = 1     # the player (and env) live on layer 1
	monitoring = true
	var cs := CollisionShape3D.new()
	var sph := SphereShape3D.new()
	sph.radius = 0.12
	cs.shape = sph
	add_child(cs)
	body_entered.connect(_on_body_entered)

func _aim() -> Vector3:
	if _target == null or not is_instance_valid(_target):
		return _dir
	var to: Vector3 = (_target.global_position + Vector3(0.0, HIT_Y, 0.0)) - global_position
	if to.length() < 0.001:
		return _dir
	return to.normalized()

func _build_visual(color: Color) -> void:
	var mi := MeshInstance3D.new()
	var mesh := SphereMesh.new()
	mesh.radius = 0.08
	mesh.height = 0.16
	mi.mesh = mesh
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.emission_enabled = true
	mat.emission = color
	mat.emission_energy_multiplier = 4.0
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mi.material_override = mat
	add_child(mi)
	# a small colored glow sells the "magic" and pops in screenshots
	var glow := OmniLight3D.new()
	glow.light_color = color
	glow.light_energy = 2.5
	glow.omni_range = 1.2
	add_child(glow)

func _physics_process(delta: float) -> void:
	if _spent:
		return
	# light homing: gently curve toward the player's current chest position
	var desired := _aim()
	_dir = _dir.lerp(desired, clampf(HOMING * delta, 0.0, 1.0)).normalized()
	var step := _dir * SPEED * delta
	global_position += step
	_travelled += step.length()
	_life -= delta
	if _life <= 0.0 or _travelled >= MAX_RANGE:
		queue_free()

func _on_body_entered(body: Node) -> void:
	if _spent:
		return
	if body.is_in_group("player") and body.has_method("take_damage"):
		_spent = true
		body.take_damage(_dmg)
		queue_free()
	# env bodies (also layer 1) are ignored — the orb passes through and relies
	# on its own timer/range to despawn (see the header note).
