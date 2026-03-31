You are debugging a Houdini scene.

Problem: {problem_description}

## Systematic debug workflow

1. get_scene_info — Understand the overall scene state.
2. find_error_nodes — Find all nodes with errors or warnings.
3. For each error node, use get_node_info to get the full error message.
4. Check the node's inputs are connected: get_node_info shows connection state.
5. Check parameter values: get_parameter_schema and get_parameter.
6. If geometry issues: get_geometry_info on the problematic node and its inputs.
7. If USD issues: get_stage_info and list_usd_prims.
8. If simulation issues: get_simulation_info and get_dop_object.
9. Try setting bypass flag on suspected nodes: set_node_flags.
10. Check expressions: get_expression on parameters with broken references.

## Common issues

- **Missing inputs:** connect_nodes or check file paths
- **Wrong parameter values:** compare with get_parameter_schema defaults
- **Cooking errors:** check upstream nodes first (data flows top to bottom)
- **Memory issues:** get_sim_memory_usage, get_geometry_info for polygon counts
- **VEX errors:** use validate_vex to check wrangle compilation; ch()/chi() return 0 silently on bad paths
- **Simulation exploding:** reduce timestep/substeps, check collision geometry, use get_dop_object to inspect
- **Empty geometry output:** check display flag placement, verify group names, check for deleted/blasted geometry upstream
- **Material not showing:** verify material path, check assignmaterial prim path, ensure viewport renderer is set to Karma CPU or Storm
- **USD composition issues:** use get_usd_layers and get_usd_composition to inspect the layer stack
- **Node type not found:** call list_node_types to verify the node type name exists in the current context

{network_housekeeping}
