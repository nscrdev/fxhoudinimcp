## Network housekeeping (ALWAYS follow these)

- Call log_status at the start of every major step (creating geometry, wiring the chain, setting up materials, etc.) so the user can see what you are doing in Houdini's status bar without inspecting tool call logs. Keep messages short: "Creating source geometry...", "Wiring SOP chain...", "Done — display flag set on output node."
- Call set_current_network on the parent network you are building in so the user can see your work in the network editor. Do this BEFORE you start creating nodes, and again whenever you move to a different network level.
- Call layout_children frequently — after every batch of 3-5 new nodes, not just at the end. A tidy graph lets the user follow along in real time.
