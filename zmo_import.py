from math import pi
from os.path import basename

import bpy
from mathutils import Vector, Quaternion, Matrix

from .rose_data import AnimationData, ik_names


class Animation:
    def __init__(self, filepath, data):
        self._armature_object = None
        self.name = basename(filepath)[:-4]
        self._data = data
        self._bone_indices = {}
        self._edit_bone_rotations = []
        self._root_translation = Vector.Fill(3)
        self._pose_bones = []

    def load(self):
        has_armature = self.read_counter_rotations()
        if not has_armature:
            return
        self.read_bones()
        self.settings()
        self.insert_keyframes()

    def read_counter_rotations(self):
        if bpy.context.active_object is not None:
            bpy.ops.object.mode_set(mode='OBJECT')
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                self._armature_object = obj
        if self._armature_object is None:
            print("No armature found.")
            return False
        bpy.context.view_layer.objects.active = self._armature_object
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self._armature_object.data.edit_bones
        self._root_translation = edit_bones[0].head

        i = 0
        for j in range(len(edit_bones)):
            edit_bone = edit_bones[j]
            if 'p_' in edit_bone.name or 'Point' in edit_bone.name or edit_bone.name in ik_names:
                continue
            self._bone_indices[edit_bone.name] = i
            parent = edit_bone.parent if j > 0 else edit_bone
            rotation_parent = Quaternion()
            current = self._bone_indices[parent.name]
            while j > 0:
                rotation_parent = self._edit_bone_rotations[current] @ rotation_parent
                if current == 0:
                    break
                parent = parent.parent
                current = self._bone_indices[parent.name]

            pos, rotation, scale = Matrix(edit_bone.matrix).decompose()
            rotation = rotation # rotation_parent.inverted() @
            self._edit_bone_rotations.append(rotation)
            i += 1

        return True

    def read_bones(self):
        bpy.ops.object.mode_set(mode='POSE')

        for pose_bone in self._armature_object.pose.bones:
            if 'p_' not in pose_bone.name and 'Point' not in pose_bone.name and pose_bone.name not in ik_names:
                self._pose_bones.append(pose_bone)

    def settings(self):
        bpy.context.scene.frame_end = self._data.frame_count
        bpy.context.scene.render.fps = self._data.fps

    def insert_keyframes(self):
        for i in range(self._data.frame_count):
            for j in range(self._data.channel_count):
                pose_bone = self._pose_bones[self._data.channels[j].identifier]
                if self._data.channels[j].position:
                    pose_bone.location = (self._armature_object.rotation_quaternion @ self._data.channels[j].position[i]) - self._root_translation
                    pose_bone.keyframe_insert(data_path="location", frame=i + 1)
                if self._data.channels[j].rotation:
                    pose_bone.rotation_quaternion = self._data.channels[j].rotation[i]# @ self._edit_bone_rotations[j-1].inverted()
                    pose_bone.keyframe_insert(data_path="rotation_quaternion", frame=i+1)


def load_zmo_animation(context, filepath):
    animation_data = AnimationData()
    animation_data.load_data(filepath)

    animation = Animation(filepath, animation_data)
    animation.load()

    return {'FINISHED'}
