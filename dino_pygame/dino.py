import pygame
import random
import sys
from pathlib import Path

# -------------------- Config --------------------
WIDTH, HEIGHT = 900, 300
FPS = 60

GROUND_Y = HEIGHT - 50
GRAVITY = 2400          # px/s^2
JUMP_VEL = -900         # px/s
DUCK_H = 32
RUN_H = 46

BASE_SPEED = 320        # px/s at start
SPEED_PER_100M = 30     # +px/s for each 100 m traveled

CACTUS_MIN_GAP = 250
CACTUS_MAX_GAP = 420
PTERO_MIN_GAP = 380
PTERO_MAX_GAP = 640
PTERO_MIN_ALT = 30
PTERO_MAX_ALT = 75

CLOUD_MIN_GAP = 180
CLOUD_MAX_GAP = 360

FONT_NAME = "freesansbold.ttf"
HIGHSCORE_FILE = Path("trex_highscore_m.txt")

COL_BG = (247, 247, 247)
COL_TEXT = (60, 60, 60)
COL_GROUND = (120, 120, 120)
COL_DINO = (60, 60, 60)
COL_DINO_EYE = (247, 247, 247)
COL_OBST = (40, 40, 40)
COL_PTERO = (40, 40, 40)
COL_CLOUD = (220, 220, 220)

# -------------------- Utils --------------------
def draw_text(surf, text, size, color, center):
    font = pygame.font.Font(FONT_NAME, size)
    ren = font.render(text, True, color)
    rect = ren.get_rect(center=center)
    surf.blit(ren, rect)

def load_highscore():
    try:
        if HIGHSCORE_FILE.exists():
            return float(HIGHSCORE_FILE.read_text().strip())
    except Exception:
        pass
    return 0.0

def save_highscore(score):
    try:
        HIGHSCORE_FILE.write_text(str(int(score)))
    except Exception:
        pass

# -------------------- Entities --------------------
class Ground:
    def __init__(self):
        self.x = 0
        self.pattern_w = 48

    def update(self, dt, speed):
        self.x -= speed * dt
        if self.x <= -self.pattern_w:
            self.x += self.pattern_w

    def draw(self, surf):
        pygame.draw.line(surf, COL_GROUND, (0, GROUND_Y), (WIDTH, GROUND_Y), 2)
        # tiny pebbles pattern
        px = int(self.x)
        for i in range(-1, WIDTH // self.pattern_w + 2):
            gx = i * self.pattern_w + px
            pygame.draw.circle(surf, COL_GROUND, (gx + 12, GROUND_Y + 6), 2)
            pygame.draw.circle(surf, COL_GROUND, (gx + 30, GROUND_Y + 10), 2)

class Cloud:
    def __init__(self, x):
        self.x = x
        self.y = random.randint(30, 110)
        self.speed = random.uniform(20, 45)

    def update(self, dt, world_speed):
        # slow parallax; not tied 1:1 to world speed
        self.x -= (world_speed * 0.25 + self.speed) * dt

    def draw(self, surf):
        x, y = int(self.x), int(self.y)
        pygame.draw.circle(surf, COL_CLOUD, (x, y), 12)
        pygame.draw.circle(surf, COL_CLOUD, (x + 15, y + 4), 10)
        pygame.draw.circle(surf, COL_CLOUD, (x - 14, y + 6), 9)

    def off(self):
        return self.x < -50

class Cactus:
    def __init__(self, x):
        self.x = x
        self.w = random.choice([16, 24, 28])
        self.h = random.choice([38, 46, 52])
        self.y = GROUND_Y - self.h

    def update(self, dt, speed):
        self.x -= speed * dt

    def rects(self):
        # little forgiving hitbox
        r = pygame.Rect(int(self.x)+2, int(self.y)+4, self.w-4, self.h-4)
        return [r]

    def draw(self, surf):
        x, y, w, h = int(self.x), int(self.y), self.w, self.h
        pygame.draw.rect(surf, COL_OBST, (x + w//3, y, w//3, h))  # trunk
        # arms
        pygame.draw.rect(surf, COL_OBST, (x, y + h//3, w//3, h//3))
        pygame.draw.rect(surf, COL_OBST, (x + 2*w//3, y + h//2 - h//6, w//3, h//3))

    def off(self):
        return self.x + self.w < -20

class Pterodactyl:
    def __init__(self, x):
        self.x = x
        self.alt = random.randint(PTERO_MIN_ALT, PTERO_MAX_ALT)  # above ground
        self.y = GROUND_Y - self.alt
        self.wing = 0.0

    def update(self, dt, speed):
        self.x -= (speed * 1.1) * dt
        self.wing += dt * 10

    def rects(self):
        # approximate body + head
        body = pygame.Rect(int(self.x), int(self.y) - 10, 40, 20)
        head = pygame.Rect(int(self.x) + 38, int(self.y) - 8, 16, 10)
        return [body, head]

    def draw(self, surf):
        x, y = int(self.x), int(self.y)
        # body
        pygame.draw.rect(surf, COL_PTERO, (x, y - 10, 40, 20), border_radius=4)
        # head/beak
        pygame.draw.polygon(surf, COL_PTERO, [(x + 40, y - 6), (x + 54, y - 2), (x + 40, y + 2)])
        # wings (flap)
        amp = 14
        dy = int(amp * (1 if int(self.wing) % 2 == 0 else -1))
        pygame.draw.line(surf, COL_PTERO, (x + 10, y), (x - 20, y + dy), 4)
        pygame.draw.line(surf, COL_PTERO, (x + 26, y), (x + 56, y - dy), 4)

    def off(self):
        return self.x < -80

class Trex:
    def __init__(self):
        self.x = 90
        self.y = GROUND_Y - RUN_H
        self.vy = 0.0
        self.on_ground = True
        self.ducking = False
        self.anim = 0.0

    @property
    def rect(self):
        if self.ducking and self.on_ground:
            return pygame.Rect(self.x, int(self.y + (RUN_H - DUCK_H)), 52, DUCK_H)
        else:
            return pygame.Rect(self.x, int(self.y), 38, RUN_H)

    def update(self, dt, keys):
        self.anim += dt * 10

        # Duck only when on ground
        self.ducking = (keys[pygame.K_DOWN] or keys[pygame.K_s]) and self.on_ground

        # Jump
        if (keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]) and self.on_ground:
            self.vy = JUMP_VEL
            self.on_ground = False

        # Gravity
        if not self.on_ground:
            self.vy += GRAVITY * dt
            self.y += self.vy * dt
            if self.y >= GROUND_Y - RUN_H:
                self.y = GROUND_Y - RUN_H
                self.vy = 0
                self.on_ground = True

    def draw(self, surf):
        r = self.rect
        # body
        pygame.draw.rect(surf, COL_DINO, r, border_radius=4)

        # legs (run cycle)
        if self.on_ground and not self.ducking:
            phase = int(self.anim) % 2
            lx = r.x + 6
            rx = r.x + r.w - 12
            y = r.bottom
            pygame.draw.line(surf, COL_DINO, (lx, y), (lx, y + (6 if phase == 0 else 2)), 4)
            pygame.draw.line(surf, COL_DINO, (rx, y), (rx, y + (2 if phase == 0 else 6)), 4)

        # tail
        pygame.draw.polygon(surf, COL_DINO, [(r.x - 10, r.y + 8), (r.x + 2, r.y + 12), (r.x - 10, r.y + 18)])

        # eye
        pygame.draw.circle(surf, COL_DINO_EYE, (r.x + r.w - 10, r.y + 10), 3)

# -------------------- Game --------------------
class Game:
    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.state = "MENU"
        self.highscore_m = load_highscore()   # meters
        self.reset()

    def reset(self):
        self.trex = Trex()
        self.ground = Ground()
        self.clouds = []
        x = 0
        for _ in range(5):
            x += random.randint(CLOUD_MIN_GAP, CLOUD_MAX_GAP)
            self.clouds.append(Cloud(WIDTH + x))

        self.obstacles = []
        self.spawn_x_cactus = WIDTH + random.randint(CACTUS_MIN_GAP, CACTUS_MAX_GAP)
        self.spawn_x_ptero  = WIDTH + random.randint(PTERO_MIN_GAP, PTERO_MAX_GAP)

        self.distance_px = 0.0
        self.speed = BASE_SPEED
        self.alive = True
        self.elapsed = 0.0
        self.flash_timer = 0.0

    # ---------- Spawning ----------
    def maybe_spawn(self):
        # spawn cacti
        if not any(isinstance(o, Cactus) and o.x > self.spawn_x_cactus - 150 for o in self.obstacles):
            if self.spawn_x_cactus < WIDTH + 20:
                self.obstacles.append(Cactus(WIDTH + 10))
                gap = random.randint(CACTUS_MIN_GAP, CACTUS_MAX_GAP)
                self.spawn_x_cactus = WIDTH + gap
            else:
                self.spawn_x_cactus -= self.speed / FPS

        # spawn pterodactyls after 150 m to ease early game
        meters = self.distance_px / 100.0
        if meters >= 150 / 10:
            if not any(isinstance(o, Pterodactyl) and o.x > self.spawn_x_ptero - 200 for o in self.obstacles):
                if self.spawn_x_ptero < WIDTH + 20:
                    self.obstacles.append(Pterodactyl(WIDTH + 10))
                    gap = random.randint(PTERO_MIN_GAP, PTERO_MAX_GAP)
                    self.spawn_x_ptero = WIDTH + gap
                else:
                    self.spawn_x_ptero -= self.speed / FPS

        # clouds
        if (len(self.clouds) == 0) or (self.clouds[-1].x < WIDTH - random.randint(CLOUD_MIN_GAP, CLOUD_MAX_GAP)):
            self.clouds.append(Cloud(WIDTH + 40))

    # ---------- Update / Draw ----------
    def update(self, dt):
        if self.state != "PLAY":
            return

        self.elapsed += dt

        keys = pygame.key.get_pressed()
        self.trex.update(dt, keys)

        # world speed grows with distance: +SPEED_PER_100M for each 100 meters
        meters = self.distance_px / 100.0
        self.speed = BASE_SPEED + SPEED_PER_100M * (meters // 10)  # every 100 m (since 100px == 1m below)
        self.speed = min(self.speed, 900)  # clamp just in case

        # move world
        self.ground.update(dt, self.speed)
        for cl in list(self.clouds):
            cl.update(dt, self.speed)
            if cl.off(): self.clouds.remove(cl)

        for o in list(self.obstacles):
            o.update(dt, self.speed)
            if o.off(): self.obstacles.remove(o)

        # distance accumulation:
        # define 100 px = 1 meter (so m = px/100)
        self.distance_px += self.speed * dt

        self.maybe_spawn()

        # collisions
        trex_r = self.trex.rect
        hit = False
        for o in self.obstacles:
            for r in o.rects():
                if trex_r.colliderect(r):
                    hit = True
                    break
            if hit: break

        if hit:
            self.state = "GAME_OVER"
            dist_m = int(self.distance_px / 100.0)
            if dist_m > self.highscore_m:
                self.highscore_m = dist_m
                save_highscore(self.highscore_m)

    def draw_hud(self):
        # distance and speed
        dist_m = int(self.distance_px / 100.0)
        draw_text(self.screen, f"DIST: {dist_m} m", 22, COL_TEXT, (90, 24))
        draw_text(self.screen, f"SPEED: {int(self.speed)} px/s", 18, (90, 90, 90), (260, 24))
        draw_text(self.screen, f"BEST: {int(self.highscore_m)} m", 18, (120, 120, 120), (WIDTH - 90, 24))

    def draw_game(self):
        self.screen.fill(COL_BG)

        # clouds (back)
        for cl in self.clouds:
            cl.draw(self.screen)

        # ground & pebbles
        self.ground.draw(self.screen)

        # obstacles
        for o in self.obstacles:
            o.draw(self.screen)

        # T-Rex
        self.trex.draw(self.screen)

        # HUD
        self.draw_hud()

    def draw_menu(self):
        self.screen.fill(COL_BG)
        draw_text(self.screen, "T-Rex Desert Run", 42, COL_TEXT, (WIDTH // 2, HEIGHT // 3 - 10))
        draw_text(self.screen, "Jump over cactuses • Dodge pterodactyls", 20, (100, 100, 100), (WIDTH // 2, HEIGHT // 3 + 32))
        draw_text(self.screen, "Press ENTER / SPACE to Start", 22, (30, 30, 30), (WIDTH // 2, HEIGHT // 3 + 78))
        draw_text(self.screen, "Controls: SPACE/UP/W to jump • DOWN/S to duck", 18, (110, 110, 110), (WIDTH // 2, HEIGHT // 3 + 110))
        draw_text(self.screen, f"Best Distance: {int(self.highscore_m)} m", 18, (110, 110, 110), (WIDTH // 2, HEIGHT // 3 + 140))

        # idle dino + cactus
        pygame.draw.rect(self.screen, COL_OBST, (WIDTH//2 - 200, GROUND_Y - 46, 12, 46))
        pygame.draw.rect(self.screen, COL_OBST, (WIDTH//2 - 200 - 10, GROUND_Y - 22, 10, 20))
        dummy = Trex()
        dummy.x = WIDTH//2 + 140
        dummy.draw(self.screen)
        pygame.draw.line(self.screen, COL_GROUND, (0, GROUND_Y), (WIDTH, GROUND_Y), 2)

    def draw_game_over(self):
        self.draw_game()
        # overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, 200))
        self.screen.blit(overlay, (0, 0))

        dist_m = int(self.distance_px / 100.0)
        draw_text(self.screen, "You Died!", 44, COL_TEXT, (WIDTH // 2, HEIGHT // 2 - 30))
        draw_text(self.screen, f"Distance: {dist_m} m", 26, COL_TEXT, (WIDTH // 2, HEIGHT // 2 + 6))
        draw_text(self.screen, f"Best: {int(self.highscore_m)} m", 20, (90, 90, 90), (WIDTH // 2, HEIGHT // 2 + 36))
        draw_text(self.screen, "R / ENTER / SPACE: Retry   •   M: Menu   •   Q: Quit", 18, (60,60,60), (WIDTH // 2, HEIGHT // 2 + 70))

    # ---------------- Loop & Input ----------------
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
                    if e.key in (pygame.K_ESCAPE,):
                        self.state = "MENU"
                elif self.state == "GAME_OVER":
                    if e.key in (pygame.K_r, pygame.K_RETURN, pygame.K_SPACE):
                        self.state = "PLAY"; self.reset()
                    elif e.key == pygame.K_m:
                        self.state = "MENU"
                    elif e.key == pygame.K_q:
                        pygame.quit(); sys.exit()

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            if self.state == "PLAY":
                self.update(dt)

            if self.state == "MENU":
                self.draw_menu()
            elif self.state == "PLAY":
                self.draw_game()
            elif self.state == "GAME_OVER":
                self.draw_game_over()

            pygame.display.flip()

# -------------------- Entrypoint --------------------
def main():
    pygame.init()
    pygame.display.set_caption("T-Rex Desert Run — Start Menu & Died Screen")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    Game(screen).run()

if __name__ == "__main__":
    main()
