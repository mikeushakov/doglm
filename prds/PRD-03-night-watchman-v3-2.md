# Product Requirements Document: Night Watchman

## 1. Overview

Night Watchman is a minimal single-level 2D game. The player is a watchman patrolling a building at night and must check four doors. The game is won when all four doors have been checked.

## 2. Technical Requirements

- Deliver the game as **one single HTML file** with all CSS and JavaScript inline.
- Use only **vanilla JavaScript** and the **HTML5 Canvas API**. No external libraries, no frameworks, no CDN imports, no build step.
- No external assets of any kind: no image files, no audio files, no fonts. Represent all characters and objects with simple colored shapes (rectangles, circles) or emoji drawn on the canvas.
- The game must run by opening the HTML file directly in a modern desktop browser (double-click, no local server required).
- Target canvas size: 800 x 600 pixels, centered on the page.

## 3. Game World

- A top-down view of the interior of a single building floor rendered on the canvas, drawn in dark night-time colors.
- The floor contains **four doors**, placed in fixed positions along the walls or corridors of the building.
- Each unchecked door has a visible indicator (for example, a small red lamp or marker next to it). When a door is checked, its indicator turns green and stays green.
- The remaining space is walkable floor. A few simple interior walls may divide the floor into rooms or corridors; walls are solid obstacles the player cannot walk through. A few simple decorative elements (crates, a desk, a plant) may be added for readability, drawn as simple shapes or emoji.
- A dog keeps the watchman company on his rounds. The dog has no role in checking doors. Its movement may be implemented as simple trailing toward the player, staying in walkable areas, without pathfinding; if a wall blocks its way, it may simply wait until the player comes back into reach. It should remain visible on the canvas.

## 4. Player

- The player character is a single figure (shape or emoji) controlled with the keyboard. Both the **arrow keys and the WASD keys** must control movement.
- Movement is smooth, in four or eight directions, at a constant speed.
- The player cannot leave the canvas boundaries.
- The player starts near the building entrance at the bottom of the map.

## 5. Core Mechanic: Checking Doors

- To check a door, the player simply stands next to it (within a small check radius) for **two continuous seconds**. No key needs to be pressed.
- While the player is standing within the radius of an unchecked door, a small progress indicator fills up over the two seconds (for example, a progress bar or a filling circle near the door). Stepping away before it fills resets the progress for that door.
- When the progress completes: the door's indicator turns green, the doors-remaining counter decreases by one, and a brief visual confirmation is shown (for example, a short "Checked!" text popup near the door).
- Each door needs to be checked exactly once; a checked door stays green.

## 6. Secondary Mechanics
- Add 2-3 game mechanics that players would enjoy.

## 7. HUD and Game Flow

- A HUD in a corner of the canvas shows doors remaining, for example: "Doors: 2 / 4".
- A short instruction line is visible at the start (for example: "Check all doors. Move: WASD/arrows. Stand near a door to check it").
- When the fourth door is checked, the game ends immediately with a victory screen: a message such as "All doors checked! Shift complete!" and a prompt to press R to restart.
- Pressing R after victory resets the game to its initial state.
- There is no way to lose; the game has no timer, enemies, or fail state.

## 8. Scope Constraints

- Exactly one level. No menus beyond the instruction line and the victory screen.
- No sound.
- No save system, no score system beyond the door counter.
- Total code should remain small and readable.

## 9. Acceptance Criteria

- The HTML file opens and runs without any console errors.
- The player character moves correctly with both arrow keys and WASD.
- All four doors are reachable and every door can be checked by standing near it for two seconds.
- Checking all four doors triggers the victory screen, and pressing R restarts the game to its initial state.

## 10. Output Format

Return only the complete HTML code of the game, with no Markdown fences and no explanation before or after the code.
