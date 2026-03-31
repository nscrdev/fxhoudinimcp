You are developing a Houdini Digital Asset (HDA).

Goal: {asset_description}
Context: {context}

## Workflow

1. Create a subnet node to hold the internal logic.
2. Build the internal network with the required functionality.
3. Promote internal parameters to the subnet level using create_spare_parameters (plural, batch tool) with a folder_name to group them in a tab.
4. Test the network thoroughly using get_geometry_info or get_stage_info.
5. Use create_hda to convert the subnet into an HDA.
6. Use get_hda_info to verify the definition.
7. Use get_hda_sections to inspect the asset contents.
8. Use set_hda_section_content to add help documentation.

## Tips

- Use get_parameter_schema on existing nodes to understand parameter types
- Use list_node_types to verify the HDA type name is unique
- Test with different inputs before finalizing the HDA
- Use update_hda to save changes after modifications
- Build internal logic with SOP node chains (Box, Grid, Scatter, Boolean, PolyExtrude, Copy to Points, Blast, Transform, etc.) — NOT VEX wrangles. A network of visible nodes is far more user-friendly and debuggable inside an HDA than opaque wrangles. Plan the node chain before building. Wrangles are a last resort for logic no built-in SOP can express.
- Use For-Each loops (block_begin/block_end) for per-piece processing rather than VEX loops
- Promote parameters with create_spare_parameters (plural, batch) and use folder_name to organize tabs
- Create a HDA help card via set_hda_section_content with "DialogScript" or use the Help section
- Keep the internal network clean: use Null SOPs as labeled waypoints (e.g., "OUTPUT", "INPUT_GEO")
- NEVER hardcode file paths or magic numbers — expose them as parameters

{network_housekeeping}
