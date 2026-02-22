"""Tests for MCP tool wrappers: validate bridge delegation."""

from __future__ import annotations

# Third-party
import pytest

# Internal
from fxhoudinimcp.tools.code import execute_python
from fxhoudinimcp.tools.materials import list_materials
from fxhoudinimcp.tools.nodes import create_node
from fxhoudinimcp.tools.scene import get_scene_info, new_scene
from fxhoudinimcp.tools.workflows import setup_pyro_sim


class TestSceneTools:
    @pytest.mark.asyncio
    async def test_get_scene_info(self, mock_ctx, mock_bridge):
        mock_bridge.execute.return_value = {"hip_file": "/tmp/test.hip"}
        result = await get_scene_info(mock_ctx)
        mock_bridge.execute.assert_called_once_with("scene.get_scene_info")
        assert result == {"hip_file": "/tmp/test.hip"}

    @pytest.mark.asyncio
    async def test_new_scene(self, mock_ctx, mock_bridge):
        mock_bridge.execute.return_value = {"created": True}
        result = await new_scene(mock_ctx, save_current=True)
        mock_bridge.execute.assert_called_once_with("scene.new_scene", {"save_current": True})


class TestNodeTools:
    @pytest.mark.asyncio
    async def test_create_node_required_params(self, mock_ctx, mock_bridge):
        mock_bridge.execute.return_value = {"path": "/obj/geo1/box1"}
        result = await create_node(mock_ctx, parent_path="/obj/geo1", node_type="box")
        mock_bridge.execute.assert_called_once_with(
            "nodes.create_node",
            {"parent_path": "/obj/geo1", "node_type": "box"},
        )

    @pytest.mark.asyncio
    async def test_create_node_all_params(self, mock_ctx, mock_bridge):
        await create_node(
            mock_ctx,
            parent_path="/obj",
            node_type="geo",
            name="my_geo",
            position=[0, 0],
        )
        mock_bridge.execute.assert_called_once_with(
            "nodes.create_node",
            {"parent_path": "/obj", "node_type": "geo", "name": "my_geo", "position": [0, 0]},
        )


class TestCodeTools:
    @pytest.mark.asyncio
    async def test_execute_python_code_only(self, mock_ctx, mock_bridge):
        await execute_python(mock_ctx, code="print('hi')")
        mock_bridge.execute.assert_called_once_with(
            "code.execute_python",
            {"code": "print('hi')"},
        )

    @pytest.mark.asyncio
    async def test_execute_python_with_return(self, mock_ctx, mock_bridge):
        await execute_python(mock_ctx, code="x = 1 + 1", return_expression="x")
        mock_bridge.execute.assert_called_once_with(
            "code.execute_python",
            {"code": "x = 1 + 1", "return_expression": "x"},
        )


class TestWorkflowTools:
    @pytest.mark.asyncio
    async def test_setup_pyro_defaults(self, mock_ctx, mock_bridge):
        await setup_pyro_sim(mock_ctx)
        mock_bridge.execute.assert_called_once_with(
            "workflow.setup_pyro_sim",
            {
                "source_geo": "/obj/geo1/sphere1",
                "container": "box",
                "res_scale": 1.0,
                "substeps": 1,
                "name": "pyro_sim",
            },
        )


class TestMaterialTools:
    @pytest.mark.asyncio
    async def test_list_materials_default(self, mock_ctx, mock_bridge):
        await list_materials(mock_ctx)
        mock_bridge.execute.assert_called_once_with(
            "materials.list_materials",
            {"root_path": "/mat"},
        )
