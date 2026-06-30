"""Derive seamless normal/roughness/AO from each albedo and package the pack.
Uses np.roll for all neighborhood ops so wrap (tiling) is preserved."""
import os, glob, json
import numpy as np
from PIL import Image

ROOT = "D:/Projects/comfyui-toolchain/products/texture_pack_fantasy_v1"
RAW = f"{ROOT}/_albedo_raw_2k"

def lum(rgb):  # 0..1 luminance
    return (0.299*rgb[...,0] + 0.587*rgb[...,1] + 0.114*rgb[...,2])

def box_blur_wrap(a, r):
    out = a.copy()
    for _ in range(2):  # two box passes ~ gaussian
        acc = np.zeros_like(out)
        for dx in range(-r, r+1):
            acc += np.roll(out, dx, axis=1)
        out = acc/(2*r+1)
        acc = np.zeros_like(out)
        for dy in range(-r, r+1):
            acc += np.roll(out, dy, axis=0)
        out = acc/(2*r+1)
    return out

def normal_from_height(h, strength=2.5):
    # central differences with wrap -> seamless gradients
    gx = (np.roll(h,-1,axis=1) - np.roll(h,1,axis=1)) * 0.5
    gy = (np.roll(h,-1,axis=0) - np.roll(h,1,axis=0)) * 0.5
    nx, ny, nz = -gx*strength, -gy*strength, np.ones_like(h)
    norm = np.sqrt(nx*nx+ny*ny+nz*nz)
    nx, ny, nz = nx/norm, ny/norm, nz/norm
    # OpenGL normal map (G = +Y up); encode to 0..1
    out = np.stack([nx*0.5+0.5, ny*0.5+0.5, nz*0.5+0.5], axis=-1)
    return out

def wrap_seam(arr):
    a = arr.astype(np.float32)
    if a.ndim==2: a=a[...,None]
    h = np.abs(a[:,0,:]-a[:,-1,:]).mean()
    v = np.abs(a[0,:,:]-a[-1,:,:]).mean()
    W=a.shape[1]
    interior=np.mean([np.abs(a[:,c,:]-a[:,c+1,:]).mean() for c in range(5,W-6,max(1,(W-11)//20))])
    return h*255, v*255, interior*255

def save(arr01, path):
    Image.fromarray((np.clip(arr01,0,1)*255).astype(np.uint8)).save(path)

albedos = sorted(glob.glob(f"{RAW}/*.png"))
print(f"processing {len(albedos)} materials")
report = []
for p in albedos:
    name = os.path.splitext(os.path.basename(p))[0]
    d = f"{ROOT}/{name}"; os.makedirs(d, exist_ok=True)
    rgb = np.asarray(Image.open(p).convert("RGB")).astype(np.float32)/255.0
    L = lum(rgb)
    # height = mild contrast-stretched luminance
    h = np.clip((L - L.min())/(L.max()-L.min()+1e-6), 0, 1)
    normal = normal_from_height(h, strength=2.5)
    # roughness: rougher where darker/high-detail; centered ~0.6, modest range
    detail = np.abs(h - box_blur_wrap(h, 3))
    rough = np.clip(0.55 + (0.5 - L)*0.35 + detail*1.5, 0.2, 0.95)
    # AO: low-freq luminance, mostly bright with darker crevices
    aoL = box_blur_wrap(L, 6)
    ao = np.clip(0.6 + (aoL - aoL.mean())*1.4, 0.25, 1.0)
    # write maps
    Image.open(p).convert("RGB").save(f"{d}/{name}_albedo.png")
    save(normal, f"{d}/{name}_normal.png")
    save(rough, f"{d}/{name}_roughness.png")
    save(ao,   f"{d}/{name}_ao.png")
    ah,av,ai = wrap_seam(rgb); nh,nv,ni = wrap_seam(normal)
    report.append({"material":name,
                   "albedo_seam":[float(round(ah,1)),float(round(av,1)),float(round(ai,1))],
                   "normal_seam":[float(round(nh,1)),float(round(nv,1)),float(round(ni,1))]})
    print(f"  {name}: albedo wrap {ah:.1f}/{av:.1f} (base {ai:.1f}) | normal wrap {nh:.1f}/{nv:.1f} (base {ni:.1f})")

# per-material preview strips + overall albedo contact sheet
cell=256; cols=4; rows=(len(albedos)+cols-1)//cols
sheet=Image.new("RGB",(cols*cell, rows*cell),(20,20,20))
for i,p in enumerate(albedos):
    im=Image.open(p).convert("RGB").resize((cell,cell))
    sheet.paste(im,((i%cols)*cell,(i//cols)*cell))
sheet.save(f"{ROOT}/_albedo_contact_sheet.png")

# one PBR strip example (first material): albedo|normal|rough|ao
ex = report[0]["material"]
strip=Image.new("RGB",(cell*4,cell))
for j,suf in enumerate(["albedo","normal","roughness","ao"]):
    im=Image.open(f"{ROOT}/{ex}/{ex}_{suf}.png").convert("RGB").resize((cell,cell))
    strip.paste(im,(j*cell,0))
strip.save(f"{ROOT}/_pbr_strip_{ex}.png")

json.dump(report, open(f"{ROOT}/_seam_report.json","w"), indent=1)
print("packaged ->", ROOT)
