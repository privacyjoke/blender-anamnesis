from mathutils import Quaternion, Matrix
from math import copysign, radians
import json
import bpy

fix_toes = False
fix_head = False

model_tag = bpy.context.object.name
ob = bpy.context.object

folder_path = "C:\\users\\conor\\Documents\\Blender\\anamnesis"
in_path = f"{folder_path}\\m_stand.pose"
map_path = f"{folder_path}\\map.json"

    

with open(in_path, 'r') as f:
    j = json.load(f)    

with open(map_path, 'r') as f:
    name_map = json.load(f)

model_tag = bpy.context.object.name

pose = bpy.data.objects[model_tag].pose

bones_done = {k: False for k in pose.bones.keys()}
world_matrices = {k: None for k in pose.bones.keys()}
local_inverses = {k: None for k in pose.bones.keys()}

def update(bone_name):
    if bone_name in name_map.values():
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
                rot_string = j['Bones'][bone_name]['Rotation']
                pos_string = j['Bones'][bone_name]['Position']
                sca_string = j['Bones'][bone_name]['Scale']
                print(f"{bone_name}: rot_string={rot_string}, pos_string={pos_string}")
                rx, ry, rz, rw = [float(x) for x in rot_string.split(',')]
                px, py, pz = [float(x) for x in pos_string.split(',')]
                sx, sy, sz = [float(x) for x in sca_string.split(',')]
                Q.x, Q.y, Q.z, Q.w = rx, ry, rz, rw
                R = Q.to_matrix()
                for i in range(3):
                    for k in range(3):
                        desired_world_matrix[i][k] = R[i][k]
                desired_world_matrix[0][3] = px
                desired_world_matrix[1][3] = py
                desired_world_matrix[2][3] = pz
                # scale columns 
                for i in range(3):
                    desired_world_matrix[i][0] *= sx 
                    desired_world_matrix[i][1] *= sy
                    desired_world_matrix[i][2] *= sz 
                    
                
                # 2. calculate the net transformation matrix (which goes from basis to world)
                parent_world = world_matrices[pose_bone.parent.name]
                parent_local_inverse = local_inverses[pose_bone.parent.name]
                basis_to_world_matrix = parent_world @ (parent_local_inverse @ local)
                
                # 3. now we can calculate the desired basis matrix
                des_basis_matrix = basis_to_world_matrix.inverted() @ desired_world_matrix
                
                # 4. now we can extract the quaternion from the des_basis_matrix
                # c.f. https://en.wikipedia.org/wiki/Rotation_matrix#Quaternion
                Q_xx = des_basis_matrix[0][0] / sx
                Q_xy = des_basis_matrix[0][1] / sy
                Q_xz = des_basis_matrix[0][2] / sz
                Q_yx = des_basis_matrix[1][0] / sx
                Q_yy = des_basis_matrix[1][1] / sy
                Q_yz = des_basis_matrix[1][2] / sz
                Q_zx = des_basis_matrix[2][0] / sx
                Q_zy = des_basis_matrix[2][1] / sy
                Q_zz = des_basis_matrix[2][2] / sz
                
                tr = Q_xx + Q_yy + Q_zz
                if tr >= 0:
                    r = (1+tr)**0.5
                    w = r/2
                    x = copysign(1, Q_zy - Q_yz) * abs(0.5 * (1 + Q_xx - Q_yy - Q_zz)**0.5)
                    y = copysign(1, Q_xz - Q_zx) * abs(0.5 * (1 - Q_xx + Q_yy - Q_zz)**0.5)
                    z = copysign(1, Q_yx - Q_xy) * abs(0.5 * (1 - Q_xx - Q_yy + Q_zz)**0.5)
                else:
                    max_diag = max(Q_xx, Q_yy, Q_zz)
                    if Q_xx == max_diag:
                        r = (1 + Q_xx - Q_yy - Q_zz)**0.5
                        s = 1/(2*r)
                        w = (Q_zy - Q_yz)*s
                        x = r/2
                        y = (Q_xy + Q_yx)*s
                        z = (Q_zx + Q_xz)*s
                    elif Q_yy == max_diag:
                        r = (1 + Q_yy - Q_zz - Q_xx)**0.5
                        s = 1/(2*r)
                        w = (Q_xz - Q_zx)*s
                        x = (Q_xy + Q_yx)*s
                        y = r/2
                        z = (Q_zy + Q_yz)*s
                    else:
                        r = (1 + Q_zz - Q_xx - Q_yy)**0.5
                        s = 1/(2*r)
                        w = (Q_yx - Q_xy)*s
                        x = (Q_xz + Q_zx)*s
                        y = (Q_yz + Q_zy)*s
                        z = r/2
                    
                Q_new = Quaternion()
                Q_new.x, Q_new.y, Q_new.z, Q_new.w = x, y, z, w
                pose_bone.rotation_quaternion = Q_new
                pose_bone.scale.x = sx
                pose_bone.scale.y = sy
                pose_bone.scale.z = sz
                world_matrices[bone_name] = pose_bone.matrix
                
            print(f"set {bone_name} rotation")
            bones_done[bone_name] = True
    else:
        print(f"skipping {bone_name}")

for bone in pose.bones:
    if not bones_done[bone.name]:
        update(bone.name)

def fix_bone(bone):
    bone.rotation_mode = 'XYZ'
    R = Matrix.Rotation(radians(180), 3, 'Y')
    bone.rotation_euler = (R @ bone.rotation_euler.to_matrix()).to_euler()
    bone.rotation_mode = 'QUATERNION'
def deep_fix(bone):
    if bone.parent is not None:
        fix_bone(bone.parent)
    fix_bone(bone)

# now fix race-specific stuff
if fix_toes:
    fix_bone(pose.bones['ToesLeft'])
    fix_bone(pose.bones['ToesRight'])
    
if fix_head:
    deep_fix(pose.bones['Head'])