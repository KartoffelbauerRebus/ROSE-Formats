import enum

import bmesh
import bpy

from .rose_data import ik_names
from .utils import *


class VertexFormat(enum.IntEnum):
    POSITION = 1 << 1
    NORMAL = 1 << 2
    COLOR = 1 << 3
    BONEWEIGHT = 1 << 4
    BONEINDEX = 1 << 5
    TANGENT = 1 << 6
    UV1 = 1 << 7
    UV2 = 1 << 8
    UV3 = 1 << 9
    UV4 = 1 << 10


class Vertex:
    def __init__(self):
        self.position = Vector.Fill(3)
        self.normal = Vector.Fill(3)
        self.color = Color()
        self.bone_weights = Vector.Fill(4)
        self.bone_indices = Vector.Fill(4)
        self.tangent = Vector.Fill(3)
        self.uv_layers = [None, None, None, None]


class MeshImportData:
    def __init__(self):
        self.identifier = ""
        self.format = -1

        self.bounding_box = BoundingBox()
        self.bones = []
        self.vertices = []
        self.indices = []
        self.materials = []
        self.strips = []

        self.pool = 0

    def positions_enabled(self):
        return (VertexFormat.POSITION & self.format) != 0

    def normals_enabled(self):
        return (VertexFormat.NORMAL & self.format) != 0

    def colors_enabled(self):
        return (VertexFormat.COLOR & self.format) != 0

    def bones_enabled(self):
        return ((VertexFormat.BONEWEIGHT & self.format) != 0) and (
                (VertexFormat.BONEINDEX & self.format) != 0
        )

    def tangents_enabled(self):
        return (VertexFormat.TANGENT & self.format) != 0

    def uv1_enabled(self):
        return (VertexFormat.UV1 & self.format) != 0

    def uv2_enabled(self):
        return (VertexFormat.UV2 & self.format) != 0

    def uv3_enabled(self):
        return (VertexFormat.UV3 & self.format) != 0

    def uv4_enabled(self):
        return (VertexFormat.UV4 & self.format) != 0

    def vertex_positions(self):
        positions = []
        for vertex in self.vertices:
            positions.append((vertex.position.x, vertex.position.y, vertex.position.z))
        return positions

    def edges(self):
        edges = []
        for face in self.indices:
            edges.append((int(face.x), int(face.y)))
            edges.append((int(face.y), int(face.z)))
            edges.append((int(face.z), int(face.y)))
        return edges

    def faces(self):
        faces = []
        for face in self.indices:
            faces.append((int(face.x), int(face.y), int(face.z)))
        return faces

    def load(self, filepath):
        with open(filepath, "rb") as f:
            self.identifier = read_str(f)

            version = None
            if self.identifier == "ZMS0007":
                version = 7
            elif self.identifier == "ZMS0008":
                version = 8

            if not version:
                raise RoseParseError(f"Unrecognized zms identifier {self.identifier}")

            self.format = read_i32(f)
            self.bounding_box.min = read_vector3_f32(f)
            self.bounding_box.max = read_vector3_f32(f)

            bone_count = read_i16(f)
            for _ in range(bone_count):
                self.bones.append(read_i16(f))

            vert_count = read_i16(f)
            for _ in range(vert_count):
                self.vertices.append(Vertex())

            if self.positions_enabled():
                for i in range(vert_count):
                    self.vertices[i].position = read_vector3_f32(f)

            if self.normals_enabled():
                for i in range(vert_count):
                    self.vertices[i].normal = read_vector3_f32(f)

            if self.colors_enabled():
                for i in range(vert_count):
                    self.vertices[i].color = read_color(f)

            if self.bones_enabled():
                for i in range(vert_count):
                    self.vertices[i].bone_weights = read_vector4_f32(f)
                    self.vertices[i].bone_indices = read_vector4_i16(f)
            if self.tangents_enabled():
                for i in range(vert_count):
                    self.vertices[i].tangent = read_vector3_f32(f)

            if self.uv1_enabled():
                for i in range(vert_count):
                    self.vertices[i].uv_layers[0] = read_vector2_f32(f)

            if self.uv2_enabled():
                for i in range(vert_count):
                    self.vertices[i].uv_layers[1] = read_vector2_f32(f)

            if self.uv3_enabled():
                for i in range(vert_count):
                    self.vertices[i].uv_layers[2] = read_vector2_f32(f)

            if self.uv4_enabled():
                for i in range(vert_count):
                    self.vertices[i].uv_layers[3] = read_vector2_f32(f)

            index_count = read_i16(f)
            for _ in range(index_count):
                self.indices.append(read_vector3_i16(f))

            material_count = read_i16(f)
            for _ in range(material_count):
                self.materials.append(read_i16(f))

            strip_count = read_i16(f)
            for _ in range(strip_count):
                self.strips.append(read_i16(f))

            if version >= 8:
                try:
                    self.pool = read_i16(f)
                except:
                    print("pool data missing")


def load_zms_mesh(context, filepath, load_texture):
    if bpy.context.active_object is not None:
        bpy.ops.object.mode_set(mode='OBJECT')
    print(f"Building mesh from {filepath}:")
    mesh_data = MeshImportData()
    mesh_data.load(filepath)
    for i in range(len(mesh_data.vertices)):
        vertex = mesh_data.vertices[i]
        print(f"Vertex {i}: \t{vertex.position}\t{vertex.bone_indices}\t{vertex.bone_weights}")
    mesh = bpy.data.meshes.new(name="New Object Mesh")
    mesh.from_pydata(mesh_data.vertex_positions(), mesh_data.edges(), mesh_data.faces())
    mesh.update()
    mesh_obj = bpy.data.objects.new('new_object', mesh)
    bpy.context.collection.objects.link(mesh_obj)
    bpy.context.view_layer.objects.active = mesh_obj
    for i in range(4):
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(mesh)
        uv_layer = bm.loops.layers.uv.new(f"UVMap_{i}")
        for f in bm.faces:
            for l in f.loops:
                if mesh_data.vertices[l.vert.index].uv_layers[i] is None:
                    break
                l_uv = l[uv_layer]
                l_uv.uv = (
                    mesh_data.vertices[l.vert.index].uv_layers[i].x,
                    1 - mesh_data.vertices[l.vert.index].uv_layers[i].y)
        bm.free()
        bmesh.update_edit_mesh(mesh)
        bpy.ops.object.mode_set(mode='OBJECT')

    if load_texture:
        box_material_obj = bpy.data.materials.new(name="Material")
        box_material_obj.use_nodes = True
        bsdf = box_material_obj.node_tree.nodes["Principled BSDF"]
        tex_image = box_material_obj.node_tree.nodes.new('ShaderNodeTexImage')
        tex_image.image = bpy.data.images.load(filepath[:-3] + 'dds')
        box_material_obj.node_tree.links.new(bsdf.inputs['Base Color'], tex_image.outputs['Color'])
        mesh_obj.data.materials.append(box_material_obj)

    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            arm_obj = obj
            break

    mesh_obj.select_set(True)
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.parent_set(type='ARMATURE_NAME')
    vertex_groups = []
    for vertex_group in mesh_obj.vertex_groups:
        if "p_" in vertex_group.name \
                or "Point" in vertex_group.name \
                or vertex_group.name in ik_names:
            continue
        vertex_groups.append(vertex_group)
    for i in range(len(vertex_groups)):
        print(f"{i}: {vertex_groups[i].name}")
    for i in range(len(mesh_data.vertices)):
        vertex = mesh_data.vertices[i]
        for j in range(4):
            bone_index = int(vertex.bone_indices[j])
            bone_weight = vertex.bone_weights[j]
            if bone_index == 0 and bone_weight < 1e-10:
                continue

            vertex_groups[mesh_data.bones[bone_index]].add([i], bone_weight, 'REPLACE')

    return {'FINISHED'}
