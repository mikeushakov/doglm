# Product Requirements Document: Gem Maze

## 1. Overview

Gem Maze is a minimal single-level 2D game. The player navigates a maze and must collect five gems, after which the exit gate opens. The game is won when the player reaches the open exit.

## 2. Technical Requirements

- Deliver the game as **one single HTML file** with all CSS and JavaScript inline.
- Use only **vanilla JavaScript** and the **HTML5 Canvas API**. No external libraries, no frameworks, no CDN imports, no build step.
- No external assets of any kind: no image files, no audio files, no fonts. Represent all characters and objects with simple colored shapes (rectangles, circles) or emoji drawn on the canvas.
- The game must run by opening the HTML file directly in a modern desktop browser (double-click, no local server required).
- Target canvas size: 800 x 600 pixels, centered on the page.

## 3. Game World

- A top-down view of a single-screen maze rendered on the canvas.
- The maze is built from solid walls the player cannot walk through, forming corridors with a moderate amount of branching. The maze layout is fixed (hard-coded), not randomly generated.
- The maze contains **five gems**, placed in fixed positions in different parts of the maze. A gem is visually distinct (for example, a colored diamond shape or emoji) and disappears once collected.
- One **exit gate** is placed on the maze border. The gate is visibly closed while gems remain and visibly open once all five gems are collected.
- A dog wanders the maze corridors, uninvolved with the gems or the gate. Its movement may be implemented as simple slow wandering within the corridors, staying in walkable areas; picking a random direction and reversing or turning when it meets a wall is sufficient, no pathfinding is needed.

## 4. Player

- The player character is a single figure (shape or emoji) controlled with the keyboard. Both the **arrow keys and the WASD keys** must control movement.
- Movement is smooth, in four or eight directions, at a constant speed.
- The player cannot leave the canvas boundaries or pass through maze walls.
- The player starts at a fixed position near the bottom of the maze, away from the exit gate.

## 5. Core Mechanic: Collecting Gems and Exiting

- A gem is collected the moment the player character touches it (collision-based pickup). No key needs to be pressed.
- On collection: the gem disappears, the gems counter updates, and a brief visual confirmation is shown (for example, a short sparkle or "+1" popup at the gem's position).
- When the fifth gem is collected, the exit gate visibly opens (for example, its bars disappear or its color changes).
- The player wins by walking into the open exit gate. Touching the gate while it is closed does nothing.

## 6. HUD and Game Flow

- A HUD in a corner of the canvas shows gems collected, for example: "Gems: 3 / 5".
- A short instruction line is visible at the start (for example: "Collect all gems to open the exit. Move: WASD/arrows").
- When the player reaches the open exit, the game ends immediately with a victory screen: a message such as "You escaped the maze! You win!" and a prompt to press R to restart.
- Pressing R after victory resets the game to its initial state.
- There is no way to lose; the game has no timer, enemies, or fail state.

## 7. Scope Constraints

- Exactly one level. No menus beyond the instruction line and the victory screen.
- No sound.
- No save system, no score system beyond the gem counter.
- Total code should remain small and readable.

## 8. Acceptance Criteria

- The HTML file opens and runs without any console errors.
- The player character moves correctly with both arrow keys and WASD.
- All five gems are reachable through the maze corridors and every gem can be collected.
- Collecting all five gems opens the exit gate, reaching the open gate triggers the victory screen, and pressing R restarts the game to its initial state.

## 9. Output Format

Return only the complete HTML code of the game, with no Markdown fences and no explanation before or after the code.
