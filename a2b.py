from mathutils import Quaternion, Matrix
from shutil import copyfile
import json
import bpy
import os


model_tag = bpy.context.selected_editable_objects[0].name
ob = bpy.context.object

print(f"iterating over bones..")
folder_path = "C:\\users\\conor\\Documents\\Blender\\ffxiv\\rosetta"
in_path = f"{folder_path}\\v_init_anam.pose"
map_path = f"{folder_path}\\map.json"

    
with open(map_path, 'r') as g:
    name_map = json.load(g)

with open(in_path, 'r') as f:
    j = json.load(f)    

model_tag = 'n_root'

pose = bpy.data.objects[model_tag].pose

bones_done = {k: False for k in pose.bones.keys()}
world_matrices = {k: None for k in pose.bones.keys()}
local_inverses = {k: None for k in pose.bones.keys()}

def update(bone_name):
    if bone_name in name_map:
        print(f'updating {bone_name}') 
        # only update the bone rotation if we haven't already
        if not bones_done[bone_name]:
            # update all parents first
            pose_bone = ob.pose.bones[bone_name]
            if pose_bone.parent is not None:
                update(pose_bone.parent.name)
            
            # now that parent is updated, update this bone
            local = ob.data.bones[bone_name].matrix_local
            local_inverses[bone_name] = local.inverted()
            
            if pose_bone.parent is None:
                # just update world matrix and proceed, nothing else to do for root
                world_matrices[bone_name] = pose_bone.matrix
            else:
                # this is largely based on this post:
                # https://blender.stackexchange.com/questions/44637/how-can-i-manually-calculate-bpy-types-posebone-matrix-using-blenders-python-ap
                # so the basic relationship that i exploit is:
                # matrix_world = parent world * parent_local_inv * matrix_local * matrix_basis,
                # matrix_local is fixed (its about rest position), and matrix_basis is basically just 
                # the local rotation, so its more or less equivalent to bone.rotation_quaternion
                
                # 1. construct the desired world matrix
                desired_world_matrix = Matrix()
                Q = Quaternion()
                rot_string = j['Bones'][name_map[bone_name]]['Rotation']
                pos_string = j['Bones'][name_map[bone_name]]['Position']
                print(f"{bone_name}: rot_string={rot_string}, pos_string={pos_string}")
                rx, ry, rz, rw = [float(x) for x in rot_string.split(',')]
                px, py, pz = [float(x) for x in pos_string.split(',')]
                Q.x, Q.y, Q.z, Q.w = rx, ry, rz, rw
                R = Q.to_matrix()
                for i in range(3):
                    for k in range(3):
                        desired_world_matrix[i][k] = R[i][k]
                desired_world_matrix[0][3] = px
                desired_world_matrix[1][3] = py
                desired_world_matrix[2][3] = pz
                
                # 2. calculate the net transformation matrix (which goes from basis to world)
                parent_world = world_matrices[pose_bone.parent.name]
                parent_local_inverse = local_inverses[pose_bone.parent.name]
                basis_to_world_matrix = parent_world @ (parent_local_inverse @ local)
                
                # 3. now we can calculate the desired basis matrix
                des_basis_matrix = basis_to_world_matrix.inverted() @ desired_world_matrix
                
                # 4. now we can extract the quaternion from the des_basis_matrix
                # c.f. https://en.wikipedia.org/wiki/Rotation_matrix#Quaternion
                Q_xx = des_basis_matrix[0][0]
                Q_xy = des_basis_matrix[0][1]
                Q_xz = des_basis_matrix[0][2]
                Q_yx = des_basis_matrix[1][0]
                Q_yy = des_basis_matrix[1][1]
                Q_yz = des_basis_matrix[1][2]
                Q_zx = des_basis_matrix[2][0]
                Q_zy = des_basis_matrix[2][1]
                Q_zz = des_basis_matrix[2][2]
                # assume that the trace is not negative
                t = Q_xx + Q_yy + Q_zz
                r = (1+t)**0.5
                s = 1/(2*r)
                w = r/2
                x = (Q_xy - Q_yz)*s
                y = (Q_xz - Q_zx)*s
                z = (Q_yx - Q_xy)*s
                Q_new = Quaternion()
                Q_new.x, Q_new.y, Q_new.z, Q_new.w = x, y, z, w
                pose_bone.rotation_quaternion = Q_new
                world_matrices[bone_name] = pose_bone.matrix
                
            print(f"set {bone_name} rotation")
            bones_done[bone_name] = True

for bone in pose.bones:
    if not bones_done[bone.name]:
        update(bone.name)
