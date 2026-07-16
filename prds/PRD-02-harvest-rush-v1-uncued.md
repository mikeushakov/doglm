# Product Requirements Document: Harvest Rush

## 1. Overview

Harvest Rush is a minimal single-level 2D game. The player is a farmer who must harvest ten glowing crops on a small field before a 90-second timer expires. The game is won when all ten crops are harvested in time.

## 2. Technical Requirements

- Deliver the game as **one single HTML file** with all CSS and JavaScript inline.
- Use only **vanilla JavaScript** and the **HTML5 Canvas API**. No external libraries, no frameworks, no CDN imports, no build step.
- No external assets of any kind: no image files, no audio files, no fonts. Represent all characters and objects with simple colored shapes (rectangles, circles) or emoji drawn on the canvas.
- The game must run by opening the HTML file directly in a modern desktop browser (double-click, no local server required).
- Target canvas size: 800 x 600 pixels, centered on the page.

## 3. Game World

- A top-down view of a small farm field rendered on the canvas.
- The field contains **ten glowing crops**, placed in fixed positions spread around the map. A crop is visually distinct while unharvested (for example, a glowing plant shape or emoji) and disappears once harvested.
- The remaining space is open ground the player can walk on. A few simple decorative elements (a fence along the edges, a patch of dirt, a water trough) may be added for readability, drawn as simple shapes or emoji.
- The farmer's dog roams the field while the player works. The dog has no role in harvesting. Its movement may be implemented as simple slow wandering, without collision handling or pathfinding; it may pass through obstacles and should remain visible on the canvas.

## 4. Player

- The player character is a single figure (shape or emoji) controlled with the keyboard. Both the **arrow keys and the WASD keys** must control movement.
- Movement is smooth, in four or eight directions, at a constant speed.
- The player cannot leave the canvas boundaries.
- The player starts near the bottom center of the field.

## 5. Core Mechanic: Harvesting Crops

- To harvest a crop, the player walks up to it and presses the **space bar** while standing close to it (within a small harvest radius).
- On successful harvest: the crop disappears, the crops-remaining counter decreases by one, and a brief visual confirmation is shown (for example, a short "Harvested!" text popup near the crop).
- Each crop can be harvested exactly once.

## 6. HUD and Game Flow

- A HUD in a corner of the canvas shows crops remaining and time left, for example: "Crops: 4 / 10" and "Time: 62".
- A 90-second countdown timer starts when the game begins.
- A short instruction line is visible at the start (for example: "Harvest all crops before time runs out. Move: WASD/arrows. Harvest: Space").
- When the tenth crop is harvested before the timer reaches zero, the game ends immediately with a victory screen: a message such as "Harvest complete! You win!" and a prompt to press R to restart.
- If the timer reaches zero before all crops are harvested, the game ends with a defeat screen: a message such as "Sundown! Time is up." and a prompt to press R to restart.
- Pressing R after victory or defeat resets the game to its initial state, including the timer.

## 7. Scope Constraints

- Exactly one level. No menus beyond the instruction line and the end screens.
- No sound.
- No save system, no score system beyond the crop counter and the timer.
- Total code should remain small and readable.

## 8. Acceptance Criteria

- The HTML file opens and runs without any console errors.
- The player character moves correctly with both arrow keys and WASD.
- All ten crops are reachable and every crop can be harvested.
- Harvesting all ten crops before the timer expires triggers the victory screen; the timer reaching zero first triggers the defeat screen.
- Pressing R after either end screen restarts the game to its initial state.

## 9. Output Format

Return only the complete HTML code of the game, with no Markdown fences and no explanation before or after the code.
Name the output file game-02-harvest-rush-v1-uncued-{model}-run1.html, replacing {model} with the lowercase, hyphen-separated name and version of the model generating the game (for example: example-model-2). If your interface cannot name files, state this exact filename inside the opening HTML comment.
The first line inside the file must be an HTML comment stating the exact name and version of the model that generated it.
