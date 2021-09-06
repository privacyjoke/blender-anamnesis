import json
import bpy
import os

model_tag = bpy.context.selected_editable_objects[0].name
print(f"got model_tag={model_tag}")

pose_map = {'n_root': 'v.pose', 
            'n_root.001': 'm.pose', 
            'n_root.002': 'a.pose', 
            'n_root.003': 'm.pose'}

print(f"iterating over bones..")
folder_path = "C:\\users\\conor\\Documents\\Blender\\ffxiv\\rosetta"
out_path = f"{folder_path}\\{pose_map[model_tag]}"
map_path = f"{folder_path}\\map.json"

    
with open(map_path, 'r') as g:
    name_map = json.load(g)

pose = bpy.data.objects[model_tag].pose
j = {"Config": {"LoadPositions": True, "LoadRotations": True, "LoadScales": True}, 
         "Bones": {}}

for bone in pose.bones:
    if bone.name in name_map:
        name = name_map[bone.name]
        mat = bone.matrix
        rot = mat.to_quaternion()
        rx, ry, rz, rw = rot.x, rot.y, rot.z, rot.w
        new_rot = f"{float(rx)}, {float(ry)}, {float(rz)}, {float(rw)}"
        j['Bones'][name] = {"Position": "0, 0, 0", "Scale": "1, 1, 1", "Rotation": new_rot}
    else:
        print(f"missing {bone.name} in name_map")

try:
    os.remove(out_path)
except OSError:
    pass

with open(out_path, 'a') as f:
    json.dump(j, f)

print(f"wrote j to {out_path}")
