from math import pi
from typing import BinaryIO

import bpy
from mathutils import Vector, Quaternion, Matrix
from .rose_data import SkeletonData, BoneData


class Skeleton:
    def __init__(self):
        self.bones = []  # type: list
        self.dummies = []  # type: list

        self._armature_object = None  # type: bpy.types.Object
        self._edit_bones = None  # type: bpy.types.ArmatureEditBones
        self._bone_indices = {}  # type: dict

    def read(self):
        has_armature = self._read_armature()
        if not has_armature:
            return False
        self._read_bones()
        self._sort_dummies()

    def _read_armature(self):
        if bpy.context.active_object is not None:
            bpy.ops.object.mode_set(mode='OBJECT')
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                self._armature_object = obj
        if self._armature_object is None:
            print("No armature found to export.")
            return False
        bpy.context.view_layer.objects.active = self._armature_object
        bpy.ops.object.mode_set(mode='EDIT')
        self._edit_bones = self._armature_object.data.edit_bones
        return True

    def _read_bones(self):
        i = 0
        for j in range(len(self._edit_bones)):
            edit_bone = self._edit_bones[j]
            parent = self._bone_indices[edit_bone.parent] if j > 0 else 0
            rotation_parent = Quaternion()
            current = parent
            while j != 0:
                rotation_parent = self.bones[current].rotation @ rotation_parent
                if current == 0:
                    break
                current = self.bones[current].parent

            position = Vector(edit_bone.head - (edit_bone.parent.head if j > 0 else Vector.Fill(3)))
            position.rotate(rotation_parent.inverted())
            position *= 100

            pos, rotation, scale = Matrix(edit_bone.matrix).decompose()
            rotation = rotation_parent.inverted() @ rotation @ Quaternion((0, 0, 1), pi / 2)

            if "p_" in edit_bone.name or "Point" in edit_bone.name:
                self.dummies.append(BoneData(parent, edit_bone.name, position, rotation))
            elif edit_bone.name not in ['LegIK.L', 'LegIK.R', 'LegTarget.L', 'LegTarget.R', 'ArmIK.L', 'ArmIK.R',
                                        'ArmTarget.L', 'ArmTarget.R']:
                self.bones.append(BoneData(parent, edit_bone.name, position, rotation))
                self._bone_indices[edit_bone] = i
                i += 1
        bpy.ops.object.mode_set(mode='OBJECT')

    def _sort_dummies(self):
        dummies_sorted = []
        for i in range(len(self.dummies)):
            for dummy in self.dummies:
                if "0" + str(i) in dummy.name:
                    dummies_sorted.append(dummy)
        self.dummies = dummies_sorted


def save_zmd_skeleton(context, filepath: BinaryIO, format_code: str):
    skeleton = Skeleton()
    skeleton.read()
    skeleton_data = SkeletonData(int(format_code), skeleton.bones, skeleton.dummies)
    skeleton_data.save_data(filepath)
    print("Completed saving skeleton.")

    return {'FINISHED'}
