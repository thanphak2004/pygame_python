import pygame
import random
import sys
from pathlib import Path

# ------------- Config -------------
WIDTH, HEIGHT = 640, 480
CELL = 20
GRID_W, GRID_H = WIDTH // CELL, HEIGHT // CELL
FPS = 12  # base speed; increases slightly as you grow
FONT_NAME = "freesansbold.ttf"
HIGHSCORE_FILE = Path("highscore.txt")

# Colors
BLACK = (12, 12, 12)
GRAY = (40, 40, 40)
WHITE = (235, 235, 235)
GREEN = (80, 200, 120)
RED = (230, 70, 70)
YELLOW = (245, 205, 60)
BLUE = (85, 160, 255)

# ------------- Helpers -------------
def load_highscore():
    try:
        if HIGHSCORE_FILE.exists():
            return int(HIGHSCORE_FILE.read_text().strip())
    except Exception:
        pass
    return 0

def save_highscore(score):
    try:
        HIGHSCORE_FILE.write_text(str(score))
    except Exception:
        pass

def draw_text(surface, text, size, color, center):
    font = pygame.font.Font(FONT_NAME, size)
    surf = font.render(text, True, color)
    rect = surf.get_rect(center=center)
    surface.blit(surf, rect)

def new_food(snake):
    while True:
        pos = (random.randrange(GRID_W), random.randrange(GRID_H))
        if pos not in snake:
            return pos

def wrap(pos):
    x, y = pos
    return (x % GRID_W, y % GRID_H)

def add_tuple(a, b):
    return (a[0] + b[0], a[1] + b[1])

# ------------- Game -------------
class SnakeGame:
    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.state = "MENU"
        self.reset()

        self.highscore = load_highscore()

    def reset(self):
        cx, cy = GRID_W // 2, GRID_H // 2
        self.snake = [(cx, cy), (cx - 1, cy), (cx - 2, cy)]
        self.dir = (1, 0)
        self.next_dir = self.dir
        self.food = new_food(self.snake)
        self.score = 0
        self.paused = False
        self.just_moved = False  # prevents instant reverse in one tick

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit_game()
            if event.type == pygame.KEYDOWN:
                if self.state == "MENU":
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.state = "PLAY"
                        self.reset()
                    elif event.key == pygame.K_q:
                        self.quit_game()
                elif self.state == "PLAY":
                    if event.key in (pygame.K_p, pygame.K_PAUSE):
                        self.paused = not self.paused
                    if not self.paused and not self.just_moved:
                        if event.key in (pygame.K_UP, pygame.K_w):
                            if self.dir != (0, 1): self.next_dir = (0, -1)
                        elif event.key in (pygame.K_DOWN, pygame.K_s):
                            if self.dir != (0, -1): self.next_dir = (0, 1)
                        elif event.key in (pygame.K_LEFT, pygame.K_a):
                            if self.dir != (1, 0): self.next_dir = (-1, 0)
                        elif event.key in (pygame.K_RIGHT, pygame.K_d):
                            if self.dir != (-1, 0): self.next_dir = (1, 0)
                elif self.state == "GAME_OVER":
                    if event.key in (pygame.K_r, pygame.K_RETURN, pygame.K_SPACE):
                        self.state = "PLAY"
                        self.reset()
                    elif event.key == pygame.K_m:
                        self.state = "MENU"
                    elif event.key == pygame.K_q:
                        self.quit_game()

    def logic(self):
        if self.state != "PLAY" or self.paused:
            return

        # move snake
        self.dir = self.next_dir
        new_head = wrap(add_tuple(self.snake[0], self.dir))

        # collision with self -> game over
        if new_head in self.snake:
            self.state = "GAME_OVER"
            if self.score > self.highscore:
                self.highscore = self.score
                save_highscore(self.highscore)
            return

        self.snake.insert(0, new_head)
        self.just_moved = True

        # eat food
        if new_head == self.food:
            self.score += 1
            self.food = new_food(self.snake)
        else:
            self.snake.pop()

    def draw_grid(self):
        for x in range(0, WIDTH, CELL):
            pygame.draw.line(self.screen, GRAY, (x, 0), (x, HEIGHT), 1)
        for y in range(0, HEIGHT, CELL):
            pygame.draw.line(self.screen, GRAY, (0, y), (WIDTH, y), 1)

    def draw_snake(self):
        # gradient-ish body
        for i, (x, y) in enumerate(self.snake):
            rect = pygame.Rect(x * CELL, y * CELL, CELL, CELL)
            if i == 0:
                pygame.draw.rect(self.screen, YELLOW, rect)
                # eyes
                cx, cy = rect.center
                eye = 3
                dx, dy = self.dir
                ex1 = cx + (CELL//4) * (dx if dx != 0 else -1)
                ey1 = cy + (CELL//4) * (dy if dy != 0 else -1)
                ex2 = cx + (CELL//4) * (dx if dx != 0 else 1)
                ey2 = cy + (CELL//4) * (dy if dy != 0 else 1)
                pygame.draw.circle(self.screen, BLACK, (ex1, ey1), eye)
                pygame.draw.circle(self.screen, BLACK, (ex2, ey2), eye)
            else:
                shade = max(60, 200 - i * 6)
                pygame.draw.rect(self.screen, (shade, 220, 160), rect)

    def draw_food(self):
        x, y = self.food
        rect = pygame.Rect(x * CELL, y * CELL, CELL, CELL)
        pygame.draw.rect(self.screen, RED, rect)
        # small highlight
        pygame.draw.rect(self.screen, WHITE, rect.inflate(-CELL//2, -CELL//2), 1)

    def draw_hud(self):
        draw_text(self.screen, f"Score: {self.score}", 20, WHITE, (60, 16))
        draw_text(self.screen, f"Best: {self.highscore}", 20, BLUE, (WIDTH - 70, 16))

        if self.paused:
            draw_text(self.screen, "PAUSED", 28, YELLOW, (WIDTH // 2, 20))

    def draw_menu(self):
        self.screen.fill(BLACK)
        title_y = HEIGHT // 3
        draw_text(self.screen, "S N A K E", 56, GREEN, (WIDTH // 2, title_y))
        draw_text(self.screen, "Eat food, avoid your tail. Wraps at edges.", 20, WHITE, (WIDTH // 2, title_y + 50))
        draw_text(self.screen, "Press ENTER/SPACE to Start", 22, YELLOW, (WIDTH // 2, title_y + 110))
        draw_text(self.screen, "Controls: Arrow Keys / WASD • P to Pause", 18, WHITE, (WIDTH // 2, title_y + 150))
        draw_text(self.screen, "Q to Quit", 16, (180, 180, 180), (WIDTH // 2, title_y + 185))

    def draw_game_over(self):
        self.screen.fill(BLACK)
        draw_text(self.screen, "You Died!", 52, RED, (WIDTH // 2, HEIGHT // 3))
        draw_text(self.screen, f"Score: {self.score}", 26, WHITE, (WIDTH // 2, HEIGHT // 3 + 60))
        draw_text(self.screen, f"Best: {self.highscore}", 22, BLUE, (WIDTH // 2, HEIGHT // 3 + 95))
        draw_text(self.screen, "R / ENTER / SPACE: Retry", 20, YELLOW, (WIDTH // 2, HEIGHT // 3 + 150))
        draw_text(self.screen, "M: Main Menu   •   Q: Quit", 18, (190, 190, 190), (WIDTH // 2, HEIGHT // 3 + 185))

    def draw(self):
        if self.state == "MENU":
            self.draw_menu()
            return

        if self.state == "PLAY":
            self.screen.fill(BLACK)
            self.draw_grid()
            self.draw_snake()
            self.draw_food()
            self.draw_hud()
            return

        if self.state == "GAME_OVER":
            self.draw_game_over()
            return

    def quit_game(self):
        pygame.quit()
        sys.exit()

    def run(self):
        tick_accumulator = 0.0
        base_dt = 1.0 / FPS

        while True:
            self.handle_input()

            # Increase speed slightly as snake grows
            dynamic_fps = FPS + min(10, self.score // 3)
            dt = 1.0 / dynamic_fps

            tick_accumulator += self.clock.tick(60) / 1000.0

            # Update only on logical ticks for crisp movement
            while tick_accumulator >= dt:
                self.logic()
                self.just_moved = False
                tick_accumulator -= dt

            self.draw()
            pygame.display.flip()

def main():
    pygame.init()
    pygame.display.set_caption("Snake — Start Menu & Died Screen")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    game = SnakeGame(screen)
    game.run()

if __name__ == "__main__":
    main()
