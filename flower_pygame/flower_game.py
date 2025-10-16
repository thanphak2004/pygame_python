import pygame
import random
import sys
from pathlib import Path

# ---------------- Config ----------------
WIDTH, HEIGHT = 640, 720
FPS = 60

BASKET_W, BASKET_H = 110, 26
FLOWER_MIN_SIZE, FLOWER_MAX_SIZE = 12, 24
FLOWER_MIN_SPEED, FLOWER_MAX_SPEED = 2.5, 7.0
SPAWN_EVERY_SECONDS = 0.45  # base spawn rate (spawns get slightly faster over time)

START_TIME = 60  # seconds
START_LIVES = 3

FONT_NAME = "freesansbold.ttf"
HIGHSCORE_FILE = Path("flower_highscore.txt")

# Colors
BG = (20, 22, 28)
WHITE = (240, 240, 240)
GRAY = (80, 86, 96)
YELLOW = (250, 208, 60)
RED = (235, 84, 84)
GREEN = (90, 210, 140)
BLUE = (90, 160, 250)
PINK = (255, 170, 220)
PURPLE = (185, 150, 255)

# ---------------- Helpers ----------------
def draw_text(surf, text, size, color, center):
    font = pygame.font.Font(FONT_NAME, size)
    ren = font.render(text, True, color)
    rect = ren.get_rect(center=center)
    surf.blit(ren, rect)

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

# ---------------- Entities ----------------
class Flower:
    def __init__(self):
        self.size = random.randint(FLOWER_MIN_SIZE, FLOWER_MAX_SIZE)
        self.x = random.uniform(self.size, WIDTH - self.size)
        self.y = -self.size - random.uniform(0, 200)
        self.speed = random.uniform(FLOWER_MIN_SPEED, FLOWER_MAX_SPEED)
        self.wind = random.uniform(-0.6, 0.6)  # slight horizontal drift
        self.color = random.choice([YELLOW, PINK, PURPLE, BLUE, GREEN])

    def update(self, dt):
        self.y += self.speed * (dt * 60)         # normalize to 60 FPS feel
        self.x += self.wind * (dt * 60) * 0.3
        # bounce a little at edges so flowers don't disappear fully
        if self.x < self.size:
            self.x, self.wind = self.size, abs(self.wind)
        elif self.x > WIDTH - self.size:
            self.x, self.wind = WIDTH - self.size, -abs(self.wind)

    def draw(self, surf):
        # Simple flower: a circle with petals
        r = self.size // 2
        cx, cy = int(self.x), int(self.y)
        petal_r = int(r * 0.9)
        offsets = [(r, 0), (-r, 0), (0, r), (0, -r)]
        for ox, oy in offsets:
            pygame.draw.circle(surf, self.color, (cx + ox, cy + oy), petal_r)
        pygame.draw.circle(surf, WHITE, (cx, cy), r)

    def rect(self):
        r = self.size
        return pygame.Rect(int(self.x - r), int(self.y - r), r * 2, r * 2)

    def off_screen(self):
        return self.y - self.size > HEIGHT + 40

class Basket:
    def __init__(self):
        self.w, self.h = BASKET_W, BASKET_H
        self.x = WIDTH // 2 - self.w // 2
        self.y = HEIGHT - 80
        self.speed = 500  # keyboard move speed

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def update_keyboard(self, dt, keys):
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.x -= self.speed * dt
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.x += self.speed * dt
        self.x = max(0, min(WIDTH - self.w, self.x))

    def update_mouse(self):
        mx, _ = pygame.mouse.get_pos()
        self.x = max(0, min(WIDTH - self.w, mx - self.w // 2))

    def draw(self, surf):
        # Basket body
        pygame.draw.rect(surf, (210, 170, 100), self.rect, border_radius=10)
        # Rim
        pygame.draw.rect(surf, (170, 130, 60), self.rect.inflate(0, -14).move(0, -6), border_radius=8)
        # Handle
        hx, hy = self.rect.centerx, self.rect.y
        pygame.draw.arc(surf, (170, 130, 60), pygame.Rect(hx - 60, hy - 40, 120, 60), 3.14, 0, 3)

# ---------------- Game ----------------
class Game:
    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.state = "MENU"
        self.highscore = load_highscore()
        self.reset()

    def reset(self):
        self.basket = Basket()
        self.flowers = []
        self.score = 0
        self.time_left = float(START_TIME)
        self.lives = START_LIVES
        self.spawn_timer = 0.0
        self.elapsed = 0.0
        self.paused = False
        # Make early game a bit easier
        for _ in range(5):
            self.flowers.append(Flower())

    # ---------- Input ----------
    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if self.state == "MENU":
                    if e.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.state = "PLAY"; self.reset()
                    elif e.key == pygame.K_q:
                        pygame.quit(); sys.exit()
                elif self.state == "PLAY":
                    if e.key in (pygame.K_p, pygame.K_PAUSE):
                        self.paused = not self.paused
                elif self.state == "GAME_OVER":
                    if e.key in (pygame.K_r, pygame.K_RETURN, pygame.K_SPACE):
                        self.state = "PLAY"; self.reset()
                    elif e.key == pygame.K_m:
                        self.state = "MENU"
                    elif e.key == pygame.K_q:
                        pygame.quit(); sys.exit()

    # ---------- Update ----------
    def update(self, dt):
        if self.state != "PLAY" or self.paused:
            return

        self.elapsed += dt
        self.time_left = max(0.0, self.time_left - dt)

        # spawn rate ramps up very slightly over time
        spawn_every = max(0.20, SPAWN_EVERY_SECONDS - min(0.20, self.elapsed * 0.01))
        self.spawn_timer += dt
        while self.spawn_timer >= spawn_every:
            self.flowers.append(Flower())
            self.spawn_timer -= spawn_every

        # player control: mouse or keyboard simultaneously
        keys = pygame.key.get_pressed()
        if pygame.mouse.get_focused():
            self.basket.update_mouse()
        self.basket.update_keyboard(dt, keys)

        # update flowers and check catches/misses
        for f in list(self.flowers):
            f.update(dt)
            if f.rect().colliderect(self.basket.rect):
                self.flowers.remove(f)
                self.score += 1
                # tiny time reward to keep streaks alive
                self.time_left = min(999, self.time_left + 0.25)
            elif f.off_screen():
                self.flowers.remove(f)
                self.lives -= 1

        # check game over
        if self.time_left <= 0 or self.lives <= 0:
            self.state = "GAME_OVER"
            if self.score > self.highscore:
                self.highscore = self.score
                save_highscore(self.highscore)

    # ---------- Draw ----------
    def draw_hud(self):
        # Top bar
        pygame.draw.rect(self.screen, (28, 30, 36), (0, 0, WIDTH, 48))
        draw_text(self.screen, f"Score: {self.score}", 22, WHITE, (80, 24))
        draw_text(self.screen, f"Time: {int(self.time_left)}", 22, YELLOW, (WIDTH // 2, 24))
        draw_text(self.screen, f"Lives: {self.lives}", 22, RED, (WIDTH - 80, 24))
        if self.paused:
            draw_text(self.screen, "PAUSED", 26, BLUE, (WIDTH // 2, 70))

    def draw_menu(self):
        self.screen.fill(BG)
        draw_text(self.screen, "F L O W E R   P I C K E R", 44, PINK, (WIDTH // 2, HEIGHT // 3))
        draw_text(self.screen, "Catch the falling flowers with your basket.", 22, WHITE, (WIDTH // 2, HEIGHT // 3 + 60))
        draw_text(self.screen, "Arrow Keys / A D to move • Mouse also works", 20, GRAY, (WIDTH // 2, HEIGHT // 3 + 95))
        draw_text(self.screen, "P to Pause", 18, GRAY, (WIDTH // 2, HEIGHT // 3 + 125))
        draw_text(self.screen, "Press ENTER / SPACE to Start", 22, YELLOW, (WIDTH // 2, HEIGHT // 3 + 170))
        draw_text(self.screen, f"Best: {self.highscore}", 20, BLUE, (WIDTH // 2, HEIGHT // 3 + 205))
        # decorative idle flowers
        for i in range(7):
            x = 70 + i * 80
            y = HEIGHT - 140 + int(10 * (i % 2))
            pygame.draw.circle(self.screen, (70, 150, 90), (x, y + 35), 35)
            pygame.draw.rect(self.screen, (60, 120, 70), (x - 30, y + 35, 60, 12), border_radius=6)

    def draw_game(self):
        self.screen.fill(BG)
        # ground
        pygame.draw.rect(self.screen, (30, 60, 40), (0, HEIGHT - 50, WIDTH, 50))
        # flowers
        for f in self.flowers:
            f.draw(self.screen)
        # basket
        self.basket.draw(self.screen)
        # hud
        self.draw_hud()

    def draw_game_over(self):
        self.screen.fill(BG)
        draw_text(self.screen, "You Died!", 52, RED, (WIDTH // 2, HEIGHT // 3))
        draw_text(self.screen, f"Score: {self.score}", 28, WHITE, (WIDTH // 2, HEIGHT // 3 + 60))
        draw_text(self.screen, f"Best:  {self.highscore}", 22, BLUE, (WIDTH // 2, HEIGHT // 3 + 95))
        draw_text(self.screen, "R / ENTER / SPACE: Retry", 20, YELLOW, (WIDTH // 2, HEIGHT // 3 + 150))
        draw_text(self.screen, "M: Main Menu   •   Q: Quit", 18, GRAY, (WIDTH // 2, HEIGHT // 3 + 185))

    # ---------- Main Loop ----------
    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)

            if self.state == "MENU":
                self.draw_menu()
            elif self.state == "PLAY":
                self.draw_game()
            elif self.state == "GAME_OVER":
                self.draw_game_over()

            pygame.display.flip()

# ---------------- Entrypoint ----------------
def main():
    pygame.init()
    pygame.display.set_caption("Flower Picker — Start Menu & Died Screen")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    Game(screen).run()

if __name__ == "__main__":
    main()
