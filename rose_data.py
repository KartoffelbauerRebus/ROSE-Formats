import enum

from .utils import *
from typing import Union, BinaryIO
from os import PathLike
from mathutils import Vector, Quaternion

ik_names = ['LegIK.L',
            'LegIK.R',
            'LegTarget.L',
            'LegTarget.R',
            'ArmIK.L',
            'ArmIK.R',
            'ArmTarget.L',
            'ArmTarget.R']


class SkeletonData:
    def __init__(self, format_code: int = 0, bones: list = None, dummies: list = None):
        self.format_code = format_code  # type: int
        self.bones = bones if bones is not None else []  # type: list
        self.dummies = dummies if dummies is not None else []  # type: list

    def load_data(self, filepath: Union[str, bytes, PathLike]):
        with open(filepath, 'rb') as f:
            self._load_format_code(f)
            self._load_bones(f)
            self._load_dummies(f)
        print(f"Loading ZMD skeleton data from {filepath}. It has formatting type {self.format_code}.\n")
        self._print_data()

    def save_data(self, filepath: Union[str, bytes, PathLike]):
        with open(filepath, 'wb') as f:
            self._save_format_code(f)
            self._save_bones(f)
            self._save_dummies(f)
        print(f"Saving ZMD skeleton data to {filepath} with formatting type {self.format_code}.\n")
        self._print_data()

    def _load_format_code(self, f: BinaryIO):
        format_code = read_fstr(f, 7)
        if format_code == 'ZMD0003':
            self.format_code = 3
        elif format_code == 'ZMD0002':
            self.format_code = 2
        else:
            raise RoseParseError(f"Unrecognized ZMD format code: {format_code}")

    def _load_bones(self, f: BinaryIO):
        bone_count = read_i32(f)
        for i in range(bone_count):
            self.bones.append(BoneData())
            self.bones[i].load_data(f, False)

    def _load_dummies(self, f: BinaryIO):
        try:
            dummy_count = read_i32(f)
        except:
            print("No dummy bones found.")
            return
        for i in range(dummy_count):
            self.dummies.append(BoneData())
            self.dummies[i].load_data(f, True, self.format_code == 2)

    def _save_format_code(self, f: BinaryIO):
        format_code = 'ZMD000' + str(self.format_code)
        write_fstr(f, format_code, 7)

    def _save_bones(self, f: BinaryIO):
        write_i32(f, len(self.bones))
        for bone in self.bones:
            bone.save_data(f, False)

    def _save_dummies(self, f: BinaryIO):
        write_i32(f, len(self.dummies))
        for dummy in self.dummies:
            dummy.save_data(f, True, self.format_code == 2)

    def _print_data(self):
        self._print_bone_list('bone')
        if not self.dummies:
            return
        self._print_bone_list('dummy')

    def _print_bone_list(self, bone_type: str):
        bone_list = self.bones if bone_type == 'bone' else self.dummies

        print(f"Skeleton has {len(bone_list)} {bone_type} type bones:\n\n"
              f"Index\t\tName\t    Parent\tPosition\t\twxyz-Rotation\n"
              f"----------------------------------------------------------"
              f"----------------------------------------------------------")

        for i in range(len(bone_list)):
            bone = bone_list[i]
            parent = self.bones[bone.parent]
            print(
                f"{i:>2}:"
                f"\t{bone.name:>13}"
                f"\t{parent.name:>13}"
                f"\t({bone.position.x:2f}, {bone.position.y:2f}, {bone.position.z:2f})  "
                f"\t({bone.rotation.w:3f}, {bone.rotation.x:3f}, {bone.rotation.y:3f}, {bone.rotation.z:3f}).")
        print("")


class BoneData:
    """Holds ROSE bone data"""

    def __init__(self,
                 parent: int = 0,
                 name: str = '',
                 position: Vector = Vector.Fill(3),
                 rotation: Quaternion = Quaternion()):
        self.parent = parent  # type: int
        self.name = name  # type: str
        self.position = position  # type: Vector
        self.rotation = rotation  # type: Quaternion

    def load_data(self, f: BinaryIO, is_dummy: bool, format_v_2: bool = False):
        if is_dummy:
            self.name = read_str(f)
        self.parent = read_i32(f)
        if not is_dummy:
            self.name = read_str(f)  # nice consistent file format kekw

        self.position = read_vector3_f32(f) / 100
        if format_v_2:
            return
        self.rotation = read_vector4_f32(f, is_rotation=True)

    def save_data(self, f: BinaryIO, is_dummy: bool, format_v_2: bool = False):
        if is_dummy:
            write_str(f, self.name)
        write_i32(f, self.parent)
        if not is_dummy:
            write_str(f, self.name)
        write_vector3_f32(f, self.position)
        if not format_v_2:
            write_vector4_f32(f, self.rotation)


class AnimationData:
    def __init__(self, format_code: int = 0, fps: int = 0, frame_count: int = 0):
        self.format_code = format_code
        self.fps = fps
        self.frame_count = frame_count
        self.channels = []

    def load_data(self, filepath: Union[str, bytes, PathLike]):
        with open(filepath, 'rb') as f:
            self._load_settings(f)
            self._setup_channels(f)
            self._load_channel_data(f)

    def _load_settings(self, f):
        self.format_code = read_fstr(f, 8)
        self.fps = read_i32(f)
        self.frame_count = read_i32(f)

    def _setup_channels(self, f):
        self.channel_count = read_i32(f)
        for i in range(self.channel_count):
            tracktype = read_i32(f)
            track_id = read_i32(f)
            self.channels.append(ChannelData(tracktype, track_id))

    def _load_channel_data(self, f):
        for i in range(self.frame_count):
            for j in range(len(self.channels)):
                if self.channels[j].positions_enabled():
                    x = read_f32(f) / 100
                    y = read_f32(f) / 100
                    z = read_f32(f) / 100
                    self.channels[j].position.append(Vector((x, y, z)))
                elif self.channels[j].rotations_enabled():
                    w = read_f32(f)
                    x = read_f32(f)
                    y = read_f32(f)
                    z = read_f32(f)
                    self.channels[j].rotation.append(Quaternion((w, x, y, z)))
                if self.channels[j].normals_enabled():
                    x = read_f32(f)
                    y = read_f32(f)
                    z = read_f32(f)
                    self.channels[j].normal.append(Vector((x, y, z)))
                if self.channels[j].alpha_enabled():
                    alpha = read_f32(f)
                    self.channels[j].alpha.append(alpha)
                if self.channels[j].uv1_enabled():
                    x = read_f32(f)
                    y = read_f32(f)
                    self.channels[j].uv_1.append(Vector((x, y)))
                if self.channels[j].uv2_enabled():
                    x = read_f32(f)
                    y = read_f32(f)
                    self.channels[j].uv_2.append(Vector((x, y)))
                if self.channels[j].uv3_enabled():
                    x = read_f32(f)
                    y = read_f32(f)
                    self.channels[j].uv_3.append(Vector((x, y)))
                if self.channels[j].uv4_enabled():
                    x = read_f32(f)
                    y = read_f32(f)
                    self.channels[j].uv_4.append(Vector((x, y)))
                if self.channels[j].textureanim_enabled():
                    texture_anim = read_f32(f)
                    self.channels[j].texture_animation.append(alpha)
                if self.channels[j].scale_enabled():
                    scale = read_f32(f)
                    self.channels[j].scale.append(alpha)


class ChannelData:
    def __init__(self, tracktype, track_id):
        self.identifier = track_id
        self.type = tracktype
        self.position = []
        self.rotation = []
        self.normal = []
        self.alpha = []
        self.uv_1 = []
        self.uv_2 = []
        self.uv_3 = []
        self.uv_4 = []
        self.texture_animation = []
        self.scale = []

    def positions_enabled(self):
        return (TrackType.POSITION & self.type) != 0

    def rotations_enabled(self):
        return (TrackType.ROTATION & self.type) != 0

    def normals_enabled(self):
        return (TrackType.NORMAL & self.type) != 0

    def alpha_enabled(self):
        return (TrackType.ALPHA & self.type) != 0

    def uv1_enabled(self):
        return (TrackType.UV1 & self.type) != 0

    def uv2_enabled(self):
        return (TrackType.UV2 & self.type) != 0

    def uv3_enabled(self):
        return (TrackType.UV3 & self.type) != 0

    def uv4_enabled(self):
        return (TrackType.UV4 & self.type) != 0

    def textureanim_enabled(self):
        return (TrackType.TEXTUREANIM & self.type) != 0

    def scale_enabled(self):
        return (TrackType.SCALE & self.type) != 0


class TrackType(enum.IntEnum):
    POSITION = 1 << 1
    ROTATION = 1 << 2
    NORMAL = 1 << 3
    ALPHA = 1 << 4
    UV1 = 1 << 5
    UV2 = 1 << 6
    UV3 = 1 << 7
    UV4 = 1 << 8
    TEXTUREANIM = 1 << 9
    SCALE = 1 << 10
