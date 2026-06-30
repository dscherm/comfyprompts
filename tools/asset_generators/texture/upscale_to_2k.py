"""Seam-preserving 2K upscale of each albedo via NMKD-Siax 4x ESRGAN.
wrap-pad 128 -> 4x (1280->5120) -> crop center 4096 (=orig*4) -> Lanczos to 2048."""
import json, time, urllib.request, urllib.error, os, glob
import numpy as np
from PIL import Image

HOST="http://localhost:8188"
ROOT="D:/Projects/comfyui-toolchain/products/texture_pack_fantasy_v1"
RAW=f"{ROOT}/_albedo_raw"
OUT=f"{ROOT}/_albedo_raw_2k"; os.makedirs(OUT, exist_ok=True)
INP="D:/Projects/ComfyUI/input"
PAD=128

def run_upscale(infile):
    g={
     "1":{"inputs":{"image":infile},"class_type":"LoadImage"},
     "2":{"inputs":{"model_name":"4x_NMKD-Siax_200k.pth"},"class_type":"UpscaleModelLoader"},
     "3":{"inputs":{"upscale_model":["2",0],"image":["1",0]},"class_type":"ImageUpscaleWithModel"},
     "4":{"inputs":{"filename_prefix":"up2k","images":["3",0]},"class_type":"SaveImage"},
    }
    body=json.dumps({"prompt":g}).encode()
    req=urllib.request.Request(f"{HOST}/prompt",data=body,headers={"Content-Type":"application/json"})
    try:
        pid=json.loads(urllib.request.urlopen(req,timeout=30).read())["prompt_id"]
    except urllib.error.HTTPError as e:
        print("  UPSCALE FAILED:",e.read().decode()[:300]); return None
    for _ in range(180):
        time.sleep(2)
        h=json.loads(urllib.request.urlopen(f"{HOST}/history/{pid}",timeout=10).read())
        if pid in h:
            for nid,o in h[pid].get("outputs",{}).items():
                if "images" in o: return o["images"][0]["filename"]
            return None
    return None

albedos=sorted(glob.glob(f"{RAW}/*.png"))
print(f"upscaling {len(albedos)} albedos to 2K")
for p in albedos:
    name=os.path.splitext(os.path.basename(p))[0]
    if os.path.exists(f"{OUT}/{name}.png"):
        print(f"  {name}: already done, skip"); continue
    a=np.asarray(Image.open(p).convert("RGB"))
    padded=np.pad(a,((PAD,PAD),(PAD,PAD),(0,0)),mode="wrap")   # seamless context
    Image.fromarray(padded).save(f"{INP}/pad_{name}.png")
    fn=run_upscale(f"pad_{name}.png")
    if not fn: print(f"  {name}: FAILED"); continue
    up=np.asarray(Image.open(f"D:/Projects/ComfyUI/output/{fn}").convert("RGB"))
    s=up.shape[0]; scale=s/padded.shape[0]                      # ~4x
    b=int(round(PAD*scale))                                     # border to crop
    core=up[b:b+int(round(a.shape[0]*scale)), b:b+int(round(a.shape[1]*scale))]
    im2k=Image.fromarray(core).resize((2048,2048),Image.LANCZOS)
    im2k.save(f"{OUT}/{name}.png")
    os.remove(f"{INP}/pad_{name}.png")
    try: os.remove(f"D:/Projects/ComfyUI/output/{fn}")
    except: pass
    print(f"  {name}: {a.shape[0]}px -> up {s}px -> 2048px OK")
print("DONE 2K albedos in", OUT)
