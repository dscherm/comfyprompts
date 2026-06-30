"""Expanded village hero (Vol1 + Vol2 pieces) -> marketing render."""
import bpy, math, mathutils, os
D="C:/Users/scher/AppData/Local/Temp/claude/D--Projects-comfyui-toolchain/25899eda-2041-4e64-a0a8-0c83c9100526/scratchpad"
G1=f"{D}/kit_glb"; G2=f"{D}/kit2_glb"
def Hx(h): return tuple(int(h[i:i+2],16)/255 for i in (0,2,4))+(1.0,)
def imp(name,loc,rot=0):
    path=f"{G2}/{name}.glb" if os.path.exists(f"{G2}/{name}.glb") else f"{G1}/{name}.glb"
    before=set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=path)
    for r in [o for o in bpy.data.objects if o not in before and not o.parent]:
        r.location=loc; r.rotation_euler.z=math.radians(rot)
def gb(sx,sy,sz,loc,rgb):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc); o=bpy.context.active_object; o.scale=(sx,sy,sz)
    m=bpy.data.materials.new("g"); m.use_nodes=True; m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=rgb
    m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value=1.0; o.data.materials.append(m)
    for p in o.data.polygons: p.use_smooth=False
bpy.ops.wm.read_factory_settings(use_empty=True); sc=bpy.context.scene
gb(26,26,0.2,(0,0,-0.1),Hx("3e5226"))           # grass
gb(13,13,0.2,(0,1,-0.06),Hx("4d3c29"))          # dirt plaza
gb(2.0,5,0.2,(0,-8,-0.05),Hx("2c6492"))         # moat/stream at front
# walls + portcullis gate, palisade wings
for x in range(-4,5): imp("wall",(x,6,0),0)
for y in range(-2,7): imp("wall",(-6,y,0),90); imp("wall",(6,y,0),90)
imp("wall_corner",(-6,6,0),0); imp("wall_corner",(6,6,0),270)
imp("gate_arch",(0,-2,0),0)
for x in (-2,-3,2,3): imp("palisade",(x,-2.4,0),0)
imp("stone_bridge",(0,-5,0),0)
# buildings ring
imp("cottage",(-4,4,0),18); imp("tavern",(4,4.2,0),-22); imp("barn",(0,5,0),0)
imp("church",(-4.3,0.6,0),90); imp("blacksmith",(4.4,0.6,0),-90)
imp("stable",(4.3,2.6,0),-95); imp("house_tall",(-4.4,2.6,0),95)
imp("windmill",(-7.6,-1.0,0),20); imp("guard_tower",(7.4,-1.0,0),0)
# plaza
imp("fountain",(0,1.2,0)); imp("well",(-1.8,-0.2,0)); imp("market_stall",(1.9,0.0,0),200)
imp("cart",(2.2,-1.2,0),30); imp("barrel",(-1.0,-1.4,0)); imp("crate",(-1.4,-1.4,0)); imp("haystack",(2.6,2.0,0))
imp("wood_pile",(-2.6,2.4,0),10); imp("anvil",(3.8,-0.2,0)); imp("trough",(4.0,1.6,0),90)
imp("weapon_rack",(6.0,0.0,0),90); imp("banner",(0.0,-1.6,0)); imp("stocks",(1.2,-1.5,0),20)
# graveyard corner (grimdark)
imp("crypt",(-5.6,-1.4,0),30); imp("gibbet",(-4.6,-1.6,0))
imp("gravestone",(-6.2,-0.6,0)); imp("gravestone",(-5.9,-1.0,0),15); imp("bone_pile",(-5.0,-0.9,0))
imp("tree_dead",(-6.6,-2.2,0)); imp("tree_dead",(-4.2,-2.4,0),40)
# nature & lights
for p,r in [((-7.0,4.6),0),((7.0,4.6),0),((-7.4,1.6),0)]: imp("pine",(p[0],p[1],0),r)
for p in [(7.2,2.6),(-2.0,-1.8),(2.0,3.4)]: imp("bush",(p[0],p[1],0))
for p in [(6.6,4.2),(-6.6,-0.2),(3.0,-1.6)]: imp("rocks",(p[0],p[1],0))
imp("tree",(5.6,3.8,0)); imp("tree",(-5.6,4.4,0)); imp("stump",(2.8,2.6,0))
imp("torch",(-0.7,-1.9,0)); imp("torch",(0.7,-1.9,0)); imp("lamppost",(-2.2,0.4,0)); imp("signpost",(1.0,-1.9,0),20)
# dusk mood
sc.world=bpy.data.worlds.new("W"); sc.world.use_nodes=True
bg=sc.world.node_tree.nodes["Background"]; bg.inputs[1].default_value=0.34; bg.inputs[0].default_value=Hx("19202c")
sc.view_settings.view_transform='Standard'
def sun(e,rot,c,sh=True):
    s=bpy.data.objects.new("S",bpy.data.lights.new("S",'SUN')); sc.collection.objects.link(s)
    s.data.energy=e; s.data.angle=math.radians(5); s.data.color=c; s.data.use_shadow=sh
    s.rotation_euler=(math.radians(rot[0]),math.radians(rot[1]),math.radians(rot[2]))
sun(2.5,(46,10,42),(0.96,0.88,0.80)); sun(1.0,(60,0,225),(0.6,0.7,0.95),False)
def pl(loc,c,e):
    l=bpy.data.lights.new("P",'POINT'); l.color=c; l.energy=e; o=bpy.data.objects.new("P",l); o.location=loc; sc.collection.objects.link(o)
pl((-0.7,-1.9,0.9),(1,0.5,0.18),60); pl((0.7,-1.9,0.9),(1,0.5,0.18),60)
pl((-4,3.3,0.9),(1,0.6,0.25),45); pl((4,3.3,0.9),(1,0.6,0.25),45)
pl((4.4,1.6,1.2),(1,0.55,0.2),40)
cam=bpy.data.objects.new("C",bpy.data.cameras.new("C")); sc.collection.objects.link(cam); sc.camera=cam
cam.data.type='ORTHO'; cam.data.ortho_scale=19; cam.location=(15,-15,13)
look=mathutils.Vector((0,0.5,0.6))-mathutils.Vector(cam.location); cam.rotation_euler=look.to_track_quat('-Z','Y').to_euler()
sc.render.engine='BLENDER_EEVEE'
try: sc.eevee.taa_render_samples=48
except Exception: pass
sc.render.resolution_x=1600; sc.render.resolution_y=1150; sc.render.filepath=f"{D}/village_hero_v2.png"
bpy.ops.render.render(write_still=True)
print("HERO2 DONE")
