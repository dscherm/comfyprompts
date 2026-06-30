"""Clean close-up beauty shots of hero buildings for the listing gallery."""
import bpy, math, mathutils, os
D="C:/Users/scher/AppData/Local/Temp/claude/D--Projects-comfyui-toolchain/25899eda-2041-4e64-a0a8-0c83c9100526/scratchpad"
G=f"{D}/kit_glb"; P="D:/Projects/comfyui-toolchain/products/village_kit_grimforge_v1"
def Hx(h): return tuple(int(h[i:i+2],16)/255 for i in (0,2,4))+(1.0,)
def imp(name,loc,rot=0):
    before=set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=f"{G}/{name}.glb")
    for r in [o for o in bpy.data.objects if o not in before and not o.parent]:
        r.location=loc; r.rotation_euler.z=math.radians(rot)

bpy.ops.wm.read_factory_settings(use_empty=True); sc=bpy.context.scene
# ground
bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,-0.06)); g=bpy.context.active_object; g.scale=(30,30,0.1)
gm=bpy.data.materials.new("g"); gm.use_nodes=True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=Hx("46582f"); g.data.materials.append(gm)
# 4 hero buildings in a row, slightly turned to show framing
imp("cottage",(-4.5,0,0),22); imp("tavern",(-1.4,0,0),18)
imp("church",(1.9,0,0),20); imp("blacksmith",(5.2,0,0),22)
# clean bright studio + warm key
s=bpy.data.objects.new("S",bpy.data.lights.new("S",'SUN')); sc.collection.objects.link(s)
s.data.energy=3.4; s.data.angle=math.radians(4); s.rotation_euler=(math.radians(50),math.radians(8),math.radians(40))
f=bpy.data.objects.new("F",bpy.data.lights.new("F",'SUN')); sc.collection.objects.link(f)
f.data.energy=1.1; f.data.use_shadow=False; f.rotation_euler=(math.radians(62),0,math.radians(220))
sc.world=bpy.data.worlds.new("W"); sc.world.use_nodes=True
bg=sc.world.node_tree.nodes["Background"]; bg.inputs[1].default_value=0.6; bg.inputs[0].default_value=Hx("9fb0c0")
sc.view_settings.view_transform='Standard'
cam=bpy.data.objects.new("C",bpy.data.cameras.new("C")); sc.collection.objects.link(cam); sc.camera=cam
cam.data.type='ORTHO'; cam.data.ortho_scale=13.5
cam.location=(0,-12,5.5); look=mathutils.Vector((0,0,1.0))-mathutils.Vector(cam.location)
cam.rotation_euler=look.to_track_quat('-Z','Y').to_euler()
sc.render.engine='BLENDER_EEVEE'
try: sc.eevee.taa_render_samples=64
except Exception: pass
sc.render.resolution_x=1800; sc.render.resolution_y=620
sc.render.filepath=f"{P}/gallery_buildings.png"
bpy.ops.render.render(write_still=True)
print("CLOSEUPS DONE")
