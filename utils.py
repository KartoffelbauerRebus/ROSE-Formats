from os import PathLike
from typing import Union, BinaryIO

from mathutils import Vector, Quaternion, Color
import struct


class BoundingBox:
    def __init__(self):
        self.min = Vector.Fill(3)
        self.max = Vector.Fill(3)


class RoseParseError(Exception):
    ...


def read_vector3_f32(f):
    v = Vector.Fill(3)
    v.x = read_f32(f)
    v.y = read_f32(f)
    v.z = read_f32(f)
    return v


def read_vector4_i16(f):
    v = Vector.Fill(4)
    v.x = read_i16(f)
    v.y = read_i16(f)
    v.z = read_i16(f)
    v.w = read_i16(f)
    return v


def read_vector4_f32(f, is_rotation: bool = False):
    w = read_f32(f)
    x = read_f32(f)
    y = read_f32(f)
    z = read_f32(f)
    if is_rotation:
        return Quaternion((w, x, y, z))
    else:
        return Vector((w, x, y, z))


def read_vector2_f32(f):
    v = Vector.Fill(2)
    v.x = read_f32(f)
    v.y = read_f32(f)
    return v


def read_vector3_i16(f):
    v = Vector.Fill(3)
    v.x = read_i16(f)
    v.y = read_i16(f)
    v.z = read_i16(f)
    return v


def read_color(f):
    r = read_f32(f)
    g = read_f32(f)
    b = read_f32(f)
    a = read_f32(f)
    return Color((r, g, b)), a


def read_i16(f):
    return struct.unpack("<h", f.read(2))[0]


def read_f32(f):
    """Read float"""
    return struct.unpack(f"<f", f.read(4))[0]


def read_i32(f):
    """Read dword"""
    return struct.unpack(f"<i", f.read(4))[0]


def read_fstr(f, size):
    """ Read fixed-size string """
    return f.read(size).decode("EUC-KR")


def read_str(f):
    """ Read null-terminated string """
    bstring = bytes("", encoding="EUC-KR")
    while True:
        byte = f.read(1)
        if byte == b"\x00":
            break
        else:
            bstring += byte
    return bstring.decode("EUC-KR")


def write_vector3_f32(f: BinaryIO, data: Vector):
    write_f32(f, data.x)
    write_f32(f, data.y)
    write_f32(f, data.z)


def write_vector4_f32(f: BinaryIO, data: Union[Vector, Quaternion]):
    write_f32(f, data.w)
    write_f32(f, data.x)
    write_f32(f, data.y)
    write_f32(f, data.z)


def write_i32(f: BinaryIO, data: int):
    f.write(struct.pack("<i", data))


def write_f32(f: BinaryIO, data: float):
    f.write(struct.pack("<f", data))


def write_fstr(f: BinaryIO, data: str, size: int):
    byte_data = bytes(data, 'EUC-KR')
    f.write(struct.pack(f"<{size}s", byte_data))


def write_str(f: BinaryIO, data: str):
    string = bytes(data, "EUC-KR") + b'\x00'
    string_size = len(string)
    f.write(struct.pack(f"<{string_size}s", string))
