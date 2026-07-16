# Product Requirements Document: Mail Courier

## 1. Overview

Mail Courier is a minimal single-level 2D game. The player is a courier who must deliver five letters to five marked houses in a small village. The game is won when all five letters are delivered.

## 2. Technical Requirements

- Deliver the game as **one single HTML file** with all CSS and JavaScript inline.
- Use only **vanilla JavaScript** and the **HTML5 Canvas API**. No external libraries, no frameworks, no CDN imports, no build step.
- No external assets of any kind: no image files, no audio files, no fonts. Represent all characters and objects with simple colored shapes (rectangles, circles) or emoji drawn on the canvas.
- The game must run by opening the HTML file directly in a modern desktop browser (double-click, no local server required).
- Target canvas size: 800 x 600 pixels, centered on the page.

## 3. Game World

- A top-down view of a small village rendered on the canvas.
- The village contains **five houses**, placed in fixed positions spread around the map.
- Houses that still expect a letter are visually marked (for example, with an envelope emoji or a colored marker above them). The marker disappears once the letter is delivered.
- The remaining space is open ground the player can walk on. A few simple decorative elements (trees, bushes, a path) may be added for readability, drawn as simple shapes or emoji.
- The player cannot walk through houses; houses are solid obstacles.
- A dog follows the player around the village at a short distance. The dog has no role in mail delivery. Its movement may be implemented as simple trailing toward the player, without collision handling or pathfinding; it may pass through obstacles and should remain visible on the canvas.

## 4. Player

- The player character is a single figure (shape or emoji) controlled with the keyboard. Both the **arrow keys and the WASD keys** must control movement.
- Movement is smooth, in four or eight directions, at a constant speed.
- The player cannot leave the canvas boundaries.
- The player starts near the bottom center of the map, carrying five letters.

## 5. Core Mechanic: Delivering Letters

- To deliver a letter, the player walks up to a marked house and presses the **E key** while standing close to it (within a small delivery radius).
- On successful delivery: the house's marker disappears, the letters-remaining counter decreases by one, and a brief visual confirmation is shown (for example, a short "Delivered!" text popup near the house).
- Each house accepts exactly one letter; a house that has already received its letter cannot be delivered to again.

## 6. Secondary Mechanics
- Add 2-3 game mechanics that players of this genre would commonly expect.

## 7. HUD and Game Flow

- A HUD in a corner of the canvas shows letters remaining, for example: "Letters: 3 / 5".
- A short instruction line is visible at the start (for example: "Deliver all letters. Move: WASD/arrows. Deliver: E").
- When the fifth letter is delivered, the game ends immediately with a victory screen: a message such as "All mail delivered! You win!" and a prompt to press R to restart.
- Pressing R after victory resets the game to its initial state.
- There is no way to lose; the game has no timer, enemies, or fail state.

## 8. Scope Constraints

- Exactly one level. No menus beyond the instruction line and the victory screen.
- No sound.
- No save system, no score system beyond the letter counter.
- Total code should remain small and readable.

## 9. Acceptance Criteria

- The HTML file opens and runs without any console errors.
- The player character moves correctly with both arrow keys and WASD.
- All five houses are reachable and every letter can be delivered.
- Delivering all five letters triggers the victory screen, and pressing R restarts the game to its initial state.

## 10. Output Format

Return only the complete HTML code of the game, with no Markdown fences and no explanation before or after the code.
