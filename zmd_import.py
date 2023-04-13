from math import pi
from os import PathLike
from typing import Union

import bpy
from mathutils import Vector, Quaternion
from .rose_data import SkeletonData


class Skeleton:
    def __init__(self, data: SkeletonData):
        self.armature_object = None  # type: bpy.types.Object
        self.edit_bones = None  # type: bpy.types.ArmatureEditBones

        self._data = data  # type: SkeletonData

    def load(self, add_leg_ik: bool, add_arm_ik: bool):
        self._load_root_bone()
        self._load_bones()
        self._load_dummies()
        if add_leg_ik:
            self._add_leg_ik()
        if add_arm_ik:
            self._add_arm_ik()
        print("Completed loading skeleton.")
        bpy.ops.object.mode_set(mode='OBJECT')

    def _load_root_bone(self):
        # add armature
        if bpy.context.active_object is not None:
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.armature_add(enter_editmode=True, align='WORLD')
        # set object attributes
        self.armature_object = bpy.context.active_object
        self.edit_bones = self.armature_object.data.edit_bones

        # set root location and rotation
        self.armature_object.rotation_quaternion = self._data.bones[0].rotation

        # setup root bone
        self.edit_bones[0].name = self._data.bones[0].name
        self.edit_bones[0].head = (0, 0, 0)
        self.edit_bones[0].tail = (1, 0, 0)
        self.edit_bones[0].transform(self._get_rotation(0, False))
        self.edit_bones[0].translate(self._get_translation(0, False))
        self.edit_bones[0].length = self._data.bones[1].position.length

    def _load_bones(self):
        for i in range(1, len(self._data.bones)):
            self._add_bone(i, is_dummy=False)

    def _load_dummies(self):
        dummies = self._data.dummies
        if not dummies:
            return
        for i in range(len(dummies)):
            self._add_bone(i, is_dummy=True)

    def _add_bone(self, index: int, is_dummy: bool):
        bone_list = self._data.dummies if is_dummy else self._data.bones
        edit_bone = self.edit_bones.new(bone_list[index].name)
        self._set_parent(index, is_dummy)

        edit_bone.head = (0, 0, 0)
        edit_bone.tail = (1, 0, 0)
        edit_bone.transform(self._get_rotation(index, is_dummy))
        edit_bone.translate(self._get_translation(index, is_dummy))

        if is_dummy:
            edit_bone.length = 0.1
        elif index + 1 == len(bone_list) or bone_list[index + 1].parent != index:
            if 'toe' in bone_list[index].name:
                edit_bone.length = 0.5 * edit_bone.parent.length
            elif 'hand' in bone_list[index].name:
                edit_bone.length = 0.75 * edit_bone.parent.length
            elif 'head' in bone_list[index].name:
                edit_bone.length = 3 * edit_bone.parent.length
            else:
                edit_bone.length = edit_bone.parent.length
        else:
            edit_bone.length = bone_list[index + 1].position.length

    def _set_parent(self, index: int, is_dummy: bool):
        """Set edit_bones' parent if available"""
        bone_list = self._data.dummies if is_dummy else self._data.bones
        edit_bone = self.edit_bones[index + (len(self._data.bones) if is_dummy else 0)]

        no_y_translation = abs(bone_list[index].position.y) < 1e-8
        no_z_translation = abs(bone_list[index].position.z) < 1e-8
        if not is_dummy and no_y_translation and no_z_translation:
            edit_bone.use_connect = True
        else:
            edit_bone.use_connect = False
        parent_index = bone_list[index].parent
        edit_bone.parent = self.edit_bones[parent_index]

    def _get_rotation(self, index: int, is_dummy: bool):
        bone_list = self._data.dummies if is_dummy else self._data.bones
        return (self._get_parent_rotation(index, is_dummy) @ bone_list[index].rotation).to_matrix()

    def _get_translation(self, index: int, is_dummy: bool):
        bone_list = self._data.dummies if is_dummy else self._data.bones
        parent_bone = self.edit_bones[bone_list[index].parent]

        position = bone_list[index].position
        position.rotate(self._get_parent_rotation(index, is_dummy))
        return Vector(parent_bone.head) + position

    def _get_parent_rotation(self, index: int, is_dummy: bool):
        bones = self._data.bones
        rotation = Quaternion()
        current = self._data.dummies[index].parent if is_dummy else bones[index].parent
        while index != 0:
            rotation = bones[current].rotation @ rotation
            if current == 0:
                break
            current = bones[current].parent
        return rotation

    def _add_leg_ik(self):
        if not self._has_bones('calf', 'foot'):
            print("Not all necessary bones found to add leg IK.")
            return
        for side in ['L', 'R']:
            leg_ik = IKCreator(self, side, is_leg=True)
            leg_ik.add()

    def _add_arm_ik(self):
        if not self._has_bones('forearm', 'hand'):
            print("Not all necessary bones found to add arm IK.")
            return
        for side in ['L', 'R']:
            arm_ik = IKCreator(self, side, is_leg=False)
            arm_ik.add()

    def _has_bones(self, bone_name_1: str, bone_name_2: str):
        count = 0
        for edit_bone in self.edit_bones:
            if bone_name_1 in edit_bone.name or bone_name_2 in edit_bone.name:
                count += 1
        return count == 4


class IKCreator:
    def __init__(self, skeleton: Skeleton, side: str, is_leg: bool):
        self._skeleton = skeleton  # type: Skeleton
        self._side = side  # type: str
        self._is_leg = is_leg  # type: bool

    def add(self):
        self._add_bones()
        self._add_constraints()

    def _add_bones(self):
        for edit_bone in self._skeleton.edit_bones:
            if f"{self._side.lower()}{'foot' if self._is_leg else 'hand'}" in edit_bone.name:
                rot_bone = edit_bone
            elif f"{self._side.lower()}{'calf' if self._is_leg else 'forearm'}" in edit_bone.name:
                ik_bone = edit_bone

        ik_head, ik_tail, target_head, target_tail = self._get_bone_positions(rot_bone, ik_bone)
        self._add_bone(f'{self._area_name()}IK',
                       ik_head,
                       ik_tail)
        self._add_bone(f'{self._area_name()}Target',
                       target_head,
                       target_tail)

    def _area_name(self) -> str:
        return 'Leg' if self._is_leg else 'Arm'

    def _get_bone_positions(self, rot_bone: bpy.types.EditBone, ik_bone: bpy.types.EditBone) \
            -> tuple[bpy.types.EditBone, bpy.types.EditBone, bpy.types.EditBone, bpy.types.EditBone]:
        ik_head = rot_bone.head
        ik_tail = rot_bone.head - Vector((0, rot_bone.length, 0)) if self._is_leg \
            else rot_bone.head + Vector((0, 0, (1 if self._side == 'L' else -1) * rot_bone.length))
        target_head = ik_bone.head + (1 if self._is_leg else -1) * Vector((0, 2 * ik_bone.length, 0))
        target_tail = ik_bone.head + (1 if self._is_leg else -1) * Vector((0, 3 * ik_bone.length, 0))
        return ik_head, ik_tail, target_head, target_tail

    def _add_bone(self, name: str, head_location: Union[Vector, tuple], tail_location: Union[Vector, tuple]):
        bone = self._skeleton.edit_bones.new(f'{name}.{self._side}')
        bone.head = head_location
        bone.tail = tail_location
        bone.use_deform = False

    def _add_constraints(self):
        bpy.ops.object.mode_set(mode='POSE')
        for pose_bone in self._skeleton.armature_object.pose.bones:
            if f"{self._side.lower()}{'foot' if self._is_leg else 'hand'}" in pose_bone.name:
                rot_bone = pose_bone
            elif f"{self._side.lower()}{'calf' if self._is_leg else 'forearm'}" in pose_bone.name:
                ik_bone = pose_bone
        self._add_copy_rotation(rot_bone)
        self._add_inverse_kinematics(ik_bone)
        bpy.ops.object.mode_set(mode='EDIT')

    def _add_copy_rotation(self, rot_bone: bpy.types.PoseBone):
        constraint = rot_bone.constraints.new('COPY_ROTATION')
        constraint.target = self._skeleton.armature_object
        constraint.subtarget = f'{self._area_name()}IK.{self._side}'
        constraint.target_space = 'LOCAL_WITH_PARENT'
        constraint.owner_space = 'LOCAL_WITH_PARENT'
        if self._is_leg:
            constraint.invert_z = True

    def _add_inverse_kinematics(self, ik_bone: bpy.types.PoseBone):
        constraint = ik_bone.constraints.new('IK')
        constraint.target = self._skeleton.armature_object
        constraint.subtarget = f'{self._area_name()}IK.{self._side}'
        constraint.pole_target = self._skeleton.armature_object
        constraint.pole_subtarget = f'{self._area_name()}Target.{self._side}'
        constraint.pole_angle = pi
        constraint.chain_count = 2


def load_zmd_skeleton(context,
                      filepath: Union[str, bytes, PathLike],
                      load_animations: bool,
                      add_leg_ik: bool,
                      add_arm_ik: bool):
    skeleton_data = SkeletonData()
    skeleton_data.load_data(filepath)

    skeleton = Skeleton(skeleton_data)
    skeleton.load(add_leg_ik, add_arm_ik)


    # if load_animations:
    #     load_zmo_animations(filepath, skeleton_data.bones, skeleton.armature_object)

    return {'FINISHED'}
