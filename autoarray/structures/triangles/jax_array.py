from typing import Tuple

from autoarray import Grid2D
from jax import numpy as np
from jax.tree_util import register_pytree_node_class
from jax import jit


@register_pytree_node_class
class ArrayTriangles:
    def __init__(
        self,
        indices: np.ndarray,
        vertices: np.ndarray,
    ):
        """
        Represents a set of triangles in efficient NumPy arrays.

        Parameters
        ----------
        indices
            The indices of the vertices of the triangles. This is a 2D array where each row is a triangle
            with the three indices of the vertices.
        vertices
            The vertices of the triangles.
        """
        self.indices = indices
        self.vertices = vertices

    @property
    @jit
    def triangles(self):
        return self.vertices[self.indices]

    @property
    @jit
    def means(self):
        return np.mean(self.triangles, axis=1)

    @jit
    def containing_indices(self, point: Tuple[float, float]) -> np.ndarray:
        """
        Find the triangles that contain a given point.

        Parameters
        ----------
        point
            The point to find the containing triangles for.

        Returns
        -------
        The triangles that contain the point.
        """
        x, y = point

        triangles = self.triangles

        y1, x1 = triangles[:, 0, 1], triangles[:, 0, 0]
        y2, x2 = triangles[:, 1, 1], triangles[:, 1, 0]
        y3, x3 = triangles[:, 2, 1], triangles[:, 2, 0]

        denominator = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)

        a = ((y2 - y3) * (x - x3) + (x3 - x2) * (y - y3)) / denominator
        b = ((y3 - y1) * (x - x3) + (x1 - x3) * (y - y3)) / denominator
        c = 1 - a - b

        inside = (0 <= a) & (a <= 1) & (0 <= b) & (b <= 1) & (0 <= c) & (c <= 1)

        return np.where(inside, size=5, fill_value=-1)[0]

    @jit
    def for_indexes(self, indexes: np.ndarray) -> "ArrayTriangles":
        """
        Create a new ArrayTriangles containing indices and vertices corresponding to the given indexes
        but without duplicate vertices.

        Parameters
        ----------
        indexes
            The indexes of the triangles to include in the new ArrayTriangles.

        Returns
        -------
        The new ArrayTriangles instance.
        """
        selected_indices = self.indices[indexes]

        flat_indices = selected_indices.flatten()
        unique_vertices, inverse_indices = np.unique(
            self.vertices[flat_indices],
            axis=0,
            return_inverse=True,
        )

        new_indices = inverse_indices.reshape(selected_indices.shape)

        return ArrayTriangles(indices=new_indices, vertices=unique_vertices)

    @jit
    def up_sample(self) -> "ArrayTriangles":
        """
        Up-sample the triangles by adding a new vertex at the midpoint of each edge.

        This means each triangle becomes four smaller triangles.
        """
        triangles = self.triangles

        m01 = (triangles[:, 0] + triangles[:, 1]) / 2
        m12 = (triangles[:, 1] + triangles[:, 2]) / 2
        m20 = (triangles[:, 2] + triangles[:, 0]) / 2

        new_triangles = np.concatenate(
            [
                np.stack([triangles[:, 0], m01, m20], axis=1),
                np.stack([triangles[:, 1], m12, m01], axis=1),
                np.stack([triangles[:, 2], m20, m12], axis=1),
                np.stack([m01, m12, m20], axis=1),
            ],
            axis=0,
        )

        unique_vertices, inverse_indices = np.unique(
            new_triangles.reshape(-1, 2), axis=0, return_inverse=True
        )
        new_indices = inverse_indices.reshape(-1, 3)

        return ArrayTriangles(
            indices=new_indices,
            vertices=unique_vertices,
        )

    @jit
    def neighborhood(self) -> "ArrayTriangles":
        """
        Create a new set of triangles that are the neighborhood of the current triangles.

        Includes the current triangles and the triangles that share an edge with the current triangles.
        """
        triangles = self.triangles

        new_v0 = triangles[:, 1] + triangles[:, 2] - triangles[:, 0]
        new_v1 = triangles[:, 0] + triangles[:, 2] - triangles[:, 1]
        new_v2 = triangles[:, 0] + triangles[:, 1] - triangles[:, 2]

        new_triangles = np.concatenate(
            [
                np.stack([new_v0, triangles[:, 1], triangles[:, 2]], axis=1),
                np.stack([triangles[:, 0], new_v1, triangles[:, 2]], axis=1),
                np.stack([triangles[:, 0], triangles[:, 1], new_v2], axis=1),
                triangles,
            ],
            axis=0,
        )
        unique_vertices, inverse_indices = np.unique(
            new_triangles.reshape(-1, 2), axis=0, return_inverse=True
        )
        new_indices = inverse_indices.reshape(-1, 3)

        new_indices_sorted = np.sort(new_indices, axis=1)

        unique_triangles_indices, unique_index_positions = np.unique(
            new_indices_sorted, axis=0, return_index=True
        )

        return ArrayTriangles(
            indices=unique_triangles_indices,
            vertices=unique_vertices,
        )

    @jit
    def with_vertices(self, vertices: np.ndarray) -> "ArrayTriangles":
        """
        Create a new set of triangles with the vertices replaced.

        Parameters
        ----------
        vertices
            The new vertices to use.

        Returns
        -------
        The new set of triangles with the new vertices.
        """
        return ArrayTriangles(
            indices=self.indices,
            vertices=vertices,
        )

    @classmethod
    @jit
    def for_grid(cls, grid: Grid2D) -> "ArrayTriangles":
        """
        Create a grid of equilateral triangles from a regular grid.

        Parameters
        ----------
        grid
            The regular grid to convert to a grid of triangles.

        Returns
        -------
        The grid of triangles.
        """

        scale = grid.pixel_scale

        HEIGHT_FACTOR = 3**0.5 / 2

        y = grid[:, 0]
        x = grid[:, 1]

        y_min = y.min()
        y_max = y.max()
        x_min = x.min()
        x_max = x.max()

        height = scale * HEIGHT_FACTOR

        vertices = []
        indices = []
        vertex_dict = {}

        def add_vertex(v):
            if v not in vertex_dict:
                vertex_dict[v] = len(vertices)
                vertices.append(v)
            return vertex_dict[v]

        rows = []
        for row_y in np.arange(y_min, y_max + height, height):
            row = []
            offset = (len(rows) % 2) * scale / 2
            for col_x in np.arange(x_min - offset, x_max + scale, scale):
                row.append((row_y, col_x))
            rows.append(row)

        for i in range(len(rows) - 1):
            row = rows[i]
            next_row = rows[i + 1]
            for j in range(len(row)):
                if i % 2 == 0 and j < len(next_row) - 1:
                    t1 = [
                        add_vertex(row[j]),
                        add_vertex(next_row[j]),
                        add_vertex(next_row[j + 1]),
                    ]
                    if j < len(row) - 1:
                        t2 = [
                            add_vertex(row[j]),
                            add_vertex(row[j + 1]),
                            add_vertex(next_row[j + 1]),
                        ]
                        indices.append(t2)
                elif i % 2 == 1 and j < len(next_row) - 1:
                    t1 = [
                        add_vertex(row[j]),
                        add_vertex(next_row[j]),
                        add_vertex(row[j + 1]),
                    ]
                    indices.append(t1)
                    if j < len(next_row) - 1:
                        t2 = [
                            add_vertex(next_row[j]),
                            add_vertex(next_row[j + 1]),
                            add_vertex(row[j + 1]),
                        ]
                        indices.append(t2)
                else:
                    continue
                indices.append(t1)

        vertices = np.array(vertices)
        indices = np.array(indices)

        return ArrayTriangles(
            indices=indices,
            vertices=vertices,
        )

    def __iter__(self):
        return iter(self.triangles)

    def tree_flatten(self):
        """
        Flatten this model as a PyTree.
        """
        return (self.indices, self.vertices), ()

    @classmethod
    def tree_unflatten(cls, aux_data, children):
        """
        Unflatten a PyTree into a model.
        """
        return cls(
            indices=children[0],
            vertices=children[1],
        )
