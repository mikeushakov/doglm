# Product Requirements Document: Firefly Meadow

## 1. Overview

Firefly Meadow is a minimal single-level 2D game. The player walks around a meadow at dusk and must catch eight drifting fireflies. The game is won when all eight fireflies are caught.

## 2. Technical Requirements

- Deliver the game as **one single HTML file** with all CSS and JavaScript inline.
- Use only **vanilla JavaScript** and the **HTML5 Canvas API**. No external libraries, no frameworks, no CDN imports, no build step.
- No external assets of any kind: no image files, no audio files, no fonts. Represent all characters and objects with simple colored shapes (rectangles, circles) or emoji drawn on the canvas.
- The game must run by opening the HTML file directly in a modern desktop browser (double-click, no local server required).
- Target canvas size: 800 x 600 pixels, centered on the page.

## 3. Game World

- A top-down view of an open meadow at dusk rendered on the canvas, drawn in muted evening colors.
- The meadow contains **eight fireflies**, each drawn as a small glowing dot. Each firefly drifts slowly and continuously in a smooth, gently changing direction (for example, a slow random walk), staying within the canvas.
- The meadow is open ground with no obstacles. A few simple decorative elements (tufts of grass, a few flowers, a pond in one corner) may be added for readability, drawn as simple shapes or emoji.
- A dog is somewhere in the meadow. Its movement may be implemented as simple slow wandering, without collision handling or pathfinding; it should remain visible on the canvas.

## 4. Player

- The player character is a single figure (shape or emoji) controlled with the keyboard. Both the **arrow keys and the WASD keys** must control movement.
- Movement is smooth, in four or eight directions, at a constant speed.
- The player cannot leave the canvas boundaries.
- The player starts near the bottom center of the meadow.

## 5. Core Mechanic: Catching Fireflies

- A firefly is caught the moment the player character touches it (collision-based catch). No key needs to be pressed.
- On catch: the firefly disappears, the fireflies counter updates, and a brief visual confirmation is shown (for example, a short sparkle or "+1" popup at the catch position).
- Fireflies drift but do not flee from the player; catching them requires only walking into them.
- Each firefly can be caught exactly once.

## 6. HUD and Game Flow

- A HUD in a corner of the canvas shows fireflies caught, for example: "Fireflies: 5 / 8".
- A short instruction line is visible at the start (for example: "Catch all fireflies. Move: WASD/arrows").
- When the eighth firefly is caught, the game ends immediately with a victory screen: a message such as "All fireflies caught! You win!" and a prompt to press R to restart.
- Pressing R after victory resets the game to its initial state.
- There is no way to lose; the game has no timer, enemies, or fail state.

## 7. Scope Constraints

- Exactly one level. No menus beyond the instruction line and the victory screen.
- No sound.
- No save system, no score system beyond the firefly counter.
- Total code should remain small and readable.
- Beyond the requirements above, you may add game mechanics that players of this genre would commonly expect.

## 8. Acceptance Criteria

- The HTML file opens and runs without any console errors.
- The player character moves correctly with both arrow keys and WASD.
- Every firefly can be caught by walking into it, and fireflies remain within the canvas while drifting.
- Catching all eight fireflies triggers the victory screen, and pressing R restarts the game to its initial state.

## 9. Output Format

Return only the complete HTML code of the game, with no Markdown fences and no explanation before or after the code.
